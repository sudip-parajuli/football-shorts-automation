import os
import sys
import json
import uuid
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
from footybitez.media.sound_downloader import download_sound_effects

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
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Error getting duration for {file_path}: {e}")
        return 0


def _fetch_chapter_visuals(chapter: dict, job_id: str, media_sourcer: MediaSourcer, media_dir: str) -> list:
    """
    Fetches visual assets for a single chapter using the AssetOrchestrator when
    visual_scenes data is present, otherwise falls back to image_queries.

    Returns: list of relative image paths (relative to remotion-video/public)
    """
    chapter_images = []

    # --- Path A: Use visual_scenes from new DocumentaryGenerator output ---
    visual_scenes = chapter.get("visual_scenes", [])
    if visual_scenes:
        logger.info(f"  Chapter has {len(visual_scenes)} visual scenes — using AssetOrchestrator.")
        try:
            from footybitez.media import asset_orchestrator
            assets_fetched = []
            for scene_idx, scene in enumerate(visual_scenes):
                scene["scene_index"] = scene_idx
                asset = asset_orchestrator.fetch_asset(scene, job_id, media_sourcer)
                assets_fetched.append(asset)

                if asset["asset_type"] in ("image", "ai_video") and asset.get("asset_path"):
                    path = asset["asset_path"]
                    if os.path.exists(path):
                        rel = os.path.relpath(path, "remotion-video/public")
                        chapter_images.append(rel.replace("\\", "/"))
                elif asset["asset_type"] == "kinetic_text":
                    # Kinetic text scenes are tracked in asset manifest — no image path needed
                    logger.info(f"  Scene {scene_idx}: kinetic_text — '{asset.get('kinetic_stat', '')}'")

            # Write manifest for this chapter
            asset_orchestrator.write_manifest(job_id, assets_fetched)

        except Exception as e:
            logger.warning(f"  AssetOrchestrator failed: {e}. Falling back to image_queries.")
            visual_scenes = []  # Force fallback

    # --- Path B: Legacy image_queries fallback ---
    if not visual_scenes or not chapter_images:
        queries = chapter.get("image_queries", [])
        if not queries:
            queries = [f"{chapter.get('chapter_title', 'football')} soccer"]

        for j, query in enumerate(queries):
            logger.info(f"  Sourcing image [{j+1}/{len(queries)}]: {query}")
            img_assets = media_sourcer.get_media_for_script([query])
            img_path = img_assets.get("image_0")
            if img_path and os.path.exists(img_path):
                rel = os.path.relpath(img_path, "remotion-video/public")
                chapter_images.append(rel.replace("\\", "/"))

    return chapter_images


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="FootyBitez Documentary Pipeline")
    parser.add_argument("--topic", help="Topic for the documentary")
    args = parser.parse_args()

    # Unique job ID for asset manifest and temp directories
    job_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    try:
        logger.info("=" * 60)
        logger.info(f"Starting FootyBitez Documentary Pipeline [job={job_id}]")
        logger.info("=" * 60)

        # 1. Select Topic
        topic_gen = TopicGenerator()
        if args.topic:
            topic = args.topic
            category = "Manual"
        else:
            topic, category = topic_gen.get_random_topic()

        logger.info(f"Selected Topic: {topic} ({category})")

        # 2. Generate Documentary Script
        doc_gen = DocumentaryGenerator()
        script_data = doc_gen.generate_script(topic)
        if not script_data:
            logger.error("Failed to generate script. Aborting.")
            sys.exit(1)

        logger.info(f"Script Generated: {script_data['title']}")

        # 3. Setup Media Sourcing
        media_dir = "remotion-video/public/assets/images"
        os.makedirs(media_dir, exist_ok=True)
        media_sourcer = MediaSourcer(download_dir=media_dir)

        # Log quota status at start
        try:
            from footybitez.media.quota_tracker import get_status
            logger.info(f"Gemini Quota Status: {get_status()}")
        except Exception:
            pass

        # 4. Generate Voice + Visuals per Chapter
        voice_gen = VoiceGenerator(output_dir="remotion-video/public/assets/audio")
        voice_index = script_data.get("suggested_voice_index", 0)
        chapters_props = []

        for i, chapter in enumerate(script_data["chapters"]):
            logger.info(f"--- Chapter {i+1}/{len(script_data['chapters'])}: {chapter['chapter_title']} ---")

            # A. Audio
            audio_filename = f"chapter_{i+1}_{hash(topic)}.mp3"
            audio_path = voice_gen.generate(chapter["script"], audio_filename, voice_index=voice_index)
            duration_sec = get_audio_duration(audio_path)
            duration_frames = int(duration_sec * 24)

            # B. Visual Assets (orchestrated with fallback chain)
            chapter_images = _fetch_chapter_visuals(chapter, job_id, media_sourcer, media_dir)

            # Guard: ensure at least 1 image per chapter
            if not chapter_images:
                logger.warning(f"  Chapter {i+1}: No images sourced — using color card placeholder.")
                placeholder = os.path.join(media_dir, "placeholder.jpg")
                if not os.path.exists(placeholder):
                    try:
                        from PIL import Image
                        Image.new("RGB", (1920, 1080), color=(10, 10, 10)).save(placeholder)
                    except Exception:
                        pass
                chapter_images = ["assets/images/placeholder.jpg"]

            chapters_props.append({
                "chapter_number": i + 1,
                "chapter_title": chapter["chapter_title"],
                "script": chapter["script"],
                "duration_in_frames": duration_frames,
                "audio_path": f"assets/audio/{audio_filename}",
                "images": chapter_images,
            })

        # 5. Generate Thumbnail (AI → PIL fallback)
        thumb_gen = ThumbnailGenerator()
        thumb_out = "remotion-video/public/thumbnail.jpg"
        ai_prompt = script_data.get("thumbnail_prompt")
        thumb_generated = False

        if ai_prompt:
            logger.info("Attempting AI thumbnail generation with Gemini...")
            result = thumb_gen.generate_ai_thumbnail(ai_prompt, thumb_out)
            if result:
                logger.info(f"AI Thumbnail saved to {thumb_out}")
                thumb_generated = True

        if not thumb_generated:
            logger.info("Falling back to PIL thumbnail generation...")
            bg_query = script_data.get("thumbnail_query", f"{topic} soccer cinematic")
            thumb_assets = media_sourcer.get_media_for_script([], thumbnail_query=bg_query)
            bg_path = thumb_assets.get("thumbnail")
            if bg_path:
                thumb_gen.generate_thumbnail(bg_path, script_data["title"], thumb_out)

        # 6. Prepare Remotion Props
        music_file = None
        music_dir = "footybitez/music"
        public_music_dir = "remotion-video/public/music"
        os.makedirs(public_music_dir, exist_ok=True)
        if os.path.exists(music_dir):
            files = [f for f in os.listdir(music_dir) if f.endswith(".mp3")]
            if files:
                import shutil, re
                chosen = random.choice(files)
                safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", chosen)
                safe_dest = os.path.join(public_music_dir, safe_name)
                shutil.copy2(os.path.join(music_dir, chosen), safe_dest)
                music_file = f"music/{safe_name}"

        image_credits = []
        credits_file = os.path.join(media_sourcer.download_dir, "image_credits.txt")
        if os.path.exists(credits_file):
            with open(credits_file, "r", encoding="utf-8") as f:
                image_credits = [line.strip() for line in f if line.strip()]

        logger.info("Downloading sound effects...")
        sound_effects = download_sound_effects()

        props = {
            "chapters": chapters_props,
            "background_music": music_file,
            "image_credits": image_credits,
            "quiz": script_data.get("quiz", None),
            "sound_effects": sound_effects,
        }

        with open("remotion-video/public/props.json", "w", encoding="utf-8") as f:
            json.dump(props, f, indent=2)

        # Save Metadata for Uploader
        metadata = {
            "title": script_data["title"],
            "tags": script_data.get("tags", ["football", "documentary"]),
            "topic": topic,
        }
        with open("remotion-video/public/metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info("=" * 60)
        logger.info("Props and Metadata generated. Content phase COMPLETE.")
        logger.info(f"Job ID: {job_id}")
        logger.info("=" * 60)
        topic_gen.mark_topic_as_used(topic)

    except Exception as e:
        logger.error(f"Critical error in documentary pipeline: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
