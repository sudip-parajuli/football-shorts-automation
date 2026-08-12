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
import base64
from gtts import gTTS
from moviepy.editor import AudioFileClip
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class VoiceGenerator:
    def __init__(self, output_dir="remotion-video/public/assets/audio", key_pool="auto"):
        load_dotenv()
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Hume Keys — separate pools for long-form and shorts to avoid quota starvation
        if key_pool == "long_form":
            self.hume_keys = [
                os.getenv("HUME_API_KEY_LONG_1"),
                os.getenv("HUME_API_KEY_LONG_2"),
                os.getenv("HUME_API_KEY_LONG_3"),
                os.getenv("HUME_API_KEY_LONG_4"),
                os.getenv("HUME_API_KEY_LONG_5"),
            ]
        elif key_pool == "shorts":
            self.hume_keys = [
                os.getenv("HUME_API_KEY_SHORT_1"),
                os.getenv("HUME_API_KEY_SHORT_2"),
                os.getenv("HUME_API_KEY_SHORT_3"),
                os.getenv("HUME_API_KEY_SHORT_4"),
                os.getenv("HUME_API_KEY_SHORT_5"),
            ]
        else:
            # Legacy "auto" mode — falls back to old generic keys
            self.hume_keys = [
                os.getenv("HUME_API_KEY"),
                os.getenv("HUME_API_KEY2"),
                os.getenv("HUME_API_KEY3"),
                os.getenv("HUME_API_KEY4"),
                os.getenv("HUME_API_KEY5"),
            ]
        self.hume_keys = [k for k in self.hume_keys if k]
        # Start at a random key index to spread initial hit and round-robin rotate from there
        self._key_index = random.randint(0, len(self.hume_keys) - 1) if self.hume_keys else 0

        
        # Hume Voice IDs
        self.hume_voices = [
            os.getenv("HUME_VOICE_ID"),
            os.getenv("HUME_VOICE_ID_1"),
            os.getenv("HUME_VOICE_ID_2")
        ]
        self.hume_voices = [v for v in self.hume_voices if v]

        # Google Cloud Text-to-Speech — first-choice provider (see generate()).
        # Free tier: ~1M chars/month per voice type (Neural2/WaveNet/Standard each
        # have their own free allowance), authenticated via a simple REST API key
        # (Cloud Console -> APIs & Services -> Credentials, with the "Cloud
        # Text-to-Speech API" enabled on the project). Supports rotating multiple
        # keys the same way Gemini/Hume do here.
        self.gcp_tts_keys = [
            os.getenv("GOOGLE_CLOUD_TTS_API_KEY"),
            os.getenv("GOOGLE_CLOUD_TTS_API_KEY2"),
        ]
        self.gcp_tts_keys = [k for k in self.gcp_tts_keys if k]
        # Deep, energetic male voice well-suited to football/sports narration.
        # Override with GOOGLE_CLOUD_TTS_VOICE if a different voice is preferred —
        # must be a MALE voice name from https://cloud.google.com/text-to-speech/docs/voices
        self.gcp_tts_voice = os.getenv("GOOGLE_CLOUD_TTS_VOICE", "en-US-Neural2-D")

    def generate(self, text, filename, voice_index=0):
        """
        Generates audio using, in order: Google Cloud TTS (primary), Hume (2nd),
        Edge TTS (3rd), gTTS (last resort).
        """
        clean_text = self._clean_text(text)
        output_path = os.path.join(self.output_dir, filename)
        json_path = output_path.replace('.mp3', '.json')

        # 1. Try Google Cloud Text-to-Speech (first choice)
        if self.gcp_tts_keys:
            if self._generate_gcp_tts(clean_text, output_path, json_path):
                logger.info(f"Google Cloud TTS generated {filename}")
                return output_path
            logger.info(f"Google Cloud TTS failed for {filename}. Falling back to Hume...")

        # 2. Try Hume AI
        if self.hume_keys:
            if self._generate_hume(clean_text, output_path, voice_index):
                logger.info(f"Hume AI generated {filename}")
                self._generate_json_fallback(clean_text, json_path, output_path)
                return output_path

        # 3. Fallback to Edge TTS
        logger.info(f"Hume failed or missing keys. Trying Edge TTS for {filename}...")
        try:
            voice = "en-US-ChristopherNeural"
            asyncio.run(self._generate_edge_async(clean_text, output_path, json_path, voice))
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
        except Exception as e:
            logger.error(f"Edge TTS failed: {e}")

        # 4. Fallback to gTTS
        logger.info(f"Edge TTS failed. Falling back to gTTS for {filename}...")
        try:
            tts = gTTS(text=clean_text, lang='en', tld='co.uk')
            tts.save(output_path)
            self._generate_json_fallback(clean_text, json_path, output_path)
            return output_path
        except Exception as e:
            logger.error(f"gTTS failed: {e}")
            
        return None

    def _generate_gcp_tts(self, text, output_path, json_path):
        """
        Calls the Google Cloud Text-to-Speech REST API (v1beta1, API-key auth — no
        service account needed). Uses SSML <mark> tags before every word plus
        `enableTimePointing` to recover accurate word-level start times for karaoke
        captions, falling back to even-split timing if timepoints aren't returned.
        """
        words = text.split()
        if not words or not self.gcp_tts_keys:
            return False

        def _escape(w):
            return w.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        ssml = "<speak>" + "".join(f'<mark name="w{i}"/>{_escape(w)} ' for i, w in enumerate(words)) + "</speak>"

        # Voice name like "en-US-Neural2-D" -> language code "en-US"
        parts = self.gcp_tts_voice.split("-")
        language_code = "-".join(parts[:2]) if len(parts) >= 2 else "en-US"

        payload = {
            "input": {"ssml": ssml},
            "voice": {"languageCode": language_code, "name": self.gcp_tts_voice, "ssmlGender": "MALE"},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.05, "pitch": -1.0},
            "enableTimePointing": ["SSML_MARK"],
        }

        for i, key in enumerate(self.gcp_tts_keys):
            try:
                url = f"https://texttospeech.googleapis.com/v1beta1/text:synthesize?key={key}"
                response = requests.post(url, json=payload, timeout=60)
                if response.status_code != 200:
                    logger.warning(f"Google Cloud TTS error {response.status_code} on key #{i+1}: {response.text[:300]}")
                    continue

                data = response.json()
                audio_b64 = data.get("audioContent")
                if not audio_b64:
                    logger.warning(f"Google Cloud TTS returned no audioContent on key #{i+1}.")
                    continue

                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(audio_b64))

                # Recover per-word timing from the SSML mark timepoints.
                mark_times = {}
                for tp in data.get("timepoints", []):
                    name = tp.get("markName", "")
                    if name.startswith("w"):
                        try:
                            mark_times[int(name[1:])] = float(tp.get("timeSeconds", 0))
                        except ValueError:
                            pass

                if mark_times:
                    audio_duration = 0.0
                    try:
                        clip = AudioFileClip(output_path)
                        audio_duration = clip.duration
                        clip.close()
                    except Exception:
                        pass

                    sorted_idx = sorted(mark_times.keys())
                    word_map = []
                    for pos, idx in enumerate(sorted_idx):
                        start = mark_times[idx]
                        end = mark_times[sorted_idx[pos + 1]] if pos + 1 < len(sorted_idx) else max(start + 0.3, audio_duration)
                        word_map.append({"word": words[idx], "start": start, "duration": max(0.05, end - start)})
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(word_map, f, indent=2)
                else:
                    # Timepointing didn't come back for some reason — even-split fallback.
                    self._generate_json_fallback(text, json_path, output_path)

                return True
            except Exception as e:
                logger.warning(f"Google Cloud TTS attempt failed on key #{i+1}: {e}")

        return False

    def _generate_hume(self, text, output_path, voice_index):
        """Internal method to call Hume TTS API with key rotation."""
        if not self.hume_keys:
            return False
        
        num_keys = len(self.hume_keys)
        for i in range(num_keys):
            # Rotate key index starting from current position
            current_index = (self._key_index + i) % num_keys
            api_key = self.hume_keys[current_index]
            try:
                voice_id = self.hume_voices[voice_index % len(self.hume_voices)] if self.hume_voices else None
                
                # Updated Hume TTS API endpoint (Octave models)
                url = "https://api.hume.ai/v0/tts/file"
                headers = {
                    "X-Hume-Api-Key": api_key,
                    "Content-Type": "application/json"
                }
                payload = {
                    "utterances": [{"text": text}],
                    "format": {"type": "mp3"}
                }
                
                if voice_id:
                     payload["utterances"][0]["description"] = f"Voice ID: {voice_id}"
                
                response = requests.post(url, json=payload, headers=headers, timeout=60)
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    # Advance rotation index to the next key after this successful key
                    self._key_index = (current_index + 1) % num_keys
                    return True
                else:
                    logger.warning(f"Hume API error {response.status_code} on key index {current_index}: {response.text}")
            except Exception as e:
                logger.warning(f"Hume attempt failed on key index {current_index}: {e}")
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
