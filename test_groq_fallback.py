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
    home = "Turkey"
    away = "Paraguay"
    date_str = "2026-06-20T19:00:00Z"
    venue = "World Cup Stadium"
    hs = 0
    as_ = 1

    # Temporarily hide Gemini keys to force Groq + DDG fallback
    gemini_keys_backup = {}
    for suffix in ["", "2", "3"]:
        key_name = f"GEMINI_API_KEY{suffix}"
        if key_name in os.environ:
            gemini_keys_backup[key_name] = os.environ[key_name]
            del os.environ[key_name]

    try:
        print("Testing get_gemini_post_match_details with GEMINI keys disabled (forcing Groq+DDG fallback)...")
        details = get_gemini_post_match_details(home, away, date_str, venue, hs, as_)
        
        print("\n--- FALLBACK MATCH DETAILS RESULT ---")
        import pprint
        pprint.pprint(details)
        
        # Validations
        print("\nValidating fetched match statistics...")
        stats = details.get("stats", {})
        possession = stats.get("possession", {})
        scorers = details.get("scorers", [])
        
        # Ensure we fetched real Paraguay vs Turkey stats rather than dummy 50-50%
        home_poss = possession.get("home", "")
        away_poss = possession.get("away", "")
        print(f"Parsed Possession: Turkey {home_poss} - {away_poss} Paraguay")
        
        # Check if the possession is in a realistic range (e.g. Turkey had >70% possession)
        try:
            home_poss_val = int(home_poss.replace("%", "").strip())
            assert home_poss_val > 65, f"Expected Turkey possession to be > 65% based on actual stats, got {home_poss}"
            print("Possession check passed!")
        except Exception as e:
            print(f"Possession check error: {e}")
            sys.exit(1)

        # Check scorers
        found_galarza = False
        for s in scorers:
            player_name = s.get("player", "").lower()
            if "galarza" in player_name:
                found_galarza = True
                print(f"Found scorer: {s.get('player')} ({s.get('minute')}')")
                break
        
        assert found_galarza, "Expected scorer Matías Galarza to be in the scorers list!"
        print("Scorer check passed!")

        print("\nALL FALLBACK TESTS PASSED SUCCESSFULLY!")
        
    finally:
        # Restore Gemini keys
        for key_name, val in gemini_keys_backup.items():
            os.environ[key_name] = val

if __name__ == "__main__":
    main()
