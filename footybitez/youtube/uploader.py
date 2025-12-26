import os
import json
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

class YouTubeUploader:
    def __init__(self, client_secrets_file="client_secret.json", token_file="token.json"):
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file
        self.scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        self.youtube = self._authenticate()

    def _authenticate(self):
        """Authenticates the user and returns the YouTube service."""
        try:
            creds = None
            
            # Check if token file exists (local run)
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
            
            # Check if token is in environment variable (GitHub Actions)
            elif os.getenv("YOUTUBE_TOKEN_JSON"):
                token_info = json.loads(os.getenv("YOUTUBE_TOKEN_JSON"))
                creds = Credentials.from_authorized_user_info(token_info, self.scopes)

            # If no valid credentials available, let the user log in (interactive, local only)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.client_secrets_file):
                         # If no client secrets file either, we can't do anything
                         print("Authentication failed: No token and no client_secret.json found.")
                         return None
                         
                    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                        self.client_secrets_file, self.scopes)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(self.token_file, "w") as token:
                    token.write(creds.to_json())

            return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

        except Exception as e:
            print(f"Auth Error: {e}")
            return None

    def upload_video(self, file_path, title, description, tags, category_id="17"):
        """Uploads a video to YouTube."""
        if not self.youtube:
            print("Cannot upload: Service not authenticated.")
            return None

        # Metadata handling
        is_short = tags and "shorts" in [t.lower() for t in tags]
        
        body = {
            "snippet": {
                "title": title[:100].replace("#shorts", "").strip() if not is_short else title[:100], # Max 100 chars
                "description": description[:5000],
                "tags": tags,
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        try:
            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=googleapiclient.http.MediaFileUpload(file_path, chunksize=-1, resumable=True)
            )
            response = request.execute()
            print(f"Uploaded Video ID: {response['id']}")
            return response['id']
            
        except googleapiclient.errors.HttpError as e:
            print(f"An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
            return None
        except Exception as e:
            print(f"Upload failed: {e}")
            return None

if __name__ == "__main__":
    # Test Stub
    pass
