"""Run with python -m footybitez.social_post_main. Preview unless --publish."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import requests
from footybitez.socials.post_composer import compose_caption, plain, render_overlay, render_story_post
from footybitez.socials.photo_posts import publish_post

TOPICS = {
    'players': ['Cristiano Ronaldo longevity and training', 'Lionel Messi early years at Barcelona'],
    'coaches': ['Pep Guardiola positional play', 'Carlo Ancelotti Champions League coaching'],
    'lifestyle': ['Cristiano Ronaldo professional training routine', 'Mohamed Salah early football career'],
    'trophies': ['FIFA World Cup Trophy design and history', 'UEFA Champions League trophy history'],
    'stats': ['Miroslav Klose World Cup goal record', 'Just Fontaine 1958 World Cup goals'],
    'matches': ['Manchester United 1999 Champions League final comeback', 'Liverpool 2005 Champions League final comeback'],
}


def result_headline(match):
    home,away=match['homeTeam']['name'],match['awayTeam']['name']
    score=match['score']['fullTime']
    h,a=score['home'],score['away']
    duration=match['score'].get('duration','REGULAR')
    suffix=' (aet)' if duration=='EXTRA_TIME' else ''
    if duration=='PENALTY_SHOOTOUT':
        penalties=match['score'].get('penalties',{})
        if not all(type(penalties.get(key)) is int for key in ('home','away')):
            raise RuntimeError('Shootout result is missing verified penalty scores')
        h-=penalties['home']; a-=penalties['away']
        if h<0 or a<0:
            raise RuntimeError('Inconsistent shootout scores')
        suffix=f" (pens {penalties['home']}–{penalties['away']})"
    return f'{home} {h}–{a} {away}{suffix}'


def verified_result(now=None):
    now = now or datetime.now(timezone.utc)
    key = os.getenv('FOOTBALL_DATA_API_KEY')
    if not key:
        raise RuntimeError('Results posts require FOOTBALL_DATA_API_KEY; no score will be invented')
    response = requests.get('https://api.football-data.org/v4/matches',
        headers={'X-Auth-Token':key}, params={'dateFrom':(now-timedelta(days=1)).date().isoformat(),
        'dateTo':now.date().isoformat(),'status':'FINISHED'},timeout=25)
    response.raise_for_status()
    candidates=[]
    for match in response.json().get('matches',[]):
        kickoff=datetime.fromisoformat(match['utcDate'].replace('Z','+00:00'))
        score=match.get('score',{}).get('fullTime',{})
        if match.get('status')=='FINISHED' and timedelta(0)<=now-kickoff<=timedelta(hours=24) and all(type(score.get(k)) is int for k in ('home','away')):
            candidates.append(match)
    if not candidates:
        raise RuntimeError('No verified finished match from the last 24 hours; skipping result post')
    match=sorted(candidates,key=lambda m:m['utcDate'],reverse=True)[0]
    home,away=match['homeTeam']['name'],match['awayTeam']['name']
    title=result_headline(match)
    caption=f"Full time: {title}\n\n{match['competition']['name']} | {match['utcDate'][:10]}\nScore shown as reported by football-data.org (including extra time when applicable).\n\nWhat stood out to you?\n\nSource: https://www.football-data.org/\n#football #matchday"
    return title,caption,[home,away],match


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--topic',default='')
    parser.add_argument('--category',choices=['auto',*TOPICS,'results'],default='auto')
    parser.add_argument('--format',choices=['auto','photo','text'],default='auto')
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    from footybitez.content.history import ContentHistory, DuplicateContent
    history = ContentHistory() if args.publish else None
    day=datetime.now(timezone.utc).date()
    out=Path('footybitez/output/social_posts'); out.mkdir(parents=True,exist_ok=True)
    state_path=Path('footybitez/data/social_posts_state.json')
    state=json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    # One durable daily slot prevents a manual retry from posting a second topic.
    slot=day.isoformat()
    existing=state.get(slot,{}).get('plan') if args.publish else None
    if existing:
        plan=existing
    else:
        rotation=[*TOPICS,'results'] if os.getenv('FOOTBALL_DATA_API_KEY') else list(TOPICS)
        category=args.category if args.category!='auto' else rotation[day.toordinal()%len(rotation)]
        topic=args.topic or (TOPICS[category][day.toordinal()%2] if category in TOPICS else 'Latest verified result')
        if history and not args.topic and category != 'results':
            pool = [(value,name) for name,values in TOPICS.items() for value in values]
            pool.sort(key=lambda pair: pair[1] != category)
            selected = next(((value,name) for value,name in pool if not history.is_duplicate(value)),None)
            if selected:
                topic, category = selected
            else:
                from footybitez.content.topic_generator import TopicGenerator
                topic, _ = TopicGenerator().get_random_topic()
        if history and not existing and history.is_duplicate(topic):
            logging.info('Topic already used. Skipping %s',topic)
            return
        if category=='results':
            title,caption,entities,evidence=verified_result()
            topic = title + " | " + evidence["utcDate"][:10]
        else:
            from footybitez.content.script_generator import ScriptGenerator
            script=ScriptGenerator().generate_script(topic,category)
            if not script:
                raise RuntimeError('No grounded caption passed editorial checks')
            title=plain(script['title']); caption=compose_caption(script, category)
            entities=list(dict.fromkeys([entity for segment in script['segments'] for entity in segment.get('visual_entities',[])]))
            primary=script.get('primary_entity')
            if primary and primary not in entities:
                entities.insert(0,primary)
            evidence=script
        post_format=args.format if args.format!='auto' else ('text' if day.toordinal()%4==0 else 'photo')
        plan={'slot':slot,'topic':topic,'category':category,'format':post_format,'title':title,'caption':caption,'entities':entities,'evidence':evidence}
    if plan['format']=='photo':
        from footybitez.media.media_sourcer import MediaSourcer
        from footybitez.media.real_assets import wikipedia_primary_photo
        saved_source = plan.get('image_source')
        photo = None
        if plan.get('visual_type') != 'editorial':
            sourcer = MediaSourcer()
            if saved_source:
                original = out/'original.jpg'
                original.unlink(missing_ok=True)
                sourcer._download_file(saved_source['url'],str(original),context_query=saved_source.get('subject','football'),strict=False)
                photo = str(original) if original.is_file() else None
                if not photo:
                    raise RuntimeError('The original published photograph could not be retrieved for this retry')
            else:
                photo = next((path for entity in plan['entities'] if (path:=wikipedia_primary_photo(sourcer,entity))),None)
        if photo:
            plan['image_path'] = render_overlay(photo,plan['title'],out/'post.jpg')
            plan['image_source'] = saved_source or json.loads(Path(photo+'.json').read_text(encoding='utf-8'))
            source = plan['image_source']
            credit = f"\n\nPhoto: {source.get('creator','')} / {source.get('license','')} / {source['source_page']} / {source.get('license_url','')}. Cropped with text overlay; entity photograph."
            if credit not in plan['caption']:
                plan['caption'] += credit
        else:
            logging.info('Creating an editorial image from the sourced caption')
            plan['visual_type'] = 'editorial'
            plan['image_path'] = render_story_post(plan['title'],plan['evidence'],out/'post.jpg')
        if len(plan['caption']) > 2200:
            raise RuntimeError('Caption plus photo attribution exceeds Instagram limit')
    (out/'post.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    (out/'caption.txt').write_text(plan['caption'],encoding='utf-8')
    if args.publish:
        try:
            publish_post(plan,state,state_path)
        except DuplicateContent as error:
            logging.info('Skipping repeated content: %s',error)
            return
    logging.info('Photo post %s: %s', 'published' if args.publish else 'preview saved',out)


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    main()
