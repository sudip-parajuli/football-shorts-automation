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
logger = logging.getLogger("post_match_pipeline")

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
    clean_date = date_str.split("T")[0].replace("-", "")
    return f"{home_tla}_{away_tla}_{clean_date}"

def get_gemini_post_match_details(home, away, date_str, venue, hs, as_):
    import json
    from google import genai
    from google.genai import types
    
    keys = []
    for suffix in ["", "2", "3"]:
        val = os.getenv(f"GEMINI_API_KEY{suffix}")
        if val:
            keys.append(val)
            
    if not keys:
        logger.warning("No GEMINI_API_KEY available for search grounding. Using fallbacks.")
        return get_fallback_post_match_data(home, away, hs, as_)
        
    prompt = f"""
    Search for the finished FIFA World Cup 2026 match between {home} and {away} played on {date_str} at {venue}. The final score was {home} {hs} - {as_} {away}.
    Gather:
    1. Scorers list (names of players who scored goals and their corresponding minutes).
    2. Detailed match statistics:
       - Possession percentage for home and away.
       - Total shots for home and away.
       - Shots on target for home and away.
       - Corner kicks for home and away.
       - Expected goals (xG) for home and away (e.g. 1.84 and 0.92, or 'N/A' if not found).
    3. Man of the match (MOTM) name, rating (out of 10), and their main stat.
    4. Key standout moment or talking point from the match.
    5. Standings table for this group (positions 1 to 4: team, played, gd, pts).
    6. Next match details for both teams.
    
    Provide the output strictly as a JSON object with these keys:
    {{
        "scorers": [
            {{"player": "Scorer name", "minute": 24, "team": "Home"/"Away", "type": "Goal", "detail": null}}
        ],
        "stats": {{
            "possession": {{"home": "60%", "away": "40%"}},
            "shots": {{"home": 12, "away": 8}},
            "shots_on_target": {{"home": 5, "away": 3}},
            "corners": {{"home": 6, "away": 4}},
            "xg": {{"home": "1.8", "away": "0.9"}}
        }},
        "motm": {{
            "player": "Player Name",
            "rating": 8.7,
            "stat": "2 assists, 4 chances created"
        }},
        "standout_moment": "Text describing the key standout moment",
        "standings": [
            {{"pos": 1, "team": "Team Name", "played": 3, "gd": "+4", "pts": 7}},
            {{"pos": 2, "team": "Team Name", "played": 3, "gd": "+1", "pts": 5}},
            {{"pos": 3, "team": "Team Name", "played": 3, "gd": "-2", "pts": 3}},
            {{"pos": 4, "team": "Team Name", "played": 3, "gd": "-3", "pts": 1}}
        ],
        "next_a": "Next opponent and date for home team",
        "next_b": "Next opponent and date for away team"
    }}
    """
    
    for key in keys:
        for model in ["gemini-2.5-flash", "gemini-1.5-flash"]:
            try:
                logger.info(f"[GeminiSearch] Fetching post-match details via model={model}...")
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
                required = ["scorers", "stats", "motm", "standout_moment", "standings", "next_a", "next_b"]
                if all(k in data for k in required):
                    logger.info("[GeminiSearch] Post-match grounding succeeded.")
                    return data
            except Exception as e:
                logger.warning(f"Gemini post-match fetch failed on {model}: {e}")
                time.sleep(2)
                continue
                
    return get_fallback_post_match_data(home, away, hs, as_)

