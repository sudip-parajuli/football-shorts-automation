import os
import json
import logging
import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _get_keys(prefix: str) -> list:
    """Collect all non-empty env vars named PREFIX, PREFIX2, PREFIX3 …"""
    keys = []
    for suffix in ["", "2", "3"]:
        val = os.getenv(f"{prefix}{suffix}")
        if val:
            keys.append(val)
    return keys


class DocumentaryGenerator:
    def __init__(self):
        self.gemini_keys = _get_keys("GEMINI_API_KEY")
        self.groq_keys   = _get_keys("GROQ_API_KEY")

        if not self.gemini_keys and not self.groq_keys:
            raise ValueError("No GEMINI_API_KEY or GROQ_API_KEY found.")

        logger.info(f"Loaded {len(self.gemini_keys)} Gemini key(s) and {len(self.groq_keys)} Groq key(s).")

    def _try_gemini(self, system_prompt: str, user_prompt: str) -> dict | None:
        """Try all Gemini keys in order, return parsed JSON on first success."""
        for i, key in enumerate(self.gemini_keys):
            try:
                logger.info(f"Attempting script generation with Gemini key #{i+1}...")
                genai.configure(api_key=key)
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    generation_config={"response_mime_type": "application/json", "temperature": 0.7}
                )
                response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")
                return json.loads(response.text)
            except Exception as e:
                logger.warning(f"Gemini key #{i+1} failed: {e}")
        return None

    def _try_groq(self, system_prompt: str, user_prompt: str) -> dict | None:
        """Try all Groq keys in order, return parsed JSON on first success."""
        for i, key in enumerate(self.groq_keys):
            try:
                logger.info(f"Attempting script generation with Groq key #{i+1}...")
                client = Groq(api_key=key)
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7
                )
                return json.loads(completion.choices[0].message.content)
            except Exception as e:
                logger.warning(f"Groq key #{i+1} failed: {e}")
        return None

    def generate_script(self, topic, hook_style="verdict_first", tone="investigative", length_words=850):
        """
        Generates a professional football documentary script in JSON format.
        Tries all Gemini keys first, then all Groq keys.
        """
        system_prompt = """
You are a professional YouTube scriptwriter specializing in football documentary content.
STRICT RULES:
1. No generic intros/outros. Start with the hook.
2. image_queries MUST be VERY specific — always include the player's full name, the team, and the action (e.g. "Neymar Jr Barcelona skills 2015", "Ronaldinho dribbling Brazil 2006"). Never use generic queries.
3. Each chapter MUST have 4-6 image_queries — enough to fill the narration with changing visuals. Think like a video editor.
4. If a chapter is about comparing two players, alternate queries between them (2-3 images per player).
5. Sentence rhythm: 2-3 long followed by 1 short punchy sentence.

OUTPUT FORMAT (JSON):
{
  "title": "video title",
  "suggested_voice_index": 0,
  "chapters": [
    {
      "chapter_number": 1,
      "chapter_title": "string",
      "script": "narration text",
      "image_queries": [
        "SPECIFIC query 1 with player name + team + action",
        "SPECIFIC query 2 with player name + team + action",
        "SPECIFIC query 3 with player name + team + action",
        "SPECIFIC query 4 with player name + team + action",
        "SPECIFIC query 5 with player name + team + action",
        "SPECIFIC query 6 with player name + team + action"
      ]
    }
  ],
  "thumbnail_prompt": "ultra detailed AI image prompt: cinematic YouTube thumbnail for a football documentary, [SPECIFIC DESCRIPTION OF PLAYERS/SCENE], dramatic stadium background, photorealistic, 4K, professional sports broadcast quality, volumetric lighting",
  "thumbnail_query": "specific high-contrast fallback query",
  "quiz": {
    "question": "string",
    "options": ["A", "B", "C"],
    "correct_answer_index": 0,
    "explanation": "short explanation"
  },
  "tags": ["tag1", "tag2"]
}
"""
        user_prompt = f"Topic: {topic}\nHook: {hook_style}\nTone: {tone}\nLength: {length_words} words"

        result = self._try_gemini(system_prompt, user_prompt)
        if result:
            return result

        logger.warning("All Gemini keys exhausted. Trying Groq...")
        result = self._try_groq(system_prompt, user_prompt)
        if result:
            return result

        logger.error("All API keys exhausted. Script generation failed.")
        return None
