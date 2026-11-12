import os
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
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

def save_publication_report(report):
    path = Path('remotion-video/output/publication-results.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    summary = os.getenv('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as target:
            target.write(f"\nDocumentary publication: **{report['status']}**. "
                         f"[YouTube video](https://www.youtube.com/watch?v={report['youtube']['id']}). "
                         f"Social status: {report['social']['status']}. "
                         "See publication-results.json in the documentary artifact.\n")


def main():
    load_dotenv()
    
    if os.getenv("ENABLE_UPLOAD_LONG") != "true":
        logger.info("Long-form upload is disabled (ENABLE_UPLOAD_LONG != true). Skipping.")
        return

    video_path = "remotion-video/output/video.mp4"
    metadata_path = "remotion-video/public/metadata.json"

    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        sys.exit(1)

    if not os.path.exists(metadata_path):
        logger.error(f"Metadata file not found: {metadata_path}")
        sys.exit(1)

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    title = metadata.get("title", "Football Documentary")
    tags = metadata.get("tags", ["football", "soccer"])
    topic = metadata.get("topic", "Football")

    narration = metadata.get('narration', '')
    summary = ' '.join(narration.split()[:100]) if narration else title
    sources = '\n'.join(metadata.get('sources', []))
    credits = '\n'.join(dict.fromkeys(metadata.get('image_credits', [])))
    description = f"{title}\n\n{summary}\n\nSources\n{sources}\n\nVisual credits\n{credits}\n\n#football #documentary #footybitez"
    if len(description) > 5000:
        raise RuntimeError('Documentary description and image attribution exceed the YouTube limit')

    logger.info(f"Starting YouTube upload for: {title}")
    
    uploader = YouTubeUploader()
    video_id = uploader.upload_video(
        file_path=video_path,
        title=title,
        description=description,
        tags=tags,
        content_text=narration or description,
        topic=topic,
        category_id="17" # Sports
    )

    if video_id:
        logger.info(f"SUCCESS: Video uploaded with ID: {video_id}")
        report = {'status':'youtube_published', 'youtube':{'id':video_id, 'status':'published'},
                  'social':{'status':'not_requested'}}
        save_publication_report(report)
        from footybitez.content.topic_generator import TopicGenerator
        TopicGenerator().mark_topic_as_used(topic)
        
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
            logger.info("Comment posted successfully (manual pinning is required).")
    else:
        raise RuntimeError("Long-form YouTube upload failed")

    # Social Publishing (Facebook, Instagram, TikTok)
    should_publish_socials = os.getenv("ENABLE_SOCIAL_PUBLISHING", "false").lower() == "true"
    if should_publish_socials:
        logger.info("Attempting long-form video upload to Meta (Facebook/Instagram) and TikTok...")
        try:
            orchestrator = SocialOrchestrator()
            results = orchestrator.publish_to_all(video_path, title, description, content_text=narration or description, topic=topic)
            report['social'] = {'status':'completed', 'results':results}
            report['status'] = 'published'
        except Exception as error:
            # The primary upload is complete. Preserve that outcome and make the
            # optional cross-post failure visible without suggesting re-upload.
            report['status'] = 'partial_success'
            report['social'] = {'status':'failed_or_needs_review', 'error_type':type(error).__name__}
            logger.warning('YouTube upload succeeded (%s); social publishing failed (%s). See publication-results.json; do not re-upload YouTube.', video_id, type(error).__name__)
        save_publication_report(report)
    else:
        logger.info("Social publishing skipped (ENABLE_SOCIAL_PUBLISHING not set to true).")


if __name__ == "__main__":
    from footybitez.content.history import DuplicateContent
    try:
        main()
    except DuplicateContent as error:
        logger.info("Skipping repeated content: %s", error)
