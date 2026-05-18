"""
World Cup 2026 Daily Content Pipeline.

5 content categories: wc_quiz, wc_fact, wc_group_preview, wc_player_spotlight, wc_history

DATE GATE: Python checks if today is within June 11 - July 19, 2026.
The GitHub Actions workflow does NOT date-gate (GitHub expressions can't compare dates).
The script exits cleanly (exit code 0, not failure) outside the window.
"""

import os
import sys
import json
import logging
import random
import numpy as np
from datetime import date
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

WC_START = date(2026, 6, 11)
WC_END = date(2026, 7, 19)

CONTENT_CATEGORIES = [
    "wc_quiz", "wc_fact", "wc_group_preview", "wc_player_spotlight", "wc_history",
]


def _get_font(size: int):
    from PIL import ImageFont
    candidates = [
        "remotion-video/public/assets/fonts/BarlowCondensed-Bold.ttf",
        "C:\\Windows\\Fonts\\impact.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for fp in candidates:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def render_quiz_slide(question_text: str, options: list = None, duration_secs: float = 6.0,
                      output_dir: str = "footybitez/output/temp_text"):
    """
    Renders a quiz question as a MoviePy VideoClip (1080x1920, 30fps).
    Answer is intentionally NOT revealed in the video.
    """
    from moviepy.editor import VideoClip
    from PIL import Image, ImageDraw

    os.makedirs(output_dir, exist_ok=True)
    W, H, FPS = 1080, 1920, 30
    DARK_BG = (18, 18, 30)
    WHITE = (255, 255, 255)
    AMBER = (245, 166, 35)

    font_q = _get_font(64)
    font_label = _get_font(48)
    font_hint = _get_font(38)

    def draw_wrapped(draw, text, font, color, y_center, max_width=920):
        words = text.split()
        lines, current = [], []
        dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        for word in words:
            test = " ".join(current + [word])
            bbox = dummy.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_width and current:
                lines.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            lines.append(" ".join(current))
        lh = 85
        y = y_center - (len(lines) * lh) // 2
        for line in lines:
            bbox = dummy.textbbox((0, 0), line, font=font)
            x = (W - (bbox[2] - bbox[0])) // 2
            draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0))
            draw.text((x, y), line, font=font, fill=color)
            y += lh

    # Build question frame
    q_img = Image.new("RGB", (W, H), DARK_BG)
    draw = ImageDraw.Draw(q_img)
    
    # Beautiful outer top/bottom borders
    draw.rectangle([0, 0, W, 20], fill=AMBER)
    draw.rectangle([0, H - 20, W, H], fill=AMBER)
    
    # Header title (dynamically centered)
    header_text = "WORLD CUP QUIZ"
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox_header = dummy.textbbox((0, 0), header_text, font=font_label)
    header_x = (W - (bbox_header[2] - bbox_header[0])) // 2
    draw.text((header_x, 60), header_text, font=font_label, fill=AMBER)
    
    # Hint text centered just below the header
    hint_text = "Drop your answer in the comments! 👇"
    bbox_hint = dummy.textbbox((0, 0), hint_text, font=font_hint)
    hint_x = (W - (bbox_hint[2] - bbox_hint[0])) // 2
    draw.text((hint_x, 140), hint_text, font=font_hint, fill=(180, 180, 180))
    
    # Render question centered in the top half
    draw_wrapped(draw, question_text, font_q, WHITE, 450)
    
    # Draw Options (if provided)
    if options:
        font_opt = _get_font(42)
        y_start = 800
        box_h = 135
        gap = 35
        for idx, opt in enumerate(options):
            y_box = y_start + idx * (box_h + gap)
            # Alternate outline color for visual premium look
            outline_color = AMBER if idx % 2 == 1 else (100, 100, 180)
            
            # Draw rounded box
            draw.rounded_rectangle(
                [100, y_box, W - 100, y_box + box_h],
                radius=18,
                fill=(28, 28, 48),
                outline=outline_color,
                width=3
            )
            # Draw option text left-padded & vertically centered
            dummy_opt = ImageDraw.Draw(Image.new("RGB", (1, 1)))
            bbox = dummy_opt.textbbox((0, 0), opt, font=font_opt)
            text_h = bbox[3] - bbox[1]
            text_y = y_box + (box_h - text_h) // 2 - 4
            draw.text((140, text_y), opt, font=font_opt, fill=WHITE)

    q_frame = np.array(q_img)


    def make_q_frame(t):
        return q_frame

    return VideoClip(make_q_frame, duration=duration_secs).set_fps(FPS)