def get_fallback_post_match_data(home, away, hs, as_):
    return {
        "scorers": [],
        "stats": {
            "possession": {"home": "50%", "away": "50%"},
            "shots": {"home": 10, "away": 10},
            "shots_on_target": {"home": 4, "away": 4},
            "corners": {"home": 5, "away": 5},
            "xg": {"home": "1.0", "away": "1.0"}
        },
        "motm": {
            "player": "Star player",
            "rating": 7.5,
            "stat": "Controlled the midfield"
        },
        "standout_moment": "An intense battle on the pitch with both teams fighting hard.",
        "standings": [
            {"pos": 1, "team": home, "played": 1, "gd": f"{hs-as_:+}", "pts": 3 if hs > as_ else (1 if hs == as_ else 0)},
            {"pos": 2, "team": away, "played": 1, "gd": f"{as_-hs:+}", "pts": 3 if as_ > hs else (1 if hs == as_ else 0)}
        ],
        "next_a": "Check schedule for upcoming matchday details.",
        "next_b": "Check schedule for upcoming matchday details."
    }

def run_pipeline(force_match_id=None, skip_upload=False):
    logger.info("Executing Post-Match Video Generation Pipeline...")
    
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
    
    # Fetch today's finished matches
    try:
        # Load match data from today
        import datetime as dt
        today = str(dt.date.today())
        matches_today = wc_data._rate_limited_get(
            f"https://api.football-data.org/v4/competitions/2000/matches",
            params={"dateFrom": today, "dateTo": today}
        ).get("matches", [])
    except Exception as e:
        logger.error(f"Failed to fetch matches from API: {e}")
        return
        
    target_match = None
    
    if force_match_id:
        # User specified a specific match ID to force generate
        # Try fetching this specific match details
        try:
            target_match = wc_data._rate_limited_get(f"https://api.football-data.org/v4/matches/{force_match_id}")
        except Exception as e:
            logger.error(f"Failed to fetch match details for {force_match_id}: {e}")
            return
    else:
        # Scan for match finished in the last 2.5 hours
        now = datetime.now(timezone.utc)
        for m in matches_today:
            if m.get("status") != "FINISHED":
                continue
                
            utc_date_str = m.get("utcDate", "")
            if not utc_date_str:
                continue
            try:
                # football-data.org lastUpdated or utcDate
                # We check the start time of the match, matches last ~2 hours
                match_time = datetime.fromisoformat(utc_date_str.replace("Z", "+00:00"))
                end_time = match_time + timedelta(hours=2) # Estimate end time
                diff_hours = (now - end_time).total_seconds() / 3600.0
                
                # If the match finished within the last 2.5 hours
                if 0 <= diff_hours <= 2.5:
                    home_tla = m.get("homeTeam", {}).get("tla", m.get("homeTeam", {}).get("name", "")[:3].upper())
                    away_tla = m.get("awayTeam", {}).get("tla", m.get("awayTeam", {}).get("name", "")[:3].upper())
                    m_key = get_match_key(home_tla, away_tla, utc_date_str)
                    
                    # Deduplicate
                    if m_key in registry["matches"] and registry["matches"][m_key].get("post_match_done"):
                        logger.info(f"Match {m_key} already processed for post-match. Skipping.")
                        continue
                        
                    target_match = m
                    break
            except Exception as e:
                logger.error(f"Error parsing date for match: {e}")
                continue
                
    if not target_match or target_match.get("status") != "FINISHED":
        logger.info("No new completed matches found in the 2.5-hour window. Stopping pipeline cleanly.")
        return
        
    # Extract details
    match_id = target_match.get("id")
    home = target_match.get("homeTeam", {}).get("name", "Home")
    away = target_match.get("awayTeam", {}).get("name", "Away")
    home_tla = target_match.get("homeTeam", {}).get("tla", home[:3].upper())
    away_tla = target_match.get("awayTeam", {}).get("tla", away[:3].upper())
    kickoff_raw = target_match.get("utcDate", "")
    group = target_match.get("group", "GROUP STAGE").replace("_", " ")
    
    score_data = target_match.get("score", {})
    hs = score_data.get("fullTime", {}).get("home", 0)
    as_ = score_data.get("fullTime", {}).get("away", 0)
    
    venue = "World Cup Stadium"
    
    m_key = get_match_key(home_tla, away_tla, kickoff_raw)
    logger.info(f"Processing finished match: {home} {hs}-{as_} {away} (Key: {m_key})")
    
    # 2. Fetch match timeline & stats via Gemini Search Grounding
    details = get_gemini_post_match_details(home, away, kickoff_raw, venue, hs, as_)
    
    # 3. Draft commentary script
    script_gen = ScriptGenerator()
    script = script_gen.generate_script(
        topic=f"{home} vs {away} World Cup 2026 post-match review",
        category="wc_post_match",
        context=json.dumps(details)
    )
    
    if not script:
        logger.error("Failed to generate script.")
        return
        
    # 4. Draw broadcast card images
    temp_dir = "footybitez/media/downloads"
    os.makedirs(temp_dir, exist_ok=True)
    
    card1 = os.path.abspath(os.path.join(temp_dir, f"post_card1_{m_key}.jpg"))
    card2 = os.path.abspath(os.path.join(temp_dir, f"post_card2_{m_key}.jpg"))
    card3 = os.path.abspath(os.path.join(temp_dir, f"post_card3_{m_key}.jpg"))
    card4 = os.path.abspath(os.path.join(temp_dir, f"post_card4_{m_key}.jpg"))
    card5 = os.path.abspath(os.path.join(temp_dir, f"post_card5_{m_key}.jpg"))
    card6 = os.path.abspath(os.path.join(temp_dir, f"post_card6_{m_key}.jpg"))
    
    card_generator.draw_post_match_card_1_score(home, away, hs, as_, group, card1)
    card_generator.draw_post_match_card_2_timeline(home, away, details["scorers"], card2)
    card_generator.draw_post_match_card_3_stats(home, away, details["stats"], card3)
    card_generator.draw_post_match_card_4_motm(details["motm"]["player"], home if hs >= as_ else away, details["motm"]["rating"], details["motm"]["stat"], card4)
    card_generator.draw_post_match_card_5_standings(group, details["standings"], card5)
    card_generator.draw_post_match_card_6_next(home, away, f"{home}: {details['next_a']} | {away}: {details['next_b']}", card6)
    
    # Map visual assets
    visual_assets = {
        "title_card": card1,
        "profile_image": card4,
        "segment_media": [
            [card2], # Timeline
            [card3], # Stats
            [card4], # MOTM
            [card5], # Standings
        ],
        "outro_image": card6 # Next Match Teaser Outro
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
    logger.info(f"Post-match video generated successfully: {video_path}")
    
    # 6. Upload
    if not skip_upload:
        title = f"{home} {hs}-{as_} {away} FULL RECAP 🔥 #WorldCup2026 #Shorts"
        description = (
            f"FIFA World Cup 2026 | {home} vs {away} | {kickoff_raw} at {venue}\n\n"
            f"🔔 Subscribe for every World Cup match recap!\n\n"
            f"{script.get('full_text', '')}\n\n"
            f"#WorldCup2026 #{home} #{away} #FIFA #Football #Soccer #Shorts"
        )
        tags = ["world cup 2026", "fifa 2026", home, away, "shorts", "football", "soccer", "recap"]
        
        uploader = YouTubeUploader()
        uploader.upload_video(video_path, title, description, tags)
        
        # Social cross-posting
        should_publish_socials = os.getenv("ENABLE_SOCIAL_PUBLISHING", "false").lower() == "true"
        if should_publish_socials:
            logger.info("Publishing post-match short to Facebook, Instagram Reels...")
            socials = SocialOrchestrator()
            socials.publish_to_all(video_path, title, description)
            
    # 7. Update Registry
    if m_key not in registry["matches"]:
        registry["matches"][m_key] = {
            "id": match_id,
            "home": home,
            "away": away,
            "datetime_utc": kickoff_raw,
            "status": "FINISHED",
            "pre_match_done": False,
            "post_match_done": False
        }
    registry["matches"][m_key]["post_match_done"] = True
    save_registry(registry)
    logger.info(f"Registry updated: {m_key} post_match_done = True")
    
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
