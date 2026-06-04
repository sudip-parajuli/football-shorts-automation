# Football Channel — Visual & Content Upgrade Plan v3.0
## B-roll + Accurate Images + Statistics + Motion Graphics + Hume Separation
### For Antigravity

---

## Critical context from the log before any upgrades

The log shows 3 issues to fix immediately alongside the upgrades:

1. **comment_manager.py still uses old `google-generativeai` SDK**
   Log: "All support for the `google.generativeai` package has ended"
   Fix: migrate comment_manager.py to `from google import genai` (same as all other files)

2. **setAtTop error when pinning comments**
   Log: "Failed to pin comment: 'Resource' object has no attribute 'setAtTop'"
   Fix: YouTube Data API v3 uses `comments().setModerationStatus()` not `setAtTop` for
   pinning — update the pin logic or remove it (pinning comments is low priority)

3. **SFX pre-committed files not found — generating procedural fallback every run**
   Log: "SFX not found: whoosh. Generating procedural fallback" for ALL 6 SFX types
   The static files were supposed to be committed to `remotion-video/public/assets/sounds/`
   but they clearly weren't. The procedural fallbacks are being used instead.
   Fix: actually download and commit the 6 CC0 SFX files before the next run.

---

## Part 1: Accurate Image Sourcing — The Core Problem

### 1.1 Why current images are wrong

The pipeline generates an `image_cue` like "Andres Iniesta penalty kick 2010 World Cup"
but then searches DDG with that query. DDG returns whatever is indexed — often wrong photos,
stock images, or completely unrelated players. When DDG fails (which it does on every run due
to rate limiting), Wikimedia is queried with truncated keywords, and Pollinations generates
a made-up image of a generic footballer.

The result: a video about Messi might show a photo of Ronaldo, or a generic stock footballer.

### 1.2 The solution: Wikipedia entity-first image lookup

Wikipedia has the most accurate, free, CC-licensed images of real football players, clubs,
stadiums, and events. Every notable player has a Wikipedia page with their photo. The
Wikimedia API can fetch images DIRECTLY from a player's Wikipedia page, not from a general
image search — this guarantees accuracy.

**New function: `get_wikipedia_entity_image(entity_name: str) -> str`**

```python
def get_wikipedia_entity_image(entity_name: str, output_path: str) -> bool:
    """
    Fetches the primary image from a Wikipedia article for a named entity.
    This guarantees accuracy — the image is the one Wikipedia uses for this exact person/club.
    
    Examples:
        get_wikipedia_entity_image("Lionel Messi") → his Wikipedia infobox photo
        get_wikipedia_entity_image("FC Barcelona") → club crest/photo
        get_wikipedia_entity_image("Camp Nou") → stadium photo
        get_wikipedia_entity_image("2010 FIFA World Cup Final") → match photo
    """
    import requests
    
    # Step 1: Get the Wikipedia page summary (includes main image)
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + entity_name.replace(" ", "_")
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return False
    
    data = r.json()
    
    # Step 2: Extract the thumbnail/original image
    image_url = (data.get("originalimage", {}).get("source") or
                 data.get("thumbnail", {}).get("source"))
    if not image_url:
        return False
    
    # Step 3: Download
    img_r = requests.get(image_url, timeout=30)
    if img_r.status_code != 200:
        return False
    
    with open(output_path, 'wb') as f:
        f.write(img_r.content)
    return True
```

### 1.3 Named entity extraction in documentary_generator.py

The Gemini/Groq prompt must extract named entities per scene and flag them for
Wikipedia lookup:

```
For each scene, extract "named_entities": a list of real people, clubs, stadiums,
or events mentioned. For each entity, add "wikipedia_lookup": true if it is the
MAIN subject of the scene. Only one entity per scene should have wikipedia_lookup=true.

Example:
{
  "visual_type": "image",
  "narration": "Cristiano Ronaldo scored his 100th Champions League goal in 2021",
  "image_cue": "Cristiano Ronaldo Champions League goal celebration",
  "named_entities": [
    {"name": "Cristiano Ronaldo", "type": "player", "wikipedia_lookup": true},
    {"name": "UEFA Champions League", "type": "competition", "wikipedia_lookup": false}
  ]
}
```

