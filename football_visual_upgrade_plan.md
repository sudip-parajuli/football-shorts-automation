# Football Channel — Visual Upgrade Plan
## Bug Fixes + Remotion Scene System
### For Antigravity

---

## Part 1: Critical Bugs From The Log (Fix First)

These bugs are causing pipeline failures and degraded output RIGHT NOW.
Fix all of these before any visual upgrade work begins.

---

### Bug 1 — Remotion crashes because Pollinations images are saved to temp paths outside public/

The render log shows:
```
http://localhost:3000/public/footybitez/data/temp/20260522_092151_fcf97d/0/image.jpg
Failed to load resource: the server responded with a status of 404 (Not Found)
CancelledError: Error loading image with src: http://localhost:3000/public/...
```

Remotion's dev server only serves files under the `public/` directory of the
Remotion project. When the AssetOrchestrator saves a Pollinations fallback image to
`footybitez/data/temp/{job_id}/0/image.jpg`, Remotion maps this as
`localhost:3000/public/footybitez/data/temp/...` — but that path doesn't exist under
the Remotion `public/` folder, so it 404s and crashes the entire render.

Fix in asset_orchestrator.py:
All downloaded assets (Pollinations, Wikimedia, DDG, Gemini) must be saved inside
the Remotion public directory. Use an environment variable REMOTION_PUBLIC_DIR that
points to remotion-video/public/. Save all temp assets to:
  {REMOTION_PUBLIC_DIR}/temp/{job_id}/{scene_index}/image.jpg

The props.json path references must use the relative public path, not the absolute
filesystem path:
  WRONG: "asset_path": "/home/runner/.../footybitez/data/temp/job/0/image.jpg"
  RIGHT: "asset_path": "temp/job_id/0/image.jpg"   ← relative to public/

Remotion then resolves this as localhost:3000/public/temp/job_id/0/image.jpg which
will 404 if missing instead of being passed the wrong absolute path.

After render completes, clean up: delete public/temp/{job_id}/ entirely.

---

### Bug 2 — Veo 2.0 requires GCP billing — wrong model for free tier

The log shows:
```
[Veo] Key #1 failed: 400 FAILED_PRECONDITION
'The model models/veo-2.0-generate-001 is exclusively available to users
with Google Cloud Platform billing enabled.'
```

The pipeline is calling veo-2.0-generate-001 on all 3 keys, all failing.
The correct free-tier model is veo-3.0-fast-generate-preview (Veo 3 Fast),
NOT veo-2.0-generate-001. Veo 2.0 has never been available on the free tier.

Fix in football_visual_generator.py:
  OLD: VEO_MODEL = "veo-2.0-generate-001"
  NEW: VEO_MODEL = "veo-3.0-fast-generate-preview"

---

### Bug 3 — gemini-2.5-flash-image quota exhausted on all 3 keys within one run

The log shows gemini-2.5-flash-image hitting 429 on all 3 keys for both
scene images AND thumbnail — all within a single 90-second pipeline run.
The quota says "limit: 0" which means the daily free quota is already
exhausted before this run even started, not that this run exceeded it.

Root cause: the per-model daily quota for gemini-2.5-flash-preview-image on
free tier is 500 images/day BUT it is shared across ALL projects using the
same API key. If you're running both football and science pipelines on the
same 3 Gemini keys, they're competing for the same 500/day quota.

Fix:
1. Separate API keys for football and science channels if possible
   (create new Google AI Studio projects, get new free keys)
2. Add per-model daily usage tracking to quota_tracker.py — track
   gemini_image calls separately from gemini_text calls
3. When gemini_image quota is exhausted, skip directly to Pollinations
   without attempting all 3 keys (saves ~10 seconds per scene)
4. Add a minimum 30-second wait between gemini-2.5-flash-image calls
   (the retry delay in the log is 27-43 seconds — calls are being made
   too fast back-to-back)

---

### Bug 4 — duckduckgo_search package renamed, causing DDG failures

The log shows:
```
RuntimeWarning: This package (duckduckgo_search) has been renamed to ddgs!
Use pip install ddgs instead.
```

Fix in requirements.txt:
  OLD: duckduckgo-search
  NEW: ddgs

Fix in media_sourcer.py:
  OLD: from duckduckgo_search import DDGS
  NEW: from ddgs import DDGS

---

### Bug 5 — Pixabay SFX search not supported by public API

The log shows 5 SFX categories all failing with:
```
Pixabay public API does not support sound effects search. Skipping search.
```

The Pixabay API's free tier does not have a sound effects endpoint.
Fix: replace Pixabay SFX with Freesound.org API (free, CC0 sounds available).

