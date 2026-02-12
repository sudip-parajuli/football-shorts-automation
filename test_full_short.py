from footybitez.video.video_creator import VideoCreator
import os
import shutil

def test_full_short():
    vc = VideoCreator()
    
    # Mock Data
    script_data = {
        "hook": "This is a test *short* video",
        "segments": [{"text": "Testing *captions* logic", "visual_keyword": "football"}],
        "outro": "Like and *Subscribe*"
    }
    
    # Mock Assets (use placeholder if needed, or rely on VideoCreator fallback)
    visual_assets = {
        "title_card": None,
        "profile_image": None,
        "segment_media": [] 
    }
    
    # Ensure output dir exists
    if os.path.exists("footybitez/output/test_short.mp4"):
        os.remove("footybitez/output/test_short.mp4")
        
    print("Starting Video Creation...")
    try:
        path = vc.create_video(script_data, visual_assets)
        print(f"Video created at: {path}")
        
        # Verify JSON existence for the generated files
        # VideoCreator doesn't return the audio paths, but we know them: hook.mp3, segment_0.mp3, outro.mp3
        base = "footybitez/media/voice"
        for name in ["hook.json", "segment_0.json", "outro.json"]:
            p = os.path.join(base, name)
            if os.path.exists(p):
                print(f"VERIFIED: {name} exists.")
                with open(p, 'r') as f:
                    print(f"Content of {name}: {f.read()}")
            else:
                print(f"FAILED: {name} MISSING!")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_short()
