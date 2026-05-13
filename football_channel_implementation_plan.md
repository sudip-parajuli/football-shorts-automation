## Part 1: Hook Styles (for Football Content)

Use one of these per video. Never combine two in the same opening.

| # | Hook Style | Description | Example Opening Line |
|---|---|---|---|
| 1 | **The Verdict First** | State the most shocking outcome immediately — then explain how it happened | *"Juventus won the title. Then lost it. Then won it again. Then had it stripped. This is the story of how Italian football ate itself."* |
| 2 | **The Single Moment** | Zoom into one specific second — a whistle, a phone call, a vote — that changed everything | *"On May 5th, 2006, at 11:47pm, a wiretap recorded a phone call that would end careers, relegate champions, and expose the rottenest secret in European football."* |
| 3 | **The Number That Breaks Context** | Lead with a statistic so extreme it demands explanation | *"66 people walked into Ibrox that day. None of them walked out."* |
| 4 | **The Betrayal Frame** | Establish trust first — then shatter it | *"For 130 years, Celtic and Rangers fans shared the same streets, the same pubs, the same city. They just wanted to kill each other every second Saturday."* |
| 5 | **The Unknown Name** | Open on a person nobody in the audience knows — who turned out to matter enormously | *"Nobody outside Singapore had heard of Dan Tan in 2013. By the end of the year, he had his fingerprints on matches in five different leagues."* |
| 6 | **The Fake Resolution** | Pretend the story is over — then reveal it isn't | *"FIFA declared the corruption era closed in 2016. They were wrong. Here's what they didn't tell you."* |
| 7 | **The Atmosphere Drop** | Open with pure sensory/crowd description — then cut to darkness | *"Sixty thousand people singing the same song. The noise so loud you feel it in your chest. Now imagine that whole stadium built on a lie."* |

---

## Part 2: Tone Options (for Football Content)

| Tone | Voice Description | Best For | Avoid |
|---|---|---|---|
| **Investigative Journalist** | Cold, precise, evidence-led. Names sources. Uses exact dates, amounts, court documents. Delivers revelations without editorializing. | Scandal, corruption, match-fixing | Rivalry/fan content |
| **Storyteller** | Cinematic. Builds scenes. Treats football history like a screenplay — characters, conflict, resolution. Short punchy sentences at dramatic peaks. | Rivalries, golden eras, legendary players | Dry statistics |
| **Fan's Voice** | Speaks directly to someone who already knows the basics. Assumes knowledge. Uses club nicknames, slang. Irreverent, opinionated. | Derby histories, controversial moments | International/global audience topics |
| **Documentary Narrator** | Authoritative but warm. The David Attenborough of football. Gravitas without coldness. | Historical retrospectives, tragedy stories | Breaking news |
| **Countdown / Listicle** | Punchy, fast-paced, each item self-contained. Tease the next item at the end of each. | Top 10 videos, "Worst ever" videos | Deep single-topic dives |

---

## Part 3: Script Generation Prompt (for Antigravity to Use)

Antigravity should call the Gemini API with the following system prompt and fill in `{VARIABLES}` from user input.

