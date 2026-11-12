import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from footybitez.socials.meta_publisher import MetaPublisher


def response(data, status=200):
    return Mock(status_code=status, json=Mock(return_value=data), headers={'Content-Type':'application/json'})


class LargeVideoPublishingTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'FOOTYBITEZ_META_ACCESS_TOKEN':'page-token',
            'FOOTYBITEZ_INSTAGRAM_BUSINESS_ACCOUNT_ID':'ig', 'DRY_RUN':'false'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.publisher = MetaPublisher()

    @patch('footybitez.socials.meta_publisher.requests.post')
    def test_facebook_transfers_exact_server_requested_chunks_before_finishing(self, post):
        post.side_effect = [response({'upload_session_id':'s','video_id':'v','start_offset':'0','end_offset':'4'}),
            response({'start_offset':'4','end_offset':'8'}), response({'start_offset':'8','end_offset':'8'}),
            response({'success':True})]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'video.mp4'
            path.write_bytes(b'abcdefgh')
            self.assertEqual(self.publisher._upload_facebook_chunks(path,'page','token','Title','Caption'), 'v')
        calls = post.call_args_list
        self.assertEqual([c.kwargs['data']['upload_phase'] for c in calls], ['start','transfer','transfer','finish'])
        self.assertEqual(calls[1].kwargs['files']['video_file_chunk'][1], b'abcd')
        self.assertEqual(calls[2].kwargs['files']['video_file_chunk'][1], b'efgh')
        self.assertIn('graph-video.facebook.com', calls[0].args[0])

    @patch('footybitez.socials.meta_publisher.requests.post')
    def test_invalid_transfer_offset_does_not_publish(self, post):
        post.side_effect = [response({'upload_session_id':'s','video_id':'v','start_offset':'0','end_offset':'4'}),
            response({'start_offset':'0','end_offset':'4'})]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'video.mp4'
            path.write_bytes(b'abcd')
            with self.assertRaisesRegex(RuntimeError,'advance'):
                self.publisher._upload_facebook_chunks(path,'page','token','Title','Caption')
        self.assertEqual(post.call_count,2)

    def test_html_error_reports_http_status_without_response_body_or_token(self):
        result = Mock(status_code=413, headers={'Content-Type':'text/html'})
        result.json.side_effect = ValueError('secret token')
        with self.assertRaisesRegex(RuntimeError,'HTTP 413, non-JSON') as error:
            self.publisher._response_data(result, 'Facebook upload')
        self.assertNotIn('secret',str(error.exception))

    @patch('footybitez.socials.meta_publisher.time.sleep')
    @patch('footybitez.socials.meta_publisher.requests.get')
    @patch('footybitez.socials.meta_publisher.requests.post')
    def test_instagram_streams_local_file_without_public_hosting(self, post, get, sleep):
        post.side_effect = [response({'id':'container','uri':'https://rupload.facebook.com/ig-api-upload/container'}),
                              response({'success':True}), response({'id':'published'})]
        get.return_value = response({'status_code':'FINISHED'})
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'video.mp4'
            path.write_bytes(b'video')
            self.assertEqual(self.publisher.publish_to_instagram_reel(None,'Caption',local_file=path),'published')
        create, upload, publish = post.call_args_list
        self.assertEqual(create.kwargs['data']['upload_type'],'resumable')
        self.assertNotIn('video_url', create.kwargs['data'])
        self.assertEqual(upload.kwargs['headers']['file_size'],'5')
        self.assertFalse(upload.kwargs['allow_redirects'])
        self.assertEqual(publish.kwargs['data']['creation_id'],'container')

    @patch('footybitez.socials.meta_publisher.requests.post')
    def test_instagram_never_sends_token_to_untrusted_upload_host(self, post):
        post.return_value=response({'id':'container','uri':'https://example.com/upload'})
        self.assertIsNone(self.publisher.publish_to_instagram_reel(None,'Caption',local_file='video.mp4'))
        self.assertEqual(post.call_count,1)

    def test_successful_youtube_upload_remains_successful_when_socials_fail(self):
        # Load the entry point with network clients stubbed, so CI needs no OAuth SDKs.
        dependencies = {name:Mock() for name in ('footybitez.youtube.uploader',
            'footybitez.youtube.comment_manager', 'footybitez.socials.social_orchestrator')}
        spec=importlib.util.spec_from_file_location('long_upload_test_target','footybitez/long_upload.py')
        module=importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules',dependencies):
            spec.loader.exec_module(module)
        module.YouTubeUploader.return_value.upload_video.return_value='existing-youtube-id'
        module.SocialOrchestrator.return_value.publish_to_all.side_effect=RuntimeError('social error')
        with tempfile.TemporaryDirectory() as directory:
            previous=os.getcwd()
            try:
                os.chdir(directory)
                Path('remotion-video/output').mkdir(parents=True)
                Path('remotion-video/public').mkdir(parents=True)
                Path('remotion-video/output/video.mp4').touch()
                Path('remotion-video/public/metadata.json').write_text(json.dumps({'title':'Title','topic':'Topic'}))
                with patch.dict(os.environ,{'ENABLE_UPLOAD_LONG':'true','ENABLE_SOCIAL_PUBLISHING':'true','GITHUB_STEP_SUMMARY':''}), patch('footybitez.content.topic_generator.TopicGenerator.mark_topic_as_used'):
                    module.main()
                report=json.loads(Path('remotion-video/output/publication-results.json').read_text())
                self.assertEqual(report['status'],'partial_success')
                self.assertEqual(report['youtube']['id'],'existing-youtube-id')
                self.assertEqual(report['social']['status'],'failed_or_needs_review')
                module.YouTubeUploader.return_value.upload_video.assert_called_once()
            finally:
                os.chdir(previous)
