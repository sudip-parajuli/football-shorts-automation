# Football Channel Visual Upgrade — AI Images + AI Video
## Implementation Plan for Antigravity

---

## ⚡ Critical Context: What Changed in April 2026

**Google made Veo 3.1 free to all Google account holders on April 2, 2026.**

This changes the plan entirely. Here is the actual free access landscape as of May 2026:

| Access Path | Free Limit | Resolution | Watermark | API-callable? | Commercial use? |
|---|---|---|---|---|---|
| **Google Flow** | 50 credits/day (~12 clips) | 720p | No | ❌ Manual only | ✅ Yes |
| **Google Vids** | 10 clips/month | 720p | Yes (Veo watermark) | ❌ Manual only | ⚠️ Check ToS |
| **Google AI Studio** | ~10-50 generations/month | 720p | No | ✅ Via Gemini API | ✅ Yes (no training data flag on API tier) |
| **Gemini API free tier** | ~50 RPD (requests/day) for Flash models | 720p | No | ✅ Yes | ✅ Yes |
| **HuggingFace CogVideoX-2B** | ~1000/month | 720p | No | ✅ Yes | ✅ Apache 2.0 |

### The Strategy

- **Automated pipeline clips**: Use **Gemini API free tier** (Veo 3.1 Fast via `veo-3.1-fast-generate-preview`) — API-callable, no watermark, ~50 clips/day limit
- **Overflow / quota exhausted**: Fall back to **HuggingFace CogVideoX-2B** (existing, Apache 2.0)
- **Final fallback**: **Pollinations.ai** AI image (already in pipeline)
- **AI images (script-matched)**: Use **Imagen 4 Fast** (`imagen-4.0-fast-generate-001`) via Gemini API free tier — same API key, no extra setup

**Key constraint**: The Gemini API free tier Veo access is listed as "preview" — Google explicitly warns limits can change. The pipeline must handle quota failures gracefully and never block on video generation.

---

## Part 1: What the Football Channel Needs vs Science Channel

The football channel has different visual requirements than the science channel:

| Visual Need | Science Channel | Football Channel |
|---|---|---|
| Abstract phenomena | ✅ Great for AI video | ❌ Rarely needed |
| Real historical moments | Image | Image (AI video would hallucinate) |
| Stadium atmospheres | Image | ✅ Great for AI video |
| Player action shots | Image (real photos best) | Image (AI video = distorted faces/bodies) |
| Scandal/document moments | Image | Image |
| Crowd energy / mood | Image | ✅ Great for AI video |
| Tactical diagrams | N/A | Kinetic text / overlay |
| Score/stat reveals | Kinetic text | Kinetic text |

**Rule for football channel**: Only use AI video for atmosphere, crowd, and abstract mood shots. Never for named players, specific matches, or real historical events — models hallucinate faces and kit numbers.

---

## Part 2: Gemini API Integration — Veo 3.1 + Imagen 4

### 2.1 API Setup (same key as Gemini script generation)

```python
# football_visual_generator.py
import google.generativeai as genai
import os, time, json

genai.configure(api_key=os.environ["GEMINI_API_KEY"])  # already in .env

VEO_MODEL   = "veo-3.1-fast-generate-preview"
IMAGEN_MODEL = "imagen-4.0-fast-generate-001"
```

### 2.2 Veo 3.1 Video Generation

```python
def generate_veo_clip(prompt: str, output_path: str) -> bool:
    """
    Generates an 8-second Veo 3.1 clip via Gemini API.
    Returns True on success, False on any failure (caller handles fallback).
    """
    try:
        operation = genai.generate_video(
            model=VEO_MODEL,
            prompt=prompt,
            config={
                "aspectRatio": "16:9",
                "durationSeconds": 8,
                "resolution": "720p"
            }
        )
        # Veo generation is async — poll until done
        for attempt in range(30):  # Max ~5 minutes wait
            if operation.done:
                break
            time.sleep(10)
            operation = operation.refresh()
        
        if not operation.done or operation.result is None:
            print(f"[Veo] Timeout after 5 minutes for prompt: {prompt[:60]}")
            return False
        
        video_bytes = operation.result.video.video_bytes
        with open(output_path, 'wb') as f:
            f.write(video_bytes)
        return True

    except Exception as e:
        print(f"[Veo] API error: {e}")
        return False
```

