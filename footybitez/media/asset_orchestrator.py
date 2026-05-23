"""
asset_orchestrator.py
4-tier fallback asset fetching for the long-form football documentary pipeline.

Scene routing:
  ai_video    → Veo 3.1 → (fallback) Gemini image → Pollinations → ColorCard
  image       → Wikimedia → Unsplash → Pixabay → Gemini image → Pollinations → ColorCard
  kinetic_text → pass-through (no asset fetch needed)
  image_with_overlay → same as image, caller adds overlay text after

Never raises — always returns a valid asset dict.
Writes asset_manifest.json for debugging.
"""

import os
import json
import logging
import subprocess

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────

def fetch_asset(scene: dict, job_id: str, media_sourcer=None) -> dict:
    """
    Fetch the best available visual asset for a scene.

    Args:
        scene: Scene dict from documentary_generator visual_scenes output.
               Expected keys: visual_type, image_cue, ai_video_prompt, kinetic_stat
        job_id: Unique identifier for this pipeline run (used for temp paths).
        media_sourcer: Optional MediaSourcer instance (reuse existing downloads).

    Returns:
        Asset dict with keys:
          asset_type: "ai_video" | "image" | "kinetic_text" | "color_card"
          asset_path: file path or None
          overlay_text: text for overlays (if image_with_overlay)
          kinetic_stat: text for kinetic text slides
    """
    out_dir = os.path.join("remotion-video", "public", "assets", "temp", job_id, str(scene.get("scene_index", "0")))
    os.makedirs(out_dir, exist_ok=True)

    visual_type = scene.get("visual_type", "image")

    if visual_type == "ai_video":
        return _fetch_ai_video(scene, out_dir)

    elif visual_type in ("image", "image_with_overlay"):
        result = _fetch_image(scene, out_dir, media_sourcer)
        if visual_type == "image_with_overlay":
            result["overlay_text"] = scene.get("kinetic_stat", "")
        return result

    elif visual_type == "kinetic_text":
        return {
            "asset_type": "kinetic_text",
            "asset_path": None,
            "kinetic_stat": scene.get("kinetic_stat", ""),
            "overlay_text": None,
        }

    else:
        # Unknown type — default to image
        logger.warning(f"[Orchestrator] Unknown visual_type '{visual_type}'. Defaulting to image.")
        return _fetch_image(scene, out_dir, media_sourcer)


# ─────────────────────────────────────────────────────────────────────────────

def _fetch_ai_video(scene: dict, out_dir: str) -> dict:
    """Tier: Veo 3.1 → Gemini image → Pollinations → ColorCard"""
    from footybitez.media import quota_tracker
    from footybitez.media import football_visual_generator

    video_path = os.path.join(out_dir, "clip.mp4")
    prompt = scene.get("ai_video_prompt", "aerial drone shot over football stadium, cinematic")

    # Tier 1: Veo 3.1
    if quota_tracker.can_use("veo"):
        logger.info(f"[Orchestrator] Trying Veo 3.1 for: {prompt[:60]}...")
        success = football_visual_generator.generate_veo_clip(prompt, video_path)
        if success and _validate_video(video_path):
            quota_tracker.record_use("veo")
            logger.info("[Orchestrator] Veo 3.1 succeeded.")
            return {"asset_type": "ai_video", "asset_path": video_path, "overlay_text": None, "kinetic_stat": None}
        logger.warning("[Orchestrator] Veo 3.1 failed or invalid output. Falling back.")

    # Tier 2: Gemini image (degrade from video to still)
    img_path = os.path.join(out_dir, "ai_image.jpg")
    if quota_tracker.can_use("gemini_image"):
        logger.info("[Orchestrator] Falling back to Gemini image generation...")
        success = football_visual_generator.generate_ai_image(prompt, img_path, aspect_ratio="16:9")
        if success:
            quota_tracker.record_use("gemini_image")
            return {"asset_type": "image", "asset_path": img_path, "overlay_text": None, "kinetic_stat": None}

    # Tier 3: Pollinations
    from footybitez.media.media_sourcer import MediaSourcer
    sourcer = MediaSourcer.__new__(MediaSourcer)
    sourcer.download_dir = out_dir
    sourcer.credits_file = os.path.join(out_dir, "credits.txt")
    sourcer.gemini_keys = []
    poll_success = sourcer._fetch_pollinations_image(
        f"football stadium atmosphere cinematic, {prompt[:80]}",
        img_path
    )
    if poll_success:
        return {"asset_type": "image", "asset_path": img_path, "overlay_text": None, "kinetic_stat": None}

    # Tier 4: Color card (never crash)
    logger.warning("[Orchestrator] All video/image tiers failed. Using color card.")
    return {
        "asset_type": "color_card",
        "asset_path": None,
        "color": "#0a0a0a",
        "overlay_text": scene.get("narration_snippet", "")[:80],
        "kinetic_stat": None,
    }


