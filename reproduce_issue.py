from footybitez.video.text_renderer import TextRenderer
import os
import json

def reproduce():
    # Setup dummy env
    os.makedirs("footybitez/media/voice", exist_ok=True)
    json_path = "footybitez/media/voice/test_debug.json"
    
    # Create dummy JSON with Asterisks to test highlight parsing too
    data = [
        {"word": "*Hello*", "start": 0.0, "duration": 0.5},
        {"word": "Football", "start": 0.5, "duration": 0.5},
        {"word": "*World*", "start": 1.0, "duration": 0.5}
    ]
    with open(json_path, 'w') as f:
        json.dump(data, f)
        
    print(f"Created dummy JSON at {json_path}")
    
    renderer = TextRenderer()
    print("Renderer init.")
    
    # Call render_karaoke_clips matching VideoCreator signature
    clips = renderer.render_karaoke_clips(
        json_path,
        2.0,
        1080, # Shorts width
        1920, # Shorts height (unused but passed)
        is_shorts=True
    )
    
    print(f"Generated {len(clips)} clips.")
    
    if len(clips) > 0:
        c = clips[0]
        # Check size of the clip
        print(f"Clip 1 Size: {c.size}")
        print(f"Clip 1 Duration: {c.duration}")
        # Try to confirm content? Hard with MoviePy clip object without saving
        # But we can check if it errored.
        
        # Check if fonts were loaded? 
        # TextRenderer doesn't expose font status easily but we can infer from logs if we saw "ERROR: Failed to load font"
        
    # Cleanup
    if os.path.exists(json_path): os.remove(json_path)

if __name__ == "__main__":
    reproduce()
