import os
import sys
import logging
from dotenv import load_dotenv

# Ensure root path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

from footybitez.pipelines.post_match_pipeline import get_gemini_post_match_details

def main():
    home = "Switzerland"
    away = "Bosnia and Herzegovina"
    date_str = "2026-06-18T19:00:00Z"
    venue = "Stade de Genève"
    hs = 4
    as_ = 1
    
    print("Testing updated get_gemini_post_match_details...")
    details = get_gemini_post_match_details(home, away, date_str, venue, hs, as_)
    
    print("\n--- MATCH DETAILS RESULT ---")
    import pprint
    pprint.pprint(details)
    
    # Assertions to verify correctness
    print("\nValidating fetched match statistics...")
    
    stats = details.get("stats", {})
    possession = stats.get("possession", {})
    shots = stats.get("shots", {})
    shots_on_target = stats.get("shots_on_target", {})
    corners = stats.get("corners", {})
    
    assert possession.get("home") == "62%", f"Expected 62% home possession, got {possession.get('home')}"
    assert possession.get("away") == "38%", f"Expected 38% away possession, got {possession.get('away')}"
    assert int(shots.get("home")) == 13, f"Expected 13 home shots, got {shots.get('home')}"
    assert int(shots.get("away")) == 5, f"Expected 5 away shots, got {shots.get('away')}"
    assert int(shots_on_target.get("home")) == 7, f"Expected 7 home shots on target, got {shots_on_target.get('home')}"
    assert int(shots_on_target.get("away")) == 3, f"Expected 3 away shots on target, got {shots_on_target.get('away')}"
    assert int(corners.get("home")) == 7, f"Expected 7 home corners, got {corners.get('home')}"
    assert int(corners.get("away")) == 3, f"Expected 3 away corners, got {corners.get('away')}"
    
    print("ALL TESTS PASSED! Match stats are 100% accurate!")

if __name__ == "__main__":
    main()
