"""
asset_orchestrator.py
4-tier fallback asset fetching for the long-form football documentary pipeline.

Scene routing:
  ai_video    → Veo 3.1 → (fallback) Gemini image → Pollinations → ColorCard
  ai_image    → Tactical Diagram (if applicable) or Gemini image → Pollinations → ColorCard
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
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────

def _validate_no_ai_faces(scenes: list) -> list:
    """
    Ensure no scene asks for AI generation of named real people or their faces.
    If a scene is classified as ai_video or ai_image for a named player/coach,
    downgrade it to "image" (real photo search) instead.
    """
    for scene in scenes:
        if scene.get("visual_type") in ["ai_video", "ai_image"]:
            # Check if the prompt mentions a named player or coach
            prompt = scene.get("ai_video_prompt", scene.get("ai_image_prompt", ""))
            
            # List of named entities that should NEVER be AI-generated
            real_people = scene.get("named_entities", [])
            for entity in real_people:
                if entity.get("name", "").lower() in prompt.lower():
                    # Named person in AI generation request — downgrade to image
                    scene["visual_type"] = "image"
                    scene["image_cue"] = f"{entity['name']} {scene.get('topic', '')}"
                    break
    
    return scenes

def _enforce_schema(scene: dict, topic: str) -> dict:
    valid_types = {
        "typewriter_text", "kinetic_stat", "image", "image_tag", "ai_image", "ai_video",
        "hook_question", "data_bars", "data_visualization", "leaderboard", "head_to_head",
        "timeline", "motion_graphic"
    }
    
    # Temporarily stash topic inside scene for validation
    scene["topic"] = topic
    
    # Map legacy names if generated
    v_type = scene.get("visual_type", "image")
    if v_type == "kinetic_text":
        v_type = "typewriter_text"
    elif v_type == "image_with_overlay":
        v_type = "image"
        
    if v_type not in valid_types:
        v_type = "image"
        
    scene["visual_type"] = v_type
    
    # Never allow None image_cue
    if not scene.get("image_cue"):
        scene["image_cue"] = f"{topic} football"

    # Downgrade kinetic_stat to typewriter if stat_data missing
    if scene["visual_type"] == "kinetic_stat" and not scene.get("stat_data"):
        scene["visual_type"] = "typewriter_text"

    # Default emphasis_phrase for hook_question
    if scene["visual_type"] == "hook_question":
        if not scene.get("question_text"):
            scene["question_text"] = scene.get("narration_snippet", "What was the truth?")
        q = scene.get("question_text", "")
        if not scene.get("emphasis_phrase"):
            words = q.split()
            scene["emphasis_phrase"] = " ".join(words[-3:]) if len(words) >= 3 else q

    # Default typewriter_words if missing
    if scene["visual_type"] == "typewriter_text" and not scene.get("typewriter_words"):
        narration = scene.get("narration_snippet", scene.get("narration", ""))
        words = narration.split() if narration else ["Football", "History"]
        scene["typewriter_words"] = [
            {"word": w, "weight": "lg" if idx % 5 == 0 else "md"}
            for idx, w in enumerate(words)
        ]

    if not scene.get("transition"):
        scene["transition"] = "cut"

    # Validate no AI faces
    scene = _validate_no_ai_faces([scene])[0]

    return scene

def _add_image_credit_overlay(image_path: str, source: str, artist: str = None) -> str:
    """
    Add a small credit overlay to images showing source and artist.
    Positioned: bottom-right corner.
    Saves to image_credited.jpg instead of overwriting original.
    """
    try:
        if not image_path or not os.path.exists(image_path):
            return image_path
            
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        
        credit_text = f"📷 {source}"
        if artist and str(artist).strip() and str(artist).strip() != "Unknown":
            if f"/ {artist}" not in source:
                credit_text += f" / {artist}"
                
        font_path = "remotion-video/public/assets/fonts/BarlowCondensed-Bold.ttf"
        font = None
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, 14)
            except Exception:
                pass
        if not font:
            font = ImageFont.load_default()
            
        bbox = draw.textbbox((0, 0), credit_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        box_width = text_w + 20
        box_height = text_h + 16
        
        x = img.width - box_width - 15
        y = img.height - box_height - 15
        
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle([x, y, x + box_width, y + box_height], fill=(10, 10, 20, 200))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        
        draw = ImageDraw.Draw(img)
        draw.text((x + 10, y + 8), credit_text, font=font, fill=(200, 200, 200))
        
        base, ext = os.path.splitext(image_path)
        credited_path = f"{base}_credited.jpg"
        img.save(credited_path, "JPEG", quality=95)
        logger.info(f"[Overlay] Saved credited image: {credited_path}")
        return credited_path
    except Exception as e:
        logger.error(f"[Overlay] Failed to add credit overlay to {image_path}: {e}")
        return image_path

# ─────────────────────────────────────────────────────────────────────────────

def fetch_asset(scene: dict, job_id: str, media_sourcer=None, topic: str = "") -> dict:
    """
    Fetch the best available visual asset for a scene.
    """
    scene = _enforce_schema(scene, topic)
    out_dir = os.path.join("remotion-video", "public", "assets", "temp", job_id, str(scene.get("scene_index", "0")))
    os.makedirs(out_dir, exist_ok=True)

    visual_type = scene.get("visual_type", "image")
    result = None

    if visual_type == "ai_video":
        result = _fetch_ai_video(scene, out_dir, media_sourcer)
    elif visual_type == "ai_image":
        result = _fetch_ai_image(scene, out_dir)
    elif visual_type in ("image", "image_tag", "image_with_overlay"):
        result = _fetch_image(scene, out_dir, media_sourcer)
        if visual_type == "image_with_overlay":
            result["overlay_text"] = scene.get("kinetic_stat", "")
    elif visual_type in ("kinetic_text", "typewriter_text", "kinetic_stat", "hook_question", "data_bars", "data_visualization", "leaderboard", "head_to_head", "timeline", "motion_graphic"):
        result = {
            "asset_type": visual_type,
            "asset_path": None,
            "kinetic_stat": scene.get("kinetic_stat", ""),
            "overlay_text": None,
        }
    else:
        logger.warning(f"[Orchestrator] Unknown visual_type '{visual_type}'. Defaulting to image.")
        result = _fetch_image(scene, out_dir, media_sourcer)

    # Apply image credit overlay if it's an image
    if result.get("asset_path") and result.get("asset_type") == "image":
        img_path = result["asset_path"]
        meta_path = img_path + ".json"
        source = "Unknown Source"
        artist = ""
        
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    source = meta.get("source", source)
                    artist = meta.get("artist", "")
            except Exception:
                pass
                
        credited_path = _add_image_credit_overlay(img_path, source, artist)
        result["asset_path"] = credited_path

    return result

# ─────────────────────────────────────────────────────────────────────────────

def _fetch_ai_video(scene: dict, out_dir: str, media_sourcer=None) -> dict:
    """Tier: Pexels Video B-roll → Veo 3.1 → Gemini image → Pollinations → ColorCard"""
    from footybitez.media import quota_tracker
    from footybitez.media import football_visual_generator

    video_path = os.path.join(out_dir, "clip.mp4")
    prompt = scene.get("ai_video_prompt", "aerial drone shot over football stadium, cinematic")

    # Tier 0: Pexels Video B-roll
    if media_sourcer is not None:
        clean_kw = prompt.replace("cinematic", "").replace("slow motion", "").replace("aerial drone shot", "")
        clean_kw = clean_kw.replace(",", " ").strip()
        words = [w for w in clean_kw.split() if w.lower() not in ["and", "or", "the", "a", "of", "with", "over", "in"]]
        search_query = " ".join(words[:4])
        if not search_query:
            search_query = "football soccer"
        
        logger.info(f"[Orchestrator] Trying Pexels Video for search query: '{search_query}'...")
        success = media_sourcer.fetch_pexels_video(search_query, video_path)
        if success and _validate_video(video_path):
            logger.info("[Orchestrator] Pexels Video B-roll succeeded.")
            return {"asset_type": "ai_video", "asset_path": video_path, "overlay_text": None, "kinetic_stat": None}
        logger.warning("[Orchestrator] Pexels Video search failed or returned nothing. Trying next tier.")

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
            _write_meta(img_path, "AI Generated / Google Gemini")
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
        _write_meta(img_path, "AI Generated / Pollinations.ai")
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

def _fetch_ai_image(scene: dict, out_dir: str) -> dict:
    """Tier: Tactical Diagram (if tactical keywords) or standard AI Image → Pollinations → ColorCard"""
    from footybitez.media import quota_tracker, football_visual_generator
    
    img_path = os.path.join(out_dir, "ai_image.jpg")
    prompt = scene.get("ai_image_prompt", scene.get("image_cue", "football tactics diagram"))
    
    prompt_lower = prompt.lower()
    is_tactical = any(k in prompt_lower for k in ["tactical", "diagram", "formation", "heat map", "heatmap", "passing", "pressure", "gegenpressing", "tiki-taka", "comparison", "stat"])
    
    if quota_tracker.can_use("gemini_image"):
        success = False
        if is_tactical:
            diagram_type = "formation"
            if "heat map" in prompt_lower or "heatmap" in prompt_lower:
                diagram_type = "heat_map"
            elif "passing" in prompt_lower or "tiki-taka" in prompt_lower:
                diagram_type = "passing_lanes"
            elif "pressure" in prompt_lower or "gegenpressing" in prompt_lower:
                diagram_type = "pressure_map"
            elif "comparison" in prompt_lower or "stat" in prompt_lower:
                diagram_type = "comparison_chart"
                
            logger.info(f"[Orchestrator] Generating tactical diagram ({diagram_type}) for: {prompt[:60]}")
            success = football_visual_generator.generate_tactical_diagram(prompt, diagram_type, img_path)
            
        if not success:
            logger.info(f"[Orchestrator] Generating standard AI image for: {prompt[:60]}")
            success = football_visual_generator.generate_ai_image(prompt, img_path, aspect_ratio="16:9")
            
        if success:
            quota_tracker.record_use("gemini_image")
            _write_meta(img_path, "AI Generated / Google Gemini")
            return {"asset_type": "image", "asset_path": img_path, "overlay_text": None, "kinetic_stat": None}
            
    # Pollinations fallback
    from footybitez.media.media_sourcer import MediaSourcer
    sourcer = MediaSourcer.__new__(MediaSourcer)
    sourcer.download_dir = out_dir
    sourcer.credits_file = os.path.join(out_dir, "credits.txt")
    sourcer.gemini_keys = []
    poll_success = sourcer._fetch_pollinations_image(
        f"football tactical analysis diagram, {prompt[:80]}",
        img_path
    )
    if poll_success:
        _write_meta(img_path, "AI Generated / Pollinations.ai")
        return {"asset_type": "image", "asset_path": img_path, "overlay_text": None, "kinetic_stat": None}
        
    logger.warning("[Orchestrator] All AI image tiers failed. Using color card.")
    return {
        "asset_type": "color_card",
        "asset_path": None,
        "color": "#111111",
        "overlay_text": prompt[:80],
        "kinetic_stat": None,
    }

def _fetch_image(scene: dict, out_dir: str, media_sourcer=None) -> dict:
    """Tier: Wikimedia → Unsplash → Pixabay → Gemini image → Pollinations → ColorCard"""
    from footybitez.media import quota_tracker, football_visual_generator

    image_cue = scene.get("image_cue", scene.get("ai_video_prompt", "football stadium"))
    img_path = os.path.join(out_dir, "image.jpg")

    if media_sourcer is None:
        from footybitez.media.media_sourcer import MediaSourcer
        media_sourcer = MediaSourcer(download_dir=out_dir)

    # Tier 0: Wikipedia Entity Lookup
    named_entities = scene.get("named_entities", [])
    for entity in named_entities:
        if isinstance(entity, dict) and entity.get("wikipedia_lookup") is True:
            entity_name = entity.get("name")
            if entity_name:
                logger.info(f"[Orchestrator] Performing Wikipedia entity image lookup for: '{entity_name}'")
                path = media_sourcer.get_wikipedia_entity_image(entity_name)
                if path:
                    logger.info(f"[Orchestrator] Wikipedia entity image succeeded: {path}")
                    return {"asset_type": "image", "asset_path": path, "overlay_text": None, "kinetic_stat": None}
                logger.warning(f"[Orchestrator] Wikipedia entity lookup failed for '{entity_name}'. Falling back.")

    path = media_sourcer._fetch_wikimedia_image(image_cue)
    if path:
        return {"asset_type": "image", "asset_path": path, "overlay_text": None, "kinetic_stat": None}

    paths = media_sourcer._fetch_unsplash_image(image_cue, count=1)
    if paths:
        return {"asset_type": "image", "asset_path": paths[0], "overlay_text": None, "kinetic_stat": None}

    paths = media_sourcer._fetch_pixabay_image(image_cue, count=1)
    if paths:
        return {"asset_type": "image", "asset_path": paths[0], "overlay_text": None, "kinetic_stat": None}

    if quota_tracker.can_use("gemini_image"):
        logger.info(f"[Orchestrator] Trying Gemini image for: {image_cue[:60]}...")
        success = football_visual_generator.generate_ai_image(image_cue, img_path, aspect_ratio="16:9")
        if success:
            quota_tracker.record_use("gemini_image")
            _write_meta(img_path, "AI Generated / Google Gemini")
            return {"asset_type": "image", "asset_path": img_path, "overlay_text": None, "kinetic_stat": None}

    poll_success = media_sourcer._fetch_pollinations_image(
        f"photorealistic football documentary, {image_cue}",
        img_path
    )
    if poll_success:
        _write_meta(img_path, "AI Generated / Pollinations.ai")
        return {"asset_type": "image", "asset_path": img_path, "overlay_text": None, "kinetic_stat": None}

    logger.warning(f"[Orchestrator] All image tiers failed for: {image_cue[:60]}. Using color card.")
    return {
        "asset_type": "color_card",
        "asset_path": None,
        "color": "#111111",
        "overlay_text": image_cue[:80],
        "kinetic_stat": None,
    }

def _write_meta(img_path: str, source: str, artist: str = ""):
    try:
        with open(img_path + ".json", "w", encoding="utf-8") as f:
            json.dump({"source": source, "artist": artist}, f)
    except Exception as e:
        logger.warning(f"Failed to write metadata for {img_path}: {e}")

def _validate_video(path: str) -> bool:
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
    manifest_path = os.path.join("remotion-video", "public", "assets", "temp", job_id, "asset_manifest.json")
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, 'w') as f:
        json.dump({"job_id": job_id, "assets": assets}, f, indent=2, default=str)
    logger.info(f"[Orchestrator] Manifest written: {manifest_path}")
