"""Measured wrapping shared by raster fallback cards."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont


def fit_text_box(text,width,height,font_paths,maximum=80,minimum=18):
    draw=ImageDraw.Draw(Image.new('RGB',(1,1)))
    font_path=next((str(path) for path in font_paths if Path(path).is_file()),None)
    if not font_path:
        raise ValueError('A TrueType font is required for safe raster text')
    for size in range(maximum,minimum-1,-2):
        font=ImageFont.truetype(font_path,size)
        words=[]
        for word in text.split():
            part=''
            for char in word:
                if part and draw.textlength(part+char,font=font)>width:
                    words.append(part);part=''
                part+=char
            if part:
                words.append(part)
        lines=[]
        for word in words:
            if lines and draw.textlength(lines[-1]+' '+word,font=font)<=width:
                lines[-1]+=' '+word
            else:
                lines.append(word)
        line_height=round(size*1.25)
        if len(lines)*line_height<=height and all(draw.textbbox((0,0),line,font=font)[2]-draw.textbbox((0,0),line,font=font)[0]<=width for line in lines):
            return {'font':font,'lines':lines,'line_height':line_height,'height':len(lines)*line_height}
    raise ValueError('Complete text cannot fit safely in the raster card')
