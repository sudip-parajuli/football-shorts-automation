import os
import sys
import time
import logging
import argparse
from datetime import datetime, timezone

# Ensure root path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from footybitez.data.worldcup_data import WorldCupData
from footybitez.pipelines import post_match_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("backfill_pipeline")

def run_backfill(skip_upload=False, limit=None):
    logger.info("Starting World Cup 2026 Match Recap Backfill Pipeline...")
    
    fd_key = os.getenv("FOOTBALL_DATA_API_KEY", "")
    if not fd_key:
        logger.error("FOOTBALL_DATA_API_KEY not set. Stopping.")
        sys.exit(1)
        
    wc_data = WorldCupData(fd_key)
    registry = post_match_pipeline.load_registry()
    
    # 1. Fetch all World Cup 2026 matches
    try:
        # football-data.org competition ID 2000 matches endpoint returns all matches
        resp = wc_data._rate_limited_get(f"https://api.football-data.org/v4/competitions/2000/matches")
        matches = resp.get("matches", [])
    except Exception as e:
        logger.error(f"Failed to fetch matches: {e}")
        return
        
    finished_matches = [m for m in matches if m.get("status") == "FINISHED"]
    logger.info(f"Found {len(finished_matches)} total completed matches since June 11, 2026.")
    
    # Sort chronologically
    finished_matches.sort(key=lambda m: m.get("utcDate", ""))
    
    backfilled_count = 0
    
    for m in finished_matches:
        if limit is not None and backfilled_count >= limit:
            logger.info(f"Reached backfill limit of {limit} matches. Stopping.")
            break
            
        home = m.get("homeTeam", {}).get("name", "")
        away = m.get("awayTeam", {}).get("name", "")
        home_tla = m.get("homeTeam", {}).get("tla", home[:3].upper())
        away_tla = m.get("awayTeam", {}).get("tla", away[:3].upper())
        utc_date_str = m.get("utcDate", "")
        
        m_key = post_match_pipeline.get_match_key(home_tla, away_tla, utc_date_str)
        
        # Check registry
        if m_key in registry["matches"] and registry["matches"][m_key].get("post_match_done"):
            logger.info(f"Match {m_key} ({home} vs {away}) already has post-match video. Skipping.")
            continue
            
        logger.info(f"Backfilling post-match recap for match: {home} vs {away} (ID: {m['id']}, Key: {m_key})...")
        
        try:
            post_match_pipeline.run_pipeline(force_match_id=m["id"], skip_upload=skip_upload)
            backfilled_count += 1
            
            # Reload registry to get updated state
            registry = post_match_pipeline.load_registry()
            
            # Add delay to respect YouTube and API rate limits
            if not skip_upload:
                logger.info("Sleeping for 30 seconds to respect rate limits...")
                time.sleep(30)
            else:
                logger.info("Test mode (skip_upload) — sleeping 5 seconds...")
                time.sleep(5)
                
        except Exception as e:
            logger.error(f"Error backfilling match {m_key}: {e}")
            continue
            
    logger.info(f"Backfill pipeline finished. Processed {backfilled_count} new match recaps.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-upload", action="store_true", help="Do not upload backfilled videos")
    parser.add_argument("--limit", type=int, help="Limit number of matches to backfill in this run")
    args = parser.parse_args()
    
    run_backfill(skip_upload=args.skip_upload, limit=args.limit)
