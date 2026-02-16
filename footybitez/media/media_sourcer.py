import os
import requests
import random
import re
from dotenv import load_dotenv

class MediaSourcer:
    def __init__(self, download_dir="footybitez/media/downloads"):
        load_dotenv()
        self.api_key = os.getenv("PEXELS_API_KEY")
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
        self.headers = {'Authorization': self.api_key} if self.api_key else {}
        self.neg_keywords = "-nfl -american -rugby -superbowl -touchdown -helmet -cfl -afl -handball"

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
        filepath = self._fetch_ddg_image(f"{query} football cinematic 4k wallpaper {self.neg_keywords}", "title")
        if filepath: return filepath
        # Fallback Pexels
        return self._fetch_pexels_image(f"{query} stadium", "portrait")

    def get_profile_image(self, query):
        """Fetches a specific person's portrait."""
        club_keywords = ["fc", "united", "city", "real", "inter", "ac", "bayern", "dortmund", 
                         "juventus", "liverpool", "arsenal", "chelsea", "tottenham", "barcelona", 
                         "madrid", "psg", "ajax", "benfica", "porto", "club", "team"]
        
        is_club = any(k in query.lower() for k in club_keywords)
        
        # 1. Wikimedia (High Priority)
        print(f"DEBUG: Searching Wikimedia for Profile: '{query}'")
        wiki_query = f"{query} logo" if is_club else f"{query}"
        wiki_path = self._fetch_wikimedia_image(wiki_query)
        if wiki_path: return wiki_path

        # 2. DDG
        if is_club:
            full_query = f"{query} football club logo badge stadium wallpaper {self.neg_keywords}"
            print(f"DEBUG: Searching DDG for CLUB Profile: '{full_query}'")
            filepath = self._fetch_ddg_image(full_query, "profile")
        else:
            full_query = f"{query} football player face portrait real life {self.neg_keywords} -cartoon -drawing -game"
            print(f"DEBUG: Searching DDG for PLAYER Profile: '{full_query}'")
            filepath = self._fetch_ddg_image(full_query, "profile")

        if filepath: return filepath
        
        # 3. Pexels (Fallback)
        print(f"DEBUG: Fallback to Pexels for Profile: '{query}'")
        return self._fetch_pexels_image(f"{query} face", "square")

    def get_media(self, query, count=5, orientation="portrait"):
        """
        Fetches media with prioritization:
        1. ScoreBat Video Highlights (if match related)
        2. Wikimedia Images (Accuracy)
        3. DDG Images (Variety)
        4. Pexels Videos (Dynamic Fallback)
        """
        paths = []
        # Cleanup query but FORCE specific context
        clean_query = query.replace(" football", "").replace(" soccer", "").strip()
        
        # Determine strict query for searches
        # If it's a specific entity (Messi, Ronaldo), we might not need "soccer" as much, 
        # but for safety, we append it to ambiguous terms.
        # actually, let's just append "soccer" to all search queries to be safe against "Giants" (NFL) vs "Giants" (Baseball/etc)
        # But for specific player names, it might dilute. 
        # Strategy: Use clean_query for specific checks, but constructed_query for APIs.
        
        search_term = f"{clean_query} soccer" 
        
        print(f"Sourcing media for: {clean_query} (Search Term: {search_term}) (Need {count})")
        needed = count
        
        # 1. ScoreBat Highlights (Experimental - Metadata/Limited)
        print(f"Fetching ScoreBat highlights for: {clean_query}")
        sb_video = self._fetch_scorebat_highlight(clean_query)
        if sb_video:
            paths.append(sb_video)
            needed -= 1

        # 2. YouTube Clips (High Specificity)
        # Attempt to find a short clip for specific entities
        if needed > 0:
            print(f"Fetching YouTube clip for: {clean_query}")
            yt_clip = self._fetch_youtube_clip(clean_query)
            if yt_clip:
                paths.append(yt_clip)
                needed -= 1

        # 3. Wikimedia (High Accuracy Images)
        if needed > 0:
            print(f"Fetching specific images from Wikimedia (Target: {needed})...")
            # If we found a video, we might only need images to fill gaps.
            # If we didn't find video, we rely heavily on images for specificity.
            wiki_imgs = self._fetch_wikimedia_images(clean_query, count=needed)
            paths.extend(wiki_imgs)
            needed -= len(wiki_imgs)
            
        # 4. DDG Images (Variety/Specific Action)
        if needed > 0:
            print(f"Fetching specific images from DDG (Target: {needed})...")
            strict_query = f"{clean_query} football match action real life {self.neg_keywords} -drawing -cartoon"
            ddg_imgs = self._fetch_ddg_images(strict_query, count=needed + 2)
            paths.extend(ddg_imgs[:needed])
            needed -= len(ddg_imgs[:needed]) # Correctly subtract what we added
            
        # 5. Pexels Videos (Generic Fallback)
        # ONLY fetch if we still have space and the query is broad enough, 
        # OR if we have absolutely nothing. 
        # User prefers specific images over generic video unless generic video is truly relevant.
        current_count = len(paths)
        if current_count < count:
            remaining = count - current_count
            print(f"Checking fallbacks. Need {remaining} more items.")
            
            # If the query is specific (e.g. has a player name), avoid generic "football" videos
            # unless we have 0 assets.
            is_specific = any(x in clean_query.lower() for x in ["ronaldo", "messi", "united", "city", "real", "barca", "liverpool", "arsenal", "chelsea", "bayern"])
            
            if not is_specific or current_count == 0:
                print(f"Fetching videos from Pexels (Fallback, Need {remaining})...")
                # Try specific query first
                # Force "soccer" to avoid NFL
                vids = self._fetch_pexels_videos(f"{clean_query} soccer", count=remaining + 1, orientation=orientation)
                if not vids:
                    # Fallback to team color or generic
                    vids = self._fetch_pexels_videos("soccer stadium atmosphere", count=remaining, orientation=orientation)
                paths.extend(vids[:remaining])
            else:
                print("Skipping generic Pexels video fallback to preserve specificity (using existing images).")

        return paths[:count]

    def _fetch_scorebat_highlight(self, query):
        """
        Fetches video highlight from ScoreBat Free API.
        Meta-data only or thumbnail as fallback.
        """
        try:
            # url = "https://www.scorebat.com/video-api/v3/feed/?token=..." # Token needed for some endpoints, but feed is free
            resp = requests.get("https://www.scorebat.com/video-api/v3/feed/")
            if resp.status_code != 200: return None
            
            data = resp.json().get('response', [])
            
            # Simple fuzzy match
            query_parts = set(query.lower().split())
            best_match = None
            
            for match in data:
                title = match['title'].lower()
                competition = match['competition'].lower()
                if any(part in title for part in query_parts):
                    best_match = match
                    break
            
            if best_match:
                thumb = best_match['thumbnail']
                fname = f"scorebat_{hash(thumb)}.jpg"
                fpath = os.path.join(self.download_dir, fname)
                self._download_file(thumb, fpath)
                return fpath
                
        except Exception as e:
            print(f"ScoreBat error: {e}")
        return None

    def _fetch_youtube_clip(self, query):
        """
        Fetches a short YouTube clip (max 15s) using yt-dlp.
        Searches for 'shorts' or short videos to avoid downloading full matches.
        """
        try:
            import yt_dlp
            import logging
            
            # Search for more candidates to increase chance of finding a short video
            # Strict filtering in search query
            search_query = f"ytsearch5:{query} soccer shorts {self.neg_keywords}"
            ydl_opts = {
                'format': 'best[ext=mp4]/best', 
                'outtmpl': os.path.join(self.download_dir, 'yt_%(id)s.%(ext)s'),
                'noplaylist': True,
                'max_filesize': 50 * 1024 * 1024, 
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 10, # Add timeout to prevent hang
                'retries': 3,
                # Remove match_filter here to handle logical filtering manually
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # download=False first to inspect metadata
                info = ydl.extract_info(search_query, download=False)
                
                entries = info.get('entries', [])
                if not entries:
                    logging.warning(f"No YouTube results found for: {query}")
                    return None
                
                best_video = None
                for video in entries:
                    duration = video.get('duration', 0)
                    if duration and duration < 60:
                        best_video = video
                        break
                
                if not best_video:
                    logging.warning(f"No short videos found for: {query}")
                    return None

                # Now download the specific video
                # We need to set the URL or id
                webpage_url = best_video.get('webpage_url')
                if not webpage_url: return None
                
                # Download using the specific URL
                info = ydl.extract_info(webpage_url, download=True)
                filename = ydl.prepare_filename(info)
                
                base, _ = os.path.splitext(filename)
                for ext in ['.mp4', '.mkv', '.webm']:
                     if os.path.exists(base + ext):
                         return base + ext
                
                if os.path.exists(filename):
                    return filename
                    
        except ImportError:
            import logging
            logging.warning("yt-dlp not installed. Skipping YouTube fetch.")
        except Exception as e:
            import logging
            logging.warning(f"YouTube fetch error: {e}")
        return None


    def _fetch_wikimedia_image(self, query):
        """Fetches image from Wikimedia Commons API."""
        try:
            search_url = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrnamespace": 6,
                "gsrsearch": f"{query} filetype:bitmap",
                "gsrlimit": 3,
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
            }
            
            headers = {'User-Agent': 'FootyBitezBot/1.0'}
            import time
            time.sleep(1)
            r = requests.get(search_url, params=params, headers=headers, timeout=10)
            data = r.json()
            
            pages = data.get("query", {}).get("pages", {})
            if not pages: return None
            
            best_url = None
            for page_id in pages:
                page = pages[page_id]
                imageinfo = page.get("imageinfo", [])
                if not imageinfo: continue
                url = imageinfo[0].get("url")
                mime = imageinfo[0].get("mime", "")
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

    def _fetch_wikimedia_images(self, query, count):
        paths = []
        try:
            search_url = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrnamespace": 6, 
                "gsrsearch": f"{query} filetype:bitmap",
                "gsrlimit": count + 2,
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
            }
            headers = {'User-Agent': 'FootyBitezBot/1.0'}
            r = requests.get(search_url, params=params, headers=headers, timeout=10)
            data = r.json()
            pages = data.get("query", {}).get("pages", {})
            if not pages: return []
            
            urls = []
            for page_id in pages:
                page = pages[page_id]
                info = page.get("imageinfo", [])
                if info:
                    url = info[0].get("url")
                    mime = info[0].get("mime", "")
                    if "image/jpeg" in mime or "image/png" in mime:
                        urls.append(url)
            
            import time
            for url in urls[:count]:
                time.sleep(1)
                fname = f"wiki_bg_{hash(url)}.jpg"
                fpath = os.path.join(self.download_dir, fname)
                self._download_file(url, fpath)
                if os.path.exists(fpath): paths.append(fpath)
        except Exception as e:
            print(f"Wikimedia multiple error: {e}")
        return paths

    def _fetch_pexels_videos(self, query, count, orientation):
        paths = []
        if not self.api_key: return []
        try:
            url = "https://api.pexels.com/videos/search"
            # Ensure query has no "NFL" context
            final_query = f"{query} {self.neg_keywords}"
            params = {"query": final_query, "per_page": count, "orientation": orientation}
            res = requests.get(url, headers=self.headers, params=params)
            if res.status_code == 200:
                for vid in res.json().get('videos', []):
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
