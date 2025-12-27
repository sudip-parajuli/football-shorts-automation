import os
import textwrap
import numpy as np
import random
from PIL import Image, ImageDraw, ImageFont
import warnings

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
from footybitez.media.voice_generator import VoiceGenerator

class VideoCreator:
    def __init__(self, output_dir="footybitez/output"):
        self.output_dir = output_dir
        self.voice_gen = VoiceGenerator()
        os.makedirs(output_dir, exist_ok=True)
        # Helper folder for text images
        os.makedirs(os.path.join(output_dir, "temp_text"), exist_ok=True)

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
                     
                     if img_path.endswith(('.mp4', '.mov')):
                         clip = VideoFileClip(img_path)
                         all_video_clips.append(clip)
                         if clip.duration < duration: clip = clip.loop(duration=duration)
                         else: clip = clip.subclip(0, duration)
                         clip = self._resize_to_vertical(clip)
                         visual_clips.append(self._ensure_rgb(clip))
                     else:
                         clip = ImageClip(img_path).set_duration(duration)
                         # Slow Zoom
                         clip = clip.resize(lambda t: 1 + 0.05 * t/duration)
                         clip = self._resize_to_vertical(clip)
                         visual_clips.append(self._ensure_rgb(clip))
                else:
                    # Segment/Outro - use multiple cuts if long
                    remaining_chunk = duration
                    chunk_visuals = []
                    
                    while remaining_chunk > 0:
                        cut_dur = min(3.0, remaining_chunk)
                        
                        # Decide media: Pick from pool.
                        # Ideally, if this is "segment_0", pick media[0]. 
                        # But we might need multiple cuts for segment_0.
                        # So we rotate through.
                        media_path = segment_media_pool[seg_media_idx % len(segment_media_pool)]
                        seg_media_idx += 1
                        
                        if media_path.endswith(('.mp4', '.mov')):
                            v = VideoFileClip(media_path)
                            all_video_clips.append(v)
                            if v.duration < cut_dur:
                                v = v.loop(duration=cut_dur)
                            else:
                                max_s = v.duration - cut_dur
                                s = 0 if max_s <= 0 else random.uniform(0, max_s)
                                v = v.subclip(s, s+cut_dur)
                            chunk_visuals.append(self._ensure_rgb(self._resize_to_vertical(v)))
                        else:
                            img = ImageClip(media_path).set_duration(cut_dur)
                            img = img.resize(lambda t: 1 + 0.1 * t/cut_dur)
                            chunk_visuals.append(self._ensure_rgb(self._resize_to_vertical(img)))
                            
                        remaining_chunk -= cut_dur
                        
                    visual_clips.extend(chunk_visuals)

            final_video_track = concatenate_videoclips(visual_clips).set_duration(total_duration)

            # 4. Text Overlays (Karaoke)
            text_clips = []
            accumulated_time = 0
            for i, chunk in enumerate(chunks):
                audio_path = audio_paths[i]
                duration = audio_clips[i].duration
                
                is_title = chunk.get('is_title', False)
                if is_title:
                    # Simple title overlay for title card
                    path = self.create_text_image(chunk['text'], fontsize=110, color_scheme="orange")
                    title_clip = ImageClip(path).set_start(accumulated_time).set_duration(duration).set_position('center')
                    # Add subtle zoom to title too
                    title_clip = title_clip.resize(lambda t: 1 + 0.05 * t/duration)
                    text_clips.append(self._ensure_rgb(title_clip))
                else:
                    # Karaoke for segments/outro
                    karaoke = self._create_karaoke_captions(audio_path, duration, accumulated_time)
                    if karaoke:
                        text_clips.append(karaoke)
                
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
                music = AudioFileClip(background_music_path).volumex(0.1)
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
    def _create_karaoke_captions(self, audio_path, total_duration, start_time_offset):
        """Creates word-level karaoke captions for Shorts (Portrait)."""
        import json
        json_path = audio_path.replace('.mp3', '.json')
        
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                word_data = json.load(f)
            
            if not word_data:
                return None

            # Group words into short lines (max 3-4 words for Shorts visibility)
            lines = []
            words_per_line = 4
            for i in range(0, len(word_data), words_per_line):
                lines.append(word_data[i:i+words_per_line])

            line_clips = []
            for line in lines:
                line_start = line[0]['start']
                line_end = line[-1]['start'] + line[-1]['duration']
                line_duration = line_end - line_start
                
                def make_line_frame(t):
                    # t is relative to line_start
                    absolute_t = line_start + t
                    
                    # Create the background image (Portrait width 1080)
                    canvas = Image.new('RGBA', (1080, 400), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(canvas)
                    
                    try:
                        font_path = "C:\\Windows\\Fonts\\impact.ttf"
                        if not os.path.exists(font_path):
                            font_path = "C:\\Windows\\Fonts\\arialbd.ttf"
                        font = ImageFont.truetype(font_path, 85)
                    except:
                        font = ImageFont.load_default()

                    full_text = " ".join([w['word'] for w in line])
                    bbox = draw.textbbox((0, 0), full_text, font=font)
                    text_w = bbox[2] - bbox[0]
                    start_x = (1080 - text_w) // 2
                    
                    # Draw each word
                    current_x = start_x
                    for word_info in line:
                        word = word_info['word'] + " "
                        w_bbox = draw.textbbox((0, 0), word, font=font)
                        w_w = w_bbox[2] - w_bbox[0]
                        
                        # Is this word currently being spoken?
                        is_active = word_info['start'] <= absolute_t <= (word_info['start'] + word_info['duration'])
                        
                        if is_active:
                            # Highlight background yellow
                            draw.rectangle([current_x, 10, current_x + w_w, 130], fill=(255, 255, 0, 255))
                            draw.text((current_x, 10), word, font=font, fill=(0, 0, 0, 255))
                        else:
                            # Standard white text with thick black stroke
                            stroke_width = 6
                            for off_x in range(-stroke_width, stroke_width+1):
                                for off_y in range(-stroke_width, stroke_width+1):
                                    draw.text((current_x + off_x, 10 + off_y), word, font=font, fill=(0, 0, 0, 255))
                            draw.text((current_x, 10), word, font=font, fill=(255, 255, 255, 255))
                        
                        current_x += w_w
                        
                    return np.array(canvas)

                line_clip = VideoClip(make_line_frame, duration=line_duration).set_start(start_time_offset + line_start).set_position(('center', 1400))
                line_clips.append(line_clip)
            
            # Ensure the combined clip has a duration
            combined = CompositeVideoClip(line_clips, size=(1080, 1920))
            return combined.set_duration(total_duration)

        except Exception as e:
            print(f"Failed to create karaoke captions for Shorts: {e}")
            return None

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
        """Ensures the clip frames are in RGB (3 channels) or maintains RGBA with mask."""
        def make_rgb(frame):
            if len(frame.shape) == 2:
                # Grayscale to RGB
                return np.dstack([frame] * 3)
            elif len(frame.shape) == 3:
                if frame.shape[2] == 4:
                    # RGBA: Return as is, CompositeVideoClip will handle the alpha
                    return frame
                elif frame.shape[2] == 2:
                    # Grayscale + Alpha to RGB
                    return np.dstack([frame[:,:,0]] * 3)
                elif frame.shape[2] == 3:
                    return frame
            return frame
        
        # If the clip has a mask, we should preserve it
        return clip.fl_image(make_rgb)


if __name__ == "__main__":
    # Test stub
    pass
