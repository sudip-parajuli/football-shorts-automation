import os
import json
import logging
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
        """Try all Gemini keys in order using new google-genai SDK."""
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            logger.error("google-genai not installed. Run: pip install google-genai>=1.0.0")
            return None

        for i, key in enumerate(self.gemini_keys):
            try:
                logger.info(f"Attempting script generation with Gemini key #{i+1}...")
                client = genai.Client(api_key=key)
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=f"{system_prompt}\n\n{user_prompt}",
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7,
                        thinking_config=types.ThinkingConfig(thinking_budget=0)
                    )
                )
                text = response.text.strip()
                # Strip markdown code fences if present
                if text.startswith("```"):
                    text = text.split("\n", 1)[-1]
                if text.endswith("```"):
                    text = text.rsplit("```", 1)[0]
                return json.loads(text.strip())
            except Exception as e:
                logger.warning(f"Gemini key #{i+1} failed: {e}")
        return None

    def _try_groq(self, system_prompt: str, user_prompt: str) -> dict | None:
        """Try all Groq keys in order, return parsed JSON on first success."""
        for i, key in enumerate(self.groq_keys):
            try:
                logger.info(f"Attempting script generation with Groq key #{i+1}...")
                from groq import Groq
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
        Tries all Gemini keys first (new SDK), then all Groq keys.
        Includes visual_type classification for each scene to power the asset orchestrator.
        """
        system_prompt = """
You are a professional YouTube scriptwriter specializing in football documentary content.

STRICT RULES:
1. No generic intros/outros. Start with the hook.
2. image_queries MUST be VERY specific — always include the player's full name, the team, and the action
   (e.g. "Neymar Jr Barcelona skills 2015", "Ronaldinho dribbling Brazil 2006"). Never use generic queries.
3. Each chapter MUST have 4-6 image_queries — enough to fill the narration with changing visuals.
4. If a chapter compares two players, alternate queries between them (2-3 images per player).
5. Sentence rhythm: 2-3 long sentences followed by 1 short punchy sentence.
6. ACCURACY: Never invent transfer fees or contract values. Only state figures you are certain of.

VISUAL TYPE CLASSIFICATION — for each chapter also output "visual_scenes" array:
Each scene in visual_scenes must have:
  - "visual_type": one of "ai_video" | "image" | "kinetic_text" | "image_with_overlay"
  - "image_cue": specific search query (for image / image_with_overlay types)
  - "ai_video_prompt": "[camera move], [subject], [atmosphere], [style]" (ONLY for ai_video type)
  - "kinetic_stat": short text to display (for kinetic_text and image_with_overlay types)
  - "narration_snippet": which sentence(s) of the chapter script this scene covers

RULES for ai_video visual type (MAXIMUM 3 per entire video — enforce strictly):
  ✅ USE FOR: stadium atmospheres, crowd energy, abstract sport moods, rain/lighting/fog effects,
              generic pitch views with no identifiable players, slow-motion ball rolling
  ❌ NEVER USE FOR: named players, specific match moments, historical events, referees showing cards,
                    any scene involving real identifiable people or club-specific kits/badges

RULES for ai_video_prompt (only written when visual_type == "ai_video"):
  Format: "[camera move], [subject], [atmosphere/mood], [cinematic style]"
  Good examples:
    "Slow aerial drone pull-back over a packed 80,000-seat stadium at night, floodlights blazing, crowd a sea of color, cinematic"
    "Low-angle tracking shot of a football rolling across a wet pitch, floodlights reflected in puddles, dramatic atmosphere"
    "Wide shot of empty stadium at dusk, golden hour light across empty seats, melancholic mood, cinematic"
  Bad examples (will hallucinate badly — use image type instead):
    "Lionel Messi scoring against Real Madrid" — named player
    "The 1966 World Cup final at Wembley" — specific real event
    "Referee showing a red card to a player" — faces distort badly

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
        "SPECIFIC query 2",
        "SPECIFIC query 3",
        "SPECIFIC query 4",
        "SPECIFIC query 5",
        "SPECIFIC query 6"
      ],
      "visual_scenes": [
        {
          "visual_type": "image",
          "image_cue": "specific search query",
          "narration_snippet": "first sentence of this chapter"
        },
        {
          "visual_type": "ai_video",
          "ai_video_prompt": "Slow aerial drone pull-back over packed stadium, cinematic",
          "narration_snippet": "crowd erupted as the final whistle blew"
        },
        {
          "visual_type": "kinetic_text",
          "kinetic_stat": "91 GOALS IN 2012",
          "narration_snippet": "he scored 91 goals that calendar year"
        }
      ]
    }
  ],
  "thumbnail_prompt": "ultra detailed AI image prompt: cinematic YouTube thumbnail for a football documentary, [SPECIFIC DESCRIPTION], dramatic stadium background, photorealistic, 4K, professional sports broadcast quality, volumetric lighting",
  "thumbnail_query": "specific high-contrast fallback query for image search",
  "quiz": {
    "question": "string",
    "options": ["A", "B", "C"],
    "correct_answer_index": 0,
    "explanation": "short explanation"
  },
  "tags": ["tag1", "tag2"]
}
"""
        user_prompt = f"Topic: {topic}\nHook style: {hook_style}\nTone: {tone}\nTarget length: {length_words} words"

        result = self._try_gemini(system_prompt, user_prompt)
        if result:
            logger.info("Gemini documentary generation succeeded.")
            return result

        logger.warning("All Gemini keys exhausted. Trying Groq...")
        result = self._try_groq(system_prompt, user_prompt)
        if result:
            logger.info("Groq documentary generation succeeded.")
            return result

        logger.error("All API keys exhausted. Script generation failed.")
        return None