### 1.4 Updated image fetching priority chain

```
For scenes with named_entities[n].wikipedia_lookup == true:
  1. Wikipedia REST API (entity-specific page image) → ALWAYS ACCURATE
  2. Wikimedia search (specific query)
  3. Unsplash
  4. Pollinations fallback

For scenes without named entities (abstract/atmospheric):
  1. Wikimedia search
  2. NASA Image API (for space/science, not needed here)
  3. Unsplash
  4. Pollinations fallback

NEVER use DDG as primary — it's rate-limited on every single run.
fix the rate-limit error for DDG.

The main approaches to accessing and using football video clips via API include:
1. Embeds for Highlights (Ready-to-Use)If you want to display clips of goals and match recaps on your website or app, you can use third-party embed APIs. These APIs provide JSON feeds with links/embed codes from official media sources.Top Options: Platforms like ScoreBat on the RapidAPI marketplace provide free, embeddable video feeds for major leagues like the Premier League, La Liga, and Champions League.2. Live Match Feeds (For Data & Betting Companies)If your intention is to build sports apps or streaming platforms, you can leverage professional sports video APIs. These are commercial-grade feeds that stream live events, game recaps, and stats.Top Options: Highlightly and Sport Highlights API offer REST JSON APIs that connect event triggers (like goals and fouls) with short highlight clips.3. Automated AI Highlight GenerationIf you have your own full-length match footage and want to extract short clips automatically, you can utilize AI video intelligence APIs. These systems analyze video, recognize gameplay actions (like a goal or tackle), and generate short clips for you.Top Options: Services like Magnifi or specialized developer tools like Twelve Labs provide AI-driven video understanding
```

---

## Part 2: Real Match Video Clips (B-roll)

### 2.1 What's actually available for free

**IMPORTANT COPYRIGHT NOTE:**
Real match footage (Premier League, Champions League, La Liga, etc.) is fully
copyrighted by the leagues and broadcasters. Using it without a license will
result in YouTube copyright claims, demonetization, and channel strikes.

**What you CAN use legally:**
- Generic football action (no specific match, no logos, no commentary) — Pexels/Pixabay
- Scorebat embed codes (for website embeds only — NOT for downloading and re-encoding)
- Creative Commons licensed football clips on Wikimedia/YouTube (rare, older matches)
- AI-generated football atmosphere clips (your existing Pollinations + Veo pipeline)

The main approaches to accessing and using football video clips via API include:
1. Embeds for Highlights (Ready-to-Use)
If you want to display clips of goals and match recaps on your website or app, you can use third-party embed APIs. These APIs provide JSON feeds with links/embed codes from official media sources.Top Options: Platforms like ScoreBat on the RapidAPI marketplace provide free, embeddable video feeds for major leagues like the Premier League, La Liga, and Champions League.
2. Live Match Feeds (For Data & Betting Companies)
If your intention is to build sports apps or streaming platforms, you can leverage professional sports video APIs. These are commercial-grade feeds that stream live events, game recaps, and stats.Top Options: Highlightly and Sport Highlights API offer REST JSON APIs that connect event triggers (like goals and fouls) with short highlight clips.

Look for the options from where you can access the real football highlights api or something for free.



### 2.2 The correct B-roll strategy

If you can't find the free option, then instead of trying to use real match footage (which will get the channel struck),
build a B-roll library of LEGAL atmospheric clips:

**Category A: Pre-downloaded CC0 stock football clips**
Sources: Pexels Video (free, CC0), Pixabay Video (free, CC0), Coverr (free)
Types to download: stadium crowd, goalkeeper training, ball skills (no logos/faces),
  empty stadium, training ground, referee walking out, trophy presentation (generic)

