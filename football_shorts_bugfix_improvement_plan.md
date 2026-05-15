# Football Shorts — Bug Fixes + Improvement Plan
## For Antigravity

---

## Part 1: Fix the Two Bugs First (Before Any New Features)

Both bugs have known causes from the error logs. Fix these before touching anything else.

---

### Bug 1 — Shorts crash: `'MediaSourcer' object has no attribute 'get_title_card_image'`

**Root cause**: `main.py` calls `media_sourcer.get_title_card_image(topic)` but this method was never implemented in `MediaSourcer`. The method is called but doesn't exist.

**Fix — tell Antigravity:**
```
In footybitez/media/media_sourcer.py, add the missing get_title_card_image() method.

It should:
1. Search for a relevant image using the existing image search logic, 
   with the query: f"football {topic} stadium crowd action"
2. If a real image is found, return its local path (same as existing fetch methods)
3. If no image found, generate one using Pollinations.ai with the same query
4. If Pollinations fails, create a solid dark background PIL image 
   (1080x1920 for Shorts aspect ratio) and return that path
5. Never raise — always return a valid image path

Signature: def get_title_card_image(self, topic: str) -> str
```

---

### Bug 2 — Thumbnail: `GenerationConfig.__init__() got an unexpected keyword argument 'response_modalities'`

**Root cause**: Your thumbnail generator is using the **old deprecated SDK** (`google-generativeai`, imported as `import google.generativeai as genai`). The old `google.generativeai` SDK's `GenerationConfig` does not support `response_modalities` — its constructor only accepts: `candidate_count`, `stop_sequences`, `max_output_tokens`, `temperature`, `top_p`, `top_k`, `response_mime_type`, `response_schema`.

The `google-generativeai` library is now deprecated. The correct replacement is the new unified Google GenAI SDK: `from google import genai`, using `types.GenerateContentConfig` instead of `genai.GenerationConfig`.

**This is a full SDK migration, not a one-line fix.** The new SDK has a different import, different client pattern, and different config object.

**Old (broken) pattern your code uses:**
```python
import google.generativeai as genai
genai.configure(api_key=KEY)
model = genai.GenerativeModel('gemini-2.0-flash')
response = model.generate_content(
    prompt,
    generation_config=genai.GenerationConfig(
        response_modalities=["TEXT", "IMAGE"]  # ← DOES NOT EXIST in old SDK
    )
)
```

**New (correct) pattern — tell Antigravity to rewrite all Gemini calls to this:**
```python
from google import genai
from google.genai import types

client = genai.Client(api_key=KEY)

response = client.models.generate_content(
    model='gemini-2.5-flash-image',  # Use image-capable model
    contents=prompt,
    config=types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],  # Works in new SDK
        image_config=types.ImageConfig(
            aspect_ratio="16:9",   # Use "9:16" for Shorts thumbnails
        ),
    ),
)

# Extract image from response
for part in response.parts:
    if part.inline_data:
        image = part.as_image()
        image.save(output_path)
        break
```

**Files to migrate — tell Antigravity to audit every file that contains `import google.generativeai` and migrate each one:**

The migration pattern for every file:
```
OLD: import google.generativeai as genai
NEW: from google import genai
     from google.genai import types
     client = genai.Client(api_key=KEY)

OLD: genai.configure(api_key=KEY)
NEW: (removed — key goes in Client constructor or GEMINI_API_KEY env var)

OLD: model = genai.GenerativeModel('model-name')
     response = model.generate_content(prompt, generation_config=genai.GenerationConfig(...))
NEW: response = client.models.generate_content(
         model='model-name',
         contents=prompt,
         config=types.GenerateContentConfig(...)
     )

OLD: from google.api_core.exceptions import GoogleAPIError
NEW: from google.genai.errors import APIError
```

**requirements.txt / pyproject.toml change:**
```
REMOVE: google-generativeai
ADD:    google-genai>=1.0.0
```

**Important**: Also add `google-genai>=1.0.0` to the GitHub Actions workflow requirements install step. The old package and new package have different PyPI names — if both are installed, they conflict.

---

### Additional fix: Python version warning in GitHub Actions

The logs show:
```
FutureWarning: You are using Python 3.10.20 which Google will stop supporting...
```

**Fix — tell Antigravity to update `.github/workflows/*.yml`:**
```yaml
# Change:
python-version: '3.10'
# To:
python-version: '3.12'
```

Python 3.12 is the current stable version and removes this warning. No code changes needed — your codebase has no 3.10-specific syntax.

