"""Source-backed captions and restrained overlays for real football photographs."""
import re
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

STYLE = json.loads((Path(__file__).resolve().parents[2] / "remotion-video/src/editorialStyle.json").read_text(encoding="utf-8"))


def plain(value):
    return re.sub(r"\s+", " ", re.sub(r"[*_`#]", "", str(value))).strip()


def compose_caption(script, category="football"):
    paragraphs = [plain(script['hook'])]
    paragraphs += [plain(segment['text']) for segment in script['segments']]
    outro = plain(script.get('outro',''))
    if outro and '?' in outro and outro not in paragraphs:
        paragraphs.append(outro)
    cited = [url for segment in script['segments'] for url in segment.get('source_urls', [])]
    sources = list(dict.fromkeys(cited or re.findall(r'https?://[^\s\]\)]+', script.get('research_context', ''))))[:2]
    if sources:
        paragraphs.append('Sources: ' + ' '.join(sources))
    tags = {'coaches':'footballtactics','stats':'footballstats','trophies':'footballhistory',
            'matches':'matchday','results':'matchday','players':'footballplayers','lifestyle':'footballplayers'}
    paragraphs.append(f"#football #{tags.get(category, 'footballstories')} #FootyBitez")
    readable = []
    for paragraph in paragraphs:
        if paragraph in readable:
            continue
        if len(paragraph) <= 350 or paragraph.startswith('Sources:'):
            readable.append(paragraph)
            continue
        current = ''
        for sentence in re.split(r'(?<=[.!?])\s+', paragraph):
            if current and len(current) + len(sentence) > 300:
                readable.append(current)
                current = sentence
            else:
                current = (current + ' ' + sentence).strip()
        if current:
            readable.append(current)
    paragraphs = readable
    caption = '\n\n'.join(paragraphs)
    if len(caption) > 2000:
        raise ValueError('Caption is too long; regenerate rather than cutting a factual sentence')
    return caption


def load_font(size):
    candidates = [Path(__file__).resolve().parents[2] / 'remotion-video/public/assets/fonts/BarlowCondensed-Bold.ttf',
                  Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
                  Path('C:/Windows/Fonts/arialbd.ttf')]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    raise RuntimeError('Install DejaVu Sans or Arial for photo overlays')


def render_overlay(source, title, output):
    title = plain(title)
    if not title or len(title) > 100:
        raise ValueError('Overlay needs a short, complete headline (maximum 100 characters)')
    image = ImageOps.fit(Image.open(source).convert('RGB'), (1080, 1350), centering=(.5, .3)).convert('RGBA')
    shade = Image.new('RGBA', image.size)
    draw = ImageDraw.Draw(shade)
    for y in range(650, 1350):
        draw.line((0,y,1080,y),fill=(5,12,21,int(235*(y-650)/700)))
    image = Image.alpha_composite(image,shade)
    draw = ImageDraw.Draw(image)
    for size in range(86, 35, -2):
        font = load_font(size)
        lines, line = [], ''
        for word in title.split():
            test = (line+' '+word).strip()
            if draw.textlength(test,font=font) > 916 and line:
                lines.append(line)
                line=word
            else:
                line=test
        lines.append(line)
        if len(lines) <= 4 and all(draw.textlength(line,font=font)<=916 for line in lines):
            break
    else:
        raise ValueError('Headline cannot fit safely')
    y = 1200-len(lines)*(size+14)
    draw.rounded_rectangle((82,y-65,318,y-27),radius=8,fill=STYLE['accent'])
    draw.text((96,y-61),'FOOTBALL STORIES',font=load_font(19),fill=STYLE['ink'])
    for line in lines:
        draw.text((82,y),line,font=font,fill=STYLE['paper'],stroke_width=1)
        y += size+14
    draw.text((82,1265),'FOOTYBITEZ  /  READ THE CAPTION',font=load_font(22),fill=STYLE['accent'])
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    image.convert('RGB').save(output,quality=94)
    return str(output)


def _draw_fitted(draw, text, box, maximum, color):
    left, top, width, height = box
    text = plain(text)
    for size in range(maximum, 25, -2):
        font = load_font(size)
        lines = []
        line = ''
        for word in text.split():
            candidate = (line + ' ' + word).strip()
            if line and draw.textlength(candidate, font=font) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        if len(lines) * (size + 12) <= height and all(draw.textlength(line, font=font) <= width for line in lines):
            for line in lines:
                draw.text((left, top), line, font=font, fill=color)
                top += size + 12
            return top
    raise ValueError('Editorial post text exceeds the safe layout')


def render_story_post(title, script, output):
    """An original typographic image with complete, sourced narration excerpts."""
    image = Image.new('RGB', (1080, 1350), STYLE['ink'])
    draw = ImageDraw.Draw(image)
    draw.line((82, 100, 998, 100), fill=STYLE['secondary'], width=3)
    draw.text((82, 126), 'FOOTYBITEZ / THE BRIEF', font=load_font(28), fill=STYLE['accent'])
    _draw_fitted(draw, title, (82, 225, 916, 350), 96, STYLE['paper'])
    segments = script.get('segments', []) if isinstance(script, dict) else []
    for index, segment in enumerate(segments[:2]):
        text = plain(segment['text'])
        y = 670 + index * 240
        draw.text((82, y), f'0{index + 1}', font=load_font(36), fill=STYLE['secondary'])
        _draw_fitted(draw, text, (158, y, 800, 195), 48, STYLE['paper'])
    draw.line((82, 1210, 998, 1210), fill=STYLE['secondary'], width=2)
    draw.text((82, 1250), 'THE CONTEXT IS IN THE CAPTION', font=load_font(28), fill=STYLE['accent'])
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=94)
    return str(output)
