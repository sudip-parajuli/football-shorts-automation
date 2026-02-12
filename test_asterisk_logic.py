import json
import os
from footybitez.media.voice_generator import VoiceGenerator

def test_asterisk_reinjection():
    print("Testing Asterisk Reinjection...")
    
    # Setup dummy data
    json_path = "test_timing.json"
    dummy_map = [
        {"word": "Lionel", "start": 0.0, "duration": 0.5},
        {"word": "Messi", "start": 0.5, "duration": 0.5},
        {"word": "scored", "start": 1.0, "duration": 0.5},
        {"word": "91", "start": 1.5, "duration": 0.5},
        {"word": "goals", "start": 2.0, "duration": 0.5}
    ]
    
    with open(json_path, 'w') as f:
        json.dump(dummy_map, f)
        
    original_text = "Lionel *Messi* scored *91* goals"
    
    vg = VoiceGenerator(output_dir=".")
    vg._reinject_asterisks(original_text, json_path)
    
    with open(json_path, 'r') as f:
        updated_map = json.load(f)
    
    # Verify
    failures = []
    if updated_map[1]['word'] != "*Messi*":
        failures.append(f"Expected *Messi*, got {updated_map[1]['word']}")
        
    if updated_map[3]['word'] != "*91*":
        failures.append(f"Expected *91*, got {updated_map[3]['word']}")
        
    if failures:
        print("FAILED:")
        for fail in failures: print(f"- {fail}")
    else:
        print("SUCCESS: Asterisks correctly reinjected.")
        print(f"Sample: {updated_map[1]['word']}, {updated_map[3]['word']}")
        
    # Cleanup
    if os.path.exists(json_path): os.remove(json_path)

if __name__ == "__main__":
    test_asterisk_reinjection()
