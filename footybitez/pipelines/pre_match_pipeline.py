import os
import sys
import json
import logging
import time
import argparse
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Ensure root path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("pre_match_pipeline")

REGISTRY_PATH = "match_registry.json"

def load_registry():
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
    return {"matches": {}}

def save_registry(registry):
    try:
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save registry: {e}")

def get_match_key(home_tla, away_tla, date_str):
    """Generates a unique deduplication key, e.g., POR_COD_20260618"""
    clean_date = date_str.split("T")[0].replace("-", "")
    return f"{home_tla}_{away_tla}_{clean_date}"

def get_gemini_pre_match_details(home, away, kickoff_str, venue):
    import json
    from google import genai
    from google.genai import types
    
    keys = []
    for suffix in ["", "2", "3"]:
        val = os.getenv(f"GEMINI_API_KEY{suffix}")
        if val:
            keys.append(val)
            
    if not keys:
        logger.warning("No GEMINI_API_KEY available for search grounding. Skipping Gemini checks.")
        
    prompt = f"""
    Search for the upcoming FIFA World Cup 2026 match between {home} and {away} on {kickoff_str} at {venue}.
    Gather:
    1. Head-to-head history (wins for {home}, draws, wins for {away}).
    2. Recent form (last 5 matches) for both {home} and {away}.
    3. Prediction statistics / winning probabilities (e.g. {home} win %, draw %, {away} win %).
    4. Key player to watch for {home} and their key stat, and key player to watch for {away} and their key stat.
    5. A short key storyline or talking point for this match.
    
    Provide the output strictly as a JSON object with these keys:
    {{
        "h2h": "e.g. 2 Wins, 1 Draw, 0 Losses",
        "form_a": "e.g. W D W L W",
        "form_b": "e.g. L D W W L",
        "prob_a": 45.0,
        "prob_draw": 25.0,
        "prob_b": 30.0,
        "player_a": "Player name",
        "player_a_stats": "e.g. 4 goals in qualifying",
        "player_b": "Player name",
        "player_b_stats": "e.g. 3 clean sheets",
        "storyline": "Short text detailing the main storyline"
    }}
    """
    
    for key in keys:
        for model in ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]:
            try:
                logger.info(f"[GeminiSearch] Fetching pre-match details via model={model}...")
                client = genai.Client(api_key=key)
                r1 = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
                time.sleep(2.5)
                r2 = client.models.generate_content(
                    model=model,
                    contents=f"Convert this text content into the requested JSON object format:\n\n{r1.text}",
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                data = json.loads(r2.text)
                required = ["h2h", "form_a", "form_b", "prob_a", "prob_draw", "prob_b", "player_a", "player_a_stats", "player_b", "player_b_stats", "storyline"]
                if all(k in data for k in required):
                    logger.info("[GeminiSearch] Pre-match grounding succeeded.")
                    return data
            except Exception as e:
                logger.warning(f"Gemini pre-match fetch failed on {model}: {e}")
                time.sleep(2)
                continue
                
    # ── Groq + DuckDuckGo Search Fallback ──────────────────────────────────
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        try:
            logger.info("[GroqSearch] Attempting Groq + DuckDuckGo fallback for pre-match details...")
            search_context = ""
            try:
                from ddgs import DDGS
            except ImportError:
                try:
                    from duckduckgo_search import DDGS
                except ImportError:
                    DDGS = None

            if DDGS:
                queries = [
                    f"{home} vs {away}",
                    f"{home} {away}",
                    f"{home} vs {away} World Cup"
                ]
                search_results = []
                for query in queries:
                    try:
                        logger.info(f"[GroqSearch] Searching DuckDuckGo for: '{query}'")
                        with DDGS() as ddgs:
                            res = list(ddgs.text(query, max_results=5))
                            if res:
                                search_results = res
                                break
                    except Exception as se:
                        logger.warning(f"DuckDuckGo search failed for query '{query}': {se}")
                        time.sleep(1)
                
                if search_results:
                    for r in search_results:
                        search_context += f"Title: {r.get('title')}\nSnippet: {r.get('body')}\nURL: {r.get('href')}\n\n"
                else:
                    logger.warning("[GroqSearch] No DuckDuckGo search results found.")
            else:
                logger.warning("[GroqSearch] DuckDuckGo search module (DDGS) is not available.")

            prompt = f"""
            Search Grounding Context:
            {search_context}

            Based on the context above (or your knowledge if the context is empty/insufficient), gather details for the upcoming FIFA World Cup 2026 match between {home} and {away} on {kickoff_str} at {venue}.
            Gather:
            1. Head-to-head history (wins for {home}, draws, wins for {away}).
            2. Recent form (last 5 matches) for both {home} and {away}.
            3. Prediction statistics / winning probabilities (e.g. {home} win %, draw %, {away} win %).
            4. Key player to watch for {home} and their key stat, and key player to watch for {away} and their key stat.
            5. A short key storyline or talking point for this match.
            
            Provide the output strictly as a JSON object with these keys:
            {{
                "h2h": "e.g. 2 Wins, 1 Draw, 0 Losses",
                "form_a": "e.g. W D W L W",
                "form_b": "e.g. L D W W L",
                "prob_a": 45.0,
                "prob_draw": 25.0,
                "prob_b": 30.0,
                "player_a": "Player name",
                "player_a_stats": "e.g. 4 goals in qualifying",
                "player_b": "Player name",
                "player_b_stats": "e.g. 3 clean sheets",
                "storyline": "Short text detailing the main storyline"
            }}
            """

            from groq import Groq
            client = Groq(api_key=groq_api_key)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt + "\n\nRespond ONLY with valid JSON."}],
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            text = completion.choices[0].message.content
            data = json.loads(text)
            required = ["h2h", "form_a", "form_b", "prob_a", "prob_draw", "prob_b", "player_a", "player_a_stats", "player_b", "player_b_stats", "storyline"]
            if all(k in data for k in required):
                logger.info("[GroqSearch] Pre-match grounding fallback succeeded.")
                return data
        except Exception as e:
            logger.error(f"[GroqSearch] Groq fallback failed for pre-match details: {e}")

    return get_fallback_pre_match_data(home, away)

