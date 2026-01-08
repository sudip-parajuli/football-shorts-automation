from footybitez.video.text_renderer import TextRenderer
import os
import sys
import time

# Ensure project root in path
sys.path.append(os.getcwd())

def test_karaoke():
    try:
        renderer = TextRenderer()
        print("TextRenderer initialized.")
        
        json_path = os.path.join("footybitez", "media", "voice", "segment_2.json")
        if not os.path.exists(json_path):
            print(f"JSON not found: {json_path}")
            return

        print(f"Testing karaoke on {json_path}...")
        start_time = time.time()
        
        # Test Shorts settings
        clips = renderer.render_karaoke_clips(
            json_path, 
            10.0, # Dummy duration
            1080, 
            1920,
            is_shorts=True
        )
        
        end_time = time.time()
        print(f"Renderer returned {len(clips)} clips in {end_time - start_time:.2f} seconds.")
        
        if len(clips) > 0:
            print(f"First clip duration: {clips[0].duration}")
            print(f"First clip position: {clips[0].pos(0)}")
            
            # Check frame generation of first clip
            print("Generating frame for first clip...")
            frame = clips[0].get_frame(0.5)
            print(f"Frame shape: {frame.shape}")

    except Exception as e:
        print(f"Karaoke Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_karaoke()