### 2.3 Imagen 4 Image Generation (Script-Matched Fallback + Standalone)

```python
def generate_ai_image(prompt: str, output_path: str) -> bool:
    """
    Generates a photorealistic image using Imagen 4 Fast.
    Used when: (1) no real image found AND ai_video failed,
               (2) visual_type == "image" AND real source search returns nothing.
    """
    try:
        result = genai.generate_images(
            model=IMAGEN_MODEL,
            prompt=f"photorealistic, cinematic lighting, {prompt}",
            config={
                "numberOfImages": 1,
                "aspectRatio": "16:9",
                "safetyFilterLevel": "BLOCK_MEDIUM_AND_ABOVE"
            }
        )
        if result.generated_images:
            result.generated_images[0].image.save(output_path)
            return True
        return False
    except Exception as e:
        print(f"[Imagen4] API error: {e}")
        return False
```

### 2.4 Quota Tracker

The Gemini API free tier has daily limits. Both Veo and Imagen share the same API key's quota bucket. Track usage to avoid silent failures:

```python
# quota_tracker.py
import json, os
from datetime import date

QUOTA_FILE = "automation/storage/gemini_quota.json"
DAILY_VEO_LIMIT   = 45   # Leave 5 buffer below ~50 RPD free tier
DAILY_IMAGEN_LIMIT = 90  # Imagen has higher free quota

def can_use(service: str) -> bool:
    data = _load()
    today = str(date.today())
    if data.get("date") != today:
        data = {"date": today, "veo": 0, "imagen": 0}
    limit = DAILY_VEO_LIMIT if service == "veo" else DAILY_IMAGEN_LIMIT
    return data.get(service, 0) < limit

def record_use(service: str):
    data = _load()
    today = str(date.today())
    if data.get("date") != today:
        data = {"date": today, "veo": 0, "imagen": 0}
    data[service] = data.get(service, 0) + 1
    with open(QUOTA_FILE, 'w') as f:
        json.dump(data, f)

def _load():
    if os.path.exists(QUOTA_FILE):
        with open(QUOTA_FILE) as f:
            return json.load(f)
    return {}
```

---

## Part 3: Visual Type Classification for Football Scripts

Update `documentary_generator.py` (the Gemini script prompt) to output `visual_type` and `ai_video_prompt` per scene:

```
Add to the Gemini script generation system prompt:

For each scene, classify visual_type as one of:
- "ai_video": ONLY for stadium atmospheres, crowd shots, abstract sport energy, 
  weather/lighting effects, generic pitch views. NEVER for named players, 
  specific match moments, or historical events.
- "image": real people, named players, match photos, documents, trophies, 
  club badges, specific venues by name
- "kinetic_text": statistics, scorelines, dates, key facts to highlight
- "image_with_overlay": a real sourced image with a stat/name overlaid

For ai_video scenes, also output "ai_video_prompt" — a 1-2 sentence 
cinematic text-to-video prompt. Format: "[camera move], [subject], 
[atmosphere], [style]"

Examples of good ai_video prompts for football:
- "Slow aerial drone pull-back over a packed 80,000-seat stadium at night, 
  floodlights blazing, crowd a sea of red and white, cinematic"
- "Low-angle tracking shot following a football rolling across a wet pitch, 
  floodlights reflected in puddles, dramatic atmosphere"
- "Wide shot of empty football stadium at dusk, golden hour light across 
  the seats, melancholic mood, cinematic"
- "Crowd in stands erupting, arms raised, scarves waving, slow-motion, 
  shot from pitch level looking up, intense atmosphere"

Max 3 ai_video scenes per video. All others must be image, kinetic_text, 
or image_with_overlay.
```

---

## Part 4: Asset Orchestrator — Updated Fallback Chain

