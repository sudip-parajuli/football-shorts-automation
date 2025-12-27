import subprocess
import edge_tts
import os
import logging
import time
import random
from gtts import gTTS
from moviepy.editor import AudioFileClip

logger = logging.getLogger(__name__)

class VoiceGenerator:
    def __init__(self, voice="en-GB-SoniaNeural", output_dir="footybitez/media/voice"):
        self.voice = voice
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _generate_gtts(self, text, output_path):
        """Internal method for gTTS."""
        tts = gTTS(text=text, lang='en', tld='co.uk')
        tts.save(output_path)

    async def _generate_async(self, text, output_path, vtt_path, json_path, voice):
        """Asynchronous core for generating audio and word-level timing."""
        import edge_tts
        import json
        
        communicate = edge_tts.Communicate(text, voice)
        submaker = edge_tts.SubMaker()
        word_map = []

        with open(output_path, "wb") as file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    # Collect word boundaries
                    word_map.append({
                        "word": chunk["text"],
                        "start": chunk["offset"] / 10**7, # Convert 100ns to seconds
                        "duration": chunk["duration"] / 10**7
                    })
                    submaker.feed(chunk)

        with open(vtt_path, "w", encoding="utf-8") as file:
            file.write(submaker.get_srt())
        
        with open(json_path, "w", encoding="utf-8") as file:
            json.dump(word_map, file)

    def generate(self, text, filename):
        """
        Generates audio, VTT, and word-level JSON using edge-tts.
        Returns the path to the audio file.
        """
        import asyncio
        clean_text = text.replace('*', '') 
        output_path = os.path.join(self.output_dir, filename)
        vtt_path = output_path.replace('.mp3', '.vtt')
        json_path = output_path.replace('.mp3', '.json')
        
        os.makedirs(self.output_dir, exist_ok=True)
        # Aria is very stable for WordBoundaries
        voice = "en-US-AriaNeural" 
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Generating audio/timing for: {filename} (Attempt {attempt+1})")
                asyncio.run(self._generate_async(clean_text, output_path, vtt_path, json_path, voice))
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"Successfully generated audio for {filename}")
                    
                    # If JSON is empty or missing, create a word-count fallback
                    if not os.path.exists(json_path) or os.path.getsize(json_path) <= 2:
                        logger.warning(f"JSON timing missing for {filename}. Creating fallback.")
                        self._generate_json_fallback(clean_text, json_path, output_path)
                        
                    return output_path
                else:
                    raise Exception("Output file is empty or missing")

            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(2, 5))
                else:
                    logger.error("Edge TTS failed completely. Falling back to gTTS.")
                    from gtts import gTTS
                    tts = gTTS(text=clean_text, lang='en', tld='co.uk')
                    tts.save(output_path)
                    # Create word-count fallback JSON
                    self._generate_json_fallback(clean_text, json_path, output_path)
                    return output_path

    def _generate_json_fallback(self, text, json_path, audio_path):
        """Creates a word-level JSON based on average word duration."""
        import json
        words = text.split()
        if not words:
            with open(json_path, 'w') as f: f.write("[]")
            return

        duration = 5.0 # Default
        if os.path.exists(audio_path):
            try:
                from moviepy.editor import AudioFileClip
                audio = AudioFileClip(audio_path)
                duration = audio.duration
                audio.close()
            except:
                pass
        
        avg_word_dur = duration / len(words)
        word_map = []
        for i, word in enumerate(words):
            word_map.append({
                "word": word,
                "start": i * avg_word_dur,
                "duration": avg_word_dur * 0.9 # Small gap
            })
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(word_map, f)

    def _generate_fallback_vtt(self, text, vtt_path, audio_path=None):
        """Generates a rough VTT file for fallback."""
        words = text.split()
        
        # Determine total duration
        total_duration = len(words) * 0.4 # Default
        if audio_path and os.path.exists(audio_path):
            try:
                audio = AudioFileClip(audio_path)
                total_duration = audio.duration
                audio.close()
            except:
                pass
        
        word_duration = total_duration / max(len(words), 1)
        
        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            current_time = 0.0
            
            # Grouping words for subtitles
            words_per_segment = 3
            for i in range(0, len(words), words_per_segment):
                chunk = words[i:i+words_per_segment]
                text_chunk = " ".join(chunk)
                start = self._format_time(current_time)
                
                # Calculate end based on word count
                chunk_dur = len(chunk) * word_duration
                end = self._format_time(current_time + chunk_dur)
                
                f.write(f"{start} --> {end}\n")
                f.write(f"{text_chunk}\n\n")
                current_time += chunk_dur

    def _format_time(self, seconds):
        # HH:MM:SS.mmm
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"

if __name__ == "__main__":
    vg = VoiceGenerator()
    path = vg.generate("Welcome to Footy Bitez. Did you know Lionel Messi has 8 Ballon d'Ors?")
    print(f"Generated voice at: {path}")
