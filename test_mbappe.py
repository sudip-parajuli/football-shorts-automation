
import os
import json
from footybitez.content.script_generator import ScriptGenerator
import logging

logging.basicConfig(level=logging.INFO)

def test_grounded_generation():
    generator = ScriptGenerator()
    
    test_cases = [
        {"topic": "Erling Haaland vs Kylian Mbappe", "category": "Comparisons & Debates"}
    ]
    
    for case in test_cases:
        print(f"\n--- Testing Topic: {case['topic']} ---")
        script = generator.generate_script(case['topic'], case['category'])
        
        if script:
            with open("test_mbappe_output.json", "w", encoding="utf-8") as f:
                json.dump(script, f, indent=2)
            print("Output written to test_mbappe_output.json")
        else:
            print("Failed to generate script.")

if __name__ == "__main__":
    test_grounded_generation()
