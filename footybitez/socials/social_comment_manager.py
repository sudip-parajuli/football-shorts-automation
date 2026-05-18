import os
import json
import logging
import requests
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class SocialCommentManager:
    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.page_ids_filter = os.getenv("FACEBOOK_PAGE_IDS")
        self.instagram_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        self.api_version = "v19.0"
        self.base_url = "https://graph.facebook.com"
        
        # Configure Gemini
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        if self.gemini_api_key:
            try:
                # Use the recommended google.genai package
                self.client = genai.Client(api_key=self.gemini_api_key)
                self.model_name = "gemini-2.5-flash"
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")

    def _get_authorized_pages(self) -> list:
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
                return res.json().get("data", [])
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
            logger.error(f"Error fetching authorized pages: {e}")
        return []

    def _generate_reply(self, comment_text, platform="social media"):
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY not configured. Cannot generate reply.")
            return None
        
        prompt = f"""
        You are the creator of a popular football documentary channel. 
        A viewer left this comment on your {platform} video: "{comment_text}"
        
        Write a short (max 2 sentences), engaging, and appreciative reply. 
        Use a "Fan's Voice" — be opinionated but respectful, use football slang if appropriate. 
        If they ask a question, answer it if possible, otherwise be encouraging.
        
        REPLY:
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip() if response.text else None
        except Exception as e:
            logger.error(f"Gemini social reply generation failed: {e}")
            return None

    def auto_reply_facebook(self, max_posts=10):
        """
        Polls recent Facebook posts across all authorized pages and replies to unanswered comments.
        """
        if not self.access_token:
            logger.warning("META_ACCESS_TOKEN not set. Skipping Facebook auto-reply.")
            return

        pages = self._get_authorized_pages()
        
        # Fallback to single configured page ID if list discovery was skipped/failed
        if not pages:
            fallback_id = None
            if self.page_ids_filter:
                fallback_id = self.page_ids_filter.split(",")[0].strip()
            elif os.getenv("FACEBOOK_PAGE_ID"):
                fallback_id = os.getenv("FACEBOOK_PAGE_ID")
            
            if fallback_id:
                logger.info("Using fallback FACEBOOK_PAGE_ID and default Page Token for Facebook comment checks.")
                pages = [{
                    "id": fallback_id,
                    "access_token": self.access_token,
                    "name": "Fallback Page"
                }]

        filter_ids = []
        if self.page_ids_filter:
            filter_ids = [pid.strip() for pid in self.page_ids_filter.split(",") if pid.strip()]


        for page in pages:
            page_id = page["id"]
            page_name = page.get("name", "Unknown Page")
            page_token = page.get("access_token")

            if filter_ids and page_id not in filter_ids:
                continue

            logger.info(f"Checking comments for Facebook Page: '{page_name}' ({page_id})...")
            
            # Step 1: Get recent posts
            posts_url = f"{self.base_url}/{self.api_version}/{page_id}/posts"
            params = {
                "access_token": page_token,
                "limit": max_posts
            }
            try:
                posts_res = requests.get(posts_url, params=params, timeout=15)
                if posts_res.status_code != 200:
                    logger.error(f"Failed to get posts for Facebook Page '{page_name}': {posts_res.text}")
                    continue
                
                posts = posts_res.json().get("data", [])
                for post in posts:
                    post_id = post["id"]
                    # Step 2: Get comments for each post
                    comments_url = f"{self.base_url}/{self.api_version}/{post_id}/comments"
                    comments_params = {
                        "access_token": page_token,
                        "fields": "id,message,from",
                        "limit": 50
                    }
                    comments_res = requests.get(comments_url, params=comments_params, timeout=15)
                    if comments_res.status_code != 200:
                        continue
                    
                    comments = comments_res.json().get("data", [])
                    for comment in comments:
                        comment_id = comment["id"]
                        comment_msg = comment.get("message", "").strip()
                        comment_from = comment.get("from", {})
                        comment_from_id = comment_from.get("id")

                        # Skip if comment is empty or written by the Page itself
                        if not comment_msg or comment_from_id == page_id:
                            continue

                        # Check if we already replied to this comment
                        replies_url = f"{self.base_url}/{self.api_version}/{comment_id}/comments"
                        replies_params = {
                            "access_token": page_token,
                            "fields": "from",
                            "limit": 50
                        }
                        replies_res = requests.get(replies_url, params=replies_params, timeout=15)
                        already_replied = False
                        if replies_res.status_code == 200:
                            replies = replies_res.json().get("data", [])
                            for rep in replies:
                                if rep.get("from", {}).get("id") == page_id:
                                    already_replied = True
                                    break
                        
                        if already_replied:
                            continue

                        logger.info(f"Found new comment on Facebook Page '{page_name}': '{comment_msg[:50]}'")
                        reply_msg = self._generate_reply(comment_msg, platform="Facebook Page")
                        if reply_msg:
                            # Post the reply comment
                            reply_url = f"{self.base_url}/{self.api_version}/{comment_id}/comments"
                            reply_payload = {
                                "message": reply_msg,
                                "access_token": page_token
                            }
                            post_res = requests.post(reply_url, data=reply_payload, timeout=15)
                            if post_res.status_code == 200:
                                logger.info(f"SUCCESS: Replied to comment ID {comment_id} on Facebook Page '{page_name}'")
                            else:
                                logger.error(f"Failed to post Facebook reply: {post_res.text}")
            except Exception as e:
                logger.error(f"Error executing auto-reply for Facebook Page '{page_name}': {e}")

    def auto_reply_instagram(self, max_media=10):
        """
        Polls recent Instagram media posts and replies to unanswered comments.
        """
        if not self.access_token or not self.instagram_id:
            logger.warning("META_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID not set. Skipping Instagram auto-reply.")
            return

        logger.info(f"Checking comments for Instagram Business Account: {self.instagram_id}...")

        try:
            # Step 0: Fetch our Instagram username to prevent replying to ourselves
            me_url = f"{self.base_url}/{self.api_version}/{self.instagram_id}"
            me_params = {
                "fields": "username",
                "access_token": self.access_token
            }
            me_res = requests.get(me_url, params=me_params, timeout=15)
            my_username = ""
            if me_res.status_code == 200:
                my_username = me_res.json().get("username", "")

            # Step 1: Get recent media posts
            media_url = f"{self.base_url}/{self.api_version}/{self.instagram_id}/media"
            params = {
                "access_token": self.access_token,
                "limit": max_media
            }
            media_res = requests.get(media_url, params=params, timeout=15)
            if media_res.status_code != 200:
                logger.error(f"Failed to fetch Instagram media: {media_res.text}")
                return

            media_items = media_res.json().get("data", [])
            for media in media_items:
                media_id = media["id"]

                # Step 2: Fetch comments
                comments_url = f"{self.base_url}/{self.api_version}/{media_id}/comments"
                comments_params = {
                    "access_token": self.access_token,
                    "fields": "id,text,username",
                    "limit": 50
                }
                comments_res = requests.get(comments_url, params=comments_params, timeout=15)
                if comments_res.status_code != 200:
                    continue

                comments = comments_res.json().get("data", [])
                for comment in comments:
                    comment_id = comment["id"]
                    comment_text = comment.get("text", "").strip()
                    comment_user = comment.get("username", "")

                    if not comment_text or comment_user == my_username:
                        continue

                    # Check if already replied
                    replies_url = f"{self.base_url}/{self.api_version}/{comment_id}/replies"
                    replies_params = {
                        "access_token": self.access_token,
                        "fields": "id,username",
                        "limit": 50
                    }
                    replies_res = requests.get(replies_url, params=replies_params, timeout=15)
                    already_replied = False
                    if replies_res.status_code == 200:
                        replies = replies_res.json().get("data", [])
                        for rep in replies:
                            if rep.get("username") == my_username:
                                already_replied = True
                                break

                    if already_replied:
                        continue

                    logger.info(f"Found new comment on Instagram Media ID {media_id} from {comment_user}: '{comment_text[:50]}'")
                    reply_msg = self._generate_reply(comment_text, platform="Instagram Reels")
                    if reply_msg:
                        # Post reply to Instagram comment
                        reply_url = f"{self.base_url}/{self.api_version}/{comment_id}/replies"
                        reply_payload = {
                            "message": reply_msg,
                            "access_token": self.access_token
                        }
                        post_res = requests.post(reply_url, data=reply_payload, timeout=15)
                        if post_res.status_code == 200:
                            logger.info(f"SUCCESS: Replied to Instagram comment ID {comment_id}")
                        else:
                            logger.error(f"Failed to post Instagram reply: {post_res.text}")

        except Exception as e:
            logger.error(f"Error in Instagram comment auto-reply: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = SocialCommentManager()
    manager.auto_reply_facebook()
    manager.auto_reply_instagram()
