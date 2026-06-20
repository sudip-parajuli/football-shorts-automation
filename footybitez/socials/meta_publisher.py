import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

class MetaPublisher:
    def __init__(self, use_footybitez=False):
        if use_footybitez:
            self.access_token = os.getenv("FOOTYBITEZ_META_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN")
            self.page_id = os.getenv("FOOTYBITEZ_FACEBOOK_PAGE_ID") or os.getenv("FACEBOOK_PAGE_ID")
            self.page_ids_filter = os.getenv("FOOTYBITEZ_FACEBOOK_PAGE_IDS") or os.getenv("FACEBOOK_PAGE_IDS")
            self.instagram_id = os.getenv("FOOTYBITEZ_INSTAGRAM_BUSINESS_ACCOUNT_ID") or os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        else:
            self.access_token = os.getenv("META_ACCESS_TOKEN")
            self.page_id = os.getenv("FACEBOOK_PAGE_ID")
            self.page_ids_filter = os.getenv("FACEBOOK_PAGE_IDS")  # Comma-separated Page IDs
            self.instagram_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        self.api_version = "v19.0"
        self.base_url = "https://graph.facebook.com"
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

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
                    logger.info("META_ACCESS_TOKEN is a Page Access Token. Dynamic page list discovery skipped; using page token directly.")
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
            logger.warning("META_ACCESS_TOKEN not configured. Skipping Facebook publishing.")
            return None

        # 1. Fetch all authorized pages dynamically
        pages = self._get_authorized_pages()
        
        # 2. Filter pages if FACEBOOK_PAGE_IDS is specified
        filtered_pages = []
        filter_ids = []
        if self.page_ids_filter:
            filter_ids = [pid.strip() for pid in self.page_ids_filter.split(",") if pid.strip()]

        for p in pages:
            pid = p.get("id")
            if filter_ids:
                if pid in filter_ids:
                    filtered_pages.append(p)
            else:
                filtered_pages.append(p)

        # Fallback to default page_id if no pages were dynamically fetched but we have a single ID
        if not filtered_pages and self.page_id:
            logger.info("Using fallback single FACEBOOK_PAGE_ID and default User Token.")
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
                    response_data = response.json()
                    
                    if response.status_code == 200 and "id" in response_data:
                        vid = response_data["id"]
                        logger.info(f"SUCCESS: Video published to Facebook Page '{pname}'. Video ID: {vid}")
                        video_ids.append(vid)
                    else:
                        logger.error(f"Facebook Page '{pname}' upload failed: {response.text}")
            except Exception as e:
                logger.error(f"Exception while uploading to Facebook Page '{pname}': {e}")

        return video_ids[0] if video_ids else None


    def publish_to_instagram_reel(self, video_url, caption):
        """
        Publishes a video to Instagram Reels.
        Requires a publicly accessible URL to the video file.
        """
        if not self.access_token or not self.instagram_id:
            logger.warning("Instagram credentials (META_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID) not configured. Skipping.")
            return None

        if self.dry_run:
            logger.info(f"[DRY RUN] Publishing video to Instagram Reels: caption='{caption[:50]}...', url='{video_url}'")
            return "mock_instagram_media_id"

        # Step 1: Create Container
        logger.info("Initializing Instagram Reels media container...")
        container_url = f"{self.base_url}/{self.api_version}/{self.instagram_id}/media"
        container_payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": self.access_token
        }
        
        try:
            container_res = requests.post(container_url, data=container_payload)
            container_data = container_res.json()
            
            if container_res.status_code != 200 or "id" not in container_data:
                logger.error(f"Failed to create Instagram media container: {container_res.text}")
                return None
                
            creation_id = container_data["id"]
            logger.info(f"Container created. ID: {creation_id}. Polling container status...")

            # Step 2: Poll Container Status until FINISHED
            status_url = f"{self.base_url}/{self.api_version}/{creation_id}"
            params = {
                "fields": "status_code,status",
                "access_token": self.access_token
            }
            
            # Instagram Reel processing usually takes 30-90 seconds. We'll poll every 10 seconds.
            max_attempts = 18 # 3 minutes total timeout
            for attempt in range(max_attempts):
                time.sleep(10)
                status_res = requests.get(status_url, params=params)
                status_data = status_res.json()
                
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
            
            publish_res = requests.post(publish_url, data=publish_payload)
            publish_data = publish_res.json()
            
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
