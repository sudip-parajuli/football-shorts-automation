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
from footybitez.video.video_creator import VideoCreator
from footybitez.youtube.uploader import YouTubeUploader

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
        logger.info("Starting FootyBitez Automation...")
        
        # 1. Select Topic & Category
        topic_gen = TopicGenerator()
        topic, category = topic_gen.get_random_topic()
        logger.info(f"Selected Category: {category} | Topic: {topic}")
        
        # 2. Generate Script
        script_gen = ScriptGenerator()
        script = script_gen.generate_script(topic, category)
        
        if not script:
            logger.error("Failed to generate script. Aborting.")
            return

        logger.info(f"Script Generated: {script['full_text']}")
        
        # 3. Get Visuals (Pexels)
        # 3. Get Visuals (Pexels)
        logger.info(f"Fetching media for topic: {topic}")
        media_sourcer = MediaSourcer()
        
        # 1. Fetch Title Card
        logger.info("Fetching Title Card...")
        title_card_path = media_sourcer.get_title_card_image(topic)
        
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
            paths = media_sourcer.get_media(visual_kw, count=2)
            segment_media.extend(paths)
            
        visual_assets = {
            "title_card": title_card_path,
            "profile_image": profile_image_path,
            "segment_media": segment_media
        }
        
        logger.info(f"Assets gathered. Title: {bool(title_card_path)}, Profile: {bool(profile_image_path)}, Media: {len(segment_media)}")
        
        # 3.1 Get Random Music (NEW)
        music_dir = "footybitez/music"
        background_music = None
        if os.path.exists(music_dir):
            music_files = [f for f in os.listdir(music_dir) if f.endswith('.mp3')]
            if music_files:
                selected_music = random.choice(music_files)
                background_music = os.path.join(music_dir, selected_music)
                logger.info(f"Selected Background Music: {selected_music}")

        # 4. Create Video
        video_creator = VideoCreator()
        video_path = video_creator.create_video(script, visual_assets, background_music_path=background_music)
        logger.info(f"Video Created at: {video_path}")
        
        # 5. Metadata
        title = f"{topic} #shorts #football"
        description = (
            f"You won't believe this fact about {topic}!\n\n"
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
                logger.error("Upload failed.")
        else:
            logger.info("Upload skipped (ENABLE_UPLOAD not set to true).")

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
