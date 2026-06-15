"""
Breaking News Pipeline — monitors finished World Cup matches and auto-publishes Shorts.

Architecture:
- Polls football-data.org (competition ID 2000) for today's finished matches every 5 min
- When a new finished match is detected, calls API-Football /fixtures/events for goal/card details
- Generates a 30-45 second breaking news script via ScriptGenerator
- Renders and uploads via RemotionVideoCreator + YouTubeUploader
- Persists processed match IDs to footybitez/data/news_state.json via [skip ci] git commit
- Hard timeout: signal.SIGALRM 220s on Linux (CI); platform-checked so local Windows testing works

Called by .github/workflows/breaking_news.yml every 5 minutes during match hours.
"""

import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime, timezone, timedelta, date
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

STATE_FILE = "footybitez/data/news_state.json"
POST_MATCH_WINDOW_HOURS = 2


class BreakingNewsPipeline:

    def __init__(self):
        from footybitez.data.worldcup_data import WorldCupData
        from footybitez.content.script_generator import ScriptGenerator
        from footybitez.media.media_sourcer import MediaSourcer
        from footybitez.video.remotion_video_creator import RemotionVideoCreator
        from footybitez.youtube.uploader import YouTubeUploader
        from footybitez.socials.social_orchestrator import SocialOrchestrator

        fd_key = os.getenv("FOOTBALL_DATA_API_KEY", "")
        af_key = os.getenv("API_FOOTBALL_KEY", "")

        if not fd_key:
            logger.error("FOOTBALL_DATA_API_KEY not set — breaking news pipeline cannot run.")
            sys.exit(1)

        self.wc_data = WorldCupData(fd_key, af_key)
        self.script_gen = ScriptGenerator()
        self.media_sourcer = MediaSourcer()
        self.video_creator = RemotionVideoCreator()
        self.uploader = YouTubeUploader()
        self.socials = SocialOrchestrator()


    # ─────────────────────────────────────────────────────────
    # STATE FILE — persists processed match IDs across GHA runs
    # ─────────────────────────────────────────────────────────

    def _load_state(self) -> dict:
        if not os.path.exists(STATE_FILE):
            return {}
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load state file: {e}")
            return {}

    def _save_state(self, state: dict):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def _commit_state(self):
        """
        Commits news_state.json back to the repo with [skip ci] to prevent
        recursive workflow triggers. Only runs in CI (git available + repo present).
        """
        try:
            subprocess.run(
                ["git", "config", "--global", "user.email", "actions@github.com"],
                check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "--global", "user.name", "GitHub Actions"],
                check=True, capture_output=True
            )
            subprocess.run(["git", "add", STATE_FILE], check=True, capture_output=True)
            result = subprocess.run(
                ["git", "commit", "-m", "Update news state [skip ci]"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                subprocess.run(["git", "push"], check=True, capture_output=True)
                logger.info("State file committed and pushed.")
            else:
                # Nothing to commit — state unchanged
                logger.info("No state changes to commit.")
        except Exception as e:
            logger.warning(f"State commit failed (non-fatal): {e}")

    # ─────────────────────────────────────────────────────────
    # MAIN MONITOR LOOP
    # ─────────────────────────────────────────────────────────

    def monitor(self):
        """
        Main entry point. Called by GitHub Actions every 5 minutes.
        Fetches recently finished matches and processes unprocessed ones.
        """
        logger.info("Breaking news monitor starting...")

        matches = self.wc_data.get_finished_matches_last_2hrs()
        state = self._load_state()
        processed_count = 0

        for match in matches:
            match_id = str(match.get("id", ""))
            if not match_id:
                continue

            if match_id in state:
                logger.info(f"Match {match_id} already processed — skipping.")
                continue

            # Skip match if the final full-time scores are not yet populated by the API
            score_obj = match.get("score") or {}
            full_time_score = score_obj.get("fullTime") or {}
            home_score = full_time_score.get("home")
            away_score = full_time_score.get("away")
            if home_score is None or away_score is None:
                logger.info(f"Match {match_id} scores are not yet available (home/away is None) — skipping this run.")
                continue

            logger.info(f"New finished match detected: {match_id}")

            try:
                events = self.wc_data.get_match_events(int(match_id))
                newsworthy = self._extract_newsworthy_events(match, events)

                for event in newsworthy:
                    script = self._generate_news_script(event)
                    if not script:
                        continue
                    video_path = self._create_news_video(script, event)
                    if video_path:
                        self._upload_news_short(video_path, script, event)
                    # Space uploads 5 minutes apart to avoid YouTube spam detection
                    if processed_count > 0:
                        logger.info("Sleeping 300s between uploads...")
                        time.sleep(300)
                    processed_count += 1

                state[match_id] = {
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "events": len(newsworthy)
                }

            except Exception as e:
                logger.error(f"Error processing match {match_id}: {e}", exc_info=True)
                # Still mark as processed to avoid retrying broken matches indefinitely
                state[match_id] = {"error": str(e)}

        self._save_state(state)
        self._commit_state()
        logger.info(f"Monitor complete. Processed {processed_count} new match events.")

    # ─────────────────────────────────────────────────────────
    # EVENT EXTRACTION
    # ─────────────────────────────────────────────────────────

    def _extract_newsworthy_events(self, match: dict, api_football_events: list | dict) -> list:
        """
        Determines which events from a finished match are worth a Short.
        """
        # Normalize events
        if isinstance(api_football_events, list):
            api_football_events = {
                "timeline": api_football_events,
                "stats": {}
            }
        elif not isinstance(api_football_events, dict):
            api_football_events = {
                "timeline": [],
                "stats": {}
            }

        timeline = api_football_events.get("timeline", [])
        stats = api_football_events.get("stats", {})

        events = []
        home = match.get("homeTeam", {}).get("name", "Home")
        away = match.get("awayTeam", {}).get("name", "Away")
        home_score = match.get("score", {}).get("fullTime", {}).get("home", 0) or 0
        away_score = match.get("score", {}).get("fullTime", {}).get("away", 0) or 0

        # Always: full-time result
        events.append({
            "type": "full_time_result",
            "home": home,
            "away": away,
            "home_score": home_score,
            "away_score": away_score,
            "match": match,
            "api_events": timeline,
            "stats": stats,
            "priority": 1,
        })

        # Upset detection: large score difference or known underdog winning
        if abs(home_score - away_score) >= 3:
            events.append({
                "type": "big_win",
                "home": home,
                "away": away,
                "home_score": home_score,
                "away_score": away_score,
                "match": match,
                "api_events": timeline,
                "priority": 0,
            })

        # From events: hat tricks and red cards
        goal_counts = {}
        for ev in timeline:
            ev_type = ev.get("type", "")
            player_name = ev.get("player", {}).get("name", "")

            if ev_type == "Goal" and player_name:
                goal_counts[player_name] = goal_counts.get(player_name, 0) + 1

            if ev_type == "Card" and ev.get("detail") == "Red Card" and player_name:
                events.append({
                    "type": "red_card",
                    "player": player_name,
                    "team": ev.get("team", {}).get("name", ""),
                    "minute": ev.get("time", {}).get("elapsed", "?"),
                    "home": home,
                    "away": away,
                    "home_score": home_score,
                    "away_score": away_score,
                    "match": match,
                    "priority": 1,
                })

        for player, count in goal_counts.items():
            if count >= 3:
                events.append({
                    "type": "hat_trick",
                    "player": player,
                    "home": home,
                    "away": away,
                    "home_score": home_score,
                    "away_score": away_score,
                    "match": match,
                    "priority": 0,
                })

        return sorted(events, key=lambda e: e["priority"])

    # ─────────────────────────────────────────────────────────
    # SCRIPT GENERATION
    # ─────────────────────────────────────────────────────────

    def _generate_news_script(self, event: dict) -> dict | None:
        home = event.get("home", "")
        away = event.get("away", "")
        hs = event.get("home_score", 0)
        as_ = event.get("away_score", 0)
        event_type = event.get("type", "")

        if event_type == "hat_trick":
            topic = f"{event['player']} scores a hat trick in {home} vs {away} ({hs}-{as_}) World Cup 2026"
        elif event_type == "red_card":
            topic = f"{event['player']} sent off in {home} vs {away} ({hs}-{as_}) at the World Cup"
        elif event_type == "big_win":
            winner = home if hs > as_ else away
            loser = away if hs > as_ else home
            topic = f"{winner} thrash {loser} {hs}-{as_} at World Cup 2026"
        else:
            topic = f"Full time: {home} {hs}-{as_} {away} — World Cup 2026 result"

        return self.script_gen.generate_breaking_news_script(topic, event)

    # ─────────────────────────────────────────────────────────
    # VIDEO CREATION
    # ─────────────────────────────────────────────────────────

    def _create_news_video(self, script: dict, event: dict) -> str | None:
        try:
            home = event.get("home", "")
            away = event.get("away", "")
            topic = f"{home} vs {away} World Cup 2026"

            # Disable AI image generation fallback for breaking news, use real images or solid cards only
            title_card = self.media_sourcer.get_title_card_image(topic, allow_ai=False)
            
            # Sourcing profile image of the primary entity (player/club), not the match string
            entity_query = script.get("primary_entity")
            if not entity_query:
                entity_query = topic
            profile_image = self.media_sourcer.get_profile_image(entity_query)

            # Build match-specific enrichment for visual searches so real match
            # images are returned instead of generic player photos
            match_context = ""
            if " vs " in topic:
                try:
                    parts = topic.split(" vs ", 1)
                    team1_words = parts[0].strip().split()
                    team2_words = parts[1].strip().split()
                    team1 = team1_words[-1] if team1_words else ""
                    team2 = team2_words[0] if team2_words else ""
                    if team1 and team2:
                        match_context = f"{team1} {team2} World Cup 2026"
                except Exception:
                    pass

            segment_media = []
            for seg in script.get("segments", []):
                kw = seg.get("visual_keyword", topic) if isinstance(seg, dict) else topic
                if match_context:
                    if not any(word.lower() in kw.lower() for word in match_context.split()[:2]):
                        kw = f"{kw} {match_context}"
                segment_media.append(self.media_sourcer.get_media(kw, count=2, prefer_real_match=True))

            visual_assets = {
                "title_card": title_card,
                "profile_image": profile_image or title_card,
                "segment_media": segment_media,
            }

            import random
            music_dir = "footybitez/music"
            bg_music = None
            if os.path.exists(music_dir):
                files = [f for f in os.listdir(music_dir) if f.endswith(".mp3")]
                if files:
                    bg_music = os.path.join(music_dir, random.choice(files))

            video_path = self.video_creator.create_video(script, visual_assets, background_music_path=bg_music)
            self.media_sourcer.cleanup()
            return video_path

        except Exception as e:
            logger.error(f"Video creation failed for breaking news: {e}", exc_info=True)
            return None

    def _upload_news_short(self, video_path: str, script: dict, event: dict):
        home = event.get("home", "")
        away = event.get("away", "")
        hs = event.get("home_score", 0)
        as_ = event.get("away_score", 0)

        title = f"FULL TIME: {home} {hs}-{as_} {away} 🔴 #worldcup2026 #shorts"
        description = (
            f"{script.get('full_text', '')}\n\n"
            "Follow for full match analysis! #worldcup2026 #football #shorts #footybitez"
        )
        tags = ["worldcup2026", "football", "breakingnews", "shorts", "soccer",
                home.lower().replace(" ", ""), away.lower().replace(" ", "")]

        try:
            self.uploader.upload_video(video_path, title, description, tags)
            logger.info(f"Uploaded breaking news Short for {home} vs {away} to YouTube.")
            
            # Cross-platform publishing to Facebook, Instagram Reels, and TikTok
            should_publish_socials = os.getenv("ENABLE_SOCIAL_PUBLISHING", "false").lower() == "true"
            if should_publish_socials:
                logger.info("Attempting cross-platform upload to Facebook, Instagram, and TikTok...")
                self.socials.publish_to_all(video_path, title, description)
            else:
                logger.info("Social publishing skipped (ENABLE_SOCIAL_PUBLISHING not true).")
                
        except Exception as e:
            logger.error(f"Upload failed: {e}")



# ─────────────────────────────────────────────────────────
# CLI ENTRY POINT WITH SIGALRM TIMEOUT
# ─────────────────────────────────────────────────────────

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )

    # 220-second hard timeout — prevents overlapping with next 5-min cron trigger
    # signal.SIGALRM is Linux-only; skip on Windows for local testing
    if sys.platform != "win32":
        import signal

        def _timeout_handler(signum, frame):
            logger.warning("Breaking news monitor exceeded 220s time limit — exiting cleanly.")
            sys.exit(0)

        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(220)  # 3 min 40 sec — leaves 20s buffer before next cron

    pipeline = BreakingNewsPipeline()
    pipeline.monitor()


if __name__ == "__main__":
    main()
