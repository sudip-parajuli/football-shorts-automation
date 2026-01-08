import os
import requests
import random
from dotenv import load_dotenv

class MediaSourcer:
    def __init__(self, download_dir="footybitez/media/downloads"):
        load_dotenv()
        self.api_key = os.getenv("PEXELS_API_KEY")
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
        self.headers = {'Authorization': self.api_key} if self.api_key else {}

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

    def _download_file(self, url, filepath):
        """Downloads a file using requests with headers."""
        if os.path.exists(filepath): return
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0'}
            with requests.get(url, headers=headers, stream=True, timeout=15) as r:
                r.raise_for_status()
                if 'text/html' in r.headers.get('Content-Type', '').lower(): return
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            if os.path.exists(filepath) and os.path.getsize(filepath) < 100: os.remove(filepath)
        except Exception as e:
            print(f"Download failed {url}: {e}")

    def get_title_card_image(self, query):
        """Fetches a high-impact cinematic image."""
        # Try DDG first for specific match
        filepath = self._fetch_ddg_image(f"{query} football cinematic 4k wallpaper", "title")
        if filepath: return filepath
        # Fallback Pexels
        return self._fetch_pexels_image(f"{query} stadium", "portrait")

    def get_profile_image(self, query):
        """Fetches a specific person's portrait."""
        # 1. DDG (Best for specific players/managers)
        # Use simple, direct query with strict terms
        full_query = f"{query} football player face portrait real life -cricket -cartoon -drawing"
        print(f"DEBUG: Searching DDG for Profile: '{full_query}'")
        filepath = self._fetch_ddg_image(full_query, "profile")
        if filepath: return filepath
        
        # 2. Pexels (Fallback)
        print(f"DEBUG: Fallback to Pexels for Profile: '{query}'")
        return self._fetch_pexels_image(f"{query} face", "square")

    def get_media(self, query, count=5, orientation="portrait"):
        """
        Fetches media with strict prioritization:
        1. Specific Image (DDG) - HIGHEST PRIORITY (User Request).
        2. Specific Video (Pexels) - Dynamic background if available.
        3. Generic Video (Pexels) - Fallback.
        """
        paths = []
        
        # Cleanup query
        clean_query = query.replace(" football", "").replace(" soccer", "").strip()
        
        print(f"Sourcing media for: {clean_query} (Need {count})")
        
        # 1. Specific Images (DDG) - Primary Source
        # We try to fill MOST slots with specific images.
        needed_images = count
        if needed_images > 0:
            print(f"Fetching specific images from DDG (Target: {needed_images})...")
            # Get extra matches to filter
            # Add strict negative keywords to avoid other sports
            strict_query = f"{clean_query} football player real life -cricket -basketball -baseball -drawing -cartoon"
            imgs = self._fetch_ddg_images(strict_query, count=needed_images + 3)
            paths.extend(imgs)
            
        # 2. Specific Video (Pexels) - Start mixing in if we have space or valid specific videos
        # Just grab 1 or 2 to mix in if possible, but keep images as main.
        if len(paths) < count:
            print(f"Fetching specific videos from Pexels (Fallback)...")
            vids = self._fetch_pexels_videos(f"{clean_query} football match", count=2, orientation=orientation)
            paths.extend(vids)

        # 3. Generic Video (Final Fallback)
        if len(paths) < count:
            needed = count - len(paths)
            print(f"Fetching generic fallback videos (Need {needed})...")
            # Fallback should still try to be relevant to the query + football
            fallback_query = f"{clean_query} football stadium atmosphere"
            fallback_vids = self._fetch_pexels_videos(fallback_query, count=needed, orientation=orientation)
            if not fallback_vids:
                 # Absolute fallback
                 fallback_vids = self._fetch_pexels_videos("football cinematic", count=needed, orientation=orientation)
            paths.extend(fallback_vids)
            
        # Shuffle slightly so we don't have all images then all videos
        # But ensure we return enough
        return paths[:count]

    def _fetch_pexels_videos(self, query, count, orientation):
        paths = []
        if not self.api_key: return []
        try:
            url = "https://api.pexels.com/videos/search"
            params = {"query": query, "per_page": count, "orientation": orientation}
            res = requests.get(url, headers=self.headers, params=params)
            if res.status_code == 200:
                for vid in res.json().get('videos', []):
                    # Pick best quality MP4
                    best = None
                    for vf in vid['video_files']:
                         if vf['file_type'] == 'video/mp4' and vf['quality'] == 'hd':
                             best = vf
                             break
                    if not best and vid['video_files']: best = vid['video_files'][0]
                    
                    if best:
                        fname = f"pexels_vid_{vid['id']}.mp4"
                        fpath = os.path.join(self.download_dir, fname)
                        self._download_file(best['link'], fpath)
                        if os.path.exists(fpath): paths.append(fpath)
        except Exception as e:
            print(f"Pexels video error: {e}")
        return paths

    def _fetch_pexels_image(self, query, orientation):
        if not self.api_key: return None
        try:
            url = "https://api.pexels.com/v1/search"
            params = {"query": query, "per_page": 1, "orientation": orientation}
            res = requests.get(url, headers=self.headers, params=params)
            if res.status_code == 200:
                photos = res.json().get('photos', [])
                if photos:
                    src = photos[0]['src']['large']
                    fpath = os.path.join(self.download_dir, f"pexels_{photos[0]['id']}.jpg")
                    self._download_file(src, fpath)
                    return fpath
        except Exception as e:
            print(f"Pexels image error: {e}")
        return None

    def _fetch_ddg_image(self, query, suffix):
        """Fetches single best image from DDG."""
        try:
            from duckduckgo_search import DDGS
            import time
            time.sleep(1)
            with DDGS() as ddgs:
                results = list(ddgs.images(query, max_results=2))
                if results:
                    url = results[0]['image']
                    fpath = os.path.join(self.download_dir, f"ddg_{suffix}_{hash(url)}.jpg")
                    self._download_file(url, fpath)
                    if os.path.exists(fpath): return fpath
        except Exception as e:
            print(f"DDG error: {e}")
        return None

    def _fetch_ddg_images(self, query, count):
        """Fetches multiple images from DDG."""
        paths = []
        try:
            from duckduckgo_search import DDGS
            import time
            time.sleep(1)
            with DDGS() as ddgs:
                results = list(ddgs.images(query, max_results=count))
                for res in results:
                    url = res['image']
                    fpath = os.path.join(self.download_dir, f"ddg_{hash(url)}.jpg")
                    self._download_file(url, fpath)
                    if os.path.exists(fpath): paths.append(fpath)
        except Exception as e:
            print(f"DDG multiple error: {e}")
        return paths
