import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from footybitez.socials.meta_publisher import MetaPublisher

class TestFBPageRouting(unittest.TestCase):

    @patch.dict(os.environ, {
        "FOOTYBITEZ_META_ACCESS_TOKEN": "mock_footybitez_user_token",
        "FOOTYBITEZ_FACEBOOK_PAGE_ID": "12345_footybitez_page",
        "FOOTYBITEZ_INSTAGRAM_BUSINESS_ACCOUNT_ID": "67890_insta_id",
        "DRY_RUN": "false"
    })
    @patch("footybitez.socials.meta_publisher.requests.post")
    @patch.object(MetaPublisher, "_get_authorized_pages")
    def test_routing_with_matching_page_id(self, mock_get_pages, mock_post):
        # Scenario 1: Both "On Trending Today" and "footybitez" are authorized dynamically
        mock_get_pages.return_value = [
            {"id": "98765_trending_today", "access_token": "token_trending", "name": "On Trending Today"},
            {"id": "12345_footybitez_page", "access_token": "token_footybitez", "name": "FootyBitez"}
        ]

        # Mock the requests.post response for video upload
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "mock_video_post_id"}
        mock_post.return_value = mock_resp

        # Initialize with use_footybitez=True
        publisher = MetaPublisher(use_footybitez=True)
        self.assertEqual(publisher.page_id, "12345_footybitez_page")

        # Mock open() to avoid actual file read
        with patch("builtins.open", unittest.mock.mock_open(read_data=b"dummy_video")):
            video_id = publisher.publish_to_facebook("dummy.mp4", "Test Match", "Description")

        self.assertEqual(video_id, "mock_video_post_id")
        
        # Verify it was only posted to FootyBitez Page ID using the specific Page Access Token
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("12345_footybitez_page/videos", args[0])
        self.assertEqual(kwargs["data"]["access_token"], "token_footybitez")

    @patch.dict(os.environ, {
        "FOOTYBITEZ_META_ACCESS_TOKEN": "mock_footybitez_user_token",
        "FOOTYBITEZ_FACEBOOK_PAGE_ID": "12345_footybitez_page",
        "FOOTYBITEZ_INSTAGRAM_BUSINESS_ACCOUNT_ID": "67890_insta_id",
        "DRY_RUN": "false"
    })
    @patch("footybitez.socials.meta_publisher.requests.post")
    @patch.object(MetaPublisher, "_get_authorized_pages")
    def test_routing_fallback_with_unmatching_page_id(self, mock_get_pages, mock_post):
        # Scenario 2: Only "On Trending Today" is authorized dynamically
        mock_get_pages.return_value = [
            {"id": "98765_trending_today", "access_token": "token_trending", "name": "On Trending Today"}
        ]

        # Mock the requests.post response for video upload
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "mock_fallback_video_post_id"}
        mock_post.return_value = mock_resp

        publisher = MetaPublisher(use_footybitez=True)

        with patch("builtins.open", unittest.mock.mock_open(read_data=b"dummy_video")):
            video_id = publisher.publish_to_facebook("dummy.mp4", "Test Match", "Description")

        self.assertEqual(video_id, "mock_fallback_video_post_id")
        
        # Verify it fell back to posting directly to the targeted page using the User token
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("12345_footybitez_page/videos", args[0])
        self.assertEqual(kwargs["data"]["access_token"], "mock_footybitez_user_token")

if __name__ == "__main__":
    unittest.main()
