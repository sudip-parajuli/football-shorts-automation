# Football Channel — Script Quality Fixes + World Cup Pipeline + Breaking News Pipeline
## For Antigravity

---

## ⚡ URGENCY NOTE

The 2026 FIFA World Cup starts June 11, 2026 — 25 days from now.
The World Cup pipeline needs to be live and tested BEFORE June 11.
Breaking news pipeline goes live ON June 11.
Fix the script quality issues in parallel — they affect every Short being published right now.

---

## Part 1: What's Wrong With the Current Shorts Scripts

### Problem 1: Stale player data (Mbappe / PSG issue)

The Haaland vs Mbappe Short said Mbappe "consistently scored around 30 goals per season
for Paris Saint-Germain." Mbappe left PSG for Real Madrid in summer 2024. This happened
because the Groq/Llama3 model's training data is stale and there is no live context
being injected into the prompt.

The context fetch is failing silently (the __NO_CONTEXT__ sentinel was added but if
the context source itself has outdated info, the script will still be wrong).

**Fix — tell Antigravity:**

In script_generator.py, add a CURRENT TRANSFER STATUS verification step for any
script that mentions a specific player:

```python
# Add to _get_prompt() for player-related topics:

PLAYER_VERIFICATION_RULE = """
CRITICAL: Before writing any fact about a player's current club, goals, or stats,
you MUST reflect on whether this information could have changed in the last 12 months.
- If you are not 100% certain a player is still at a specific club RIGHT NOW, 
  say "at [club] at the time" or omit the club name entirely.
- Never state a player's current club as fact unless you are certain it is still true.
- Transfer windows happen every summer and winter. When in doubt, omit.
- For stats: only use season-specific stats ("in the 2023-24 season, Mbappe scored X")
  not present-tense claims ("Mbappe scores X goals per season for PSG").
"""
```

Additionally, add a topic_type classifier to the Groq prompt. When topic_type is
"player_comparison" or "player_profile", prepend a temporal disclaimer:

```python
TEMPORAL_DISCLAIMER = """
This script is being generated in {current_year}. 
Any player career facts must be verified as current.
Do not reference clubs, contracts, or stats as "current" unless explicitly confirmed.
"""
```

### Problem 2: Wrong / irrelevant images

The Haaland vs Mbappe Short showed an AI-generated image of "random guys" instead of
the actual players. This happened because:
1. The image search query was too generic
2. When real images failed, the AI image fallback used a vague prompt that generated
   generic footballer silhouettes instead of recognisable player-related imagery

**Two-part fix:**

PART A — Smarter image search queries for player topics.
Tell Antigravity to update the image_cue generation in documentary_generator.py:

```
For player-specific topics, the image_cue must include the player's full name
as the primary search term. Example:
- BAD:  "football player scoring goal"
- GOOD: "Erling Haaland Manchester City goal celebration"
- BAD:  "two footballers competing"  
- GOOD: "Erling Haaland Kylian Mbappe comparison"

For comparison topics, generate TWO image cues — one per subject — so the
video can alternate between images of each player rather than showing one image.
```

PART B — Better AI image prompts when real images fail.
When all real image sources (Wikimedia, Unsplash, Pixabay, DDG) fail for a
player-specific query, the AI image prompt must reflect that it cannot generate
a real likeness of a named person:

```python
def _build_ai_image_prompt(self, image_cue: str, is_player_topic: bool) -> str:
    if is_player_topic:
        # Can't generate real player likenesses — generate context instead
        # e.g. for "Haaland vs Mbappe", generate stadium/kit/number context
        return (
            f"football match atmosphere related to: {image_cue}, "
            f"stadium crowd, team colors, cinematic sports photography, "
            f"no faces visible, dramatic lighting, professional sports photo style"
        )
    else:
        return f"photorealistic, cinematic, {image_cue}, dramatic sports photography"
```

This is important: AI image models cannot reliably generate recognisable likenesses of
real named people. Attempting to generate "Erling Haaland" produces a random person.
The correct approach is to generate atmospheric context (stadium, team colors, crowd)
and source real player photos separately from verified image sources.

**For real player photos specifically**, add these to the image search chain:
1. Wikipedia Commons (many licensed player photos)
2. The club's official press image search (e.g. "site:mancity.com haaland")
3. Getty Images embed search (embed-only, no download — but usable as a reference)

---

## Part 2: World Cup Pipeline

The World Cup runs June 11 – July 19, 2026. That is 39 days of the highest-traffic
football content period of the year. Your channel needs to be publishing World Cup
Shorts every day during this window.

### 2.1 Content Categories for World Cup Shorts

