import os
import json
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import googleapiclient.discovery
import googleapiclient.errors
import google_auth_oauthlib.flow
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

class CommentManager:
    def __init__(self, client_secrets_file="client_secret.json", token_file="token.json"):
        self.scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]
        self.youtube = self._authenticate(client_secrets_file, token_file)
        
        # Configure Gemini for reply generation
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")

    def _authenticate(self, client_secrets_file, token_file):
        """Authenticates and returns the YouTube service."""
        try:
            creds = None
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, self.scopes)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(client_secrets_file):
                        logger.error("No client_secret.json found.")
                        return None
                    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                        client_secrets_file, self.scopes)
                    creds = flow.run_local_server(port=0)
                
                with open(token_file, "w") as token:
                    token.write(creds.to_json())

            return googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        except Exception as e:
            logger.error(f"YouTube Auth Error: {e}")
            return None

    def auto_reply(self, video_id=None, max_replies=10):
        """
        Fetches recent top-level unanswered comments and replies to them.
        """
        if not self.youtube:
            logger.error("YouTube service not initialized.")
            return

        try:
            # 1. Fetch comments
            params = {
                "part": "snippet",
                "maxResults": 50,
                "moderationStatus": "published",
                "order": "time"
            }
            if video_id:
                params["videoId"] = video_id
            else:
                params["allThreadsRelatedToChannelId"] = self._get_channel_id()

            results = self.youtube.commentThreads().list(**params).execute()
            
            replied_count = 0
            for item in results.get("items", []):
                if replied_count >= max_replies:
                    break
                
                thread_id = item["id"]
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comment_text = snippet["textDisplay"]
                author = snippet["authorDisplayName"]
                
                # Check if we already replied (simple check: has any replies?)
                # More robust check: check replies list for our own authorId
                if item["snippet"]["totalReplyCount"] > 0:
                    continue
                
                logger.info(f"Generating reply for comment from {author}: {comment_text[:50]}...")
                
                # 2. Generate Reply with Gemini
                reply_text = self._generate_reply(comment_text)
                
                if reply_text:
                    # 3. Post Reply
                    self._post_reply(thread_id, reply_text)
                    replied_count += 1
                    logger.info(f"Replied to {author}.")
            
            logger.info(f"Auto-reply finished. Total replies posted: {replied_count}")

        except Exception as e:
            logger.error(f"Error in auto_reply: {e}")

    def _get_channel_id(self):
        """Helper to get own channel ID."""
        res = self.youtube.channels().list(part="id", mine=True).execute()
        return res["items"][0]["id"]

    def _generate_reply(self, comment_text):
        """Uses Gemini to generate an engaging, fan-style reply."""
        prompt = f"""
        You are the creator of a popular football documentary channel. 
        A viewer left this comment on your video: "{comment_text}"
        
        Write a short (max 2 sentences), engaging, and appreciative reply. 
        Use a "Fan's Voice" — be opinionated but respectful, use football slang if appropriate. 
        If they ask a question, answer it if possible, otherwise be encouraging.
        
        REPLY:
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini reply generation failed: {e}")
            return None

    def _post_reply(self, parent_id, text):
        """Posts a reply to a comment thread."""
        try:
            body = {
                "snippet": {
                    "parentId": parent_id,
                    "textOriginal": text
                }
            }
            self.youtube.comments().insert(part="snippet", body=body).execute()
        except Exception as e:
            logger.error(f"Failed to post reply: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = CommentManager()
    # manager.auto_reply() # Be careful running this
