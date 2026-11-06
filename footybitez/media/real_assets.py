"""Real entity photos and illustrative stock footage with source provenance."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse, unquote
import requests


def identity_tokens(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"\([^)]*\)", "", value)
    return set(re.findall(r"[a-z0-9]+", value)) - {"fc", "f", "c", "afc", "a", "football", "club", "cf", "the"}


def exact_entity_match(entity, page):
    expected = identity_tokens(entity)
    actual = identity_tokens(page.get("title", ""))
    extract = page.get("extract", "").lower()
    return bool(expected and expected == actual and any(term in extract for term in
        ("football", "soccer", "stadium", "fifa", "uefa", "goalkeeper", "footballer")))


def wikipedia_primary_photo(sourcer, entity):
    """Use the primary photo on the matching football article, never random files.

    Identity and source metadata supply the fallback when the vision quota is
    unavailable. This path is for entity portraits only, never dated match proof.
    """
    if len(identity_tokens(entity)) < 2:
        return None
    params = {"action":"query", "format":"json", "redirects":1, "titles":entity,
              "prop":"pageimages|extracts", "piprop":"original", "exintro":1, "explaintext":1, "exchars":900}
    try:
        response = requests.get("https://en.wikipedia.org/w/api.php", params=params,
                                headers={"User-Agent":"FootyBitez/2.0 (football documentary automation)"}, timeout=12)
        response.raise_for_status()
        for page in response.json().get("query", {}).get("pages", {}).values():
            if not exact_entity_match(entity, page):
                continue
            url = page.get("original", {}).get("source", "")
            host = urlparse(url).hostname or ""
            if not host.endswith("wikimedia.org") or sourcer._is_bad_image(url=url, title=page.get("title", "")):
                continue
            if url.lower().endswith(".svg"):
                continue
            # Retrieve the actual file's author/license, not just an article link.
            filename = unquote(urlparse(url).path.rsplit('/', 1)[-1])
            info = requests.get('https://commons.wikimedia.org/w/api.php',
                params={'action':'query','format':'json','titles':'File:'+filename,
                        'prop':'imageinfo','iiprop':'extmetadata|url'},
                headers={'User-Agent':'FootyBitez/2.0'},timeout=12)
            info.raise_for_status()
            files = info.json().get('query',{}).get('pages',{}).values()
            details = next((item['imageinfo'][0] for item in files if item.get('imageinfo')), {})
            metadata = details.get('extmetadata',{})
            def value(key):
                return re.sub('<[^>]+>', '', metadata.get(key,{}).get('value','')).strip()
            license_name = value('LicenseShortName')
            if not license_name or not (license_name.startswith(('CC BY','CC0','Public domain'))):
                continue
            path = Path(sourcer.download_dir) / f"entity_{hashlib.sha256(url.encode()).hexdigest()[:16]}.jpg"
            sourcer._download_file(url, str(path), context_query=entity, strict=False)
            if path.is_file():
                page_url = "https://en.wikipedia.org/wiki/" + page["title"].replace(" ", "_")
                meta = {"source":"Wikipedia primary entity image", "subject":entity, "url":url,
                        "source_page":details.get('descriptionurl',page_url), "license":license_name,
                        "license_url":value('LicenseUrl'), "creator":value('Artist'),
                        "verification":"exact football article identity; entity portrait, not match footage"}
                Path(str(path)+".json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
                sourcer._add_credit(f"{entity}: {meta['creator']} / {license_name} / {meta['source_page']} / {meta['license_url']}; cropped/overlaid")
                return str(path)
    except (requests.RequestException, ValueError, TypeError):
        pass
    return None


def supported_entities(segment, script):
    """Only source people/places actually mentioned in narration or evidence."""
    allowed = " ".join([segment.get("text", ""), *segment.get("source_quotes", []), script.get("research_context", "")]).lower()
    candidates = list(segment.get("visual_entities", []))
    primary = script.get("primary_entity", "")
    if primary and primary.lower() in allowed:
        candidates.append(primary)
    output = []
    for entity in candidates:
        if isinstance(entity, str) and len(identity_tokens(entity)) >= 2 and entity.lower() in allowed and entity not in output:
            output.append(entity)
    return output[:3]


def stock_query(text):
    lower = text.lower()
    if 'contract' in lower and any(term in lower for term in ('sign', 'negotiat')):
        return "contract signing"
    if any(term in lower for term in ("stadium", "crowd", "fans")):
        return "soccer stadium"
    if any(term in lower for term in ("kit", "shirt", "jersey")):
        return "soccer jersey"
    if any(term in lower for term in ('training', 'practice', 'drill')):
        return "soccer training"
    return None


def pexels_short_clip(sourcer, query, index=0):
    if not query or not sourcer.pexels_api_key:
        return None
    try:
        response = requests.get("https://api.pexels.com/v1/videos/search",
            headers={"Authorization":sourcer.pexels_api_key},
            params={"query":query,"orientation":"portrait","per_page":6},timeout=15)
        response.raise_for_status()
        videos = response.json().get("videos", [])
        # Rotate candidates to avoid showing one stock clip for every segment.
        videos = videos[index % len(videos):] + videos[:index % len(videos)] if videos else []
        for video in videos:
            files = [item for item in video.get("video_files", []) if item.get("file_type")=="video/mp4"
                     and item.get("height",0)>=720 and item.get("width",0)>=480]
            files.sort(key=lambda item: (item.get("width",0)*item.get("height",0)))
            if not files:
                continue
            file = files[0]
            path = Path(sourcer.download_dir) / f"pexels_video_{video['id']}.mp4"
            # Pexels is a curated stock source; this is visibly labelled
            # illustrative footage, never presented as a specific named event.
            with requests.get(file["link"], stream=True, timeout=45) as download:
                download.raise_for_status()
                with path.open("wb") as output:
                    for chunk in download.iter_content(65536):
                        output.write(chunk)
            if path.stat().st_size < 10000:
                path.unlink(missing_ok=True)
                continue
            meta = {"source":"Pexels", "source_page":video.get("url", ""), "query":query,
                    "creator":video.get("user", {}).get("name", ""), "license":"Pexels License", "role":"illustrative stock footage"}
            Path(str(path)+".json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
            sourcer._add_credit(f"Video: {meta['creator']} / Pexels — {meta['source_page']} (Pexels License)")
            return str(path)
    except (requests.RequestException, ValueError, KeyError, TypeError, OSError):
        pass
    return None


def segment_real_media(sourcer, segment, script, index):
    paths = []
    for entity in supported_entities(segment, script):
        path = wikipedia_primary_photo(sourcer, entity)
        if not path:
            from footybitez.media.football_assets import sports_entity_image
            path = sports_entity_image(sourcer, entity)
        if path and path not in paths:
            paths.append(path)
    if not paths:
        paths = sourcer.get_media(segment.get("visual_keyword", "football soccer"), count=2)
    clip = None
    if not supported_entities(segment, script):
        clip = pexels_short_clip(sourcer, stock_query(segment.get("text", "")), index)
    if clip:
        paths.append(clip)
    return paths
