"""
football_visual_generator.py
Veo 3.1 + Gemini image generation for the long-form football documentary pipeline.

Uses new google-genai SDK (google-genai>=1.0.0).
All functions return True/False — never raise. Callers handle fallback chains.

AI VIDEO RULES (enforce at prompt level):
  ✅ Stadium atmospheres, crowd energy, abstract sport moods, rain/fog/lighting, generic pitch views
  ❌ NEVER: named players, specific match moments, historical events, club-specific kits/badges
"""

import os
import io
import time
import logging
import re

logger = logging.getLogger(__name__)


def _get_gemini_keys() -> list:
    keys = []
    for suffix in ["", "2", "3"]:
        val = os.getenv(f"GEMINI_API_KEY{suffix}")
        if val:
            keys.append(val)
    return keys


def handle_429_sleep(err_msg: str) -> float:
    """
    Parses the retryDelay value from error response.
    Supports both 'Please retry in 27.613595891s' and 'retryDelay: 27s' or similar.
    Sleeps for the parsed duration and returns it. If 429/quota error is detected
    but not parsed, sleeps for a default 30s.
    """
    delay = 0.0
    
    # 1. Parse 'Please retry in 27.61s'
    match1 = re.search(r"Please retry in ([0-9.]+)\s*s", err_msg, re.IGNORECASE)
    if match1:
        try:
            delay = float(match1.group(1))
        except ValueError:
            pass
            
    # 2. Parse 'retryDelay: 27s' or 'retryDelay': '27s'
    if delay == 0.0:
        match2 = re.search(r"retryDelay[\"']?\s*:\s*[\"']?([0-9.]+)\s*s", err_msg, re.IGNORECASE)
        if match2:
            try:
                delay = float(match2.group(1))
            except ValueError:
                pass
                
    if delay > 0.0:
        logger.warning(f"[Gemini API] Rate limited (429). Sleeping for exactly {delay} seconds.")
        time.sleep(delay)
        return delay
    elif any(term in err_msg.lower() for term in ["429", "resourceexhausted", "quota", "limit"]):
        logger.warning("[Gemini API] Rate limited (429) but could not parse retryDelay. Sleeping 30s fallback.")
        time.sleep(30.0)
        return 30.0
        
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# VEO 3.0 VIDEO GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def generate_veo_clip(prompt: str, output_path: str, duration_seconds: int = 8) -> bool:
    """
    Disabled due to Veo 3.x models requiring paid GCP billing (March 2026).
    Forces orchestrator fallback to Gemini Image or Pollinations.
    """
    logger.warning("[Veo] Veo 3.x API requires paid billing. Disabling and forcing fallback.")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI AI IMAGE GENERATION (free tier)
# ─────────────────────────────────────────────────────────────────────────────

def generate_ai_image(
    prompt: str,
    output_path: str,
    aspect_ratio: str = "16:9"
) -> bool:
    """
    Generates a photorealistic AI image using Gemini (free tier).
    Model: gemini-2.5-flash-image

    NOTE: imagen-4.0-fast-generate-001 is a PAID model. We use the free
    gemini-2.5-flash-image instead, which supports
    response_modalities=["TEXT", "IMAGE"] in the new SDK.

    Args:
        prompt: Descriptive image prompt.
        output_path: Where to save the resulting .jpg file.
        aspect_ratio: "16:9" (long-form) or "9:16" (Shorts). Used to hint the prompt.

    Returns:
        True on success, False on any failure.
    """
    keys = _get_gemini_keys()
    if not keys:
        logger.warning("[GeminiImg] No GEMINI_API_KEY available.")
        return False

    try:
        from google import genai
        from google.genai import types
        from PIL import Image as PILImage
    except ImportError:
        logger.error("[GeminiImg] google-genai or Pillow not installed.")
        return False

    orientation_hint = "portrait 9:16 vertical" if aspect_ratio == "9:16" else "landscape 16:9 widescreen"
    full_prompt = (
        f"photorealistic, cinematic lighting, {orientation_hint}, {prompt}"
    )

    # Target pixel dimensions
    if aspect_ratio == "9:16":
        target_size = (1080, 1920)
    else:
        target_size = (1920, 1080)

    for key_idx, key in enumerate(keys):
        try:
            logger.info(f"[GeminiImg] Attempting with key #{key_idx + 1}...")
            client = genai.Client(api_key=key)

            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"]
                )
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    img = PILImage.open(io.BytesIO(part.inline_data.data)).convert("RGB")
                    img = img.resize(target_size, PILImage.LANCZOS)
                    os.makedirs(
                        os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
                        exist_ok=True
                    )
                    img.save(output_path, "JPEG", quality=95)
                    logger.info(f"[GeminiImg] Image saved: {output_path}")
                    return True

            logger.warning(f"[GeminiImg] Key #{key_idx + 1}: no image parts in response.")

        except Exception as e:
            logger.warning(f"[GeminiImg] Key #{key_idx + 1} failed: {e}")
            handle_429_sleep(str(e))
            continue

    logger.warning("[GeminiImg] All keys exhausted. Caller should use Pollinations fallback.")
    return False

def generate_tactical_diagram(prompt: str, diagram_type: str, output_path: str) -> bool:
    """
    Generates a minimalist tactical diagram using Gemini.
    diagram_type: 'formation', 'heat_map', 'passing_lanes', 'pressure_map', 'comparison_chart'
    """
    style_prompts = {
        "formation": "minimalist football pitch, 2D top-down view, player dots, clean lines, dark theme #111111 background, #F5A623 amber and #C0392B red tactical markings, professional broadcast style, no text",
        "heat_map": "football pitch heat map, dark theme background, intense red and amber gradient zones showing player activity, professional data visualization style, glowing effects, no text",
        "passing_lanes": "football pitch, minimalist dark theme, glowing passing lane arrows, player nodes, tiki-taka visualization, #F5A623 amber lines, clean professional graphics, no text",
        "pressure_map": "football tactical pressure map, dark theme #111111, glowing red zones for gegenpressing, subtle grid lines, professional broadcast graphics, no text",
        "comparison_chart": "minimalist football data visualization chart, dark theme #111111, amber #F5A623 and red #C0392B accent colors, sleek modern broadcast graphic, neon lines, no text"
    }
    
    style_suffix = style_prompts.get(diagram_type, style_prompts["formation"])
    full_prompt = f"tactical football graphic: {prompt}. {style_suffix}"
    
    return generate_ai_image(full_prompt, output_path, aspect_ratio="16:9")