```
SYSTEM PROMPT:
You are a professional YouTube scriptwriter specializing in football (soccer) documentary content. Your scripts are used in a fully automated video channel that uses only still images — no video footage. Scripts must be written for narration over images.

STRICT RULES — never violate these:
1. Never open with "In the world of football..." or "Football has always been..." or any broad-context preamble.
2. Never use filler words: legendary, iconic, incredible, stunning, amazing, beautiful game (unless in a direct quote).
3. Never write a closing line that says viewers "continue to explore" or that football "will always have a place in our hearts."
4. Every claim must be specific: name the person, the date, the amount, the scoreline. No vague superlatives.
5. Sentence rhythm: after every 2-3 long sentences, write 1 short punchy sentence (under 8 words). Read it aloud — if it sounds robotic, rewrite it.
6. After every sentence that needs a visual, write a bracketed image cue: [image: packed stadium aerial view 1960s black and white]. These cues are for the automated image sourcing system — make them specific enough to search for.

INPUT VARIABLES:
- Topic: {TOPIC}
- Hook style: {HOOK_STYLE} — see hook descriptions below
- Tone: {TONE} — see tone descriptions below
- Length: {LENGTH_WORDS} words
- Chapter titles: {CHAPTER_TITLES} (comma-separated, or "auto" to generate)

HOOK STYLES:
- verdict_first: State the most shocking outcome immediately, then explain how it happened.
- single_moment: Zoom into one specific second — a wiretap, a whistle, a vote — that changed everything. Include a real date and time if known.
- number_breaks_context: Lead with a statistic so extreme it forces the viewer to keep watching.
- betrayal_frame: Establish trust or normalcy first, then shatter it in one sentence.
- unknown_name: Open on a person the audience has never heard of who turned out to matter enormously.
- fake_resolution: Pretend the story is resolved — then reveal it isn't.
- atmosphere_drop: Open with crowd/stadium sensory detail, then cut immediately to darkness or crisis.

TONE DESCRIPTIONS:
- investigative: Cold, precise, evidence-led. Uses exact dates, court documents, financial figures. Never editorializes.
- storyteller: Cinematic. Builds scenes and characters. Short punchy sentences at dramatic peaks.
- fan_voice: Direct address. Assumes football knowledge. Uses slang and club nicknames. Opinionated.
- documentary: Authoritative and warm. Gravitas without coldness. Appropriate for tragedy and history.
- countdown: Fast-paced listicle. Each item self-contained. Tease the next item at each segment end.

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{
  "title": "video title (punchy, under 60 characters, no colons)",
  "chapters": [
    {
      "chapter_number": 1,
      "chapter_title": "string",
      "script": "full narration text with [image: ...] cues inline",
      "estimated_duration_seconds": 45
    }
  ],
  "total_words": 850,
  "image_queries": ["query 1", "query 2", ...],
  "tags": ["football", "scandal", ...]
}

Return only the JSON. No preamble, no markdown fences.
```

---

## Part 4: Image Sourcing System

Since the channel uses only still images, Antigravity should build an image pipeline that:

### 4.1 Sources (in priority order)
1. **Wikimedia Commons API** — `https://commons.wikimedia.org/w/api.php` — Free, no attribution issues for commercial use (check license per image)
2. **Unsplash API** — `https://api.unsplash.com/search/photos` — Free tier, 50 requests/hour, attribution required in video description
3. **Pixabay API** — `https://pixabay.com/api/` — Free, no attribution required
4. **NASA/Getty embed fallback** — For historical sports images, use publicly embedded press images (embed only, no download)

### 4.2 Image Query Extraction
The script JSON returns `image_queries[]`. For each chapter, Antigravity should:
1. Parse all `[image: ...]` cues from the script text
2. Send each cue as a search query to the image APIs above
3. Download 3 candidate images per cue, save to `/assets/images/{chapter_number}/{cue_index}/`
4. Select the highest-resolution result with a valid license

### 4.3 Image Fallback Logic
```
if (wikimedia_result.license includes "CC" or "public domain") → use it
else if (unsplash_result exists) → use it, add credit to description
else if (pixabay_result exists) → use it
else → use a solid color card with text overlay (Remotion TextLayer)
```

---

## Part 5: Remotion Video Composition

### 5.1 Project Structure
```
/football-channel-automation/
  /src/
    compositions/
      MainVideo.tsx       ← root composition
      ChapterIntro.tsx    ← chapter title card
      ImageSlide.tsx      ← single image + narration segment
      LowerThird.tsx      ← name/date overlay
      EndCard.tsx         ← subscribe + next video
    hooks/
      useScript.ts        ← loads generated script JSON
      useImageAssets.ts   ← loads image manifest
    utils/
      timing.ts           ← word-count to duration calculator
  /public/
    /assets/
      /images/            ← sourced images
      /audio/             ← TTS narration files
      fonts/
  /scripts/
    generate.js           ← main pipeline runner
    fetch-images.js
    tts.js
```

### 5.2 Remotion Composition Rules

