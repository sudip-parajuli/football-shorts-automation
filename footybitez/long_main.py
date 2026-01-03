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
from footybitez.content.long_form_script_generator import LongFormScriptGenerator
from footybitez.media.media_sourcer import MediaSourcer
from footybitez.video.long_form_video_creator import LongFormVideoCreator
from footybitez.youtube.uploader import YouTubeUploader

# Setup Logging
os.makedirs("footybitez/logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"footybitez/logs/long_form_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def create_chapters_text(script_data):
    """Generates YouTube chapters string."""
    chapters = []
    current_offset = 0
    
    # Intro
    chapters.append(f"00:00 - Intro")
    # Intro duration is roughly word_count / 2.5 (estimate)
    # This is a very rough estimate, in a perfect world we'd get actual audio durations
    current_offset += 10 # Intro is usually ~10s
    
    for i, chapter in enumerate(script_data['chapters']):
        minutes = int(current_offset // 60)
        seconds = int(current_offset % 60)
        chapters.append(f"{minutes:02d}:{seconds:02d} - {chapter['chapter_title']}")
        # Estimate chapter duration: 6 facts * 10s = 60s?
        current_offset += len(chapter['facts']) * 12 
        
    return "\n".join(chapters)

def main():
    load_dotenv()
    
    try:
        logger.info("Starting FootyBitez LONG-FORM Automation...")
        
        # 1. Select Topic
        topic_gen = TopicGenerator()
        topic = topic_gen.get_random_topic()
        logger.info(f"Selected Topic: {topic}")
        
        # 2. Generate Long Script
        script_gen = LongFormScriptGenerator()
        script = script_gen.generate_long_script(topic)
        
        if not script:
            logger.error("Failed to generate long script. Aborting.")
            return

        logger.info(f"Long Script Generated: {script['metadata']['title']}")
        
        # 3. Gather Visual Assets
        media_sourcer = MediaSourcer()
        logger.info(f"Fetching media for topic: {topic}")
        
        # For long-form, we need MORE media.
        segment_media = []
        # Pull 5 media items for the topic generally
        segment_media.extend(media_sourcer.get_media(topic, count=10, orientation='landscape'))
        
        # Pull 2 items for each chapter visual keyword
        for chapter in script['chapters'][:3]: # Limit to first few to save API
            for fact in chapter['facts'][:2]:
                 segment_media.extend(media_sourcer.get_media(fact['visual_keyword'], count=1, orientation='landscape'))

        visual_assets = {
            "segment_media": segment_media
        }
        
        # 4. Music
        music_dir = "footybitez/music"
        background_music = None
        if os.path.exists(music_dir):
            music_files = [f for f in os.listdir(music_dir) if f.endswith('.mp3')]
            if music_files:
                background_music = os.path.join(music_dir, random.choice(music_files))

        # 5. Create Video
        video_creator = LongFormVideoCreator()
        video_path = video_creator.create_long_video(script, visual_assets, background_music_path=background_music)
        logger.info(f"Long Video Created at: {video_path}")
        
        # 6. Metadata
        metadata = script['metadata']
        chapters_text = create_chapters_text(script)
        
        title = metadata['title']
        description = (
            f"{metadata['description']}\n\n"
            f"Chapters:\n{chapters_text}\n\n"
            f"#football #soccer #footybitez #documentary"
        )
        tags = metadata.get('tags', []) + ["football", "soccer", "documentary"]
        
        # 7. Upload
        should_upload = os.getenv("ENABLE_UPLOAD_LONG", "false").lower() == "true"
        if should_upload:
            logger.info("Attempting upload to YouTube...")
            uploader = YouTubeUploader()
            video_id = uploader.upload_video(video_path, title, description, tags)
            if video_id:
                logger.info(f"Successfully uploaded long-form video: {video_id}")
                # Mark topic as used to prevent repetition
                topic_gen.mark_topic_as_used(topic)
                logger.info(f"Topic '{topic}' marked as used.")
            else:
                logger.error("Upload failed.")
        
        # 8. Cleanup
        media_sourcer.cleanup()
        
        logger.info("Long-form Workflow completed.")
        
    except Exception as e:
        logger.error(f"Critical long-form error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
