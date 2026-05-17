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


def render_quiz_slide(question_text: str, duration_secs: float = 6.0,
                      output_dir: str = "footybitez/output/temp_text"):
    """
    Renders a quiz question as a MoviePy VideoClip (1080x1920, 30fps).
    Answer is intentionally NOT revealed in the video.
    """
    from moviepy.editor import VideoClip
    from PIL import Image, ImageDraw

    os.makedirs(output_dir, exist_ok=True)
    W, H, FPS = 1080, 1920, 30
    DARK_BG = (15, 15, 25)
    WHITE = (255, 255, 255)
    AMBER = (245, 166, 35)

    font_q = _get_font(72)
    font_label = _get_font(48)
    font_hint = _get_font(36)

    def draw_wrapped(draw, text, font, color, y_center, max_width=900):
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
        lh = 95
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
    draw.rectangle([0, 0, W, 10], fill=AMBER)
    draw.text((W // 2 - 55, 35), "QUIZ", font=font_label, fill=AMBER)
    draw_wrapped(draw, question_text, font_q, WHITE, H // 2)
    draw.text((W // 2 - 270, H - 130), "Drop your answer in the comments! 👇", font=font_hint, fill=(160, 160, 160))
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

        self.script_gen = ScriptGenerator()
        self.media_sourcer = MediaSourcer()
        self.video_creator = RemotionVideoCreator()
        self.uploader = YouTubeUploader()

        fd_key = os.getenv("FOOTBALL_DATA_API_KEY", "")
        af_key = os.getenv("API_FOOTBALL_KEY", "")
        self.wc_data = WorldCupData(fd_key, af_key) if fd_key else None

    def run(self, category: str, skip_upload: bool = False):
        today = date.today()
        if not (WC_START <= today <= WC_END):
            logger.info(f"Outside World Cup window ({WC_START}–{WC_END}). Today={today}. Exiting cleanly.")
            sys.exit(0)

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
                 "answer": "Brazil — 5 times (1958, 62, 70, 94, 2002)"},
                {"question": "How many teams play in the 2026 World Cup?",
                 "answer": "48 teams — the biggest ever"},
            ],
            "medium": [
                {"question": "Who holds the record for most World Cup goals?",
                 "answer": "Miroslav Klose — 16 goals across 4 tournaments"},
                {"question": "Which 3 nations co-host the 2026 World Cup?",
                 "answer": "USA, Canada, and Mexico"},
            ],
            "hard": [
                {"question": "Who scored the fastest goal in World Cup history?",
                 "answer": "Hakan Sukur — 11 seconds vs South Korea, 2002"},
                {"question": "What was the score in the 1954 World Cup final?",
                 "answer": "West Germany 3–2 Hungary (Miracle of Bern)"},
            ],
        }
        return [random.choice(pool["easy"]), random.choice(pool["medium"]), random.choice(pool["hard"])]

    def _run_quiz(self, skip_upload=False):
        from moviepy.editor import concatenate_videoclips
        questions = self.generate_wc_quiz()
        clips = [render_quiz_slide(q["question"], duration_secs=6.0) for q in questions]
        clips.append(render_quiz_slide(
            "Did you know them all?\nComment your answers below and we'll reply to let you know if you are right! ⬇️",
            duration_secs=5.0
        ))
        final = concatenate_videoclips(clips, method="compose")
        out = "footybitez/output/wc_quiz.mp4"
        os.makedirs("footybitez/output", exist_ok=True)
        final.write_videofile(out, fps=30, codec="libx264", audio_codec="aac", logger=None)
        if not skip_upload:
            self.uploader.upload_video(
                out,
                "3 World Cup Questions — Do You Know The Answers? 🏆 #shorts #worldcup2026",
                "Test your World Cup knowledge!\nComment your answers and we'll reply with the results!\n\n#worldcup2026 #football #shorts",
                ["worldcup2026", "football", "quiz", "shorts"]
            )
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
            self.uploader.upload_video(
                video_path,
                f"{topic} 🏆 #worldcup2026 #shorts",
                f"{script.get('full_text', '')}\n\n#worldcup2026 #football #shorts #footybitez",
                ["worldcup2026", "football", "soccer", "shorts", "footybitez", category]
            )

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
