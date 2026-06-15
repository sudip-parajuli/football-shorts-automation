"""
Football-data.org v4 API wrapper for World Cup 2026 data.

Competition ID 2000 = FIFA World Cup (numeric ID required for tournaments).
String codes (PL, BL1, etc.) only work for domestic leagues.

Free tier: 10 requests/minute. Rate limiter enforces 6-second gaps.
"""

import requests
import time
import logging
from datetime import date, datetime, timezone, timedelta

logger = logging.getLogger(__name__)

FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
WC_2026_ID = 2000  # FIFA World Cup numeric competition ID (NOT "WC")

# API-Football (Direct API-Sports) for event-level match data
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
API_FOOTBALL_WC_LEAGUE = 1   # FIFA World Cup league ID in API-Football
API_FOOTBALL_WC_SEASON = 2026


class WorldCupData:
    """
    Wraps football-data.org v4 API for World Cup fixture, standings, and scorer data.
    Uses API-Football as a secondary source for detailed match events (goals, cards).
    """

    def __init__(self, football_data_key: str, api_football_key: str = None):
        self.headers = {"X-Auth-Token": football_data_key}
        self.api_football_key = api_football_key
        self._last_request_time = 0.0  # Unix timestamp of last football-data.org request

    # ─────────────────────────────────────────────────────────
    # RATE LIMITER — 10 req/min free tier → 6s minimum gap
    # ─────────────────────────────────────────────────────────

    def _rate_limited_get(self, url: str, params: dict = None, retries: int = 3) -> dict:
        """Makes a GET request to football-data.org, examining response headers for rate limits."""
        for attempt in range(retries):
            try:
                r = requests.get(url, headers=self.headers, params=params, timeout=15)
                
                # Check rate limiting headers
                requests_available = r.headers.get("X-Requests-Available-Minute")
                reset_in_seconds = r.headers.get("X-RequestCounter-Reset")
                
                if requests_available is not None and reset_in_seconds is not None:
                    avail = int(requests_available)
                    reset = int(reset_in_seconds)
                    logger.debug(f"Rate limiter: {avail} requests left this minute, resets in {reset}s")
                    if avail == 0:
                        logger.warning(f"Rate limit approaching. Sleeping for {reset + 1} seconds.")
                        time.sleep(reset + 1)
                else:
                    # Fallback to basic 6-second delay if headers are missing
                    elapsed = time.time() - self._last_request_time
                    if elapsed < 6.0:
                        time.sleep(6.0 - elapsed)
                    self._last_request_time = time.time()

                if r.status_code == 429:
                    reset = int(r.headers.get("X-RequestCounter-Reset", 60))
                    logger.warning(f"HTTP 429 Too Many Requests. Retrying in {reset + 1} seconds.")
                    time.sleep(reset + 1)
                    continue

                r.raise_for_status()
                return r.json()
            except requests.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else 'Unknown'
                logger.error(f"football-data.org HTTP error {status_code}: {e}")
                if attempt == retries - 1:
                    return {}
            except Exception as e:
                logger.error(f"football-data.org request failed: {e}")
                if attempt == retries - 1:
                    return {}
        return {}

    # ─────────────────────────────────────────────────────────
    # FOOTBALL-DATA.ORG — Fixture & Competition Data
    # ─────────────────────────────────────────────────────────

    def check_coverage(self) -> dict:
        """
        Prints the competition's coverage object to verify which data types
        are available on the free tier (goals, bookings, etc.).
        Call this once before building event extraction logic.
        """
        data = self._rate_limited_get(f"{FOOTBALL_DATA_BASE}/competitions/{WC_2026_ID}")
        coverage = data.get("currentSeason", {})
        logger.info(f"WC 2026 Coverage: {coverage}")
        return coverage

    def get_today_matches(self) -> list:
        """Returns all World Cup matches scheduled, live, or finished today."""
        today = str(date.today())
        data = self._rate_limited_get(
            f"{FOOTBALL_DATA_BASE}/competitions/{WC_2026_ID}/matches",
            params={"dateFrom": today, "dateTo": today}
        )
        return data.get("matches", [])

    def get_standings(self) -> dict:
        """Returns the current World Cup group standings."""
        data = self._rate_limited_get(
            f"{FOOTBALL_DATA_BASE}/competitions/{WC_2026_ID}/standings"
        )
        return data

    def get_scorers(self) -> list:
        """Returns the World Cup top scorers list."""
        data = self._rate_limited_get(
            f"{FOOTBALL_DATA_BASE}/competitions/{WC_2026_ID}/scorers"
        )
        return data.get("scorers", [])

    def get_finished_matches_last_2hrs(self) -> list:
        """
        Returns World Cup matches that finished in the last 2 hours.

        Strategy:
        1. Fetch only TODAY's matches (dateFrom/dateTo = today) to avoid loading
           the entire competition history (which would be hundreds of matches).
        2. Client-side filter: status == FINISHED AND lastUpdated within 2 hours.

        The state file deduplication in BreakingNewsPipeline handles the rest.
        """
        today = str(date.today())
        data = self._rate_limited_get(
            f"{FOOTBALL_DATA_BASE}/competitions/{WC_2026_ID}/matches",
            params={
                "dateFrom": today,
                "dateTo": today,
                "status": "FINISHED"
            }
        )
        all_matches = data.get("matches", [])

        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        recent = []

        for match in all_matches:
            if match.get("status") != "FINISHED":
                continue
            last_updated_str = match.get("lastUpdated", "")
            try:
                # football-data.org uses ISO 8601 with Z suffix
                last_updated = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00"))
                if last_updated >= cutoff:
                    recent.append(match)
            except Exception:
                # If we can't parse the timestamp, include it to be safe
                recent.append(match)

        logger.info(f"Found {len(recent)} recently finished matches (within last 2hrs) out of {len(all_matches)} today")
        return recent

    def get_upcoming_matches(self) -> list:
        """Returns World Cup matches scheduled in the next 3 days."""
        today = str(date.today())
        future = str(date.today() + timedelta(days=3))
        data = self._rate_limited_get(
            f"{FOOTBALL_DATA_BASE}/competitions/{WC_2026_ID}/matches",
            params={
                "dateFrom": today,
                "dateTo": future,
                "status": "SCHEDULED"
            }
        )
        return data.get("matches", [])

    # ─────────────────────────────────────────────────────────
    # API-FOOTBALL — Event-Level Match Data (goals, cards)
    # ─────────────────────────────────────────────────────────

    def get_match_events(self, football_data_match_id: int) -> list:
        """
        Fetches detailed goal and card events for a specific match using API-Football.
        Falls back to Gemini Google Search Grounding if API-Football returns no data.
        """
        # Fetch match details from football-data.org first to get team names and date
        match_detail = self._rate_limited_get(f"{FOOTBALL_DATA_BASE}/matches/{football_data_match_id}")
        if not match_detail:
            logger.warning(f"Could not retrieve match details for {football_data_match_id} from football-data.org")
            return []

        home_team = match_detail.get("homeTeam", {}).get("name", "")
        away_team = match_detail.get("awayTeam", {}).get("name", "")
        utc_date_str = match_detail.get("utcDate", "")
        
        # Parse date to a friendly format for search, e.g. "June 11, 2026"
        date_str = ""
        if utc_date_str:
            try:
                dt = datetime.fromisoformat(utc_date_str.replace("Z", "+00:00"))
                date_str = dt.strftime("%B %d, %Y")
            except Exception:
                date_str = utc_date_str.split("T")[0]

        logger.info(f"Fetching events for match: {home_team} vs {away_team} on {date_str} (ID: {football_data_match_id})")

        events = []
        if self.api_football_key:
            headers = {
                "x-apisports-key": self.api_football_key
            }
            try:
                # Find the API-Football fixture ID matching this match
                today = str(date.today())
                fixtures_resp = requests.get(
                    f"{API_FOOTBALL_BASE}/fixtures",
                    headers=headers,
                    params={
                        "league": API_FOOTBALL_WC_LEAGUE,
                        "season": API_FOOTBALL_WC_SEASON,
                        "date": today,
                        "status": "FT"  # Full Time
                    },
                    timeout=15
                )
                fixtures_resp.raise_for_status()
                fixtures = fixtures_resp.json().get("response", [])

                # Match by team names
                fixture_id = None
                for f in fixtures:
                    f_home = f.get("teams", {}).get("home", {}).get("name", "").lower()
                    f_away = f.get("teams", {}).get("away", {}).get("name", "").lower()
                    if (home_team.lower() in f_home or f_home in home_team.lower()) and \
                       (away_team.lower() in f_away or f_away in away_team.lower()):
                        fixture_id = f["fixture"]["id"]
                        break

                if fixture_id:
                    # Get events for that fixture
                    events_resp = requests.get(
                        f"{API_FOOTBALL_BASE}/fixtures/events",
                        headers=headers,
                        params={"fixture": fixture_id},
                        timeout=15
                    )
                    events_resp.raise_for_status()
                    events = events_resp.json().get("response", [])
                    logger.info(f"Fetched {len(events)} events from API-Football for fixture {fixture_id}")
            except Exception as e:
                logger.error(f"API-Football event fetch failed: {e}")

        # Fallback to Wikipedia API for 2026 World Cup match data (free, no key needed)
        if not events:
            logger.info("Falling back to Wikipedia for match events...")
            wiki_events = self._fetch_wikipedia_match_events(home_team, away_team, date_str)
            if wiki_events:
                logger.info(f"Retrieved {len(wiki_events)} events from Wikipedia.")
                return wiki_events

        # Fallback to Gemini Google Search Grounding if API-Football did not return events
        if not events:
            logger.info("Falling back to Gemini Google Search Grounding for match events...")
            import os
            import json
            gemini_keys = []
            for suffix in ["", "2", "3"]:
                val = os.getenv(f"GEMINI_API_KEY{suffix}")
                if val:
                    gemini_keys.append(val)
            
            if not gemini_keys:
                logger.warning("No GEMINI_API_KEY available for match events search fallback.")
                return []

            for key in gemini_keys:
                for model_name in ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]:
                    for attempt in range(3):
                        try:
                            from google import genai
                            from google.genai import types
                            
                            client = genai.Client(api_key=key)
                            
                            # Step 1: Search match details
                            search_prompt = (
                                f"Find the goals (scorers and minute), red cards (player, team, minute), and full match statistics "
                                f"(possession %, shots, shots on target, corner kicks, offsides, fouls, yellow cards) "
                                f"for the World Cup match {home_team} vs {away_team} on {date_str}."
                            )
                            r1 = client.models.generate_content(
                                model=model_name,
                                contents=search_prompt,
                                config=types.GenerateContentConfig(
                                    tools=[types.Tool(google_search=types.GoogleSearch())]
                                )
                            )
                            
                            # Space out calls to avoid hitting free-tier 15 RPM limits
                            time.sleep(4)
                            
                            # Step 2: Parse to JSON list of events and match statistics
                            parse_prompt = (
                                "Parse the following match information into a JSON object with two keys:\n"
                                "1. 'timeline': a list of events, where each event has keys: 'type' ('Goal' or 'Card'), "
                                "'detail' ('Red Card', 'Yellow Card', or null), 'player' (dict with 'name'), "
                                "'team' (dict with 'name'), 'time' (dict with 'elapsed' integer).\n"
                                "2. 'stats': a dict with keys: 'possession' (dict with 'home' and 'away' strings/percentages), "
                                "'shots' (dict with 'home' and 'away' integers or 'N/A'), 'shots_on_target' (dict with 'home' and 'away' integers or 'N/A'), "
                                "'fouls' (dict with 'home' and 'away' integers or 'N/A'), 'corners' (dict with 'home' and 'away' integers or 'N/A'), "
                                "'offsides' (dict with 'home' and 'away' integers or 'N/A'), 'yellow_cards' (dict with 'home' and 'away' integers or 'N/A').\n\n"
                                f"Match info:\n{r1.text}"
                            )
                            r2 = client.models.generate_content(
                                model=model_name,
                                contents=parse_prompt,
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json"
                                )
                            )
                            parsed_data = json.loads(r2.text)
                            if isinstance(parsed_data, dict) and "timeline" in parsed_data:
                                logger.info(f"Successfully retrieved match data via Gemini Search ({model_name}).")
                                return parsed_data
                        except Exception as e:
                            logger.warning(f"Gemini events search failed (model={model_name}, attempt={attempt+1}): {e}")
                            time.sleep(5)
                            continue
        return events

    def _fetch_wikipedia_match_events(self, home_team: str, away_team: str, date_str: str) -> list:
        """
        Fetches match events (goals, cards) from Wikipedia for a 2026 World Cup match.
        Free API, no key needed. Searches the match page and parses goal/card info.
        """
        import re
        try:
            # Search Wikipedia for the match page
            search_terms = f"{home_team} vs {away_team} 2026 FIFA World Cup"
            search_url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": search_terms,
                "format": "json",
                "srlimit": 3,
            }
            r = requests.get(search_url, params=params,
                             headers={"User-Agent": "FootyBitezBot/1.0"}, timeout=10)
            if r.status_code != 200:
                return []
            data = r.json()
            search_results = data.get("query", {}).get("search", [])
            if not search_results:
                return []
            page_title = search_results[0].get("title", "")
            if not page_title:
                return []

            # Get the page content
            params = {
                "action": "query",
                "titles": page_title,
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "format": "json",
            }
            r = requests.get(search_url, params=params,
                             headers={"User-Agent": "FootyBitezBot/1.0"}, timeout=10)
            if r.status_code != 200:
                return []
            data = r.json()
            pages = data.get("query", {}).get("pages", {})
            if not pages:
                return []
            page_id = next(iter(pages))
            extract = pages[page_id].get("extract", "")
            if not extract:
                return []

            # Parse goals (e.g. "Quiñones 9'" or "Raúl Jiménez 67' pen.")
            events = []
            goal_pattern = re.compile(r'([A-Za-zÀ-ÿ\s\.\-]+?)\s+(\d+)(?:\+(\d+))?\s*\'')
            for match in goal_pattern.finditer(extract):
                player_name = match.group(1).strip()
                minute = int(match.group(2))
                events.append({
                    "type": "Goal",
                    "detail": None,
                    "player": {"name": player_name},
                    "team": {"name": ""},
                    "time": {"elapsed": minute},
                })

            # Parse red cards (e.g. "Sithole 49'" in context of red card)
            red_card_pattern = re.compile(r'(red card|sent off|dismissed).*?([A-Za-zÀ-ÿ\s\.\-]+?)\s+(\d+)\s*\'', re.IGNORECASE)
            for match in red_card_pattern.finditer(extract):
                player_name = match.group(2).strip()
                minute = int(match.group(3))
                events.append({
                    "type": "Card",
                    "detail": "Red Card",
                    "player": {"name": player_name},
                    "team": {"name": ""},
                    "time": {"elapsed": minute},
                })

            # Alternative red card pattern (player name followed by minute in red card context)
            if not any(e["type"] == "Card" for e in events):
                alt_rc = re.compile(r'([A-Za-zÀ-ÿ\s\.\-]+?)\s+(\d+)\s*\'[^.]*?(?:red card|sent off|dismissed)', re.IGNORECASE)
                for match in alt_rc.finditer(extract):
                    player_name = match.group(1).strip()
                    minute = int(match.group(2))
                    # Avoid duplicates
                    if not any(e["type"] == "Card" and e["player"]["name"] == player_name for e in events):
                        events.append({
                            "type": "Card",
                            "detail": "Red Card",
                            "player": {"name": player_name},
                            "team": {"name": ""},
                            "time": {"elapsed": minute},
                        })

            logger.info(f"Wikipedia extracted {len(events)} events for {home_team} vs {away_team}")
            return events

        except Exception as e:
            logger.warning(f"Wikipedia match events fetch failed: {e}")
            return []


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not key:
        print("Set FOOTBALL_DATA_API_KEY in .env first")
    else:
        wc = WorldCupData(key)
        print("=== Coverage ===")
        print(wc.check_coverage())
        print("\n=== Today's Matches ===")
        matches = wc.get_today_matches()
        print(f"Found {len(matches)} matches today")
        for m in matches:
            print(f"  {m.get('homeTeam',{}).get('name')} vs {m.get('awayTeam',{}).get('name')} [{m.get('status')}]")
