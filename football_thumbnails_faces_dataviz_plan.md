# Football Channel — Thumbnail Redesign + Face Restriction + Data Visualization
## Complete Implementation Plan

---

## Part 1: Thumbnail Redesign (Upgrade from Current)

The current football channel thumbnails use simple design. We'll upgrade to a formula-based system matching the successful science channel model but with football-specific accent colors (amber #F5A623, dark red #C0392B).

### 1.1 Thumbnail Generation Rules

**When to use AI-generated thumbnail vs. real image:**

```
✅ USE AI-GENERATED:
  - Tactical diagrams (tiki-taka formations, pressing patterns, heat maps)
  - Abstract concepts (passion, speed, transformation, tactics)
  - Visual data representations (graphs, charts, player stat visualizations)
  - Atmospheric scenes (stadium energy, crowd, weather conditions)
  
❌ NEVER USE AI-GENERATED:
  - Real named players (faces will be wrong/hallucinated)
  - Real managers/coaches (faces will be wrong)
  - Real clubs/stadiums (will be wrong/generic)
  - Any content where accuracy matters to the viewer
```

Tell Antigravity:
"In `thumbnail_generator.py`, add a `thumbnail_generation_rule` field to the script JSON. 
The documentary_generator.py prompt should determine WHICH TYPE of thumbnail to generate:
- `type: 'ai_diagram'` → use Gemini image for a tactical/data visualization
- `type: 'real_image'` → use Wikimedia/Unsplash search for real photos
- `type: 'composite'` → real player image + AI-generated tactical overlay"

---

### 1.2 Thumbnail Design Formula (Football)

```
LAYOUT (1280×720):

1. FULL-BLEED BACKGROUND (40% of design)
   - Real photo from Wikimedia/Unsplash (player action, stadium, crowd)
   - OR AI-generated tactical diagram (if real image unavailable)
   - Apply cinematic filter: contrast(1.15) saturate(0.88)
   - Dark gradient overlay (left 50%, fade from opaque to transparent)

2. MAIN TEXT (top-left, 40% of thumbnail width)
   - Hook phrase: 2-4 words, ALL CAPS, bold condensed font
   - Examples: "IMPOSSIBLE GOAL", "THE TIKI-TAKA REVOLUTION", "TACTICAL GENIUS"
   - Font: Barlow Condensed Bold, size 80-100px
   - Color: white with amber (#F5A623) drop shadow (3px offset)
   - NO full title — only the dramatic hook

3. LEFT ACCENT BAR (5px wide, full height)
   - Color: #F5A623 (amber/gold)
   - Positioned: x=0

4. BOTTOM STRIP (720-100px to 720px, full width)
   - Background: #0A0A12 (dark) with 85% opacity
   - Supporting fact or stat in white, size 32px
   - Examples: "100 METERS FROM GOAL", "5000-1 ODDS", "NEVER BEEN DONE BEFORE"
   - Positioned: bottom-center

5. OPTIONAL: Data visualization overlay (if `type: 'composite'`)
   - Small chart, graph, or formation diagram (10% of thumbnail)
   - Positioned: bottom-right
   - Semi-transparent: 70% opacity
   - Examples: tiki-taka passing lanes, formation shape, win/loss bars

COLORS (Football Channel):
Primary accent:  #F5A623  (amber/gold)
Secondary:       #C0392B  (deep red — for emphasis)
Background:      #0A0A12  (dark navy)
Text:            #FFFFFF  (white)
Overlay:         rgba(10, 10, 20, 0.85)
```

---

### 1.3 Thumbnail Data Structure

Update the documentary_generator.py script output to include:

```json
{
  "thumbnail_data": {
    "hook_phrase": "THE TIKI-TAKA REVOLUTION",
    "supporting_fact": "POSSESSION-BASED DOMINATION",
    "background_query": "Barcelona football tiki-taka passing",
    "background_type": "real_image",
    "diagram_query": "tiki-taka formation passing lanes diagram",
    "diagram_type": "ai_generated",
    "composite": true
  }
}
```

Rules for the prompt:
- `hook_phrase`: 2-4 words max, dramatic, all-caps compatible
- `supporting_fact`: 1-3 words, strikes fear/awe (not "A Good Game")
- `background_query`: use only the most iconic searchable terms
- `background_type`: "real_image" if named players/places, else "ai_generated"
- `diagram_type`: "ai_generated" for tactical/data visualizations
- `composite`: true if both background + diagram should be layered

