import os
import textwrap
import numpy as np
import random
from PIL import Image, ImageDraw, ImageFont
import warnings

import logging

# Fix for MoviePy + ImageIO v3 deprecation warning
try:
    import imageio
    import imageio.v2 as imageio_v2
except ImportError:
    pass

# Monkeypatch for MoviePy + Pillow 10 compatibility
if not hasattr(Image, 'ANTIALIAS'):
    try:
        from PIL import Image as PILImage
        if hasattr(PILImage, 'Resampling'):
            Image.ANTIALIAS = PILImage.Resampling.LANCZOS
        else:
            Image.ANTIALIAS = 1 # Fallback for old PIL
    except:
        pass

# Suppress DeprecationWarning for ANTIALIAS and ImageIO
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="moviepy")

from moviepy.editor import *
import moviepy.video.fx.all as vfx
from footybitez.media.voice_generator import VoiceGenerator
from footybitez.media.sfx_manager import SFXManager

logger = logging.getLogger(__name__)

class VideoCreator:
    def __init__(self, output_dir="footybitez/output"):
        self.output_dir = output_dir
        self.voice_gen = VoiceGenerator()
        self.sfx_man = SFXManager()
        os.makedirs(output_dir, exist_ok=True)
        # Helper folder for text images
        os.makedirs(os.path.join(output_dir, "temp_text"), exist_ok=True)

    def create_text_image(self, text, fontsize=85, max_width=20, color_scheme="white"):
        """
        Creates a high-visibility text image.
        color_scheme: "white" (default logic) or "orange" (for title cards).
        """
        # ... (rest of method unchanged until next modifications)
        # For this tool call we only update imports and init. 
        # Wait, I need to update the methods where I used print too.
        # I will do that in the "create_video" replacement below.
        
        # ... (skipping to create_video for brevity in this thought trace, 
        # but for the tool call I must act on specific lines.
        # I will split this into two replacement chunks if needed, or one big one if contiguous?
        # They are not contiguous. Imports are at top, create_video is at line 205.
        
        # I will use multi_replace for this.



    def create_text_image(self, text, fontsize=85, max_width=20, color_scheme="white"):
        """
        Creates a high-visibility text image.
        color_scheme: "white" (default logic) or "orange" (for title cards).
        """
        # 1. Parse text (Preserve *highlight*)
        words_styled = []
        raw_words = text.split()
        for word in raw_words:
            # Check for *word*
            if '*' in word:
                clean = word.replace('*', '')
                words_styled.append((clean, "yellow"))
            else:
                words_styled.append((word, color_scheme))

        # Load font (Try heavier fonts)
        font_path = "arialbd.ttf"
        try:
             # Try Impact or Arial Black for maximum visibility
             # Windows Paths
             if os.path.exists("C:\\Windows\\Fonts\\impact.ttf"):
                 font_path = "C:\\Windows\\Fonts\\impact.ttf"
             elif os.path.exists("C:\\Windows\\Fonts\\arialbd.ttf"):
                 font_path = "C:\\Windows\\Fonts\\arialbd.ttf"
             # Linux Paths (GHA)
             elif os.path.exists("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
                 font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
             elif os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
                 font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                 
             print(f"Using font: {font_path}")
             font = ImageFont.truetype(font_path, fontsize)
        except:
             font = ImageFont.load_default()

        # Wrap text manually (Strict limit for max 2-3 lines)
        lines = []
        current_line = []
        current_width = 0
        space_width = 20
        safe_width = 900
        
        dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1,1)))
        
        for word, color in words_styled:
            bbox = dummy_draw.textbbox((0, 0), word, font=font)
            w = bbox[2] - bbox[0]
            
            if current_width + w + space_width > safe_width:
                lines.append(current_line)
                current_line = []
                current_width = 0
            
            current_line.append((word, color, w))
            current_width += w + space_width
            
        if current_line: lines.append(current_line)

        # Draw real text
        img = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Calculate total height
        total_height = 0
        line_heights = []
        for line in lines:
            max_h = 0
            for w, _, _ in line:
                 bbox = draw.textbbox((0, 0), w, font=font)
                 h = bbox[3] - bbox[1]
                 if h > max_h: max_h = h
            line_heights.append(max_h + 30) # Extra leading
            total_height += max_h + 30
            
        current_y = (1920 - total_height) // 2
        # Move up slightly for better visibility over overlay? No, center is best for focus.
        
        # Colors
        COLOR_MAP = {
            "white": (255, 255, 255, 255),
            "yellow": (255, 255, 0, 255), # Pure Bright Yellow
            "orange": (255, 165, 0, 255)  # Title Color
        }
        STROKE_COLOR = (0, 0, 0, 255)
        STROKE_WIDTH = 8 # Thick stroke

        for i, line in enumerate(lines):
            line_total = sum([x[2] for x in line]) + (len(line)-1)*space_width
            start_x = (1080 - line_total) // 2
            
            for word_text, color_key, w in line:
                # Stroke
                for off in range(-STROKE_WIDTH, STROKE_WIDTH+1):
                    for off2 in range(-STROKE_WIDTH, STROKE_WIDTH+1):
                         draw.text((start_x+off, current_y+off2), word_text, font=font, fill=STROKE_COLOR)
                
                # Fill
                draw.text((start_x, current_y), word_text, font=font, fill=COLOR_MAP[color_key])
                start_x += w + space_width
                
            current_y += line_heights[i]

        filename = f"text_{hash(text)}.png"
        path = os.path.join(self.output_dir, "temp_text", filename)
        img.save(path)
        return path

    def parse_vtt(self, vtt_path):
        """
        Parses a WebVTT file and returns a list of (start, end, text) tuples.
        """
        captions = []
        if not os.path.exists(vtt_path):
            return []
            
        with open(vtt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Simple VTT parser (Edge TTS output usually standard)
        # Format:
        # 00:00:00.100 --> 00:00:02.500
        # Text line
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if '-->' in line:
                times = line.split(' --> ')
                start = self._time_str_to_seconds(times[0])
                end = self._time_str_to_seconds(times[1])
                
                # Get text (next line)
                text = ""
                if i + 1 < len(lines):
                    text = lines[i+1].strip()
                    i += 1
                
                captions.append({
                    "start": start,
                    "end": end,
                    "text": text
                })
            i += 1
        return captions

    def _time_str_to_seconds(self, time_str):
        """Robustly converts VTT time string to seconds."""
        try:
            # Handle comma instead of dot for milliseconds
            time_str = time_str.replace(',', '.')
            parts = time_str.split(':')
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + float(s)
            else:
                return float(parts[0])
        except Exception as e:
            print(f"Error parsing time string '{time_str}': {e}")
            return 0.0

    def create_video(self, script_data, visual_assets, background_music_path=None):
        """
        Creates a professional Youtube Short.
        visual_assets: Dict containing 'title_card', 'profile_image', and list of 'segment_media'.
        """
        try:
            # 1. Flatten Script chunks (Hook, Segments, Outro)
            # We treat Hook as the Title Card section
            chunks = []
            
            # Hook
            chunks.append({"type": "hook", "text": script_data.get("hook", ""), "is_title": True})
            
            # Segments
            segments = script_data.get("segments", [])
            for i, seg in enumerate(segments):
                # seg is now dict {text, visual_keyword}
                text = seg['text'] if isinstance(seg, dict) else seg
                chunks.append({"type": f"segment_{i}", "text": text, "is_title": False, "index": i})
            
            # Outro
            chunks.append({"type": "outro", "text": script_data.get("outro", ""), "is_title": False})

            # 2. Generate Audio & VTT
            # 2. Generate Audio
            audio_clips = []
            audio_paths = [] # Store for JSON/VTT lookups
            current_audio_time = 0
            
            for chunk in chunks:
                path = self.voice_gen.generate(chunk['text'], f"{chunk['type']}.mp3")
                audioclip = AudioFileClip(path)
                audio_clips.append(audioclip)
                audio_paths.append(path)
                current_audio_time += audioclip.duration

            final_audio = concatenate_audioclips(audio_clips)
            total_duration = final_audio.duration
            
            # Tracking clips for closure
            all_video_clips = []

            # 3. Create Visual Track
            # Strategy: One visual clip per Chunk duration? Or strictly 3s cuts?
            # User wants "Fast Paced Editing". 
            # Best: For Title Card (Hook) -> Show Title Image.
            # For Segments -> Show Segment Media, cutting every ~3s if segment is long.
            
            visual_clips = []
            current_time = 0
            
            # Prepare media pools
            title_img = visual_assets.get('title_card')
            segment_media_pool = visual_assets.get('segment_media', [])
            # Fallback
            if not segment_media_pool: 
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                segment_media_pool = [os.path.join(base_dir, "media", "images", "placeholder.jpg")]
            
            # We map chunks to time ranges
            chunk_times = []
            t_accum = 0
            for i, clip in enumerate(audio_clips):
                dur = clip.duration
                chunk_times.append({
                    "start": t_accum,
                    "end": t_accum + dur,
                    "type": chunks[i]["type"],
                    "is_title": chunks[i].get("is_title", False),
                    "index": chunks[i].get("index", 0) # segment index
                })
                t_accum += dur

            # Build visual track matching audio chunks
            seg_media_idx = 0
            
            for c_time in chunk_times:
                duration = c_time["end"] - c_time["start"]
                
                if c_time["is_title"]:
                     # Show Title Card
                     img_path = title_img if title_img and os.path.exists(title_img) else segment_media_pool[0]
                     logger.info(f"DEBUG: Title Card: {img_path}, Duration: {duration}")
                     
                     if img_path.endswith(('.mp4', '.mov')):
                         clip = VideoFileClip(img_path).without_audio()
                         all_video_clips.append(clip)
                         if clip.duration < duration: 
                             # Loop video to fill time
                             clip = vfx.loop(clip, duration=duration)
                         else: 
                             clip = clip.subclip(0, duration)
                         clip = self._resize_to_vertical(clip)
                         visual_clips.append(self._ensure_rgb(clip))
                         clip = self._resize_to_vertical(clip)
                         visual_clips.append(self._ensure_rgb(clip))
                     else:
                         clip = ImageClip(img_path).set_duration(duration)
                         
                         # Random Effect for Title Image (Sniper or Glitch or Slow Zoom)
                         effect_choice = random.choice(["sniper", "glitch", "slow_zoom"])
                         if effect_choice == "sniper":
                             clip = self._apply_sniper_zoom(clip)
                         elif effect_choice == "glitch":
                             clip = self._apply_glitch_effect(clip)
                         else:
                             # Slow Zoom
                             clip = clip.resize(lambda t: 1 + 0.05 * t/duration)
                             
                         clip = self._resize_to_vertical(clip)
                         visual_clips.append(self._ensure_rgb(clip))
                         
                     # Title SFX (Dong Only - Bounce handled later)
                     pass # Removed riser_shake as per user request
                     # Removed riser_shake logic.
                     pass
                else:
                    # Segment/Outro - use multiple cuts if long
                    remaining_chunk = duration
                    chunk_visuals = []
                    
                    while remaining_chunk > 0.1: # Threshold to avoid tiny frames
                        cut_dur = min(3.0, remaining_chunk)
                        
                        # Decide media: Pick from pool.
                        media_path = segment_media_pool[seg_media_idx % len(segment_media_pool)]
                        seg_media_idx += 1
                        
                        logger.info(f"DEBUG: Segment Clip: {media_path}, Cut Duration: {cut_dur}")
                        
                        if media_path.endswith(('.mp4', '.mov')):
                            v = VideoFileClip(media_path).without_audio()
                            all_video_clips.append(v)
                            if v.duration < cut_dur:
                                v = vfx.loop(v, duration=cut_dur)
                            else:
                                max_s = v.duration - cut_dur
                                s = 0 if max_s <= 0 else random.uniform(0, max_s)
                                v = v.subclip(s, s+cut_dur)
                            chunk_visuals.append(self._ensure_rgb(self._resize_to_vertical(v)))
                        else:
                            img = ImageClip(media_path).set_duration(cut_dur)
                            
                            # E) Effects Logic
                            is_title = chunk.get('is_title', False)
                            
                            if is_title:
                                # User Request: "use dong SFX and bounce effect to the title"
                                eff = "bounce"
                                sfx_to_use = "dong"
                            else:
                                # Random Effect for normal chunks
                                # REMOVED: alien_invert, sniper (maybe keep visual?), glitch (keep visual?)
                                # User said "No need to use other sfx than that (dong/whoosh)"
                                # Visual effects are fine, but NO SFX strictly.
                                eff = random.choice(["sniper", "glitch", "slow_zoom", "slide_bounce"])
                            
                            if eff == "bounce":
                                # Pulse: Scale 1.0 -> 1.1 -> 1.0
                                img = img.resize(lambda t: 1 + 0.15 * np.sin(np.pi * t/cut_dur)) 
                                
                                # Add Dong SFX (Strictly Requested)
                                if sfx_to_use == "dong":
                                    sfx = self.sfx_man.get_sfx("dong")
                                    if sfx:
                                        sfx = sfx.volumex(0.5)
                                        img = img.set_audio(sfx)
                                        
                            elif eff == "sniper":
                                img = self._apply_sniper_zoom(img)
                            elif eff == "glitch":
                                img = self._apply_glitch_effect(img)

                            chunk_visuals.append(self._ensure_rgb(self._resize_to_vertical(img)))
                            
                            # Add transition SFX (Whoosh ONLY) for NON-Title
                            # We use 'slide_bounce' as the trigger for whoosh.
                            # Alien Invert is REMOVED.
                            if not is_title and eff == "slide_bounce":
                                sfx = self.sfx_man.get_sfx("whoosh")
                                if sfx:
                                    sfx = sfx.subclip(0, 0.5).volumex(0.3)
                                    chunk_visuals[-1] = chunk_visuals[-1].set_audio(sfx)
                            
                            # Removed alien_invert SFX block entirely.
                            
                        remaining_chunk -= cut_dur
                        
                    visual_clips.extend(chunk_visuals)

            # Use method='compose' to avoid IndexError due to floating point duration mismatches
            final_video_track = concatenate_videoclips(visual_clips, method="compose").set_duration(total_duration)

            # 4. Text Overlays (Karaoke)
            text_clips = []
            accumulated_time = 0
            for i, chunk in enumerate(chunks):
                audio_path = audio_paths[i]
                duration = audio_clips[i].duration
                
                is_title = chunk.get('is_title', False)
                if is_title:
                    # Animated Typewriter Title (TextRenderer)
                    from footybitez.video.text_renderer import TextRenderer
                    renderer = TextRenderer()
                    
                    # Create fake timestamped words for title since we don't have word-level timestamps for the hook yet
                    # We just distribute them evenly across the audio duration
                    raw_words = chunk['text'].split()
                    word_duration = duration / max(1, len(raw_words))
                    
                    phrase_data = []
                    for w_idx, w in enumerate(raw_words):
                        phrase_data.append({
                            "word": w,
                            "start": 0 + (w_idx * word_duration), # Relative start
                            "duration": word_duration
                        })
                        
                    # Render
                    # Force GOLD for Title Card (Hook) as requested
                    title_clip = renderer.render_phrase(
                        phrase_data, 
                        duration, 
                        1080, # Shorts Width
                        is_shorts=True,
                        override_color="gold"
                    ).set_start(accumulated_time).set_position('center')
                    
                    text_clips.append(title_clip)
                    text_clips.append(title_clip)
                else:
                    # Karaoke for segments/outro
                    karaoke_clips = self._get_karaoke_clips(audio_path, duration, accumulated_time)
                    text_clips.extend(karaoke_clips)
                
                accumulated_time += duration

            # 5. Profile Overlay (Corner)
            overlays = [final_video_track] + text_clips
            
            profile_img = visual_assets.get('profile_image')
            if profile_img and os.path.exists(profile_img):
                 try:
                    profile_clip = ImageClip(profile_img).set_duration(total_duration)
                    # Resize to 350x350 (Larger)
                    overlay_size = 350
                    profile_clip = profile_clip.resize(height=overlay_size, width=overlay_size)
                    
                    # Circular Mask
                    w, h = profile_clip.size
                    Y, X = np.ogrid[:h, :w]
                    center = (h/2, w/2)
                    mask_arr = ((X - center[1])**2 + (Y-center[0])**2 <= (h/2)**2).astype(np.float32)
                    mask = ImageClip(mask_arr, ismask=True).set_duration(total_duration)
                    profile_clip = self._ensure_rgb(profile_clip).set_mask(mask)
                    
                    profile_clip = profile_clip.set_position(("right", "top")).margin(top=50, right=20, opacity=0)
                    overlays.append(self._ensure_rgb(profile_clip))
                 except Exception as e:
                     print(f"Profile overlay error: {e}")

            # 6. Composite
            final_video = CompositeVideoClip(overlays)
            final_video = final_video.set_audio(final_audio)

            # 7. Music
            if background_music_path and os.path.exists(background_music_path):
                music = AudioFileClip(background_music_path).volumex(0.05) # Lower to 5%
                if music.duration < total_duration:
                    music = afx.audio_loop(music, duration=total_duration)
                else:
                    music = music.subclip(0, total_duration)
                final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, music]))

            # 8. Export
            output_filename = "final_short.mp4"
            output_path = os.path.join(self.output_dir, output_filename)
            final_video.write_videofile(
                output_path, fps=30, codec='libx264', logger=None, audio_codec="aac"
            )
            return output_path
        except Exception as e:
             print(f"Video creation failed: {e}")
             raise e
    def _get_karaoke_clips(self, audio_path, total_duration, start_time_offset, override_color=None):
        """Creates word-level karaoke caption clips using TextRenderer."""
        try:
            print(f"DEBUG: Generating karaoke for {audio_path}...")
            from footybitez.video.text_renderer import TextRenderer
            renderer = TextRenderer()
            
            json_path = audio_path.replace('.mp3', '.json')
            if not os.path.exists(json_path):
                 print(f"DEBUG: JSON missing: {json_path}")
                 return []

            clips = renderer.render_karaoke_clips(
                json_path, 
                total_duration, 
                1080, # Shorts Width 
                1920, # Shorts Height
                is_shorts=True,
                override_color=override_color
            )
            print(f"DEBUG: Renderer returned {len(clips)} clips for {audio_path}")
            
            # Apply global offset
            final_clips = []
            for c in clips:
                # Debug Check
                # print(f"DEBUG: Clip start: {c.start} + {start_time_offset}")
                final_clips.append(c.set_start(c.start + start_time_offset))
                
            return final_clips

        except Exception as e:
            print(f"Failed to create karaoke captions for Shorts: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _resize_to_vertical(self, clip):
        """Resizes and crops a clip to 1080x1920."""
        w, h = clip.size
        # If already vertical/correct aspect, just resize. But usually we crop landscape to portrait.
        # Target 9:16
        target_ratio = 1080 / 1920
        current_ratio = w / h
        
        if current_ratio > target_ratio:
            # Wider than target -> Crop width (sides)
            new_width = int(h * target_ratio)
            # Center crop
            clip = clip.crop(x1=w/2 - new_width/2, width=new_width, height=h)
        else:
            # Taller than target -> Crop height (top/bottom)
            new_height = int(w / target_ratio)
            clip = clip.crop(y1=h/2 - new_height/2, width=w, height=new_height)
            
        return clip.resize((1080, 1920))

    def _ensure_rgb(self, clip):
        """Ensures the clip frames are in RGB (3 channels) and explicitly handles masks."""
        if hasattr(clip, 'mask') and clip.mask is not None:
             return clip # Already masked
             
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


if __name__ == "__main__":
    # Test stub
    pass
