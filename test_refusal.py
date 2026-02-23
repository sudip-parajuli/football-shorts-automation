import logging
import json
from footybitez.content.script_generator import ScriptGenerator

logging.basicConfig(level=logging.INFO)

def test_script_refusal():
    generator = ScriptGenerator()
    
    # 1. Topic guaranteed to fail context/generate a refusal
    topic = "Chelsea's billion pound squad"
    category = "Money & Transfers"
    
    print(f"\n--- Testing Topic: {topic} ---")
    script = generator.generate_script(topic, category)
    
    if script:
        with open("refusal_output.json", "w", encoding="utf-8") as f:
            json.dump(script, f, indent=2)
        print("[FAIL] The script generator returned a script instead of False. Output saved to refusal_output.json")
    else:
        print("[SUCCESS] The script generator correctly rejected the refusal response and returned False.")

if __name__ == "__main__":
    test_script_refusal()
