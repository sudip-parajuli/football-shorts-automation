import os
import json
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv

# Ensure the project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from footybitez.youtube.uploader import YouTubeUploader
from footybitez.youtube.comment_manager import CommentManager
from footybitez.socials.social_orchestrator import SocialOrchestrator


# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    load_dotenv()
    
    if os.getenv("ENABLE_UPLOAD_LONG") != "true":
        logger.info("Long-form upload is disabled (ENABLE_UPLOAD_LONG != true). Skipping.")
        return

    video_path = "remotion-video/output/video.mp4"
    metadata_path = "remotion-video/public/metadata.json"

    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return

    if not os.path.exists(metadata_path):
        logger.error(f"Metadata file not found: {metadata_path}")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    title = metadata.get("title", "Football Documentary")
    tags = metadata.get("tags", ["football", "soccer"])
    topic = metadata.get("topic", "Football")

    description = f"""
{title}

Explore the world of football with FootyBitez! ⚽️
In this episode, we dive deep into: {topic}

If you enjoyed this documentary, please Like and Subscribe for more high-quality football stories.

#football #soccer #documentary #footybitez #footballhistory
"""

    logger.info(f"Starting YouTube upload for: {title}")
    
    uploader = YouTubeUploader()
    video_id = uploader.upload_video(
        file_path=video_path,
        title=title,
        description=description,
        tags=tags,
        category_id="17" # Sports
    )

    if video_id:
        logger.info(f"SUCCESS: Video uploaded with ID: {video_id}")
        
        # Upload custom thumbnail if exists
        thumbnail_path = "remotion-video/public/thumbnail.jpg"
        if os.path.exists(thumbnail_path):
            logger.info(f"Uploading custom thumbnail from: {thumbnail_path}...")
            if uploader.set_thumbnail(video_id, thumbnail_path):
                logger.info("Custom thumbnail uploaded successfully.")
            else:
                logger.warning("Custom thumbnail upload failed.")
        
        # Auto-pin a comment
        comment_manager = CommentManager()
        comment_text = "Which football legend should we cover next? Let us know in the comments! 👇"
        if comment_manager.pin_comment(video_id, comment_text):
            logger.info("Comment pinned successfully.")
    else:
        logger.error("Upload FAILED.")

    # Social Publishing (Facebook, Instagram, TikTok)
    should_publish_socials = os.getenv("ENABLE_SOCIAL_PUBLISHING", "false").lower() == "true"
    if should_publish_socials:
        logger.info("Attempting long-form video upload to Meta (Facebook/Instagram) and TikTok...")
        orchestrator = SocialOrchestrator()
        orchestrator.publish_to_all(video_path, title, description)
    else:
        logger.info("Social publishing skipped (ENABLE_SOCIAL_PUBLISHING not set to true).")


if __name__ == "__main__":
    main()
