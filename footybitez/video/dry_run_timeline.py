
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

# Mock modules BEFORE importing the unit under test
sys.modules['moviepy.editor'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['footybitez.media.voice_generator'] = MagicMock()

import footybitez.video.long_form_video_creator as module

# Setup Mocks in module namespace
mock_afx = MagicMock()
module.afx = mock_afx

# We will use these lists to track what happens
timeline_events = []

def mock_audio_file_clip(path):
    m = MagicMock()
    # deduce duration from path name if possible, else default
    if "hook" in path: m.duration = 5.0
    elif "intro" in path: m.duration = 10.0
    elif "fact" in path: m.duration = 8.0
    elif "outro" in path: m.duration = 7.0
    else: m.duration = 5.0
    m.name = f"Audio: {path}"
    m.volumex = MagicMock(return_value=m)
    m.subclip = MagicMock(return_value=m)
    return m

def mock_image_clip(path):
    # print(f"DEBUG: Creating Mock ImageClip for {path}")
    m = MagicMock()
    m.duration = 0.0 # Default, usually set later
    m.size = (1920, 1080) 
    m.w = 1920
    m.h = 1080
    
    def set_duration(d):
        m.duration = float(d)
        # print(f"DEBUG: Setting duration to {d} for {m.name}")
        return m
    m.set_duration = set_duration
    m.set_position = MagicMock(return_value=m)
    m.set_start = MagicMock(return_value=m)
    m.resize = MagicMock(return_value=m)
    m.crop = MagicMock(return_value=m)
    m.set_audio = MagicMock(return_value=m)
    m.set_mask = MagicMock(return_value=m)
    m.crossfadein = MagicMock(return_value=m)
    m.fadeout = MagicMock(return_value=m)
    m.fl_image = MagicMock(return_value=m) # For _ensure_rgb
    m.fl = MagicMock(return_value=m) # For add_zoom_effect
    m.name = f"Image: {os.path.basename(path)}"
    
    # Handle resize logic comparisons
    m.get_frame = MagicMock(return_value=MagicMock(shape=(1080, 1920, 3)))
    
    return m

def mock_composite(clips, size=None):
    # Analyze the clips to guess the phase
    duration = 0.0
    for c in clips:
        if hasattr(c, 'duration') and isinstance(c.duration, (int, float)):
             if c.duration > duration: duration = c.duration
    
    # Identify content
    desc = "Unknown Composite"
    
    # Check for specific artifacts we know
    clip_names = [str(getattr(c, 'name', '')) for c in clips]
    has_hook = any("hook" in n for n in clip_names)
    overlays = [n for n in clip_names if "overlay" in n]
    
    # Heuristics based on my logic
    if has_hook: 
        desc = "PHASE 1: COLD HOOK (Voiceover + Subtitles)"
    elif duration == 4.0 and len(overlays) > 0:
        desc = "PHASE 2: MAIN TITLE CARD (Silent, Music Only)"
    elif duration == 10.0: # Matches intro duration
        desc = "PHASE 3: SPOKEN INTRO (Voiceover + Subtitles)"
    elif duration == 2.0:
        desc = "PHASE 4A: CHAPTER TITLE CARD (Silent, Music Only)"
    elif duration == 8.0:
        desc = "PHASE 4B: CHAPTER CONTENT (Voiceover + Subtitles)"
    elif duration >= 7.0 and any("outro" in n for n in clip_names): 
        desc = "PHASE 5: OUTRO"
    else:
        # Fallback detection
        if len(clips) > 2: # Likely visual + overlay + subtitles
             desc = "Content Segment (Narrated)"
        else:
             desc = "Title/Transition Card (Silent)"

    event = {
        "duration": duration,
        "description": desc,
        "clip_count": len(clips)
    }
    timeline_events.append(event)
    
    m = MagicMock()
    m.duration = float(duration)
    m.crossfadein = lambda d: m
    m.fadeout = lambda d: m
    m.name = f"Composite: {desc}"
    m.audio = MagicMock() # For final mix
    return m

module.AudioFileClip = mock_audio_file_clip
module.ImageClip = mock_image_clip
module.CompositeVideoClip = mock_composite
module.VideoFileClip = MagicMock()
module.ColorClip = MagicMock()
module.VideoClip = MagicMock()
module.CompositeAudioClip = MagicMock()
module.concatenate_videoclips = MagicMock(return_value=MagicMock(duration=100)) # return dummy final

from footybitez.video.long_form_video_creator import LongFormVideoCreator

def run_dry_run():
    print("Initializing Dry Run...")
    creator = LongFormVideoCreator()
    
    # Mock internal helpers
    # Return a PROPER mock image clip
    def mock_get_visual(keyword, assets, duration):
         m = mock_image_clip(f"visual_{keyword}")
         m.set_duration(duration)
         return m
    creator._get_visual = MagicMock(side_effect=mock_get_visual)

    creator._ensure_rgb = MagicMock(side_effect=lambda x: x)
    creator._get_karaoke_clips = MagicMock(return_value=[MagicMock(name="Subtitle1"), MagicMock(name="Subtitle2")])
    
    # Mock voice gen to just return the filename as path
    creator.voice_gen.generate = lambda text, filename: filename
    
    # Mock overlay creation to return a descriptive path
    def mock_overlay(upper, lower):
        # Clean strings for filename
        upper = "".join([c for c in upper if c.isalnum() or c==' '])
        lower = "".join([c for c in lower if c.isalnum() or c==' '])
        return f"temp_text/overlay_{upper}_{lower}.png"
    creator._create_chapter_overlay = mock_overlay

    script_data = {
        "metadata": {"title": "The Rise of Yamal"},
        "hook": {"text": "A star was born in Spain.", "visual_keyword": "Lamine Yamal smiling"},
        "intro": {"text": "Lamine Yamal is breaking every record.", "visual_keyword": "Camp Nou"},
        "chapters": [
            {
                "chapter_title": "Early Life",
                "facts": [
                    {"text": "He joined La Masia at age 7.", "visual_keyword": "La Masia"},
                    {"text": "He debuted at 15.", "visual_keyword": "Debut match"}
                ]
            }
        ],
        "outro": {"text": "What will he do next?", "visual_keyword": "Yamal celebrating"}
    }
    
    print("\n--- STARTING VIDEO COMPOSITION ---")
    creator.create_long_video(script_data, {})
    
    print("\n--- GENERATED VIDEO TIMELINE ---")
    current_time = 0.0
    for i, event in enumerate(timeline_events):
        start = current_time
        end = current_time + event['duration']
        print(f"[{start:05.2f}s - {end:05.2f}s] {event['description']}")
        print(f"                   Duration: {event['duration']}s | Layers: {event['clip_count']} (Visuals, Overlays, Subs)")
        print("-" * 60)
        current_time = end

    print(f"Total Estimated Duration: {current_time:.2f}s")
    print("--------------------------------")

if __name__ == "__main__":
    run_dry_run()