class WorldCupPipeline:

    def __init__(self):
        from footybitez.content.script_generator import ScriptGenerator
        from footybitez.media.media_sourcer import MediaSourcer
        from footybitez.video.remotion_video_creator import RemotionVideoCreator
        from footybitez.youtube.uploader import YouTubeUploader
        from footybitez.data.worldcup_data import WorldCupData
        from footybitez.media.voice_generator import VoiceGenerator
        from footybitez.socials.social_orchestrator import SocialOrchestrator

        self.script_gen = ScriptGenerator()
        self.media_sourcer = MediaSourcer()
        self.video_creator = RemotionVideoCreator()
        self.uploader = YouTubeUploader()
        self.voice_gen = VoiceGenerator()
        self.socials = SocialOrchestrator()

        fd_key = os.getenv("FOOTBALL_DATA_API_KEY", "")
        af_key = os.getenv("API_FOOTBALL_KEY", "")
        self.wc_data = WorldCupData(fd_key, af_key) if fd_key else None


    def run(self, category: str, skip_upload: bool = False):
        logger.info(f"WorldCupPipeline: category={category}")
        dispatch = {
            "wc_quiz": self._run_quiz,
            "wc_fact": self._run_fact,
            "wc_group_preview": self._run_group_preview,
            "wc_player_spotlight": self._run_player_spotlight,
            "wc_history": self._run_history,
        }
        fn = dispatch.get(category)
        if not fn:
            logger.error(f"Unknown category: {category}")
            sys.exit(1)
        return fn(skip_upload=skip_upload)

    def generate_wc_quiz(self) -> list:
        """3 questions: easy → medium → hard."""
        pool = {
            "easy": [
                {"question": "Which country has won the most World Cups?",
                 "options": ["A) Germany", "B) Brazil", "C) Italy", "D) Argentina"],
                 "answer": "Brazil — 5 times (1958, 62, 70, 94, 2002)"},
                {"question": "How many teams play in the 2026 World Cup?",
                 "options": ["A) 32 teams", "B) 40 teams", "C) 48 teams", "D) 64 teams"],
                 "answer": "48 teams — the biggest ever"},
            ],
            "medium": [
                {"question": "Who holds the record for most World Cup goals?",
                 "options": ["A) Pele", "B) Ronaldo (R9)", "C) Miroslav Klose", "D) Lionel Messi"],
                 "answer": "Miroslav Klose — 16 goals across 4 tournaments"},
                {"question": "Which 3 nations co-host the 2026 World Cup?",
                 "options": ["A) USA, Canada, Mexico", "B) Brazil, Argentina, Chile", "C) Spain, Portugal, Morocco", "D) Japan, South Korea, China"],
                 "answer": "USA, Canada, and Mexico"},
            ],
            "hard": [
                {"question": "Who scored the fastest goal in World Cup history?",
                 "options": ["A) Clint Dempsey", "B) Hakan Sukur", "C) Bernard Lacombe", "D) Hama Souza"],
                 "answer": "Hakan Sukur — 11 seconds vs South Korea, 2002"},
                {"question": "What was the score in the 1954 World Cup final?",
                 "options": ["A) West Germany 3-2 Hungary", "B) Uruguay 2-1 Brazil", "C) Italy 4-2 Hungary", "D) Brazil 5-2 Sweden"],
                 "answer": "West Germany 3–2 Hungary (Miracle of Bern)"},
            ],
        }
        return [random.choice(pool["easy"]), random.choice(pool["medium"]), random.choice(pool["hard"])]


    def _run_quiz(self, skip_upload=False):
        from moviepy.editor import concatenate_videoclips, AudioFileClip, CompositeAudioClip
        logger.info("Starting professional World Cup Quiz generation with TTS and Music...")
        
        questions = self.generate_wc_quiz()
        clips = []
        
        for i, q in enumerate(questions):
            # Text for TTS voiceover reading
            speak_text = f"Question {i+1}: {q['question']}"
            options = q.get("options", [])
            
            # Generate TTS audio
            audio_path = self.voice_gen.generate(speak_text, f"wc_quiz_q{i}.mp3")
            
            audio_duration = 5.0
            tts_clip = None
            if audio_path and os.path.exists(audio_path):
                tts_clip = AudioFileClip(audio_path)
                audio_duration = tts_clip.duration
            
            # Question slide duration: length of TTS voiceover + 3 seconds thinking pause
            slide_duration = max(audio_duration + 3.0, 6.5)
            
            # Visual slide with beautiful alternating option boxes
            v_clip = render_quiz_slide(q["question"], options=options, duration_secs=slide_duration)
            
            # Add voiceover track to this clip
            if tts_clip:
                v_clip = v_clip.set_audio(tts_clip)
                
            clips.append(v_clip)
            
        # Outro slide
        outro_text = "Did you know them all? Comment your answers below and we'll reply to let you know if you are right!"
        audio_path = self.voice_gen.generate(outro_text, "wc_quiz_outro.mp3")
        
        audio_duration = 5.0
        tts_clip = None
        if audio_path and os.path.exists(audio_path):
            tts_clip = AudioFileClip(audio_path)
            audio_duration = tts_clip.duration
            
        slide_duration = max(audio_duration + 1.5, 5.0)
        outro_clip = render_quiz_slide(
            "Did you know them all?\nComment your answers below and we'll reply to let you know if you are right! ⬇️",
            duration_secs=slide_duration
        )
        if tts_clip:
            outro_clip = outro_clip.set_audio(tts_clip)
        clips.append(outro_clip)
        
        # Concat slides together
        final = concatenate_videoclips(clips, method="compose")
        
        # Mix looping background music
        music_dir = "footybitez/music"
        bg_music = None
        if os.path.exists(music_dir):
            files = [f for f in os.listdir(music_dir) if f.endswith(".mp3")]
            if files:
                bg_music = os.path.join(music_dir, random.choice(files))
                
        if bg_music:
            try:
                from moviepy.editor import vfx
                bg_audio = AudioFileClip(bg_music)
                bg_audio = bg_audio.fx(vfx.loop, duration=final.duration)
                bg_audio = bg_audio.volumex(0.12) # Lower background music volume so voiceover is clear
                
                if final.audio:
                    final.audio = CompositeAudioClip([final.audio, bg_audio])
                else:
                    final.audio = bg_audio
                logger.info("Successfully mixed background music into quiz video.")
            except Exception as e:
                logger.warning(f"Failed to add background music to quiz: {e}")


                
        out = "footybitez/output/wc_quiz.mp4"
        os.makedirs("footybitez/output", exist_ok=True)
        final.write_videofile(out, fps=30, codec="libx264", audio_codec="aac", logger=None)
        
        title = "3 World Cup Questions — Do You Know The Answers? 🏆 #shorts #worldcup2026"
        description = (
            "Test your World Cup knowledge!\n"
            "Comment your answers and we'll reply with the results!\n\n"
            "#worldcup2026 #football #shorts #quiz"
        )
        tags = ["worldcup2026", "football", "quiz", "shorts"]
        
        if not skip_upload:
            logger.info("Attempting upload to YouTube...")
            self.uploader.upload_video(out, title, description, tags)
            
            # Cross-platform publishing to Facebook, Instagram Reels, and TikTok
            should_publish_socials = os.getenv("ENABLE_SOCIAL_PUBLISHING", "false").lower() == "true"
            if should_publish_socials:
                logger.info("Attempting cross-platform upload to Facebook, Instagram, and TikTok...")
                self.socials.publish_to_all(out, title, description)
            else:
                logger.info("Social publishing skipped (ENABLE_SOCIAL_PUBLISHING not true).")
                
        return out


    def _run_fact(self, skip_upload=False):
        facts = [
            "Brazil is the only nation to play in every single World Cup",
            "The fastest goal in World Cup history was scored in 11 seconds",
            "The 1950 World Cup final drew 199,000 spectators — the largest crowd ever",
            "Pele was just 17 years old when he won his first World Cup in 1958",
            "The 2026 World Cup will be the first with 48 teams",
            "Miroslav Klose scored 16 World Cup goals — the all-time record",
        ]
        topic = random.choice(facts)
        script = self.script_gen.generate_script(topic, category="World Cup & Stats")
        return self._produce_and_upload(script, topic, "wc_fact", skip_upload=skip_upload)

    def _run_group_preview(self, skip_upload=False):
        group = random.choice(["A", "B", "C", "D", "E", "F", "G", "H"])
        topic = f"2026 World Cup Group {group} preview — who goes through?"
        script = self.script_gen.generate_script(topic, category="World Cup & Stats")
        return self._produce_and_upload(script, topic, "wc_group_preview", skip_upload=skip_upload)

    def _run_player_spotlight(self, skip_upload=False):
        players = [
            "Kylian Mbappe at Real Madrid World Cup 2026",
            "Erling Haaland Norway World Cup 2026",
            "Jude Bellingham England World Cup 2026",
            "Vinicius Junior Brazil World Cup 2026",
            "Lamine Yamal Spain World Cup 2026",
        ]
        topic = random.choice(players)
        script = self.script_gen.generate_script(topic, category="Football Stories")
        return self._produce_and_upload(script, topic, "wc_player_spotlight", skip_upload=skip_upload)

    def _run_history(self, skip_upload=False):
        topics = [
            "Greatest World Cup upsets in history",
            "Most iconic World Cup goals ever scored",
            "World Cup moments that shocked the world",
            "The curse of the defending World Cup champion",
        ]
        topic = random.choice(topics)
        script = self.script_gen.generate_script(topic, category="World Cup & Stats")
        return self._produce_and_upload(script, topic, "wc_history", skip_upload=skip_upload)

    def _produce_and_upload(self, script, topic, category, skip_upload=False):
        if not script:
            logger.error(f"Script generation failed for: {topic}")
            return None

        title_card = self.media_sourcer.get_title_card_image(f"World Cup 2026 {topic}")
        profile_image = self.media_sourcer.get_profile_image(topic)

        segment_media = []
        for seg in script.get("segments", []):
            kw = seg.get("visual_keyword", topic) if isinstance(seg, dict) else topic
            player_names = ["Mbappe", "Haaland", "Messi", "Ronaldo", "Bellingham", "Vinicius", "Yamal"]
            is_player = any(n in kw for n in player_names)
            if is_player:
                kw = self.media_sourcer._build_ai_image_prompt(kw, is_player_topic=True)
            segment_media.append(self.media_sourcer.get_media(kw, count=2))

        visual_assets = {
            "title_card": title_card,
            "profile_image": profile_image or title_card,
            "segment_media": segment_media,
        }

        music_dir = "footybitez/music"
        bg_music = None
        if os.path.exists(music_dir):
            files = [f for f in os.listdir(music_dir) if f.endswith(".mp3")]
            if files:
                bg_music = os.path.join(music_dir, random.choice(files))

        video_path = self.video_creator.create_video(script, visual_assets, background_music_path=bg_music)
        logger.info(f"Video created: {video_path}")
 
        if not skip_upload:
            title = f"{topic} 🏆 #worldcup2026 #shorts"
            description = f"{script.get('full_text', '')}\n\n#worldcup2026 #football #soccer #shorts #footybitez"
            tags = ["worldcup2026", "football", "soccer", "shorts", "footybitez", category]
            
            logger.info("Attempting upload to YouTube...")
            self.uploader.upload_video(video_path, title, description, tags)
            
            # Cross-platform publishing to Facebook, Instagram Reels, and TikTok
            should_publish_socials = os.getenv("ENABLE_SOCIAL_PUBLISHING", "false").lower() == "true"
            if should_publish_socials:
                logger.info("Attempting cross-platform upload to Facebook, Instagram, and TikTok...")
                self.socials.publish_to_all(video_path, title, description)
            else:
                logger.info("Social publishing skipped (ENABLE_SOCIAL_PUBLISHING not true).")
 
        self.media_sourcer.cleanup()
        return video_path



if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default="wc_fact", choices=CONTENT_CATEGORIES)
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument("--force", action="store_true", help="Bypass date gate for testing")
    args = parser.parse_args()

    if args.force:
        import footybitez.pipelines.worldcup_pipeline as _m
        _m.WC_START = date(2000, 1, 1)
        _m.WC_END = date(2099, 12, 31)

    pipeline = WorldCupPipeline()
    print(pipeline.run(args.category, skip_upload=args.skip_upload))
