import os
import json
import logging
import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

class DocumentaryGenerator:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        
        if not self.gemini_key and not self.groq_key:
            raise ValueError("Neither GEMINI_API_KEY nor GROQ_API_KEY found.")
        
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.gemini_model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config={"response_mime_type": "application/json", "temperature": 0.7}
            )
            
        if self.groq_key:
            self.groq_client = Groq(api_key=self.groq_key)

    def generate_script(self, topic, hook_style="verdict_first", tone="investigative", length_words=850):
        """
        Generates a professional football documentary script in JSON format.
        Tries Gemini first, falls back to Groq.
        """
        system_prompt = """
You are a professional YouTube scriptwriter specializing in football documentary content. 
STRICT RULES:
1. No generic intros/outros. Start with the hook.
2. Specific image queries per chapter that strictly follow the script narrative.
3. Sentence rhythm: 2-3 long followed by 1 short punchy sentence.

OUTPUT FORMAT (JSON):
{
  "title": "video title",
  "suggested_voice_index": 0, (Select 0 for deep/serious, 1 for energetic/storyteller, 2 for analytical)
  "chapters": [
    {
      "chapter_number": 1,
      "chapter_title": "string",
      "script": "narration text",
      "image_queries": ["specific search query 1 based on this chapter", "specific search query 2"]
    }
  ],
  "thumbnail_query": "specific high-contrast query",
  "tags": ["tag1", "tag2"]
}
"""
        user_prompt = f"Topic: {topic}\nHook: {hook_style}\nTone: {tone}\nLength: {length_words} words"

        # 1. Try Gemini
        if self.gemini_key:
            try:
                logger.info("Attempting script generation with Gemini...")
                response = self.gemini_model.generate_content(f"{system_prompt}\n\n{user_prompt}")
                return json.loads(response.text)
            except Exception as e:
                logger.warning(f"Gemini failed: {e}. Falling back to Groq...")

        # 2. Try Groq
        if self.groq_key:
            try:
                logger.info("Attempting script generation with Groq...")
                completion = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7
                )
                return json.loads(completion.choices[0].message.content)
            except Exception as e:
                logger.error(f"Groq also failed: {e}")
        
        return None