Or simpler: pre-download a small SFX library (5-6 files: whoosh, impact, transition,
drum, rise) and commit them directly to the repo under sfx/. Never search at runtime.
These files are typically 20-50KB each — total <300KB added to the repo.

Tell Antigravity:
"Download these CC0 SFX from freesound.org and commit to sfx/ directory:
whoosh.mp3, impact.mp3, transition.mp3, drum_hit.mp3, rise.mp3, crowd_cheer.mp3
Remove all runtime SFX API calls. Load directly from sfx/{name}.mp3 at render time."

---

### Bug 6 — Wikimedia multi-fetch JSON parse error

The log shows:
```
Wikimedia multi-fetch error (query='Asmir Begovic Stoke City goal kick 2013 football'):
Expecting value: line 1 column 1 (char 0)
```

The Wikimedia API returned an empty response body. This happens when the query
is too long or contains special characters Wikimedia rejects.

Fix in asset_orchestrator.py: truncate Wikimedia queries to 50 characters max
before sending. Strip apostrophes, special characters. Use only the key nouns:
"Asmir Begovic Stoke City goal kick 2013 football" → "Asmir Begovic goalkeeper"

---

## Part 2: Football Channel Visual Upgrade — Remotion Scene System

The football channel uses Remotion (TypeScript/React) for rendering —
this is different from the science channel which uses MoviePy (Python).
The visual upgrade must be implemented in Remotion components.

The current pipeline produces: static images with Ken Burns + text overlay.
The goal: same 6-scene-type system as the science channel, but for football.

---

### 2.1 The 6 Remotion Scene Components

Create these new components in remotion-video/src/compositions/:

---

#### Component 1: TypewriterScene.tsx

Words appear one-by-one synced to narration. Word size and color encode meaning.

```tsx
// Props interface
interface TypewriterSceneProps {
  words: Array<{
    word: string;
    weight: "xl_accent" | "xl_amber" | "lg" | "md" | "dim";
  }>;
  wordTimestamps: Array<{ word: string; startFrame: number }>;
  durationInFrames: number;
}

// Weight → style mapping
const WEIGHT_STYLES = {
  xl_accent: { fontSize: 72, color: "#F5A623" },  // amber for football (not teal)
  xl_amber:  { fontSize: 72, color: "#FFFFFF" },
  lg:        { fontSize: 52, color: "#FFFFFF" },
  md:        { fontSize: 38, color: "#AAAAAA" },
  dim:       { fontSize: 28, color: "#444444" },
};

// Each word fades in (opacity 0→1 over 4 frames) when its startFrame is reached
// Show a rolling window of the last 10 words
// Blinking amber cursor after the last visible word
// Background: #0A0A12 (near black)
// Font: Barlow Condensed Bold (load via @remotion/google-fonts)
```

---

#### Component 2: KineticStatScene.tsx

Single dramatic number counts up from 0 to its value.

```tsx
interface KineticStatSceneProps {
  value: number;
  unit: string;        // e.g. "METERS"
  label: string;       // e.g. "Distance of Begovic's goal kick"
  durationInFrames: number;
}

// Count-up: interpolate from 0 to value over first 60 frames (2s at 30fps)
// Use spring() from Remotion for natural easing
// Number color: #F5A623 (amber) — football accent color
// Large number, unit above, label below, thin amber separator line
// Background: #060610
```

---

#### Component 3: ImageScene.tsx (upgrade of existing)

Real photo + Ken Burns + lower-third + cinematic grade.

```tsx
interface ImageSceneProps {
  assetPath: string;
  durationInFrames: number;
  kenBurnsStyle: "zoom_in_center" | "zoom_in_topleft" | "pan_left" | "pan_right";
  namedEntity?: { name: string; description: string };
  caption?: string;
}

// Ken Burns: interpolate transform over full duration
// zoom_in_center: scale 1.0→1.08, no translate
// zoom_in_topleft: scale 1.0→1.10, translate toward top-left
// pan_left: scale 1.04, translateX 0%→-4%
// pan_right: scale 1.04, translateX -4%→0%
// Cinematic grade: CSS filter contrast(1.15) saturate(0.88)
// Vignette: radial-gradient overlay div, pointer-events:none
// Lower-third: slides in from left at t=0.5s, holds, slides out at t=3.5s
//   amber left bar, teal name text, gray description
```

---

#### Component 4: AIVideoScene.tsx

AI-generated clip (or Pollinations fallback image with more aggressive Ken Burns).

