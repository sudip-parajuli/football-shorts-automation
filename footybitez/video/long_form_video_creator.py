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
            # Audio: Riser Shake SFX
            
            title_text_path = self._create_chapter_overlay("FOOTYBITEZ PRESENTS", script_data['metadata']['title'])
            
            # --- PHASE 1: MAIN TITLE CARD (EXACT-TIME VISUAL TYPEWRITER) ---
            # 1. Background
            title_bg_keyword = script_data.get('intro', {}).get('visual_keyword', 'football stadium')
            title_visual = self._get_visual(title_bg_keyword, visual_assets, 4.0)
            title_visual = self._add_blur_effect(title_visual, radius=20)
            if not hasattr(title_visual, 'fl'):
                 title_visual = self._add_zoom_effect(title_visual, 0.05)
            
            # 2. Render Animated Text (Typewriter + Gold Colors)
            from footybitez.video.text_renderer import TextRenderer
            renderer = TextRenderer()
            
            # Create a fake "phrase" to feed the renderer
            # We want to display: "TOPIC NAME"
            # Split into words for animation
            title_words = script_data['metadata']['title'].split()
            
            # Create timing data (distribute 2.0s duration across words)
            # Start at 0.5s
            start_offset = 0.5
            phrase_duration = 2.5
            step = phrase_duration / max(1, len(title_words))
            
            phrase_data = []
            for i, word in enumerate(title_words):
                phrase_data.append({
                    "word": f"*{word}*", # Force GOLD via asterisk
                    "start": start_offset + (i * step),
                    "duration": step
                })
                
            # Render the animated title clip
            # Render the animated title clip
            # Using shorts=False (1920x1080)
            # Width = 1920
            # Force GOLD for Title
            title_anim_clip = renderer.render_phrase(
                phrase_data, 
                duration=4.0, 
                video_width=self.width, 
                is_shorts=False,
                override_color="gold" 
            ).set_position('center')
            
            # "FOOTYBITEZ PRESENTS" (Small, static above)
            # Kept simple to not distract from main typewriter
            presents_path = self._create_chapter_overlay("", "FOOTYBITEZ PRESENTS") 
            presents_clip = ImageClip(presents_path).set_duration(4.0).set_position(('center', 200)) # Top offset

            # 3. Sheen Effect (Kept but simplified to overlay)
            # Create base RGB clip (discard alpha for color source)
            # We'll re-use the function but just make it a simple overlay that moves across
            # Not masking by text anymore because text is animated/complex.
            # Just a subtle "Light Sweep" across the screen?
            # User asked for "Glowing effect". The renderer already does Gold/Stroke.
            # Let's add a "Flash" or "Bloom" if possible?
            # Or just keep the Sheen logic but apply it to the *whole* title duration?
            # Simpler: Make the typewriter text contain the glow? 
            # The renderer is returning a VideoClip. 
            # Converting it to a Glow is expensive (blurring every frame).
            
            # Let's stick to the Typewriter as the main effect. 
            # Maybe add a "God Ray" or "Spotlight" background?
            # We already have Blur + Zoom background.
            
            # 4. SFX (Dong - Title Reveal)
            sfx_title = self.sfx_man.get_sfx("dong")
            
            title_card = CompositeVideoClip([
                title_visual, 
                title_anim_clip
            ], size=(self.width, self.height)).set_duration(4.0)
            
            if sfx_title:
                sfx_title = sfx_title.volumex(0.5) # Dong can be a bit louder than kick
                title_card = title_card.set_audio(sfx_title)
            
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
                
                # SFX: Whoosh (Slide Effect)
                sfx_chap = self.sfx_man.get_sfx("whoosh")
                
                chap_slide = CompositeVideoClip([
                    first_fact_visual, 
                    ImageClip(chap_text_path).set_duration(2.0).set_position('center')
                ], size=(self.width, self.height)).set_duration(2.0)
                
                # Attach Whoosh SFX
                if sfx_chap:
                    sfx_chap = sfx_chap.subclip(0, 0.5).volumex(0.3)
                    chap_slide = chap_slide.set_audio(sfx_chap.set_start(0))
                
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
            
            # Removed static overlay to avoid overlap with captions
            
            outro_combined = CompositeVideoClip([outro_visual] + outro_captions, size=(self.width, self.height)).set_duration(outro_audio.duration)
            clips.append(outro_combined.crossfadein(0.5))

            # --- CONCATENATE & MIXING ---
            final_video = concatenate_videoclips(clips, method="compose")
            
            # Add Background Music (Looping)
            if background_music_path and os.path.exists(background_music_path):
                music = AudioFileClip(background_music_path).volumex(0.05) # Lower volume (5%)
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
            # Reduced threads to 1 (single threaded) to prevent deadlocks on Windows
            final_video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac", threads=1, logger='bar')
            
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
            # Static Image with Random Effects (Sniper Zoom, Glitch, or Slow Zoom)
            clip = ImageClip(path).set_duration(duration)
            clip = self._resize_to_horizontal(clip)
            
            effect_choice = random.choice(["sniper", "glitch", "slow_zoom", "slow_zoom"]) # Bias towards slow zoom
            
            if effect_choice == "sniper":
                return self._apply_sniper_zoom(clip).set_duration(duration)
            elif effect_choice == "glitch":
                return self._apply_glitch_effect(clip).set_duration(duration)
            else:
                 return self._add_zoom_effect(clip).set_duration(duration)

    def _add_zoom_effect(self, clip, zoom_ratio=0.04):
        """Adds a subtle Ken Burns zoom-in effect."""
        def effect(get_frame, t):
            frame = get_frame(t)
            if len(frame.shape) == 2:
                h, w = frame.shape
            else:
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

    def _apply_sniper_zoom(self, clip):
        """Rapid zoom in/out effect."""
        def effect(get_frame, t):
            frame = get_frame(t)
            
            # Ensure uint8 for PIL
            if frame.dtype != np.uint8:
                 frame = frame.astype(np.uint8)
                 
            h, w = frame.shape[:2]
            
            # Simple Sniper: Fast zoom in and hold
            # 0.0 -> 0.2s: Zoom 1.0 -> 1.5
            # 0.2 -> end: Hold 1.5
            target_zoom = 1.5
            zoom_duration = 0.2
            
            if t < zoom_duration:
                zoom = 1.0 + ((target_zoom - 1.0) * (t / zoom_duration))
            else:
                zoom = target_zoom
                
            # Resize frame
            new_h, new_w = int(h * zoom), int(w * zoom)
            img = Image.fromarray(frame)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            
            # Center Crop
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            img = img.crop((left, top, left + w, top + h))
            return np.array(img)
        return clip.fl(effect)

    def _apply_glitch_effect(self, clip):
        """RGB Channel split glitch."""
        def filter(image):
            # Random chance of glitch per frame? No, makes it too noisy.
            # Constant slight offset?
            # Or randomized offset every few frames.
            
            # For simplicity: Constant RGB split
            # Shift Red channel left, Blue channel right
            rows, cols, chans = image.shape
            if chans < 3: return image
            
            offset = random.randint(5, 20) # Significant jitter
            
            r = np.roll(image[:,:,0], offset, axis=1)
            g = image[:,:,1]
            b = np.roll(image[:,:,2], -offset, axis=1)
            
            # Add some vertical scanline jitter
            if random.random() > 0.8:
                v_offset = random.randint(-10, 10)
                r = np.roll(r, v_offset, axis=0)
                b = np.roll(b, v_offset, axis=0)
                
            return np.dstack((r, g, b))
            
        return clip.fl_image(filter)

    def _get_karaoke_clips(self, audio_filename, total_duration, start_time_offset, font_scale=1.0):
        """Creates word-level karaoke caption clips using TextRenderer."""
        try:
            from footybitez.video.text_renderer import TextRenderer
            renderer = TextRenderer()
            
            # Construct path (assumes caller passes filename in footybitez/media/voice relative path or full?)
            # The caller passes "intro.mp3" or similar.
            # LongFormVideoCreator usage suggests it assumes it is in "footybitez/media/voice"
            # BUT renderer expects full path or correct relative.
            # Let's verify caller.
            # Caller: audio_path = self.voice_gen.generate(...) -> returns full path.
            # Caller: self._get_karaoke_clips("intro.mp3", ...) 
            # Wait, caller passes filename, and original method constructed path:
            # json_path = os.path.join("footybitez/media/voice", audio_filename.replace('.mp3', '.json'))
            
            # New renderer expects full path.
            import os
            base_dir = "footybitez/media/voice"
            json_path = os.path.join(base_dir, audio_filename.replace('.mp3', '.json'))
            
            # Need absolute path usually for file ops if CWD varies?
            # Assuming CWD is project root.
            
            clips = renderer.render_karaoke_clips(
                json_path, 
                total_duration, 
                self.width, 
                self.height,
                is_shorts=False
            )
            
            # Apply global offset
            final_clips = []
            for c in clips:
                final_clips.append(c.set_start(c.start + start_time_offset))
                
            return final_clips

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
