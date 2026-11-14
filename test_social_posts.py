import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from PIL import Image
from footybitez.socials.photo_posts import publish_post, PhotoPostPublisher
from footybitez.socials.post_composer import render_overlay, compose_caption
from footybitez.social_post_main import verified_result, result_headline
from footybitez.media.football_assets import sports_image_url, football_logo, LogoPage
from footybitez.socials.meta_publisher import MetaPublisher


class SocialPostTests(unittest.TestCase):
    @patch.dict('os.environ',{'FOOTYBITEZ_META_ACCESS_TOKEN':'footy-test-token',
        'FOOTYBITEZ_FACEBOOK_PAGE_ID':'footy-page','FOOTYBITEZ_INSTAGRAM_BUSINESS_ACCOUNT_ID':'footy-ig',
        'META_ACCESS_TOKEN':'generic-test-token','FACEBOOK_PAGE_ID':'generic-page',
        'FACEBOOK_PAGE_IDS':'generic-filter','INSTAGRAM_BUSINESS_ACCOUNT_ID':'generic-ig'},clear=True)
    def test_photo_publisher_defaults_to_footybitez_credentials_only(self):
        publisher=PhotoPostPublisher()
        self.assertEqual(publisher.meta.access_token,'footy-test-token')
        self.assertEqual(publisher.meta.page_id,'footy-page')
        self.assertEqual(publisher.meta.instagram_id,'footy-ig')
        self.assertIsNone(publisher.meta.page_ids_filter)
        for publisher_args in ({},{'use_footybitez':True},{'use_footybitez':False}):
            shared=MetaPublisher(**publisher_args)
            self.assertEqual(shared.access_token,'footy-test-token')
            self.assertEqual(shared.page_id,'footy-page')
            self.assertEqual(shared.instagram_id,'footy-ig')
            self.assertIsNone(shared.page_ids_filter)
        with patch.object(publisher.meta,'_get_authorized_pages',return_value=[{'id':'footy-page'},{'id':'generic-page'}]):
            self.assertEqual(publisher.pages(),[{'id':'footy-page'}])

    @patch.dict('os.environ',{'META_ACCESS_TOKEN':'generic-test-token','FACEBOOK_PAGE_ID':'generic-page',
        'INSTAGRAM_BUSINESS_ACCOUNT_ID':'generic-ig'},clear=True)
    def test_missing_footybitez_secrets_never_fall_back_to_generic_brand(self):
        publisher=PhotoPostPublisher()
        self.assertIsNone(publisher.meta.access_token)
        self.assertIsNone(publisher.meta.page_id)
        self.assertIsNone(publisher.meta.instagram_id)
        with patch.object(publisher.meta,'_get_authorized_pages') as discover:
            with self.assertRaisesRegex(RuntimeError,'FOOTYBITEZ_META_ACCESS_TOKEN'):
                publisher.pages()
            discover.assert_not_called()

    def test_workflow_passes_the_dedicated_secret_names(self):
        social_workflows=0
        for path in Path('.github/workflows').glob('*.yml'):
            workflow=path.read_text(encoding='utf-8')
            if 'META_ACCESS_TOKEN' not in workflow:
                continue
            social_workflows+=1
            for name in ('META_ACCESS_TOKEN','FACEBOOK_PAGE_ID','INSTAGRAM_BUSINESS_ACCOUNT_ID'):
                self.assertIn('${{ secrets.FOOTYBITEZ_'+name+' }}',workflow,str(path))
                self.assertNotIn('${{ secrets.'+name+' }}',workflow,str(path))
        self.assertEqual(social_workflows,10)

    @patch.dict('os.environ',{'FOOTYBITEZ_META_ACCESS_TOKEN':'footy-test-token',
        'FOOTYBITEZ_FACEBOOK_PAGE_ID':'footy-page','FOOTYBITEZ_INSTAGRAM_BUSINESS_ACCOUNT_ID':'footy-ig',
        'META_ACCESS_TOKEN':'generic-test-token','FACEBOOK_PAGE_IDS':'generic-page'},clear=True)
    def test_comment_workflow_uses_and_filters_footybitez_account(self):
        with patch('dotenv.load_dotenv'):
            from footybitez.socials.social_comment_manager import SocialCommentManager
        manager=SocialCommentManager()
        self.assertEqual(manager.access_token,'footy-test-token')
        self.assertEqual(manager.page_ids_filter,'footy-page')
        self.assertEqual(manager.instagram_id,'footy-ig')

    def test_shootout_totals_are_not_presented_as_goals_during_play(self):
        match={'homeTeam':{'name':'Germany'},'awayTeam':{'name':'England'},
               'score':{'duration':'PENALTY_SHOOTOUT','fullTime':{'home':7,'away':6},'penalties':{'home':6,'away':5}}}
        self.assertEqual(result_headline(match),'Germany 1–1 England (pens 6–5)')
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

    @patch.dict('os.environ',{'FOOTBALL_DATA_API_KEY':'test'})
    @patch('footybitez.social_post_main.requests.get')
    def test_no_result_is_a_clean_cli_skip_without_publishing_or_claiming(self,get):
        from footybitez.social_post_main import main
        get.return_value.json.return_value={'matches':[]}
        with tempfile.TemporaryDirectory() as folder:
            previous=os.getcwd()
            try:
                os.chdir(folder)
                output=Path(folder)/'github-output.txt'
                summary=Path(folder)/'summary.md'
                with patch.dict('os.environ',{'GITHUB_OUTPUT':str(output),'GITHUB_STEP_SUMMARY':str(summary)}), patch('sys.argv',['social-post','--category','results','--publish']), patch('footybitez.content.history.ContentHistory') as history, patch('footybitez.social_post_main.publish_post') as publish:
                    history.return_value.is_duplicate.return_value=False
                    main()
                    publish.assert_not_called()
                    history.return_value.claim.assert_not_called()
                report=json.loads(Path('footybitez/output/social_posts/run-status.json').read_text())
                self.assertEqual(report['status'],'skipped')
                self.assertIn('skipped=true',output.read_text())
                self.assertIn('Nothing was published',summary.read_text())
                self.assertFalse(Path('footybitez/data/social_posts_state.json').exists())
            finally:
                os.chdir(previous)

    @patch.dict('os.environ',{'FOOTBALL_DATA_API_KEY':'test'})
    @patch('footybitez.social_post_main.requests.get')
    def test_result_api_failure_is_not_hidden_as_an_empty_match_day(self,get):
        import requests
        from footybitez.social_post_main import NoVerifiedResult
        get.return_value.raise_for_status.side_effect=requests.HTTPError('HTTP 401')
        with self.assertRaises(requests.HTTPError):
            verified_result(datetime(2026,11,6,12,tzinfo=timezone.utc))
        self.assertFalse(issubclass(requests.HTTPError,NoVerifiedResult))


if __name__=='__main__': unittest.main()