```tsx
interface AIVideoSceneProps {
  assetPath: string;
  assetType: "video" | "image_fallback";
  durationInFrames: number;
  aiLabel?: string;   // shown as small badge top-left
}

// If assetType == "video": use <Video> component, loop if shorter than duration
// If assetType == "image_fallback": use <Img> with aggressive Ken Burns
//   (zoom 1.0→1.15 — much more movement than static image scenes)
// Ambient particle overlay: use useCurrentFrame() + Math.sin() to drift
//   small white dots across the frame at low opacity (5%)
// Small "AI GENERATED" badge top-left, amber border, semi-transparent bg
```

---

#### Component 5: HookQuestionScene.tsx

Chapter openings and rhetorical questions. Preceded by 2-frame white flash.

```tsx
interface HookQuestionSceneProps {
  questionText: string;
  emphasisPhrase: string;   // words to highlight in amber
  durationInFrames: number;
}

// Background: #050510
// Centered text, Georgia/serif font
// emphasisPhrase words render in amber, rest in white
// Thin amber line above and below text (animate width 0→40px over 8 frames)
// Full text fades in over 0.5s
// Prepend 2-frame white ColorClip before this scene (in MainVideo.tsx)
```

---

#### Component 6: DataBarsScene.tsx

Comparative horizontal bar chart for multiple values.

```tsx
interface DataBarsSceneProps {
  title: string;
  bars: Array<{ label: string; value: number; color: "amber" | "teal" | "purple" | "gray" }>;
  durationInFrames: number;
}

// Each bar animates width 0→final over 1.5s with 0.3s stagger between bars
// Use spring() from Remotion for the bar width animation
// Value labels appear after bar reaches 80% of its final width
// Background: #080810
```

---

### 2.2 Transition System in MainVideo.tsx

Add rule-based transitions between scene components:

```tsx
// In MainVideo.tsx, between each scene:

function getTransition(sceneA: SceneType, sceneB: SceneType): "flash" | "fade" | "cut" {
  if (sceneB === "hook_question" || sceneB === "kinetic_stat") return "flash";
  if (
    (sceneA === "image" && sceneB === "ai_video") ||
    (sceneA === "ai_video" && sceneB === "image")
  ) return "fade";
  return "cut";
}

// Flash: render a 2-frame white <ColorClip> between the two scenes
// Fade: use Remotion's <TransitionSeries> with a fade preset
// Cut: concatenate directly
```

---

### 2.3 New Remotion Component File Structure

```
remotion-video/src/compositions/
  MainVideo.tsx          ← updated to route scene types
  TypewriterScene.tsx    ← NEW
  KineticStatScene.tsx   ← NEW
  HookQuestionScene.tsx  ← NEW
  DataBarsScene.tsx      ← NEW
  ImageScene.tsx         ← UPGRADE (Ken Burns variations + lower-thirds)
  AIVideoScene.tsx       ← UPGRADE (video + image fallback + particles)
  LowerThird.tsx         ← SHARED (used by ImageScene and AIVideoScene)
  ChapterIntro.tsx       ← EXISTING (keep, just update colors)
  EndCard.tsx            ← EXISTING
```

---

### 2.4 Props Schema Update

The Python pipeline writes props.json which Remotion reads.
Update the props schema to include the new scene type fields:

```typescript
// In remotion-video/src/types.ts (create if doesn't exist)

interface VisualScene {
  visual_type: "typewriter_text" | "kinetic_stat" | "image" | "ai_video" | "hook_question" | "data_bars";
  asset_path?: string;          // relative to public/
  asset_type?: "video" | "image_fallback" | "image";
  duration_frames: number;
  transition: "flash" | "fade" | "cut";

  // typewriter_text
  typewriter_words?: Array<{ word: string; weight: string }>;
  word_timestamps?: Array<{ word: string; startFrame: number }>;

  // kinetic_stat
  stat_data?: { value: number; unit: string; label: string };

  // hook_question
  question_text?: string;
  emphasis_phrase?: string;

  // data_bars
  bar_data?: Array<{ label: string; value: number; color: string }>;

  // image / ai_video
  named_entity?: { name: string; description: string };
  ken_burns_style?: string;
  caption?: string;
}
```

---

### 2.5 Python Side: documentary_generator.py Updates

Update the Gemini classification prompt to output the new fields.
Add schema enforcement for missing fields (same as science channel):