Tell Antigravity:
"Create a B-roll library script `download_broll_library.py` that:
1. Downloads 20-30 CC0 football clips from Pexels Video API (free key at pexels.com/api)
   Search queries: 'football stadium crowd', 'soccer ball goal', 'football training',
   'stadium lights', 'football trophy', 'referee football', 'football fans cheering'
2. Saves them to `remotion-video/public/assets/broll/` with metadata tags
3. Commits them to the repo (total ~50-100MB for 30 clips at 720p)

Then in asset_orchestrator.py for ai_video scenes, before trying HF/Pollinations:
  4. Match the scene's ai_video_prompt keywords to the broll library metadata
  5. Return the best-matching local clip — instant, no API calls, always works"

**Category B: AI-generated atmospheric clips**
The existing Pollinations + Veo pipeline already handles this. When local B-roll
doesn't match, generate an atmospheric clip. The key rule (already in place):
NEVER try to generate named players — only atmosphere.

### 2.3 Pexels Video API integration

```python
# New function in media_sourcer.py

def fetch_pexels_video(query: str, output_path: str) -> bool:
    """
    Fetches a CC0 stock football video from Pexels.
    Pexels API is free — register at pexels.com/api for a key.
    """
    import requests
    
    PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
    if not PEXELS_API_KEY:
        return False
    
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "per_page": 5, "orientation": "landscape"},
        timeout=15
    )
    
    if r.status_code != 200:
        return False
    
    videos = r.json().get("videos", [])
    if not videos:
        return False
    
    # Pick the best quality 720p or 1080p file
    for video in videos:
        for vfile in video.get("video_files", []):
            if vfile.get("width", 0) >= 1280 and vfile.get("file_type") == "video/mp4":
                video_url = vfile["link"]
                vid_r = requests.get(video_url, timeout=60, stream=True)
                with open(output_path, 'wb') as f:
                    for chunk in vid_r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
    
    return False
```

Add `PEXELS_API_KEY` to `.env.example` and GitHub Secrets.

---

## Part 3: Statistics & Motion Graphics in Remotion

### 3.1 Upgrade DataVisualizationScene.tsx for football stats

The existing DataVisualizationScene supports bar_chart and line_chart.
Add these football-specific visualization types:

**A) Top scorer leaderboard** (for content like "Champions League goal stats")

```tsx
// In DataVisualizationScene.tsx — add leaderboard type

interface LeaderboardEntry {
  rank: number;
  name: string;        // e.g. "Cristiano Ronaldo"
  club: string;        // e.g. "Real Madrid"
  value: number;       // e.g. 140
  unit: string;        // e.g. "goals"
}

// Animated reveal: rows slide in from left one by one with 0.3s stagger
// Row 1 (top scorer) slides in first, row 5 last — creates countdown feel
// Each row: rank number (amber) | player name (white) | club (gray) | value (amber bold)
// Background: dark gradient, subtle grid lines
```

**B) Head-to-head comparison** (for topics like "Messi vs Ronaldo")

```tsx
interface HeadToHeadProps {
  playerA: { name: string; value: number; color: string };
  playerB: { name: string; value: number; color: string };
  metric: string;  // e.g. "Champions League Goals"
}

// Split screen: left half for player A, right half for player B
// Both bars grow toward center simultaneously from their respective sides
// Values count up using spring animation
// Middle divider line in white
```

**C) Timeline chart** (for "Evolution of Champions League goal scoring")

```tsx
interface TimelineProps {
  data: Array<{ year: number; value: number; event?: string }>;
  title: string;
}

// Line chart with year on X axis, value on Y axis
// Line draws itself (animated path from left to right over 2 seconds)
// Significant events shown as dots with labels
// Recharts LineChart with animated strokeDashoffset trick
```

### 3.2 Data injection from script

The documentary_generator.py Gemini prompt must generate data for these scene types.
Update the Groq/Gemini classification prompt to include:

