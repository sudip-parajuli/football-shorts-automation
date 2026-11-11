import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from footybitez.content.history import ContentHistory, DuplicateContent, signature


class ContentHistoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'history.json'
        seed = patch('footybitez.content.history.seed_history',side_effect=lambda: {'entries':{},'legacy_hashes':[]})
        seed.start()
        self.addCleanup(seed.stop)
        self.history = ContentHistory(self.path)

    def test_same_piece_can_reach_multiple_platforms_but_not_upload_twice(self):
        claim = self.history.claim('A new managerial decision','The board has announced a new coach.','youtube')
        self.history.complete(claim['key'],'youtube','video-id')
        repeat = self.history.claim('A reworded title','The board has announced a new coach.','youtube')
        self.assertEqual(repeat['previous'],'video-id')
        social = self.history.claim('A new managerial decision','The board has announced a new coach.','social')
        self.assertEqual(social['key'],claim['key'])
        self.assertIsNone(social['previous'])

    def test_same_finished_video_can_use_platform_specific_captions(self):
        claim = self.history.claim('The coaching decision','Longer YouTube description.','youtube',piece_id='video-file-hash')
        self.history.complete(claim['key'],'youtube','video-id')
        social = self.history.claim('The coaching decision','A short Instagram caption.','social',piece_id='video-file-hash')
        self.assertEqual(social['key'],claim['key'])
        self.assertIsNone(social['previous'])

    def test_reworded_topic_is_blocked_across_formats(self):
        self.history.claim('How Manchester United choose the next manager','First narration.','youtube')
        self.assertTrue(self.history.is_duplicate('Why Manchester United choose their next manager'))
        with self.assertRaises(DuplicateContent):
            self.history.claim('Why Manchester United choose their next manager','A rewritten narration.','post')

    def test_same_script_with_a_different_title_is_blocked(self):
        text='The club board reviewed the coaching position during its meeting.'
        self.history.claim('The coaching decision',text,'youtube')
        with self.assertRaises(DuplicateContent):
            self.history.claim('A completely different headline',text,'post')

    def test_publication_claim_rechecks_after_a_stale_selection_snapshot(self):
        other = ContentHistory(self.path)
        self.assertFalse(other.is_duplicate('A unique managerial story'))
        self.history.claim('A unique managerial story','The club confirmed a new coach.','youtube')
        with self.assertRaises(DuplicateContent):
            other.claim('A unique managerial story','The club confirmed a new coach.','youtube')

    def test_pending_photo_can_resume_only_through_its_existing_ledger(self):
        self.history.claim('The football board vote','A vote is pending.','post')
        with self.assertRaises(DuplicateContent):
            self.history.claim('The football board vote','A vote is pending.','post')
        self.assertIsNone(self.history.claim('The football board vote','A vote is pending.','post',resume=True)['previous'])

    def test_matches_on_different_dates_have_distinct_identity(self):
        self.history.claim('Arsenal 1–0 Chelsea | 2026-11-09','The match was played on 2026-11-09.','youtube')
        self.assertFalse(self.history.is_duplicate('Arsenal 1–0 Chelsea | 2026-11-10','The match was played on 2026-11-10.'))

    def test_different_fixtures_can_share_the_same_editorial_template(self):
        common = ' '.join(f'context{index}' for index in range(40))
        self.history.claim('Arsenal vs Chelsea Premier League 2026-11-09',common+' Arsenal Chelsea','youtube')
        self.assertFalse(self.history.is_duplicate('Liverpool vs Everton Premier League 2026-11-09',common+' Liverpool Everton'))

    def test_remote_conflict_preserves_the_other_workflows_claim(self):
        self.history.remote = True
        first = {'entries':{},'legacy_hashes':[]}
        second = {'entries':{'another':{**signature('A trophy design history','Different content.'),'kind':'video','channels':{}}},'legacy_hashes':[]}
        conflict = Mock(status_code=409)
        success = Mock(status_code=200,ok=True)
        with patch.object(self.history,'_ensure_branch'), \
             patch.object(self.history,'_read',side_effect=[(copy.deepcopy(first),'sha-1'),(copy.deepcopy(second),'sha-2')]), \
             patch('footybitez.content.history.requests.put',side_effect=[conflict,success]) as put:
            self.history.claim('How a stadium was built','A new stadium opened beside the river.','youtube')
        payload = put.call_args.kwargs['json']
        saved = json.loads(base64.b64decode(payload['content']))
        self.assertIn('another',saved['entries'])
        self.assertEqual(payload['sha'],'sha-2')
        self.assertEqual(len(saved['entries']),2)

    def test_topic_generator_does_not_recycle_an_exhausted_pool(self):
        from footybitez.content.topic_generator import TopicGenerator
        generator = TopicGenerator.__new__(TopicGenerator)
        generator.categories = {'Stories':['Already used']}
        generator.all_topics = ['Already used']
        generator._load_used_topics = lambda: {'already used'}
        with patch('footybitez.content.history.ContentHistory'):
            with self.assertRaisesRegex(ValueError,'All configured topics have been used'):
                generator.get_random_topic('Stories')


if __name__=='__main__':
    unittest.main()