```
CATEGORY 1: Daily Quiz Shorts (publish every match day)
  Format: 3 questions about that day's matches or World Cup history
  Hook: "Think you know football? 3 World Cup questions — pause and answer each one"
  End card: "Comment your score below"
  
CATEGORY 2: Group Stage Previews (publish day before each group's first match)
  Format: "Group [X] preview — who goes through?"
  Hook: One surprising fact about a team in the group
  
CATEGORY 3: "Did You Know" World Cup Facts (publish daily even on non-match days)
  Format: Single surprising World Cup historical fact
  Hook: The most counterintuitive fact first
  
CATEGORY 4: Match Result Recaps (publish within 2 hours of final whistle)
  Format: Goals, scorers, key moments, group table update
  This is handled by the Breaking News pipeline (Part 3)
```

### 2.2 World Cup Pipeline Architecture

This is NOT a separate codebase — it is a new pipeline MODE within the existing
footybitez system, triggered by a new GitHub Actions workflow.

**New file: `worldcup_pipeline.py`**

```python
# footybitez/pipelines/worldcup_pipeline.py

class WorldCupPipeline:
    
    CONTENT_CATEGORIES = [
        "wc_quiz",          # Daily quiz with 3 questions
        "wc_fact",          # Single surprising fact
        "wc_group_preview", # Group stage preview
        "wc_player_spotlight", # One player to watch
        "wc_history",       # Historical World Cup comparison
    ]
    
    def run(self, category: str, match_date: str = None):
        """
        category: one of CONTENT_CATEGORIES
        match_date: ISO date string, defaults to today
        """
        topic = self._generate_topic(category, match_date)
        script = self._generate_wc_script(topic, category)
        assets = self.asset_orchestrator.fetch_all(script["visual_scenes"])
        video = self.video_creator.create(script, assets)
        thumbnail = self.thumbnail_generator.generate(topic, script)
        self.uploader.upload(video, thumbnail, script["title"], script["tags"])
```

**New GitHub Actions workflow: `worldcup.yml`**

```yaml
name: World Cup Daily
on:
  schedule:
    # Runs twice daily during World Cup window (June 11 - July 19)
    - cron: '0 8 * * *'   # 8am UTC — morning fact/quiz
    - cron: '0 20 * * *'  # 8pm UTC — evening recap/preview
  workflow_dispatch:       # Manual trigger for same-day content
    inputs:
      category:
        description: 'Content category'
        required: true
        default: 'wc_fact'
        type: choice
        options:
          - wc_quiz
          - wc_fact
          - wc_group_preview
          - wc_player_spotlight
          - wc_history

jobs:
  worldcup:
    runs-on: ubuntu-latest
    # Only run during World Cup window
    if: |
      github.event_name == 'workflow_dispatch' ||
      (
        format('{0}-{1:02d}-{2:02d}', 
          github.run_started_at | date('yyyy'),
          github.run_started_at | date('MM') | int,
          github.run_started_at | date('dd') | int
        ) >= '2026-06-11' &&
        format(...) <= '2026-07-19'
      )
```

### 2.3 World Cup Quiz Format

The quiz is your highest-engagement format. Tell Antigravity to add a
`generate_wc_quiz()` method to worldcup_pipeline.py:

```
Quiz script format:
- 3 questions total, increasing difficulty
- Each question shown as text overlay on screen for 5 seconds
- Answer revealed after 3-second pause ("The answer is...")
- Final screen: "How many did you get right? Comment below!"
- Always end with a World Cup 2026-specific teaser: 
  "The answer might surprise you at this year's tournament..."

Example output structure:
{
  "title": "3 World Cup Questions — Can You Get All 3? 🏆",
  "questions": [
    {
      "question": "Which country has won the most World Cups?",
      "options": ["Germany", "Brazil", "Italy", "Argentina"],
      "answer": "Brazil (5 times)",
      "difficulty": "easy",
      "display_seconds": 5
    },
    ...
  ],
  "teaser": "Brazil face Morocco on June 13 — will they add a 6th?",
  "cta": "Comment your score: 1/3, 2/3, or 3/3! ⬇️"
}
```

The quiz format is a text-heavy visual in Remotion/MoviePy — questions appear as
kinetic_text slides, answers appear with a color-reveal animation (question text
turns green for correct answer). This needs a new `_render_quiz_slide()` method
in video_creator.py.

### 2.4 World Cup Data Source

Use **football-data.org** for World Cup fixture data — it is completely free forever,
no credit card, includes the World Cup competition endpoint:

```python
# worldcup_data.py
import requests

FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
WC_2026_ID = "WC"  # competition code

class WorldCupData:
    def __init__(self, api_key: str):  # Free key from football-data.org
        self.headers = {"X-Auth-Token": api_key}
    
    def get_today_matches(self) -> list:
        r = requests.get(f"{FOOTBALL_DATA_BASE}/competitions/WC/matches",
                        params={"status": "SCHEDULED,LIVE,FINISHED"},
                        headers=self.headers)
        return r.json().get("matches", [])
    
    def get_standings(self) -> dict:
        r = requests.get(f"{FOOTBALL_DATA_BASE}/competitions/WC/standings",
                        headers=self.headers)
        return r.json()
    
    def get_scorers(self) -> list:
        r = requests.get(f"{FOOTBALL_DATA_BASE}/competitions/WC/scorers",
                        headers=self.headers)
        return r.json().get("scorers", [])
```

Add `FOOTBALL_DATA_API_KEY` to `.env.example`. Free registration at football-data.org.

---

## Part 3: Breaking News Pipeline

This is a separate pipeline that monitors live match events and publishes Shorts
within 60-90 minutes of a match ending.

### 3.1 What It Covers

```
TRIGGER EVENTS (each becomes a Short):
- Full-time result: "X beat Y [score] — here's what happened"
- Upset/shock result: "SHOCK RESULT: [underdog] beats [favorite]"  
- Hat trick: "[Player] scored a hat trick in [match]"
- Red card: "[Player] sent off in [match] — here's why"
- Penalty shootout: "[match] goes to penalties — every kick"
- Last-minute winner: "90+[X]' — [player] wins it for [team]"
```

### 3.2 API Stack (All Free)

| API | Purpose | Free Limit | Sign Up |
|---|---|---|---|
| **football-data.org** | Fixtures, results, goals, cards | 10 req/min, free forever | football-data.org/client |
| **BSD (Bzzoiro Sports Data)** | Live scores, lineups, events, ML predictions | No rate limit, completely free | sports.bzzoiro.com |
| **API-Football (RapidAPI)** | Backup live events | 100 req/day free | rapidapi.com |

**Primary**: football-data.org for World Cup (officially supported, reliable)
**Secondary**: BSD for all other leagues (no rate limit is a major advantage)
**Backup**: API-Football for cross-verification

### 3.3 Breaking News Pipeline Architecture

**New file: `breaking_news_pipeline.py`**

```python
# footybitez/pipelines/breaking_news_pipeline.py
import time
from datetime import datetime

class BreakingNewsPipeline:
    
    POLL_INTERVAL_SECONDS = 300   # Check every 5 minutes
    POST_MATCH_WINDOW_HOURS = 2   # Only post within 2hrs of final whistle
    
    def monitor(self):
        """
        Main loop — runs continuously during match windows.
        Called by GitHub Actions on a 5-minute cron schedule.
        Uses a state file to track which matches have already been processed.
        """
        matches = self.football_data.get_finished_matches_last_2hrs()
        state = self._load_state()  # dict of match_id → processed bool
        
        for match in matches:
            if match["id"] in state:
                continue  # Already processed
            
            events = self._extract_newsworthy_events(match)
            for event in events:
                script = self._generate_news_script(event)
                video = self._create_news_video(script)
                self.uploader.upload_short(video, priority="breaking")
                time.sleep(300)  # Space uploads 5 mins apart
            
            state[match["id"]] = True
        
        self._save_state(state)
    
    def _extract_newsworthy_events(self, match: dict) -> list:
        events = []
        
        # Always: full-time result
        events.append({
            "type": "full_time_result",
            "match": match,
            "priority": 1
        })
        
        # Upset: underdog wins (check odds/expected result)
        if self._is_upset(match):
            events.append({"type": "upset", "match": match, "priority": 0})
        
        # Hat trick
        for scorer in match.get("goals", []):
            if scorer["count"] >= 3:
                events.append({
                    "type": "hat_trick",
                    "player": scorer["player"],
                    "match": match,
                    "priority": 0
                })
        
        # Red card
        for card in match.get("bookings", []):
            if card["card"] == "RED_CARD":
                events.append({
                    "type": "red_card",
                    "player": card["player"],
                    "team": card["team"],
                    "match": match,
                    "priority": 1
                })
        
        return sorted(events, key=lambda e: e["priority"])
```

### 3.4 News Script Generation

Breaking news scripts are SHORT — 30-45 seconds max (not the 130-150 word format).
Add a `generate_breaking_news_script()` method to script_generator.py:

```
BREAKING NEWS script prompt rules:
- Max 60 words total (30-45 seconds at narration pace)
- Structure: [RESULT] → [KEY MOMENT] → [ONE REACTION/STAT] → [CTA]
- Always start with the scoreline in the first sentence
- Name the goalscorers with minute of goal
- If red card: name the player, minute, and reason (if known)
- End with: "Full match analysis coming soon — follow for more"
- Never include speculation or analysis — facts only
- Tone: urgent, fast, like a news ticker

Example output:
"FULL TIME: Spain 3 - 1 Morocco. Yamal opened the scoring in the 
23rd minute, with Torres adding two in the second half. 
Hakimi pulled one back from the spot in 71 minutes but Spain 
held on. Spain top Group E and face the Group F runner-up in 
the Round of 32. Follow for the full breakdown."
```