**ImageSlide component** — the core building block:
```tsx
// Each script segment becomes one ImageSlide
// Duration = word count of segment × 0.45 seconds (average narration pace)
// Image: Ken Burns effect (slow zoom 100% → 108% over segment duration)
// Text: no subtitle overlay — let narration carry it
// Transition: 12-frame cross-dissolve between slides
```

**Visual style for football channel:**
```
Background: #0a0a0a (near black)
Chapter title cards:
  - Font: Bold condensed sans (use Google Fonts: Barlow Condensed 700)
  - Color: White text on black, with a single accent stripe in club colors if relevant
  - Duration: 48 frames (2 seconds at 24fps)
Lower thirds (for names/dates):
  - Small white text, bottom-left, 70% opacity background bar
  - Fade in: 8 frames, hold, fade out: 8 frames
Ken Burns: always zoom in (never out) — creates urgency
```

**Chapter intro card template:**
```
Chapter number: small, uppercase, letter-spaced, amber (#F5A623)
Chapter title: large, white, bold condensed
Duration: 2 seconds, then cross-dissolve to first image
```

### 5.3 Audio Pipeline

1. **TTS narration**: Use Hume, if failed use Google Cloud TTS (Neural2 voice, en-US-Neural2-D for male authoritative tone) or ElevenLabs API for more natural delivery
2. **Background music**: Use royalty-free tracks from `freemusicarchive.org` API or `incompetech.com`
   - Music volume: -18dB under narration
   - For scandal/dark content: minor key, slow tempo
   - For rivalry/hype content: orchestral builds
3. **Audio ducking**: Lower music by -6dB additional during the first and last 5 seconds of each chapter

### 5.4 Timing Calculation
```javascript
// utils/timing.ts
export function wordsToFrames(wordCount: number, fps: number = 24): number {
  const wordsPerMinute = 140; // conservative narration pace
  const seconds = (wordCount / wordsPerMinute) * 60;
  return Math.ceil(seconds * fps);
}
// Add 48 frames per chapter for chapter title card
// Add 72 frames for intro card
// Add 96 frames for end card
```

---

## Part 6: Full Pipeline Runner

Antigravity should build a single `generate.js` script that runs the entire pipeline end-to-end:

```javascript
// generate.js — run with: node generate.js --topic "Calciopoli scandal" --hook single_moment --tone investigative --length 900

const steps = [
  "1. Call Gemini API with system prompt → receive script JSON",
  "2. Parse image_queries[] from script JSON",
  "3. For each image query: call Wikimedia → Unsplash → Pixabay in order",
  "4. Download selected images to /public/assets/images/",
  "5. Send script text (chapter by chapter) to TTS API → save MP3 files",
  "6. Download background music track from Free Music Archive",
  "7. Mix audio: narration + music with ducking (FFmpeg)",
  "8. Write Remotion props JSON: /public/props.json",
  "9. Run: npx remotion render src/index.ts MainVideo output/video.mp4",
  "10. Write video description file: output/description.txt (with image credits)",
];
```

---

## Part 7: What to Fix in the Current Scripts (Specific Notes)

### "Darkest Secrets" video
- **Current problem**: Opens with "A single match that changed the course of history forever" — this is vague and tells the viewer nothing. What match? When?
- **Fix**: Use `single_moment` hook. Open on the specific wiretap date. Name the prosecutor.
- **Chapter structure**: Currently feels like a Wikipedia list. Each chapter should end with a 1-sentence cliffhanger that leads into the next.

### "Celtic vs Rangers" video  
- **Current problem**: "A rivalry so intense it divides a nation" is cliché — every rivalry video opens this way.
- **Fix**: Use `number_breaks_context` hook. Open on the Ibrox disaster death toll, then pull back to explain the full rivalry.
- **Missing**: The script never names specific players. Naming Jimmy Johnstone, Brian Laudrup, Henrik Larsson makes it real.
- **Sectarianism section**: Currently handled too gently. The `investigative` tone handles sensitive topics with more specificity and less editorializing — which is actually more respectful.
