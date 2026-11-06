"""Identity-matched football badges and public V1 sports images.

Provider IDs are never guessed or supplied by a language model. The registry
stores verified name/ID pairs; SportsAPI search is optional and requires a key.
"""
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
from urllib.parse import urlparse
import requests
from PIL import Image
from footybitez.media.real_assets import identity_tokens


class LogoPage(HTMLParser):
    def __init__(self):
        super().__init__(); self.images=[]; self.links=[]; self.current=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='img': self.images.append(attrs)
        if tag=='a': self.current=[attrs.get('href',''),'']
    def handle_data(self,data):
        if self.current is not None: self.current[1]+=data
    def handle_endtag(self,tag):
        if tag=='a' and self.current is not None:
            self.links.append(self.current); self.current=None


def sports_image_url(entity_type, entity_id, version=1):
    if entity_type not in ('competitors','competitions','countries','athletes'):
        raise ValueError('Unsupported SportsAPI image type')
    if not str(entity_id).isdigit() or not str(version).isdigit():
        raise ValueError('SportsAPI IDs and image versions must be numeric')
    return f'https://api.sportsapipro.com/v1/football/images/{entity_type}/{entity_id}?imageVersion={version}'


def _save_image(sourcer,url,entity,source,page,role):
    path=Path(sourcer.download_dir)/('football_asset_'+hashlib.sha256(url.encode()).hexdigest()[:20]+'.png')
    try:
        if not path.exists():
            response=requests.get(url,timeout=20)
            response.raise_for_status()
            if not response.headers.get('Content-Type','').startswith('image/') or len(response.content)>12_000_000:
                return None
            path.write_bytes(response.content)
        with Image.open(path) as image:
            image.load()
            if min(image.size)<48: return None
        meta={'source':source,'source_page':page,'url':url,'subject':entity,'role':role,
              'license':'Provider editorial asset; underlying rights belong to their owners'}
        Path(str(path)+'.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
        sourcer._add_credit(f'{entity}: {source} — {page}; {role}; rights remain with their owners')
        return str(path)
    except (requests.RequestException,OSError,ValueError):
        return None


def football_logo(sourcer,entity):
    """Resolve exact club names from the provider's own index and image alt text."""
    expected=identity_tokens(entity)
    if not expected: return None
    if not hasattr(sourcer,'_football_logo_index'):
        try:
            response=requests.get('https://football-logos.cc/',timeout=15); response.raise_for_status()
            index=LogoPage();index.feed(response.text)
            sourcer._football_logo_index=index.links
        except requests.RequestException:
            sourcer._football_logo_index=[]
    page=next(('https://football-logos.cc'+href for href,name in sourcer._football_logo_index
               if identity_tokens(name)==expected and href.startswith('/') and not href.startswith('//')),None)
    if page:
        try:
            response=requests.get(page,timeout=15);response.raise_for_status()
            parser=LogoPage();parser.feed(response.text)
            for image in parser.images:
                alt=image.get('alt','').split(' logo')[0]
                url=image.get('src','')
                if identity_tokens(alt)==expected and urlparse(url).hostname=='assets.football-logos.cc' and url.lower().endswith('.png'):
                    result=_save_image(sourcer,url,entity,'football-logos.cc',page,'club badge for editorial identification')
                    if result: return result
        except requests.RequestException: pass
    return sports_entity_image(sourcer,entity,('competitors','competitions'))


def sports_entity_image(sourcer,entity,types=('athletes',)):
    registry_path=Path('footybitez/data/football_image_ids.json')
    registry=json.loads(registry_path.read_text(encoding='utf-8')) if registry_path.exists() else []
    for item in registry:
        if item['type'] in types and identity_tokens(item['name'])==identity_tokens(entity):
            url=sports_image_url(item['type'],item['id'],item.get('imageVersion',1))
            return _save_image(sourcer,url,entity,'SportsAPI Pro',
                'https://docs.sportsapipro.com/api-reference/v1-legacy/images',
                'athlete portrait' if item['type']=='athletes' else 'editorial badge')
    return None


def scene_club_logos(sourcer,scene):
    text=' '.join(str(scene.get(key,'')) for key in ('text','narration_snippet','caption','motion_label'))
    names=[item.get('name','') if isinstance(item,dict) else item for item in scene.get('named_entities',[])]
    names+=scene.get('visual_entities',[])
    # Require the club to occur in the scene, rather than decorating an unrelated story.
    return list(dict.fromkeys(path for name in names if name and name.lower() in text.lower()
                             if (path:=football_logo(sourcer,name))))[:2]
