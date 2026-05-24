import os
import re
import json
import time
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

    @staticmethod
    def _parse_retry_delay(error_str: str, default: float = 10.0) -> float:
        """Extract retry delay seconds from a Gemini 429 error message."""
        match = re.search(r"retry[\w\s]*?in\s+(\d+(?:\.\d+)?)s", str(error_str), re.IGNORECASE)
        if match:
            return min(float(match.group(1)), 120.0)  # cap at 2 minutes
        return default

    def _try_gemini(self, system_prompt: str, user_prompt: str) -> dict | None:
        """Try all Gemini keys in order using new google-genai SDK.
        On 429, waits the suggested retry-after delay and retries once per key.
        """
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            logger.error("google-genai not installed. Run: pip install google-genai>=1.0.0")
            return None

        for i, key in enumerate(self.gemini_keys):
            for attempt in range(2):  # 2 attempts per key (initial + 1 retry after 429)
                try:
                    logger.info(f"Attempting script generation with Gemini key #{i+1} (attempt {attempt+1})...")
                    client = genai.Client(api_key=key)
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
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
                    err_str = str(e)
                    if "429" in err_str and attempt == 0:
                        delay = self._parse_retry_delay(err_str)
                        logger.warning(f"Gemini key #{i+1} hit 429. Waiting {delay:.0f}s before retry...")
                        time.sleep(delay)
                        continue  # retry same key
                    logger.warning(f"Gemini key #{i+1} failed: {e}")
                    break  # move to next key
        return None

    # Ordered model fallback chain for Groq
    GROQ_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
    ]

    def _try_groq(self, system_prompt: str, user_prompt: str) -> dict | None:
        """Try all Groq keys × model fallback chain.
        400 Bad Request on one model automatically tries the next model.
        """
        from groq import Groq

        # Groq json_object mode requires the word "json" in the messages.
        # Append a reminder to the user prompt to be safe.
        groq_user_prompt = user_prompt + "\n\nRespond ONLY with valid JSON matching the schema above."

        for i, key in enumerate(self.groq_keys):
            client = Groq(api_key=key)

            for model in self.GROQ_MODELS:
                logger.info(f"Groq key #{i+1} — trying model '{model}'...")
                temperatures = [0.7, 0.3, 0.1]
                for attempt, temp in enumerate(temperatures):
                    try:
                        logger.info(f"  Attempt {attempt+1}/3 (temp={temp})...")
                        completion = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user",   "content": groq_user_prompt}
                            ],
                            response_format={"type": "json_object"},
                            temperature=temp,
                            max_tokens=4096,
                        )
                        content = completion.choices[0].message.content
                        return json.loads(content)
                    except json.JSONDecodeError as jde:
                        logger.warning(f"  JSON decode error: {jde}. Retrying with lower temp...")
                    except Exception as e:
                        err_msg = str(e)
                        if "json_validate_failed" in err_msg or "Failed to generate JSON" in err_msg:
                            logger.warning(f"  Schema validation failed: {e}. Retrying with lower temp...")
                        elif "400" in err_msg or "Bad Request" in err_msg:
                            # 400 means this model rejected the request — try next model
                            logger.warning(f"  Model '{model}' returned 400. Falling back to next model...")
                            break  # break temperature loop → next model
                        elif "429" in err_msg:
                            delay = self._parse_retry_delay(err_msg, default=30.0)
                            logger.warning(f"  Groq key #{i+1} rate limited. Waiting {delay:.0f}s...")
                            time.sleep(delay)
                            break  # break temperature loop → next key
                        else:
                            logger.warning(f"  Groq key #{i+1} / model '{model}' error: {e}. Trying next key...")
                            break  # break temperature loop → next key
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
7. THUMBNAIL HOOK: The "hook_phrase" in thumbnail_data MUST be exactly 2-4 words. Never use the full video title. Make it punchy and intriguing.

VISUAL TYPE CLASSIFICATION — for each chapter also output "visual_scenes" array:
Each scene in visual_scenes must have:
  - "visual_type": one of "typewriter_text" | "kinetic_stat" | "image" | "ai_image" | "ai_video" | "hook_question" | "data_bars"
  - "image_cue": specific search query (for image types)
  - "ai_image_prompt": specific prompt for generating AI image (ONLY for ai_image type)
  - "ai_video_prompt": "[camera move], [subject], [atmosphere], [style]" (ONLY for ai_video type)
  - "narration_snippet": which sentence(s) of the chapter script this scene covers
  - "transition": "flash" | "fade" | "cut" (default is "cut")

Type-specific fields:
  - typewriter_text: include "typewriter_words" array (each with "word" and "weight": "xl_accent" | "xl_amber" | "lg" | "md" | "dim")
  - kinetic_stat: include "stat_data" object with "value", "unit", "label"
  - hook_question: include "question_text" and "emphasis_phrase" (words to highlight)
  - data_bars: include "bar_data" array (each with "label", "value", and "color": "amber" | "teal" | "purple" | "gray")
  - image / ai_image / ai_video: optional "named_entities" list (each with "name", "description"), "ken_burns_style" ("zoom_in_center", "zoom_in_topleft", "pan_left", "pan_right"), "caption"

CRITICAL FACE RULE:
Never output visual_type='ai_image' or visual_type='ai_video' for scenes where a named, real player or coach is the main subject. AI models cannot generate recognizable faces of real people — they produce hallucinated, wrong, or generic faces.

If a scene describes a named player (e.g., "Messi scoring"), classify it as:
  visual_type: "image"
  image_cue: "Messi Ligue 1 goal 2023"

Only use ai_image/ai_video for:
  - Abstract concepts (speed, passion, tactics, formations)
  - Atmospheric scenes (stadium crowds, team celebrations without faces)
  - Tactical diagrams and formations
  - Generic actions (a goalkeeper diving, a midfielder passing, soccer ball close-up)

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
          "visual_type": "hook_question",
          "question_text": "But was it really that simple?",
          "emphasis_phrase": "really that simple?",
          "narration_snippet": "But was it really that simple?",
          "transition": "flash"
        },
        {
          "visual_type": "image",
          "image_cue": "specific search query",
          "ken_burns_style": "zoom_in_center",
          "narration_snippet": "first sentence of this chapter",
          "transition": "cut"
        },
        {
          "visual_type": "ai_video",
          "ai_video_prompt": "Slow aerial drone pull-back over packed stadium, cinematic",
          "narration_snippet": "crowd erupted as the final whistle blew",
          "transition": "fade"
        },
        {
          "visual_type": "kinetic_stat",
          "stat_data": {"value": 91, "unit": "GOALS", "label": "IN 2012"},
          "narration_snippet": "he scored 91 goals that calendar year",
          "transition": "flash"
        }
      ]
    }
  ],
  "thumbnail_data": {
    "hook_phrase": "THE TIKI-TAKA REVOLUTION",
    "supporting_fact": "POSSESSION-BASED DOMINATION",
    "background_query": "Barcelona football tiki-taka passing",
    "background_type": "real_image",
    "diagram_query": "tiki-taka formation passing lanes diagram",
    "diagram_type": "ai_generated",
    "composite": true
  },
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
