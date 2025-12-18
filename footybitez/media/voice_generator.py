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

    def generate(self, text, filename):
        """
        Generates audio and subtitles from text using edge-tts.
        Returns the path to the audio file.
        Also generates a .vtt file with the same basename.
        """
        clean_text = text.replace('*', '') # Remove highlights for audio
        output_path = os.path.join(self.output_dir, filename)
        vtt_path = output_path.replace('.mp3', '.vtt')
        
        # Ensure output dir exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Use ChristopherNeural for viral shorts top tier voice
        voice = "en-US-ChristopherNeural" 
        
        max_retries = 3
        import time
        import random

        for attempt in range(max_retries):
            try:
                print(f"Generating audio for: {filename} (Attempt {attempt+1})")
                
                cmd = [
                    "edge-tts",
                    "--voice", voice,
                    "--text", clean_text,
                    "--write-media", output_path,
                    "--write-subtitles", vtt_path
                ]
                
                # Run CLI
                logger.info(f"Executing: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"Edge TTS CLI failed (Attempt {attempt+1}): {result.stderr}")
                    if attempt < max_retries - 1:
                        sleep_time = random.uniform(3, 7)
                        time.sleep(sleep_time)
                        continue
                    else:
                        raise Exception(f"Edge TTS failed after {max_retries} attempts: {result.stderr}")
                    
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"Successfully generated audio for {filename}")
                    return output_path
                else:
                    raise Exception("Output file is empty or missing")

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Edge TTS attempt {attempt+1} failed ({e}). Retrying...")
                    time.sleep(random.uniform(3, 7))
                else:
                    logger.error(f"Edge TTS failed ({e}). Falling back to gTTS...")
                    try:
                        # Fallback (No subtitles for gTTS natively)
                        from gtts import gTTS
                        # Use co.uk for a more neutral/professional sounding English voice (usually female though)
                        tts = gTTS(text=clean_text, lang='en', tld='co.uk')
                        tts.save(output_path)
                        
                        # Calculate a slightly slower duration to avoid text being "ahead"
                        # Short sentences are often spoken slower than long ones.
                        self._generate_fallback_vtt(clean_text, vtt_path, audio_path=output_path)
                        return output_path
                    except Exception as e2:
                         logger.error(f"gTTS failed: {e2}")
                         raise e2

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
