import subprocess
import edge_tts
import os
from gtts import gTTS

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
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"Edge TTS CLI failed (Attempt {attempt+1}): {result.stderr}")
                    if attempt < max_retries - 1:
                        sleep_time = random.uniform(2, 5)
                        time.sleep(sleep_time)
                        continue
                    else:
                        raise Exception(f"Edge TTS failed after {max_retries} attempts")
                    
                return output_path

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Edge TTS attempt {attempt+1} failed ({e}). Retrying...")
                    time.sleep(random.uniform(2, 5))
                else:
                    print(f"Edge TTS failed ({e}). Falling back to gTTS...")
                    try:
                        # Fallback (No subtitles for gTTS, sad)
                        from gtts import gTTS
                        # Use co.uk for a more neutral/professional sounding English voice
                        tts = gTTS(text=clean_text, lang='en', tld='co.uk')
                        tts.save(output_path)
                        
                        self._generate_fallback_vtt(clean_text, vtt_path)
                        return output_path
                    except Exception as e2:
                         print(f"gTTS failed: {e2}")
                         raise e2

    def _generate_fallback_vtt(self, text, vtt_path):
        """Generates a rough VTT file for fallback."""
        words = text.split()
        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            current_time = 0.0
            word_duration = 0.4 # Rough estimate
            
            for i in range(0, len(words), 4): # Group 4 words
                chunk = words[i:i+4]
                text_chunk = " ".join(chunk)
                start = self._format_time(current_time)
                end = self._format_time(current_time + (len(chunk) * word_duration))
                
                f.write(f"{start} --> {end}\n")
                f.write(f"{text_chunk}\n\n")
                current_time += (len(chunk) * word_duration)

    def _format_time(self, seconds):
        # HH:MM:SS.mmm
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"

if __name__ == "__main__":
    vg = VoiceGenerator()
    path = vg.generate("Welcome to Footy Bitez. Did you know Lionel Messi has 8 Ballon d'Ors?")
    print(f"Generated voice at: {path}")