```
For data_visualization scenes, you MUST provide structured data.

For leaderboard visual_type, provide:
  "leaderboard_data": [
    {"rank": 1, "name": "Cristiano Ronaldo", "club": "Real Madrid", "value": 140, "unit": "goals"},
    {"rank": 2, "name": "Lionel Messi", "club": "Barcelona", "value": 129, "unit": "goals"},
    ...up to 5 entries
  ]

For head_to_head visual_type, provide:
  "head_to_head_data": {
    "playerA": {"name": "Messi", "value": 129, "color": "amber"},
    "playerB": {"name": "Ronaldo", "value": 140, "color": "red"},
    "metric": "Champions League Goals"
  }

For timeline visual_type, provide:
  "timeline_data": [
    {"year": 1992, "value": 2.1, "event": "Competition rebranded"},
    {"year": 2000, "value": 2.8},
    ...
  ]
  "timeline_title": "Average Goals per Game"

MANDATORY RULE: For any topic involving goal records, player statistics,
match counts, or historical comparisons, at least ONE scene MUST be
data_visualization with the appropriate sub-type.
```

### 3.3 Motion graphics: chapter intro upgrade in Remotion

Replace the current static ChapterIntro.tsx with an animated one:

```tsx
// Upgrade ChapterIntro.tsx

export const ChapterIntro: React.FC<{
  chapterNumber: number;
  title: string;
  durationInFrames: number;
}> = ({ chapterNumber, title, durationInFrames }) => {
  const frame = useCurrentFrame();
  
  // 1. Black frame for first 6 frames
  // 2. Amber horizontal line sweeps across screen (frames 6-18)
  // 3. "CHAPTER X" text slams in from top (frames 12-20, spring animation)
  // 4. Chapter title fades in below (frames 20-30)
  // 5. Hold for remaining frames
  // 6. Fade to black on last 8 frames
  
  const lineProgress = interpolate(frame, [6, 18], [0, 1], { extrapolateRight: "clamp" });
  const chapterScale = spring({ frame: frame - 12, fps: 30, config: { damping: 12, stiffness: 200 } });
  const titleOpacity = interpolate(frame, [20, 30], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [durationInFrames - 8, durationInFrames], [1, 0], { extrapolateLeft: "clamp" });
  
  return (
    <AbsoluteFill style={{ backgroundColor: "#0A0A12", opacity: fadeOut }}>
      {/* Amber sweep line */}
      <div style={{
        position: "absolute", top: "45%", left: 0,
        width: `${lineProgress * 100}%`, height: 3,
        backgroundColor: "#F5A623"
      }} />
      {/* CHAPTER X */}
      <div style={{
        position: "absolute", top: "30%", left: "50%",
        transform: `translateX(-50%) scale(${chapterScale})`,
        color: "#F5A623", fontSize: 32, fontFamily: "Barlow Condensed, sans-serif",
        fontWeight: 700, letterSpacing: 8, textTransform: "uppercase"
      }}>
        Chapter {chapterNumber}
      </div>
      {/* Chapter title */}
      <div style={{
        position: "absolute", top: "52%", left: "50%",
        transform: "translateX(-50%)", opacity: titleOpacity,
        color: "#FFFFFF", fontSize: 52, fontFamily: "Barlow Condensed, sans-serif",
        fontWeight: 700, textAlign: "center", maxWidth: 900
      }}>
        {title}
      </div>
    </AbsoluteFill>
  );
};
```

---

## Part 4: Separate Hume API Keys for Long-form vs Shorts

### 4.1 The problem

The log shows all 3 Hume keys failing with E0300 (zero credits) for EVERY chapter.
This is because Shorts are consuming the Hume credits first (Shorts run more frequently —
they upload daily, long-form uploads less often), leaving nothing for long-form.

The fix is separate Hume key pools for each pipeline.

### 4.2 Implementation

In `.env.example` and GitHub Secrets, add:

