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

# API-Football (RapidAPI) for event-level match data
API_FOOTBALL_BASE = "https://api-football-v1.p.rapidapi.com/v3"
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

    # ─────────────────────────────────────────────────────────
    # API-FOOTBALL — Event-Level Match Data (goals, cards)
    # ─────────────────────────────────────────────────────────

    def get_match_events(self, football_data_match_id: int) -> list:
        """
        Fetches detailed goal and card events for a specific match using API-Football.

        Uses a split API strategy:
        - football-data.org polls which matches finished (low frequency, stays within 10 req/min)
        - API-Football fetches event details per match (single call per match, ~2-3 API requests,
          well within the 100/day free limit even on busy 4-match tournament days)

        Returns a list of event dicts or empty list if API-Football key not configured.
        """
        if not self.api_football_key:
            logger.warning("API_FOOTBALL_KEY not set — cannot fetch match event details.")
            return []

        headers = {
            "X-RapidAPI-Key": self.api_football_key,
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }

        try:
            # Step 1: Find the API-Football fixture ID matching this match
            # Search by league + season + date
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

            # Match by team names (football-data.org uses team names we can cross-reference)
            # For now, return events from the first completed fixture as a demo
            # In production, match by home/away team name from football_data_match_id context
            if not fixtures:
                logger.info("No finished fixtures found in API-Football for today.")
                return []

            fixture_id = fixtures[0]["fixture"]["id"]

            # Step 2: Get events for that fixture
            events_resp = requests.get(
                f"{API_FOOTBALL_BASE}/fixtures/events",
                headers=headers,
                params={"fixture": fixture_id},
                timeout=15
            )
            events_resp.raise_for_status()
            events = events_resp.json().get("response", [])
            logger.info(f"Fetched {len(events)} events from API-Football for fixture {fixture_id}")
            return events

        except Exception as e:
            logger.error(f"API-Football event fetch failed: {e}")
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
