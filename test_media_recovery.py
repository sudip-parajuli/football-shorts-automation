import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
from footybitez.media.relevance import metadata_matches
from footybitez.media.editorial_cards import make_beat_cards
from footybitez.content.quality import grounding_errors
from footybitez.media.media_sourcer import MediaSourcer
from footybitez.utils.gemini_client import create_gemini_client


class RecoveryTests(unittest.TestCase):
    def test_json_client_uses_beta_endpoint(self):
        with patch('google.genai.Client') as client:
            create_gemini_client('not-a-real-key')
        self.assertEqual(client.call_args.kwargs['http_options'].api_version, 'v1beta')

    def test_reject_logged_irrelevant_commons_results(self):
        self.assertFalse(metadata_matches('Manchester United 2026 home kit launch soccer', 'File:Skylight in the abandoned City Hall Station.jpg', categories='Manchester United football'))
        self.assertFalse(metadata_matches('Lionel Messi Paris Saint-Germain 2026 home kit', 'File:Lionel Messi 2009.jpg'))
        self.assertFalse(metadata_matches('Juventus 2021 black away kit', 'File:1899 Foot-Ball Club Juventus.jpg'))
        self.assertTrue(metadata_matches('Manchester United 2026 home kit', 'File:Manchester United 2026 home kit launch.jpg'))

    def test_missing_or_nonboolean_vision_response_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidate.jpg'
            Image.new('RGB', (640, 640)).save(path)
            sourcer = MediaSourcer.__new__(MediaSourcer)
            sourcer.gemini_keys = ['not-a-key']
            sourcer._gemini_unusable = set()
            for data in ({}, {'is_nsfw': 'false', 'is_football_related': True, 'matches_context': True}):
                client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kwargs: SimpleNamespace(text=json.dumps(data))))
                with patch('footybitez.media.media_sourcer.create_gemini_client', return_value=client):
                    self.assertFalse(sourcer._check_image_safety_and_relevance(str(path), 'kit launch'))

    def test_permanent_error_not_retried_on_every_image(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidate.jpg'
            Image.new('RGB', (640, 640)).save(path)
            sourcer = MediaSourcer.__new__(MediaSourcer)
            sourcer.gemini_keys = ['not-a-key']
            sourcer._gemini_unusable = set()
            with patch('footybitez.media.media_sourcer.create_gemini_client', side_effect=RuntimeError('400 INVALID_ARGUMENT')) as client:
                self.assertFalse(sourcer._check_image_safety_and_relevance(str(path), 'kit launch'))
                self.assertFalse(sourcer._check_image_safety_and_relevance(str(path), 'kit launch'))
                self.assertEqual(client.call_count, 1)

    def test_editorial_graphics_work_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            for size in ((1080, 1920), (1920, 1080)):
                paths = make_beat_cards('Why kits change', 'Clubs release fresh designs and sell shirts to supporters. A new design offers another choice for fans who collect the shirts.', directory, size=size)
                self.assertGreater(len(paths), 1)
                for path in paths:
                    with Image.open(path) as graphic:
                        self.assertEqual(graphic.size, size)
                        self.assertEqual(graphic.mode, 'RGB')

    def test_match_card_text_drops_asterisks(self):
        from footybitez.media.card_generator import _draw_text
        from unittest.mock import Mock
        draw = Mock()
        _draw_text(draw, (10, 20), '**Juventus** vs *Milan*', fill='white')
        self.assertEqual(draw.text.call_args.args[1], 'Juventus vs Milan')

    def test_unsupported_juventus_date_and_messi_query_rejected(self):
        context = 'Clubs release fresh designs and sell shirts to supporters.'
        segment = {'text': 'Juventus changed the kit in 2021 after outrage.', 'source_quote': context, 'visual_keyword': 'Lionel Messi Paris Saint-Germain 2026 kit'}
        errors = grounding_errors({'segments': [segment]}, context)
        self.assertTrue(any('numbers/dates' in error for error in errors))
        self.assertTrue(any('visual query' in error for error in errors))
        segment.update(text='Clubs sell shirts to supporters.', visual_keyword='football shirt design launch')
        self.assertFalse(grounding_errors({'segments': [segment]}, context))

if __name__ == '__main__':
    unittest.main()
