import os
import json
import numpy as np
from PIL import Image
import sys

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from footybitez.video.video_creator import VideoCreator

def verify_captions():
    print("Testing caption rendering logic...")
    vc = VideoCreator()
    
    # Mock some word data with distinct lines
    word_data = [
        {"word": "Line", "start": 0.0, "duration": 0.5},
        {"word": "One", "start": 0.5, "duration": 0.5},
        {"word": "Test", "start": 1.0, "duration": 0.5},
        
        {"word": "Line", "start": 1.5, "duration": 0.5},
        {"word": "Two", "start": 2.0, "duration": 0.5},
        {"word": "Works", "start": 2.5, "duration": 0.5},
    ]
    
    # Use the logic from _get_karaoke_clips (Simplified)
    # We'll just manually call make_line_frame for different times
    
    lines = [word_data[0:3], word_data[3:6]]
    
    os.makedirs("footybitez/output/test_captions", exist_ok=True)
    
    for i, line in enumerate(lines):
        l_start = line[0]['start']
        l_content = line
        
        # This is the inner function we want to test
        def make_line_frame_local(t, current_line=l_content, line_start_abs=l_start):
            from PIL import Image, ImageDraw, ImageFont
            absolute_t = line_start_abs + t
            canvas = Image.new('RGBA', (1080, 400), (0, 0, 0, 0))
            draw = ImageDraw.Draw(canvas)
            
            # Use basic font for test
            font = ImageFont.load_default(size=60)
            
            full_text = " ".join([w['word'] for w in current_line])
            bbox = draw.textbbox((0, 0), full_text, font=font)
            text_w = bbox[2] - bbox[0]
            start_x = (1080 - text_w) // 2
            
            current_x = start_x
            for word_info in current_line:
                word = word_info['word'] + " "
                w_bbox = draw.textbbox((0, 0), word, font=font)
                w_w = w_bbox[2] - w_bbox[0]
                
                is_active = word_info['start'] <= absolute_t <= (word_info['start'] + word_info['duration'])
                
                if is_active:
                    draw.rectangle([current_x, 10, current_x + w_w, 130], fill=(255, 255, 0, 255))
                    draw.text((current_x, 10), word, font=font, fill=(0, 0, 0, 255))
                else:
                    draw.text((current_x, 10), word, font=font, fill=(255, 255, 255, 255))
                current_x += w_w
            return canvas

        # Check line content
        print(f"Testing Line {i+1}: {' '.join([w['word'] for w in l_content])}")
        
        # Save a frame for each word in the line
        for j, word_info in enumerate(l_content):
            t_mid = word_info['start'] - l_start + 0.1
            frame = make_line_frame_local(t_mid)
            frame.save(f"footybitez/output/test_captions/line_{i+1}_word_{j+1}.png")

    print("Frames saved to footybitez/output/test_captions/")
    print("Verification script finished.")

if __name__ == "__main__":
    verify_captions()
