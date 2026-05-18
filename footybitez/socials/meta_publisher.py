import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

class MetaPublisher:
    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.page_id = os.getenv("FACEBOOK_PAGE_ID")
        self.instagram_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        self.api_version = "v19.0"
        self.base_url = "https://graph.facebook.com"
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    def publish_to_facebook(self, file_path, title, description):
        """
        Uploads a video to a Facebook Page.
        Uses direct binary upload.
        """
        if not self.access_token or not self.page_id:
            logger.warning("Facebook credentials (META_ACCESS_TOKEN, FACEBOOK_PAGE_ID) not configured. Skipping.")
            return None

        if self.dry_run:
            logger.info(f"[DRY RUN] Publishing video to Facebook Page {self.page_id}: '{title}'")
            return "mock_facebook_video_id"

        url = f"{self.base_url}/{self.api_version}/{self.page_id}/videos"
        
        logger.info(f"Uploading video {file_path} to Facebook Page {self.page_id}...")
        
        try:
            with open(file_path, "rb") as video_file:
                payload = {
                    "title": title,
                    "description": description,
                    "access_token": self.access_token
                }
                files = {
                    "source": video_file
                }
                response = requests.post(url, data=payload, files=files)
                response_data = response.json()
                
                if response.status_code == 200 and "id" in response_data:
                    video_id = response_data["id"]
                    logger.info(f"SUCCESS: Video published to Facebook. Video ID: {video_id}")
                    return video_id
                else:
                    logger.error(f"Facebook upload failed: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Exception while uploading to Facebook: {e}")
            return None

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
