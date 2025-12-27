import os
import requests
import random
import urllib.request
from bs4 import BeautifulSoup
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
            # Try to delete individual files first to skip locked ones
            for filename in os.listdir(self.download_dir):
                file_path = os.path.join(self.download_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"Skipping {file_path} (likely locked): {e}")
            
            # Finally attempt to remove the directory if empty
            try:
                if not os.listdir(self.download_dir):
                    shutil.rmtree(self.download_dir)
                    os.makedirs(self.download_dir, exist_ok=True)
            except:
                pass
            print(f"Cleaned up {self.download_dir}")

    def get_media(self, query, count=5, orientation="portrait"):
        """
        Fetches 'count' media items (videos/images) from Pexels.
        Returns a list of local file paths.
        """
        if not self.api_key:
            print("Warning: PEXELS_API_KEY not found. Using placeholder fallback.")
            return []

        media_paths = []
        
        # 1. Search Videos (Priority)
        try:
            video_url = "https://api.pexels.com/videos/search"
            # Reinforce context - ensure it explicitly mentions football/soccer
            clean_query = query
            if "football" not in clean_query.lower() and "soccer" not in clean_query.lower():
                 clean_query += " football soccer"
            
            params = {
                "query": clean_query,
                "per_page": count,
                "orientation": orientation
            }
            response = requests.get(video_url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                videos = response.json().get('videos', [])
                for vid in videos:
                    # Find a good quality file, prefer 720p/1080p, MP4
                    video_files = vid.get('video_files', [])
                    best_file = None
                    for vf in video_files:
                        if vf['quality'] == 'hd' and vf['file_type'] == 'video/mp4':
                            best_file = vf
                            break
                    if not best_file and video_files:
                        best_file = video_files[0]
                    
                    if best_file:
                        link = best_file['link']
                        filename = f"pexels_vid_{vid['id']}.mp4"
                        filepath = os.path.join(self.download_dir, filename)
                        self._download_file(link, filepath)
                        media_paths.append(filepath)
            else:
                print(f"Pexels Video Search Failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Pexels Video Search Failed: {e}")

        # 2. Search Images (Fallback/Filler)
        if len(media_paths) < count:
            try:
                msg = f"Fetching images to fill gap (Have {len(media_paths)}, need {count})"
                print(msg)
                img_url = "https://api.pexels.com/v1/search"
                # Reinforce context
                clean_query = query
                if "football" not in clean_query.lower() and "soccer" not in clean_query.lower():
                     clean_query += " football soccer"
                
                params = {
                    "query": clean_query,
                    "per_page": count,
                    "orientation": orientation
                }
                response = requests.get(img_url, headers=self.headers, params=params)
                
                if response.status_code == 200:
                   photos = response.json().get('photos', [])
                   for photo in photos:
                       if len(media_paths) >= count:
                           break
                       src = photo['src']['portrait']
                       filename = f"pexels_img_{photo['id']}.jpg"
                       filepath = os.path.join(self.download_dir, filename)
                       self._download_file(src, filepath)
                       media_paths.append(filepath)
                else:
                    print(f"Pexels Image Search Failed: {response.status_code}")
            except Exception as e:
                 print(f"Pexels Image Search Failed: {e}")

        return media_paths

    def _download_file(self, url, filepath):
        """Downloads a file using requests with headers to avoid 403."""
        if os.path.exists(filepath):
            return
        
        try:
            # User-Agent is often required to avoid 403 on direct file links
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            with requests.get(url, headers=headers, stream=True, timeout=15) as r:
                r.raise_for_status()
                
                # Check content type for safety
                content_type = r.headers.get('Content-Type', '').lower()
                if 'text/html' in content_type:
                    print(f"Warning: URL {url} returned HTML instead of media. Skipping.")
                    return

                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            # Final check: is it an empty file?
            if os.path.exists(filepath) and os.path.getsize(filepath) < 100:
                print(f"Warning: Downloaded file {filepath} is too small (<100 bytes). Likely corrupted.")
                os.remove(filepath)
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)

    # Updated MediaSourcer with DuckDuckGo for Images
    def get_profile_image(self, query):
        """Fetches a specific image (Portrait/Face) using DDG -> Wikipedia -> Pexels."""
        filepath = None
        
        # 1. Try DuckDuckGo
        try:
            from duckduckgo_search import DDGS
            import time
            time.sleep(1) # Tiny delay to mitigate rate limiting
            print(f"Fetching profile image (DDG) for: {query}")
            with DDGS() as ddgs:
                # Be very specific
                search_term = f"{query} professional football player soccer portrait"
                # Use retry logic for DDG
                for attempt in range(2):
                    try:
                        results = list(ddgs.images(search_term, max_results=3))
                        if results:
                            img_url = results[0].get('image')
                            if img_url:
                                filename = f"profile_ddg_{hash(query)}.jpg"
                                filepath = os.path.join(self.download_dir, filename)
                                self._download_file(img_url, filepath)
                                break
                    except Exception as e:
                        if "403" in str(e) and attempt == 0:
                            print("DDG Rate Limit hit, retrying with slight delay...")
                            import time
                            time.sleep(2)
                            continue
                        raise e
        except Exception as e:
            print(f"DDG Profile fetch failed: {e}")
        
        if filepath and os.path.exists(filepath):
            return filepath
            
        # 2. Try Wikipedia Scraper (Great for specific players)
        print(f"Falling back to Wikipedia for Profile Image: {query}")
        filepath = self.get_wikipedia_image(query)
        if filepath and os.path.exists(filepath):
            return filepath

        # 3. Fallback to Pexels
        print("Falling back to Pexels for Profile Image...")
        return self._get_pexels_image(f"{query} face", orientation='square')

    def get_wikipedia_image(self, query):
        """Scrapes the main image from the Wikipedia Infobox for a topic."""
        try:
            import wikipedia
            search_res = wikipedia.search(query, results=1)
            if not search_res:
                return None
            
            # Get the page URL
            page = wikipedia.page(search_res[0], auto_suggest=False)
            url = page.url
            print(f"Scraping Wikipedia Page: {url}")
            
            # Scrape the page for the infobox image
            headers = {'User-Agent': 'FootyBitez/1.0 (contact: footybitez@example.com)'}
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Multiple infobox patterns
            infobox = soup.find('table', class_=lambda x: x and 'infobox' in x)
            if not infobox:
                # Some articles use diverse classes
                infobox = soup.select_one('.infobox, .vcard, .biog')
                
            if not infobox:
                return None
            
            img_tag = infobox.find('img')
            if not img_tag:
                return None
            
            img_url = img_tag['src']
            if img_url.startswith('//'):
                img_url = "https:" + img_url
            elif not img_url.startswith('http'):
                img_url = "https://en.wikipedia.org" + img_url
                
            filename = f"wiki_{hash(query)}.jpg"
            filepath = os.path.join(self.download_dir, filename)
            
            self._download_file(img_url, filepath)
            return filepath
        except Exception as e:
            print(f"Wikipedia Image Scrape failed: {e}")
            return None

    def get_title_card_image(self, query):
        """Fetches a high-impact cinematic image using DuckDuckGo, falls back to Pexels."""
        filepath = None
        try:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                from ddgs import DDGS
            print(f"Fetching title card (DDG) for: {query}")
            with DDGS() as ddgs:
                # Use retry logic for DDG
                for attempt in range(2):
                    try:
                        results = list(ddgs.images(f"{query} football cinematic wallpaper 4k", max_results=3))
                        if results:
                            img_url = results[0].get('image')
                            if img_url:
                                filename = f"title_ddg_{hash(query)}.jpg"
                                filepath = os.path.join(self.download_dir, filename)
                                self._download_file(img_url, filepath)
                                break
                    except Exception as e:
                        if "403" in str(e) and attempt == 0:
                            import time
                            time.sleep(2)
                            continue
                        raise e
        except Exception as e:
            print(f"DDG Title fetch failed: {e}")
            
        if filepath and os.path.exists(filepath):
            return filepath
            
        # Fallback to Pexels
        print("Falling back to Pexels for Title Image...")
        return self._get_pexels_image(f"{query} stadium", orientation='portrait')

    def _get_pexels_image(self, query, orientation='portrait'):
        """Helper to fetch image from Pexels."""
        try:
            img_url = "https://api.pexels.com/v1/search"
            # Be very specific
            full_query = query + " football soccer sports"
            params = {
                "query": full_query,
                "per_page": 1,
                "orientation": orientation
            }
            response = requests.get(img_url, headers=self.headers, params=params)
            if response.status_code == 200:
                photos = response.json().get('photos', [])
                if photos:
                    src = photos[0]['src']['large']
                    filename = f"pexels_{photos[0]['id']}.jpg"
                    filepath = os.path.join(self.download_dir, filename)
                    self._download_file(src, filepath)
                    return filepath
        except Exception as e:
            print(f"Pexels fallback failed: {e}")
        return None
            
    def get_media(self, query, count=5, video_mode=True, orientation="portrait"):
        """
        Fetches media.
        If video_mode=True (default), tries to fetch VIDEOS from Pexels (best for background).
        If video_mode=False or specific image requested, uses DuckDuckGo for images.
        """
        if "visual_keyword" in query:
             # Legacy or specific dict handling
             pass
             
        # For our usage:
        # Pexels is great for "Stadium", "Crowd", "Abstract Football" VIDEOS.
        # DDG is great for "Messi lifting trophy" IMAGES.
        
        # Strategy: Mix.
        # But user said "Pexels doesn't provide images according to context".
        # So for Segments, we might want IMAGES from DDG if the keyword is a Person.
        
        # Let's split:
        # If query implies a specific person (Messi, Ronaldo), prefer DDG Image.
        # If query is generic (Stadium, Football), prefer Pexels Video.
        
        # Actually, user wants "images related to football only or the images of that particular player".
        # Let's implement a dual search:
        # 1. Try DDG Image for specific context.
        # 2. Key Pexels for motion textures.
        
        visual_assets = []
        
        try:
            from duckduckgo_search import DDGS
            import time
            time.sleep(1) # Tiny delay
            
            # 1. Fetch DDG Images (Specifics)
            print(f"Fetching DDG Images for: {query}")
            with DDGS() as ddgs:
                # Use retry logic for DDG
                results = []
                for attempt in range(2):
                    try:
                        results = list(ddgs.images(f"{query} football high quality", max_results=count))
                        break
                    except Exception as e:
                        if "403" in str(e) and attempt == 0:
                            import time
                            time.sleep(2)
                            continue
                        raise e
                
            for res in results:
                try:
                    url = res.get('image')
                    if not url: continue
                    ext = url.split('.')[-1].split('?')[0]
                    if ext.lower() not in ['jpg', 'jpeg', 'png', 'webp']: ext = 'jpg'
                    
                    filename = f"ddg_{hash(url)}.{ext}"
                    filepath = os.path.join(self.download_dir, filename)
                    self._download_file(url, filepath)
                    if os.path.exists(filepath):
                        visual_assets.append(filepath)
                except:
                    continue
        except Exception as e:
            print(f"DDG Image search failed: {e}")

        # If we need more or want video backup, hit Pexels
        if len(visual_assets) < count:
             print("Falling back to Pexels/Video for extra media...")
             # Pexels search already appends "football" via the updated get_media helper logic above
             # But here we'll do a focused search for football action
             fallback_query = "football action match"
             headers = self.headers
             params = {"query": fallback_query, "per_page": count - len(visual_assets), "orientation": orientation}
             try:
                 v_url = "https://api.pexels.com/videos/search"
                 response = requests.get(v_url, headers=headers, params=params)
                 if response.status_code == 200:
                     videos = response.json().get('videos', [])
                     for video in videos:
                         video_files = video.get('video_files', [])
                         best_video = None
                         for vf in video_files:
                             is_correct_orient = (vf['width'] < vf['height']) if orientation == "portrait" else (vf['width'] > vf['height'])
                             if is_correct_orient and vf['height'] >= 720:
                                  best_video = vf
                                  break
                         if not best_video and video_files: best_video = video_files[0]
                         if best_video:
                             src = best_video['link']
                             filename = f"pexels_{video['id']}.mp4"
                             filepath = os.path.join(self.download_dir, filename)
                             self._download_file(src, filepath)
                             visual_assets.append(filepath)
                 else:
                    print(f"Pexels Video Search Failed: {response.status_code} - {response.text}")
             except Exception as pe:
                 print(f"Pexels fallback error: {pe}")
        
        return visual_assets[:count]

if __name__ == "__main__":
    sourcer = MediaSourcer()
    # paths = sourcer.get_media("football stadium", count=3)
    # print(paths)
