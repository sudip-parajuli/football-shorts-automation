import os
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
        self.download_dir = download_dir
        self.credits_file = os.path.join(download_dir, "image_credits.txt")
        os.makedirs(download_dir, exist_ok=True)
        self.neg_keywords = "-nfl -american -rugby -superbowl -touchdown -helmet -cfl -afl -handball"
        
        # Initialize credits file
        if os.path.exists(self.credits_file):
            os.remove(self.credits_file)

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
        if os.path.exists(filepath): return
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0'}
            with requests.get(url, headers=headers, stream=True, timeout=15) as r:
                r.raise_for_status()
                if 'text/html' in r.headers.get('Content-Type', '').lower(): return
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

    def get_thumbnail_image(self, query):
        """Fetches a high-contrast image for the thumbnail."""
        print(f"Sourcing thumbnail for: {query}")
        # Try Unsplash first for "high contrast" thumbnail look
        path = self._fetch_unsplash_image(f"{query} high contrast documentary", count=1)
        if path: return path[0]
        
        # Fallback Pixabay
        path = self._fetch_pixabay_image(f"{query} cinematic", count=1)
        if path: return path[0]
        
        # Fallback DDG
        return self._fetch_ddg_image(f"{query} soccer wallpaper 4k", "thumb")

    def get_media_for_script(self, image_queries, thumbnail_query=None):
        """
        Main pipeline for documentary image sourcing.
        Prioritizes Wikimedia -> Unsplash -> Pixabay.
        """
        assets = {}
        
        # 1. Source Thumbnail
        if thumbnail_query:
            assets['thumbnail'] = self.get_thumbnail_image(thumbnail_query)
        
        # 2. Source Script Images
        for i, query in enumerate(image_queries):
            print(f"Sourcing image {i+1}/{len(image_queries)}: {query}")
            
            # Step 1: Wikimedia
            path = self._fetch_wikimedia_image(query)
            if path:
                assets[f"image_{i}"] = path
                continue
                
            # Step 2: Unsplash
            paths = self._fetch_unsplash_image(query, count=1)
            if paths:
                assets[f"image_{i}"] = paths[0]
                continue
                
            # Step 3: Pixabay
            paths = self._fetch_pixabay_image(query, count=1)
            if paths:
                assets[f"image_{i}"] = paths[0]
                continue
                
            # Fallback: Solid color (Handled by Remotion if path is None, but let's provide a fallback query)
            assets[f"image_{i}"] = self._fetch_ddg_image(f"{query} soccer", f"fallback_{i}")
            
        return assets

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
                "gsrlimit": 1,
                "prop": "imageinfo",
                "iiprop": "url|size|mime|extmetadata",
            }
            
            headers = {'User-Agent': 'FootyBitezBot/1.0'}
            r = requests.get(search_url, params=params, headers=headers, timeout=10)
            data = r.json()
            
            pages = data.get("query", {}).get("pages", {})
            if not pages: return None
            
            for page_id in pages:
                page = pages[page_id]
                imageinfo = page.get("imageinfo", [])
                if not imageinfo: continue
                url = imageinfo[0].get("url")
                
                # Record License
                meta = imageinfo[0].get("extmetadata", {})
                license_name = meta.get("LicenseShortName", {}).get("value", "CC BY-SA")
                artist = meta.get("Artist", {}).get("value", "Unknown")
                # Clean HTML tags from artist
                artist = re.sub('<[^<]+?>', '', artist)
                
                fname = f"wiki_{hash(url)}.jpg"
                fpath = os.path.join(self.download_dir, fname)
                self._download_file(url, fpath)
                
                if os.path.exists(fpath):
                    self._add_credit(f"Image from Wikimedia Commons: {artist} ({license_name})")
                    return fpath
        except Exception as e:
            print(f"Wikimedia error: {e}")
        return None

    def _fetch_unsplash_image(self, query, count=1):
        if not self.unsplash_api_key: return []
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
        if not self.pixabay_api_key: return []
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
        """Fetches an image using DDG as final fallback."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.images(query, max_results=1))
                if results:
                    image_url = results[0].get('image')
                    if image_url:
                        filename = f"ddg_{suffix}_{hash(query)}.{image_url.split('.')[-1].split('?')[0][:3]}"
                        if len(filename.split('.')[-1]) > 3: filename += ".jpg"
                        filepath = os.path.join(self.download_dir, filename)
                        self._download_file(image_url, filepath)
                        if os.path.exists(filepath):
                            return filepath
        except Exception as e:
            print(f"DDG Fallback error: {e}")
        return None

if __name__ == "__main__":
    sourcer = MediaSourcer()
    # Test
    # sourcer.get_media_for_script(["Lionel Messi lifting world cup"], "Lionel Messi face focus")