---

### 1.4 Implementation in `thumbnail_generator.py`

```python
def generate_football_thumbnail(self, thumbnail_data: dict) -> str:
    """
    Generate a football-specific thumbnail with hook phrase, supporting fact,
    background image/diagram, and optional overlay chart.
    """
    canvas = Image.new("RGB", (1280, 720), (10, 10, 18))
    
    # 1. Fetch background (real or AI)
    if thumbnail_data["background_type"] == "real_image":
        bg = self._fetch_wikimedia_image(thumbnail_data["background_query"])
        if not bg:
            bg = self._fetch_unsplash_image(thumbnail_data["background_query"])
        if not bg:
            bg = self._generate_ai_diagram(thumbnail_data["diagram_query"])
    else:
        bg = self._generate_ai_diagram(thumbnail_data["background_query"])
    
    # Resize, apply cinematic grade
    bg = bg.resize((1280, 720), Image.LANCZOS)
    bg = self._apply_cinematic_grade(bg)  # contrast, saturation, vignette
    canvas.paste(bg, (0, 0))
    
    # 2. Dark gradient overlay (left side fade)
    gradient = self._create_gradient_overlay(width=640, height=720)
    canvas.paste(gradient, (0, 0), gradient)
    
    # 3. Amber left bar
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, 5, 720], fill=(245, 166, 35, 255))
    
    # 4. Main text (hook phrase)
    hook_font = ImageFont.truetype("automation/fonts/Barlow-CondensedBold.ttf", 90)
    hook_text = thumbnail_data["hook_phrase"].upper()
    # Wrap text if needed
    lines = self._wrap_text(hook_text, hook_font, max_width=500)
    y = 40
    for line in lines:
        # Outline
        for dx, dy in [(-3,0),(3,0),(0,-3),(0,3)]:
            draw.text((50+dx, y+dy), line, font=hook_font, fill=(0, 0, 0))
        # Text
        draw.text((50, y), line, font=hook_font, fill=(255, 255, 255))
        y += 90
    
    # 5. Bottom strip
    draw.rectangle([0, 620, 1280, 720], fill=(10, 10, 18, 217))  # 85% opacity
    fact_font = ImageFont.truetype("automation/fonts/Barlow-Bold.ttf", 36)
    fact_text = thumbnail_data["supporting_fact"].upper()
    draw.text((640, 670), fact_text, font=fact_font, fill=(255, 255, 255), anchor="mm")
    
    # 6. Optional: overlay diagram (bottom-right)
    if thumbnail_data.get("composite"):
        diagram = self._generate_ai_diagram(thumbnail_data["diagram_query"])
        diagram = diagram.resize((150, 100), Image.LANCZOS)
        diagram.putalpha(int(255 * 0.7))  # 70% opacity
        canvas.paste(diagram, (1100, 600), diagram)
    
    output_path = f"automation/storage/thumbnails/thumb_{thumbnail_data['hook_phrase'][:20].replace(' ','_')}.jpg"
    canvas.save(output_path, "JPEG", quality=95)
    return output_path
```

---

## Part 2: AI Face Restriction Policy

**CRITICAL RULE:** Never use AI-generated images of named, real people's faces. 
AI image models hallucinate faces and cannot generate recognizable likenesses of real people.

### 2.1 Implementation

In `documentary_generator.py`, add a validation rule AFTER Gemini generates scenes:

```python
def _validate_no_ai_faces(scenes: list) -> list:
    """
    Ensure no scene asks for AI generation of named real people or their faces.
    If a scene is classified as ai_video or ai_image for a named player/coach,
    downgrade it to "image" (real photo search) instead.
    """
    for scene in scenes:
        if scene["visual_type"] in ["ai_video", "ai_image"]:
            # Check if the prompt mentions a named player or coach
            prompt = scene.get("ai_video_prompt", scene.get("ai_image_prompt", ""))
            
            # List of named entities that should NEVER be AI-generated
            real_people = scene.get("named_entities", [])
            for entity in real_people:
                if entity["name"].lower() in prompt.lower():
                    # Named person in AI generation request — downgrade to image
                    scene["visual_type"] = "image"
                    scene["image_cue"] = f"{entity['name']} {scene.get('topic', '')}"
                    break
    
    return scenes
```

