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
        Creates a long-form 16:9 video with karaoke captions and transitions.
        """
        try:
            clips = []
            current_time = 0
            
            # 1. Process Intro
            intro_audio_path = self.voice_gen.generate(script_data['intro']['text'], "intro.mp3")
            intro_audio = AudioFileClip(intro_audio_path)
            intro_visual = self._get_visual(script_data['intro']['visual_keyword'], visual_assets, intro_audio.duration)
            intro_visual = self._ensure_rgb(intro_visual).set_audio(intro_audio)
            
            intro_text = self._create_chapter_overlay("FOOTY BITEZ PRESENTS", script_data['metadata']['title'])
            intro_overlay = self._ensure_rgb(ImageClip(intro_text).set_duration(intro_audio.duration)).set_position('center')
            
            intro_combined = CompositeVideoClip([intro_visual, intro_overlay], size=(self.width, self.height))
            
            # Add Karaoke for Intro
            intro_captions = self._create_karaoke_captions("intro.mp3", intro_audio.duration)
            if intro_captions:
                intro_combined = CompositeVideoClip([intro_combined, intro_captions], size=(self.width, self.height))
            
            clips.append(intro_combined.crossfadein(0.5))
            current_time += intro_audio.duration
            
            # 2. Process Chapters
            for i, chapter in enumerate(script_data['chapters']):
                chapter_title = chapter['chapter_title']
                
                # CHAPTER START SLIDE (Pause for 2 seconds)
                chap_text_path = self._create_chapter_overlay(f"CHAPTER {i+1}", chapter_title)
                # Use the first fact's visual as background for the chapter slide
                first_fact_visual = self._get_visual(chapter['facts'][0]['visual_keyword'], visual_assets, 2.5)
                chap_slide = CompositeVideoClip([first_fact_visual, self._ensure_rgb(ImageClip(chap_text_path).set_duration(2.5))], size=(self.width, self.height))
                clips.append(chap_slide.crossfadein(0.5).fadeout(0.5))
                current_time += 2.5
                
                for j, fact in enumerate(chapter['facts']):
                    filename = f"chap_{i}_fact_{j}.mp3"
                    audio_path = self.voice_gen.generate(fact['text'], filename)
                    audio = AudioFileClip(audio_path)
                    
                    visual = self._get_visual(fact['visual_keyword'], visual_assets, audio.duration)
                    visual = self._ensure_rgb(visual).set_audio(audio)
                    
                    # Chapter overlay removed from facts (moved to separate slide)
                    fact_video = visual
                    
                    # Add Karaoke for Fact
                    fact_captions = self._create_karaoke_captions(filename, audio.duration)
                    if fact_captions:
                        fact_video = CompositeVideoClip([fact_video, fact_captions.set_duration(audio.duration)], size=(self.width, self.height))
                    
                    clips.append(fact_video.crossfadein(0.5))
                
            # 3. Process Outro
            outro_audio_path = self.voice_gen.generate(script_data['outro']['text'], "outro.mp3")
            outro_audio = AudioFileClip(outro_audio_path)
            outro_visual = self._get_visual(script_data['outro']['visual_keyword'], visual_assets, outro_audio.duration)
            outro_visual = self._ensure_rgb(outro_visual).set_audio(outro_audio)
            
            outro_text = self._create_chapter_overlay("THANKS FOR WATCHING", "SUBSCRIBE FOR MORE")
            outro_overlay = self._ensure_rgb(ImageClip(outro_text).set_duration(outro_audio.duration)).set_position('center')
            
            outro_combined = CompositeVideoClip([outro_visual, outro_overlay], size=(self.width, self.height))
            
            # Add Karaoke for Outro
            outro_captions = self._create_karaoke_captions("outro.mp3", outro_audio.duration)
            if outro_captions:
                outro_combined = CompositeVideoClip([outro_combined, outro_captions], size=(self.width, self.height))
                
            clips.append(outro_combined.crossfadein(0.5))

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
        """Fetches visual and applies effects."""
        segment_media = assets.get('segment_media', [])
        if not segment_media:
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
            # Static Image with Zoom Effect
            clip = ImageClip(path).set_duration(duration)
            clip = self._resize_to_horizontal(clip)
            return self._add_zoom_effect(clip)

    def _add_zoom_effect(self, clip, zoom_ratio=0.04):
        """Adds a subtle Ken Burns zoom-in effect."""
        def effect(get_frame, t):
            frame = get_frame(t)
            h, w, c = frame.shape
            # Calculate zoom factor
            zoom = 1 + (zoom_ratio * (t / clip.duration))
            # Resize frame
            new_h, new_w = int(h * zoom), int(w * zoom)
            img = Image.fromarray(frame)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            # Crop back to center
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            img = img.crop((left, top, left + w, top + h))
            return np.array(img)
        return clip.fl(effect)

    def _create_karaoke_captions(self, audio_filename, total_duration):
        """Creates word-level karaoke captions."""
        import json
        json_path = os.path.join("footybitez/media/voice", audio_filename.replace('.mp3', '.json'))
        
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                word_data = json.load(f)
            
            if not word_data:
                return None

            # Group words into lines (sentences) to avoid flickering
            # For simplicity, we'll show segments of ~5 words
            lines = []
            words_per_line = 6
            for i in range(0, len(word_data), words_per_line):
                lines.append(word_data[i:i+words_per_line])

            line_clips = []
            for line in lines:
                line_start = line[0]['start']
                line_end = line[-1]['start'] + line[-1]['duration']
                line_duration = line_end - line_start
                
                # Create a clip for this line
                def make_line_frame(t):
                    # t is relative to line_start
                    absolute_t = line_start + t
                    
                    # Create the canvas (Transparent)
                    canvas = Image.new('RGBA', (self.width, 250), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(canvas)
                    
                    try:
                        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                        if os.name == 'nt': font_path = "C:\\Windows\\Fonts\\arialbd.ttf"
                        font = ImageFont.truetype(font_path, 65)
                    except:
                        font = ImageFont.load_default()

                    full_text = " ".join([w['word'] for w in line])
                    bbox = draw.textbbox((0, 0), full_text, font=font)
                    text_w = bbox[2] - bbox[0]
                    # Ensure some margin
                    start_x = (self.width - text_w) // 2
                    
                    # Draw each word
                    current_x = start_x
                    for word_info in line:
                        word = word_info['word'] + " "
                        w_bbox = draw.textbbox((0, 0), word, font=font)
                        w_w = w_bbox[2] - w_bbox[0]
                        
                        # Is this word currently being spoken?
                        is_active = word_info['start'] <= absolute_t <= (word_info['start'] + word_info['duration'])
                        
                        if is_active:
                            # Highlight background yellow with rounded-like corners
                            padding = 5
                            draw.rectangle([current_x - padding, 40, current_x + w_w + padding, 130], fill=(255, 255, 0, 255))
                            draw.text((current_x, 40), word, font=font, fill=(0, 0, 0, 255))
                        else:
                            # Standard white text with thick black stroke for high visibility
                            stroke_width = 4
                            for off_x in range(-stroke_width, stroke_width+1):
                                for off_y in range(-stroke_width, stroke_width+1):
                                    if off_x != 0 or off_y != 0:
                                        draw.text((current_x + off_x, 40 + off_y), word, font=font, fill=(0, 0, 0, 255))
                            draw.text((current_x, 40), word, font=font, fill=(255, 255, 255, 255))
                        
                        current_x += w_w
                        
                    return np.array(canvas)

                def make_mask_frame(t):
                    rgba = make_line_frame(t)
                    return rgba[:,:,3] / 255.0

                def make_rgb_frame(t):
                    rgba = make_line_frame(t)
                    return rgba[:,:,:3]

                line_clip = VideoClip(make_rgb_frame, duration=line_duration).set_start(line_start)
                line_mask = VideoClip(make_mask_frame, ismask=True, duration=line_duration).set_start(line_start)
                line_clip = line_clip.set_mask(line_mask).set_position(('center', 850))
                line_clips.append(line_clip)
            
            # Use CompositeVideoClip to combine all lines for this audio segment
            combined = CompositeVideoClip(line_clips, size=(self.width, self.height))
            return combined.set_duration(total_duration)

        except Exception as e:
            logger.error(f"Failed to create karaoke captions: {e}")
            return None

    def _resize_to_horizontal(self, clip):
        """Ensures 1920x1080 crop/resize."""
        w, h = clip.size
        # If already exactly 1920x1080, just return
        if w == self.width and h == self.height:
            return clip
            
        target_ratio = self.width / self.height
        current_ratio = w / h
        
        if current_ratio > target_ratio:
            new_width = int(h * target_ratio)
            clip = clip.crop(x1=w/2 - new_width/2, width=new_width, height=h)
        else:
            new_height = int(w / target_ratio)
            clip = clip.crop(y1=h/2 - new_height/2, width=w, height=new_height)
            
        return clip.resize((self.width, self.height))

    def _create_chapter_overlay(self, upper_text, lower_text):
        """Creates a clean documentary-style text overlay image with multi-line support."""
        img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        try:
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if os.name == 'nt': font_path = "C:\\Windows\\Fonts\\arialbd.ttf"
            font_upper = ImageFont.truetype(font_path, 50)
            font_lower = ImageFont.truetype(font_path, 110)
        except:
            font_upper = ImageFont.load_default()
            font_lower = ImageFont.load_default()

        import textwrap
        # Margin: left and right
        max_width_chars = 25 # roughly for 110pt font on 1920px
        wrapped_lower = textwrap.wrap(lower_text.upper(), width=max_width_chars)
        
        def draw_text_centered(text_lines, start_y, font, fill, spacing=20):
            current_y = start_y
            for line in text_lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                x = (self.width - w) // 2
                # Stroke for visibility
                stroke_w = 4
                for ox in range(-stroke_w, stroke_w+1):
                    for oy in range(-stroke_w, stroke_w+1):
                        draw.text((x+ox, current_y+oy), line, font=font, fill=(0,0,0,255))
                draw.text((x, current_y), line, font=font, fill=fill)
                current_y += (bbox[3] - bbox[1]) + spacing
            return current_y

        # Draw Upper Text
        y_after_upper = draw_text_centered([upper_text.upper()], self.height//2 - 120, font_upper, (200, 200, 200, 255))
        # Draw Lower Text (Wrapped)
        draw_text_centered(wrapped_lower, y_after_upper + 10, font_lower, (255, 255, 255, 255))
        
        temp_path = os.path.join(self.output_dir, "temp_text", f"overlay_{hash(upper_text+lower_text)}.png")
        img.save(temp_path)
        return temp_path

    def _ensure_rgb(self, clip):
        """Ensures the clip frames are in RGB (3 channels) or maintains RGBA."""
        def make_rgb(frame):
            if len(frame.shape) == 2:
                return np.dstack([frame] * 3)
            elif len(frame.shape) == 3:
                if frame.shape[2] == 4:
                    return frame
                elif frame.shape[2] == 2:
                    return np.dstack([frame[:,:,0]] * 3)
                elif frame.shape[2] == 3:
                    return frame
            return frame
        # CRITICAL: We MUST set apply_to=[] so the mask is NOT processed by make_rgb
        return clip.fl_image(make_rgb, apply_to=[])

if __name__ == "__main__":
    pass
