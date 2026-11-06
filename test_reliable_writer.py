import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from footybitez.content.short_writer import ShortWriter, evidence_catalog, prepare_script, script_schema
from footybitez.content.quality import visual_query_errors
from test_content_quality import good_script


def fixture():
    data = good_script()
    data.update(title='Why the back-pass rule matters', music_mood='neutral', primary_entity='')
    context = ' '.join(segment['text'] for segment in data['segments'])
    records, context = evidence_catalog(context)
    for segment in data['segments']:
        segment['evidence_ids'] = ['S1']
    return data, records, context


class ReliableWriterTests(unittest.TestCase):
    def test_application_attaches_original_source_text(self):
        data, records, context = fixture()
        output, errors = prepare_script(data, records, context)
        self.assertFalse(errors)
        self.assertEqual(output['segments'][0]['source_quote'], records[0]['text'])
        self.assertNotIn('source_quote', data['segments'][0])

    def test_unknown_source_id_is_not_silently_replaced(self):
        data, records, context = fixture()
        data['segments'][0]['evidence_ids'] = ['S999']
        output, errors = prepare_script(data, records, context)
        self.assertIsNone(output)
        self.assertTrue(errors)

    def test_exact_quote_copying_is_not_in_provider_schema(self):
        schema = script_schema(['S1', 'S2'])
        self.assertEqual(schema['type'], 'object')
        segment = schema['properties']['segments']['items']
        self.assertEqual(segment['properties']['evidence_ids']['items']['enum'], ['S1', 'S2'])
        self.assertNotIn('source_quote', segment['properties'])
        self.assertFalse(segment['additionalProperties'])

    def test_title_case_diagram_is_not_a_named_player(self):
        self.assertFalse(visual_query_errors('Offside Rule Tactical Diagram', 'The offside rule discourages goal hanging.', 'The offside rule discourages goal hanging.'))

    def test_bad_query_is_repaired_without_discarding_good_narration(self):
        data, records, context = fixture()
        data['segments'][0]['visual_keyword'] = 'Lionel Messi Paris Saint-Germain 2026 shirt'
        output, errors = prepare_script(data, records, context)
        self.assertFalse(errors)
        self.assertIsNotNone(output)
        self.assertNotIn('2026', output['segments'][0]['visual_keyword'])
        self.assertNotIn('Messi', output['segments'][0]['visual_keyword'])
        self.assertEqual(output['segments'][0]['text'], data['segments'][0]['text'])

    def test_unsupported_narration_date_still_rejected(self):
        data, records, context = fixture()
        data['segments'][0]['text'] += ' This happened in 2026.'
        output, errors = prepare_script(data, records, context)
        self.assertIsNone(output)
        self.assertTrue(any('numbers/dates' in error for error in errors))

    def test_short_or_missing_visual_metadata_is_repaired_before_validation(self):
        for query in ('Manchester United', 'comeback', '', None, []):
            with self.subTest(query=query):
                data, records, context = fixture()
                data['segments'][0]['visual_keyword'] = query
                output, errors = prepare_script(data, records, context)
                self.assertFalse(errors)
                self.assertEqual(output['segments'][0]['text'], data['segments'][0]['text'])
                self.assertGreaterEqual(len(output['segments'][0]['visual_keyword'].split()),3)
                self.assertFalse(visual_query_errors(output['segments'][0]['visual_keyword'],data['segments'][0]['text'],context))

    def test_caption_with_short_visual_queries_does_not_consume_provider_retries(self):
        data, records, context = fixture()
        for segment in data['segments']:
            segment['visual_keyword'] = 'football'
        writer = ShortWriter(['not-a-key'], ['unused-gemini-key'])
        with patch.object(writer, '_request', return_value=json.dumps(data)) as request:
            result = writer.write('Back-pass rule', 'matches', context, lambda data, **kwargs: True)
        self.assertIsNotNone(result)
        self.assertEqual(request.call_count,1)

    def test_visual_repair_never_hides_unsupported_facts_or_malformed_narration(self):
        data, records, context = fixture()
        data['segments'][0].update(text=data['segments'][0]['text']+' This happened in 2026.',visual_keyword='')
        output, errors = prepare_script(data, records, context)
        self.assertIsNone(output)
        self.assertTrue(any('numbers/dates' in error for error in errors))
        data['segments'][0]['text'] = None
        output, errors = prepare_script(data, records, context)
        self.assertIsNone(output)
        self.assertIn('Every segment needs narration text',errors)

    def test_malformed_candidate_is_repaired_with_feedback(self):
        data, records, context = fixture()
        writer = ShortWriter(['not-a-key'], [])
        with patch.object(writer, '_request', side_effect=[json.dumps([data]), json.dumps(data)]) as request:
            result = writer.write('The back-pass rule', 'Rules', context, lambda data, **kwargs: True)
        self.assertIsNotNone(result)
        self.assertEqual(request.call_count, 2)
        self.assertIn('not an array', request.call_args.args[3])
        self.assertIn('Previous candidate', request.call_args.args[3])

    def test_rate_limited_model_is_skipped_on_next_topic(self):
        data, records, context = fixture()
        writer = ShortWriter(['not-a-key'], [])
        with patch.object(writer, '_request', side_effect=RuntimeError('429 rate limited')) as request:
            self.assertIsNone(writer.write('Rules', 'Rules', context, lambda **kwargs: True))
            self.assertIsNone(writer.write('Rules again', 'Rules', context, lambda **kwargs: True))
        self.assertEqual(request.call_count, 1)

    def test_groq_uses_strict_schema_without_hidden_sdk_retries(self):
        data, records, context = fixture()
        client = MagicMock()
        client.__enter__.return_value = client
        client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(data)))])
        factory = MagicMock(return_value=client)
        with patch.dict('sys.modules', {'groq': SimpleNamespace(Groq=factory)}):
            result = ShortWriter([], [])._request('groq', 'not-a-key', 'openai/gpt-oss-120b', 'Write JSON', script_schema(['S1']))
        self.assertEqual(factory.call_args.kwargs['max_retries'], 0)
        args = client.chat.completions.create.call_args.kwargs
        self.assertEqual(args['response_format']['type'], 'json_schema')
        self.assertTrue(args['response_format']['json_schema']['strict'])
        self.assertEqual(args['reasoning_effort'], 'low')
        self.assertEqual(json.loads(result)['title'], data['title'])

    def test_full_generator_accepts_evidence_ids_and_title_case_visuals(self):
        from footybitez.content.script_generator import ScriptGenerator
        data, records, context = fixture()
        data['segments'][0]['visual_keyword'] = 'Football Rule Tactical Diagram'
        generator = ScriptGenerator()
        generator._short_writer = ShortWriter(['not-a-key'], [])
        with patch.object(generator._short_writer, '_request', return_value=json.dumps(data)) as request:
            output = generator.generate_script('The back-pass rule', 'Football Explained Simply', context=context)
        self.assertIsNotNone(output)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(output['segments'][0]['source_quote'], records[0]['text'])
        self.assertIn('exactly one JSON object', request.call_args.args[3])
        self.assertNotIn('ALWAYS include the FULL name', request.call_args.args[3])

    def test_json_match_context_can_be_cited(self):
        records, context = evidence_catalog(json.dumps({'home': 'Tunisia', 'away': 'Japan', 'form_a': 'W D W L W', 'prob_a': 45.0}, separators=(',', ':')))
        self.assertTrue(records)
        self.assertIn('45.0', records[0]['text'])
        self.assertIn(records[0]['text'], context)

if __name__ == '__main__':
    unittest.main()
