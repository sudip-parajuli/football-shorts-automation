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
        self.neg_keywords = "-nfl -american -rugby -superbowl -touchdown -helmet -cfl -afl -handball"

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
        Returns None if nothing found — caller handles the fallback.
        """
        print(f"Sourcing profile image for: {entity_query}")

        # 1. Wikimedia (best quality, free, licensed)
        path = self._fetch_wikimedia_image(f"{entity_query} footballer portrait")
        if path:
            return path

        # 2. Unsplash
        paths = self._fetch_unsplash_image(f"{entity_query} soccer player portrait", count=1)
        if paths:
            return paths[0]

        # 3. Pixabay
        paths = self._fetch_pixabay_image(f"{entity_query} football player", count=1)
        if paths:
            return paths[0]

        # 4. DDG fallback
        return self._fetch_ddg_image(f"{entity_query} soccer portrait high quality", suffix=f"profile_{hash(entity_query)}")

    def get_media(self, visual_keyword: str, count: int = 3) -> list:
        """
        Fetches a list of image paths for a given visual keyword.
        Used by Shorts pipeline for segment visuals.
        Returns an interleaved list of Wikimedia and Unsplash images.
        """
        wiki_paths = self._fetch_wikimedia_images(visual_keyword, count=count)
        
        unsplash_count = max(1, count - (len(wiki_paths) // 2))
        portrait_query = f"{visual_keyword} football soccer"
        unsplash_paths = self._fetch_unsplash_image(portrait_query, count=unsplash_count)

        # Interleave
        results = []
        for i in range(max(len(wiki_paths), len(unsplash_paths))):
            if i < len(wiki_paths):
                results.append(wiki_paths[i])
            if i < len(unsplash_paths):
                results.append(unsplash_paths[i])

        # Pixabay fallback if still low
        if len(results) < count:
            results.extend(self._fetch_pixabay_image(visual_keyword, count=count - len(results)))

        # DDG fallback
        if not results:
            path = self._fetch_ddg_image(f"{visual_keyword} soccer player", suffix=f"seg_{hash(visual_keyword)}")
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

        return False

    # ─────────────────────────────────────────────────────────
    # PRIVATE FETCH HELPERS
    # ─────────────────────────────────────────────────────────

    def _fetch_wikimedia_image(self, query):
        """Fetches a single image from Wikimedia Commons API (used for profile images)."""
        results = self._fetch_wikimedia_images(query, count=1)
        return results[0] if results else None

    def _fetch_wikimedia_images(self, query, count=3):
        """Fetches up to `count` images from Wikimedia Commons. Retries with broader query on failure."""
        results = []
        
        # Clean query: remove special chars and too many words
        clean_query = query.replace("*", "").strip()
        
        queries_to_try = [
            clean_query,
            f"{clean_query} soccer",
            f"{clean_query} football",
            # If the specific subject fails, try to at least get a stadium or trophy if applicable
            "stadium football" if "stadium" in clean_query.lower() else f"{clean_query.split()[0]} football",
        ]

        seen_urls = set()
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
                    "gsrlimit": 10, # Fetch more to find high quality
                    "prop": "imageinfo",
                    "iiprop": "url|size|mime|extmetadata",
                }
                headers = {'User-Agent': 'FootyBitezBot/1.0'}
                r = requests.get(search_url, params=params, headers=headers, timeout=10)
                data = r.json()

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
                    mime = imageinfo[0].get("mime", "")

                    # Skip SVGs, audio, video
                    if not mime.startswith("image/") or "svg" in mime.lower():
                        continue

                    meta = imageinfo[0].get("extmetadata", {})
                    license_name = meta.get("LicenseShortName", {}).get("value", "CC BY-SA")
                    artist = meta.get("Artist", {}).get("value", "Unknown")
                    artist = re.sub('<[^<]+?>', '', artist)

                    fname = f"wiki_{hash(url)}.jpg"
                    fpath = os.path.join(self.download_dir, fname)
                    self._download_file(url, fpath)

                    if os.path.exists(fpath) and os.path.getsize(fpath) > 5000:
                        self._add_credit(f"Image from Wikimedia Commons: {artist} ({license_name})")
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
            url = "https://api.unsplash.com/search/photos"
            params = {"query": query, "per_page": count, "client_id": self.unsplash_api_key}
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for photo in data.get('results', []):
                    src = photo['urls']['regular']
                    user = photo['user']['name']
                    fpath = os.path.join(self.download_dir, f"unsplash_{photo['id']}.jpg")
                    self._download_file(src, fpath)
                    if os.path.exists(fpath):
                        paths.append(fpath)
                        self._add_credit(f"Photo by {user} on Unsplash")
        except Exception as e:
            print(f"Unsplash error: {e}")
        return paths

    def _fetch_pixabay_image(self, query, count=1):
        if not self.pixabay_api_key:
            return []
        paths = []
        try:
            url = "https://pixabay.com/api/"
            params = {"key": self.pixabay_api_key, "q": query, "image_type": "photo", "per_page": count}
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for hit in data.get('hits', []):
                    src = hit['largeImageURL']
                    user = hit['user']
                    fpath = os.path.join(self.download_dir, f"pixabay_{hit['id']}.jpg")
                    self._download_file(src, fpath)
                    if os.path.exists(fpath):
                        paths.append(fpath)
                        self._add_credit(f"Image by {user} from Pixabay")
        except Exception as e:
            print(f"Pixabay error: {e}")
        return paths

    def _fetch_ddg_image(self, query, suffix):
        """Fetches an image using DuckDuckGo as final free fallback."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.images(query, max_results=1))
                if results:
                    image_url = results[0].get('image')
                    if image_url:
                        ext = image_url.split('.')[-1].split('?')[0][:3]
                        filename = f"ddg_{suffix}_{hash(query)}.{ext}"
                        if len(ext) > 4 or not ext.isalpha():
                            filename = f"ddg_{suffix}_{hash(query)}.jpg"
                        filepath = os.path.join(self.download_dir, filename)
                        self._download_file(image_url, filepath)
                        if os.path.exists(filepath):
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