```python
# In asset_orchestrator.py, after receiving Gemini JSON:
# Apply defaults for all optional fields before writing manifest

def _enforce_schema(scene: dict, topic: str) -> dict:
    # Never allow None image_cue
    if not scene.get("image_cue"):
        scene["image_cue"] = f"{topic} football"

    # Downgrade kinetic_stat to typewriter if stat_data missing
    if scene["visual_type"] == "kinetic_stat" and not scene.get("stat_data"):
        scene["visual_type"] = "typewriter_text"

    # Default emphasis_phrase for hook_question
    if scene["visual_type"] == "hook_question":
        q = scene.get("question_text", "")
        scene.setdefault("emphasis_phrase", " ".join(q.split()[-3:]))

    # Default typewriter_words if missing
    if scene["visual_type"] == "typewriter_text" and not scene.get("typewriter_words"):
        words = scene.get("narration", "").split()
        scene["typewriter_words"] = [
            {"word": w, "weight": "lg" if i % 5 == 0 else "md"}
            for i, w in enumerate(words)
        ]

    return scene
```

---

## Part 3: Football Channel Color Palette (Different from Science)

The science channel uses teal/cyan (#1EC8C8) as its accent color.
The football channel should use amber/gold (#F5A623) as primary accent
with a dark red (#8B1A1A) as secondary — matching the football channel
thumbnail colors already established.

Update all Remotion components to use these values:
```
Primary accent:  #F5A623  (amber/gold)
Secondary:       #C0392B  (deep red — for emphasis/danger)
Background dark: #0A0A12
Background stat: #060610
Text primary:    #FFFFFF
Text secondary:  #AAAAAA
Text dim:        #444444
Lower-third bg:  rgba(10, 10, 20, 0.85)
Lower-third bar: #F5A623  (amber)
```

---

## Part 4: Per-Video Visual Mix Target (Football Long-form)

For a 3-7 minute football documentary (~9 scenes per chapter × 3 chapters):

```
Per chapter (3 scenes each):
  Scene 1: hook_question    ← chapter opener, white flash before
  Scene 2: image            ← real photo with lower-third
  Scene 3: typewriter_text  ← key revelation

Across the full video:
  2-3 × kinetic_stat        (dramatic numbers: 100 meters, 13th minute, etc.)
  1-2 × ai_video            (atmospheric stadium/crowd — Veo 3 fast)
  1 × data_bars             (a comparison moment)
  Rest: image + typewriter mix
```

---

## Part 5: Build Order for Antigravity

```
STEP 1 — Fix the 6 pipeline bugs (do this first, test that render completes)
  - Fix Remotion asset path (temp files inside public/)
  - Fix Veo model name (veo-3.0-fast-generate-preview)
  - Fix DDG package rename (ddgs)
  - Pre-commit SFX files, remove runtime SFX API calls
  - Add 30s wait between gemini-2.5-flash-image calls
  - Truncate Wikimedia queries to 50 chars
  Test: run full pipeline for "Tiki-Taka Revolution", confirm render completes

STEP 2 — Create types.ts with VisualScene interface
  This defines the contract between Python props.json and Remotion components.
  Both sides must match exactly.

STEP 3 — Build TypewriterScene.tsx and KineticStatScene.tsx
  These are pure Remotion components with no asset dependencies — test them first.
  Test: render a 10-second test composition with one of each.

STEP 4 — Upgrade ImageScene.tsx with Ken Burns variations + LowerThird
  Test: render with a real image asset, confirm lower-third slides in correctly.

STEP 5 — Build HookQuestionScene.tsx and DataBarsScene.tsx
  Test: render each with sample data.

STEP 6 — Build AIVideoScene.tsx
  Test: render with both a video asset and an image_fallback asset.

STEP 7 — Update MainVideo.tsx to route scene types + add transition system
  Test: render a full 3-chapter documentary with mixed scene types.

STEP 8 — Update documentary_generator.py classification prompt + schema enforcement
  Test: generate visual scenes for "When a goalkeeper scored from 100 meters"
  Confirm: 3 kinetic_stat scenes (100 METERS, 13th MINUTE, 1 GOAL IN 172 APPEARANCES),
           hook_questions at each chapter start, no None image_cues

STEP 9 — End-to-end test
  Topic: "Andres Iniesta's 2010 World Cup winning goal"
  Expected: varied scene types, completed Remotion render, correct thumbnail
```

---

## Part 6: Send to Antigravity as One Message

Combine Parts 1-5 and tell Antigravity:

"Implement in strict step order. Do not start Step 2 until Step 1's render
completes successfully. Do not start Step 7 until Steps 3-6 are each
individually tested. The most common failure mode is Step 7 (MainVideo.tsx)
breaking because a component from Steps 3-6 has a prop mismatch — isolated
testing prevents this."

---

*Football Channel Visual Upgrade Plan v1.0*
