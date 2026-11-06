import os
import sys
from PIL import Image

# Monkeypatch for MoviePy 1.0.3 compatibility with Pillow 10+
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS
import logging
import random
from datetime import datetime
from dotenv import load_dotenv

# Ensure the project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from footybitez.content.topic_generator import TopicGenerator
from footybitez.content.script_generator import ScriptGenerator
from footybitez.media.media_sourcer import MediaSourcer
from footybitez.video.remotion_video_creator import RemotionVideoCreator
from footybitez.youtube.uploader import YouTubeUploader
from footybitez.socials.social_orchestrator import SocialOrchestrator


# Setup Logging
os.makedirs("footybitez/logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"footybitez/logs/automation_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    load_dotenv()
    
    try:
        from footybitez.video.preflight import require_media_tools
        require_media_tools()
        logger.info("Starting FootyBitez Automation...")
        
        # 1-2. Select Topic & Generate Script (With Retry Logic)
        topic_gen = TopicGenerator()
        script_gen = ScriptGenerator()
        
        script = None
        for attempt in range(1, 4):
            topic, category = topic_gen.get_random_topic()
            logger.info(f"Attempt {attempt}/3 - Selected Category: {category} | Topic: {topic}")
            
            script = script_gen.generate_script(topic, category)
            if script:
                break
            logger.warning(f"Script generation failed or was rejected for topic '{topic}'. Retrying...")
            
        if not script:
            logger.error("Failed to generate a valid script after 3 attempts. Aborting.")
            raise RuntimeError("All topics failed editorial quality checks")

        import json
        os.makedirs("footybitez/output", exist_ok=True)
        with open("footybitez/output/script.json", "w", encoding="utf-8") as report:
            json.dump({"topic": topic, "category": category, "script": script}, report, indent=2)
        logger.info(f"Script Generated: {script['full_text']}")
        # 3. Get Visuals (Pexels)
        logger.info(f"Fetching media for topic: {topic}")
        media_sourcer = MediaSourcer()
        
        # 1. Fetch Title Card
        logger.info("Fetching Title Card...")
        title_card_path = media_sourcer.get_title_card_image(topic, allow_ai=False)
        
        # Replace a generic emergency title card with the actual hook graphic.
        if not title_card_path or os.path.basename(title_card_path).startswith("card_"):
            from footybitez.media.editorial_cards import make_beat_cards
            title_card_path = make_beat_cards(topic, script["hook"], media_sourcer.download_dir)[0]

        # 2. Fetch Profile Image
        entity_query = script.get('primary_entity')
        if not entity_query:
            logger.info("No primary_entity found in script, falling back to topic.")
            entity_query = topic
            
        logger.info(f"Fetching Profile Image for: {entity_query}")
        profile_image_path = media_sourcer.get_profile_image(entity_query)
        
        # 2.1 Last resort: Reuse Title Card if Profile Image fails
        if not profile_image_path and title_card_path:
            logger.info("No Profile Image found. Reusing Title Card.")
            profile_image_path = title_card_path
        
        # 3. Fetch Segment Media (Dynamic)
        segment_media = []
        logger.info("Fetching Dynamic Segment Media...")
        
        # Extract keywords from script segments
        segments = script.get('segments', [])
        for seg in segments:
            # Handle dict vs string (legacy support)
            visual_kw = topic + " football"
            if isinstance(seg, dict):
                visual_kw = seg.get('visual_keyword', visual_kw)
            
            # Fetch 2-3 clips/images per segment
            logger.info(f"Searching for visual: {visual_kw}")
            paths = media_sourcer.get_media(visual_kw, count=3)
            segment_media.append(paths) # Append list of paths for this segment
            
        visual_assets = {
            "title_card": title_card_path,
            "profile_image": profile_image_path,
            "segment_media": segment_media # Now a list of lists [[p1, p2], [p3, p4]...]
        }
        
        logger.info(f"Assets gathered. Title: {bool(title_card_path)}, Profile: {bool(profile_image_path)}, Media: {len(segment_media)}")
        
        # 3.1 Get Random Music (NEW)
        from footybitez.media.music_selector import select_music
        background_music = select_music(script.get("music_mood", "neutral"))

        # 4. Create Video
        video_creator = RemotionVideoCreator()
        video_path = video_creator.create_video(script, visual_assets, background_music_path=background_music)
        logger.info(f"Video Created at: {video_path}")
        
        # 5. Metadata
        title = str(script.get("title") or topic).strip()[:100]
        description = (
            f"{title}\n\n"
            f"{script['full_text']}\n\n"
            "#football #soccer #didyouknow #footybitez #shorts"
        )
        tags = ["football", "soccer", "shorts", "footybitez", "facts"]
        
        # 6. Upload (Optional flag)
        # Check for upload flag or environment variable, default to True if API available
        # But we need to be careful not to spam if testing.
        should_upload = os.getenv("ENABLE_UPLOAD", "false").lower() == "true"
        
        if should_upload:
            logger.info("Attempting upload to YouTube...")
            uploader = YouTubeUploader()
            video_id = uploader.upload_video(video_path, title, description, tags)
            if video_id:
                logger.info(f"Successfully uploaded video: {video_id}")
            else:
                raise RuntimeError("YouTube upload failed")
        else:
            logger.info("Upload skipped (ENABLE_UPLOAD not set to true).")

        # 6.1 Publish to Social Platforms (Facebook, Instagram, TikTok)
        should_publish_socials = os.getenv("ENABLE_SOCIAL_PUBLISHING", "false").lower() == "true"
        if should_publish_socials:
            logger.info("Attempting upload to Meta (Facebook/Instagram) and TikTok...")
            orchestrator = SocialOrchestrator()
            orchestrator.publish_to_all(video_path, title, description)
        else:
            logger.info("Social publishing skipped (ENABLE_SOCIAL_PUBLISHING not set to true).")


        # 7. Cleanup (NEW)
        logger.info("Starting cleanup of temporary assets...")
        media_sourcer.cleanup()
        
        # Cleanup temp_text folder
        temp_text_path = os.path.join("footybitez/output", "temp_text")
        if os.path.exists(temp_text_path):
            import shutil
            shutil.rmtree(temp_text_path)
            os.makedirs(temp_text_path, exist_ok=True)
            logger.info("Cleaned up temp_text directory.")

        logger.info("Workflow completed successfully.")
        
    except Exception as e:
        logger.error(f"Critical workflow error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
