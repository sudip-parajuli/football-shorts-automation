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

logger = logging.getLogger(__name__)


def _get_gemini_keys() -> list:
    keys = []
    for suffix in ["", "2", "3"]:
        val = os.getenv(f"GEMINI_API_KEY{suffix}")
        if val:
            keys.append(val)
    return keys


# ─────────────────────────────────────────────────────────────────────────────
# VEO 3.1 VIDEO GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def generate_veo_clip(prompt: str, output_path: str, duration_seconds: int = 8) -> bool:
    """
    Generates an AI video clip using Veo 3.1 Fast via Gemini API.
    Polls every 10 seconds, max 36 attempts (~6 minutes timeout).

    Args:
        prompt: Cinematic text-to-video prompt. Must follow football channel rules:
                only atmospheric/generic shots, NO named players or specific events.
        output_path: Where to save the resulting .mp4 file.
        duration_seconds: Clip length (default 8s, Veo supports 5-8s).

    Returns:
        True on success, False on any failure (API error, timeout, invalid output).
    """
    keys = _get_gemini_keys()
    if not keys:
        logger.warning("[Veo] No GEMINI_API_KEY available. Skipping Veo generation.")
        return False

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.error("[Veo] google-genai not installed. Run: pip install google-genai>=1.0.0")
        return False

    for key_idx, key in enumerate(keys):
        try:
            logger.info(f"[Veo] Attempting generation with key #{key_idx + 1}...")
            client = genai.Client(api_key=key)

            # Start async generation operation
            operation = client.models.generate_videos(
                model="veo-2.0-generate-001",
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    duration_seconds=duration_seconds,
                    number_of_videos=1,
                )
            )

            # Poll until done — max ~6 minutes (36 × 10s)
            MAX_POLLS = 36
            POLL_INTERVAL = 10
            start = time.time()
            for attempt in range(MAX_POLLS):
                if operation.done:
                    break
                if (time.time() - start) > 360:
                    logger.warning(f"[Veo] Wall-clock timeout exceeded for key #{key_idx + 1}.")
                    break
                logger.info(f"[Veo] Polling attempt {attempt + 1}/{MAX_POLLS}...")
                time.sleep(POLL_INTERVAL)
                try:
                    operation = client.operations.get(operation)
                except Exception as e:
                    logger.error(f"[Veo] Failed to refresh operation: {e}")
                    return False

            if not operation.done:
                logger.warning(f"[Veo] Timeout after {MAX_POLLS * POLL_INTERVAL}s for key #{key_idx + 1}.")
                continue

            # Extract video bytes
            result = operation.result
            if not result or not hasattr(result, 'generated_videos') or not result.generated_videos:
                logger.warning(f"[Veo] Key #{key_idx + 1}: operation done but no video in result.")
                continue

            video = result.generated_videos[0]
            if not hasattr(video, 'video') or not video.video:
                logger.warning(f"[Veo] Key #{key_idx + 1}: video object has no data.")
                continue

            # Save to disk
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(video.video.video_bytes)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
                logger.info(f"[Veo] Clip saved: {output_path} ({os.path.getsize(output_path) // 1024}KB)")
                return True
            else:
                logger.warning(f"[Veo] Saved file too small or missing: {output_path}")

        except Exception as e:
            logger.warning(f"[Veo] Key #{key_idx + 1} failed: {e}")
            continue

    logger.warning("[Veo] All keys exhausted or failed. Caller should use fallback.")
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
            continue

    logger.warning("[GeminiImg] All keys exhausted. Caller should use Pollinations fallback.")
    return False