def get_fallback_pre_match_data(home, away):
    return {
        "h2h": "First meeting in World Cup history",
        "form_a": "W D W L W",
        "form_b": "L D W W L",
        "prob_a": 40.0,
        "prob_draw": 30.0,
        "prob_b": 30.0,
        "player_a": f"{home} Captain",
        "player_a_stats": "Key playmaker",
        "player_b": f"{away} Captain",
        "player_b_stats": "Defensive rock",
        "storyline": f"A highly anticipated clash in the World Cup group stages between {home} and {away}."
    }

def run_pipeline(force_match_id=None, skip_upload=False):
    logger.info("Executing Pre-Match Video Generation Pipeline...")
    
    from footybitez.data.worldcup_data import WorldCupData
    from footybitez.content.script_generator import ScriptGenerator
    from footybitez.video.remotion_video_creator import RemotionVideoCreator
    from footybitez.youtube.uploader import YouTubeUploader
    from footybitez.socials.social_orchestrator import SocialOrchestrator
    from footybitez.media import card_generator
    
    fd_key = os.getenv("FOOTBALL_DATA_API_KEY", "")
    af_key = os.getenv("API_FOOTBALL_KEY", "")
    
    if not fd_key:
        logger.error("FOOTBALL_DATA_API_KEY not set. Stopping pipeline.")
        sys.exit(1)
        
    wc_data = WorldCupData(fd_key, af_key)
    registry = load_registry()
    
    # 1. Fetch upcoming matches (scheduled for next 3 days)
    try:
        upcoming = wc_data.get_upcoming_matches()
    except Exception as e:
        logger.error(f"Failed to fetch matches from API: {e}")
        return
        
    target_match = None
    
    if force_match_id:
        # User specified a specific match ID to force generate
        for m in upcoming:
            if str(m.get("id")) == str(force_match_id):
                target_match = m
                break
        if not target_match:
            logger.error(f"Match with ID {force_match_id} not found in scheduled fixtures.")
            return
    else:
        # Scan for match scheduled in the next 6 hours
        now = datetime.now(timezone.utc)
        for m in upcoming:
            utc_date_str = m.get("utcDate", "")
            if not utc_date_str:
                continue
            try:
                match_time = datetime.fromisoformat(utc_date_str.replace("Z", "+00:00"))
                diff_hours = (match_time - now).total_seconds() / 3600.0
                
                # We target matches scheduled in the next 6 hours
                if 0 <= diff_hours <= 6.0:
                    home_tla = m.get("homeTeam", {}).get("tla", m.get("homeTeam", {}).get("name", "")[:3].upper())
                    away_tla = m.get("awayTeam", {}).get("tla", m.get("awayTeam", {}).get("name", "")[:3].upper())
                    m_key = get_match_key(home_tla, away_tla, utc_date_str)
                    
                    # Deduplicate
                    if m_key in registry["matches"] and registry["matches"][m_key].get("pre_match_done"):
                        logger.info(f"Match {m_key} already processed for pre-match. Skipping.")
                        continue
                        
                    target_match = m
                    break
            except Exception as e:
                logger.error(f"Error parsing date for match: {e}")
                continue
                
    if not target_match:
        logger.info("No new matches found within the 6-hour window. Stopping pipeline cleanly.")
        return
        
    # Extract details
    match_id = target_match.get("id")
    home = target_match.get("homeTeam", {}).get("name", "Home")
    away = target_match.get("awayTeam", {}).get("name", "Away")
    home_tla = target_match.get("homeTeam", {}).get("tla", home[:3].upper())
    away_tla = target_match.get("awayTeam", {}).get("tla", away[:3].upper())
    kickoff_raw = target_match.get("utcDate", "")
    group = target_match.get("group", "GROUP STAGE").replace("_", " ")
    
    # Simple venue parsing
    venue = "World Cup Stadium"
    
    m_key = get_match_key(home_tla, away_tla, kickoff_raw)
    logger.info(f"Processing target match: {home} vs {away} (Key: {m_key})")
    
    # 2. Gather pre-match details via Gemini Grounding
    details = get_gemini_pre_match_details(home, away, kickoff_raw, venue)
    
    # 3. Draft commentary script
    script_gen = ScriptGenerator()
    script = script_gen.generate_script(
        topic=f"{home} vs {away} World Cup 2026 prediction",
        category="wc_pre_match",
        context=json.dumps(details)
    )
    
    if not script:
        logger.error("Failed to generate script.")
        return
        
    # 4. Draw broadcast graphic cards via card_generator
    # Initialize MediaSourcer first so it cleans the downloads directory before we write cards
    from footybitez.media.media_sourcer import MediaSourcer
    media_sourcer = MediaSourcer()
    
    temp_dir = "footybitez/media/downloads"
    os.makedirs(temp_dir, exist_ok=True)
    
    card1 = os.path.abspath(os.path.join(temp_dir, f"pre_card1_{m_key}.jpg"))
    card2 = os.path.abspath(os.path.join(temp_dir, f"pre_card2_{m_key}.jpg"))
    card3 = os.path.abspath(os.path.join(temp_dir, f"pre_card3_{m_key}.jpg"))
    card4 = os.path.abspath(os.path.join(temp_dir, f"pre_card4_{m_key}.jpg"))
    card5 = os.path.abspath(os.path.join(temp_dir, f"pre_card5_{m_key}.jpg"))
    card6 = os.path.abspath(os.path.join(temp_dir, f"pre_card6_{m_key}.jpg"))
    
    card_generator.draw_pre_match_card_1_hook(home, away, group, venue, card1)
    card_generator.draw_pre_match_card_2_form(home, away, details["form_a"], details["form_b"], card2)
    card_generator.draw_pre_match_card_3_h2h(home, away, details["h2h"], card3)
    card_generator.draw_pre_match_card_4_probability(home, away, details["prob_a"], details["prob_draw"], details["prob_b"], card4)
    card_generator.draw_pre_match_card_5_spotlight(details["player_a"], home, details["player_a_stats"], card5)
    card_generator.draw_pre_match_card_6_cta(home, away, card6)
    
    # Map assets to Remotion structure
    match_context = f"{home} {away} World Cup 2026"
    segment_media = []
    
    for i, seg in enumerate(script.get("segments", [])):
        kw = seg.get("visual_keyword", f"{home} vs {away} World Cup 2026")
        if match_context not in kw:
            kw = f"{kw} {match_context}"
            
        logger.info(f"Sourcing real match image for keyword: '{kw}'")
        fetched_images = media_sourcer.get_media(kw, count=1, prefer_real_match=True)
        
        # Match segment index to card
        if i == 0:
            card = card2
        elif i == 1:
            card = card3
        elif i == 2:
            card = card4
        else:
            card = card5
            
        if fetched_images:
            segment_media.append([card, fetched_images[0]])
        else:
            segment_media.append([card])
            
    visual_assets = {
        "title_card": card1,
        "profile_image": card5,
        "segment_media": segment_media,
        "outro_image": card6 # Outro
    }
    
    # 5. Compile video
    music_dir = "footybitez/music"
    bg_music = None
    if os.path.exists(music_dir):
        files = [f for f in os.listdir(music_dir) if f.endswith(".mp3")]
        if files:
            import random
            bg_music = os.path.join(music_dir, random.choice(files))
            
    video_creator = RemotionVideoCreator()
    video_path = video_creator.create_video(script, visual_assets, background_music_path=bg_music)
    logger.info(f"Pre-match video generated successfully: {video_path}")
    
    # Clean up MediaSourcer downloads
    try:
        media_sourcer.cleanup()
    except Exception as ce:
        logger.warning(f"Error cleaning MediaSourcer downloads: {ce}")
    
    # 6. Upload
    if not skip_upload:
        title = f"{home} vs {away} PREDICTION 🔥 Who Wins? #WorldCup2026 #Shorts"
        description = (
            f"FIFA World Cup 2026 | {home} vs {away} | {kickoff_raw} at {venue}\n\n"
            f"🔔 Subscribe for every World Cup match recap!\n\n"
            f"{script.get('full_text', '')}\n\n"
            f"#WorldCup2026 #{home} #{away} #FIFA #Football #Soccer #Shorts"
        )
        tags = ["world cup 2026", "fifa 2026", home, away, "shorts", "football", "soccer", "prediction"]
        
        uploader = YouTubeUploader()
        uploader.upload_video(video_path, title, description, tags)
        
        # Social cross-posting
        should_publish_socials = os.getenv("ENABLE_SOCIAL_PUBLISHING", "false").lower() == "true"
        if should_publish_socials:
            logger.info("Publishing pre-match short to Facebook, Instagram Reels...")
            socials = SocialOrchestrator(use_footybitez=True)
            socials.publish_to_all(video_path, title, description)
            
    # 7. Update Registry
    if m_key not in registry["matches"]:
        registry["matches"][m_key] = {
            "id": match_id,
            "home": home,
            "away": away,
            "datetime_utc": kickoff_raw,
            "status": target_match.get("status"),
            "pre_match_done": False,
            "post_match_done": False
        }
    registry["matches"][m_key]["pre_match_done"] = True
    save_registry(registry)
    logger.info(f"Registry updated: {m_key} pre_match_done = True")
    
    # Clean downloads
    try:
        import shutil
        shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
    except Exception as ce:
        logger.warning(f"Error cleaning downloads folder: {ce}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-id", help="Force run match by ID")
    parser.add_argument("--skip-upload", action="store_true", help="Generate video but do not upload")
    args = parser.parse_args()
    
    run_pipeline(force_match_id=args.fixture_id, skip_upload=args.skip_upload)
