import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from footybitez.content.script_generator import ScriptGenerator
from footybitez.content.long_form_script_generator import LongFormScriptGenerator

class TestKeyRotation(unittest.TestCase):

    @patch.dict(os.environ, {
        "GROQ_API_KEY": "groq_key_1",
        "GROQ_API_KEY2": "groq_key_2",
        "GROQ_API_KEY3": "groq_key_3",
        "GEMINI_API_KEY": "",
        "GEMINI_API_KEY2": "",
        "GEMINI_API_KEY3": ""
    })
    @patch("groq.Groq")
    def test_groq_key_rotation_in_script_generator(self, mock_groq_class):
        # We have three groq keys configured.
        # Mock key 1 to raise an exception.
        # Mock key 2 to succeed and return a valid script.
        
        mock_client_1 = MagicMock()
        mock_client_1.chat.completions.create.side_effect = Exception("Rate limit reached on Key 1")

        mock_client_2 = MagicMock()
        mock_completion = MagicMock()
        valid_script = {
            "hook": "Test hook",
            "primary_entity": "Test Entity",
            "segments": [
                {"text": "Segment 1 text", "visual_keyword": "soccer match action"},
                {"text": "Segment 2 text", "visual_keyword": "soccer match action"},
                {"text": "Segment 3 text", "visual_keyword": "soccer match action"},
                {"text": "Segment 4 text", "visual_keyword": "soccer match action"}
            ],
            "outro": "Test outro",
            "full_text": "Test hook Segment 1 text Segment 2 text Segment 3 text Segment 4 text Test outro"
        }
        mock_completion.choices[0].message.content = json.dumps(valid_script)
        mock_client_2.chat.completions.create.return_value = mock_completion

        # The mock class should yield mock_client_1 on first call, mock_client_2 on second call
        mock_groq_class.side_effect = [mock_client_1, mock_client_2]

        generator = ScriptGenerator()
        self.assertEqual(len(generator.groq_keys), 3)

        # Call script generation
        result = generator.generate_script(
            topic="Test Topic",
            category="wc_pre_match",
            context=json.dumps({"test": "context"})
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["hook"], "Test hook")
        # Ensure Groq was initialized twice (first failed, second succeeded)
        self.assertEqual(mock_groq_class.call_count, 2)
        mock_groq_class.assert_any_call(api_key="groq_key_1")
        mock_groq_class.assert_any_call(api_key="groq_key_2")

    @patch.dict(os.environ, {
        "GEMINI_API_KEY": "gemini_key_1",
        "GEMINI_API_KEY2": "gemini_key_2",
        "GEMINI_API_KEY3": "gemini_key_3",
        "GROQ_API_KEY": "",
        "GROQ_API_KEY2": "",
        "GROQ_API_KEY3": ""
    })
    @patch("google.generativeai.GenerativeModel")
    @patch("google.generativeai.configure")
    def test_gemini_key_rotation_in_long_form_script_generator(self, mock_configure, mock_model_class):
        # Mock first key failing on all models, second key succeeding
        # In LongFormScriptGenerator:
        # loop keys:
        #   loop models:
        #     try api_key, model
        
        # We will mock the GenerativeModel instances:
        # For gemini_key_1 (first key):
        #   flash, pro, flash -> all raise Exception
        # For gemini_key_2 (second key):
        #   flash -> succeeds
        
        mock_model_fail = MagicMock()
        mock_model_fail.generate_content.side_effect = Exception("Quota exceeded on Key 1")

        mock_model_success = MagicMock()
        valid_long_script = {
            "hook": "Long hook",
            "intro": "Intro",
            "chapters": [
                {"text": "Text 1", "visual_keyword": "football match"}
            ],
            "outro": "Conclusion",
            "metadata": {"some_key": "some_value"}
        }
        mock_response = MagicMock()
        mock_response.text = json.dumps(valid_long_script)
        mock_model_success.generate_content.return_value = mock_response

        # mock_model_class side effect:
        # For key #1: we have models ["models/gemini-2.5-flash", "models/gemini-2.5-pro", "models/gemini-2.0-flash"]
        # So we expect 3 calls for key 1. All of them fail.
        # Then for key #2, the first model ("models/gemini-2.5-flash") succeeds.
        mock_model_class.side_effect = [
            mock_model_fail, # key 1, flash
            mock_model_fail, # key 1, pro
            mock_model_fail, # key 1, flash20
            mock_model_success # key 2, flash (success!)
        ]

        generator = LongFormScriptGenerator()
        self.assertEqual(len(generator.gemini_keys), 3)

        result = generator._generate_compilation_script("Test Prompt")

        self.assertIsNotNone(result)
        self.assertEqual(result["hook"], "Long hook")
        
        # Verify configure was called with different keys
        # Call 1, 2, 3: gemini_key_1
        # Call 4: gemini_key_2
        self.assertEqual(mock_configure.call_count, 4)
        mock_configure.assert_any_call(api_key="gemini_key_1")
        mock_configure.assert_any_call(api_key="gemini_key_2")


if __name__ == "__main__":
    unittest.main()