Add to the Gemini classification prompt:

```
CRITICAL FACE RULE:
Never output visual_type='ai_image' or visual_type='ai_video' for scenes where
a named, real player or coach is the main subject. AI models cannot generate
recognizable faces of real people — they produce hallucinated, wrong, or 
generic faces.

If a scene describes a named player (e.g., "Messi scoring"), classify it as:
  visual_type: "image"
  image_cue: "Messi Ligue 1 goal 2023"

Only use ai_image/ai_video for:
  - Abstract concepts (speed, passion, tactics, formations)
  - Atmospheric scenes (stadium crowds, team celebrations without faces)
  - Tactical diagrams and formations
  - Generic actions (a goalkeeper diving, a midfielder passing)
```

---

### 2.2 What to Show Instead of Named Player Faces

When the content is about a specific player but you can't use AI faces:

| Content | Visual | Example |
|---------|--------|---------|
| "Messi's dribbling skill" | Ball close-up, field perspective | Soccer ball at player's feet (no face) |
| "Ronaldo's aerial dominance" | Stadium crowd reacting, ball in air | Ball high in frame, stadium background |
| "Goalkeeper's impossible save" | Gloves, diving motion (no face) | Close-up of gloved hands, net in bg |
| "Team's possession style" | Tactical diagram, formation heat map | AI-generated tiki-taka passing lanes |
| "Manager's tactical genius" | Whiteboard/tactics diagram, clipboard | AI-generated formation overlay |
| "Defensive wall" | Players from behind (no faces) | Overhead view of formation, no close-ups |

Tell Antigravity:
"In the visual scene classification, when a scene's narration names a specific player 
but requests ai_image, automatically generate these alternative visuals:
- If action-focused (scoring, defending, passing): show action (ball, feet, motion) not face
- If tactical-focused: generate a formation diagram or heat map
- If emotional-focused: show team celebration or crowd reaction, not individual face"

---

## Part 3: Data Visualization Charts (Tactical & Statistical)

For content about tactics, formations, statistics, use AI-generated charts and diagrams.

### 3.1 Tactical Diagram Generation (AI Images)

For topics like "Tiki-Taka Revolution", "Gegenpressing Explained", "Formation Comparison":

```python
def _generate_tactical_diagram(self, topic: str, diagram_type: str) -> str:
    """
    Generate AI images for tactical and statistical visualizations.
    diagram_type: 'formation', 'heat_map', 'passing_lanes', 'pressure_map', 'comparison_chart'
    """
    prompts = {
        "formation": f"Football formation diagram, {topic}, tactical blueprint, field lines, player positions, blue jerseys, clean diagram style, no logos, professional coaching board illustration",
        "heat_map": f"Football pitch heat map showing {topic}, intensity gradient from cool blue to hot red, tactical analysis, sports analytics style",
        "passing_lanes": f"Tiki-taka passing lanes diagram, {topic}, interconnected passing network, football pitch, possession-based tactics, clean lines, minimalist design",
        "pressure_map": f"Gegenpressing pressure diagram, {topic}, high-pressure zones highlighted, aggressive pressing lines, football field, tactical coaching visualization",
        "comparison_chart": f"Football statistics comparison chart, {topic}, horizontal bars, player metrics, clean modern design, no named faces, data visualization",
    }
    
    prompt = prompts.get(diagram_type, prompts["formation"])
    
    # Use gemini-2.5-flash-image with explicit instruction
    response = self.gemini_client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="16:9"),
        ),
    )
    
    # Save and return path
    for part in response.parts:
        if part.inline_data:
            img = part.as_image()
            img = img.resize((1280, 720), Image.LANCZOS)
            output_path = f"automation/storage/temp/{topic[:20]}_{diagram_type}.jpg"
            img.save(output_path, "JPEG", quality=95)
            return output_path
```

### 3.2 Data Visualization in Remotion

Add a new scene type to the Remotion system: `"data_visualization"`

This is rendered using recharts library (already available in Remotion):

