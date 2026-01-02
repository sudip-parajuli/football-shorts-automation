
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
# current_dir is .../footybitez/video
# We want .../football-shorts-automation
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
# Actually, let's just act relative to CWD if possible, currently CWD is project root
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

# Mock modules BEFORE importing the unit under test
sys.modules['moviepy.editor'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['footybitez.media.voice_generator'] = MagicMock()

from footybitez.video.long_form_video_creator import LongFormVideoCreator

class TestLongFormVideoFlow(unittest.TestCase):
    
    def setUp(self):
        # Inject mocks into the module namespace because 'from moviepy.editor import *' 
        # doesn't work well with MagicMock modules
        import footybitez.video.long_form_video_creator as module
        
        self.mock_afx = MagicMock()
        module.afx = self.mock_afx
        
        module.AudioFileClip = MagicMock()
        module.ImageClip = MagicMock()
        module.CompositeVideoClip = MagicMock()
        module.VideoFileClip = MagicMock()
        module.ColorClip = MagicMock()
        module.VideoClip = MagicMock()
        module.CompositeAudioClip = MagicMock()
        module.concatenate_videoclips = MagicMock()
        
        # Store for assertions
        self.mock_composite = module.CompositeVideoClip
        self.mock_concat = module.concatenate_videoclips
        
        self.creator = LongFormVideoCreator()
        # Mock internal helpers
        self.creator._get_visual = MagicMock(return_value=MagicMock())
        self.creator._ensure_rgb = MagicMock(side_effect=lambda x: x)
        self.creator._get_karaoke_clips = MagicMock(return_value=[])
        self.creator._create_chapter_overlay = MagicMock(return_value="mock_overlay_path.png")
        
        # Mock VoiceGenerator
        self.creator.voice_gen.generate = MagicMock(return_value="mock_audio.mp3")

    def test_5_phase_structure(self):
        # Setup Mocks
        module = sys.modules['footybitez.video.long_form_video_creator']
        
        mock_audio = MagicMock()
        mock_audio.duration = 5.0
        module.AudioFileClip.return_value = mock_audio
        
        mock_visual_clip = MagicMock()
        mock_visual_clip.duration = 5.0
        self.creator._get_visual.return_value = mock_visual_clip
        
        # Define Script Data
        script_data = {
            "metadata": {"title": "Test Title"},
            "hook": {"text": "Hook text", "visual_keyword": "hook"},
            "intro": {"text": "Intro text", "visual_keyword": "intro"},
            "chapters": [
                {
                    "chapter_title": "Chapter 1",
                    "facts": [{"text": "Fact 1", "visual_keyword": "fact1"}]
                }
            ],
            "outro": {"text": "Outro text", "visual_keyword": "outro"}
        }
        
        visual_assets = {}
        
        # Mock afx
        self.creator.afx = MagicMock()
        sys.modules['moviepy.editor'].afx = MagicMock()
        
        # Run
        try:
            self.creator.create_long_video(script_data, visual_assets)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.fail(f"Execution failed with error: {e}")


        # Verify Phases
        
        calls = self.mock_composite.call_args_list
        print(f"Total CompositeVideoClip calls: {len(calls)}")
        
        # Analyze Calls (This is a heuristic based on my implementation knowledge)
        # 1. Title: list length 2 (Visual + Overlay)
        # 2. Intro: list length 2 (Visual + [Karaoke...])
        # 3. Chapter Card: list length 2 (Visual + Overlay)
        # 4. Chapter Fact: list length 2 (Visual + [Karaoke...])
        # 5. Outro: list length ~3 (Visual + Overlay + [Karaoke...])
        
        self.assertTrue(len(calls) >= 5, f"Should have at least 5 composite clips for the phases, got {len(calls)}")
        
        # Specific check: Main Title Card
        # Arguments to _create_chapter_overlay for Main Title
        # Refined: "FOOTYBITEZ PRESENTS" + Title
        self.creator._create_chapter_overlay.assert_any_call("FOOTYBITEZ PRESENTS", "Test Title")
        
        # Specific check: Chapter Card
        self.creator._create_chapter_overlay.assert_any_call("CHAPTER 1", "Chapter 1")
        
        # Specific check: Outro Card
        self.creator._create_chapter_overlay.assert_any_call("FOOTYBITEZ", "MORE UNTOLD STORIES")

        print("Test Passed: Phases confirmed via mock calls.")

if __name__ == '__main__':
    unittest.main()
