"""Club match previews and recaps using verified fixture data."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path

import requests

from footybitez.data.worldcup_data import API_FOOTBALL_BASE, FOOTBALL_DATA_BASE

logger = logging.getLogger(__name__)
COMPETITIONS = {
    39: "Premier League", 140: "La Liga", 78: "Bundesliga", 135: "Serie A",
    61: "Ligue 1", 2: "UEFA Champions League", 253: "MLS", 307: "Saudi Pro League",
}
FOOTBALL_DATA_CODES = {"PL": 39, "PD": 140, "BL1": 78, "SA": 135, "FL1": 61, "CL": 2}
FINISHED = {"FT", "AET", "PEN"}


def score_pair(value):
    if not isinstance(value, dict):
        return None
    home, away = value.get("home"), value.get("away")
    return (home, away) if type(home) is int and type(away) is int and min(home, away) >= 0 else None


def fetch_fixtures(mode, now):
    begin, end = (now, now + timedelta(hours=6)) if mode == "pre" else (now - timedelta(hours=8), now)
    api_key = os.getenv("API_FOOTBALL_KEY")
    data_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if api_key:
        try:
            fixtures = []
            day = begin.date()
            while day <= end.date():
                response = requests.get(f"{API_FOOTBALL_BASE}/fixtures", params={"date": day.isoformat()},
                                        headers={"x-apisports-key": api_key}, timeout=25)
                response.raise_for_status()
                body = response.json()
                if body.get("errors") or body.get("paging", {}).get("total", 1) > 1:
                    raise ValueError("Fixture feed rejected the request or returned incomplete results")
                fixtures.extend(body["response"])
                day += timedelta(days=1)
            return fixtures
        except (requests.RequestException, ValueError, KeyError):
            if not data_key:
                raise
            logger.warning("API-Football unavailable. Using football-data.org for the six European competitions.")
    if not data_key:
        raise RuntimeError("Set API_FOOTBALL_KEY or FOOTBALL_DATA_API_KEY for club fixture discovery")
    response = requests.get(f"{FOOTBALL_DATA_BASE}/matches",
                            headers={"X-Auth-Token": data_key},
                            params={"competitions": ",".join(FOOTBALL_DATA_CODES),
                                    "dateFrom": begin.date().isoformat(),
                                    "dateTo": (end.date() + timedelta(days=1)).isoformat()}, timeout=25)
    response.raise_for_status()
    fixtures = []
    for match in response.json()["matches"]:
        league = FOOTBALL_DATA_CODES.get(match["competition"]["code"])
        status = {"TIMED": "NS", "SCHEDULED": "NS", "FINISHED": "FT"}.get(match["status"])
        score = match.get("score") or {}
        goals = score_pair(score.get("fullTime"))
        penalties = score_pair(score.get("penalties"))
        if score.get("duration") == "PENALTY_SHOOTOUT":
            status = "PEN" if status == "FT" else status
            goals = tuple(total - penalty for total, penalty in zip(goals, penalties)) if goals and penalties else None
        elif score.get("duration") == "EXTRA_TIME" and status == "FT":
            status = "AET"
        fixtures.append({
            "fixture": {"id": match["id"], "date": match["utcDate"], "status": {"short": status}, "venue": {}},
            "league": {"id": league}, "teams": {"home": match["homeTeam"], "away": match["awayTeam"]},
            "goals": dict(zip(("home", "away"), goals)) if goals else None,
            "score": {"penalty": score.get("penalties"), "halftime": score.get("halfTime")}, "source": "football-data.org",
        })
    return fixtures


def eligible_fixtures(fixtures, mode, now, recorded):
    candidates = []
    for item in fixtures:
        league = COMPETITIONS.get(item["league"]["id"])
        if not league:
            continue
        fixture = item["fixture"]
        kickoff = datetime.fromisoformat(fixture["date"].replace("Z", "+00:00"))
        delta = kickoff - now
        status = fixture["status"]["short"]
        goals = score_pair(item.get("goals"))
        penalties = score_pair((item.get("score") or {}).get("penalty"))
        if mode == "pre":
            eligible = status == "NS" and timedelta(0) < delta <= timedelta(hours=6)
        else:
            eligible = (status in FINISHED and -timedelta(hours=8) <= delta <= timedelta(0)
                        and goals is not None and (status != "PEN" or (penalties is not None
                             and penalties[0] != penalties[1])))
        home, away = (item["teams"][side]["name"] for side in ("home", "away"))
        # Teams and kickoff identify the same match when the provider changes.
        from footybitez.media.real_assets import identity_tokens
        identity = "|".join(" ".join(sorted(identity_tokens(team))) for team in (home, away))
        key = f"{item['league']['id']}:{kickoff.astimezone(timezone.utc).isoformat()}:{identity}"
        if eligible and key not in recorded:
            candidates.append((kickoff, key, league, home, away, item, goals, penalties))
    return sorted(candidates, key=lambda row: (row[0], row[1]))


def match_story(candidate, mode):
    kickoff, _, league, home, away, item, goals, penalties = candidate
    venue = (item["fixture"].get("venue") or {}).get("name")
    fixture_date = kickoff.astimezone(timezone.utc).strftime("%A %d %B at %H:%M UTC")
    if mode == "pre":
        title = f"{home} vs {away} | {league} preview"
        hook = f"{home} face {away} in the {league}."
        first = f"The match is scheduled for {fixture_date}."
        if venue:
            first += f" The venue is {venue}."
        first += f" {home} are listed as the home side for this fixture."
        second = f"How should {away} approach the opening minutes? An early press can disrupt the home side, while sitting deeper can leave space for a counterattack. Which approach would you choose?"
    else:
        home_goals, away_goals = goals
        title = f"{home} {home_goals}–{away_goals} {away} | {league}"
        hook = f"Full time in the {league}: {home} {home_goals}, {away} {away_goals}."
        first = f"The fixture kicked off on {fixture_date}."
        if venue:
            first += f" The teams played at {venue}."
        if item["fixture"]["status"]["short"] == "PEN":
            title += f" (pens {penalties[0]}–{penalties[1]})"
            first += f" The shootout finished {penalties[0]} to {penalties[1]}."
        elif item["fixture"]["status"]["short"] == "AET":
            first += " That score includes goals scored during extra time."
        halftime = score_pair((item.get("score") or {}).get("halftime"))
        second = ""
        if halftime:
            second = f"At half time, the score was {halftime[0]} to {halftime[1]}. "
        if item["fixture"]["status"]["short"] == "PEN":
            winner = home if penalties[0] > penalties[1] else away
            second += f"{winner} won the shootout. "
        elif home_goals == away_goals:
            second += "The teams finished level. "
        else:
            winner = home if home_goals > away_goals else away
            second += f"{winner} won by a margin of {abs(home_goals - away_goals)}. "
        second += "Which moment changed the game for you? Was it a goal, a defensive decision, or a change made from the bench?"
    if len(hook.split()) > 16:
        first = f"{hook} {first}"
        hook = f"Here is the latest from the {league}."
    outro = "Tell us what stood out to you and what you would look for in the next match."
    return {"title": title, "hook": hook, "outro": outro, "segments": [
        {"text": first, "visual_keyword": f"{home} {away} fixture"},
        {"text": second, "visual_keyword": f"{home} {away} fixture"},
    ]}


def run(mode, publish=False):
    now = datetime.now(timezone.utc)
    state_path = Path(f"club_{mode}_match_registry.json")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    fixtures = eligible_fixtures(fetch_fixtures(mode, now), mode, now, state)
    if not fixtures:
        logger.info("No eligible unposted club %s-match fixtures in the current window.", mode)
        return

    candidate = fixtures[0]
    kickoff, key, league, home, away, item, goals, penalties = candidate
    script = match_story(candidate, mode)
    output = Path("footybitez/output")
    output.mkdir(parents=True, exist_ok=True)
    card = output / f"card_club_{mode}.jpg"
    from footybitez.media.card_generator import draw_pre_match_card_1_hook, draw_post_match_card_1_score
    if mode == "pre":
        venue = item["fixture"].get("venue") or {}
        details = venue.get("name") or kickoff.astimezone(timezone.utc).strftime("%d %b · %H:%M UTC")
        draw_pre_match_card_1_hook(home, away, league, details, str(card))
    else:
        label = league
        if item["fixture"]["status"]["short"] == "PEN":
            label = f"{league} · pens {penalties[0]}–{penalties[1]}"
        draw_post_match_card_1_score(home, away, *goals, label, str(card))

    from footybitez.video.remotion_video_creator import RemotionVideoCreator
    video = RemotionVideoCreator().create_video(script, {
        "title_card": str(card), "outro_image": str(card),
        "segment_media": [[str(card)] for _ in script["segments"]],
    })
    if not publish:
        logger.info("Preview rendered at %s", video)
        return

    def save():
        temporary = state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
        temporary.replace(state_path)

    from footybitez.youtube.uploader import YouTubeUploader
    from footybitez.socials.social_orchestrator import SocialOrchestrator
    source = item.get("source", "API-Football")
    description = f"{script['title']}\n\n{script['full_text']}\n\nFixture data: {source}"
    record = state[key] = {"status": "pending", "title": script["title"]}
    save()
    video_id = YouTubeUploader().upload_video(video, script["title"][:100], description, ["football", "shorts", league])
    if not video_id:
        raise RuntimeError("YouTube upload returned no ID. Check the pending registry entry before retrying.")
    record.update(status="youtube_published", youtube=video_id)
    save()
    record["social"] = SocialOrchestrator(skip_tiktok=True).publish_to_all(video, script["title"][:100], description)
    record["status"] = "published"
    save()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("pre", "post"))
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    run(args.mode, args.publish)