```tsx
// DataVisualizationScene.tsx
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";

interface DataVisualizationSceneProps {
  title: string;
  dataType: "bar_chart" | "line_chart" | "formation_diagram" | "heat_map";
  data: Array<{ label: string; value: number }>;
  durationInFrames: number;
}

export const DataVisualizationScene: React.FC<DataVisualizationSceneProps> = ({
  title,
  dataType,
  data,
  durationInFrames,
}) => {
  const progress = useCurrentFrame() / durationInFrames;
  
  if (dataType === "bar_chart") {
    return (
      <div style={{ width: 1280, height: 720, background: "#0A0A12", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
        <h2 style={{ color: "#F5A623", marginBottom: 20 }}>{title}</h2>
        <BarChart width={1000} height={400} data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#444" />
          <XAxis dataKey="label" stroke="#888" />
          <YAxis stroke="#888" />
          <Tooltip contentStyle={{ backgroundColor: "#1a1a2e", border: "1px solid #F5A623" }} />
          <Bar dataKey="value" fill="#F5A623" animationDuration={2000} />
        </BarChart>
      </div>
    );
  }
  
  // Similar implementations for line_chart, formation_diagram, heat_map
};
```

### 3.3 Image Tags/Credits System

For all images used in videos, add metadata tags showing the source.

```python
def _add_image_credit_overlay(image_path: str, source: str, artist: str = None) -> Image:
    """
    Add a small credit overlay to images showing source and artist.
    Positioned: bottom-right corner
    """
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    # Small semi-transparent dark box in bottom-right
    box_width, box_height = 250, 60
    x = img.width - box_width - 10
    y = img.height - box_height - 10
    
    draw.rectangle([x, y, x + box_width, y + box_height], fill=(10, 10, 20, 200))
    
    # Text: "Source: Wikimedia Commons" or "Image by Artist Name"
    font_small = ImageFont.truetype("automation/fonts/Barlow-Regular.ttf", 10)
    credit_text = f"📷 {source}"
    if artist:
        credit_text += f" / {artist}"
    
    draw.text((x + 10, y + 10), credit_text, font=font_small, fill=(200, 200, 200))
    
    return img
```

Tell Antigravity:
"In asset_orchestrator.py, after fetching any image from Wikimedia, Unsplash, or Pixabay, 
call _add_image_credit_overlay() with the source name (e.g., 'Wikimedia Commons', 'Unsplash / 
Chris Unger'). This adds a subtle credit in the corner of the image, giving proper attribution 
to photographers and sources. For AI-generated images, credit as 'AI Generated / Google Gemini'."

---

## Part 4: Build Order for Antigravity

```
STEP 1 — Thumbnail redesign
  Update thumbnail_generator.py with the new formula
  Update documentary_generator.py to output thumbnail_data with hook_phrase, 
  supporting_fact, background_query, diagram_type
  Test: generate thumbnail for "Tiki-Taka Revolution"

STEP 2 — AI face restriction validation
  Add _validate_no_ai_faces() to documentary_generator.py
  Update Gemini classification prompt with the CRITICAL FACE RULE
  Test: generate visual scenes for a named-player topic, confirm no ai_image/ai_video for that player

STEP 3 — Tactical diagram generation
  Add _generate_tactical_diagram() to football_visual_generator.py
  Wire it into asset_orchestrator.py for topics involving tactics
  Test: generate a tiki-taka passing lanes diagram

STEP 4 — Image credit overlay system
  Add _add_image_credit_overlay() to asset_orchestrator.py
  Call it for all non-AI images after fetching
  Test: verify credit appears in corner of Wikimedia/Unsplash images in final render

STEP 5 — Data visualization in Remotion
  Create DataVisualizationScene.tsx (optional, lower priority)
  This is for future video content specifically about statistics/comparisons
  Test: render a bar chart comparing player stats
```

---

## Summary: What This Achieves

| Problem | Solution | Outcome |
|---------|----------|---------|
| Boring generic thumbnails | Formula-based design with hook phrase + supporting fact | Higher CTR, more YouTube recommendations |
| AI hallucinating player faces | Validate no named people in ai_image/ai_video requests | Avoid embarrassing/wrong player photos |
| Over-relying on player photos | Generate tactical diagrams and data visualizations | More variety, shows domain expertise |
| No image attribution | Add credit overlays to all sourced images | Proper photographer/source credit |
| Static visual content | Support data visualization charts in Remotion | More engaging for tactics/analysis videos |

---

*Football Channel Visual Upgrade Plan v2.0 — Thumbnails + Face Restriction + Data Viz*
