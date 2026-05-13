import os
import sys
import json
import logging
import argparse
import subprocess
import random
from datetime import datetime
from dotenv import load_dotenv

# Ensure the project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from footybitez.content.topic_generator import TopicGenerator
from footybitez.content.documentary_generator import DocumentaryGenerator
from footybitez.media.media_sourcer import MediaSourcer
from footybitez.media.voice_generator import VoiceGenerator
from footybitez.media.thumbnail_generator import ThumbnailGenerator

# Setup Logging
os.makedirs("footybitez/logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"footybitez/logs/documentary_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_audio_duration(file_path):
    """Gets audio duration using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Error getting duration for {file_path}: {e}")
        return 0

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="FootyBitez Documentary Pipeline")
    parser.add_argument("--topic", help="Topic for the documentary")
    args = parser.parse_args()

    try:
        logger.info("Starting FootyBitez Documentary Production Pipeline...")
        
        # 1. Select Topic
        topic_gen = TopicGenerator()
        if args.topic:
            topic = args.topic
            category = "Manual"
        else:
            topic, category = topic_gen.get_random_topic()
        
        logger.info(f"Selected Topic: {topic} ({category})")

        # 2. Generate Documentary Script (Gemini with Groq Fallback)
        doc_gen = DocumentaryGenerator()
        script_data = doc_gen.generate_script(topic)
        if not script_data:
            logger.error("Failed to generate script. Aborting.")
            sys.exit(1)
        
        logger.info(f"Script Generated: {script_data['title']}")

        # 3. Setup Sourcing
        media_dir = "remotion-video/public/assets/images"
        os.makedirs(media_dir, exist_ok=True)
        media_sourcer = MediaSourcer(download_dir=media_dir)
        
        # 4. Generate Content per Chapter
        voice_gen = VoiceGenerator(output_dir="remotion-video/public/assets/audio")
        voice_index = script_data.get('suggested_voice_index', 0)
        chapters_props = []
        
        for i, chapter in enumerate(script_data['chapters']):
            logger.info(f"Processing Chapter {i+1}: {chapter['chapter_title']}...")
            
            # A. Audio
            audio_filename = f"chapter_{i+1}_{hash(topic)}.mp3"
            audio_path = voice_gen.generate(chapter['script'], audio_filename, voice_index=voice_index)
            duration_sec = get_audio_duration(audio_path)
            duration_frames = int(duration_sec * 24)
            
            # B. Strictly Linked Images
            chapter_images = []
            queries = chapter.get('image_queries', [])
            if not queries:
                # Fallback to chapter title if no queries provided
                queries = [f"{topic} {chapter['chapter_title']} soccer"]
            
            for j, query in enumerate(queries):
                logger.info(f"  Sourcing chapter-linked image: {query}")
                img_assets = media_sourcer.get_media_for_script([query])
                img_path = img_assets.get("image_0")
                if img_path:
                    rel_path = os.path.relpath(img_path, "remotion-video/public")
                    chapter_images.append(rel_path.replace("\\", "/"))

            chapters_props.append({
                "chapter_number": i + 1,
                "chapter_title": chapter['chapter_title'],
                "script": chapter['script'],
                "duration_in_frames": duration_frames,
                "audio_path": f"assets/audio/{audio_filename}",
                "images": chapter_images
            })

        # 5. Generate Thumbnail
        thumb_gen = ThumbnailGenerator()
        bg_query = script_data.get('thumbnail_query', f"{topic} soccer cinematic")
        thumb_assets = media_sourcer.get_media_for_script([], thumbnail_query=bg_query)
        bg_path = thumb_assets.get('thumbnail')
        if bg_path:
            logger.info("Generating professional thumbnail...")
            thumb_gen.generate_thumbnail(bg_path, script_data['title'], "remotion-video/public/thumbnail.jpg")

        # 6. Prepare Props for Remotion
        music_file = None
        music_dir = "footybitez/music"
        if os.path.exists(music_dir):
            files = [f for f in os.listdir(music_dir) if f.endswith('.mp3')]
            if files:
                music_file = f"music/{random.choice(files)}"

        image_credits = []
        credits_file = os.path.join(media_sourcer.download_dir, "image_credits.txt")
        if os.path.exists(credits_file):
            with open(credits_file, "r", encoding="utf-8") as f:
                image_credits = [line.strip() for line in f if line.strip()]

        props = {
            "chapters": chapters_props,
            "background_music": music_file,
            "image_credits": image_credits,
            "quiz": script_data.get('quiz', None)
        }

        with open("remotion-video/public/props.json", "w", encoding="utf-8") as f:
            json.dump(props, f, indent=2)
            
        # Save Metadata for Uploader
        metadata = {
            "title": script_data['title'],
            "tags": script_data.get('tags', ["football", "documentary"]),
            "topic": topic
        }
        with open("remotion-video/public/metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("Props and Metadata generated for Remotion. Content phase COMPLETE.")
        topic_gen.mark_topic_as_used(topic)

    except Exception as e:
        logger.error(f"Critical error in documentary pipeline: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
