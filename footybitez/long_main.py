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


def assign_scene_durations(scenes: list, total_frames: int):
    """
    Distribute total_frames across scenes proportionally by narration_snippet
    word count, then enforce per-type caps/minimums and redistribute excess.
    """
    if not scenes:
        return

    # --- word-count weights ---
    word_counts = []
    for scene in scenes:
        snippet = scene.get("narration_snippet", "")
        words = max(1, len(snippet.split()) if snippet else 5)
        v = scene.get("visual_type", "image")
        if v in _DATA_TYPES:
            words = max(words, 20)      # charts need reading time
        elif v in _TEXT_TYPES:
            words = max(words, 10)
        elif v in _MG_TYPES:
            words = max(words, 8)
        word_counts.append(words)

    total_words = sum(word_counts)

    # --- first pass: proportional ---
    raw = [max(1, int((wc / total_words) * total_frames)) for wc in word_counts]

    # --- second pass: apply caps + collect excess ---
    final = list(raw)
    excess = 0
    for idx, scene in enumerate(scenes):
        v = scene.get("visual_type", "image")
        d = raw[idx]
        if v in _IMAGE_TYPES:
            if d > _MAX_IMAGE_FRAMES:
                excess += d - _MAX_IMAGE_FRAMES
                d = _MAX_IMAGE_FRAMES
        elif v in _DATA_TYPES:
            d = max(d, _MIN_DATA_FRAMES)
        elif v in _TEXT_TYPES:
            d = max(d, _MIN_TEXT_FRAMES)
        elif v in _MG_TYPES:
            d = max(d, _MIN_MG_FRAMES)
        final[idx] = max(1, d)

    # --- redistribute excess to data/text scenes ---
    if excess > 0:
        recipients = [
            i for i, s in enumerate(scenes)
            if s.get("visual_type", "image") in (_DATA_TYPES | _TEXT_TYPES | _MG_TYPES)
        ] or list(range(len(scenes)))
        extra_each = excess // len(recipients)
        remainder  = excess % len(recipients)
        for j, ridx in enumerate(recipients):
            final[ridx] += extra_each + (1 if j < remainder else 0)

    # --- assign + fix rounding diff on last scene ---
    for idx, scene in enumerate(scenes):
        scene["duration_frames"] = max(1, final[idx])

    diff = total_frames - sum(s["duration_frames"] for s in scenes)
    if diff and scenes:
        scenes[-1]["duration_frames"] = max(1, scenes[-1]["duration_frames"] + diff)


