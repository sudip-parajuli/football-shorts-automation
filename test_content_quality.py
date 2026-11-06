import copy
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from footybitez.content.quality import contains_term, short_errors, documentary_errors
from footybitez.content.script_generator import ScriptGenerator
from footybitez.video.preflight import inspect_video


def good_script():
    return {'hook': 'Why can a teammate cost the goalkeeper a free kick?', 'segments': [
        {'text': 'A goalkeeper cannot handle a ball deliberately kicked to them by a teammate. The restriction targets the deliberate kick rather than every pass that travels backwards.', 'visual_keyword': 'goalkeeper teammate deliberate back pass soccer'},
        {'text': 'A headed pass is treated differently. That distinction matters because the law describes how the teammate played the ball, rather than simply where the goalkeeper receives it.', 'visual_keyword': 'soccer goalkeeper headed teammate pass'},
        {'text': 'So watch the action before the catch. The key question is whether the teammate deliberately kicked the ball to the keeper, not whether the ball moved backwards.', 'visual_keyword': 'goalkeeper catching ball penalty area soccer'}], 'outro': 'Would you spot the difference during a match?'}


class QualityTests(unittest.TestCase):
    def test_word_boundaries(self):
        for word in ('teammate', 'summary', 'command', 'performance'):
            self.assertFalse(contains_term(word, 'mma'))
        self.assertTrue(contains_term('An MMA fight', 'mma'))
        self.assertTrue(contains_term('American football match', 'american football'))

    def test_good_script_and_canonical_transcript(self):
        data = good_script()
        data['full_text'] = 'stale hook only'
        self.assertFalse(short_errors(data))
        self.assertIn(data['segments'][2]['text'], data['full_text'])
        self.assertTrue(ScriptGenerator()._validate_script_data(data))

    def test_placeholder_and_malformed_rejected(self):
        for data in (None, [], {}, {'hook': 12, 'segments': [None, {}]},
                     {'hook': 'Here is a crazy fact about football', 'segments': [{'text': 'A true legend'}]}):
            self.assertTrue(short_errors(data))
            self.assertFalse(ScriptGenerator()._validate_script_data(data))
        data = good_script()
        data['segments'][1]['text'] = 'Their story inspires millions around the globe and creates a legacy of football.'
        self.assertTrue(short_errors(data))

    def test_provider_exhaustion_skips(self):
        gen = ScriptGenerator()
        gen.gemini_keys = []
        gen.groq_keys = []
        gen.anthropic_api_key = None
        self.assertIsNone(gen.generate_script('Back pass rule', context='Law 12 supplied research'))

    def test_no_research_skips(self):
        self.assertIsNone(ScriptGenerator().generate_script('Back pass rule', context='__NO_CONTEXT__'))

    def test_counterfactual_requires_historical_research(self):
        generator = ScriptGenerator()
        self.assertIsNone(generator.generate_script('What if VAR existed in 1990?', category='What If?', context='__NO_CONTEXT__'))

    def test_documentary_missing_and_misordered_snippets(self):
        self.assertTrue(documentary_errors({}))
        chapter = {'script': ' '.join(['A concrete football explanation.'] * 60), 'visual_scenes': [{'narration_snippet': 'Invented sentence'}] * 6}
        self.assertTrue(documentary_errors({'title': 'Football', 'chapters': [copy.deepcopy(chapter) for _ in range(3)]}))

    @patch('footybitez.video.preflight.subprocess.run')
    def test_missing_audio_blocks_upload(self, run):
        run.return_value = SimpleNamespace(stdout=json.dumps({'format': {'duration': '30'}, 'streams': [{'codec_type': 'video'}]}))
        with self.assertRaisesRegex(ValueError, 'no audio'):
            inspect_video('video.mp4')

    @patch('footybitez.video.preflight.subprocess.run')
    def test_silent_mix_blocks_upload(self, run):
        run.side_effect = [SimpleNamespace(stdout=json.dumps({'format': {'duration': '30'}, 'streams': [{'codec_type': 'video'}, {'codec_type': 'audio'}]})), SimpleNamespace(stderr='mean_volume: -inf dB')]
        with self.assertRaisesRegex(ValueError, 'silent'):
            inspect_video('video.mp4')

class MusicTests(unittest.TestCase):
    def test_manifest_mood_rights_and_path(self):
        import tempfile
        from pathlib import Path
        from footybitez.media.music_selector import select_music
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(select_music("tense", directory))
            (root / 'track.mp3').write_bytes(b'audio')
            (root / 'manifest.json').write_text(json.dumps([{'file': 'track.mp3', 'moods': ['tense'], 'rights_confirmed': False}]))
            self.assertIsNone(select_music("tense", directory))
            (root / 'manifest.json').write_text(json.dumps([{'file': 'track.mp3', 'moods': ['tense'], 'rights_confirmed': True}]))
            self.assertEqual(select_music("tense", directory), str((root / 'track.mp3').resolve()))
            self.assertIsNone(select_music("reflective", directory))


class TimelineTests(unittest.TestCase):
    def test_pauses_and_rounding_preserve_coverage(self):
        from footybitez.video.scene_timing import align_scenes_with_voice_timings
        scenes = [{'narration_snippet': 'First sentence'}, {'narration_snippet': 'Second sentence'}]
        words = [{'word': 'First', 'start': 0, 'duration': .2}, {'word': 'sentence', 'start': .3, 'duration': .2},
                 {'word': 'Second', 'start': 2, 'duration': .2}, {'word': 'sentence', 'start': 2.3, 'duration': .2}]
        align_scenes_with_voice_timings(scenes, words, 72)
        self.assertEqual([scene['duration_frames'] for scene in scenes], [48, 24])

    def test_proportional_fallback_preserves_total(self):
        from footybitez.video.scene_timing import assign_scene_durations
        for count in (2, 6, 12, 20):
            scenes = [{'narration_snippet': 'word ' * (index + 1)} for index in range(count)]
            assign_scene_durations(scenes, 107)
            self.assertEqual(sum(scene['duration_frames'] for scene in scenes), 107)
            self.assertTrue(all(scene['duration_frames'] > 0 for scene in scenes))

if __name__ == '__main__':
    unittest.main()
