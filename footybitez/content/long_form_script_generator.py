import os
import json
import logging
import random
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

class LongFormScriptGenerator:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            
        self.models = ["models/gemini-1.5-flash", "models/gemini-1.5-pro"]

    def generate_long_script(self, topic, method="compilation"):
        """
        Generates a long-form video script.
        topic: e.g., "Lionel Messi", "Real Madrid", "Football Facts"
        """
        if method == "compilation":
            return self._generate_compilation_script(topic)
        else:
            # Fallback to compilation for now
            return self._generate_compilation_script(topic)

    def _generate_compilation_script(self, topic):
        """
        Method 1: Combine documentary narration into 3-5 distinct chapters.
        """
        prompt = f"""
        Create a detailed LONG-FORM cinematic YouTube documentary script about: "{topic}".
        Format: Horizontal (16:9).
        Style: Emotional, Conversational, Documentary/Netflix-style. Avoid robotic facts.

        STRUCTURE & WRITING RULES (CRITICAL):
        1. COLD HOOK (4-6s): A mystery hook. NEVER mention the exact player/club name. Build curiosity.
           e.g., "[dramatic] A football record... no one can touch."
        2. INTRO: A strong 8-12 second explanation matching the hook.
        3. CHAPTERS (3-5 max): Group the story logically.
           - Every chapter MUST have a "chapter_title" (e.g., "The Impossible Tournament").
           - Tell a mini-story with 4-7 facts.
           - MUST provide a "transition" sentence at the end linking to the next chapter.
        4. OUTRO: A 10-15 second soft, somber or dramatic conclusion.

        EMOTION TAGS & TEXT:
        - "narration": The EXACT spoken text. MUST include emotion tags inside brackets at the start of sentences.
          Allowable tags: [dramatic], [curious], [serious], [excited], [somber].
          Use short dramatic pauses using commas and ellipses (...).
          AVOID: "This video will discuss...", "In this documentary...".
        - "screen_text": A SHORT, punchy phrase for the screen (e.g., "WORLD RECORD", "1958", "13 GOALS"). NEVER repeat the full narration.
        - "visual_keyword": A generic, highly descriptive search term (e.g., "dark football stadium").

        REQUIRED JSON FORMAT STRICTLY:
        {{
            "metadata": {{
                "title": "SEO Title",
                "description": "Emotional description",
                "tags": ["tag1", "tag2"]
            }},
            "hook": {{
                "narration": "[dramatic] This record... refuses to die.",
                "screen_text": "UNBREAKABLE",
                "visual_keyword": "dark football stadium"
            }},
            "intro": {{
                "narration": "[curious] In 1958, one man shocked the World Cup...",
                "screen_text": "THE GREATEST SECERT",
                "visual_keyword": "vintage world cup footage"
            }},
            "chapters": [
                {{
                    "chapter_title": "A Tournament of Fire",
                    "facts": [
                        {{
                            "narration": "[excited] In just six matches... he scored *13 goals*.",
                            "screen_text": "13 GOALS",
                            "visual_keyword": "1958 world cup match"
                        }}
                    ],
                    "transition": "But this miracle... had a dark ending."
                }}
            ],
            "outro": {{
                "narration": "[somber] Some records fall... but this one became immortal.",
                "screen_text": "IMMORTAL",
                "visual_keyword": "empty stadium sunset"
            }}
        }}

        RULES:
        - Total narration length should feel like 5-10 minutes.
        - HIGHLIGHTING: Enclose *Key Entities* in asterisks in the narration. Example: "*Messi* won *8* Ballon d'Ors."
        - Avoid copyrighted references. Avoid Wikipedia tone. Tell a dynamic story.
        """

        if self.groq_api_key:
            try:
                from groq import Groq
                client = Groq(api_key=self.groq_api_key)
                logger.info("Generating long-form script with Groq...")
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=4096,
                    response_format={"type": "json_object"}
                )
                data = json.loads(completion.choices[0].message.content)
                if self._validate_long_script(data):
                    return data
            except Exception as e:
                logger.error(f"Groq long-script generation failed: {e}")

        # Fallback to Gemini
        if self.api_key:
            for model_name in self.models:
                try:
                    logger.info(f"Trying Gemini ({model_name}) for long-form script...")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    text = response.text.strip()
                    if text.startswith('```json'): text = text[7:]
                    if text.endswith('```'): text = text[:-3]
                    data = json.loads(text.strip())
                    if self._validate_long_script(data):
                        return data
                except Exception as e:
                    logger.error(f"Gemini {model_name} failed for long-form: {e}")

        return None

    def _validate_long_script(self, data):
        required = ["hook", "intro", "chapters", "outro", "metadata"]
        return all(k in data for k in required)

if __name__ == "__main__":
    gen = LongFormScriptGenerator()
    script = gen.generate_long_script("Lionel Messi")
    print(json.dumps(script, indent=2))
