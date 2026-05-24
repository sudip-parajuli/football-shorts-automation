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



def assign_scene_durations(scenes: list, total_frames: int):
    if not scenes:
        return
    
    word_counts = []
    for scene in scenes:
        snippet = scene.get("narration_snippet", "")
        words = len(snippet.split()) if snippet else 5
        word_counts.append(words)
        
    total_words = sum(word_counts)
    if total_words == 0:
        total_words = len(scenes)
        word_counts = [1] * len(scenes)
        
    allocated_frames = 0
    for idx, scene in enumerate(scenes):
        pct = word_counts[idx] / total_words
        duration = int(pct * total_frames)
        scene["duration_frames"] = duration
        allocated_frames += duration
        
    diff = total_frames - allocated_frames
    if diff != 0 and scenes:
        scenes[-1]["duration_frames"] = max(1, scenes[-1]["duration_frames"] + diff)


def _fetch_chapter_visuals(chapter: dict, job_id: str, media_sourcer: MediaSourcer, media_dir: str, topic: str) -> tuple:
    """
    Fetches visual assets for a single chapter using the AssetOrchestrator when
    visual_scenes data is present, otherwise falls back to image_queries.

    Returns: (list of relative image paths, list of visual scene props)
    """
    chapter_images = []
    visual_scenes_props = []

    # --- Path A: Use visual_scenes from new DocumentaryGenerator output ---
    visual_scenes = chapter.get("visual_scenes", [])
    if visual_scenes:
        logger.info(f"  Chapter has {len(visual_scenes)} visual scenes — using AssetOrchestrator.")
        try:
            from footybitez.media import asset_orchestrator
            for scene_idx, scene in enumerate(visual_scenes):
                scene["scene_index"] = scene_idx
                
                # Fetch asset
                asset = asset_orchestrator.fetch_asset(scene, job_id, media_sourcer)
                
                # Create scene prop object
                scene_prop = {
                    "visual_type": scene["visual_type"],
                    "transition": scene["transition"],
                }
                
                # Copy relevant generator fields
                for field in ["typewriter_words", "word_timestamps", "stat_data", "question_text", "emphasis_phrase", "bar_data", "named_entity", "ken_burns_style", "caption"]:
                    if field in scene:
                        scene_prop[field] = scene[field]
                
                if asset.get("asset_path"):
                    rel_path = os.path.relpath(asset["asset_path"], "remotion-video/public").replace("\\", "/")
                    scene_prop["asset_path"] = rel_path
                    chapter_images.append(rel_path)
                    
                    if asset["asset_type"] == "ai_video":
                        scene_prop["asset_type"] = "video"
                    else:
                        scene_prop["asset_type"] = "image"
                else:
                    scene_prop["asset_type"] = "image_fallback" if scene["visual_type"] == "ai_video" else "image"
                    # Default placeholder if image failed to download
                    placeholder = "assets/images/placeholder.jpg"
                    scene_prop["asset_path"] = placeholder
                    chapter_images.append(placeholder)
                    
                visual_scenes_props.append(scene_prop)

        except Exception as e:
            logger.warning(f"  AssetOrchestrator failed: {e}. Falling back to image_queries.")
            visual_scenes_props = []

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

    return chapter_images, visual_scenes_props


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
            chapter_images, visual_scenes_props = _fetch_chapter_visuals(chapter, job_id, media_sourcer, media_dir, topic)

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

            # Distribute scene durations and generate typewriter timestamps
            if visual_scenes_props:
                assign_scene_durations(visual_scenes_props, duration_frames)
                for scene in visual_scenes_props:
                    if scene["visual_type"] == "typewriter_text" and not scene.get("word_timestamps"):
                        words = scene.get("typewriter_words", [])
                        num_words = len(words)
                        if num_words > 0:
                            word_timestamps = []
                            for w_idx, w_item in enumerate(words):
                                start_frame = int((w_idx / num_words) * scene["duration_frames"])
                                word_timestamps.append({
                                    "word": w_item["word"],
                                    "startFrame": start_frame
                                })
                            scene["word_timestamps"] = word_timestamps

            chapter_data = {
                "chapter_number": i + 1,
                "chapter_title": chapter["chapter_title"],
                "script": chapter["script"],
                "duration_in_frames": duration_frames,
                "audio_path": f"assets/audio/{audio_filename}",
                "images": chapter_images,
            }
            if visual_scenes_props:
                chapter_data["visual_scenes"] = visual_scenes_props

            chapters_props.append(chapter_data)

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

        logger.info("Setting up offline sound effects...")
        sound_effects = {
            "whoosh": "assets/sounds/whoosh.mp3",
            "transition": "assets/sounds/transition.mp3",
            "rise": "assets/sounds/rise.mp3",
            "impact": "assets/sounds/impact.mp3",
            "drum": "assets/sounds/drum.mp3",
            "crowd_cheer": "assets/sounds/crowd_cheer.mp3"
        }

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

        # 7. Render Video via Remotion CLI
        import platform
        import shutil
        logger.info("Starting Remotion render step...")
        # Concurrency=1 renders one frame at a time — prevents Chrome OOM crashes on low-RAM machines.
        # Timeout=60000 gives each frame up to 60s to render (default is 30s).
        cmd = [
            "npx", "remotion", "render",
            "src/index.ts", "MainVideo",
            "output/video.mp4",
            "--props=public/props.json",
            "--concurrency=1",
            "--timeout=60000",
        ]

        remotion_dir = "remotion-video"
        if platform.system() != "Windows":
            import shlex
            cmd_str = shlex.join(cmd)
            logger.info("Linux/Mac detected. Using shlex joined command.")
        else:
            cmd_str = " ".join(cmd)
            
        logger.info(f"Executing rendering command in {remotion_dir}: {cmd_str}")
        
        try:
            process = subprocess.run(
                cmd_str,
                cwd=remotion_dir,
                check=True,
                shell=True,
                capture_output=True,
                text=True
            )
            if process.stdout:
                logger.info(f"Remotion Render Output: {process.stdout}")
            if process.stderr:
                logger.warning(f"Remotion Render Warnings/Errors: {process.stderr}")
                
            logger.info("Remotion rendering completed successfully (exit code 0).")
            
            # Clean up temp assets on success
            temp_dir = os.path.join("remotion-video", "public", "assets", "temp", job_id)
            if os.path.exists(temp_dir):
                logger.info(f"Cleaning up temporary assets: {temp_dir}")
                shutil.rmtree(temp_dir)
            else:
                logger.info(f"No temp directory found to clean up: {temp_dir}")
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Remotion Render Failed (Code {e.returncode})")
            logger.error(f"RENDER STDOUT: {e.stdout}")
            logger.error(f"RENDER STDERR: {e.stderr}")
            logger.warning(f"Keeping temporary assets in remotion-video/public/assets/temp/{job_id}/ for debugging.")
            raise Exception(f"Remotion failed to render video: {e.stderr}")

    except Exception as e:
        logger.error(f"Critical error in documentary pipeline: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