```
# Long-form Hume TTS keys (use for football documentary + science long-form)
HUME_API_KEY_LONG_1=""
HUME_API_KEY_LONG_2=""
HUME_API_KEY_LONG_3=""
HUME_API_KEY_LONG_4=""
HUME_API_KEY_LONG_5=""

# Shorts Hume TTS keys (use for football shorts + science shorts)
HUME_API_KEY_SHORT_1=""
HUME_API_KEY_SHORT_2=""
HUME_API_KEY_SHORT_3=""
HUME_API_KEY_SHORT_4=""
HUME_API_KEY_SHORT_5=""
```

In `hume_tts.py`, accept a `key_pool` parameter:

```python
class HumeTTS:
    def __init__(self, key_pool: str = "auto"):
        """
        key_pool: "long_form" | "shorts" | "auto"
        "auto" uses the existing HUME_API_KEY_1/2/3 (backward compat)
        """
        if key_pool == "long_form":
            self.keys = [
                os.environ.get("HUME_API_KEY_LONG_1"),
                os.environ.get("HUME_API_KEY_LONG_2"),
                os.environ.get("HUME_API_KEY_LONG_3"),
            ]
        elif key_pool == "shorts":
            self.keys = [
                os.environ.get("HUME_API_KEY_SHORT_1"),
                os.environ.get("HUME_API_KEY_SHORT_2"),
                os.environ.get("HUME_API_KEY_SHORT_3"),
            ]
        else:
            # backward compat — use existing keys
            self.keys = [
                os.environ.get("HUME_API_KEY"),
                os.environ.get("HUME_API_KEY2"),
                os.environ.get("HUME_API_KEY3"),
            ]
        self.keys = [k for k in self.keys if k]  # filter None
```

In `long_main.py`:
```python
tts = HumeTTS(key_pool="long_form")
```

In `main.py` (Shorts):
```python
tts = HumeTTS(key_pool="shorts")
```

In `science_pipeline.py` for daily:
```python
tts = HumeTTS(key_pool="long_form")
```

In `science_pipeline.py` for shorts:
```python
tts = HumeTTS(key_pool="shorts")
```

Hume free tier gives you 10,000 characters per month per account.
Register at hume.ai with different email addresses for each key pool.
You need 6 free accounts total (3 for long-form, 3 for shorts) across both channels.

---

## Part 5: Script Quality Upgrade

The current Groq-generated scripts have these problems visible in the log:
- Title: "Uncovering the Secrets of Champions League Goal Stats" — generic
- No specific data points were included despite the topic being stats-heavy
- Edge TTS voice sounds robotic compared to Hume

### 5.1 Script prompt upgrade for statistics topics

For any topic containing keywords: "stats", "records", "goals", "history", "best", "top":

```
STATISTICS TOPIC RULES:
1. Every claim must have a specific number. Not "many goals" — "140 goals".
2. Include at least 3 specific match dates or seasons.
3. Include at least 1 comparison between 2 players or eras.
4. Opening sentence must state the most shocking number first.
5. Use active voice for goal descriptions: "Messi struck past Casillas" not
   "a goal was scored by Messi against Real Madrid".
```

### 5.2 Upgrade YouTube title formula

The uploaded title was "Uncovering the Secrets of Champions League Goal Stats".
This is vague, boring, and not searchable.

Update `long_main.py` to generate better titles:

```python
TITLE_TEMPLATES = {
    "stats":     "{hook_phrase}: The Numbers That Changed Football",
    "history":   "{hook_phrase}: The Story Nobody Told",
    "tactics":   "{hook_phrase}: How It Really Works",
    "shocking":  "{hook_phrase}: The Truth Behind the Headlines",
    "player":    "{hook_phrase}: The Career That Defined a Generation",
}

# Example outputs:
# "Champions League's Greatest Scorers: The Numbers That Changed Football"
# "Tiki-Taka Revolution: How It Really Works"
# "Iniesta's World Cup Winner: The Story Nobody Told"
```

---

## Part 6: Build Order for Antigravity

