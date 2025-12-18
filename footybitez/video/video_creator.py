import os
import textwrap
import numpy as np
import random
from PIL import Image, ImageDraw, ImageFont
import warnings

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

# Suppress DeprecationWarning for ANTIALIAS (comes from MoviePy internals)
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*ANTIALIAS.*")

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
             if os.path.exists("C:\\Windows\\Fonts\\impact.ttf"):
                 font_path = "C:\\Windows\\Fonts\\impact.ttf"
             elif os.path.exists("C:\\Windows\\Fonts\\arialbd.ttf"):
                 font_path = "C:\\Windows\\Fonts\\arialbd.ttf"
                 
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
        # Format: HH:MM:SS.mmm
        try:
            h, m, s = time_str.split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
        except:
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
            audio_clips = []
            caption_data = [] 
            current_audio_time = 0
            
            for chunk in chunks:
                path = self.voice_gen.generate(chunk['text'], f"{chunk['type']}.mp3")
                audioclip = AudioFileClip(path)
                audio_clips.append(audioclip)
                
                # Parse VTT
                vtt_path = path.replace('.mp3', '.vtt')
                chunk_captions = self.parse_vtt(vtt_path)
                
                keywords = [w.strip('*') for w in chunk['text'].split() if w.startswith('*') and w.endswith('*')]
                
                for idx, cap in enumerate(chunk_captions):
                    cap['start'] += current_audio_time
                    cap['end'] += current_audio_time
                    cap['keywords'] = keywords
                    cap['is_title'] = chunk.get('is_title', False)
                    
                    # Fix Gaps
                    if idx < len(chunk_captions) - 1:
                        next_start = chunk_captions[idx+1]['start'] + current_audio_time
                        cap['end'] = next_start
                    else:
                        cap['end'] = current_audio_time + audioclip.duration
                        
                    caption_data.append(cap)
                
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
                         visual_clips.append(clip)
                     else:
                         clip = ImageClip(img_path).set_duration(duration)
                         # Slow Zoom
                         clip = clip.resize(lambda t: 1 + 0.05 * t/duration)
                         clip = self._resize_to_vertical(clip)
                         visual_clips.append(clip)
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
                            chunk_visuals.append(self._resize_to_vertical(v))
                        else:
                            img = ImageClip(media_path).set_duration(cut_dur)
                            img = img.resize(lambda t: 1 + 0.1 * t/cut_dur)
                            chunk_visuals.append(self._resize_to_vertical(img))
                            
                        remaining_chunk -= cut_dur
                        
                    visual_clips.extend(chunk_visuals)

            final_video_track = concatenate_videoclips(visual_clips).set_duration(total_duration)

            # 4. Text Overlays
            text_clips = []
            for cap in caption_data:
                # Title Styling vs Caption Styling
                is_title = cap.get('is_title', False)
                fontsize = 110 if is_title else 90
                
                display_text = cap['text']
                
                # Apply Highlights
                words = display_text.split()
                final_words = []
                for forw in words:
                     final_words.append(forw)
                
                # Actually create_text_video logic for yellow needs * markers.
                # We need to re-apply asterisks based on keywords.
                
                reconstructed_text = []
                for w in words:
                    clean = w.strip('.,!?').replace('*', '') # removing existing just in case
                    if clean in cap['keywords']:
                        reconstructed_text.append(f"*{w}*")
                    else:
                        reconstructed_text.append(w)
                
                final_str = " ".join(reconstructed_text)

                color_scheme = "orange" if is_title else "white"
                txt_img_path = self.create_text_image(final_str, fontsize=fontsize, color_scheme=color_scheme)
                if txt_img_path:
                    dur = cap['end'] - cap['start']
                    if dur < 0.2: dur = 0.5
                    
                    # Position: Center for Title, Bottom-Center for Captions?
                    # For now keep center but maybe adjust y in create_text_image
                    
                    txt_clip = ImageClip(txt_img_path).set_start(cap['start']).set_duration(dur)
                    text_clips.append(txt_clip)

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
                    mask_arr = ((X - center[1])**2 + (Y-center[0])**2 <= (h/2)**2).astype(float)
                    mask = ImageClip(mask_arr, ismask=True).set_duration(total_duration)
                    profile_clip = profile_clip.set_mask(mask)
                    
                    profile_clip = profile_clip.set_position(("right", "top")).margin(top=50, right=20, opacity=0)
                    overlays.append(profile_clip)
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
                output_path, fps=30, codec='libx264', logger=None
            )
            return output_path
        except Exception as e:
             print(f"Video creation failed: {e}")
             raise e
        finally:
            # Cleanup Clips (Release Files)
            try:
                for c in all_video_clips:
                    try: c.close()
                    except: pass
                for c in audio_clips:
                    try: c.close()
                    except: pass
                if 'final_audio' in locals():
                    try: final_audio.close()
                    except: pass
                if 'final_video' in locals():
                    try: final_video.close()
                    except: pass
            except:
                pass

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

if __name__ == "__main__":
    # Test stub
    pass
