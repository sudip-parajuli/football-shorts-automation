import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import logging

logger = logging.getLogger(__name__)

class ThumbnailGenerator:
    def __init__(self, font_path="remotion-video/public/assets/fonts/BarlowCondensed-Bold.ttf"):
        self.font_path = font_path
        if not os.path.exists(self.font_path):
            logger.warning(f"Font not found at {self.font_path}. Using default font.")
            self.font_path = None

    def generate_thumbnail(self, background_path, text, output_path="output/thumbnail.jpg", is_list=False):
        """
        Generates a punchy football thumbnail.
        """
        try:
            # 1. Load Background
            img = Image.open(background_path).convert("RGBA")
            # Resize to 1280x720 (YouTube standard)
            img = img.resize((1280, 720), Image.Resampling.LANCZOS)
            
            # Create a layer for text/graphics
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # 2. Add Contrast (Subtle darkening of bg)
            # We can use a dark gradient or just darken the whole thing
            bg_darken = Image.new("RGBA", img.size, (0, 0, 0, 60))
            img = Image.alpha_composite(img, bg_darken)
            
            # 3. Add Text
            # Determine font size (dynamic based on text length)
            font_size = 140 if len(text) < 15 else 100
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                font = ImageFont.load_default()
            
            # Wrap text if too long
            lines = self._wrap_text(text, font, 800)
            
            y_offset = 60
            x_offset = 60
            
            for line in lines:
                # Draw Drop Outline (actually 8 offsets for a robust outline)
                outline_color = (0, 0, 0, 255)
                outline_width = 8
                for ox in range(-outline_width, outline_width + 1):
                    for oy in range(-outline_width, outline_width + 1):
                        draw.text((x_offset + ox, y_offset + oy), line, font=font, fill=outline_color)
                
                # Draw Main Text
                draw.text((x_offset, y_offset), line, font=font, fill=(255, 255, 255, 255))
                
                # Update y_offset for next line
                bbox = draw.textbbox((x_offset, y_offset), line, font=font)
                y_offset += (bbox[3] - bbox[1]) + 20
            
            # 4. Add Decorative Element (e.g., Orange Accent)
            if is_list:
                # Add a big orange number/arrow or just a stripe
                draw.rectangle([0, 0, 20, 720], fill=(245, 166, 35, 255)) # Orange side stripe
            
            # Final composite
            final_img = Image.alpha_composite(img, overlay).convert("RGB")
            
            # Create output dir if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            final_img.save(output_path, "JPEG", quality=95)
            logger.info(f"Thumbnail saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            return None

    def _wrap_text(self, text, font, max_width):
        """Simple text wrapping."""
        lines = []
        words = text.split()
        current_line = []
        
        # Temp draw to measure text
        temp_img = Image.new("RGB", (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = temp_draw.textbbox((0, 0), test_line, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(" ".join(current_line))
        return lines

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gen = ThumbnailGenerator()
    # gen.generate_thumbnail("path/to/bg.jpg", "HOW THE PREMIER LEAGUE ATE ITSELF", "output/test_thumb.jpg")