```
STEP 1 — Fix 3 active bugs from current log (1 hour)
  - Migrate comment_manager.py to google-genai SDK
  - Fix setAtTop comment pin error (remove or fix)
  - Download and commit 6 SFX files to remotion-video/public/assets/sounds/

STEP 2 — Wikipedia entity-first image lookup (2 hours)
  - Add get_wikipedia_entity_image() to media_sourcer.py
  - Update documentary_generator.py prompt to extract named_entities with wikipedia_lookup flag
  - Update asset_orchestrator.py image chain: Wikipedia REST API first, DDG last
  Test: run pipeline for "Cristiano Ronaldo Champions League record" — confirm
        his actual Wikipedia photo appears, not a generic footballer

STEP 3 — Pexels Video B-roll integration (1 hour)
  - Register at pexels.com/api (free), add PEXELS_API_KEY to .env
  - Add fetch_pexels_video() to media_sourcer.py
  - Wire into asset_orchestrator for ai_video scenes before HF/Pollinations
  - Create download_broll_library.py and pre-download 20 generic football clips
  Test: confirm ai_video scenes use Pexels clips or local broll, not color cards

STEP 4 — Separate Hume key pools (30 minutes)
  - Update HumeTTS class with key_pool parameter
  - Add HUME_API_KEY_LONG_1/2/3 and HUME_API_KEY_SHORT_1/2/3 to .env.example
  - Register new free Hume accounts, add keys to GitHub Secrets
  - Update long_main.py, science_pipeline.py (daily), shorts pipeline
  Test: run long-form — confirm it uses LONG keys, not SHORT keys

STEP 5 — Data visualization upgrades in Remotion (3 hours)
  - Add leaderboard, head_to_head, timeline scene types to DataVisualizationScene.tsx
  - Update documentary_generator.py prompt with mandatory stats data rules
  - Update MainVideo.tsx routing for new sub-types
  Test: run "Champions League goal stats" topic — confirm leaderboard scene appears

STEP 6 — Animated ChapterIntro.tsx (1 hour)
  - Rewrite ChapterIntro.tsx with amber sweep line + slam-in animation
  Test: render a chapter intro in isolation, review visually

STEP 7 — Script quality upgrade (1 hour)
  - Add statistics topic rules to Gemini/Groq prompt
  - Update YouTube title formula with template system
  Test: run "Top 10 Champions League scorers" — confirm specific numbers in script
        and punchy YouTube title generated

STEP 8 — End-to-end test
  Topic: "Lionel Messi's Champions League records"
  Expected:
    - Wikipedia photo of Messi (accurate)
    - Leaderboard data visualization
    - Pexels B-roll clip for atmospheric scenes
    - Long-form Hume keys used (not shorts keys)
    - Punchy title like "Messi's Champions League Legacy: The Numbers That Changed Football"
```

---

## Part 7: New API Keys Needed

| Key | Source | Cost | Purpose |
|-----|--------|------|---------|
| `PEXELS_API_KEY` | pexels.com/api | Free | Stock football video B-roll |
| `HUME_API_KEY_LONG_1/2/3/4/5` | hume.ai | Free (10k chars/mo each) | Long-form TTS |
| `HUME_API_KEY_SHORT_1/2/3/4/5` | hume.ai | Free (10k chars/mo each) | Shorts TTS |

Wikipedia REST API requires no key — it's completely free and open.

Total new free accounts needed: 11 (1 Pexels + 10 Hume)

---

## Summary: Before vs After

| Issue | Current | After upgrade |
|-------|---------|---------------|
| Wrong player images | Generic/random photos | Wikipedia entity-specific photos and other APIs |
| No match video | Color card fallback | Pexels CC0 B-roll or AI atmospheric |
| No statistics visuals | Mostly typewriter text | Leaderboard, head-to-head, timeline charts |
| Hume credits depleted | Shorts use all credits | Separate key pools per pipeline |
| Generic titles | "Uncovering the Secrets of..." | Punchy template-based titles |
| Boring chapter intros | Static text card | Amber sweep line + slam animation |
| DDG rate-limited | 100% failure rate | DDG removed from primary chain |

---

*Football Channel Visual Upgrade Plan v3.0*