```python
# asset_orchestrator.py — updated for football channel

def fetch_asset(scene: dict, job_id: str) -> dict:
    visual_type = scene["visual_type"]
    scene_idx   = scene["scene_index"]
    out_dir     = f"automation/storage/temp/{job_id}/{scene_idx}/"
    os.makedirs(out_dir, exist_ok=True)

    if visual_type == "ai_video":
        return _fetch_ai_video(scene, out_dir)
    
    elif visual_type in ("image", "image_with_overlay"):
        return _fetch_image(scene, out_dir)
    
    elif visual_type == "kinetic_text":
        return {"asset_type": "kinetic_text", "asset_path": None,
                "kinetic_stat": scene.get("kinetic_stat")}

def _fetch_ai_video(scene, out_dir):
    path = out_dir + "clip.mp4"
    
    # Step 1: Veo 3.1 via Gemini API (if quota available)
    if quota_tracker.can_use("veo"):
        success = football_visual_generator.generate_veo_clip(
            scene["ai_video_prompt"], path)
        if success:
            quota_tracker.record_use("veo")
            # Validate output with ffprobe before returning
            if _validate_video(path):
                return {"asset_type": "ai_video", "asset_path": path}
    
    # Step 2: HuggingFace CogVideoX-2B (quota-free fallback)
    success = hf_video_generator.generate_clip(
        scene["ai_video_prompt"], path)
    if success and _validate_video(path):
        return {"asset_type": "ai_video", "asset_path": path}
    
    # Step 3: Degrade to AI image (Imagen 4)
    return _fetch_ai_image(scene, out_dir)

def _fetch_image(scene, out_dir):
    path_img = out_dir + "image.jpg"
    
    # Step 1: Real sources (Wikimedia → Unsplash → Pixabay)
    result = media_sourcer.fetch(scene["image_cue"], path_img)
    if result:
        return {"asset_type": "image", "asset_path": path_img,
                "overlay": scene.get("kinetic_stat") if scene["visual_type"] == "image_with_overlay" else None}
    
    # Step 2: Imagen 4 Fast (script-matched AI image)
    return _fetch_ai_image(scene, out_dir)

def _fetch_ai_image(scene, out_dir):
    path_img = out_dir + "ai_image.jpg"
    prompt = scene.get("image_cue") or scene.get("ai_video_prompt", "football stadium")
    
    if quota_tracker.can_use("imagen"):
        success = football_visual_generator.generate_ai_image(prompt, path_img)
        if success:
            quota_tracker.record_use("imagen")
            return {"asset_type": "image", "asset_path": path_img}
    
    # Step 3: Pollinations.ai (no quota, always available)
    success = pollinations_generator.generate(prompt, path_img)
    if success:
        return {"asset_type": "image", "asset_path": path_img}
    
    # Step 4: Solid color card (never crash)
    return {"asset_type": "color_card", "asset_path": None,
            "color": "#0a0a0a", "text": scene.get("narration", "")[:80]}
```

---

## Part 5: MoviePy Video Rendering — Handling AI Video Clips

In `video_long.py`, add handling for `ai_video` asset type alongside existing image logic:

```python
def _build_scene_clip(self, scene_manifest: dict, tts_duration: float):
    asset_type = scene_manifest["asset_type"]
    asset_path = scene_manifest["asset_path"]

    if asset_type == "ai_video":
        clip = VideoFileClip(asset_path)
        # Sync to TTS duration
        if tts_duration > clip.duration:
            clip = clip.loop(duration=tts_duration)   # Loop short clip
        else:
            clip = clip.subclip(0, tts_duration)       # Trim long clip
        return clip.resize((1920, 1080))

    elif asset_type == "image":
        clip = ImageClip(asset_path, duration=tts_duration)
        clip = self._apply_ken_burns(clip, tts_duration)
        # Add overlay if present
        if scene_manifest.get("overlay"):
            clip = self._add_lower_third_overlay(clip, scene_manifest["overlay"])
        return clip

    elif asset_type == "kinetic_text":
        return self._render_kinetic_stat_slide(
            scene_manifest["kinetic_stat"], tts_duration)

    elif asset_type == "color_card":
        return self._render_color_card(
            scene_manifest.get("text", ""), tts_duration)
```

---

## Part 6: New Files Summary

