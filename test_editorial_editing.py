import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image
from footybitez.content.edit_direction import graphic_brief
from footybitez.media.caption_alignment import align_transcript
from footybitez.media.edit_audio import plan_sound_cues
from footybitez.video.short_timeline import plan_visual_beats


class EditorialEditingTests(unittest.TestCase):
    def test_editorial_graphic_contains_only_spoken_claims(self):
        for text in ['The board will decide whether to keep the coach.',
                     'The club scored 3 goals during the match.',
                     'A squad announcement is expected after the meeting.']:
            graphic = graphic_brief(text)
            self.assertIn(graphic['detail'], text)
            self.assertIn(graphic['headline'], text)
            if graphic['focus']:
                self.assertIn(graphic['focus'], text)
        self.assertEqual(graphic_brief('The board will decide after the vote.')['layout'], 'decision')

    def test_complete_sentences_and_contextual_motifs_are_preserved(self):
        text = 'The player reviewed the contract carefully before explaining why the final decision would depend on his family and the next stage of his career rather than the size of the offer.'
        self.assertEqual(graphic_brief(text)['detail'], text)
        self.assertEqual(graphic_brief(text)['motif'], 'contract')
        self.assertEqual(graphic_brief('The board has not announced the decision.')['motif'], '')
        self.assertEqual(graphic_brief('The team lifted the trophy.')['motif'], 'trophy')
        self.assertEqual(graphic_brief('Recovery from injury took time.')['motif'], 'recovery')

    def test_no_photo_plan_is_complete_and_does_not_invent_diagrams(self):
        scenes, _, _ = plan_visual_beats('The board discussed the coach. No final decision has been announced. Reports describe talks about the next steps.', [], 12)
        self.assertTrue(all(scene['kind']=='editorial' for scene in scenes))
        self.assertEqual(sum(scene['duration_frames'] for scene in scenes), 288)
        self.assertTrue(all(scene['graphic']['detail'] in scene['narration_snippet'] for scene in scenes))

    def test_whisper_anchors_keep_the_authored_words(self):
        text = 'The manager is discussing a new contract with the board'
        observed = [{'word': word, 'start': index*.4, 'duration':.3} for index,word in enumerate(text.split())]
        observed[1]['word'] = 'stranger'
        words, source = align_transcript(text, observed, 5)
        self.assertEqual(source, 'whisper_word_marks')
        self.assertEqual(' '.join(word['word'] for word in words), text)
        self.assertEqual(words[4]['start'], 1.6)

    def test_unreliable_transcript_is_reported_as_approximate(self):
        words, source = align_transcript('The manager is discussing a contract', [{'word':'hallucination','start':0,'duration':1}], 5)
        self.assertEqual(source, 'interpolated')
        self.assertEqual(words[-1]['start']+words[-1]['duration'], 5)

    def test_sound_cues_follow_reveals_and_have_spacing_and_a_budget(self):
        scenes = [{'from_frame':i*24,'graphic':{'layout':'number'}} for i in range(40)]
        cues = plan_sound_cues([{'duration':40,'visual_scenes':scenes}])
        self.assertLessEqual(len(cues), 6)
        self.assertTrue(all(b['from_frame']-a['from_frame']>=96 for a,b in zip(cues,cues[1:])))
        self.assertEqual(plan_sound_cues([{'duration':8,'visual_scenes':[{'from_frame':0,'graphic':{'layout':'statement'}}]}]), [])

    def test_processed_rss_articles_without_hash_do_not_crash_story_retry(self):
        from footybitez.pipelines.general_news_pipeline import GeneralNewsPipeline
        class MissingVisual(Exception):
            pass
        pipeline = GeneralNewsPipeline.__new__(GeneralNewsPipeline)
        old_hash = hashlib.sha256(b'Old story').hexdigest()
        articles = [{'title':'Old story'}, {'title':'First new story'}, {'title':'Second new story'}]
        pipeline.state = {'processed_hashes':[old_hash]}
        pipeline.crawl_rss_headlines = Mock(return_value=articles)
        pipeline.select_viral_headline = lambda items: next((item for item in items if item['hash'] not in pipeline.state['processed_hashes']), None)
        pipeline._produce_story = Mock(side_effect=[MissingVisual('missing'), 'video.mp4'])
        pipeline.media_sourcer = Mock()
        module = SimpleNamespace(MissingVisualError=MissingVisual)
        with patch.dict('sys.modules', {'footybitez.video.remotion_video_creator':module}):
            self.assertEqual(pipeline.run(skip_upload=True), 'video.mp4')
        self.assertEqual(pipeline._produce_story.call_count, 2)
        self.assertEqual(articles[0]['hash'], old_hash)

    def test_photo_post_uses_original_editorial_image_when_photos_are_unavailable(self):
        from test_content_quality import good_script
        from footybitez.social_post_main import main
        script = good_script()
        script.update(title='The decision behind a football rule', primary_entity='', research_context='')
        cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                with patch('sys.argv',['social_post_main','--topic','Rule','--format','photo']), \
                     patch('footybitez.content.script_generator.ScriptGenerator.generate_script',return_value=script), \
                     patch('footybitez.media.media_sourcer.MediaSourcer'), \
                     patch('footybitez.social_post_main.publish_post') as publish:
                    main()
                plan = json.loads(Path('footybitez/output/social_posts/post.json').read_text())
                self.assertEqual(plan['visual_type'],'editorial')
                with Image.open(plan['image_path']) as image:
                    self.assertEqual(image.size,(1080,1350))
                publish.assert_not_called()
            finally:
                os.chdir(cwd)


if __name__=='__main__':
    unittest.main()
