import os
import random
import numpy as np
import logging
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from footybitez.media.voice_generator import VoiceGenerator
from footybitez.media.sfx_manager import SFXManager

logger = logging.getLogger(__name__)

class LongFormVideoCreator:
    def __init__(self, output_dir="footybitez/output"):
        self.output_dir = output_dir
        self.voice_gen = VoiceGenerator()
        self.sfx_man = SFXManager()
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "temp_text"), exist_ok=True)
        self.width = 1920
        self.height = 1080

    def create_long_video(self, script_data, visual_assets, background_music_path=None):
        """
        Creates a long-form 16:9 video with distinct phases:
        1. Main Title (Silent, Title Text, NO Subs)
        2. Intro (VO + Subs, NO Title)
        3. Chapters (Silent Card -> VO + Subs)
        4. Outro
        """
        try:
            clips = []
            
            # Prepare Media Deck (Shuffle to avoid repeats)
            segment_media = visual_assets.get('segment_media', [])
            if segment_media:
                random.shuffle(segment_media)
            self.media_deck = list(segment_media) # Copy
            self.used_media_indices = []

            # --- PHASE 1: MAIN TITLE CARD (HERO MOMENT) ---
            # Visuals: Blurred + Zoomed Background
            # Overlays: Text + Sheen Effect (Glowing line runs through words)
            # Audio: Kick SFX
            
            title_text_path = self._create_chapter_overlay("FOOTYBITEZ PRESENTS", script_data['metadata']['title'])
            
            # 1. Background
            title_bg_keyword = script_data.get('intro', {}).get('visual_keyword', 'football stadium')
            title_visual = self._get_visual(title_bg_keyword, visual_assets, 4.0)
            title_visual = self._add_blur_effect(title_visual, radius=20)
            if not hasattr(title_visual, 'fl'):
                 title_visual = self._add_zoom_effect(title_visual, 0.05)
            
            # 2. Text Overlay Base
            title_img_clip = ImageClip(title_text_path).set_duration(4.0).set_position('center')
            
            # 3. Sheen Effect (Glowing Multicolor Line runs "through" words)
            # Use a mask generated from the title text alpha channel
            title_mask = ImageClip(title_text_path, ismask=True).to_mask()
            
            # Create a moving gradient bar (Gold/Cyan)
            def make_sheen_frame(t):
                w, h = 150, self.height 
                if t < 0.5 or t > 2.5:
                    return np.zeros((self.height, self.width, 3), dtype=np.uint8)
                
                progress = (t - 0.5) / 1.5 
                center_x = -w + (self.width + w*2) * progress
                
                frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                
                x_start = int(max(0, center_x))
                x_end = int(min(self.width, center_x + w))
                
                if x_end > x_start:
                    # Simple robust implementation: Two bands
                    # 50% Gold [255, 215, 0], 50% Cyan [0, 255, 255]
                    mid = x_start + (x_end - x_start)//2
                    if mid > x_start:
                        frame[:, x_start:mid] = [0, 255, 255] # Cyan
                    if x_end > mid:
                        frame[:, mid:x_end] = [255, 215, 0] # Gold
                
                return frame

            sheen_clip = VideoClip(make_sheen_frame, duration=4.0).set_opacity(0.8)
            sheen_masked = sheen_clip.set_mask(title_mask)

            # 4. SFX (Kick)
            sfx_kick = self.sfx_man.get_sfx("kick")
            
            title_card = CompositeVideoClip([
                title_visual, 
                title_img_clip, 
                sheen_masked.set_position('center') 
            ], size=(self.width, self.height)).set_duration(4.0)
            
            # Attach SFX
            if sfx_kick:
                sfx_kick = sfx_kick.volumex(0.8)
                title_card = title_card.set_audio(sfx_kick)
            
            clips.append(title_card.crossfadein(1.0).fadeout(0.5))

            # --- PHASE 2: SPOKEN INTRO ---
            intro_audio_path = self.voice_gen.generate(script_data['intro']['text'], "intro.mp3")
            intro_audio = AudioFileClip(intro_audio_path)
            intro_visual = self._get_visual(script_data['intro']['visual_keyword'], visual_assets, intro_audio.duration)
            intro_visual = self._ensure_rgb(intro_visual).set_audio(intro_audio)
            
            intro_captions = self._get_karaoke_clips("intro.mp3", intro_audio.duration, 0, font_scale=1.0)
            intro_combined = CompositeVideoClip([intro_visual] + intro_captions, size=(self.width, self.height)).set_duration(intro_audio.duration)
            clips.append(intro_combined.crossfadein(0.5))
            
            # --- PHASE 3: CHAPTER FLOW ---
            for i, chapter in enumerate(script_data['chapters']):
                chapter_title = chapter['chapter_title']
                
                # A) CHAPTER TITLE CARD (KICK EFFECT)
                chap_text_path = self._create_chapter_overlay(f"CHAPTER {i+1}", chapter_title)
                
                # Visual background
                first_fact_visual = self._get_visual(chapter['facts'][0]['visual_keyword'], visual_assets, 2.0)
                
                # SFX: Kick
                sfx_kick_chap = self.sfx_man.get_sfx("kick", duration=0.5)
                
                chap_slide = CompositeVideoClip([
                    first_fact_visual, 
                    ImageClip(chap_text_path).set_duration(2.0).set_position('center')
                ], size=(self.width, self.height)).set_duration(2.0)
                
                # Attach Kick SFX
                if sfx_kick_chap:
                    sfx_kick_chap = sfx_kick_chap.volumex(0.7)
                    chap_slide = chap_slide.set_audio(sfx_kick_chap.set_start(0))
                
                # TRANSITION: Fast Fade In (0.1s)
                clips.append(chap_slide.fadein(0.1).fadeout(0.3)) 
                
                # B) CHAPTER NARRATION
                for j, fact in enumerate(chapter['facts']):
                    filename = f"chap_{i}_fact_{j}.mp3"
                    audio_path = self.voice_gen.generate(fact['text'], filename)
                    audio = AudioFileClip(audio_path)
                    
                    visual = self._get_visual(fact['visual_keyword'], visual_assets, audio.duration)
                    visual = self._ensure_rgb(visual).set_audio(audio)
                    
                    fact_captions = self._get_karaoke_clips(filename, audio.duration, 0, font_scale=1.0)
                    fact_video = CompositeVideoClip([visual] + fact_captions, size=(self.width, self.height)).set_duration(audio.duration)
                    
                    clips.append(fact_video.crossfadein(0.5))
                
            # --- PHASE 4: OUTRO ---
            outro_audio_path = self.voice_gen.generate(script_data['outro']['text'], "outro.mp3")
            outro_audio = AudioFileClip(outro_audio_path)
            outro_visual = self._get_visual(script_data['outro']['visual_keyword'], visual_assets, outro_audio.duration)
            outro_visual = self._ensure_rgb(outro_visual).set_audio(outro_audio)
            
            # Outro Text Overlay (Refined Soft CTA)
            # "More untold football stories — FootyBitez"
            outro_captions = self._get_karaoke_clips("outro.mp3", outro_audio.duration, 0, font_scale=1.0)
            
            # Create a simple final card for the last 3-4 seconds
            final_card_dur = 4.0
            final_card_start = max(0, outro_audio.duration - final_card_dur)
            outro_text = self._create_chapter_overlay("FOOTYBITEZ", "MORE UNTOLD STORIES")
            outro_overlay = ImageClip(outro_text).set_duration(final_card_dur).set_start(final_card_start).set_position('center')
            
            outro_combined = CompositeVideoClip([outro_visual, outro_overlay] + outro_captions, size=(self.width, self.height)).set_duration(outro_audio.duration)
            clips.append(outro_combined.crossfadein(0.5))

            # --- CONCATENATE & MIXING ---
            final_video = concatenate_videoclips(clips, method="compose")
            
            # Add Background Music (Looping)
            if background_music_path and os.path.exists(background_music_path):
                music = AudioFileClip(background_music_path).volumex(0.1) # Low volume
                # Loop explicitly to avoid cutoff
                if music.duration < final_video.duration:
                    music = afx.audio_loop(music, duration=final_video.duration)
                else:
                    music = music.subclip(0, final_video.duration)
                
                # Mix audio: Voiceover from video + Background Music
                final_audio = CompositeAudioClip([final_video.audio, music])
                final_video = final_video.set_audio(final_audio)

            # Export
            output_path = os.path.join(self.output_dir, "long_form_video.mp4")
            # Using 'threads' can sometimes cause sync issues or freezing on windows
            # Reduced threads to 4 often fixes freeze at complex joins
            final_video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac", threads=4, logger=None)
            
            return output_path

        except Exception as e:
            logger.error(f"Long-form video creation failed: {e}")
            raise e

    def _get_visual(self, keyword, assets, duration):
        """Fetches visual and applies effects."""
        
        # Use Media Deck first for unique visuals
        path = None
        if hasattr(self, 'media_deck') and self.media_deck:
            path = self.media_deck.pop(0) 
        
        if not path:
             # Fallback to random if deck empty
            segment_media = assets.get('segment_media', [])
            if not segment_media:
                 return ColorClip(size=(self.width, self.height), color=(0,0,0)).set_duration(duration)
            path = random.choice(segment_media)

        if not os.path.exists(path):
            logger.warning(f"Media path does not exist: {path}")
            return ColorClip(size=(self.width, self.height), color=(0,0,0)).set_duration(duration)

        if path.endswith(('.mp4', '.mov')):
            clip = VideoFileClip(path)
            # FORCE MUTE video segments to avoid noise
            clip = clip.without_audio()
            
            if clip.duration is None:
                 pass # Trust moviepy
            
            if clip.duration and clip.duration < duration:
                # Loop
                try:
                    clip = clip.loop(duration=duration)
                except Exception as e:
                    logger.warning(f"Failed to loop clip: {e}. using subclip/color fallback")
                    return ColorClip(size=(self.width, self.height), color=(0,0,0)).set_duration(duration)
            else:
                clip = clip.subclip(0, duration)
            
            # Ensure resizing matches target
            clip = self._resize_to_horizontal(clip)
            return clip.set_duration(duration)
        else:
            # Static Image with Zoom Effect
            clip = ImageClip(path).set_duration(duration)
            clip = self._resize_to_horizontal(clip)
            return self._add_zoom_effect(clip).set_duration(duration)

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

    def _add_blur_effect(self, clip, radius=15):
        """Applies Gaussian Blur to the clip."""
        def filter(image):
            return np.array(Image.fromarray(image).filter(ImageFilter.GaussianBlur(radius)))
        return clip.fl_image(filter)

    def _get_karaoke_clips(self, audio_filename, total_duration, start_time_offset, font_scale=1.0):
        """Creates word-level karaoke caption clips list."""
        import json
        json_path = os.path.join("footybitez/media/voice", audio_filename.replace('.mp3', '.json'))
        
        if not os.path.exists(json_path):
            logger.warning(f"JSON not found for karaoke: {json_path}")
            return []
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                word_data = json.load(f)
            
            if not word_data:
                return []

            # Group words into lines (sentences)
            lines = []
            words_per_line = 4 # Reduced for better sync/visibility
            for i in range(0, len(word_data), words_per_line):
                lines.append(word_data[i:i+words_per_line])

            line_clips = []
            for line in lines:
                l_start = line[0]['start']
                l_end = line[-1]['start'] + line[-1]['duration']
                l_duration = l_end - l_start
                l_content = line
                
                # Factory function for Long-form
                def create_long_clip(current_line, line_start_abs, duration, global_offset):
                    def make_frame(t):
                        absolute_t = line_start_abs + t
                        canvas = Image.new('RGBA', (self.width, 350), (0, 0, 0, 0))
                        draw = ImageDraw.Draw(canvas)
                        
                        # Robust Font Selection
                        font_path = "arialbd.ttf"
                        if os.name == 'nt':
                            candidates = ["C:\\Windows\\Fonts\\arialbd.ttf", "C:\\Windows\\Fonts\\impact.ttf", "arialbd.ttf"]
                        else:
                            candidates = [
                                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                                "arialbd.ttf"
                            ]
                        
                        font = None
                        # Base size 80 * scale
                        base_size = int(80 * font_scale)
                        
                        for cp in candidates:
                            if os.path.exists(cp):
                                try:
                                    font = ImageFont.truetype(cp, base_size)
                                    break
                                except:
                                    continue
                        if not font:
                            font = ImageFont.load_default()

                        full_text = " ".join([w['word'] for w in current_line])
                        bbox = draw.textbbox((0, 0), full_text, font=font)
                        text_w = bbox[2] - bbox[0]
                        
                        # Margin Safety (200px padding each side for 16:9)
                        safe_width = self.width - 400
                        if text_w > safe_width:
                            # Recalculate size to fit
                            new_size = int(base_size * (safe_width / text_w))
                            try:
                                font = ImageFont.truetype(font.path, new_size)
                            except:
                                font = ImageFont.truetype("arialbd.ttf", new_size)
                            bbox = draw.textbbox((0, 0), full_text, font=font)
                            text_w = bbox[2] - bbox[0]

                        start_x = (self.width - text_w) // 2
                        
                        current_x = start_x
                        for word_info in current_line:
                            word = word_info['word'] + " "
                            w_bbox = draw.textbbox((0, 0), word, font=font)
                            w_w = w_bbox[2] - w_bbox[0]
                            
                            # Add 0.05s buffer for sync
                            is_active = word_info['start'] <= (absolute_t + 0.05) <= (word_info['start'] + word_info['duration'] + 0.05)
                            
                            y_pos = 50
                            if is_active:
                                padding = 10
                                draw.rectangle([current_x - padding, y_pos - 5, current_x + w_w + padding, y_pos + 110], fill=(255, 255, 0, 255))
                                draw.text((current_x, y_pos), word, font=font, fill=(0, 0, 0, 255))
                            else:
                                stroke_width = 5
                                for off_x in range(-stroke_width, stroke_width+1):
                                    for off_y in range(-stroke_width, stroke_width+1):
                                        if off_x != 0 or off_y != 0:
                                            draw.text((current_x + off_x, y_pos + off_y), word, font=font, fill=(0, 0, 0, 255))
                                draw.text((current_x, y_pos), word, font=font, fill=(255, 255, 255, 255))
                            current_x += w_w
                        return np.array(canvas)

                    clip = VideoClip(lambda t: make_frame(t)[:,:,:3], duration=duration)
                    mask = VideoClip(lambda t: make_frame(t)[:,:,3]/255.0, ismask=True, duration=duration)
                    return clip.set_mask(mask).set_start(global_offset + line_start_abs).set_position(('center', 780))

                line_clips.append(create_long_clip(l_content, l_start, l_duration, start_time_offset))
            
            return line_clips

        except Exception as e:
            logger.error(f"Failed to create karaoke captions: {e}")
            return []

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

    def _create_chapter_overlay(self, upper_small_text, main_large_text):
        """
        Creates a clean documentary-style text overlay image with strong visual hierarchy.
        
        Args:
            upper_small_text (str): Top line, smaller font (e.g., "FOOTYBITEZ PRESENTS" or "CHAPTER 1").
            main_large_text (str): Main content, larger font (e.g., Topic or Chapter Title).
        """
        img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        try:
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if os.name == 'nt': font_path = "C:\\Windows\\Fonts\\arialbd.ttf"
            
            # HIERARCHY: Main Text = 100%, Upper Text = ~70% of Main (relative visual weight)
            # Actually, User requested: Main 100%, Chapter 70%.
            # Let's set baselines:
            # Main Title Large: 120px
            # Chapter Title: 90px
            # Upper Label ("PRESENTS"/"CHAPTER"): 50px
            
            # Heuristic: Detect if this is Main Title or Chapter based on content?
            # Better: Make the caller decide? For now, I'll infer slightly or use safe defaults.
            
            # Default sizes
            size_upper = 50
            size_main = 100 
            
            font_upper = ImageFont.truetype(font_path, size_upper)
            font_main = ImageFont.truetype(font_path, size_main)
        except:
            font_upper = ImageFont.load_default()
            font_main = ImageFont.load_default()

        import textwrap
        max_width_chars = 20
        wrapped_main = textwrap.wrap(main_large_text.upper(), width=max_width_chars)
        
        def draw_text_centered(text_lines, start_y, font, fill, spacing=20):
            current_y = start_y
            for line in text_lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (self.width - w) // 2
                
                # Stroke
                stroke_w = 4
                for ox in range(-stroke_w, stroke_w+1):
                    for oy in range(-stroke_w, stroke_w+1):
                        draw.text((x+ox, current_y+oy), line, font=font, fill=(0,0,0,255))
                
                draw.text((x, current_y), line, font=font, fill=fill)
                current_y += h + spacing
            return current_y

        # Layout
        # Calculate total height to center vertically
        # Rough estimation
        total_h = 60 + (len(wrapped_main) * 120) 
        start_y = (self.height - total_h) // 2
        
        # Draw Upper Small Text
        y_cursor = draw_text_centered([upper_small_text.upper()], start_y, font_upper, (220, 220, 220, 255))
        
        # Draw Main Large Text
        draw_text_centered(wrapped_main, y_cursor + 30, font_main, (255, 255, 255, 255))
        
        temp_path = os.path.join(self.output_dir, "temp_text", f"overlay_{hash(upper_small_text+main_large_text)}.png")
        img.save(temp_path)
        return temp_path

    def _ensure_rgb(self, clip):
        """Ensures the clip frames are in RGB (3 channels) and explicitly handles masks."""
        if hasattr(clip, 'mask') and clip.mask is not None:
             return clip # Already masked, assume safe
             
        def make_rgb(frame):
            if len(frame.shape) == 2:
                return np.dstack([frame] * 3)
            elif len(frame.shape) == 3:
                if frame.shape[2] == 4:
                    return frame[:,:,:3] # Return RGB
                elif frame.shape[2] == 2:
                    return np.dstack([frame[:,:,0]] * 3)
            return frame

        def make_mask_frame(get_frame, t):
            frame = get_frame(t)
            if len(frame.shape) == 3 and frame.shape[2] == 4:
                return frame[:,:,3] / 255.0
            return np.ones(frame.shape[:2], dtype=float)

        # Check if the clip's first frame is RGBA
        test_frame = clip.get_frame(0)
        if len(test_frame.shape) == 3 and test_frame.shape[2] == 4:
             mask = VideoClip(lambda t: make_mask_frame(clip.get_frame, t), ismask=True, duration=clip.duration)
             clip = clip.fl_image(make_rgb).set_mask(mask)
        else:
             clip = clip.fl_image(make_rgb)
        
        return clip

if __name__ == "__main__":
    pass
