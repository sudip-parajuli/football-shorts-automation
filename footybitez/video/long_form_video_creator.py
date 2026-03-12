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

            # --- PHASE 1: COLD HOOK ---
            # Hook has no text overlay to build mystery, just voice and fast visuals
            if 'hook' in script_data:
                hook_data = script_data['hook']
                hook_audio_path = self.voice_gen.generate(hook_data['narration'], "hook.mp3")
                hook_audio = AudioFileClip(hook_audio_path)
                
                # Fetch paced visuals (cut every ~4s)
                hook_visual = self._get_paced_visuals(hook_data['visual_keyword'], visual_assets, hook_audio.duration)
                hook_visual = self._ensure_rgb(hook_visual).set_audio(hook_audio)
                
                # Add cinematic screen text (centered, large)
                from footybitez.video.text_renderer import TextRenderer
                renderer = TextRenderer()

                if hook_data.get('screen_text'):
                    hook_text_clip = renderer.render_dynamic_overlay(
                        hook_data['screen_text'].upper(), hook_audio.duration, self.width, self.height)
                    
                    hook_combined = CompositeVideoClip([hook_visual, hook_text_clip], size=(self.width, self.height)).set_duration(hook_audio.duration)
                else:
                    hook_combined = hook_visual
                
                clips.append(hook_combined.fadeout(0.5))

            # --- PHASE 2: MAIN TITLE CARD (HERO MOMENT) ---
            # Silent title card with sound effect
            title_bg_keyword = script_data.get('intro', {}).get('visual_keyword', 'football stadium')
            title_visual = self._get_visual(title_bg_keyword, visual_assets, 4.0)
            title_visual = self._add_blur_effect(title_visual, radius=20)
            if not hasattr(title_visual, 'fl'):
                 title_visual = self._add_zoom_effect(title_visual, 0.05)
            
            from footybitez.video.text_renderer import TextRenderer
            renderer = TextRenderer()
            
            presents_clip, type_dur = renderer.render_typewriter_overlay(
                "", "FOOTYBITEZ PRESENTS", 2.0, self.width, self.height, y_pos=150)
            sfx_type = self.sfx_man.get_sfx("typewriter", type_dur).volumex(0.3)
            # Center horizontally, place at specific height
            presents_clip = presents_clip.set_position(('center', 150)).set_audio(sfx_type)

            title_words = script_data['metadata']['title'].split()
            step = 2.5 / max(1, len(title_words))
            phrase_data = [{"word": f"*{word}*", "start": 0.5 + (i * step), "duration": step} for i, word in enumerate(title_words)]
            
            title_anim_clip = renderer.render_phrase(phrase_data, duration=4.0, video_width=self.width, is_shorts=False, override_color="gold").set_position(('center', 350))
            
            sfx_title = self.sfx_man.get_sfx("dong")
            title_card = CompositeVideoClip([title_visual, presents_clip, title_anim_clip], size=(self.width, self.height)).set_duration(4.0)
            
            from moviepy.editor import CompositeAudioClip
            title_audios = []
            if title_card.audio: title_audios.append(title_card.audio)
            if sfx_title: title_audios.append(sfx_title.volumex(0.5).set_start(0))
            if title_audios:
                title_card = title_card.set_audio(CompositeAudioClip(title_audios))
            
            clips.append(title_card.crossfadein(0.5).fadeout(0.5))

            # --- PHASE 3: SPOKEN INTRO ---
            if 'intro' in script_data:
                intro_data = script_data['intro']
                intro_audio_path = self.voice_gen.generate(intro_data['narration'], "intro.mp3")
                intro_audio = AudioFileClip(intro_audio_path)
                intro_visual = self._get_paced_visuals(intro_data['visual_keyword'], visual_assets, intro_audio.duration)
                intro_visual = self._ensure_rgb(intro_visual).set_audio(intro_audio)
                
                if intro_data.get('screen_text'):
                    intro_text_clip = renderer.render_dynamic_overlay(
                        intro_data['screen_text'].upper(), intro_audio.duration, self.width, self.height)
                    
                    intro_combined = CompositeVideoClip([intro_visual, intro_text_clip], size=(self.width, self.height)).set_duration(intro_audio.duration)
                else:
                    intro_combined = intro_visual
                
                clips.append(intro_combined.crossfadein(0.5))
            
            # --- PHASE 4: CHAPTER FLOW ---
            for i, chapter in enumerate(script_data['chapters']):
                chapter_title = chapter['chapter_title']
                
                # A) SILENT CHAPTER TITLE CARD (KICK EFFECT)
                chap_text_clip, type_dur = renderer.render_typewriter_overlay(
                    f"CHAPTER {i+1}", chapter_title.upper(), 2.5, self.width, self.height)
                first_fact_visual = self._get_visual(chapter['facts'][0]['visual_keyword'], visual_assets, 2.5)
                first_fact_visual = self._add_blur_effect(first_fact_visual, radius=15)
                
                chap_slide = CompositeVideoClip([first_fact_visual, chap_text_clip], size=(self.width, self.height)).set_duration(2.5)
                
                sfx_chap = self.sfx_man.get_sfx("whoosh")
                sfx_type = self.sfx_man.get_sfx("typewriter", type_dur).volumex(0.3)
                
                from moviepy.editor import CompositeAudioClip
                audios_to_mix = [sfx_type.set_start(0)]
                if sfx_chap: audios_to_mix.append(sfx_chap.subclip(0, 0.5).volumex(0.3).set_start(0))
                
                chap_slide = chap_slide.set_audio(CompositeAudioClip(audios_to_mix))
                clips.append(chap_slide.fadein(0.1).fadeout(0.3)) 
                
                # B) CHAPTER NARRATION (FACTS)
                for j, fact in enumerate(chapter['facts']):
                    filename = f"chap_{i}_fact_{j}.mp3"
                    audio_path = self.voice_gen.generate(fact['narration'], filename)
                    audio = AudioFileClip(audio_path)
                    
                    visual = self._get_paced_visuals(fact['visual_keyword'], visual_assets, audio.duration)
                    visual = self._ensure_rgb(visual).set_audio(audio)
                    
                    if fact.get('screen_text'):
                        fact_text_clip = renderer.render_dynamic_overlay(
                            fact['screen_text'].upper(), audio.duration, self.width, self.height)
                        
                        fact_video = CompositeVideoClip([visual, fact_text_clip], size=(self.width, self.height)).set_duration(audio.duration)
                    else:
                        fact_video = visual
                    
                    clips.append(fact_video.crossfadein(0.3))
                
                # C) CHAPTER TRANSITION
                if chapter.get('transition'):
                    trans_filename = f"chap_{i}_trans.mp3"
                    trans_audio_path = self.voice_gen.generate(chapter['transition'], trans_filename)
                    trans_audio = AudioFileClip(trans_audio_path)
                    
                    # Uses the last fact's visual background, but darkened/blurred as a bridge
                    trans_visual = self._get_visual("dark shadow aesthetic", visual_assets, trans_audio.duration)
                    trans_visual = self._ensure_rgb(trans_visual).set_audio(trans_audio)
                    
                    clips.append(trans_visual.crossfadein(0.5).fadeout(0.3))

            # --- PHASE 5: OUTRO ---
            if 'outro' in script_data:
                outro_data = script_data['outro']
                outro_audio_path = self.voice_gen.generate(outro_data['narration'], "outro.mp3")
                outro_audio = AudioFileClip(outro_audio_path)
                outro_visual = self._get_paced_visuals(outro_data['visual_keyword'], visual_assets, outro_audio.duration)
                outro_visual = self._ensure_rgb(outro_visual).set_audio(outro_audio)
                
                if outro_data.get('screen_text'):
                    outro_text_clip = renderer.render_dynamic_overlay(
                        outro_data['screen_text'].upper(), outro_audio.duration, self.width, self.height)
                    
                    outro_combined = CompositeVideoClip([outro_visual, outro_text_clip], size=(self.width, self.height)).set_duration(outro_audio.duration)
                else:
                    outro_combined = outro_visual
                    
                clips.append(outro_combined.crossfadein(0.5))

            # --- CONCATENATE & MIXING ---
            final_video = concatenate_videoclips(clips, method="compose")
            
            # Add Background Music (Looping)
            if background_music_path and os.path.exists(background_music_path):
                music = AudioFileClip(background_music_path).volumex(0.03) # Lower volume to 3%
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

    def _get_paced_visuals(self, keyword, assets, total_duration, pace=4.5):
        """
        Creates a single composite clip of `total_duration` by fetching multiple visuals
        and cutting between them every `pace` seconds. Applies random transitions.
        """
        if total_duration <= pace:
            # If the audio is short enough, just return one visual
            return self._get_visual(keyword, assets, total_duration)
            
        paced_clips = []
        time_added = 0.0
        
        while time_added < total_duration:
            # Calculate how much time is left. If it's a tiny sliver (e.g. < 2s), 
            # just make the last clip longer to avoid jarring micro-cuts.
            time_left = total_duration - time_added
            clip_dur = pace if time_left > (pace * 1.5) else time_left
            
            clip = self._get_visual(keyword, assets, clip_dur)
            
            # Phase 7: Advanced Transitions Between Paced Clips
            if len(paced_clips) > 0:
                transition = random.choice(["crossfade", "none", "none"]) # Bias towards hard cuts
                if transition == "crossfade":
                    # Moviepy crossfadein requires the previous clip to overlap. 
                    # For simplicity in a sequential list concatenation, we just fadein the current.
                    clip = clip.fadein(0.3)
                    
            paced_clips.append(clip)
            time_added += clip_dur
            
        return concatenate_videoclips(paced_clips, method="compose").set_duration(total_duration)

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
