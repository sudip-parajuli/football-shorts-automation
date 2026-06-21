import os
import sys
import json
import logging
from dotenv import load_dotenv

# Ensure root path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

from footybitez.content.script_generator import ScriptGenerator

def test_local_fallback():
    print("==================================================")
    print("TEST 1: Local Rule-Based Pre-Match Fallback")
    print("==================================================")
    
    # Pre-Match dummy details
    pre_match_details = {
        "h2h": "2 Wins, 1 Draw, 0 Losses for Tunisia",
        "form_a": "W D W L W",
        "form_b": "L D W W L",
        "prob_a": 45.0,
        "prob_draw": 25.0,
        "prob_b": 30.0,
        "player_a": "Wahbi Khazri",
        "player_a_stats": "3 goals in qualifying",
        "player_b": "Takumi Minamino",
        "player_b_stats": "4 assists in last 5 games",
        "storyline": "Tunisia looks to break their underdog status against a high-flying Japanese squad."
    }
    
    # Disable all keys to force local fallback
    env_backup = {}
    keys_to_clear = ["GROQ_API_KEY", "ANTHROPIC_API_KEY"]
    for suffix in ["", "2", "3"]:
        keys_to_clear.append(f"GEMINI_API_KEY{suffix}")
        
    for k in keys_to_clear:
        if k in os.environ:
            env_backup[k] = os.environ[k]
            del os.environ[k]
            
    try:
        generator = ScriptGenerator()
        topic = "Tunisia vs Japan World Cup 2026 prediction"
        script = generator.generate_script(
            topic=topic,
            category="wc_pre_match",
            context=json.dumps(pre_match_details)
        )
        
        print("Generated Pre-Match Fallback Script:")
        print(json.dumps(script, indent=2))
        
        assert script is not None, "Script is None!"
        assert "Tunisia" in script["hook"], "Hook should contain Tunisia"
        assert "Japan" in script["hook"], "Hook should contain Japan"
        assert "Khazri" in script["full_text"], "Script should mention Wahbi Khazri"
        assert "Minamino" in script["full_text"], "Script should mention Takumi Minamino"
        assert "45.0%" in script["full_text"], "Script should mention 45.0% probability"
        
        # Verify visual keywords
        for seg in script["segments"]:
            assert "visual_keyword" in seg and seg["visual_keyword"], "Each segment must have a visual_keyword"
            assert "soccer" in seg["visual_keyword"] or "football" in seg["visual_keyword"], "Keywords must specify soccer/football context"
            
        print("--> Pre-match local fallback check PASSED!")
        
    finally:
        # Restore keys
        for k, v in env_backup.items():
            os.environ[k] = v

    print("\n==================================================")
    print("TEST 2: Local Rule-Based Post-Match Fallback")
    print("==================================================")
    
    post_match_details = {
        "scorers": [
            {"player": "Matías Galarza", "minute": 1, "team": "Away", "type": "Goal", "detail": None}
        ],
        "stats": {
            "possession": {"home": "77%", "away": "23%"},
            "shots": {"home": 20, "away": 5},
            "shots_on_target": {"home": 2, "away": 3},
            "corners": {"home": 5, "away": 0},
            "xg": {"home": "1.9", "away": "0.8"}
        },
        "motm": {
            "player": "Matías Galarza",
            "rating": 8.7,
            "stat": "scored the fastest goal of the tournament"
        },
        "standout_moment": "Miguel Almirón was sent off in the 45th minute, leaving Paraguay to defend their lead with 10 men."
    }
    
    # Disable all keys again
    for k in keys_to_clear:
        if k in os.environ:
            del os.environ[k]
            
    try:
        generator = ScriptGenerator()
        topic = "Turkey vs Paraguay World Cup 2026 post-match review"
        script = generator.generate_script(
            topic=topic,
            category="wc_post_match",
            context=json.dumps(post_match_details)
        )
        
        print("Generated Post-Match Fallback Script:")
        print(json.dumps(script, indent=2))
        
        assert script is not None, "Script is None!"
        assert "Turkey" in script["hook"], "Hook should contain Turkey"
        assert "Paraguay" in script["hook"], "Hook should contain Paraguay"
        assert "Galarza" in script["full_text"], "Script should mention Galarza"
        assert "77%" in script["full_text"], "Script should mention 77%"
        assert "23%" in script["full_text"], "Script should mention 23%"
        assert "Almirón" in script["full_text"], "Script should mention Almirón"
        
        # Verify visual keywords
        for seg in script["segments"]:
            assert "visual_keyword" in seg and seg["visual_keyword"], "Each segment must have a visual_keyword"
            assert "soccer" in seg["visual_keyword"] or "football" in seg["visual_keyword"], "Keywords must specify soccer/football context"
            
        print("--> Post-match local fallback check PASSED!")
        
    finally:
        # Restore keys
        for k, v in env_backup.items():
            os.environ[k] = v

def test_groq_script_generation():
    print("\n==================================================")
    print("TEST 3: Script Generation with Groq (Gemini disabled)")
    print("==================================================")
    
    if not os.getenv("GROQ_API_KEY"):
        print("Skipping Groq test - GROQ_API_KEY not found in environment.")
        return
        
    # Disable Gemini keys
    gemini_keys_backup = {}
    for suffix in ["", "2", "3"]:
        key_name = f"GEMINI_API_KEY{suffix}"
        if key_name in os.environ:
            gemini_keys_backup[key_name] = os.environ[key_name]
            del os.environ[key_name]
            
    try:
        generator = ScriptGenerator()
        topic = "Tunisia vs Japan World Cup 2026 prediction"
        script = generator.generate_script(
            topic=topic,
            category="wc_pre_match",
            context=json.dumps({
                "h2h": "2 Wins, 1 Draw, 0 Losses for Tunisia",
                "form_a": "W D W L W",
                "form_b": "L D W W L",
                "prob_a": 45.0,
                "prob_draw": 25.0,
                "prob_b": 30.0,
                "player_a": "Wahbi Khazri",
                "player_a_stats": "3 goals in qualifying",
                "player_b": "Takumi Minamino",
                "player_b_stats": "4 assists in last 5 games",
                "storyline": "Tunisia looks to break their underdog status against a high-flying Japanese squad."
            })
        )
        
        print("Generated Script using Groq:")
        print(json.dumps(script, indent=2))
        assert script is not None, "Script from Groq is None!"
        assert "hook" in script and "segments" in script, "Invalid script format from Groq!"
        print("--> Groq script generation check PASSED!")
        
    finally:
        # Restore Gemini keys
        for k, v in gemini_keys_backup.items():
            os.environ[k] = v

if __name__ == "__main__":
    test_local_fallback()
    test_groq_script_generation()
