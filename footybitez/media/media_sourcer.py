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
        self.neg_keywords = "-nfl -american -rugby -superbowl -touchdown -helmet"

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
        # STRICT NEGATIVE KEYWORDS for all searches to avoid NFL/Rugby
        filepath = self._fetch_ddg_image(f"{query} football cinematic 4k wallpaper {self.neg_keywords}", "title")
        if filepath: return filepath
        # Fallback Pexels
        return self._fetch_pexels_image(f"{query} stadium", "portrait")

    def get_profile_image(self, query):
        """Fetches a specific person's portrait."""
        # 1. Determine if Club or Player
        club_keywords = ["fc", "united", "city", "real", "inter", "ac", "bayern", "dortmund", 
                         "juventus", "liverpool", "arsenal", "chelsea", "tottenham", "barcelona", 
                         "madrid", "psg", "ajax", "benfica", "porto", "club", "team"]
        
        is_club = any(k in query.lower() for k in club_keywords)
        
        # 2. Try Wikimedia Commons (High Priority for verifiable profiles)
        print(f"DEBUG: Searching Wikimedia for Profile: '{query}'")
        wiki_query = f"{query} logo" if is_club else f"{query}"
        wiki_path = self._fetch_wikimedia_image(wiki_query)
        if wiki_path: return wiki_path

        # 3. DDG (Best for specific players/managers/logos)
        if is_club:
            full_query = f"{query} football club logo badge stadium wallpaper {self.neg_keywords}"
            print(f"DEBUG: Searching DDG for CLUB Profile: '{full_query}'")
            filepath = self._fetch_ddg_image(full_query, "profile")
        else:
            full_query = f"{query} football player face portrait real life {self.neg_keywords} -cartoon -drawing -game"
            print(f"DEBUG: Searching DDG for PLAYER Profile: '{full_query}'")
            filepath = self._fetch_ddg_image(full_query, "profile")

        if filepath: return filepath
        
        # 4. Pexels (Fallback)
        print(f"DEBUG: Fallback to Pexels for Profile: '{query}'")
        return self._fetch_pexels_image(f"{query} face", "square")

    def _fetch_wikimedia_image(self, query):
        """Fetches image from Wikimedia Commons API."""
        try:
            # Search for files
            search_url = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrnamespace": 6, # File namespace
                "gsrsearch": f"{query} filetype:bitmap", # Prefer bitmaps (jpg/png) over huge TIFFs/SVGs for simple usage
                "gsrlimit": 3,
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
            }
            
            headers = {'User-Agent': 'FootyBitezBot/1.0 (sudip@example.com)'} # Good practice
            import time
            time.sleep(1)
            r = requests.get(search_url, params=params, headers=headers, timeout=10)
            data = r.json()
            
            pages = data.get("query", {}).get("pages", {})
            if not pages: return None
            
            # Select best candidate
            best_url = None
            for page_id in pages:
                page = pages[page_id]
                imageinfo = page.get("imageinfo", [])[0]
                url = imageinfo.get("url")
                mime = imageinfo.get("mime", "")
                
                # Filter useful types
                if "image/jpeg" in mime or "image/png" in mime:
                    best_url = url
                    break
            
            if best_url:
                fname = f"wiki_{hash(best_url)}.jpg"
                fpath = os.path.join(self.download_dir, fname)
                self._download_file(best_url, fpath)
                if os.path.exists(fpath): return fpath
                
        except Exception as e:
            print(f"Wikimedia error: {e}")
        return None

    def get_media(self, query, count=5, orientation="portrait"):
        """
        Fetches media with strict prioritization:
        1. Specific Image (Wikimedia) - HIGHEST PRIORITY (Accuracy).
        2. Specific Image (DDG) - High Priority (Variety).
        3. Specific Video (Pexels) - Dynamic background.
        4. Generic Video (Pexels) - Fallback.
        """
        paths = []
        
        # Cleanup query
        clean_query = query.replace(" football", "").replace(" soccer", "").strip()
        
        print(f"Sourcing media for: {clean_query} (Need {count})")
        
        needed = count
        
        # 1. Wikimedia (Most Accurate)
        if needed > 0:
            print(f"Fetching specific images from Wikimedia (Target: {needed})...")
            # Try to get half from Wiki if we need many, or all if few?
            # User wants accurate images. Let's try to get as many as possible from Wiki first.
            wiki_imgs = self._fetch_wikimedia_images(clean_query, count=needed)
            paths.extend(wiki_imgs)
            needed -= len(wiki_imgs)
            
        # 2. DDG (Supplement)
        if needed > 0:
            print(f"Fetching specific images from DDG (Target: {needed})...")
            strict_query = f"{clean_query} football match action real life {self.neg_keywords} -drawing -cartoon"
            # Request a few extra in case of duplicates/failures
            ddg_imgs = self._fetch_ddg_images(strict_query, count=needed + 2)
            paths.extend(ddg_imgs[:needed])
            
        # Check count again
        current_count = len(paths)
        if current_count < count:
            # 3. Pexels Videos (Dynamic Fallback)
            needed = count - current_count
            print(f"Fetching specific videos from Pexels (Fallback, Need {needed})...")
            vids = self._fetch_pexels_videos(f"{clean_query} football match", count=needed + 1, orientation=orientation)
            paths.extend(vids[:needed])

        # 4. Generic Video (Final Fallback)
        current_count = len(paths)
        if current_count < count:
            needed = count - current_count
            print(f"Fetching generic fallback videos (Need {needed})...")
            fallback_query = f"{clean_query} football stadium atmosphere" 
            fallback_vids = self._fetch_pexels_videos(fallback_query, count=needed, orientation=orientation)
            if not fallback_vids:
                 fallback_vids = self._fetch_pexels_videos("football cinematic", count=needed, orientation=orientation)
            paths.extend(fallback_vids)
            
        return paths[:count]

    def _fetch_wikimedia_images(self, query, count):
        """Fetches multiple images from Wikimedia Commons."""
        paths = []
        try:
            search_url = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrnamespace": 6, 
                "gsrsearch": f"{query} filetype:bitmap",
                "gsrlimit": count + 2, # Request extra
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
            }
            
            headers = {'User-Agent': 'FootyBitezBot/1.0 (sudip@example.com)'}
            r = requests.get(search_url, params=params, headers=headers, timeout=10)
            data = r.json()
            
            pages = data.get("query", {}).get("pages", {})
            if not pages: return []
            
            # Collect URLs
            urls = []
            for page_id in pages:
                page = pages[page_id]
                imageinfo = page.get("imageinfo", [])
                if not imageinfo: continue
                
                info = imageinfo[0]
                url = info.get("url")
                mime = info.get("mime", "")
                
                if "image/jpeg" in mime or "image/png" in mime:
                    urls.append(url)
                    
            # Download
            import time
            for url in urls[:count]:
                time.sleep(1) # Be polite to Wikimedia API (avoid 429)
                fname = f"wiki_bg_{hash(url)}.jpg"
                fpath = os.path.join(self.download_dir, fname)
                self._download_file(url, fpath)
                if os.path.exists(fpath):
                    paths.append(fpath)
                    
        except Exception as e:
            print(f"Wikimedia multiple error: {e}")
        return paths

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
