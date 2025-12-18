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
        
        try:
            # Check edge-tts availability and version if needed using subprocess
            # Command: edge-tts --text "..." --write-media out.mp3 --write-subtitles out.vtt --voice ...
            print(f"Generating audio for: {filename}")
            
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
                print(f"Edge TTS CLI failed: {result.stderr}")
                raise Exception("Edge TTS CLI failed")
                
            return output_path

        except Exception as e:
            print(f"Edge TTS failed ({e}). Falling back to gTTS...")
            try:
                # Fallback (No subtitles for gTTS, sad)
                from gtts import gTTS
                tts = gTTS(text=clean_text, lang='en')
                tts.save(output_path)
                
                # Generate fake VTT for gTTS so video doesn't break
                # Estimate duration based on file size or text length?
                # We can't know exact duration without loading audio, but let's try.
                # Actually, main script generates audio first, then creates video.
                # Video creator reads duration from audio file. 
                # So here we just need a VTT with *relative* timing or just words.
                # We will write a placeholder VTT that will be fixed/ignored or simple word spread?
                # Using simple word spread estimation: 150 words per minute ~ 0.4s per word
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