---

## Part 2: Shorts Content Quality Improvements

After the bugs are fixed, these are the highest-impact improvements for Shorts.

---

### Problem 1: Script accuracy issues

From the log, the generated script for "Top 10 one-season wonders" contains factual errors:
- Robin van Persie in 2012 was described as a "one-season wonder" — he stayed 3 seasons
- Transfer fees and contract values are hallucinated (the script invents specific £ figures)
- The topic was "one-season wonders" but the script wandered into general player stats

**Fix — tell Antigravity to update the Groq/Llama3 prompt in `script_writer.py`:**
```
Add these rules to the Shorts script generation system prompt:

STRICT ACCURACY RULES:
1. Only include players who genuinely fit the topic definition. 
   "One-season wonder" means a player who performed exceptionally 
   for exactly ONE season then significantly declined or left. 
   Do not include players who had sustained success.
2. Never invent or estimate transfer fees, contract values, or 
   bonus amounts. Only state fees if you are certain of the figure. 
   If uncertain, omit the number entirely.
3. Every statistic (goals, assists, points) must be a real verified figure. 
   If you are not certain, use approximate language ("around X goals") 
   or omit.
4. The script must stay on topic for all 10 entries. Do not drift 
   to adjacent topics.
5. Script length: 55-65 seconds when read at normal narration pace 
   (~140 words/min = target 130-150 words total). Count words before returning.
```

---

### Problem 2: Title card and visual quality for Shorts

Currently the Shorts pipeline:
- Has a broken title card (Bug 1 above)
- Uses the same visual logic as long-form (landscape images in a portrait 9:16 frame)

**Fix — tell Antigravity to update `media_sourcer.py` and `video_short.py`:**

```
All image fetching for Shorts must target 9:16 aspect ratio content.
When searching for images, add "portrait vertical" to the query when 
appropriate (player photos, action shots crop well to portrait).
When building the title card in get_title_card_image():
- Canvas: 1080x1920 (9:16)
- Background: dark gradient (#0a0a0a to #1a1a2e)
- Title text: Barlow Condensed Bold, size 90, white, centered, 
  with amber (#F5A623) accent for key words
- Add a subtle top strip in club color if the topic mentions a specific club
- Add channel logo/watermark bottom-right at 30% opacity
```

---

### Problem 3: No visual variety in Shorts

Shorts currently shows static images. For a 60-second Short, you need visual movement to keep viewers from swiping away in the first 3 seconds.

**Add to `video_short.py` — tell Antigravity:**

```
Add these three visual techniques to Shorts rendering (all in MoviePy/PIL):

1. ZOOM PUNCH on scene start:
   Every new image should start at 105% scale and zoom to 100% over 
   8 frames. Creates an "impact" feel when cutting between items.
   Implementation: interpolate scale from 1.05 to 1.0 over first 
   8 frames of each ImageClip.

2. FLASH CUT transition:
   Between items 5 and 6 (the halfway point of a Top 10), add a 
   4-frame white flash (solid white ImageClip) before the next image.
   Creates energy and signals the "second half" of the list.

3. RANKING NUMBER OVERLAY:
   For list-style Shorts (Top 10, Rankings & Lists category), 
   overlay a large ranking number on each clip:
   - Bottom-left corner
   - Font: Barlow Condensed Bold, size 140, amber (#F5A623)
   - Drop shadow: 4px offset, black, 60% opacity
   - Fade in over 6 frames at start of each clip
   Implementation: PIL text rendered as ImageClip, 
   composited over the base image using CompositeVideoClip.
```

---

### Problem 4: No AI image fallback for Shorts

When `get_title_card_image()` fails (currently crashes), and when image search returns nothing, there's no AI fallback. After fixing Bug 1, extend the fallback chain:

```
For Shorts image sourcing, the fallback chain should be:
1. DuckDuckGo image search (existing)
2. Wikimedia Commons API  
3. Pollinations.ai (already integrated — use for Shorts too)
4. Gemini image generation (new SDK — gemini-2.5-flash-image)
5. PIL solid color card with text (never crash)

For Shorts specifically, Pollinations.ai is the right Step 3 choice 
(no quota, instant, no API key needed). 
Reserve Gemini image generation for cases where the topic is abstract 
enough that a real photo won't exist.
```

---

### Problem 5: Context fetch failing silently

The log shows:
```
WARNING - Failed to fetch context for [topic]: Expecting value: line 1 column 1 (char 0)
```

