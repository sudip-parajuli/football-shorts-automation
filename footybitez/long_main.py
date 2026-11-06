import os
import sys
import json
import uuid
import logging
import argparse
import subprocess
import random
import shutil
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



# ── Duration assignment constants ────────────────────────────────────────────
_FPS = 24
_MAX_IMAGE_FRAMES = 4 * _FPS    # 4 s hard cap for any image scene (updated per request)
_MIN_DATA_FRAMES  = 3 * _FPS    # 3 s minimum for charts/leaderboards
_MIN_TEXT_FRAMES  = 2 * _FPS    # 2 s minimum for kinetic/typewriter scenes
_MIN_MG_FRAMES    = int(1.2 * _FPS)  # 1.2 s minimum for motion_graphic (snappier)

_IMAGE_TYPES = {"image", "image_tag", "ai_video", "ai_image"}
_DATA_TYPES  = {"leaderboard", "head_to_head", "timeline", "data_visualization", "data_bars"}
_TEXT_TYPES  = {"typewriter_text", "kinetic_stat", "hook_question"}
_MG_TYPES    = {"motion_graphic"}

_KB_STYLES = [
    "zoom_in_center", "pan_left", "zoom_out_center", "pan_right",
    "zoom_in_topleft", "pan_diagonal", "tilt_up", "tilt_down",
]


from footybitez.video.scene_timing import assign_scene_durations, align_scenes_with_voice_timings


