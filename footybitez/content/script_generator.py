import os
import time
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

class ScriptGenerator:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. AI generation might fail if Groq also missing.")
        else:
            genai.configure(api_key=self.api_key)
            
        self.models = ["gemini-pro", "gemini-1.5-flash"]

    def generate_script(self, topic):
        """
        Generates a short video script using Groq (Priority), Gemini, or Wikipedia (Fallback).
        """
        # 1. Try Groq (User preferred for facts)
        if self.groq_api_key:
            try:
                from groq import Groq
                client = Groq(api_key=self.groq_api_key)
                logger.info("Generating script with Groq (Llama3)...")
                
                prompt = self._get_prompt(topic)
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1024,
                    response_format={"type": "json_object"}
                )
                text = completion.choices[0].message.content
                data = json.loads(text)
                if self._validate_script_data(data):
                    logger.info("Groq generation successful.")
                    return data
            except Exception as e:
                logger.error(f"Groq generation failed: {e}")

        # 2. Try Gemini
        if self.api_key:
            logger.info("Generating script with Gemini...")
            prompt = self._get_prompt(topic)
            for attempt, model_name in enumerate(self.models):
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    text = response.text.strip()
                    if text.startswith('```json'): text = text[7:]
                    if text.endswith('```'): text = text[:-3]
                    
                    try:
                        data = json.loads(text.strip())
                        if self._validate_script_data(data):
                            logger.info(f"Gemini generation successful ({model_name}).")
                            return data
                    except: continue
                except Exception as e:
                    logger.error(f"Gemini model {model_name} failed: {e}")
                    time.sleep(1)

        # 3. Fallback: Wikipedia
        logger.warning("All AI models failed. Converting to Wikipedia Mode.")
        return self._get_wikipedia_script(topic)

    def _get_prompt(self, topic):
        return f"""
        create a viral YouTube Short script about: "{topic}".
        Style: High energy, "Did you know?" style.
        
        CRITICAL OUTPUT FORMAT:
        You MUST return valid JSON.
        The JSON structure must be:
        {{
            "hook": "The first 3 seconds hook text (max 10 words)",
            "segments": [
                {{ "text": "Sentence 1 (Fact part 1)...", "visual_keyword": "messi face" }},
                {{ "text": "Sentence 2 (Fact part 2)...", "visual_keyword": "camp nou stadium" }}
            ],
            "outro": "Call to action text"
        }}

        CONTENT RULES:
        1. "hook": Must be shocking/intriguing.
        2. "segments": The main fact split into 2-3 short, punchy sentences.
        3. "visual_keyword": A specific search term (e.g. "Messi lifting trophy", "Real Madrid Stadium"). ALWAYS include the word "football" or "soccer" in keywords.
        4. HIGHLIGHTING: You MUST enclose *Key Entities* (Names, Clubs, Numbers) in asterisks. Example: "*Messi* won *7* Ballon d'Ors." This is critical.
        """

    def _validate_script_data(self, data):
        if "hook" in data and "segments" in data:
            # Normalize list of strings to list of dicts if needed
            new_segments = []
            for s in data["segments"]:
                if isinstance(s, str):
                    new_segments.append({"text": s, "visual_keyword": "football"})
                else:
                    new_segments.append(s)
            data["segments"] = new_segments
            
            full_text = f"{data['hook']} {' '.join([s['text'] for s in data['segments']])} {data.get('outro', '')}"
            data['full_text'] = full_text.replace('*', '') 
            return True
        return False

    def _get_wikipedia_script(self, topic):
        """Fetches a summary from Wikipedia and structures it as a script."""
        try:
            import wikipedia
            # wikipedia.set_lang("en") # Default
            search_res = wikipedia.search(topic, results=1)
            if not search_res: raise Exception("No wikipedia results")
            
            page = wikipedia.page(search_res[0], auto_suggest=False)
            # Use 'summary' but limit sentences
            sentences = page.summary.split('. ')
            
            # Smart Selection: First sentence (Intro) + 2 most interesting (heuristic: contains numbers or 'first')
            final_segments = []
            
            # Hook
            hook = f"Did you know this about *{page.title}*?"
            
            # Body (Max 3 sentences to keep it short as requested)
            count = 0
            for s in sentences:
                if len(s) < 20: continue # skip too short
                clean_s = s.strip()
                if not clean_s.endswith('.'): clean_s += '.'
                
                # Highlighting: Highlight the Topic or Numbers
                words = clean_s.split()
                highlighted_s = []
                for w in words:
                    if w.isdigit() or page.title.split()[0] in w:
                        highlighted_s.append(f"*{w}*")
                    else:
                        highlighted_s.append(w)
                
                final_segments.append({
                    "text": " ".join(highlighted_s),
                    "visual_keyword": f"{page.title} football context"
                })
                count += 1
                if count >= 3: break
            
            return {
                "hook": hook,
                "segments": final_segments,
                "outro": "Subscribe for more verified facts!",
                "full_text": f"{hook} {' '.join([s['text'] for s in final_segments])}"
            }
            
        except Exception as e:
            logger.error(f"Wikipedia fallback failed: {e}")
            return {
                "hook": f"Here is a crazy fact about *{topic}*!",
                "segments": [
                    { "text": f"*{topic}* is a true legend of football.", "visual_keyword": f"{topic} player" },
                    { "text": "Their story inspires millions around the globe.", "visual_keyword": "football stadium crowd" }
                ],
                "outro": "Comment below!",
                "full_text": f"Here is a crazy fact about {topic}!"
            }

if __name__ == "__main__":
    # Test
    try:
        generator = ScriptGenerator()
        script = generator.generate_script("Lionel Messi")
        print(script)
    except Exception as e:
        print(f"Setup failed: {e}")
