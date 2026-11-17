import importlib.util
import json
import logging
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch


class RequestedShortTests(unittest.TestCase):
    def setUp(self):
        clients=['footybitez.content.script_generator','footybitez.media.media_sourcer',
                 'footybitez.video.remotion_video_creator','footybitez.youtube.uploader',
                 'footybitez.socials.social_orchestrator']
        self.dependencies={name:Mock() for name in clients}
        self.dependencies['footybitez.video.remotion_video_creator'].MissingVisualError=type('MissingVisualError',(RuntimeError,),{})
        modules=patch.dict('sys.modules',self.dependencies)
        modules.start();self.addCleanup(modules.stop)
        spec=importlib.util.spec_from_file_location('daily_short_test_target','footybitez/main.py')
        self.module=importlib.util.module_from_spec(spec)
        with patch('logging.FileHandler',return_value=logging.NullHandler()):
            spec.loader.exec_module(self.module)
        self.directory=tempfile.TemporaryDirectory()
        self.previous=os.getcwd()
        os.chdir(self.directory.name)
        self.addCleanup(self.cleanup)
        self.env=patch.dict(os.environ,{'ENABLE_UPLOAD':'false','ENABLE_SOCIAL_PUBLISHING':'false'})
        self.env.start();self.addCleanup(self.env.stop)
        self.topics=patch.object(self.module,'TopicGenerator');self.topic=self.topics.start();self.addCleanup(self.topics.stop)
        self.topic.return_value.get_random_topic.return_value=('Automatic story','Football Stories')
        self.history=patch.object(self.module,'ContentHistory');self.history_mock=self.history.start();self.addCleanup(self.history.stop)
        self.history_mock.return_value.is_duplicate.return_value=False
        tools=patch('footybitez.video.preflight.require_media_tools');tools.start();self.addCleanup(tools.stop)
        music=patch('footybitez.media.music_selector.select_music',return_value=None);music.start();self.addCleanup(music.stop)
        self.script={'title':'Requested story','hook':'A grounded opening','full_text':'Narration','segments':[]}
        self.module.ScriptGenerator.return_value.generate_script.return_value=self.script
        self.module.RemotionVideoCreator.return_value.create_video.return_value='preview.mp4'
        self.module.MediaSourcer.return_value.credits_file='missing-credits.txt'

    def cleanup(self):
        os.chdir(self.previous)
        self.directory.cleanup()

    def test_requested_topic_and_angle_reach_script_and_artifact_without_random_selection(self):
        topic='England vs Croatia UEFA Nations League 2026-11-17'
        self.module.main(['--topic',topic,'--category','pre-match preview'])
        self.module.ScriptGenerator.return_value.generate_script.assert_called_once_with(topic,'pre-match preview')
        self.topic.return_value.get_random_topic.assert_not_called()
        saved=json.loads(Path('footybitez/output/script.json').read_text())
        self.assertEqual(saved['topic'],topic)
        self.assertEqual(saved['category'],'pre-match preview')
        self.module.YouTubeUploader.assert_not_called()
        self.module.SocialOrchestrator.assert_not_called()

    def test_blank_topic_keeps_automatic_mode(self):
        self.module.main(['--topic','   '])
        self.topic.return_value.get_random_topic.assert_called_once()
        self.module.ScriptGenerator.return_value.generate_script.assert_called_once_with('Automatic story','Football Stories')

    def test_failed_custom_research_does_not_switch_topics_or_render(self):
        self.module.ScriptGenerator.return_value.generate_script.return_value=None
        with self.assertRaises(SystemExit) as error:
            self.module.main(['--topic','Specific fixture'])
        self.assertEqual(error.exception.code,1)
        self.topic.return_value.get_random_topic.assert_not_called()
        self.module.RemotionVideoCreator.assert_not_called()
        self.module.ScriptGenerator.return_value.generate_script.assert_called_once_with('Specific fixture','General')

    def test_published_custom_topic_is_skipped_before_generation(self):
        with patch.dict(os.environ,{'ENABLE_UPLOAD':'true','GITHUB_OUTPUT':str(Path(self.directory.name)/'outputs.txt')}):
            self.history_mock.return_value.is_duplicate.return_value=True
            self.module.main(['--topic','Existing story'])
        self.module.ScriptGenerator.assert_not_called()
        self.assertIn('skipped=true',Path('outputs.txt').read_text())

    def test_request_is_passed_as_data_even_when_it_contains_shell_characters(self):
        topic='England vs Croatia; $(echo unsafe) "quoted"'
        self.module.main(['--topic',topic])
        self.module.ScriptGenerator.return_value.generate_script.assert_called_once_with(topic,'General')


class TopicWorkflowTests(unittest.TestCase):
    def test_workflow_passes_inputs_through_quoted_environment_values(self):
        workflow=Path('.github/workflows/upload.yml').read_text()
        self.assertIn('SHORT_TOPIC: ${{ inputs.topic }}',workflow)
        self.assertIn('--topic "$SHORT_TOPIC" --category "$SHORT_CATEGORY"',workflow)
        self.assertNotIn('--topic "${{ inputs.topic }}"',workflow)
        self.assertIn('default: false',workflow)