def _fetch_image(scene: dict, out_dir: str, media_sourcer=None) -> dict:
    """Tier: Wikimedia → Unsplash → Pixabay → Gemini image → Pollinations → ColorCard"""
    from footybitez.media import quota_tracker, football_visual_generator

    image_cue = scene.get("image_cue", scene.get("ai_video_prompt", "football stadium"))
    img_path = os.path.join(out_dir, "image.jpg")

    # Use existing MediaSourcer if provided, else create minimal one
    if media_sourcer is None:
        from footybitez.media.media_sourcer import MediaSourcer
        media_sourcer = MediaSourcer(download_dir=out_dir)

    # Tier 1: Wikimedia
    path = media_sourcer._fetch_wikimedia_image(image_cue)
    if path:
        return {"asset_type": "image", "asset_path": path, "overlay_text": None, "kinetic_stat": None}

    # Tier 2: Unsplash
    paths = media_sourcer._fetch_unsplash_image(image_cue, count=1)
    if paths:
        return {"asset_type": "image", "asset_path": paths[0], "overlay_text": None, "kinetic_stat": None}

    # Tier 3: Pixabay
    paths = media_sourcer._fetch_pixabay_image(image_cue, count=1)
    if paths:
        return {"asset_type": "image", "asset_path": paths[0], "overlay_text": None, "kinetic_stat": None}

    # Tier 4: Gemini AI image
    if quota_tracker.can_use("gemini_image"):
        logger.info(f"[Orchestrator] Trying Gemini image for: {image_cue[:60]}...")
        success = football_visual_generator.generate_ai_image(image_cue, img_path, aspect_ratio="16:9")
        if success:
            quota_tracker.record_use("gemini_image")
            return {"asset_type": "image", "asset_path": img_path, "overlay_text": None, "kinetic_stat": None}

    # Tier 5: Pollinations
    poll_success = media_sourcer._fetch_pollinations_image(
        f"photorealistic football documentary, {image_cue}",
        img_path
    )
    if poll_success:
        return {"asset_type": "image", "asset_path": img_path, "overlay_text": None, "kinetic_stat": None}

    # Tier 6: Color card (never crash)
    logger.warning(f"[Orchestrator] All image tiers failed for: {image_cue[:60]}. Using color card.")
    return {
        "asset_type": "color_card",
        "asset_path": None,
        "color": "#111111",
        "overlay_text": image_cue[:80],
        "kinetic_stat": None,
    }


def _validate_video(path: str) -> bool:
    """
    Validates a video file using ffprobe. Returns True if valid.
    Falls back to file-size check if ffprobe unavailable.
    """
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < 10000:
        logger.warning(f"[Orchestrator] Video too small ({os.path.getsize(path)} bytes): {path}")
        return False
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15
        )
        codec = result.stdout.strip()
        if codec:
            logger.info(f"[Orchestrator] ffprobe validated video codec: {codec}")
            return True
        else:
            logger.warning(f"[Orchestrator] ffprobe found no video stream in: {path}")
            return False
    except FileNotFoundError:
        logger.warning("[Orchestrator] ffprobe not found — skipping codec validation, using size check only.")
        return True
    except Exception as e:
        logger.warning(f"[Orchestrator] ffprobe error: {e}")
        return os.path.getsize(path) > 50000


def write_manifest(job_id: str, assets: list):
    """
    Writes asset_manifest.json for debugging and downstream consumers.

    Args:
        job_id: Pipeline run identifier.
        assets: List of asset dicts returned by fetch_asset().
    """
    manifest_path = os.path.join("remotion-video", "public", "assets", "temp", job_id, "asset_manifest.json")
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, 'w') as f:
        json.dump({"job_id": job_id, "assets": assets}, f, indent=2, default=str)
    logger.info(f"[Orchestrator] Manifest written: {manifest_path}")
