import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

class TikTokPublisher:
    def __init__(self):
        self.client_key = os.getenv("TIKTOK_CLIENT_KEY")
        self.client_secret = os.getenv("TIKTOK_CLIENT_SECRET")
        self.refresh_token = os.getenv("TIKTOK_REFRESH_TOKEN")
        self.access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        self.base_url = "https://open.tiktokapis.com/v2"

    def _get_access_token(self):
        """
        Gets a valid access token. Uses a direct token if provided, 
        otherwise refreshes it using the Client Credentials & Refresh Token.
        """
        if self.access_token:
            return self.access_token

        if not self.client_key or not self.client_secret or not self.refresh_token:
            logger.warning("TikTok credentials missing. Cannot refresh token.")
            return None

        logger.info("Refreshing TikTok access token...")
        url = f"{self.base_url}/oauth/token/"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        payload = {
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }

        try:
            res = requests.post(url, headers=headers, data=payload)
            data = res.json()
            if res.status_code == 200 and "access_token" in data:
                # Log the refreshed refresh token if TikTok rotated it
                new_refresh = data.get("refresh_token")
                if new_refresh and new_refresh != self.refresh_token:
                    logger.warning(
                        "TikTok rotated the Refresh Token! "
                        f"Make sure to update TIKTOK_REFRESH_TOKEN secret in GitHub repository with: {new_refresh}"
                    )
                self.access_token = data["access_token"]
                return self.access_token
            else:
                logger.error(f"Failed to refresh TikTok token: {res.text}")
                return None
        except Exception as e:
            logger.error(f"Exception refreshing TikTok token: {e}")
            return None

    def publish_video(self, file_path, title):
        """
        Publishes a video to TikTok via Direct Post API.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Publishing video to TikTok: '{title}'")
            return "mock_tiktok_publish_id"

        access_token = self._get_access_token()
        if not access_token:
            logger.warning("TikTok authentication not configured. Skipping.")
            return None

        if not os.path.exists(file_path):
            logger.error(f"TikTok upload failed: Video file not found at {file_path}")
            return None

        video_size = os.path.getsize(file_path)
        logger.info(f"Initializing TikTok video upload ({video_size} bytes)...")

        # Step 1: Initialize Upload
        init_url = f"{self.base_url}/post/publish/video/init/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }
        
        # Max title size on TikTok is 150 chars usually
        truncated_title = title[:150]
        
        payload = {
            "post_info": {
                "title": truncated_title,
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False,
                "video_cover_timestamp_ms": 1000
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1
            }
        }

        try:
            init_res = requests.post(init_url, headers=headers, json=payload)
            init_data = init_res.json()
            
            if init_res.status_code != 200 or "data" not in init_data:
                logger.error(f"TikTok initialization failed: {init_res.text}")
                return None
                
            upload_url = init_data["data"]["upload_url"]
            publish_id = init_data["data"].get("publish_id")
            logger.info(f"TikTok upload initialized. Publish ID: {publish_id}. Uploading binary...")

            # Step 2: Upload Video Binary Chunk
            upload_headers = {
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{video_size-1}/{video_size}"
            }
            
            with open(file_path, "rb") as video_file:
                upload_res = requests.put(upload_url, headers=upload_headers, data=video_file)
                
                # TikTok returns 200 or 201 for successful chunk uploads
                if upload_res.status_code in [200, 201]:
                    logger.info("SUCCESS: Video binary uploaded to TikTok successfully.")
                    return publish_id
                else:
                    logger.error(f"TikTok chunk upload failed with code {upload_res.status_code}: {upload_res.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Exception during TikTok publication: {e}")
            return None