| File | Purpose | New / Modify |
|---|---|---|
| `football_visual_generator.py` | Veo 3.1 + Imagen 4 via Gemini API | NEW |
| `quota_tracker.py` | Daily Gemini API usage counter | NEW |
| `asset_orchestrator.py` | 4-tier fallback chain for all asset types | NEW |
| `documentary_generator.py` | Add football-specific visual_type rules to prompt | MODIFY |
| `video_long.py` | Handle ai_video asset type in scene builder | MODIFY |
| `science_pipeline.py` / `football_pipeline.py` | Wire orchestrator | MODIFY |
| `.env.example` | `GEMINI_API_KEY` already there — no new keys needed | ✅ Nothing |

**No new API keys required.** Veo 3.1 and Imagen 4 use the same `GEMINI_API_KEY` already in your `.env` for script generation.

---

## Part 7: Veo Prompt Rules for Football Content

Give Antigravity these rules to include in the Gemini classification prompt:

### ✅ Good Veo prompts (abstract, atmospheric, generic)
```
"Aerial drone shot slowly descending over a packed football stadium at 
 night, floodlights illuminating 80,000 fans, cinematic atmosphere"

"Low-angle shot of football boots on a wet pitch, rain falling in 
 slow motion, floodlights in background, dramatic sports photography"

"Empty stadium seats in late afternoon golden light, a lone groundskeeper 
 walking across the pitch in the distance, melancholic mood"

"Wide shot of a referee's whistle on a green pitch, crowd noise implied 
 by packed stands blurred in background, cinematic close-up"

"Night sky above a stadium, floodlights casting upward beams, 
 atmospheric fog, slow upward camera tilt"
```

### ❌ Bad Veo prompts (will hallucinate badly — use image instead)
```
"Lionel Messi scoring against Real Madrid"         ← named player
"The 1966 World Cup final at Wembley"              ← specific real event
"Juventus players celebrating winning the title"   ← named club + people
"referee showing a red card to a player"           ← faces distort badly
"TV presenter reading match-fixing allegations"    ← people + text
```

---

## Part 8: Per-Video Visual Mix Target

For a 6-10 minute football documentary video (~8-12 scenes):

```
3 scenes  → Veo 3.1 AI video clips (atmospheric, crowd, stadium)
4 scenes  → Real sourced images (Wikimedia/Unsplash/Pixabay)
2 scenes  → Imagen 4 AI images (where real images not found)
2 scenes  → Kinetic text / stat slides
1 scene   → Image with lower-third overlay
```

This gives a professional, varied visual rhythm without over-relying on any one source.

---

## Part 9: Commands for Antigravity

### To build football_visual_generator.py:
```
Build football_visual_generator.py using the Gemini API (same key as 
documentary_generator.py). Implement two functions:
1. generate_veo_clip(prompt, output_path) — calls veo-3.1-fast-generate-preview,
   polls until done (10s interval, 30 attempts max), saves MP4 bytes to output_path.
   Returns True/False.
2. generate_ai_image(prompt, output_path) — calls imagen-4.0-fast-generate-001,
   saves JPEG to output_path. Returns True/False.
Both functions must catch all exceptions and return False (never raise).
```

### To build asset_orchestrator.py:
```
Build asset_orchestrator.py implementing the 4-tier fallback chain:
Veo 3.1 → HuggingFace CogVideoX-2B → Imagen 4 → Pollinations.ai
For image scenes: Wikimedia → Unsplash → Pixabay → Imagen 4 → Pollinations.ai
Import quota_tracker and check can_use() before every Gemini API call.
Write asset_manifest.json to automation/storage/temp/{job_id}/manifest.json.
Never raise exceptions — always return a valid asset dict even if all steps fail 
(fall back to color_card type).
```

### To update documentary_generator.py for football:
```
Add football-specific visual_type classification rules to the Gemini prompt 
in generate_visual_scenes(). Rules:
- ai_video: ONLY atmospheric/crowd/stadium shots with no named players or 
  specific real events. Max 3 per video.
- image: all named players, clubs, historical events, documents.
- kinetic_text: stats, scores, dates.
- image_with_overlay: image + stat to overlay.
Also output "ai_video_prompt" for ai_video scenes using the cinematic 
prompt format: "[camera move], [subject], [atmosphere], [style]"
```

---

*Football Channel Visual Upgrade Plan v1.0*