This is a JSON parse error — the context fetch is getting an empty or non-JSON response and failing silently. The script then proceeds without context, which is why accuracy suffers.

**Fix — tell Antigravity:**
```
In the context fetching function, add:
1. Log the raw response text (first 200 chars) when JSON parsing fails, 
   so you can see what the API actually returned.
2. If the context fetch fails, do NOT silently continue with empty context. 
   Instead, retry once with a simplified query (just the topic name, 
   no extra parameters).
3. If both attempts fail, add a note to the Groq prompt: 
   "Note: no external context available. Use only your training knowledge. 
   Be conservative — omit any statistic you are not certain about."
```

---

## Part 3: Shorts Visual Upgrade — AI Images + AI Video

Once the bugs are fixed and content quality is improved, add these:

### AI Image Generation for Shorts (Gemini 2.5 Flash Image)

For Shorts, AI image generation is most useful for:
- Abstract concept illustrations (no real photo exists)
- Title cards with custom designs
- Ranking/list separator cards between every 3-4 items

```python
# In media_sourcer.py — add generate_ai_image_for_shorts() method

from google import genai
from google.genai import types
import io
from PIL import Image

def generate_ai_image_for_shorts(self, prompt: str, output_path: str) -> bool:
    """
    Generates a 9:16 portrait AI image for Shorts using Gemini.
    Returns True on success, False on any failure.
    """
    try:
        client = genai.Client(api_key=self.gemini_key)
        
        # Add Shorts-specific style to prompt
        full_prompt = (
            f"portrait orientation 9:16, {prompt}, "
            f"dramatic lighting, dark background, sports photography style, "
            f"no text overlays, cinematic quality"
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-image',
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="9:16"),
            ),
        )
        
        for part in response.parts:
            if part.inline_data:
                img = part.as_image()
                # Ensure it's exactly 1080x1920
                img = img.resize((1080, 1920), Image.LANCZOS)
                img.save(output_path, "JPEG", quality=95)
                return True
        return False
    except Exception as e:
        print(f"[Gemini Image] Failed: {e}")
        return False
```

### AI Video for Shorts (Optional — Low Priority)

For Shorts, AI video clips are less useful than for long-form because:
- Shorts are 60 seconds max — each visual is only 3-6 seconds anyway
- The zoom-punch and flash-cut effects above create enough movement from stills
- HF CogVideoX-2B clips take 30-90s to generate — too slow to be worth it for a 60s Short

**Recommendation**: Skip AI video for Shorts in v1. Add it only if watch time data shows viewers dropping off at specific visual moments.

---

## Part 4: Build Order for Antigravity

```
PRIORITY 1 (bugs — do immediately):
  Step 1: Migrate all files from google-generativeai to google-genai SDK
  Step 2: Add get_title_card_image() to MediaSourcer
  Step 3: Update GitHub Actions python-version to 3.12
  Step 4: Fix context fetch error logging and retry logic
  Test: Run pipeline once, confirm no crashes

PRIORITY 2 (content quality):
  Step 5: Update Groq script prompt with accuracy rules + word count target
  Step 6: Update image fetching for 9:16 aspect ratio
  Step 7: Add ranking number overlay to video_short.py
  Step 8: Add zoom-punch and flash-cut transitions
  Test: Run full Shorts pipeline, review output video

PRIORITY 3 (AI image upgrade):
  Step 9: Add generate_ai_image_for_shorts() using new Gemini SDK
  Step 10: Wire it into the image fallback chain (after Pollinations)
  Step 11: Add quota_tracker for Gemini image calls
  Test: Run with a topic that has few real images available
```

---

## Summary of What's Wrong and Why

| Issue | Root Cause | Fix |
|---|---|---|
| Shorts crash on title card | Missing method in MediaSourcer | Add `get_title_card_image()` |
| Thumbnail `response_modalities` error | Using deprecated `google-generativeai` SDK | Migrate to `google-genai` SDK |
| Script accuracy / hallucinated stats | Groq prompt has no accuracy constraints | Add strict accuracy rules to prompt |
| Context fetch fails silently | JSON parse error not logged or retried | Add logging + retry + fallback prompt note |
| Python version warning | GitHub Actions using Python 3.10 | Upgrade to 3.12 in workflow YAML |
| No visual movement in Shorts | No Ken Burns / zoom / transitions | Add zoom-punch + flash-cut in MoviePy |

---

*Football Shorts Bug Fix + Improvement Plan v1.0*
