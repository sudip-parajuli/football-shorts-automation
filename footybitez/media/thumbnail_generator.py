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
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

    def generate_ai_thumbnail(self, ai_prompt, output_path="remotion-video/public/thumbnail.jpg"):
        """
        Generates a thumbnail using Gemini Imagen API (free tier).
        Returns the output path if successful, None otherwise.
        """
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set. Skipping AI thumbnail.")
            return None

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)

            # Use Gemini 2.0 Flash image generation (free)
            model = genai.GenerativeModel("gemini-2.0-flash-exp-image-generation")
            
            full_prompt = (
                f"{ai_prompt}\n\n"
                "Style: cinematic YouTube thumbnail, 16:9 aspect ratio, "
                "dramatic lighting, bold text space on left side, "
                "photorealistic professional sports photography, vivid colors, "
                "no watermarks, no text in image."
            )
            
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    response_modalities=["IMAGE"]
                )
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    img_data = part.inline_data.data
                    img = Image.open(io.BytesIO(img_data)).convert("RGB")
                    img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
                    img.save(output_path, "JPEG", quality=95)
                    logger.info(f"AI thumbnail saved to {output_path}")
                    return output_path

            logger.warning("Gemini returned no image in response.")
            return None

        except Exception as e:
            logger.warning(f"AI thumbnail generation failed: {e}. Will use PIL fallback.")
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
