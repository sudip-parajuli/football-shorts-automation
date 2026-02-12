import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from footybitez.media.media_sourcer import MediaSourcer

class TestMediaLogic(unittest.TestCase):
    def setUp(self):
        self.sourcer = MediaSourcer(download_dir="test_downloads")

    @patch('footybitez.media.media_sourcer.MediaSourcer._fetch_youtube_clip')
    @patch('footybitez.media.media_sourcer.MediaSourcer._fetch_scorebat_highlight')
    @patch('footybitez.media.media_sourcer.MediaSourcer._fetch_wikimedia_images')
    @patch('footybitez.media.media_sourcer.MediaSourcer._fetch_ddg_images')
    @patch('footybitez.media.media_sourcer.MediaSourcer._fetch_pexels_videos')
    def test_media_priority(self, mock_pexels, mock_ddg, mock_wiki, mock_sb, mock_yt):
        print("DEBUG: Setting up mocks")
        mock_sb.return_value = None
        mock_yt.return_value = "youtube.mp4"
        mock_wiki.return_value = ["wiki.jpg"]
        mock_ddg.return_value = ["ddg.jpg"]
        mock_pexels.return_value = ["pexels.mp4"]

        print("DEBUG: Calling get_media")
        paths = self.sourcer.get_media("Ronaldo", count=4)
        print(f"DEBUG: Paths returned: {paths}")
        
        # Strict fallback: "Ronaldo" is specific, so we SKIP Pexels if we have other media.
        # We expect 3 paths (YT, Wiki, DDG), not 4.
        self.assertEqual(len(paths), 3, f"Expected 3 paths (Strict Fallback), got {len(paths)}")
        self.assertIn("youtube.mp4", paths, "YouTube clip not in paths")
        self.assertIn("wiki.jpg", paths, "Wiki image not in paths")
        self.assertIn("ddg.jpg", paths, "DDG image not in paths")
        
        mock_yt.assert_called_once()


    @patch('footybitez.media.media_sourcer.MediaSourcer._fetch_pexels_videos')
    def test_generic_fallback(self, mock_pexels):
        # Test generic query fallback
        mock_pexels.return_value = ["pexels.mp4"]
        
        # Query "football match" is not in specific list
        # We assume other sources fail or return partial
        with patch('footybitez.media.media_sourcer.MediaSourcer._fetch_youtube_clip', return_value=None), \
             patch('footybitez.media.media_sourcer.MediaSourcer._fetch_scorebat_highlight', return_value=None), \
             patch('footybitez.media.media_sourcer.MediaSourcer._fetch_wikimedia_images', return_value=[]), \
             patch('footybitez.media.media_sourcer.MediaSourcer._fetch_ddg_images', return_value=[]):
             
             paths = self.sourcer.get_media("football match", count=2)
             
             self.assertIn("pexels.mp4", paths)
             mock_pexels.assert_called()

if __name__ == '__main__':
    unittest.main()
