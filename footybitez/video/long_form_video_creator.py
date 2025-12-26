import os
import random
import numpy as np
import logging
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
from footybitez.media.voice_generator import VoiceGenerator

logger = logging.getLogger(__name__)

class LongFormVideoCreator:
    def __init__(self, output_dir="footybitez/output"):
        self.output_dir = output_dir
        self.voice_gen = VoiceGenerator()
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "temp_text"), exist_ok=True)
        self.width = 1920
        self.height = 1080

    def create_long_video(self, script_data, visual_assets, background_music_path=None):
        """
        Creates a long-form 16:9 video.
        """
        try:
            clips = []
            audio_clips = []
            current_time = 0
            
            # 1. Process Intro
            intro_audio_path = self.voice_gen.generate(script_data['intro']['text'], "intro.mp3")
            intro_audio = AudioFileClip(intro_audio_path)
            intro_visual = self._get_visual(script_data['intro']['visual_keyword'], visual_assets, intro_audio.duration)
            intro_visual = self._ensure_rgb(intro_visual).set_audio(intro_audio)
            
            # Add intro overlay
            intro_text = self._create_chapter_overlay("FOOTY BITEZ PRESENTS", script_data['metadata']['title'])
            intro_overlay = self._ensure_rgb(ImageClip(intro_text).set_duration(intro_audio.duration)).set_position('center')
            
            clips.append(CompositeVideoClip([intro_visual, intro_overlay], size=(self.width, self.height)))
            current_time += intro_audio.duration
            
            # 2. Process Chapters
            for i, chapter in enumerate(script_data['chapters']):
                chapter_clips = []
                chapter_title = chapter['chapter_title']
                
                for j, fact in enumerate(chapter['facts']):
                    filename = f"chap_{i}_fact_{j}.mp3"
                    audio_path = self.voice_gen.generate(fact['text'], filename)
                    audio = AudioFileClip(audio_path)
                    
                    visual = self._get_visual(fact['visual_keyword'], visual_assets, audio.duration)
                    visual = self._ensure_rgb(visual).set_audio(audio)
                    
                    # Fact overlay (optional, maybe just chapter title at start of chapter)
                    if j == 0:
                        chap_text = self._create_chapter_overlay(f"CHAPTER {i+1}", chapter_title)
                        chap_overlay = self._ensure_rgb(ImageClip(chap_text).set_duration(min(3, audio.duration))).set_position('center').fadeout(0.5)
                        visual = CompositeVideoClip([visual, chap_overlay], size=(self.width, self.height))
                    
                    chapter_clips.append(visual)
                
                clips.extend(chapter_clips)

            # 3. Process Outro
            outro_audio_path = self.voice_gen.generate(script_data['outro']['text'], "outro.mp3")
            outro_audio = AudioFileClip(outro_audio_path)
            outro_visual = self._get_visual(script_data['outro']['visual_keyword'], visual_assets, outro_audio.duration)
            outro_visual = self._ensure_rgb(outro_visual).set_audio(outro_audio)
            
            outro_text = self._create_chapter_overlay("THANKS FOR WATCHING", "SUBSCRIBE FOR MORE")
            outro_overlay = self._ensure_rgb(ImageClip(outro_text).set_duration(outro_audio.duration)).set_position('center')
            
            clips.append(CompositeVideoClip([outro_visual, outro_overlay], size=(self.width, self.height)))

            # 4. Concatenate and Music
            final_video = concatenate_videoclips(clips, method="compose")
            total_duration = final_video.duration
            
            if background_music_path and os.path.exists(background_music_path):
                music = AudioFileClip(background_music_path).volumex(0.1)
                if music.duration < total_duration:
                    music = afx.audio_loop(music, duration=total_duration)
                else:
                    music = music.subclip(0, total_duration)
                
                final_audio = CompositeAudioClip([final_video.audio, music])
                final_video = final_video.set_audio(final_audio)

            # 5. Export
            output_path = os.path.join(self.output_dir, "long_form_video.mp4")
            final_video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac", logger=None)
            
            return output_path

        except Exception as e:
            logger.error(f"Long-form video creation failed: {e}")
            raise e

    def _get_visual(self, keyword, assets, duration):
        """Reuses logic but for 16:9."""
        # For simplicity in this first version, we'll pick a random clip from assets or placeholder
        # In a real run, MediaSourcer would have fetched specific 16:9 clips.
        segment_media = assets.get('segment_media', [])
        if not segment_media:
            # Placeholder color clip if no media
            return ColorClip(size=(self.width, self.height), color=(0,0,0)).set_duration(duration)
        
        path = random.choice(segment_media)
        if path.endswith(('.mp4', '.mov')):
            clip = VideoFileClip(path)
            if clip.duration < duration:
                clip = clip.loop(duration=duration)
            else:
                clip = clip.subclip(0, duration)
            return self._resize_to_horizontal(clip)
        else:
            clip = ImageClip(path).set_duration(duration)
            return self._resize_to_horizontal(clip)

    def _resize_to_horizontal(self, clip):
        """Ensures 1920x1080."""
        w, h = clip.size
        target_ratio = self.width / self.height
        current_ratio = w / h
        
        if current_ratio > target_ratio:
            # wider than 16:9 -> crop width
            new_width = int(h * target_ratio)
            clip = clip.crop(x1=w/2 - new_width/2, width=new_width, height=h)
        else:
            # taller than 16:9 -> crop height
            new_height = int(w / target_ratio)
            clip = clip.crop(y1=h/2 - new_height/2, width=w, height=new_height)
            
        return clip.resize((self.width, self.height))

    def _create_chapter_overlay(self, upper_text, lower_text):
        """Creates a clean documentary-style text overlay image."""
        img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        try:
            # Use industrial/bold fonts
            font_path = "arialbd.ttf"
            if os.name == 'nt':
                font_path = "C:\\Windows\\Fonts\\arialbd.ttf"
            else:
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                
            font_upper = ImageFont.truetype(font_path, 40)
            font_lower = ImageFont.truetype(font_path, 80)
        except:
            font_upper = ImageFont.load_default()
            font_lower = ImageFont.load_default()

        # Draw with shadow for readability
        def draw_text_centered(text, y, font, fill):
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
            x = (self.width - w) // 2
            # Shadow
            draw.text((x+4, y+4), text, font=font, fill=(0,0,0,180))
            # Main
            draw.text((x, y), text, font=font, fill=fill)

        draw_text_centered(upper_text.upper(), self.height//2 - 60, font_upper, (200, 200, 200, 255))
        draw_text_centered(lower_text.upper(), self.height//2, font_lower, (255, 255, 255, 255))
        
        temp_path = os.path.join(self.output_dir, "temp_text", f"overlay_{hash(upper_text+lower_text)}.png")
        img.save(temp_path)
        return temp_path

    def _ensure_rgb(self, clip):
        """Ensures the clip frames are in RGB (3 channels)."""
        def make_rgb(frame):
            if len(frame.shape) == 2:
                # Grayscale to RGB
                return np.dstack([frame] * 3)
            elif len(frame.shape) == 3:
                if frame.shape[2] == 4:
                    # RGBA to RGB
                    return frame[:,:,:3]
                elif frame.shape[2] == 2:
                    # Grayscale + Alpha to RGB
                    return np.dstack([frame[:,:,0]] * 3)
                elif frame.shape[2] == 3:
                    return frame
            
            if len(frame.shape) == 3 and frame.shape[2] > 3:
                return frame[:,:,:3]
            
            return frame
        return clip.fl_image(make_rgb)

if __name__ == "__main__":
    # Test stub
    pass
