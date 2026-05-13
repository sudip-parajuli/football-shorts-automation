"""
Downloads free cinematic sound effects from Pixabay.
Requires PIXABAY_API_KEY in environment (free signup at pixabay.com/api/docs/).
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

SOUNDS_OUT_DIR = "remotion-video/public/assets/sounds"

# Curated search queries for different SFX categories
SFX_QUERIES = {
    "whoosh": "whoosh cinematic",
    "transition": "transition swoosh",
    "impact": "impact cinematic hit",
    "drum": "cinematic drum hit",
    "rise": "cinematic rise swell",
}


def _pixabay_search(api_key: str, query: str, per_page: int = 5) -> list:
    """Search Pixabay sounds and return download URLs."""
    try:
        url = "https://pixabay.com/api/sounds/"
        params = {"key": api_key, "q": query, "per_page": per_page}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        return [h["sound_url"] for h in hits if h.get("sound_url")]
    except Exception as e:
        logger.warning(f"Pixabay search failed for '{query}': {e}")
        return []


def download_sound_effects(force: bool = False) -> dict:
    """
    Downloads one sound per category into SOUNDS_OUT_DIR.
    Returns dict mapping category -> local relative path (from public/).
    Falls back gracefully if API key missing or calls fail.
    """
    api_key = os.getenv("PIXABAY_API_KEY")
    os.makedirs(SOUNDS_OUT_DIR, exist_ok=True)

    results = {}

    if not api_key:
        logger.warning("PIXABAY_API_KEY not set. Sound effects will be skipped.")
        return results

    for category, query in SFX_QUERIES.items():
        dest_path = os.path.join(SOUNDS_OUT_DIR, f"{category}.mp3")
        rel_path = f"assets/sounds/{category}.mp3"

        # Skip if already downloaded and not forcing
        if os.path.exists(dest_path) and not force:
            logger.info(f"SFX '{category}' already exists. Skipping download.")
            results[category] = rel_path
            continue

        urls = _pixabay_search(api_key, query, per_page=3)
        downloaded = False
        for sound_url in urls:
            try:
                r = requests.get(sound_url, timeout=15)
                r.raise_for_status()
                with open(dest_path, "wb") as f:
                    f.write(r.content)
                logger.info(f"Downloaded SFX '{category}' -> {dest_path}")
                results[category] = rel_path
                downloaded = True
                break
            except Exception as e:
                logger.warning(f"Failed to download '{sound_url}': {e}")

        if not downloaded:
            logger.warning(f"Could not download SFX for category '{category}'.")

    return results
