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
        
        from footybitez.video.remotion_video_creator import MissingVisualError
        tried = set()
        had_script = False
        for attempt in range(1, 4):
            topic, category = topic_gen.get_random_topic()
            if topic in tried:
                continue
            tried.add(topic)
            logger.info("Attempt %s/3: %s", attempt, topic)
            script = script_gen.generate_script(topic, category)
            if not script:
                continue
            had_script = True
            import json
            os.makedirs("footybitez/output", exist_ok=True)
            with open("footybitez/output/script.json", "w", encoding="utf-8") as report:
                json.dump({"topic": topic, "category": category, "script": script}, report, indent=2)
            logger.info(f"Script Generated: {script['full_text']}")
            # 3. Get Visuals (Pexels)
            logger.info(f"Fetching media for topic: {topic}")
            media_sourcer = MediaSourcer()
        
            from footybitez.media.real_assets import segment_real_media
            segment_media = []
            for index, segment in enumerate(script.get("segments", [])):
                paths = segment_real_media(media_sourcer, segment, script, index)
                segment_media.append(paths)
                logger.info("Segment %s: %s real photos/clips", index + 1, len(paths))
            # Spend the limited media budget on the actual story first. The opening
            # uses a relevant story asset, not a broad keyword-search title card.
            title_card_path = next((path for pool in segment_media for path in pool if path), None)
            profile_image_path = title_card_path

            visual_assets = {
                "title_card": title_card_path,
                "profile_image": profile_image_path,
                "segment_media": segment_media # Now a list of lists [[p1, p2], [p3, p4]...]
            }
            from footybitez.media.football_assets import scene_club_logos
            visual_assets['club_logos'] = list(dict.fromkeys(path for segment in script.get('segments',[])
                for path in scene_club_logos(media_sourcer,segment)))[:2]
        
            logger.info(f"Assets gathered. Title: {bool(title_card_path)}, Profile: {bool(profile_image_path)}, Media: {len(segment_media)}")
        
            # 3.1 Get Random Music (NEW)
            from footybitez.media.music_selector import select_music
            background_music = select_music(script.get("music_mood", "neutral"))

            # 4. Create Video
            video_creator = RemotionVideoCreator()
            try:
                video_path = video_creator.create_video(script, visual_assets, background_music_path=background_music)
            except MissingVisualError as error:
                logger.warning("Skipping %s: %s", topic, error)
                media_sourcer.cleanup()
                continue
            break
        else:
            if not had_script:
                raise RuntimeError("All candidate topics failed editorial or research checks")
            logger.warning("No topic had both a grounded script and relevant visuals. Skipping upload.")
            if os.getenv("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                    output.write("skipped=true\n")
            return
        logger.info("Video created at %s", video_path)

        # 5. Metadata
        title = str(script.get("title") or topic).strip()[:100]
        description = (
            f"{title}\n\n"
            f"{script['full_text']}\n\n"
            "#football #soccer #didyouknow #footybitez #shorts"
        )
        tags = ["football", "soccer", "shorts", "footybitez", "facts"]
        if os.path.isfile(media_sourcer.credits_file):
            description += '\n\nVisual credits:\n' + open(media_sourcer.credits_file,encoding='utf-8').read()
        
        # 6. Upload (Optional flag)
        # Check for upload flag or environment variable, default to True if API available
        # But we need to be careful not to spam if testing.
        should_upload = os.getenv("ENABLE_UPLOAD", "false").lower() == "true"
        if should_upload or os.getenv('ENABLE_SOCIAL_PUBLISHING','false').lower()=='true':
            with open(os.path.join(video_creator.output_dir,'visual-coverage.json'),encoding='utf-8') as report:
                coverage=json.load(report)
            if coverage['media_fraction'] < float(os.getenv('MIN_REAL_MEDIA_FRACTION','0.25')):
                raise RuntimeError('Real photos/footage cover less than the required part of this Short; keeping preview instead of publishing an all-diagram video')
        
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
