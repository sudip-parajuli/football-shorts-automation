import os
import io
import logging
import requests
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

class ThumbnailGenerator:
    def __init__(self, font_path="remotion-video/public/assets/fonts/BarlowCondensed-Bold.ttf"):
        self.font_path = font_path
        if not os.path.exists(self.font_path):
            logger.warning(f"Font not found at {self.font_path}. Using default font.")
            self.font_path = None

    def generate_ai_thumbnail(self, ai_prompt, output_path="remotion-video/public/thumbnail.jpg"):
        """
        Generates a thumbnail using Gemini image generation (free tier).
        Tries GEMINI_API_KEY, GEMINI_API_KEY2, GEMINI_API_KEY3 in order.

        Uses new google-genai SDK (replaces deprecated google-generativeai).
        Model: gemini-2.5-flash-image
          - Free tier, supports response_modalities=["TEXT","IMAGE"]
          - The old SDK's GenerationConfig had no response_modalities — that was the crash.
        """
        gemini_keys = []
        for suffix in ["", "2", "3"]:
            val = os.getenv(f"GEMINI_API_KEY{suffix}")
            if val:
                gemini_keys.append(val)

        if not gemini_keys:
            logger.warning("No GEMINI_API_KEY found. Skipping AI thumbnail.")
            return None

        for i, key in enumerate(gemini_keys):
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=key)

                full_prompt = (
                    f"{ai_prompt}\n\n"
                    "Style: cinematic YouTube thumbnail, 16:9 aspect ratio, "
                    "dramatic lighting, bold text space on left side, "
                    "photorealistic professional sports photography, vivid colors, "
                    "no watermarks, no text in image."
                )

                response = client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"]
                    )
                )

                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                        img_data = part.inline_data.data
                        img = Image.open(io.BytesIO(img_data)).convert("RGB")
                        img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                        os.makedirs(
                            os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
                            exist_ok=True
                        )
                        img.save(output_path, "JPEG", quality=95)
                        logger.info(f"AI thumbnail saved to {output_path} (key #{i+1})")
                        return output_path

                logger.warning(f"Gemini key #{i+1} returned no image parts.")
            except Exception as e:
                logger.warning(f"Gemini key #{i+1} failed for thumbnail: {e}")

        logger.warning("All Gemini keys failed for AI thumbnail. Will use PIL fallback.")
        return None


    def generate_thumbnail(self, background_path, text, output_path="remotion-video/public/thumbnail.jpg", is_list=False):
        """
        PIL-based thumbnail — used as fallback when AI generation fails.
        """
        try:
            img = Image.open(background_path).convert("RGBA")
            img = img.resize((1280, 720), Image.Resampling.LANCZOS)

            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            bg_darken = Image.new("RGBA", img.size, (0, 0, 0, 80))
            img = Image.alpha_composite(img, bg_darken)

            font_size = 140 if len(text) < 15 else 100
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                font = ImageFont.load_default()

            lines = self._wrap_text(text, font, 800)
            y_offset = 60
            x_offset = 60

            for line in lines:
                outline_color = (0, 0, 0, 255)
                outline_width = 8
                for ox in range(-outline_width, outline_width + 1):
                    for oy in range(-outline_width, outline_width + 1):
                        draw.text((x_offset + ox, y_offset + oy), line, font=font, fill=outline_color)
                draw.text((x_offset, y_offset), line, font=font, fill=(255, 255, 255, 255))
                bbox = draw.textbbox((x_offset, y_offset), line, font=font)
                y_offset += (bbox[3] - bbox[1]) + 20

            if is_list:
                draw.rectangle([0, 0, 20, 720], fill=(245, 166, 35, 255))

            final_img = Image.alpha_composite(img, overlay).convert("RGB")
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
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

    def generate_football_thumbnail(
        self,
        thumbnail_data: dict,
        background_path: str,
        diagram_path: str = None,
        output_path: str = "remotion-video/public/thumbnail.jpg"
    ) -> str:
        """
        Generate a football-specific thumbnail with hook phrase, supporting fact,
        background image/diagram, and optional overlay chart.
        """
        try:
            canvas = Image.new("RGB", (1280, 720), (10, 10, 18))

            # 1. Paste and resize background image
            if background_path and os.path.exists(background_path):
                bg = Image.open(background_path).convert("RGB")
            else:
                # Default dark canvas fallback
                bg = Image.new("RGB", (1280, 720), (10, 10, 18))

            bg = bg.resize((1280, 720), Image.Resampling.LANCZOS)
            bg = self._apply_cinematic_grade(bg)  # contrast, saturation
            canvas.paste(bg, (0, 0))

            # 2. Dark gradient overlay (left side fade)
            gradient = self._create_gradient_overlay(width=640, height=720)
            canvas.paste(gradient, (0, 0), gradient)

            # 3. Amber left bar (width=5px)
            draw = ImageDraw.Draw(canvas)
            draw.rectangle([0, 0, 5, 720], fill=(245, 166, 35, 255))

            # 4. Main text (hook phrase)
            font_size = 90
            if self.font_path:
                hook_font = ImageFont.truetype(self.font_path, font_size)
            else:
                hook_font = ImageFont.load_default()

            hook_text = thumbnail_data.get("hook_phrase", "FOOTBALL HISTORY").upper()
            # Wrap text if needed
            lines = self._wrap_text(hook_text, hook_font, max_width=500)
            y = 80
            for line in lines:
                # Draw drop shadow (offset = 3px, color = amber/gold #F5A623)
                for dx, dy in [(-3, -3), (-3, 3), (3, -3), (3, 3), (0, 3), (3, 0)]:
                    draw.text((50 + dx, y + dy), line, font=hook_font, fill=(245, 166, 35, 255))
                # Draw black outline for readability
                for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    draw.text((50 + dx, y + dy), line, font=hook_font, fill=(0, 0, 0, 255))
                # Text
                draw.text((50, y), line, font=hook_font, fill=(255, 255, 255, 255))
                y += font_size + 10

            # 5. Bottom strip (y from 620 to 720)
            draw.rectangle([0, 620, 1280, 720], fill=(10, 10, 18, 217))  # 85% opacity
            if self.font_path:
                fact_font = ImageFont.truetype(self.font_path, 36)
            else:
                fact_font = ImageFont.load_default()

            fact_text = thumbnail_data.get("supporting_fact", "").upper()
            # Draw text centered anchor="mm" at (640, 670)
            draw.text((640, 670), fact_text, font=fact_font, fill=(255, 255, 255, 255), anchor="mm")

            # 6. Optional: overlay diagram (bottom-right)
            if thumbnail_data.get("composite") and diagram_path and os.path.exists(diagram_path):
                diagram = Image.open(diagram_path).convert("RGBA")
                diagram = diagram.resize((150, 100), Image.Resampling.LANCZOS)
                
                # Apply 70% opacity
                alpha = diagram.split()[3]
                alpha = alpha.point(lambda p: int(p * 0.7))
                diagram.putalpha(alpha)
                
                canvas.paste(diagram, (1100, 500), diagram)

            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            canvas.save(output_path, "JPEG", quality=95)
            logger.info(f"Football thumbnail saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate football thumbnail: {e}")
            return None

    def _apply_cinematic_grade(self, img: Image.Image) -> Image.Image:
        """Applies cinematic grade: contrast(1.15) saturate(0.88)"""
        try:
            from PIL import ImageEnhance
            # Contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.15)
            # Saturation (Color)
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(0.88)
            return img
        except Exception as e:
            logger.warning(f"Failed to apply cinematic grade: {e}")
            return img

    def _create_gradient_overlay(self, width: int = 640, height: int = 720) -> Image.Image:
        """Create dark gradient overlay (left side fade, opaque to transparent)"""
        try:
            gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(gradient)
            for x in range(width):
                # Opaque at x=0 (220 alpha), fading to transparent at x=width (0 alpha)
                alpha = int(220 * (1 - (x / width)))
                draw.line([(x, 0), (x, height)], fill=(10, 10, 18, alpha))
            return gradient
        except Exception as e:
            logger.warning(f"Failed to create gradient overlay: {e}")
            return Image.new("RGBA", (width, height), (10, 10, 18, 150))
