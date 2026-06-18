import os
import re
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)

# Color Palette
DARK_BG = (12, 16, 32)        # Deep Carbon Navy
CARD_BG = (22, 28, 52)        # Slightly lighter navy for cards
ACCENT_BLUE = (116, 172, 223) # Argentina Blue (#74ACDF)
ACCENT_AMBER = (245, 166, 35) # Amber Gold (#F5A623)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (160, 170, 195)
COLOR_GREEN = (46, 204, 113)  # Bright green for wins
COLOR_RED = (231, 76, 60)     # Bright red for losses
COLOR_YELLOW = (241, 196, 15) # Yellow for draws

def _get_font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    """Helper to retrieve a matching font candidate."""
    candidates = [
        "remotion-video/public/assets/fonts/BarlowCondensed-Bold.ttf" if bold else "remotion-video/public/assets/fonts/BarlowCondensed-Regular.ttf",
        "C:\\Windows\\Fonts\\impact.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in candidates:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()

def _create_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Creates a blank 1080x1920 vertical canvas with a premium dark gradient."""
    W, H = 1080, 1920
    img = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(img)
    
    # Draw premium gradient: deep carbon navy (#0A0D1A) top to pitch dark (#05060C) bottom
    for y in range(H):
        r = int(10 - (5 * y / H))
        g = int(13 - (7 * y / H))
        b = int(26 - (14 * y / H))
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))
        
    # Draw a thin amber accent line at the top
    draw.rectangle([0, 0, W, 12], fill=ACCENT_AMBER + (255,))
    
    # Add subtle soccer pitch outline (bottom 1/3 fade-in)
    try:
        # Draw a penalty box at the bottom
        draw.arc([100, H - 400, W - 100, H + 200], 180, 360, fill=(255, 255, 255, 20), width=3)
        draw.rectangle([200, H - 200, W - 200, H], outline=(255, 255, 255, 20), width=3)
    except Exception:
        pass
        
    return img, draw

def _draw_card_frame(draw, title_text: str, subtitle_text: str = ""):
    """Draws standard broadcast header card layout."""
    font_title = _get_font(68, bold=True)
    font_sub = _get_font(38, bold=False)
    
    # Watermark-style logo banner at top
    draw.rectangle([340, 60, 740, 110], fill=(22, 28, 52, 180), outline=ACCENT_AMBER + (100,), width=2)
    draw.text((540, 82), "FIFA WORLD CUP 2026", font=_get_font(28, bold=True), fill=ACCENT_AMBER, anchor="mm")
    
    # Header card title
    draw.text((540, 200), title_text.upper(), font=font_title, fill=COLOR_WHITE, anchor="mm")
    if subtitle_text:
        draw.text((540, 260), subtitle_text.upper(), font=font_sub, fill=ACCENT_BLUE, anchor="mm")

def _draw_team_emblem_placeholder(draw, x_center, y_center, team_name, radius=110):
    """Draws a premium fallback national flag/badge card if no SVG/PNG flag image is on disk."""
    # Draw shadow
    draw.ellipse([x_center - radius - 5, y_center - radius - 5, x_center + radius + 5, y_center + radius + 5], fill=(0, 0, 0, 80))
    # Outer ring
    draw.ellipse([x_center - radius, y_center - radius, x_center + radius, y_center + radius], fill=CARD_BG + (255,), outline=ACCENT_BLUE + (255,), width=6)
    
    # Inner gold border
    draw.ellipse([x_center - radius + 10, y_center - radius + 10, x_center + radius - 10, y_center + radius - 10], fill=(14, 18, 36, 255), outline=ACCENT_AMBER + (255,), width=2)
    
    # Team initial text
    init = team_name.strip()[:3].upper()
    font_text = _get_font(52, bold=True)
    draw.text((x_center, y_center), init, font=font_text, fill=COLOR_WHITE, anchor="mm")

# ─────────────────────────────────────────────────────────────────────────────
# PRE-MATCH SCENE GENERATORS
# ─────────────────────────────────────────────────────────────────────────────

def draw_pre_match_card_1_hook(home: str, away: str, group: str, venue: str, output_path: str):
    """Scene 1: Match title hook card."""
    img, draw = _create_canvas()
    _draw_card_frame(draw, "MATCH PREVIEW", group)
    
    # Draw Home Team Card
    _draw_team_emblem_placeholder(draw, 280, 750, home, radius=130)
    draw.text((280, 930), home.upper(), font=_get_font(56, bold=True), fill=COLOR_WHITE, anchor="mm")
    
    # Draw Away Team Card
    _draw_team_emblem_placeholder(draw, 800, 750, away, radius=130)
    draw.text((800, 930), away.upper(), font=_get_font(56, bold=True), fill=COLOR_WHITE, anchor="mm")
    
    # VS Center Badge
    draw.ellipse([490, 700, 590, 800], fill=ACCENT_AMBER + (255,), outline=COLOR_WHITE + (255,), width=4)
    draw.text((540, 747), "VS", font=_get_font(38, bold=True), fill=DARK_BG, anchor="mm")
    
    # Venue Text
    draw.rounded_rectangle([140, 1100, 940, 1220], radius=15, fill=CARD_BG + (230,), outline=ACCENT_BLUE + (100,), width=2)
    draw.text((540, 1160), f"VENUE: {venue.upper()}", font=_get_font(34, bold=True), fill=COLOR_WHITE, anchor="mm")
    
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    logger.info(f"[CardGen] Saved pre-match Hook card: {output_path}")

def draw_pre_match_card_2_form(home: str, away: str, form_a: str, form_b: str, output_path: str):
    """Scene 2: Team Form guide card."""
    img, draw = _create_canvas()
    _draw_card_frame(draw, "FORM GUIDE", "LAST 5 MATCHES")
    
    def draw_form_row(draw, y_pos, team_name, form_str):
        # Card Background box
        draw.rounded_rectangle([80, y_pos, 1000, y_pos + 280], radius=20, fill=CARD_BG + (230,), outline=ACCENT_BLUE + (80,), width=2)
        
        # Team Name
        draw.text((120, y_pos + 60), team_name.upper(), font=_get_font(46, bold=True), fill=COLOR_WHITE, anchor="ls")
        
        # Parse Form chars, e.g. "W D W L W" or "WWDLW"
        chars = [c.upper() for c in form_str.replace(" ", "")]
        # Pad if short
        while len(chars) < 5:
            chars.append("D")
            
        # Draw Circles
        x_start = 540
        radius = 30
        gap = 25
        for idx, char in enumerate(chars[:5]):
            cx = x_start + idx * (radius * 2 + gap)
            cy = y_pos + 150
            
            # Choose color
            color = COLOR_YELLOW
            if char == "W": color = COLOR_GREEN
            elif char == "L": color = COLOR_RED
            
            # Circle
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color + (255,))
            # Text in circle
            draw.text((cx, cy - 2), char, font=_get_font(32, bold=True), fill=DARK_BG, anchor="mm")
            
    draw_form_row(draw, 500, home, form_a)
    draw_form_row(draw, 880, away, form_b)
    
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    logger.info(f"[CardGen] Saved pre-match Form card: {output_path}")

def draw_pre_match_card_3_h2h(home: str, away: str, h2h_desc: str, output_path: str):
    """Scene 3: Head to Head stat card."""
    img, draw = _create_canvas()
    _draw_card_frame(draw, "HEAD TO HEAD", "HISTORICAL RECORD")
    
    # Outer box
    draw.rounded_rectangle([100, 500, 980, 1180], radius=25, fill=CARD_BG + (230,), outline=ACCENT_AMBER + (100,), width=3)
    
    # Split text or details
    # Parse numbers if we find them in string like "3 Wins, 2 Draws, 1 Loss" or custom H2H record
    matches = re.findall(r'\d+', h2h_desc)
    
    if len(matches) >= 3:
        w1, d, w2 = matches[0], matches[1], matches[2]
    else:
        # Defaults
        w1, d, w2 = "2", "1", "1"
        
    font_huge = _get_font(130, bold=True)
    font_label = _get_font(34, bold=False)
    
    # Left Wins
    draw.text((250, 680), w1, font=font_huge, fill=COLOR_GREEN, anchor="mm")
    draw.text((250, 770), f"{home.upper()} WINS", font=font_label, fill=COLOR_GRAY, anchor="mm")
    
    # Center Draws
    draw.text((540, 680), d, font=font_huge, fill=COLOR_YELLOW, anchor="mm")
    draw.text((540, 770), "DRAWS", font=font_label, fill=COLOR_GRAY, anchor="mm")
    
    # Right Wins
    draw.text((830, 680), w2, font=font_huge, fill=COLOR_GREEN, anchor="mm")
    draw.text((830, 770), f"{away.upper()} WINS", font=font_label, fill=COLOR_GRAY, anchor="mm")
    
    # Details paragraph
    detail_font = _get_font(32, bold=False)
    # Wrap description text
    words = h2h_desc.split()
    lines = []
    curr = []
    for w in words:
        test = " ".join(curr + [w])
        if len(test) < 50:
            curr.append(w)
        else:
            lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))
        
    y_text = 900
    for line in lines[:3]:
        draw.text((540, y_text), line, font=detail_font, fill=COLOR_WHITE, anchor="mm")
        y_text += 45
        
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    logger.info(f"[CardGen] Saved pre-match H2H card: {output_path}")

def draw_pre_match_card_4_probability(home: str, away: str, prob_a: float, prob_draw: float, prob_b: float, output_path: str):
    """Scene 4: Animated win probability card."""
    img, draw = _create_canvas()
    _draw_card_frame(draw, "WIN PROBABILITY", "PREDICTION MODELS")
    
    # Outer box
    draw.rounded_rectangle([80, 500, 1000, 1150], radius=20, fill=CARD_BG + (230,), outline=ACCENT_BLUE + (80,), width=2)
    
    font_pct = _get_font(90, bold=True)
    font_lbl = _get_font(34, bold=True)
    
    # Safe float conversion
    try:
        f_a = float(prob_a)
    except (ValueError, TypeError):
        f_a = 33.0
    try:
        f_draw = float(prob_draw)
    except (ValueError, TypeError):
        f_draw = 34.0
    try:
        f_b = float(prob_b)
    except (ValueError, TypeError):
        f_b = 33.0

    if f_a < 0: f_a = 0.0
    if f_draw < 0: f_draw = 0.0
    if f_b < 0: f_b = 0.0

    total_prob = f_a + f_draw + f_b
    if total_prob <= 0:
        f_a, f_draw, f_b = 33.0, 34.0, 33.0
        total_prob = 100.0

    # Draw Boxes
    draw.rounded_rectangle([120, 580, 390, 820], radius=15, fill=(14, 18, 36, 200))
    draw.text((255, 660), f"{int(f_a)}%", font=font_pct, fill=COLOR_GREEN, anchor="mm")
    draw.text((255, 750), home.upper(), font=font_lbl, fill=COLOR_WHITE, anchor="mm")
    
    draw.rounded_rectangle([425, 580, 655, 820], radius=15, fill=(14, 18, 36, 200))
    draw.text((540, 660), f"{int(f_draw)}%", font=font_pct, fill=COLOR_YELLOW, anchor="mm")
    draw.text((540, 750), "DRAW", font=font_lbl, fill=COLOR_WHITE, anchor="mm")
    
    draw.rounded_rectangle([690, 580, 960, 820], radius=15, fill=(14, 18, 36, 200))
    draw.text((825, 660), f"{int(f_b)}%", font=font_pct, fill=ACCENT_AMBER, anchor="mm")
    draw.text((825, 750), away.upper(), font=font_lbl, fill=COLOR_WHITE, anchor="mm")
    
    # Draw continuous horizontal bar representing the splits
    bar_x1, bar_y1, bar_x2, bar_y2 = 120, 950, 960, 1010
    total_w = bar_x2 - bar_x1
    
    # Calculations
    w_a = int(total_w * (f_a / total_prob))
    w_draw = int(total_w * (f_draw / total_prob))
    w_b = total_w - w_a - w_draw
    
    # Team A bar (green)
    draw.rounded_rectangle([bar_x1, bar_y1, bar_x1 + w_a, bar_y2], radius=8, fill=COLOR_GREEN + (255,))
    # Draw bar (yellow)
    draw.rectangle([bar_x1 + w_a, bar_y1, bar_x1 + w_a + w_draw, bar_y2], fill=COLOR_YELLOW + (255,))
    # Team B bar (amber)
    draw.rounded_rectangle([bar_x1 + w_a + w_draw, bar_y1, bar_x2, bar_y2], radius=8, fill=ACCENT_AMBER + (255,))
    
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    logger.info(f"[CardGen] Saved pre-match win probability card: {output_path}")

def draw_pre_match_card_5_spotlight(player: str, team: str, stats_desc: str, output_path: str):
    """Scene 5: Player Spotlight card."""
    img, draw = _create_canvas()
    _draw_card_frame(draw, "PLAYER TO WATCH", team)
    
    # Spotlight frame card
    draw.rounded_rectangle([100, 480, 980, 1250], radius=25, fill=CARD_BG + (230,), outline=ACCENT_AMBER + (100,), width=3)
    
    # Profile pic circle/card placeholder
    draw.rounded_rectangle([390, 540, 690, 840], radius=35, fill=(14, 18, 36, 255), outline=ACCENT_AMBER + (255,), width=4)
    # Initial representation
    draw.text((540, 690), player.strip()[:2].upper(), font=_get_font(90, bold=True), fill=COLOR_WHITE, anchor="mm")
    
    # Player Name
    draw.text((540, 920), player.upper(), font=_get_font(54, bold=True), fill=COLOR_WHITE, anchor="mm")
    # Player Team
    draw.text((540, 980), team.upper(), font=_get_font(32, bold=False), fill=ACCENT_BLUE, anchor="mm")
    
    # Stat callout
    draw.rounded_rectangle([200, 1050, 880, 1180], radius=15, fill=(14, 18, 36, 200), outline=ACCENT_BLUE + (100,), width=2)
    draw.text((540, 1115), stats_desc.upper(), font=_get_font(36, bold=True), fill=ACCENT_AMBER, anchor="mm")
    
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    logger.info(f"[CardGen] Saved pre-match Player Spotlight card: {output_path}")

def draw_pre_match_card_6_cta(home: str, away: str, output_path: str):
    """Scene 6: Bold prediction call to action card."""
    img, draw = _create_canvas()
    _draw_card_frame(draw, "WHO WINS?", "MAKE YOUR CALL")
    
    # Main big prompt box
    draw.rounded_rectangle([100, 500, 980, 1100], radius=30, fill=CARD_BG + (230,), outline=ACCENT_AMBER + (255,), width=4)
    
    draw.text((540, 650), f"{home.upper()} OR {away.upper()}?", font=_get_font(52, bold=True), fill=COLOR_WHITE, anchor="mm")
    draw.text((540, 770), "DROP YOUR PREDICTION", font=_get_font(46, bold=True), fill=ACCENT_AMBER, anchor="mm")
    draw.text((540, 840), "IN THE COMMENTS BELOW! 👇", font=_get_font(38, bold=False), fill=COLOR_WHITE, anchor="mm")
    
    # Bottom Subscribe block
    draw.rounded_rectangle([180, 1250, 900, 1370], radius=15, fill=ACCENT_BLUE + (255,))
    draw.text((540, 1310), "SUBSCRIBE FOR DAILY WORLD CUP RECALS! 🏆", font=_get_font(30, bold=True), fill=DARK_BG, anchor="mm")
    
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    logger.info(f"[CardGen] Saved pre-match CTA card: {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# POST-MATCH SCENE GENERATORS
# ─────────────────────────────────────────────────────────────────────────────

def draw_post_match_card_1_score(home: str, away: str, hs: int, as_: int, stage: str, output_path: str):
    """Scene 1: Match Scoreline splash card."""
    img, draw = _create_canvas()
    _draw_card_frame(draw, "MATCH RESULT", stage)
    
    # Home Team
    _draw_team_emblem_placeholder(draw, 280, 750, home, radius=130)
    draw.text((280, 930), home.upper(), font=_get_font(56, bold=True), fill=COLOR_WHITE, anchor="mm")
    
    # Away Team
    _draw_team_emblem_placeholder(draw, 800, 750, away, radius=130)
    draw.text((800, 930), away.upper(), font=_get_font(56, bold=True), fill=COLOR_WHITE, anchor="mm")
    
    # Score Box
    draw.rounded_rectangle([440, 700, 640, 800], radius=20, fill=ACCENT_AMBER + (255,), outline=COLOR_WHITE + (255,), width=4)
    draw.text((540, 747), f"{hs} - {as_}", font=_get_font(56, bold=True), fill=DARK_BG, anchor="mm")
    
    # FT status box
    draw.rounded_rectangle([420, 1050, 660, 1130], radius=10, fill=CARD_BG + (255,), outline=ACCENT_BLUE + (150,), width=2)
    draw.text((540, 1090), "FULL TIME", font=_get_font(32, bold=True), fill=COLOR_WHITE, anchor="mm")
    
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    logger.info(f"[CardGen] Saved post-match Score card: {output_path}")

def draw_post_match_card_2_timeline(home: str, away: str, scorers: list, output_path: str):
    """Scene 2: Goals Timeline card."""
    img, draw = _create_canvas()
    _draw_card_frame(draw, "GOALS TIMELINE", "SCORERS & KEY MOMENTS")
    
    # Timeline box
    draw.rounded_rectangle([100, 480, 980, 1250], radius=25, fill=CARD_BG + (230,), outline=ACCENT_BLUE + (80,), width=2)
    
    # Draw center line
    draw.line([(540, 540), (540, 1180)], fill=COLOR_GRAY + (100,), width=4)
    
    y_offset = 580
    # scorers format: list of dicts with {"type": "Goal", "player": "Name", "minute": 12, "team": "Home"/"Away"}
    # limit to top 6 events
    for ev in scorers[:6]:
        team = ev.get("team", "Home")
        player = ev.get("player", "")
        minute = ev.get("minute", 0)
        ev_type = ev.get("type", "Goal")
        detail = ev.get("detail", "")
        
        # Determine center circle indicator color
        circ_color = COLOR_GREEN if ev_type == "Goal" else COLOR_RED
        if detail == "Yellow Card": circ_color = COLOR_YELLOW
        
        # Center Node
        draw.ellipse([520, y_offset - 20, 560, y_offset + 20], fill=circ_color + (255,))
        # Text inside center node
        draw.text((540, y_offset - 2), f"{minute}'", font=_get_font(22, bold=True), fill=DARK_BG, anchor="mm")
        
        # Content layout
        if team == "Home":
            draw.text((500, y_offset - 2), player.upper(), font=_get_font(28, bold=True), fill=COLOR_WHITE, anchor="rm")
            # draw icon label next to name
            if ev_type == "Goal":
                draw.text((500, y_offset + 20), "⚽ GOAL", font=_get_font(20, bold=False), fill=COLOR_GREEN, anchor="rm")
            else:
                draw.text((500, y_offset + 20), detail.upper(), font=_get_font(20, bold=False), fill=circ_color, anchor="rm")
        else:
            draw.text((580, y_offset - 2), player.upper(), font=_get_font(28, bold=True), fill=COLOR_WHITE, anchor="lm")
            if ev_type == "Goal":
                draw.text((580, y_offset + 20), "⚽ GOAL", font=_get_font(20, bold=False), fill=COLOR_GREEN, anchor="lm")
            else:
                draw.text((580, y_offset + 20), detail.upper(), font=_get_font(20, bold=False), fill=circ_color, anchor="lm")
                
        y_offset += 100
        
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    logger.info(f"[CardGen] Saved post-match Timeline card: {output_path}")

def draw_post_match_card_3_stats(home: str, away: str, stats_dict: dict, output_path: str):
    """Scene 3: Match stats comparison charts card."""
    img, draw = _create_canvas()
    _draw_card_frame(draw, "MATCH STATISTICS", "KEY PERFORMANCE INDICATORS")
    
    # outer box
    draw.rounded_rectangle([80, 480, 1000, 1250], radius=25, fill=CARD_BG + (230,), outline=ACCENT_BLUE + (80,), width=2)
    
    # We display up to 4 major stats side by side, e.g. Possession, Shots, Shots on Target, Expected Goals
    # stats_dict format: {"possession": {"home": "60%", "away": "40%"}, "shots": {"home": 14, "away": 8}, etc.}
    stats_list = [
        {"key": "possession", "label": "POSSESSION"},
        {"key": "shots", "label": "TOTAL SHOTS"},
        {"key": "shots_on_target", "label": "SHOTS ON TARGET"},
        {"key": "corners", "label": "CORNER KICKS"},
    ]
    
    y_pos = 540
    for stat in stats_list:
        key = stat["key"]
        label = stat["label"]
        
        # Get values
        pair = stats_dict.get(key, {"home": "0", "away": "0"})
        val_a = str(pair.get("home", "0"))
        val_b = str(pair.get("away", "0"))
        
        # Draw Label in center
        draw.text((540, y_pos), label, font=_get_font(30, bold=True), fill=ACCENT_BLUE, anchor="mm")
        
        # Draw Values
        draw.text((150, y_pos), val_a, font=_get_font(42, bold=True), fill=COLOR_WHITE, anchor="mm")
        draw.text((930, y_pos), val_b, font=_get_font(42, bold=True), fill=COLOR_WHITE, anchor="mm")
        
        # Clean values for bars (strip % sign if present)
        try:
            num_a = float(val_a.replace("%", "").strip())
            num_b = float(val_b.replace("%", "").strip())
        except ValueError:
            num_a, num_b = 0, 0
            
        total = num_a + num_b
        pct_a = num_a / total if total > 0 else 0.5
        pct_b = num_b / total if total > 0 else 0.5
        
        # Draw horizontal split bars
        bar_y1, bar_y2 = y_pos + 30, y_pos + 46
        bar_len = 340
        
        # Left bar (fills to left)
        len_a = int(bar_len * pct_a)
        draw.rounded_rectangle([350 - len_a, bar_y1, 350, bar_y2], radius=4, fill=COLOR_GREEN + (255,))
        # Right bar (fills to right)
        len_b = int(bar_len * pct_b)
        draw.rounded_rectangle([730, bar_y1, 730 + len_b, bar_y2], radius=4, fill=ACCENT_AMBER + (255,))
        
        y_pos += 160
        
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    logger.info(f"[CardGen] Saved post-match Stats card: {output_path}")

def draw_post_match_card_4_motm(player: str, team: str, rating: float, stat_desc: str, output_path: str):
    """Scene 4: Man of the match card."""
    img, draw = _create_canvas()
    _draw_card_frame(draw, "MAN OF THE MATCH", team)
    
    # MOTM card frame
    draw.rounded_rectangle([100, 480, 980, 1250], radius=25, fill=CARD_BG + (230,), outline=ACCENT_AMBER + (255,), width=4)
    
    # Glow ring on profile pic
    draw.ellipse([390, 540, 690, 840], fill=(14, 18, 36, 255), outline=ACCENT_AMBER + (255,), width=6)
    # Initials representation
    draw.text((540, 690), player.strip()[:2].upper(), font=_get_font(90, bold=True), fill=COLOR_WHITE, anchor="mm")
    
    # MOTM Rating Badge
    draw.rounded_rectangle([590, 520, 710, 600], radius=15, fill=COLOR_GREEN + (255,), outline=COLOR_WHITE + (255,), width=3)
    draw.text((650, 560), f"{rating:.1f}", font=_get_font(34, bold=True), fill=DARK_BG, anchor="mm")
    
    # Player Name
    draw.text((540, 920), player.upper(), font=_get_font(54, bold=True), fill=COLOR_WHITE, anchor="mm")
    # Player Team
    draw.text((540, 980), team.upper(), font=_get_font(32, bold=False), fill=ACCENT_BLUE, anchor="mm")
    
    # Stat callout
    draw.rounded_rectangle([180, 1050, 900, 1180], radius=15, fill=(14, 18, 36, 200), outline=ACCENT_AMBER + (100,), width=2)
    draw.text((540, 1115), stat_desc.upper(), font=_get_font(36, bold=True), fill=ACCENT_AMBER, anchor="mm")
    
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    logger.info(f"[CardGen] Saved post-match MOTM card: {output_path}")

def draw_post_match_card_5_standings(group: str, standings_list: list, output_path: str):
    """Scene 5: Group Standings table card."""
    img, draw = _create_canvas()
    _draw_card_frame(draw, "GROUP STANDINGS", group)
    
    # table box
    draw.rounded_rectangle([80, 480, 1000, 1250], radius=25, fill=CARD_BG + (230,), outline=ACCENT_BLUE + (80,), width=2)
    
    font_header = _get_font(32, bold=True)
    font_cell = _get_font(36, bold=False)
    font_bold_cell = _get_font(36, bold=True)
    
    # Header row
    draw.text((120, 540), "POS  TEAM", font=font_header, fill=ACCENT_BLUE, anchor="ls")
    draw.text((620, 540), "PL", font=font_header, fill=ACCENT_BLUE, anchor="ms")
    draw.text((740, 540), "GD", font=font_header, fill=ACCENT_BLUE, anchor="ms")
    draw.text((880, 540), "PTS", font=font_header, fill=ACCENT_BLUE, anchor="ms")
    
    draw.line([(100, 560), (960, 560)], fill=COLOR_GRAY + (100,), width=3)
    
    # Row loop (standings_list has dicts with {"pos": 1, "team": "Argentina", "played": 3, "gd": "+5", "pts": 7})
    y_offset = 640
    for idx, row in enumerate(standings_list[:4]):
        pos = row.get("pos", idx + 1)
        team = row.get("team", "")
        played = row.get("played", 0)
        gd = row.get("gd", "0")
        pts = row.get("pts", 0)
        
        # Color highlight top 2 teams (qualification zone)
        txt_color = COLOR_WHITE if pos <= 2 else COLOR_GRAY
        
        # Draw Rank
        draw.text((140, y_offset), f"{pos}", font=font_bold_cell, fill=ACCENT_AMBER if pos <= 2 else COLOR_GRAY, anchor="ms")
        # Draw Team Name
        draw.text((220, y_offset), team.upper(), font=font_bold_cell if pos <= 2 else font_cell, fill=txt_color, anchor="ls")
        # Draw Played
        draw.text((620, y_offset), f"{played}", font=font_cell, fill=txt_color, anchor="ms")
        # Draw Goal Difference
        draw.text((740, y_offset), f"{gd}", font=font_cell, fill=COLOR_GREEN if str(gd).startswith("+") else (COLOR_RED if str(gd).startswith("-") else txt_color), anchor="ms")
        # Draw Points
        draw.text((880, y_offset), f"{pts}", font=font_bold_cell, fill=COLOR_GREEN if pos <= 2 else txt_color, anchor="ms")
        
        draw.line([(100, y_offset + 30), (960, y_offset + 30)], fill=COLOR_GRAY + (40,), width=1)
        y_offset += 130
        
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    logger.info(f"[CardGen] Saved post-match Standings card: {output_path}")

def draw_post_match_card_6_next(home: str, away: str, next_match_desc: str, output_path: str):
    """Scene 6: Next Match Teaser card."""
    img, draw = _create_canvas()
    _draw_card_frame(draw, "UPCOMING FIXTURE", "WORLD CUP 2026")
    
    # Outer box
    draw.rounded_rectangle([100, 500, 980, 1100], radius=30, fill=CARD_BG + (230,), outline=ACCENT_AMBER + (255,), width=4)
    
    draw.text((540, 620), "NEXT MATCH FOR TEAMS:", font=_get_font(36, bold=False), fill=COLOR_GRAY, anchor="mm")
    
    draw.text((540, 730), f"{home.upper()} OR {away.upper()}?", font=_get_font(48, bold=True), fill=COLOR_WHITE, anchor="mm")
    
    # Info badge
    draw.rounded_rectangle([180, 830, 900, 980], radius=15, fill=(14, 18, 36, 255), outline=ACCENT_BLUE + (100,), width=2)
    
    # Wrap text if long
    desc_words = next_match_desc.split()
    desc_lines = []
    curr = []
    for w in desc_words:
        test = " ".join(curr + [w])
        if len(test) < 40:
            curr.append(w)
        else:
            desc_lines.append(" ".join(curr))
            curr = [w]
    if curr:
        desc_lines.append(" ".join(curr))
        
    y_desc = 885
    for line in desc_lines[:2]:
        draw.text((540, y_desc), line.upper(), font=_get_font(28, bold=True), fill=ACCENT_AMBER, anchor="mm")
        y_desc += 40
        
    # Subscribe prompt
    draw.rounded_rectangle([180, 1250, 900, 1370], radius=15, fill=ACCENT_BLUE + (255,))
    draw.text((540, 1310), "SUBSCRIBE FOR ALL WORLD CUP RECALS! 🏆", font=_get_font(30, bold=True), fill=DARK_BG, anchor="mm")
    
    img.convert("RGB").save(output_path, "JPEG", quality=95)
    logger.info(f"[CardGen] Saved post-match Next Match card: {output_path}")
