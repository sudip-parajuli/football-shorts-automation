import subprocess
import edge_tts
import os
import logging
import time
import random
import requests
import re
import asyncio
import json
from gtts import gTTS
from moviepy.editor import AudioFileClip
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class VoiceGenerator:
    def __init__(self, output_dir="remotion-video/public/assets/audio"):
        load_dotenv()
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Hume Keys
        self.hume_keys = [
            os.getenv("HUME_API_KEY"),
            os.getenv("HUME_API_KEY2"),
            os.getenv("HUME_API_KEY3")
        ]
        self.hume_keys = [k for k in self.hume_keys if k]
        
        # Hume Voice IDs
        self.hume_voices = [
            os.getenv("HUME_VOICE_ID"),
            os.getenv("HUME_VOICE_ID_1"),
            os.getenv("HUME_VOICE_ID_2")
        ]
        self.hume_voices = [v for v in self.hume_voices if v]

    def generate(self, text, filename, voice_index=0):
        """
        Generates audio using Hume (primary), Edge TTS (fallback), or gTTS (last resort).
        """
        clean_text = self._clean_text(text)
        output_path = os.path.join(self.output_dir, filename)
        json_path = output_path.replace('.mp3', '.json')
        
        # 1. Try Hume AI
        if self.hume_keys:
            if self._generate_hume(clean_text, output_path, voice_index):
                logger.info(f"Hume AI generated {filename}")
                self._generate_json_fallback(clean_text, json_path, output_path)
                return output_path
        
        # 2. Fallback to Edge TTS
        logger.info(f"Hume failed or missing keys. Trying Edge TTS for {filename}...")
        try:
            voice = "en-US-ChristopherNeural"
            asyncio.run(self._generate_edge_async(clean_text, output_path, json_path, voice))
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
        except Exception as e:
            logger.error(f"Edge TTS failed: {e}")

        # 3. Fallback to gTTS
        logger.info(f"Edge TTS failed. Falling back to gTTS for {filename}...")
        try:
            tts = gTTS(text=clean_text, lang='en', tld='co.uk')
            tts.save(output_path)
            self._generate_json_fallback(clean_text, json_path, output_path)
            return output_path
        except Exception as e:
            logger.error(f"gTTS failed: {e}")
            
        return None

    def _generate_hume(self, text, output_path, voice_index):
        """Internal method to call Hume TTS API."""
        # Note: Using rotation of keys if one fails
        for api_key in self.hume_keys:
            try:
                voice_id = self.hume_voices[voice_index % len(self.hume_voices)] if self.hume_voices else None
                
                # Placeholder for Hume TTS API call
                # Hume's TTS is often part of their EVI or a specific endpoint
                # Assuming typical REST pattern if using their newer TTS engine
                url = "https://api.hume.ai/v0/tti/tts" 
                headers = {
                    "X-Hume-Api-Key": api_key,
                    "Content-Type": "application/json"
                }
                payload = {
                    "text": text,
                    "voice_id": voice_id,
                    "format": "mp3"
                }
                
                # Since exact Hume TTS endpoint might vary, let's ensure we handle errors
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    return True
                else:
                    logger.warning(f"Hume API error {response.status_code}: {response.text}")
            except Exception as e:
                logger.warning(f"Hume attempt failed: {e}")
        return False

    async def _generate_edge_async(self, text, output_path, json_path, voice):
        communicate = edge_tts.Communicate(text, voice)
        word_map = []
        with open(output_path, "wb") as file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    word_map.append({
                        "word": chunk["text"],
                        "start": chunk["offset"] / 10**7,
                        "duration": chunk["duration"] / 10**7
                    })
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(word_map, f, indent=2)

    def _clean_text(self, text):
        clean = text.replace('*', '')
        clean = re.sub(r'\[.*?\]', '', clean).strip()
        return clean

    def _generate_json_fallback(self, text, json_path, audio_path):
        words = text.split()
        duration = 5.0
        if os.path.exists(audio_path):
            try:
                audio = AudioFileClip(audio_path)
                duration = audio.duration
                audio.close()
            except: pass
        avg = duration / max(len(words), 1)
        word_map = [{"word": w, "start": i*avg, "duration": avg*0.9} for i, w in enumerate(words)]
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(word_map, f, indent=2)
