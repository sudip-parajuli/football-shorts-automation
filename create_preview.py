from footybitez.video.text_renderer import TextRenderer
from moviepy.editor import ColorClip, CompositeVideoClip, TextClip
import os
import sys

# Ensure project root in path
sys.path.append(os.getcwd())

def create_preview():
    try:
        renderer = TextRenderer()
        print("TextRenderer initialized.")
        
        # 1. Chunk 1: "THIS IS MASSIVE"
        chunk1 = [
            {"start": 0.0, "duration": 0.5, "word": "THIS"},
            {"start": 0.5, "duration": 0.5, "word": "is"},
            {"start": 1.0, "duration": 1.0, "word": "MASSIVE"},
        ]
        clip1 = renderer.render_phrase(chunk1, 2.0, 1080, is_shorts=True)
        clip1 = clip1.set_start(0).set_position("center")
        
        # 2. Chunk 2: "AND CENTERED!"
        chunk2 = [
            {"start": 2.0, "duration": 0.5, "word": "AND"},
            {"start": 2.5, "duration": 1.0, "word": "CENTERED!"},
        ]
        clip2 = renderer.render_phrase(chunk2, 1.5, 1080, is_shorts=True)
        clip2 = clip2.set_start(2.0).set_position("center")
        
        # 3. Chunk 3: "ATTACK with RED"
        chunk3 = [
            {"start": 3.5, "duration": 0.5, "word": "ATTACK"},
            {"start": 4.0, "duration": 0.5, "word": "with"},
            {"start": 4.5, "duration": 0.5, "word": "RED"},
            {"start": 5.0, "duration": 0.5, "word": "Danger!"},
        ]
        clip3 = renderer.render_phrase(chunk3, 2.0, 1080, is_shorts=True)
        clip3 = clip3.set_start(3.5).set_position("center")

        # Background (Black/Dark Grey)
        bg = ColorClip(size=(1080, 1920), color=(20, 20, 20), duration=6.0)
        
        # Composite
        final = CompositeVideoClip([bg, clip1, clip2, clip3])
        
        output_path = "footybitez/output/preview_style.mp4"
        print(f"Writing preview to {output_path}...")
        final.write_videofile(output_path, fps=30, codec='libx264', audio=False)
        print("Done!")
        
    except Exception as e:
        print(f"Preview Creation Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_preview()
