import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import VideoClip, ImageClip, CompositeVideoClip

class TextRenderer:
    def __init__(self, font_dir="footybitez/data/fonts"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.font_dir = os.path.join(base_dir, "data", "fonts")
        
        # Expanded Semantic Color Map (No Black)
        self.semantic_colors = {
            "gold": { # SUBJECTS / NAMES (Priority)
                "keywords": [
                    "messi", "ronaldo", "best", "pele", "maradona", "zidane", "cruyff", "puskas", "di stefano", 
                    "platini", "van basten", "gullit", "rijkaard", "maldini", "baresi", "buffon", "neuer", "yashin", 
                    "banks", "moore", "beckenbauer", "matthaus", "xavi", "iniesta", "pirlo", "modric", "kroos", 
                    "busquets", "casemiro", "kante", "makelele", "vieira", "keane", "scholes", "gerrard", "lampard", 
                    "henry", "ronaldinho", "rivaldo", "kaka", "neymar", "suarez", "lewandowski", "benzema", "mbappe", 
                    "haaland", "kane", "salah", "mane", "firmino", "debruyne", "aguero", "rooney", "cantona", 
                    "beckham", "giggs", "ferguson", "wenger", "mourinho", "guardiola", "klopp", "ancelotti", "flick", 
                    "tuchel", "nagelsmann", "ten hag", "arteta", "conte", "allegri", "simerine", "zoff", "facchetti",
                    "scirea", "gento", "kopa", "fontaine", "eusebio", "charlton", "law", "greaves", "rush", "dalglish",
                    "hansen", "souness", "keegan", "robson", "lineker", "shearer", "gascoigne", "owen", "fowler",
                    "mcmanaman", "cole", "yorke", "sheringham", "solskjaer", "schmeichel", "evra", "vidic", "ferdinand",
                    "neville", "carrick", "park", "tevez", "berbatov", "nani", "valencia", "young", "de gea", "mata",
                    "ibrahimovic", "zlatan", "etoo", "drogba", "lampard", "terry", "cech", "cole", "ivanovic", "carvalho",
                    "makelele", "essien", "ballack", "deco", "shevchenko", "torres", "villa", "silva", "aguero", "company",
                    "toure", "hart", "zabaleta", "kolarov", "nasri", "dzeko", "balotelli", "sterling", "sane", "mahrez",
                    "bernardo", "foden", "grealish", "stones", "dias", "walker", "cancelo", "ederson", "alisson", "van dijk",
                    "matip", "konate", "gomez", "robertson", "arnold", "fabinho", "henderson", "thiago", "wijnaldum",
                    "milner", "keitaby", "jones", "elliott", "carvalho", "nunez", "gapko", "diaz", "jota", "origi", "minamino",
                    "shaqiri", "oxlade-chamberlain", "lallana", "lovren", "klavan", "mignolet", "karius", "adrian",
                    "legend", "king", "goat", "god", "boss", "manager", "coach", "captain", "star", "hero", "idol", "icon", "genius"
                ],
                "hex": "#FFD700" # Gold
            },
            "magenta": { # DATES / YEARS (Regex handled separately)
                "keywords": ["year", "date", "time", "history", "record", "world", "cup", "euro", "ucl", "champions", "league"],
                "hex": "#FF00FF" # Magenta
            },
            "red": {
                "keywords": ["attack", "hit", "kill", "destroy", "goal", "score", "fight", "punch", "red", "card", "foul", "injury", "blood", "fire", "danger", "shock", "death", "mad", "crazy", "beast", "monster", "fail", "miss", "bad", "stop", "urgent", "important", "alert", "lose", "defeat", "error", "mistake"],
                "hex": "#FF004D" # Bright Red
            },
            "green": {
                "keywords": ["win", "success", "pass", "safe", "money", "grass", "pitch", "start", "go", "good", "best", "great", "amazing", "approve", "grow", "nature", "victory", "trophy", "title", "cup", "champion", "winner"],
                "hex": "#00FF66" # Neon Green
            },
            "yellow": {
                "keywords": ["yellow", "caution", "warning", "attention", "happy", "smile", "fun", "highlight", "optimism", "wait", "slow", "pause"],
                "hex": "#FFFF00" # Bright Yellow
            },
            "blue": {
                "keywords": ["blue", "calm", "cool", "sky", "sad", "cry", "tears", "cold", "ice", "trust", "stable", "security", "chelsea", "city"],
                "hex": "#00CCFF" # Cyan/Sky Blue
            },
            "white": {
                "keywords": [], 
                "hex": "#FFFFFF"
            }
        }
        
    def _get_font(self, font_name, size):
        font_path = os.path.join(self.font_dir, f"{font_name}.ttf")
        if not os.path.exists(font_path):
            if "Montserrat" in font_name:
                font_path = os.path.join(self.font_dir, "Montserrat-Black.ttf")
            else:
                font_path = os.path.join(self.font_dir, "TheBoldFont.ttf")
                
        try:
            return ImageFont.truetype(font_path, size)
        except Exception as e:
            print(f"ERROR: Failed to load font {font_path}: {e}")
            return ImageFont.load_default()

    def _get_word_style(self, word, base_size):
        # 1. Parse Asterisks (from Script)
        is_highlighted = False
        clean_word = word
        if "*" in word:
            is_highlighted = True
            clean_word = word.replace("*", "")
            
        clean_word_lower = clean_word.lower().strip(",.!?")
        
        # 2. Determine Color
        color = "#FFFFFF" # Default White
        import re
        
        # A) Digits / Time -> Magenta
        # Matches years (1999), simple numbers (7, 100), dates (20th), time (90+5)
        if re.search(r'\d', clean_word):
             color = "#FF00FF" # Magenta for ANY digit-containing word
        
        # B) Highlighted Entity -> Gold (unless it was a number above)
        elif is_highlighted and color == "#FFFFFF":
             color = "#FFD700" # Gold
             
        # C) Keyword Fallback (if not explicitly highlighted or digit)
        elif color == "#FFFFFF":
            # Check Gold Keywords (Legacy list)
            if clean_word_lower in self.semantic_colors['gold']['keywords']:
                 color = self.semantic_colors['gold']['hex']
            else:
                 for cat, data in self.semantic_colors.items():
                    if clean_word_lower in data['keywords']:
                        color = data['hex']
                        break
        
        # 3. Determine Size (Important words get MASSIVE boost)
        is_keyword = (color != "#FFFFFF")
        # 1.5x boost for massive emphasis as requested
        size = int(base_size * 1.5) if is_keyword else base_size
        
        # Stroke always black
        stroke_color = "#000000"
        
        return {
            "color": color,
            "size": size,
            "stroke": stroke_color,
            "font": self._get_font("Montserrat-Black", size)
        }

    def render_phrase(self, phrase_words, duration, video_width, is_shorts=True, override_color=None):
        """
        Renders a CENTERED, HUGE caption clip with Exact-Time Letter-by-Letter Sync.
        Optimized to return a CROPPED clip to save memory.
        """
        # Base Sizing: Requested slightly smaller (100px)
        base_size = 100 if is_shorts else 90
        
        # Calculate Start Time Offset for this phrase
        phrase_start_t = phrase_words[0]['start']
        
        # 1. Stylize Words and Calculate Letter Timings
        styled_words = []
        for w_data in phrase_words:
            # Use original word (with potential asterisks) to determine style
            # If override_color is set (e.g. 'magenta' for Hook), force it.
            style = self._get_word_style(w_data['word'], base_size)
            
            if override_color:
                 # Check if the override is a valid semantic color
                 if override_color in self.semantic_colors:
                     style['color'] = self.semantic_colors[override_color]['hex']
                     # Ensure size boost for colored text
                     style['size'] = int(base_size * 1.3)
                     style['font'] = self._get_font("Montserrat-Black", style['size'])
            
            # Clean word for rendering (remove asterisks)
            word_str = w_data['word'].replace("*", "")
            
            char_duration = w_data['duration'] / max(1, len(word_str))
            word_rel_start = w_data['start'] - phrase_start_t
            
            # Measure Word Size using Clean String
            dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1,1)))
            bbox = dummy_draw.textbbox((0, 0), word_str, font=style['font'])
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            
            styled_words.append({
                "word": word_str,
                "font": style['font'],
                "color": style['color'],
                "stroke_color": style['stroke'],
                "width": w,
                "height": h,
                "size": style['size'],
                "word_rel_start": word_rel_start,
                "char_duration": char_duration
            })

        # 2. Layout Logic (Virtual Canvas)
        lines = []
        current_line = []
        current_line_width = 0
        space = 35 # Increased word spacing
        
        # Safe Width 80% (To FORCE wrapping and prevent cutoff/overlap)
        # Previous 90% was too lenient for massive fonts in Long Form
        safe_max_width = video_width * 0.80
        
        for dw in styled_words:
            if current_line_width + dw['width'] + space > safe_max_width:
                if current_line:
                    lines.append({"words": current_line, "width": current_line_width, "height": max(w['height'] for w in current_line)})
                current_line = [dw]
                current_line_width = dw['width']
            # Bug fix: Previously we added space even for the first word. Fixed logic:
            elif current_line:
                current_line_width += space
                current_line.append(dw)
                current_line_width += dw['width']
            else:
                current_line = [dw]
                current_line_width = dw['width']
                
        if current_line:
            lines.append({"words": current_line, "width": current_line_width, "height": max(w['height'] for w in current_line)})

        # 3. Calculate Virtual Coordinates
        virtual_width = video_width
        virtual_height = 1920 if is_shorts else 1080
        
        # Line Spacing Fix:
        # Use dynamic spacing dependent on Font Height + Padding
        # Previous hardcoded 50 was too small for 100px font + shadow.
        # Max height of line is approx 120px. 
        # Needs at least 150px spacing.
        
        line_spacing = 60 # Vertical gap BETWEEN lines (not total height)
        # So total height for a line is line_height + line_spacing
        
        total_content_height = sum(line['height'] for line in lines) + (len(lines)-1) * line_spacing
        start_y = (virtual_height - total_content_height) // 2
        
        current_y = start_y
        
        letter_render_list = []
        
        min_x, min_y = virtual_width, virtual_height
        max_x, max_y = 0, 0
        
        shadow_dist = 6
        stroke_w = 6
        # Increased padding to prevent Cutouts
        padding = 40 
        
        for line in lines:
            line_w = line['width']
            start_x = (virtual_width - line_w) // 2
            curr_x = start_x
            line_valign_h = line['height']
            
            for word_obj in line['words']:
                y = current_y + (line_valign_h - word_obj['height']) // 2
                
                char_x = curr_x
                font = word_obj['font']
                
                for idx, char in enumerate(word_obj['word']):
                    reveal_time = word_obj['word_rel_start'] + (idx * word_obj['char_duration'])
                    
                    cb = dummy_draw.textbbox((0,0), char, font=font)
                    cw = cb[2] - cb[0]
                    ch = cb[3] - cb[1]
                    advance = font.getlength(char)
                    
                    item = {
                        "char": char,
                        "font": font,
                        "fill": word_obj['color'],
                        "stroke": word_obj['stroke_color'],
                        "x": char_x,
                        "y": y,
                        "reveal_time": reveal_time
                    }
                    letter_render_list.append(item)
                    
                    min_x = min(min_x, char_x - padding)
                    min_y = min(min_y, y - padding)
                    max_x = max(max_x, char_x + cw + padding + shadow_dist)
                    max_y = max(max_y, y + ch + padding + shadow_dist)
                    
                    char_x += advance

                curr_x += word_obj['width'] + space
                
            current_y += line_valign_h + line_spacing
            
        # 4. Create Cropped Canvas
        # Ensure valid dimensions
        if max_x <= min_x or max_y <= min_y:
            # Fallback for empty/weird text
            crop_w, crop_h = 100, 100
            offset_x, offset_y = 0, 0
        else:
            crop_w = int(max_x - min_x)
            crop_h = int(max_y - min_y)
            offset_x = min_x
            offset_y = min_y
            
        # Enforce even dimensions for video codecs often prefer events
        if crop_w % 2 != 0: crop_w += 1
        if crop_h % 2 != 0: crop_h += 1

        # 5. Render Function
        def make_frame(t):
            img = Image.new("RGBA", (crop_w, crop_h), (0,0,0,0))
            draw = ImageDraw.Draw(img)
            
            for l in letter_render_list:
                if t >= l['reveal_time']:
                    # Adjusted coords
                    lx = l['x'] - offset_x
                    ly = l['y'] - offset_y
                    
                    # Shadow
                    draw.text((lx + shadow_dist, ly + shadow_dist), l['char'], font=l['font'], fill="black")
                    
                    # Stroke
                    for ox in range(-stroke_w, stroke_w+1):
                        for oy in range(-stroke_w, stroke_w+1):
                            draw.text((lx+ox, ly+oy), l['char'], font=l['font'], fill="black")
                    
                    # Fill
                    draw.text((lx, ly), l['char'], font=l['font'], fill=l['fill'])
            
            return np.array(img)

        # 6. Create Video Clip
        def get_rgb(t):
            arr = make_frame(t)
            return arr[:,:,:3]
            
        def get_mask(t):
            arr = make_frame(t)
            return arr[:,:,3] / 255.0

        clip = VideoClip(get_rgb, duration=duration)
        mask = VideoClip(get_mask, ismask=True, duration=duration)
        clip = clip.set_mask(mask)
        
        return clip

    def render_karaoke_clips(self, audio_json_path, audio_duration, video_width, video_height, is_shorts=True, override_color=None):
        import json
        if not os.path.exists(audio_json_path):
            return []
            
        with open(audio_json_path, 'r', encoding='utf-8') as f:
            words = json.load(f)
            
        if not words: return []
        
        # Group into phrases
        chunk_size = 3 if is_shorts else 5
        chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
        
        clips = []
        
        for i, chunk in enumerate(chunks):
            start_t = chunk[0]['start']
            
            # Determine end time: 
            # If there is a next chunk, extend to its start (Bridge the gap)
            # Otherwise, use the natural end of the last word + buffer
            if i < len(chunks) - 1:
                next_start = chunks[i+1][0]['start']
                end_t = next_start
            else:
                 word_end = chunk[-1]['start'] + chunk[-1]['duration']
                 end_t = word_end + 0.5 # Small buffer at end of phrase
                 
            dur = end_t - start_t
            
            # Render the phrase clip (It is already full-screen centered)
            txt_clip = self.render_phrase(chunk, dur, video_width, is_shorts, override_color=override_color)
            # Position at (0,0) or center since it's full canvas
            txt_clip = txt_clip.set_start(start_t).set_position('center')
            
            clips.append(txt_clip)
            
        return clips
