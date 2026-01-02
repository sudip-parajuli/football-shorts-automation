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
        Method 1: Combine 25-40 individual football facts grouped by theme.
        """
        prompt = f"""
        Create a detailed LONG-FORM YouTube documentary script about: "{topic}".
        Format: Horizontal (16:9).
        Style: Documentary, Clean, Minimal, Engaging.
        
        STRUCTURE:
        1. COLD HOOK: A 4-6 second mystery hook. 
           - MUST NOT mention Player Name or Club Name. 
           - Must imply curiosity or mystery. 
           - 1 sentence only. Max 8-10 words.
        2. INTRO: A strong 8-12 second explanation.
        3. BODY: 25 to 30 individual football facts related to "{topic}".
           - Group them into 3-5 distinct THEMES (e.g., Records, Early Life, Controversies, etc.).
           - Each fact should be a punchy sentence or two.
           - Provide a "chapter_title" for each theme.
        4. OUTRO: A 10-15 second soft call to action. 
           - Focus on "More untold stories" or similar soft continuation.

        CRITICAL OUTPUT FORMAT (JSON ONLY):
        {{
            "metadata": {{
                "title": "Long-form SEO Title here",
                "description": "500-800 character description here containing keywords.",
                "tags": ["tag1", "tag2", "tag3"]
            }},
            "hook": {{
                "text": "Hook text here (mystery building)",
                "visual_keyword": "mysterious football visual"
            }},
            "intro": {{
                "text": "Intro text here",
                "visual_keyword": "cinematic football stadium"
            }},
            "chapters": [
                {{
                    "chapter_title": "Theme Title",
                    "facts": [
                        {{ "text": "Fact 1 content...", "visual_keyword": "specific search term" }},
                        {{ "text": "Fact 2 content...", "visual_keyword": "specific search term" }}
                    ]
                }}
            ],
            "outro": {{
                "text": "Outro text here",
                "visual_keyword": "football closing shot"
            }}
        }}

        RULES:
        - Total duration must feel like 5-10 minutes (Narration speed: ~150 words per minute).
        - HIGHLIGHTING: Enclose *Key Entities* in asterisks. Example: "*Messi* won *8* Ballon d'Ors."
        - Avoid copyrighted references to specific broadcasters.
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
