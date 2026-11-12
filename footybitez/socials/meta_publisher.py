import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

class MetaPublisher:
    def __init__(self, use_footybitez=True):
        # Retain the legacy argument for existing callers. All workflows now
        # target FootyBitez; even use_footybitez=False cannot select another token.
        self.access_token = os.getenv("FOOTYBITEZ_META_ACCESS_TOKEN")
        self.page_id = os.getenv("FOOTYBITEZ_FACEBOOK_PAGE_ID")
        self.page_ids_filter = os.getenv("FOOTYBITEZ_FACEBOOK_PAGE_IDS")
        self.instagram_id = os.getenv("FOOTYBITEZ_INSTAGRAM_BUSINESS_ACCOUNT_ID")
        self.api_version = os.getenv("META_GRAPH_API_VERSION", "v25.0")
        self.base_url = "https://graph.facebook.com"
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    @staticmethod
    def _response_data(response, operation):
        try:
            data = response.json()
        except ValueError:
            raise RuntimeError(f"{operation}: HTTP {response.status_code}, non-JSON response (content-type {response.headers.get('Content-Type', 'unknown')})") from None
        if not 200 <= response.status_code < 300 or not isinstance(data, dict) or data.get('error'):
            error = data.get('error', {}) if isinstance(data, dict) else {}
            # Log codes, never raw responses which may contain credentials.
            raise RuntimeError(f"{operation}: HTTP {response.status_code}, Meta code {error.get('code', 'unknown')}, subcode {error.get('error_subcode', 'unknown')}")
        return data

    def _upload_facebook_chunks(self, file_path, page_id, token, title, description):
        url = f"https://graph-video.facebook.com/{self.api_version}/{page_id}/videos"
        size = os.path.getsize(file_path)
        data = self._response_data(requests.post(url, data={
            'access_token':token, 'upload_phase':'start', 'file_size':size}, timeout=(15, 120)), 'Facebook start')
        session, video_id = data['upload_session_id'], data['video_id']
        start, end = int(data['start_offset']), int(data['end_offset'])
        with open(file_path, 'rb') as source:
            while start < end:
                if not 0 <= start < end <= size or end-start > 32*1024*1024:
                    raise RuntimeError('Facebook returned an invalid or oversized chunk range')
                source.seek(start)
                chunk = source.read(end-start)
                if len(chunk) != end-start:
                    raise RuntimeError('Facebook upload file changed during transfer')
                data = self._response_data(requests.post(url, data={
                    'access_token':token, 'upload_phase':'transfer', 'upload_session_id':session,
                    'start_offset':start}, files={'video_file_chunk':('chunk.mp4',chunk,'application/octet-stream')},
                    timeout=(15, 180)), 'Facebook transfer')
                next_start, next_end = int(data['start_offset']), int(data['end_offset'])
                if next_start != end or not next_start <= next_end <= size:
                    raise RuntimeError('Facebook upload offsets did not advance correctly')
                start, end = next_start, next_end
        if start != size:
            raise RuntimeError('Facebook upload ended before the whole file was transferred')
        data = self._response_data(requests.post(url, data={
            'access_token':token, 'upload_phase':'finish', 'upload_session_id':session,
            'title':title, 'description':description}, timeout=(15, 180)), 'Facebook finish')
        if data.get('success') is not True:
            raise RuntimeError('Facebook did not confirm upload completion')
        return video_id

    def preflight_instagram(self):
        """Check account access before spending time hosting a video."""
        if not self.access_token or not self.instagram_id:
            return False
        try:
            response = requests.get(
                f"{self.base_url}/{self.api_version}/{self.instagram_id}",
                params={"fields": "id", "access_token": self.access_token}, timeout=15)
            return response.ok and bool(response.json().get("id"))
        except Exception:
            return False

    def _get_authorized_pages(self) -> list:
        """
        Retrieves all authorized Facebook Pages and their Page Access Tokens dynamically.
        Returns a list of dicts: [{'id': '...', 'access_token': '...', 'name': '...'}]
        """
        if not self.access_token:
            return []

        url = f"{self.base_url}/{self.api_version}/me/accounts"
        params = {
            "access_token": self.access_token,
            "limit": 100
        }
        try:
            res = requests.get(url, params=params, timeout=15)
            if res.status_code == 200:
                data = res.json().get("data", [])
                logger.info(f"Retrieved {len(data)} authorized Facebook Pages from Meta account.")
                return data
            else:
                err_data = {}
                try:
                    err_data = res.json()
                except Exception:
                    pass
                err_msg = err_data.get("error", {}).get("message", "")
                if "accounts" in err_msg or err_data.get("error", {}).get("code") == 100:
                    logger.info("FOOTYBITEZ_META_ACCESS_TOKEN is a Page Access Token. Dynamic page list discovery skipped; using page token directly.")
                else:
                    logger.warning(f"Failed to fetch authorized pages: {res.text}")
        except Exception as e:
            logger.error(f"Error fetching authorized pages from Meta: {e}")
        return []


    def publish_to_facebook(self, file_path, title, description):
        """
        Uploads a video to all authorized or filtered Facebook Pages.
        Uses dynamic Page Access Tokens.
        """
        if not self.access_token:
            logger.warning("FOOTYBITEZ_META_ACCESS_TOKEN not configured. Skipping Facebook publishing.")
            return None

        # 1. Fetch all authorized pages dynamically
        pages = self._get_authorized_pages()
        
        # 2. Filter pages if filter or page_id is set
        filtered_pages = []
        target_ids = []
        if self.page_ids_filter:
            target_ids = [pid.strip() for pid in self.page_ids_filter.split(",") if pid.strip()]
        elif self.page_id:
            target_ids = [self.page_id.strip()]

        for p in pages:
            pid = p.get("id")
            if target_ids:
                if pid in target_ids:
                    filtered_pages.append(p)
            else:
                filtered_pages.append(p)

        # Fallback to default page_id if no pages were dynamically fetched/matched but we have a single ID
        if not filtered_pages and self.page_id:
            logger.info("Using fallback single FOOTYBITEZ_FACEBOOK_PAGE_ID and configured Page token.")
            filtered_pages.append({
                "id": self.page_id,
                "access_token": self.access_token,
                "name": "Fallback Page"
            })

        if not filtered_pages:
            logger.warning("No Facebook Pages available or matching filter criteria. Skipping.")
            return None

        video_ids = []
        for page in filtered_pages:
            pid = page["id"]
            pname = page.get("name", "Unknown Page")
            pat = page.get("access_token", self.access_token)

            if self.dry_run:
                logger.info(f"[DRY RUN] Publishing video to Facebook Page '{pname}' ({pid}): '{title}'")
                video_ids.append(f"mock_fb_id_{pid}")
                continue

            url = f"{self.base_url}/{self.api_version}/{pid}/videos"
            logger.info(f"Uploading video {file_path} to Facebook Page '{pname}' ({pid})...")
            
            try:
                if os.path.getsize(file_path) >= 32*1024*1024:
                    video_ids.append(self._upload_facebook_chunks(file_path, pid, pat, title, description))
                    continue
                with open(file_path, "rb") as video_file:
                    payload = {
                        "title": title,
                        "description": description,
                        "access_token": pat
                    }
                    files = {
                        "source": video_file
                    }
                    response = requests.post(url, data=payload, files=files, timeout=120)
                    response_data = self._response_data(response, "Facebook upload")
                    
                    if response.status_code == 200 and "id" in response_data:
                        vid = response_data["id"]
                        logger.info(f"SUCCESS: Video published to Facebook Page '{pname}'. Video ID: {vid}")
                        video_ids.append(vid)
                    else:
                        logger.error(f"Facebook Page '{pname}' upload failed: {response.text}")
            except Exception as e:
                logger.error(f"Exception while uploading to Facebook Page '{pname}': {e}")

        return video_ids[0] if video_ids else None


    def publish_to_instagram_reel(self, video_url, caption, local_file=None):
        """
        Publishes a video to Instagram Reels.
        Accepts a local file via Meta resumable upload or a public video URL.
        """
        if not self.access_token or not self.instagram_id:
            logger.warning("Instagram credentials (FOOTYBITEZ_META_ACCESS_TOKEN, FOOTYBITEZ_INSTAGRAM_BUSINESS_ACCOUNT_ID) not configured. Skipping.")
            return None

        if self.dry_run:
            logger.info(f"[DRY RUN] Publishing video to Instagram Reels: caption='{caption[:50]}...', url='{video_url}'")
            return "mock_instagram_media_id"

        # Step 1: Create Container
        logger.info("Initializing Instagram Reels media container...")
        container_url = f"{self.base_url}/{self.api_version}/{self.instagram_id}/media"
        container_payload = {
            "media_type": "REELS",
            "caption": caption[:2200],
            "access_token": self.access_token
        }
        if local_file:
            container_payload['upload_type'] = 'resumable'
        else:
            container_payload['video_url'] = video_url
        
        try:
            container_res = requests.post(container_url, data=container_payload, timeout=(15, 60))
            container_data = self._response_data(container_res, "Instagram create")
            
            if container_res.status_code != 200 or "id" not in container_data:
                logger.error(f"Failed to create Instagram media container: {container_res.text}")
                return None
                
            creation_id = container_data["id"]
            if local_file:
                from urllib.parse import urlparse
                upload_uri = container_data.get('uri', '')
                parsed = urlparse(upload_uri)
                if parsed.scheme != 'https' or parsed.hostname != 'rupload.facebook.com':
                    raise RuntimeError('Instagram returned an unexpected upload URI')
                with open(local_file, 'rb') as source:
                    uploaded = requests.post(upload_uri, headers={
                        'Authorization':f'OAuth {self.access_token}', 'offset':'0',
                        'file_size':str(os.path.getsize(local_file)), 'Content-Type':'application/octet-stream'},
                        data=source, timeout=(15, 900), allow_redirects=False)
                self._response_data(uploaded, 'Instagram binary upload')
            logger.info(f"Container created. ID: {creation_id}. Polling container status...")

            # Step 2: Poll Container Status until FINISHED
            status_url = f"{self.base_url}/{self.api_version}/{creation_id}"
            params = {
                "fields": "status_code,status",
                "access_token": self.access_token
            }
            
            # Instagram Reel processing usually takes 30-90 seconds. We'll poll every 10 seconds.
            max_attempts = 60 # Allow up to ten minutes for documentary processing
            for attempt in range(max_attempts):
                time.sleep(10)
                status_res = requests.get(status_url, params=params, timeout=(15, 60))
                status_data = self._response_data(status_res, "Instagram processing")
                
                if status_res.status_code == 200:
                    status_code = status_data.get("status_code")
                    logger.info(f"Poll attempt {attempt+1}/{max_attempts} - Status: {status_code}")
                    
                    if status_code == "FINISHED":
                        break
                    elif status_code == "ERROR":
                        logger.error(f"Instagram media container processing failed: {status_data.get('status')}")
                        return None
                else:
                    logger.warning(f"Failed to fetch container status: {status_res.text}")

            else:
                logger.error("Timed out waiting for Instagram Reel processing container to finish.")
                return None

            # Step 3: Publish Container
            logger.info("Publishing Instagram Reel...")
            publish_url = f"{self.base_url}/{self.api_version}/{self.instagram_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }
            
            publish_res = requests.post(publish_url, data=publish_payload, timeout=(15, 120))
            publish_data = self._response_data(publish_res, "Instagram publish")
            
            if publish_res.status_code == 200 and "id" in publish_data:
                media_id = publish_data["id"]
                logger.info(f"SUCCESS: Video published to Instagram Reels. Media ID: {media_id}")
                return media_id
            else:
                logger.error(f"Instagram media publish failed: {publish_res.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception during Instagram Reels publication: {e}")
            return None