### 3.5 Breaking News GitHub Actions Workflow

**New file: `.github/workflows/breaking_news.yml`**

```yaml
name: Breaking News Monitor
on:
  schedule:
    # Every 5 minutes during typical match hours (14:00-23:00 UTC)
    - cron: '*/5 14-23 * * *'
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    timeout-minutes: 4  # Must finish before next 5-min trigger
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run breaking news monitor
        run: python -m footybitez.pipelines.breaking_news_pipeline
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
          FOOTBALL_DATA_API_KEY: ${{ secrets.FOOTBALL_DATA_API_KEY }}
          BSD_API_KEY: ${{ secrets.BSD_API_KEY }}
```

**Critical**: The monitor must finish in under 4 minutes or it will overlap with
the next trigger. Use a hard timeout wrapper around the monitor() call:

```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Monitor exceeded 4-minute window")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(220)  # 3 min 40 sec — leave 20s buffer
```

### 3.6 State File for Deduplication

The monitor needs to remember which matches it has already posted about across
GitHub Actions runs (each run starts fresh — no in-memory state):

```python
# State file: footybitez/data/news_state.json
# Updated in the repo via git commit after each run

STATE_FILE = "footybitez/data/news_state.json"

# After processing, commit state back to repo:
# git add footybitez/data/news_state.json
# git commit -m "Update news state [skip ci]"
# git push
# (Use [skip ci] to prevent triggering other workflows)
```

---

## Part 4: Build Order for Antigravity

```
IMMEDIATE (this week — before World Cup starts June 11):

Step 1 — Fix script quality issues (Part 1)
  - Add player verification rule to _get_prompt()
  - Add temporal disclaimer with current year injection
  - Update image_cue generation for player topics (two cues for comparisons)
  - Add _build_ai_image_prompt() with is_player_topic flag
  Test: Re-run "Haaland vs Mbappe" topic and verify Mbappe is described 
        as "at Real Madrid" not "at PSG"

Step 2 — Register football-data.org API key
  - Go to football-data.org/client, register free account
  - Add FOOTBALL_DATA_API_KEY to GitHub Actions secrets
  - Build worldcup_data.py with get_today_matches(), get_standings(), get_scorers()
  Test: Print today's WC fixtures to console

Step 3 — Build worldcup_pipeline.py
  - Implement all 5 content categories
  - Add generate_wc_quiz() with 3-question format
  - Add _render_quiz_slide() to video_creator.py
  - Build worldcup.yml GitHub Actions workflow
  Test: Run wc_fact and wc_quiz categories manually, review output videos

Step 4 — Build breaking_news_pipeline.py
  - Register BSD API key (sports.bzzoiro.com — free, no credit card)
  - Implement monitor(), _extract_newsworthy_events(), state file deduplication
  - Add generate_breaking_news_script() to script_generator.py
  - Build breaking_news.yml workflow with 5-minute cron and 4-minute timeout
  - Add [skip ci] git commit for state updates
  Test: Manually trigger with a completed match ID, verify Short is generated

Step 5 — Activate before June 11
  - Enable worldcup.yml and breaking_news.yml workflows in GitHub Actions
  - Publish 3-5 World Cup preview Shorts before the tournament starts
    (group previews, "5 facts about WC 2026", "who will win?" quiz)
  - Monitor the first match day (June 11: Mexico vs South Africa) live
```

---

## Part 5: New API Keys to Add

| Key | Source | Cost | Required for |
|---|---|---|---|
| `FOOTBALL_DATA_API_KEY` | football-data.org/client | Free forever | World Cup data, Breaking news |
| `BSD_API_KEY` | sports.bzzoiro.com | Free, no limits | Breaking news (all leagues) |
| `API_FOOTBALL_KEY` | rapidapi.com (API-Football) | Free (100/day) | Backup live scores |

All three are free. football-data.org requires email registration. BSD requires
registration. API-Football requires a RapidAPI account.

---

## Summary

| Issue / Feature | Urgency | Effort |
|---|---|---|
| Fix stale player data in scripts | High — live now | Low — prompt change |
| Fix irrelevant images for player topics | High — live now | Medium |
| World Cup daily Shorts pipeline | Critical — starts June 11 | Medium |
| World Cup quiz format | High | Medium |
| Breaking news pipeline | Critical — starts June 11 | High |
| football-data.org integration | Critical — needed by June 11 | Low |

---

*Football Channel Expansion Plan v1.0 — World Cup 2026 Edition*
