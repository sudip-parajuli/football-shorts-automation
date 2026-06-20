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

from footybitez.media.media_sourcer import MediaSourcer

def main():
    print("Initializing MediaSourcer...")
    sourcer = MediaSourcer()

    # We will test two things:
    # 1. Download a football image and ensure it passes visual check
    # 2. Download a non-football image and ensure it fails visual check (relevance filter)
    
    temp_dir = "footybitez/media/downloads"
    os.makedirs(temp_dir, exist_ok=True)
    
    football_img_path = os.path.join(temp_dir, "ddg_football_test.jpg")
    non_football_img_path = os.path.join(temp_dir, "ddg_coffee_test.jpg")
    
    # Clean old test files
    for path in [football_img_path, non_football_img_path]:
        if os.path.exists(path):
            os.remove(path)
            
    # URLs for testing
    football_url = "https://upload.wikimedia.org/wikipedia/commons/c/c1/Lionel_Messi_20180626.jpg"
    non_football_url = "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"

    try:
        # Test 1: Download football image
        print(f"\n--- Test 1: Downloading normal football image from {football_url} ---")
        sourcer._download_file(football_url, football_img_path)
        
        # Verify that it exists (means it passed safety and relevance check!)
        assert os.path.exists(football_img_path), "Football image should have passed safety check and remained on disk!"
        print("Success: Football image passed visual safety check!")

        # Test 2: Download non-football image
        print(f"\n--- Test 2: Downloading non-football coffee image from {non_football_url} ---")
        sourcer._download_file(non_football_url, non_football_img_path)
        
        # Verify that it does NOT exist (means it got deleted because of the relevance check!)
        assert not os.path.exists(non_football_img_path), "Non-football image should have been deleted by the relevance filter!"
        print("Success: Non-football image was correctly filtered and deleted!")

        print("\nALL VISUAL SAFETY AND RELEVANCE TESTS PASSED!")
        
    finally:
        # Cleanup
        for path in [football_img_path, non_football_img_path]:
            if os.path.exists(path):
                os.remove(path)

if __name__ == "__main__":
    main()