def align_scenes_with_voice_timings(scenes: list, timing_data: list, total_frames: int):
    """
    Align scenes to exact spoken word timings using sequential matching.
    """
    if not scenes:
        return
    
    if not timing_data:
        assign_scene_durations(scenes, total_frames)
        return

    # Clean punctuation helper
    def clean_w(w):
        return "".join(c.lower() for c in w if c.isalnum())

    # Prep timed words
    timed_words = []
    for t in timing_data:
        w_clean = clean_w(t.get("word", ""))
        if w_clean:
            timed_words.append({
                "word": w_clean,
                "raw_word": t.get("word", ""),
                "start": t.get("start", 0.0),
                "duration": t.get("duration", 0.0)
            })

    # If timing_data has no clean words, fallback
    if not timed_words:
        assign_scene_durations(scenes, total_frames)
        return

    # Match sequentially
    timed_idx = 0
    num_timed = len(timed_words)

    for s_idx, scene in enumerate(scenes):
        snippet = scene.get("narration_snippet", "")
        if not snippet:
            snippet_words = []
        else:
            snippet_words = [clean_w(w) for w in snippet.split() if clean_w(w)]

        start_time = None
        end_time = None
        matched_timed_words = []

        if not snippet_words:
            # Naive fallback for this specific scene: consume next few words or use current time
            if timed_idx < num_timed:
                start_time = timed_words[timed_idx]["start"]
                # Consume up to 5 words or remaining
                consume_count = min(5, num_timed - timed_idx)
                end_time = timed_words[timed_idx + consume_count - 1]["start"] + timed_words[timed_idx + consume_count - 1]["duration"]
                matched_timed_words = timed_words[timed_idx : timed_idx + consume_count]
                timed_idx += consume_count
            else:
                # No more words left
                start_time = timed_words[-1]["start"] + timed_words[-1]["duration"]
                end_time = start_time
        else:
            # Find candidate start match index
            best_match_idx = timed_idx
            min_diff = len(snippet_words)
            
            # Lookahead window of up to 15 words to handle minor omissions/insertions
            for lookahead in range(min(15, num_timed - timed_idx)):
                candidate_idx = timed_idx + lookahead
                # Calculate how many of the snippet_words match starting here
                matches = 0
                for offset in range(min(len(snippet_words), num_timed - candidate_idx)):
                    if timed_words[candidate_idx + offset]["word"] == snippet_words[offset]:
                        matches += 1
                diff = len(snippet_words) - matches
                if diff < min_diff:
                    min_diff = diff
                    best_match_idx = candidate_idx
                    if min_diff == 0:
                        break # perfect match

            # Consume matching range
            consume_len = len(snippet_words)
            end_match_idx = min(best_match_idx + consume_len, num_timed)
            
            # Extract timings
            matched_slice = timed_words[best_match_idx:end_match_idx]
            if matched_slice:
                start_time = matched_slice[0]["start"]
                end_time = matched_slice[-1]["start"] + matched_slice[-1]["duration"]
                matched_timed_words = matched_slice
                timed_idx = end_match_idx
            else:
                start_time = timed_words[min(timed_idx, num_timed - 1)]["start"]
                end_time = start_time

        # Convert times to frames
        start_frame = int(start_time * 24)
        end_frame = int(end_time * 24)
        duration_frames = max(24, end_frame - start_frame) # minimum 1 second duration
        
        scene["duration_frames"] = duration_frames
        scene["_matched_words"] = matched_timed_words

    # Resolve any rounding diffs on the last scene
    diff = total_frames - sum(s["duration_frames"] for s in scenes)
    if diff and scenes:
        scenes[-1]["duration_frames"] = max(24, scenes[-1]["duration_frames"] + diff)

    # Now populate typewriter word timestamps with exact timings relative to the start of the scene
    for scene in scenes:
        if scene.get("visual_type") == "typewriter_text":
            matched = scene.get("_matched_words", [])
            word_timestamps = []
            if matched:
                scene_start_sec = matched[0]["start"]
                for w in matched:
                    rel_start_frame = max(0, int((w["start"] - scene_start_sec) * 24))
                    word_timestamps.append({
                        "word": w["raw_word"],
                        "startFrame": rel_start_frame
                    })
            else:
                # Fallback to linear distribution if no matches
                words = scene.get("typewriter_words", [])
                num_words = len(words)
                for w_idx, w_item in enumerate(words):
                    start_frame = int((w_idx / num_words) * scene["duration_frames"])
                    word_timestamps.append({
                        "word": w_item["word"],
                        "startFrame": start_frame
                    })
            scene["word_timestamps"] = word_timestamps



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
        thumbnail_data = script_data.get("thumbnail_data", {})
        hook_phrase = thumbnail_data.get("hook_phrase", "").strip()
        
        # Read category directly from script JSON top-level field
        script_category = script_data.get("category", "").strip()
        category_map = {
            "What If?": "what_if",
            "Shocking Moments": "shocking",
            "Stats": "stats",
            "Tactics": "tactics",
        }
        t_type = category_map.get(script_category, "player") if script_category else "player"
        
        if hook_phrase:
            if hook_phrase.endswith(":"):
                hook_phrase = hook_phrase[:-1].strip()
            
            templates = {
                "what_if":   "{hook_phrase}: What History Could Have Looked Like",
                "stats":     "{hook_phrase}: The Numbers That Changed Football",
                "history":   "{hook_phrase}: The Story Nobody Told",
                "tactics":   "{hook_phrase}: How It Really Works",
                "shocking":  "{hook_phrase}: The Truth Behind the Headlines",
                "player":    "{hook_phrase}: The Career That Defined a Generation",
            }
            if t_type in templates:
                title = templates[t_type].format(hook_phrase=hook_phrase)
            else:
                title = f"{hook_phrase}: The Full Story"

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
        topic_gen.mark_topic_as_used(topic)

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
            "--video-bitrate=4000k",
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
