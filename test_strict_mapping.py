
import os
import logging
from footybitez.video.video_creator import VideoCreator
from PIL import Image

# Setup logging
logging.basicConfig(level=logging.INFO)

def create_dummy_image(filename, color):
    img = Image.new('RGB', (1080, 1920), color)
    img.save(filename)
    return os.path.abspath(filename)

def test_strict_mapping():
    print("\n--- Testing Strict Media Mapping ---")
    
    # 1. Setup Dummy Assets
    img_a = create_dummy_image("seg1_a.jpg", "red")
    img_b = create_dummy_image("seg1_b.jpg", "blue")
    img_c = create_dummy_image("seg2_a.jpg", "green")
    
    # Structure: List of Lists
    segment_media = [
        [img_a, img_b], # Segment 0
        [img_c]         # Segment 1
    ]
    
    assets = {
        "title_card": img_a,
        "profile_image": None,
        "segment_media": segment_media
    }
    
    # 2. Mock Script
    script = {
        "hook": "This is the hook",
        "segments": [
            {"text": "Segment one text about red and blue.", "visual_keyword": "red blue"},
            {"text": "Segment two text about green.", "visual_keyword": "green"}
        ],
        "outro": "Outro text."
    }
    
    # 3. Initialize Creator
    creator = VideoCreator()
    
    # Mock VoiceGenerator to strictly return a dummy MP3 without API usage
    # We can't easily mock the import inside the class without patching, 
    # but we can patch the instance method.
    
    original_generate = creator.voice_gen.generate
    
    def mock_generate(text, filename):
        # Create silent mp3
        from moviepy.editor import AudioClip
        import numpy as np
        
        def make_silence(t):
            t = np.atleast_1d(t)
            return np.zeros((len(t), 2))
            
        # 1 sec silent clip
        clip = AudioClip(make_silence, duration=1.0, fps=44100)
        path = os.path.join("footybitez/output", filename)
        clip.write_audiofile(path, logger=None)
        return path
        
    creator.voice_gen.generate = mock_generate
    
    try:
        print("Running create_video with strict mapping...")
        output = creator.create_video(script, assets)
        print(f"Video created successfully: {output}")
        assert os.path.exists(output)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAILED: {e}")
        raise e
    finally:
        # Cleanup
        if os.path.exists("seg1_a.jpg"): os.remove("seg1_a.jpg")
        if os.path.exists("seg1_b.jpg"): os.remove("seg1_b.jpg")
        if os.path.exists("seg2_a.jpg"): os.remove("seg2_a.jpg")

if __name__ == "__main__":
    test_strict_mapping()
