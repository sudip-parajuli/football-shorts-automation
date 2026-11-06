"""Local explanatory layouts for narration without suitable documentary photos.

These graphics never impersonate players, match footage, or evidence of events.
"""
import hashlib
from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageFont


def _font(size):
    for path in (
        "remotion-video/public/assets/fonts/BarlowCondensed-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap(draw, text, font, width):
    lines = []
    for word in text.split():
        candidate = (lines[-1] + " " + word) if lines else word
        if lines and draw.textlength(candidate, font=font) <= width:
            lines[-1] = candidate
        else:
            lines.append(word)
    return lines


def make_beat_cards(topic, narration, directory, size=(1080, 1920)):
    clean = re.sub(r"[*\[\]]", "", narration).strip()
    if not clean:
        raise ValueError("Cannot illustrate empty narration")
    words = clean.split()
    chunks = [" ".join(words[index:index + 14]) for index in range(0, len(words), 14)]
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    width, height = size
    portrait = height > width
    scale = width / 1080 if portrait else height / 1080
    margin = round(75 * scale)
    paths = []
    for index, text in enumerate(chunks):
        image = Image.new("RGB", size, "#0b1d23")
        draw = ImageDraw.Draw(image)
        # A restrained pitch-grid background, never a fabricated real-world photo.
        for x in range(0, width, max(1, round(120 * scale))):
            draw.line((x, 0, x, height), fill="#102b31", width=2)
        for y in range(0, height, max(1, round(120 * scale))):
            draw.line((0, y, width, y), fill="#102b31", width=2)
        draw.rounded_rectangle((margin, int(height * .17), width - margin, int(height * .23)), radius=12, fill="#e8c65b")
        draw.text((margin + 20, int(height * .178)), "FOOTBALL EXPLAINED", font=_font(round(38 * scale)), fill="#102329")
        font_size = round((94 if portrait else 98) * scale)
        max_width = width - 2 * margin
        while True:
            font = _font(font_size)
            lines = _wrap(draw, text, font, max_width)
            if len(lines) <= 5 or font_size <= 30:
                break
            font_size -= 4
        y = int(height * (.30 if portrait else .32))
        for line in lines:
            draw.text((margin, y), line, font=font, fill="#f6f5e9")
            y += round(font_size * 1.16)
        # Leave the lower third free for the existing spoken captions.
        draw.text((margin, int(height * .63)), f"BEAT {index + 1:02d} / {len(chunks):02d}", font=_font(round(28 * scale)), fill="#e8c65b")
        draw.text((margin, int(height * (.81 if portrait else .88))), "ILLUSTRATION / NOT MATCH FOOTAGE", font=_font(round(25 * scale)), fill="#9fb6bc")
        digest = hashlib.sha256(f"{topic}|{text}|{size}".encode()).hexdigest()[:16]
        path = directory / f"editorial_{digest}.jpg"
        image.save(path, quality=95)
        paths.append(str(path))
    return paths
