import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from PIL import Image
from footybitez.socials.photo_posts import publish_post
from footybitez.socials.post_composer import render_overlay, compose_caption
from footybitez.social_post_main import verified_result
from footybitez.media.football_assets import sports_image_url, football_logo, LogoPage


class SocialPostTests(unittest.TestCase):
    def test_public_sports_urls_use_provider_ids_and_versions(self):
        self.assertEqual(sports_image_url('competitors',132,8),'https://api.sportsapipro.com/v1/football/images/competitors/132?imageVersion=8')
        for kind,identifier in [('players',132),('athletes','Lionel Messi'),('competitors','../123')]:
            with self.assertRaises(ValueError): sports_image_url(kind,identifier)

    def test_logo_page_retains_exact_identity_and_real_image_url(self):
        page=LogoPage()
        page.feed('<a href="/england/manchester-united/">Manchester United</a><img src="https://assets.football-logos.cc/real.png" alt="Manchester United logo">')
        self.assertEqual(page.links,[['/england/manchester-united/','Manchester United']])
        self.assertEqual(page.images[0]['alt'],'Manchester United logo')

    @patch('footybitez.media.football_assets.sports_entity_image',return_value=None)
    @patch('footybitez.media.football_assets.requests.get')
    def test_logo_lookup_never_substitutes_similar_club(self,get,fallback):
        get.return_value.text='<a href="/england/manchester-city/">Manchester City</a>'
        self.assertIsNone(football_logo(Mock(spec=['download_dir']), 'Manchester United'))
        self.assertEqual(get.call_count,1)

    def test_text_rerun_skips_published_page_and_instagram(self):
        publisher=Mock()
        publisher.pages.return_value=[{'id':'page'}]
        publisher.facebook.return_value='posted'
        state={}
        plan={'slot':'day','format':'text','caption':'**test**'}
        with tempfile.TemporaryDirectory() as folder:
            for _ in range(2):
                publish_post(plan,state,Path(folder)/'state.json',publisher)
        self.assertEqual(publisher.facebook.call_count,1)
        publisher.instagram.assert_not_called()

    def test_ambiguous_facebook_response_does_not_retry(self):
        publisher=Mock(); publisher.pages.return_value=[{'id':'page'}]
        publisher.facebook.side_effect=TimeoutError('timeout')
        state={}; plan={'slot':'day','format':'text','caption':'test'}
        with tempfile.TemporaryDirectory() as folder:
            for _ in range(2):
                with self.assertRaises(RuntimeError):
                    publish_post(plan,state,Path(folder)/'state.json',publisher)
        self.assertEqual(publisher.facebook.call_count,1)

    def test_caption_strips_formatting_without_truncating_sentences(self):
        caption=compose_caption({'hook':'**A real story**','segments':[{'text':'A grounded sentence.'}],'outro':'Your view?'})
        self.assertNotIn('**',caption)
        self.assertIn('A grounded sentence.',caption)

    def test_overlay_has_expected_social_dimensions(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'real.jpg'; Image.new('RGB',(1600,900),'green').save(source)
            output=Path(folder)/'post.jpg'
            render_overlay(source,'How a football stadium became an icon',output)
            with Image.open(output) as image:
                self.assertEqual(image.size,(1080,1350))

    @patch.dict('os.environ',{'FOOTBALL_DATA_API_KEY':'test'})
    @patch('footybitez.social_post_main.requests.get')
    def test_result_rejects_scheduled_and_missing_scores(self,get):
        get.return_value.json.return_value={'matches':[{'utcDate':'2026-11-06T08:00:00Z','status':'SCHEDULED','score':{'fullTime':{'home':None,'away':None}}}]}
        with self.assertRaises(RuntimeError):
            verified_result(datetime(2026,11,6,12,tzinfo=timezone.utc))


if __name__=='__main__': unittest.main()