def _split_long_image_scenes(visual_scenes: list) -> list:
    """
    After duration assignment, split any image scene still > MAX_IMAGE_FRAMES
    (can happen if excess redistribution pushed the last scene over the cap)
    into sub-scenes reusing the same asset but with a different Ken Burns style.
    Also inserts a 'flash' transition between sub-scenes.
    """
    expanded = []
    kb_idx = 0
    for scene in visual_scenes:
        v = scene.get("visual_type", "image")
        d = scene.get("duration_frames", _MAX_IMAGE_FRAMES)
        if v in _IMAGE_TYPES and d > _MAX_IMAGE_FRAMES:
            num_splits = -(-d // _MAX_IMAGE_FRAMES)   # ceil division
            frames_each = d // num_splits
            remainder   = d - frames_each * num_splits
            for s_idx in range(num_splits):
                sub = dict(scene)
                sub["duration_frames"] = frames_each + (remainder if s_idx == num_splits - 1 else 0)
                sub["ken_burns_style"] = _KB_STYLES[kb_idx % len(_KB_STYLES)]
                if s_idx > 0:
                    sub["transition"] = "flash"
                kb_idx += 1
                expanded.append(sub)
        else:
            if v in _IMAGE_TYPES:
                # Ensure ken_burns_style is cycled globally
                if not scene.get("ken_burns_style"):
                    scene["ken_burns_style"] = _KB_STYLES[kb_idx % len(_KB_STYLES)]
                kb_idx += 1
            expanded.append(scene)
    return expanded


def _pad_short_visual_coverage(visual_scenes: list, target_frames: int) -> list:
    """
    If image caps cause total scene duration to fall below target_frames,
    insert duplicate image scenes (with new Ken Burns styles) to fill the gap.
    Only called when the gap is significant (> 1 second).
    """
    total = sum(s.get("duration_frames", 0) for s in visual_scenes)
    gap   = target_frames - total
    if gap < _FPS:   # < 1 second — ignore
        return visual_scenes

    image_pool = [s for s in visual_scenes if s.get("visual_type") in _IMAGE_TYPES]
    if not image_pool:
        return visual_scenes

    result = list(visual_scenes)
    kb_idx = len(result)
    pool_idx = 0
    while gap >= _FPS:
        base = image_pool[pool_idx % len(image_pool)]
        new_dur = min(gap, _MAX_IMAGE_FRAMES)
        sub = dict(base)
        sub["duration_frames"]  = new_dur
        sub["ken_burns_style"]  = _KB_STYLES[kb_idx % len(_KB_STYLES)]
        sub["transition"]       = "flash"
        sub["caption"]          = None    # suppress caption on duplicates
        sub["named_entity"]     = None
        result.append(sub)
        gap     -= new_dur
        kb_idx  += 1
        pool_idx += 1

    return result


def _fetch_chapter_visuals(chapter: dict, job_id: str, media_sourcer: MediaSourcer, media_dir: str, topic: str) -> tuple:
    """
    Fetches visual assets for a single chapter using the AssetOrchestrator when
    visual_scenes data is present, otherwise falls back to image_queries.

    Returns: (list of relative image paths, list of visual scene props)
    """
    chapter_images = []
    visual_scenes_props = []

    # --- Path A: Use visual_scenes from DocumentaryGenerator output ---
    visual_scenes = chapter.get("visual_scenes", [])
    if visual_scenes:
        logger.info(f"  Chapter has {len(visual_scenes)} visual scenes — using AssetOrchestrator.")
        try:
            from footybitez.media import asset_orchestrator
            for scene_idx, scene in enumerate(visual_scenes):
                scene["scene_index"] = scene_idx

                # Fetch asset (pass-through for non-image types)
                asset = asset_orchestrator.fetch_asset(scene, job_id, media_sourcer, topic=topic)

                # Build scene prop object
                scene_prop = {
                    "visual_type": scene["visual_type"],
                    "transition":  scene["transition"],
                }
                if scene['visual_type']=='motion_graphic':
                    from footybitez.media.football_assets import scene_club_logos
                    scene_prop['club_logos']=[]
                    for path in scene_club_logos(media_sourcer,scene):
                        target=os.path.join('remotion-video/public/assets/images',os.path.basename(path))
                        os.makedirs(os.path.dirname(target),exist_ok=True)
                        shutil.copy2(path,target)
                        scene_prop['club_logos'].append(os.path.relpath(target,'remotion-video/public').replace('\\','/'))

                # Copy all relevant generator fields
                for field in [
                    "typewriter_words", "word_timestamps", "stat_data",
                    "question_text", "emphasis_phrase",
                    "bar_data", "named_entity", "ken_burns_style", "caption",
                    "leaderboard_data", "head_to_head_data",
                    "timeline_data", "timeline_title",
                    # motion_graphic fields
                    "motion_style", "accent_color", "motion_label",
                    "counter_value", "counter_unit",
                    # named_entities needed for pipeline logic
                    "named_entities",
                ]:
                    if field in scene:
                        scene_prop[field] = scene[field]

                if asset.get("asset_path"):
                    rel_path = os.path.relpath(
                        asset["asset_path"], "remotion-video/public"
                    ).replace("\\", "/")
                    scene_prop["asset_path"] = rel_path
                    chapter_images.append(rel_path)

                    if asset["asset_type"] == "ai_video":
                        scene_prop["asset_type"] = "video"
                    else:
                        scene_prop["asset_type"] = "image"
                else:
                    v_type = scene["visual_type"]
                    scene_prop["asset_type"] = (
                        "image_fallback" if v_type == "ai_video" else "image"
                    )
                    placeholder = "assets/images/placeholder.jpg"
                    scene_prop["asset_path"] = placeholder
                    if v_type not in ("motion_graphic", "typewriter_text",
                                     "kinetic_stat", "hook_question",
                                     "data_bars", "data_visualization",
                                     "leaderboard", "head_to_head", "timeline"):
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
    from footybitez.video.preflight import require_media_tools
    require_media_tools()
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
            used_topics = topic_gen._load_used_topics()
            if topic.lower() in used_topics:
                logger.warning(f"Topic '{topic}' has already been processed. Skipping.")
                sys.exit(0)
        else:
            topic, category = topic_gen.get_random_topic()

        logger.info(f"Selected Topic: {topic} ({category})")

        # Pre-flight SFX generation - ensure all sound effects exist
        from footybitez.media.sfx_manager import SFXManager
        sfx_out_dir = "remotion-video/public/assets/sounds"
        os.makedirs(sfx_out_dir, exist_ok=True)
        try:
            sfx_man = SFXManager(sfx_dir=sfx_out_dir)
            sfx_mapping = {
                "whoosh": "whoosh",
                "impact": "impact",
                "rise": "rise",
                "kick": "kick",
                "crowd_cheer": "riser_shake",
                "transition": "whoosh",
                "drum": "kick",
            }
            for sfx_file, sfx_gen in sfx_mapping.items():
                out_path = os.path.join(sfx_out_dir, f"{sfx_file}.mp3")
                if not os.path.exists(out_path):
                    logger.info(f"Pre-flight SFX generation: {sfx_file}")
                    clip = sfx_man.get_sfx(sfx_gen)
                    clip.write_audiofile(out_path, fps=44100, logger=None)
        except Exception as e:
            logger.warning(f"Pre-flight SFX check failed: {e}")

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
        voice_gen = VoiceGenerator(output_dir="remotion-video/public/assets/audio", key_pool="long_form")
        voice_index = script_data.get("suggested_voice_index", 0)
        chapters_props = []

        for i, chapter in enumerate(script_data["chapters"]):
            logger.info(f"--- Chapter {i+1}/{len(script_data['chapters'])}: {chapter['chapter_title']} ---")

            # A. Audio
            audio_filename = f"chapter_{i+1}_{hash(topic)}.mp3"
            audio_path = voice_gen.generate(chapter["script"], audio_filename, voice_index=voice_index)
            duration_sec = get_audio_duration(audio_path)
            if duration_sec <= 0.1:
                raise ValueError(f"Missing narration for chapter {i+1}")
            duration_frames = round(duration_sec * 24)

            # B. Visual Assets (orchestrated with fallback chain)
            chapter_images, visual_scenes_props = _fetch_chapter_visuals(chapter, job_id, media_sourcer, media_dir, topic)

            if not chapter_images and not visual_scenes_props:
                raise ValueError(f"Chapter {i+1} has no usable visuals")

            # Distribute scene durations and generate typewriter timestamps
            if visual_scenes_props:
                # Load exact word timing JSON from voice generator output
                json_path = audio_path.replace(".mp3", ".json")
                timing_data = []
                if os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            timing_data = json.load(f)
                    except Exception as e:
                        logger.warning(f"Failed to load timing JSON {json_path}: {e}")

                if timing_data:
                    align_scenes_with_voice_timings(visual_scenes_props, timing_data, duration_frames)
                else:
                    assign_scene_durations(visual_scenes_props, duration_frames)
                    # Fallback to linear typewriter timestamps if no timing data
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

        if ai_prompt and os.getenv("ENABLE_AI_THUMBNAILS", "false").lower() == "true":
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
                thumb_text = script_data.get("thumbnail_data", {}).get("hook_phrase") or script_data["title"]
                thumb_text = " ".join(thumb_text.replace(":", "").split()[:5])
                thumb_gen.generate_thumbnail(bg_path, thumb_text, thumb_out)

        # 6. Prepare Remotion Props
        music_file = None
        music_dir = "footybitez/music"
        public_music_dir = "remotion-video/public/music"
        os.makedirs(public_music_dir, exist_ok=True)
        from footybitez.media.music_selector import select_music
        chosen = select_music(script_data.get("music_mood", "neutral"))
        if chosen:
            import shutil
            safe_dest = os.path.join(public_music_dir, os.path.basename(chosen))
            shutil.copy2(chosen, safe_dest)
            music_file = f"music/{os.path.basename(chosen)}"

        image_credits = []
        credits_file = os.path.join(media_sourcer.download_dir, "image_credits.txt")
        if os.path.exists(credits_file):
            with open(credits_file, "r", encoding="utf-8") as f:
                image_credits = [line.strip() for line in f if line.strip()]

        logger.info("Setting up sound effects...")
        sfx_out_dir = "remotion-video/public/assets/sounds"
        os.makedirs(sfx_out_dir, exist_ok=True)
        sound_effects = {}
        
        try:
            sfx_manager = SFXManager(sfx_dir=sfx_out_dir)
            
            sfx_mapping = {
                "whoosh": "whoosh",
                "transition": "whoosh",
                "rise": "rise",
                "impact": "impact",
                "drum": "kick",
                "crowd_cheer": "riser_shake"
            }
            
            for sfx_key, gen_name in sfx_mapping.items():
                out_path = os.path.join(sfx_out_dir, f"{sfx_key}.mp3")
                if not os.path.exists(out_path):
                    logger.info(f"Generating SFX: {sfx_key} at {out_path}")
                    clip = sfx_manager.get_sfx(gen_name)
                    clip.write_audiofile(out_path, fps=44100, logger=None)
                sound_effects[sfx_key] = f"assets/sounds/{sfx_key}.mp3"
        except Exception as e:
            logger.error(f"Error setting up sound effects: {e}")

        props = {
            "chapters": chapters_props,
            "background_music": music_file,
            "image_credits": image_credits,
            "quiz": script_data.get("quiz", None),
            "sound_effects": sound_effects,
        }

        with open("remotion-video/public/props.json", "w", encoding="utf-8") as f:
            json.dump(props, f, indent=2)

        # Save Metadata for Uploader with template titles
        title = script_data["title"]
        metadata = {
            "title": title,
            "tags": script_data.get("tags", ["football", "documentary"]),
            "topic": topic,
        }
        with open("remotion-video/public/metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info("=" * 60)
        logger.info("Props and Metadata generated. Content phase COMPLETE.")
        logger.info(f"Job ID: {job_id}")
        logger.info("=" * 60)


        # 7. Render Video via Remotion CLI
        import platform
        import shutil
        logger.info("Starting Remotion render step...")
        cmd = [
            "npx", "remotion", "render",
            "src/index.ts", "MainVideo",
            "output/video.mp4",
            "--props=public/props.json",
            "--concurrency=1",
            "--timeout=60000",
            "--video-bitrate=8000k",
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
            
            from footybitez.video.preflight import inspect_video
            report = inspect_video("remotion-video/output/video.mp4")
            with open("remotion-video/output/quality.json", "w", encoding="utf-8") as f:
                json.dump({"script": script_data, "render": report}, f, indent=2)
            topic_gen.mark_topic_as_used(topic)

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
