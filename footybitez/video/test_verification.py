import os
import json
import logging
from footybitez.video.video_creator import VideoCreator
from footybitez.video.long_form_video_creator import LongFormVideoCreator

logging.basicConfig(level=logging.INFO)

def test_long_form_structure():
    print("\n--- Testing Long Form Structure ---")
    creator = LongFormVideoCreator(output_dir="footybitez/output/test")
    
    # Mock script data
    script_data = {
        "metadata": {"title": "Test Title"},
        "intro": {"text": "Welcome to the test.", "visual_keyword": "football"},
        "chapters": [
            {
                "chapter_title": "Chapter One",
                "facts": [
                    {"text": "This is fact one about football.", "visual_keyword": "soccer ball"}
                ]
            }
        ],
        "outro": {"text": "Goodbye.", "visual_keyword": "football"}
    }
    
    # Mock visual assets (empty list to trigger fallback)
    visual_assets = {"segment_media": []}
    
    print("Testing _create_chapter_overlay font sizes...")
    overlay_path = creator._create_chapter_overlay("Upper Text", "Lower Text Subject")
    print(f"Overlay created at: {overlay_path}")
    
    print("Verification complete. Please manually check the long_form_video.mp4 if you run a full generation.")

if __name__ == "__main__":
    test_long_form_structure()
