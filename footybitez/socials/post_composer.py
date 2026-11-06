"""Source-backed captions and restrained overlays for real football photographs."""
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps


def plain(value):
    return re.sub(r"\s+", " ", re.sub(r"[*_`#]", "", str(value))).strip()


def compose_caption(script):
    paragraphs = [plain(script['hook'])]
    paragraphs += [plain(segment['text']) for segment in script['segments']]
    if script.get('outro'):
        paragraphs.append(plain(script['outro']))
    sources = list(dict.fromkeys(re.findall(r'https?://[^\s\]\)]+', script.get('research_context', ''))))[:2]
    if sources:
        paragraphs.append('Sources: ' + ' '.join(sources))
    paragraphs.append('#football #footballstories #FootyBitez')
    caption = '\n\n'.join(paragraphs)
    if len(caption) > 2000:
        raise ValueError('Caption is too long; regenerate rather than cutting a factual sentence')
    return caption


def load_font(size):
    candidates = [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
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
    draw.rounded_rectangle((82,y-65,318,y-27),radius=8,fill='#d9ff43')
    draw.text((96,y-61),'FOOTBALL STORIES',font=load_font(19),fill='#08111c')
    for line in lines:
        draw.text((82,y),line,font=font,fill='white',stroke_width=1)
        y += size+14
    draw.text((82,1265),'FOOTYBITEZ  /  READ THE CAPTION',font=load_font(22),fill='#d9ff43')
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    image.convert('RGB').save(output,quality=94)
    return str(output)
