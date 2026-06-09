import os
import io
import requests
import random
import re
import warnings
import json
from dotenv import load_dotenv

# Suppress the ddgs package rename warning from duckduckgo_search
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*duckduckgo_search.*ddgs.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*ddgs.*")

# Support both the new 'ddgs' package and the legacy 'duckduckgo_search'
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None


class MediaSourcer:
    def __init__(self, download_dir="footybitez/media/downloads"):
        load_dotenv()
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
        self.unsplash_api_key = os.getenv("UNSPLASH_ACCESS_KEY")
        self.pixabay_api_key = os.getenv("PIXABAY_API_KEY")
        self.gemini_keys = self._collect_gemini_keys()
        self.download_dir = download_dir
        self.credits_file = os.path.join(download_dir, "image_credits.txt")
        
        # Clean directory at startup to ensure no stale cached assets are reused
        self.startup_cleanup()
        os.makedirs(download_dir, exist_ok=True)
        self.used_urls = set()

        # ── Football-only filter constants ──────────────────────────────────
        # Keywords that identify wrong-sport or wrong-gender content
        self._BAD_KEYWORDS = [
            # American football
            "nfl", "gridiron", "american football", "superbowl", "super bowl",
            "touchdown", "quarterback", "helmet", "nfl draft", "cfl", "afl",
            # Rugby
            "rugby", "rugby union", "rugby league",
            # Other sports
            "cricket", "hockey", "nhl", "baseball", "basketball", "nba",
            "tennis", "golf", "boxing", "mma", "handball", "volleyball",
            # Beach/pitch variants (different from standard football)
            "beach soccer", "beach football", "sand soccer", "futsal", "futbol sala",
            "seven-a-side", "five-a-side", "indoor football", "indoor soccer",
            # Wrong gender
            "women", "woman", "female", "ladies", "girls",
            "nwsl", "wsl", "nwt", "women's national", "women football",
            "women soccer", "womens",
        ]
        # Safe suffix appended to every query
        self._FOOTBALL_SAFE_SUFFIX = "association football soccer men"
        # Negative suffix for search engines that support it
        self._FOOTBALL_NEG_SUFFIX = "-nfl -american -rugby -gridiron -cricket -hockey -women -nwsl -wsl -beach -futsal"

        # Initialize credits file
        if os.path.exists(self.credits_file):
            os.remove(self.credits_file)

    def startup_cleanup(self):
        """Cleans download folder of any leftover or failed cache files at startup."""
        import shutil
        if os.path.exists(self.download_dir):
            try:
                for filename in os.listdir(self.download_dir):
                    file_path = os.path.join(self.download_dir, filename)
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
            except Exception as e:
                print(f"Startup cleanup warning: {e}")


    def _collect_gemini_keys(self):
        keys = []
        for suffix in ["", "2", "3"]:
            val = os.getenv(f"GEMINI_API_KEY{suffix}")
            if val:
                keys.append(val)
        return keys

    def cleanup(self):
        """Deletes all downloaded media files to save space."""
        import shutil
        if os.path.exists(self.download_dir):
            try:
                shutil.rmtree(self.download_dir)
                os.makedirs(self.download_dir, exist_ok=True)
                print(f"Cleaned up {self.download_dir}")
            except Exception as e:
                print(f"Cleanup warning: {e}")

    def _add_credit(self, text):
        """Appends a credit line to the credits file."""
        with open(self.credits_file, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    def _write_image_meta(self, filepath: str, source: str, artist: str = ""):
        try:
            with open(filepath + ".json", "w", encoding="utf-8") as f:
                json.dump({"source": source, "artist": artist}, f)
        except Exception:
            pass

    def _download_file(self, url, filepath):
        """Downloads a file using requests with headers."""
        if os.path.exists(filepath):
            return
        try:
            if "wikimedia.org" in url:
                headers = {
                    'User-Agent': 'FootyBitezBot/1.0 (contact: admin@footybitez.com; sudden-developer)'
                }
            else:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0'
                }
            with requests.get(url, headers=headers, stream=True, timeout=15) as r:
                r.raise_for_status()
                if 'text/html' in r.headers.get('Content-Type', '').lower():
                    return
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            if os.path.exists(filepath):
                if os.path.getsize(filepath) < 100:
                    os.remove(filepath)
                else:
                    print(f"DEBUG MEDIA: Downloaded {os.path.basename(filepath)} FROM {url}")

        except Exception as e:
            print(f"Download failed {url}: {e}")


    # ─────────────────────────────────────────────────────────
    # FOOTBALL-ONLY FILTER ENGINE
    # ─────────────────────────────────────────────────────────

    def _make_football_query(self, raw_query: str, is_entity: bool = False) -> str:
        """
        Sanitizes a raw search query to be football-specific.
        Strips bad-sport keywords and appends sport-safe terms.
        """
        q = raw_query.strip()
        # Remove any bad keywords accidentally in the query
        for bk in self._BAD_KEYWORDS:
            q = re.sub(re.escape(bk), "", q, flags=re.IGNORECASE).strip()
        # Always append the safe football suffix
        if self._FOOTBALL_SAFE_SUFFIX not in q.lower():
            q = f"{q} {self._FOOTBALL_SAFE_SUFFIX}"
        return q

    def _is_bad_image(self, url: str = "", title: str = "", tags: str = "") -> bool:
        """
        Returns True if this image should be rejected (wrong sport / wrong gender).
        Checks URL, filename, title, and tags strings.
        """
        combined = f"{url} {title} {tags}".lower()
        for bk in self._BAD_KEYWORDS:
            if bk in combined:
                print(f"[Filter] Rejected image — matched bad keyword '{bk}' in: {url[:80]}")
                return True
        return False

    def _fetch_thesportsdb_image(self, entity_name: str) -> str | None:
        """
        Fetches an official player or team image from TheSportsDB free API.
        TheSportsDB only covers association football (soccer) when filtered by sport.
        No API key needed for the free tier.
        Returns a local file path or None.
        """
        try:
            # Search players
            url = f"https://www.thesportsdb.com/api/v1/json/3/searchplayers.php"
            r = requests.get(url, params={"p": entity_name},
                             headers={"User-Agent": "FootyBitezBot/1.0"}, timeout=10)
            if r.status_code == 200:
                players = r.json().get("player", []) or []
                # Filter: only soccer/football (idSport=17 in TSDB) and men
                for p in players:
                    sport = (p.get("strSport") or "").lower()
                    gender = (p.get("strGender") or "Male").strip()
                    if sport not in ("soccer", "football") and sport != "":
                        continue
                    if gender.lower() not in ("male", "m", ""):
                        continue
                    thumb = p.get("strThumb") or p.get("strCutout")
                    if thumb and thumb not in self.used_urls:
                        fname = f"tsdb_player_{hash(entity_name)}.jpg"
                        fpath = os.path.join(self.download_dir, fname)
                        self._download_file(thumb, fpath)
                        if os.path.exists(fpath) and os.path.getsize(fpath) > 5000:
                            self.used_urls.add(thumb)
                            self._add_credit(f"Image from TheSportsDB (Player: {entity_name})")
                            self._write_image_meta(fpath, "TheSportsDB", entity_name)
                            print(f"[TheSportsDB] Got player image for '{entity_name}'")
                            return fpath

            # Search teams
            url2 = f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php"
            r2 = requests.get(url2, params={"t": entity_name},
                              headers={"User-Agent": "FootyBitezBot/1.0"}, timeout=10)
            if r2.status_code == 200:
                teams = r2.json().get("teams", []) or []
                for t in teams:
                    sport = (t.get("strSport") or "").lower()
                    if sport not in ("soccer", "football", ""):
                        continue
                    badge = t.get("strTeamBadge") or t.get("strTeamJersey")
                    banner = t.get("strTeamBanner")
                    img_url = banner or badge
                    if img_url and img_url not in self.used_urls:
                        fname = f"tsdb_team_{hash(entity_name)}.jpg"
                        fpath = os.path.join(self.download_dir, fname)
                        self._download_file(img_url, fpath)
                        if os.path.exists(fpath) and os.path.getsize(fpath) > 5000:
                            self.used_urls.add(img_url)
                            self._add_credit(f"Image from TheSportsDB (Team: {entity_name})")
                            self._write_image_meta(fpath, "TheSportsDB", entity_name)
                            print(f"[TheSportsDB] Got team image for '{entity_name}'")
                            return fpath
        except Exception as e:
            print(f"[TheSportsDB] Error for '{entity_name}': {e}")
        return None

    # ─────────────────────────────────────────────────────────
    # PUBLIC API — called by main.py (Shorts pipeline)
    # ─────────────────────────────────────────────────────────

    def _is_player_query(self, query: str) -> bool:
        players = {
            "klose", "messi", "ronaldo", "haaland", "mbappe", "bellingham", "vinicius", "yamal", "neymar",
            "pele", "maradona", "zidane", "cruyff", "ronaldinho", "henry", "beckham", "kane", "salah",
            "lewandowski", "modric", "kroos", "benzema", "suarez", "zlatan", "ibrahimovic", "hazard",
            "de bruyne", "saka", "foden", "palmer", "musiala", "wirtz", "griezmann", "martinez", "rashford"
        }
        query_lower = query.lower()
        return any(p in query_lower for p in players)

    def get_title_card_image(self, topic: str) -> str:
        """
        Fetches or generates a portrait (9:16) title card image for Shorts.
        4-tier fallback chain — NEVER raises, always returns a valid path.
        """
        print(f"Sourcing title card image for: {topic}")

        # 1. DuckDuckGo portrait search
        path = self._fetch_ddg_image(
            f"football {topic} stadium crowd action portrait",
            suffix=f"title_{hash(topic)}"
        )
        if path:
            return path

        # 2. Unsplash
        paths = self._fetch_unsplash_image(f"{topic} football portrait", count=1)
        if paths:
            return paths[0]

        is_player = self._is_player_query(topic)

        # 3. Pollinations.ai (no API key, no quota)
        poll_path = os.path.join(self.download_dir, f"poll_title_{hash(topic)}.jpg")
        
        poll_prompt = f"football {topic} stadium crowd action, portrait vertical, dramatic lighting, dark background, cinematic"
        if is_player:
            poll_prompt = (
                "football match atmosphere with stadium crowd cheering, team colors, banners, "
                "dramatic lighting, dark background, portrait vertical, no faces visible, cinematic, "
                "sports photography style"
            )

        if self._fetch_pollinations_image(poll_prompt, poll_path):
            return poll_path

        # 4. Gemini AI image generation (new SDK)
        if self.gemini_keys:
            ai_path = os.path.join(self.download_dir, f"ai_title_{hash(topic)}.jpg")
            
            gemini_prompt = f"football {topic} stadium crowd action, sports photography, dramatic"
            if is_player:
                gemini_prompt = (
                    "football match atmosphere with stadium crowd cheering, team colors, banners, "
                    "sports photography style, dramatic, no faces visible"
                )

            if self.generate_ai_image_for_shorts(gemini_prompt, ai_path):
                return ai_path


        # 5. PIL solid dark gradient card (ultimate fallback — never crash)
        return self._create_solid_card(topic)

    def get_profile_image(self, entity_query: str) -> str | None:
        """
        Fetches a portrait image of the primary entity (player/club).
        Priority chain: Wikipedia → TheSportsDB → Wikimedia → Unsplash → Pixabay → DDG
        Returns None if nothing found — caller handles the fallback.
        """
        print(f"Sourcing profile image for: {entity_query}")

        # 1. Wikipedia Page Summary (most accurate — exact match for players/clubs)
        path = self.get_wikipedia_entity_image(entity_query)
        if path:
            return path

        # 2. TheSportsDB (football-specific database, no wrong-sport risk)
        path = self._fetch_thesportsdb_image(entity_query)
        if path:
            return path

        # 3. Wikimedia Commons (filtered)
        path = self._fetch_wikimedia_image(f"{entity_query} footballer portrait")
        if path:
            return path

        # 4. Unsplash (filtered)
        paths = self._fetch_unsplash_image(f"{entity_query} soccer player portrait", count=1)
        if paths:
            return paths[0]

        # 5. Pixabay (filtered)
        paths = self._fetch_pixabay_image(f"{entity_query} football player", count=1)
        if paths:
            return paths[0]

        # 6. DDG fallback (filtered)
        return self._fetch_ddg_image(f"{entity_query} soccer portrait", suffix=f"profile_{hash(entity_query)}")

    def get_media(self, visual_keyword: str, count: int = 3) -> list:
        """
        Fetches a list of image paths for a given visual keyword.
        Used by Shorts pipeline for segment visuals.
        Priority: Wikipedia entity → TheSportsDB → Wikimedia → Unsplash → Pixabay → DDG
        All queries are filtered to men's association football only.
        """
        results = []
        safe_query = self._make_football_query(visual_keyword)

        # 1. If the keyword looks like a named entity, try Wikipedia + TheSportsDB first
        if self._is_player_query(visual_keyword) or len(visual_keyword.split()) <= 4:
            wiki_entity = self.get_wikipedia_entity_image(visual_keyword)
            if wiki_entity:
                results.append(wiki_entity)

            if len(results) < count:
                tsdb = self._fetch_thesportsdb_image(visual_keyword)
                if tsdb:
                    results.append(tsdb)

        # 2. Wikimedia Commons (filtered)
        if len(results) < count:
            wiki_paths = self._fetch_wikimedia_images(safe_query, count=count - len(results))
            results.extend(wiki_paths)

        # 3. Unsplash (filtered)
        if len(results) < count:
            unsplash_paths = self._fetch_unsplash_image(safe_query, count=count - len(results))
            results.extend(unsplash_paths)

        # 4. Pixabay (filtered)
        if len(results) < count:
            pix_paths = self._fetch_pixabay_image(safe_query, count=count - len(results))
            results.extend(pix_paths)

        # 5. DDG fallback (filtered)
        if not results:
            path = self._fetch_ddg_image(safe_query, suffix=f"seg_{hash(visual_keyword)}")
            if path:
                results.append(path)

        return results[:count]

    def get_thumbnail_image(self, query):
        """Fetches a high-contrast image for the thumbnail."""
        print(f"Sourcing thumbnail for: {query}")
        path = self._fetch_unsplash_image(f"{query} high contrast documentary", count=1)
        if path:
            return path[0]

        path = self._fetch_pixabay_image(f"{query} cinematic", count=1)
        if path:
            return path[0]

        return self._fetch_ddg_image(f"{query} soccer wallpaper 4k", "thumb")

    def get_media_for_script(self, image_queries, thumbnail_query=None):
        """
        Main pipeline for documentary image sourcing.
        Prioritizes Wikimedia -> Unsplash -> Pixabay.
        """
        assets = {}

        if thumbnail_query:
            assets['thumbnail'] = self.get_thumbnail_image(thumbnail_query)

        for i, query in enumerate(image_queries):
            print(f"Sourcing image {i+1}/{len(image_queries)}: {query}")

            path = self._fetch_wikimedia_image(query)
            if path:
                assets[f"image_{i}"] = path
                continue

            paths = self._fetch_unsplash_image(query, count=1)
            if paths:
                assets[f"image_{i}"] = paths[0]
                continue

            paths = self._fetch_pixabay_image(query, count=1)
            if paths:
                assets[f"image_{i}"] = paths[0]
                continue

            assets[f"image_{i}"] = self._fetch_ddg_image(f"{query} soccer", f"fallback_{i}")

        return assets

    def get_wikipedia_entity_image(self, entity_name: str) -> str | None:
        """
        Fetches the primary image from a Wikipedia article for a named entity.
        This guarantees accuracy — the image is the one Wikipedia uses for this exact person/club.
        Validates that the image is football-relevant before returning.
        """
        import requests
        try:
            url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + entity_name.replace(" ", "_")
            r = requests.get(url, headers={'User-Agent': 'FootyBitezBot/1.0 (contact: admin@footybitez.com)'}, timeout=10)
            if r.status_code != 200:
                return None
            
            data = r.json()
            image_url = (data.get("originalimage", {}).get("source") or
                         data.get("thumbnail", {}).get("source"))
            
            # Validate that the image is football-relevant
            if image_url:
                url_lower = image_url.lower()
                if any(kw in url_lower for kw in ["trump", "president", "politician", "award", "ceremony", "meeting"]):
                    # Non-football image - fall through to MediaWiki API for more options
                    logger.info(f"[Orchestrator] Wikipedia thumbnail contains non-football keywords - trying MediaWiki images list")
                    result = self._get_wikipedia_images_from_api(entity_name)
                    if result:
                        return result
                    return None
                
                fname = f"wiki_entity_{hash(image_url)}.jpg"
                fpath = os.path.join(self.download_dir, fname)
                self._download_file(image_url, fpath)
                if os.path.exists(fpath) and os.path.getsize(fpath) > 5000:
                    self._add_credit(f"Image from Wikipedia (Entity: {entity_name})")
                    self._write_image_meta(fpath, "Wikipedia Page Summary API", entity_name)
                    return fpath
            else:
                # No thumbnail - try MediaWiki API for all images on the page
                result = self._get_wikipedia_images_from_api(entity_name)
                if result:
                    return result
                    
        except Exception as e:
            print(f"Wikipedia entity image lookup error ({entity_name}): {e}")
            # Try MediaWiki API as fallback
            return self._get_wikipedia_images_from_api(entity_name)
        return None
    
    def _get_wikipedia_images_from_api(self, entity_name: str) -> str | None:
        """
        Fetches the first football-relevant image from Wikipedia's full images list via MediaWiki API.
        Filters for images containing entity name + football keywords in the filename.
        """
        try:
            api_url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "titles": entity_name,
                "prop": "images",
                "format": "json",
                "redirects": True,
            }
            r = requests.get(api_url, params=params, headers={'User-Agent': 'FootyBitezBot/1.0'}, timeout=10)
            if r.status_code != 200:
                return None
            
            data = r.json()
            pages = data.get("query", {}).get("pages", {})
            if not pages:
                return None
            
            page_id = next(iter(pages))
            images = pages[page_id].get("images", [])
            
            football_keywords = ["playing", "football", "soccer", "goal", "match", "training", "action", "ronaldo", "goalkeeper", "ball", "kit", "stadium"]
            entity_lower = entity_name.lower().replace(" ", "_")
            
            for img in images:
                img_title = img.get("title", "")
                img_lower = img_title.lower()
                
                # Prefer images with entity name and football keywords
                has_entity = entity_lower in img_lower or entity_name.split()[0].lower() in img_lower
                has_football = any(kw in img_lower for kw in football_keywords)
                
                if has_entity or has_football:
                    # Get imageinfo for the image URL
                    info_params = {
                        "action": "query",
                        "titles": img_title,
                        "prop": "imageinfo",
                        "iiprop": "url",
                        "format": "json",
                    }
                    info_r = requests.get(api_url, params=info_params, headers={'User-Agent': 'FootyBitezBot/1.0'}, timeout=10)
                    if info_r.status_code == 200:
                        info_data = info_r.json()
                        info_pages = info_data.get("query", {}).get("pages", {})
                        for info_page in info_pages.values():
                            imageinfo = info_page.get("imageinfo", [])
                            if imageinfo:
                                img_url = imageinfo[0].get("url", "")
                                if img_url:
                                    fname = f"wiki_api_{hash(img_url)}.jpg"
                                    fpath = os.path.join(self.download_dir, fname)
                                    self._download_file(img_url, fpath)
                                    if os.path.exists(fpath) and os.path.getsize(fpath) > 5000:
                                        self._add_credit(f"Image from Wikipedia (Entity: {entity_name})")
                                        self._write_image_meta(fpath, "Wikipedia API Images", entity_name)
                                        return fpath
            return None
        except Exception as e:
            print(f"Wikipedia API images fallback error ({entity_name}): {e}")
            return None

    def fetch_pexels_video(self, query: str, output_path: str) -> bool:
        """
        Fetches a CC0 stock football video from Pexels.
        Pexels API is free — register at pexels.com/api for a key.
        """
        import requests
        
        PEXELS_API_KEY = self.pexels_api_key
        if not PEXELS_API_KEY:
            print("[Pexels] No API Key set.")
            return False
        
        try:
            r = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": query, "per_page": 5, "orientation": "landscape"},
                timeout=15
            )
            
            if r.status_code != 200:
                print(f"[Pexels] API error {r.status_code}: {r.text}")
                return False
            
            videos = r.json().get("videos", [])
            if not videos:
                print(f"[Pexels] No videos found for query '{query}'")
                return False
            
            for video in videos:
                for vfile in video.get("video_files", []):
                    if vfile.get("width", 0) >= 1280 and vfile.get("file_type") == "video/mp4":
                        video_url = vfile["link"]
                        vid_r = requests.get(video_url, timeout=60, stream=True)
                        if vid_r.status_code == 200:
                            os.makedirs(os.path.dirname(output_path), exist_ok=True)
                            with open(output_path, 'wb') as f:
                                for chunk in vid_r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            print(f"[Pexels] Successfully downloaded video for '{query}' to {output_path}")
                            return True
        except Exception as e:
            print(f"[Pexels] Exception during video fetch: {e}")
        return False

    # ─────────────────────────────────────────────────────────
    # AI IMAGE GENERATION
    # ─────────────────────────────────────────────────────────

    def generate_ai_image_for_shorts(self, prompt: str, output_path: str) -> bool:
        """
        Generates a 9:16 portrait AI image for Shorts using Gemini (new SDK, free tier).
        Model: gemini-2.5-flash-image
        Returns True on success, False on any failure.
        """
        if not self.gemini_keys:
            return False

        try:
            from google import genai
            from google.genai import types
            from PIL import Image as PILImage
        except ImportError:
            print("[AI Image] google-genai or Pillow not installed.")
            return False

        full_prompt = (
            f"portrait orientation 9:16, {prompt}, "
            f"dramatic lighting, dark background, sports photography style, "
            f"no text overlays, cinematic quality"
        )

        for i, key in enumerate(self.gemini_keys):
            try:
                client = genai.Client(api_key=key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"]
                    )
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                        img = PILImage.open(io.BytesIO(part.inline_data.data)).convert("RGB")
                        img = img.resize((1080, 1920), PILImage.LANCZOS)
                        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
                        img.save(output_path, "JPEG", quality=95)
                        print(f"[AI Image] Generated shorts image with key #{i+1}")
                        return True
            except Exception as e:
                print(f"[AI Image] Key #{i+1} failed: {e}")
                try:
                    from footybitez.media.football_visual_generator import handle_429_sleep
                    handle_429_sleep(str(e))
                except Exception as sleep_err:
                    print(f"[AI Image] Error during sleep: {sleep_err}")

        return False

    # ─────────────────────────────────────────────────────────
    # PRIVATE FETCH HELPERS
    # ─────────────────────────────────────────────────────────

    def _fetch_wikimedia_image(self, query):
        """Fetches a single image from Wikimedia Commons API (used for profile images)."""
        results = self._fetch_wikimedia_images(query, count=1)
        return results[0] if results else None

    def _fetch_wikimedia_images(self, query, count=3):
        """Fetches up to `count` images from Wikimedia Commons with football-only filter."""
        results = []

        # Apply football filter to the incoming query
        safe_q = self._make_football_query(query)
        # Clean: remove special chars, truncate
        clean_query = re.sub(r"[^\w\s-]", "", safe_q)
        clean_query = re.sub(r"\s+", " ", clean_query).strip()[:60]

        queries_to_try = [
            clean_query,
            f"{clean_query} soccer"[:60],
            f"{clean_query} football"[:60],
            ("stadium football soccer men" if "stadium" in clean_query.lower()
             else f"{clean_query.split()[0] if clean_query.split() else ''} football soccer")[:60],
]

        for attempt_query in queries_to_try:
            if len(results) >= count:
                break
            try:
                search_url = "https://commons.wikimedia.org/w/api.php"
                params = {
                    "action": "query",
                    "format": "json",
                    "generator": "search",
                    "gsrnamespace": 6,
                    "gsrsearch": f"{attempt_query} filetype:bitmap",
                    "gsrlimit": 15,
                    "prop": "imageinfo",
                    "iiprop": "url|size|mime|extmetadata",
                }
                headers = {'User-Agent': 'FootyBitezBot/1.0'}
                r = requests.get(search_url, params=params, headers=headers, timeout=10)
                if r.status_code != 200 or not r.text.strip():
                    continue
                try:
                    data = r.json()
                except json.JSONDecodeError:
                    continue

                pages = data.get("query", {}).get("pages", {})
                if not pages:
                    continue

                for page_id in pages:
                    if len(results) >= count:
                        break
                    page = pages[page_id]
                    imageinfo = page.get("imageinfo", [])
                    if not imageinfo:
                        continue

                    url = imageinfo[0].get("url", "")
                    if url in self.used_urls:
                        continue
                    mime = imageinfo[0].get("mime", "")

                    # Skip SVGs, audio, video
                    if not mime.startswith("image/") or "svg" in mime.lower():
                        continue

                    meta = imageinfo[0].get("extmetadata", {})
                    categories = meta.get("Categories", {}).get("value", "")
                    license_name = meta.get("LicenseShortName", {}).get("value", "CC BY-SA")
                    artist = meta.get("Artist", {}).get("value", "Unknown")
                    artist = re.sub('<[^<]+?>', '', artist)

                    # ── Football-only filter ──────────────────────────────
                    img_title = page.get("title", "")
                    if self._is_bad_image(url=url, title=img_title, tags=categories):
                        continue

                    fname = f"wiki_{hash(url)}.jpg"
                    fpath = os.path.join(self.download_dir, fname)
                    self._download_file(url, fpath)

                    if os.path.exists(fpath) and os.path.getsize(fpath) > 5000:
                        self.used_urls.add(url)
                        self._add_credit(f"Image from Wikimedia Commons: {artist} ({license_name})")
                        self._write_image_meta(fpath, "Wikimedia Commons", artist)
                        results.append(fpath)

            except Exception as e:
                print(f"Wikimedia multi-fetch error (query='{attempt_query}'): {e}")
                continue

        return results

    def _fetch_unsplash_image(self, query, count=1):
        if not self.unsplash_api_key:
            return []
        paths = []
        try:
            safe_query = self._make_football_query(query)
            url = "https://api.unsplash.com/search/photos"
            params = {
                "query": safe_query,
                "per_page": count * 4,  # Fetch more to filter bad ones
                "client_id": self.unsplash_api_key,
                "content_filter": "high",
            }
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for photo in data.get('results', []):
                    if len(paths) >= count:
                        break
                    src = photo['urls']['regular']
                    if src in self.used_urls:
                        continue
                    # Check photo tags for bad-sport content
                    photo_tags = " ".join(t.get("title", "") for t in photo.get("tags", []))
                    alt = photo.get("alt_description") or ""
                    if self._is_bad_image(url=src, title=alt, tags=photo_tags):
                        continue
                    user = photo['user']['name']
                    fpath = os.path.join(self.download_dir, f"unsplash_{photo['id']}.jpg")
                    self._download_file(src, fpath)
                    if os.path.exists(fpath):
                        self.used_urls.add(src)
                        paths.append(fpath)
                        self._add_credit(f"Photo by {user} on Unsplash")
                        self._write_image_meta(fpath, "Unsplash", user)
        except Exception as e:
            print(f"Unsplash error: {e}")
        return paths

    def _fetch_pixabay_image(self, query, count=1):
        if not self.pixabay_api_key:
            return []
        paths = []
        try:
            safe_query = self._make_football_query(query)
            url = "https://pixabay.com/api/"
            params = {
                "key": self.pixabay_api_key,
                "q": safe_query,
                "image_type": "photo",
                "category": "sports",  # Restrict to sports category
                "per_page": count * 4,  # Fetch more to filter
            }
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for hit in data.get('hits', []):
                    if len(paths) >= count:
                        break
                    src = hit['largeImageURL']
                    if src in self.used_urls:
                        continue
                    # Check pixabay tags field
                    tags = hit.get("tags", "")
                    if self._is_bad_image(url=src, title=tags, tags=tags):
                        continue
                    user = hit['user']
                    fpath = os.path.join(self.download_dir, f"pixabay_{hit['id']}.jpg")
                    self._download_file(src, fpath)
                    if os.path.exists(fpath):
                        self.used_urls.add(src)
                        paths.append(fpath)
                        self._add_credit(f"Image by {user} from Pixabay")
                        self._write_image_meta(fpath, "Pixabay", user)
        except Exception as e:
            print(f"Pixabay error: {e}")
        return paths

    def _fetch_ddg_image(self, query, suffix):
        """Fetches an image using DuckDuckGo as final free fallback with football-only filter."""
        if DDGS is None:
            print("[DDG] Neither 'ddgs' nor 'duckduckgo_search' is installed. Skipping.")
            return None
        try:
            safe_query = self._make_football_query(query)
            # Append negative terms in the query string (DDG supports them)
            ddg_query = f"{safe_query} {self._FOOTBALL_NEG_SUFFIX}"
            with DDGS() as ddgs:
                results = list(ddgs.images(ddg_query, max_results=25))
                if results:
                    for result in results:
                        image_url = result.get('image', '')
                        title = result.get('title', '')
                        if not image_url or image_url in self.used_urls:
                            continue
                        # Filter: reject bad-sport URLs and titles
                        if self._is_bad_image(url=image_url, title=title):
                            continue
                        ext = image_url.split('.')[-1].split('?')[0][:3]
                        filename = f"ddg_{suffix}_{hash(query)}.{ext}"
                        if len(ext) > 4 or not ext.isalpha():
                            filename = f"ddg_{suffix}_{hash(query)}.jpg"
                        filepath = os.path.join(self.download_dir, filename)
                        self._download_file(image_url, filepath)
                        if os.path.exists(filepath):
                            self.used_urls.add(image_url)
                            return filepath
        except Exception as e:
            print(f"DDG Fallback error: {e}")
        return None

    def _fetch_pollinations_image(self, prompt: str, output_path: str) -> bool:
        """
        Fetches an AI image from Pollinations.ai — no API key, no quota.
        Returns True on success, False on failure.
        """
        try:
            import urllib.parse
            encoded = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true"
            headers = {'User-Agent': 'FootyBitezBot/1.0'}
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 200 and 'image' in r.headers.get('Content-Type', ''):
                os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(r.content)
                if os.path.getsize(output_path) > 5000:
                    print(f"[Pollinations] Generated image: {output_path}")
                    return True
                os.remove(output_path)
        except Exception as e:
            print(f"[Pollinations] Error: {e}")
        return False

    def _create_solid_card(self, text: str) -> str:
        """
        Creates a solid dark gradient PIL image (1080x1920) as an ultimate fallback.
        Adds centered text. Never crashes.
        """
        try:
            from PIL import Image as PILImage, ImageDraw, ImageFont
            import numpy as np

            w, h = 1080, 1920
            # Dark gradient: #0a0a0a top to #1a1a2e bottom
            img = PILImage.new("RGB", (w, h))
            draw = ImageDraw.Draw(img)
            for y in range(h):
                r = int(10 + (16 * y / h))
                g = int(10 + (16 * y / h))
                b = int(10 + (36 * y / h))
                draw.line([(0, y), (w, y)], fill=(r, g, b))

            # Try to load font
            font = None
            font_candidates = [
                "remotion-video/public/assets/fonts/BarlowCondensed-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "C:\\Windows\\Fonts\\impact.ttf",
            ]
            for fp in font_candidates:
                if os.path.exists(fp):
                    try:
                        font = ImageFont.truetype(fp, 80)
                        break
                    except Exception:
                        continue
            if not font:
                font = ImageFont.load_default()

            # Amber accent line at top
            draw.rectangle([0, 0, w, 8], fill=(245, 166, 35))

            # Centered text
            label = text.upper()[:40]
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            tx = (w - tw) // 2
            ty = h // 2 - 60
            for ox in range(-4, 5):
                for oy in range(-4, 5):
                    draw.text((tx + ox, ty + oy), label, font=font, fill=(0, 0, 0))
            draw.text((tx, ty), label, font=font, fill=(245, 166, 35))

            fname = f"card_{hash(text)}.jpg"
            fpath = os.path.join(self.download_dir, fname)
            os.makedirs(self.download_dir, exist_ok=True)
            img.save(fpath, "JPEG", quality=90)
            return fpath

        except Exception as e:
            print(f"[SolidCard] PIL card creation failed: {e}")
            # Absolute last resort — return a blank file path that VideoCreator handles
            return os.path.join(self.download_dir, "placeholder.jpg")


    # ─────────────────────────────────────────────────────────
    # AI IMAGE PROMPT BUILDER
    # ─────────────────────────────────────────────────────────

    def _build_ai_image_prompt(self, image_cue: str, is_player_topic: bool = False) -> str:
        """
        Builds an AI image generation prompt from an image cue.

        IMPORTANT: AI image models cannot reliably generate recognisable likenesses of
        real named people. Attempting to generate "Erling Haaland" produces a random person.

        For player topics: generate atmospheric context (stadium, team colors, crowd)
        and let the real image search chain (Wikimedia, Unsplash, Pixabay, DDG) handle
        actual player photos.

        For generic topics: return a photorealistic sports photography prompt.
        """
        if is_player_topic:
            return (
                f"football match atmosphere related to: {image_cue}, "
                "stadium crowd cheering, team colors and scarves, "
                "cinematic sports photography, dramatic stadium lighting, "
                "no faces visible, aerial view or wide shot, professional photo style"
            )
        else:
            return f"photorealistic, cinematic, {image_cue}, dramatic sports photography, high quality"


if __name__ == "__main__":
    sourcer = MediaSourcer()
    # Test
    # path = sourcer.get_title_card_image("Lionel Messi")
    # print(path)

