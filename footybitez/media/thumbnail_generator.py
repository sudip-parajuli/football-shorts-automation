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
                        img = self._crop_to_fill(img, (1280, 720))
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
        Uses crop-to-fit to preserve aspect ratio.
        """
        try:
            img = Image.open(background_path).convert("RGBA")
            img = self._crop_to_fill(img, (1280, 720))

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
        Generate a football-specific thumbnail matching the channel's visual formula:
        - Full-bleed background (darkened, cinematic grade)
        - Global dark overlay (top-heavy vignette)
        - Top-left: Amber/gold label line (small caps)
        - Middle-left: White bold title on dark maroon bar
        - Bottom strip: Dark maroon full-width bar with bullet subtitle
        """
        try:
            from PIL import ImageEnhance, ImageFilter
            import numpy as np

            W, H = 1280, 720

            # ── 1. Background ────────────────────────────────────────────────
            if background_path and os.path.exists(background_path):
                bg = Image.open(background_path).convert("RGB")
            else:
                bg = Image.new("RGB", (W, H), (20, 10, 10))

            bg = self._crop_to_fill(bg, (W, H))

            # Cinematic grade: boost contrast slightly, desaturate a touch
            bg = ImageEnhance.Contrast(bg).enhance(1.2)
            bg = ImageEnhance.Color(bg).enhance(0.85)
            canvas = bg.copy()

            # ── 2. Global dark overlay (top & left heavier) ──────────────────
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ov_draw = ImageDraw.Draw(overlay)

            # Left-side gradient: opaque (#0A0A0A, 200) → transparent at x=750
            for x in range(750):
                alpha = int(200 * (1 - x / 750))
                ov_draw.line([(x, 0), (x, H)], fill=(10, 10, 10, alpha))

            # Top gradient: semi-opaque at top → transparent at y=350
            for y in range(350):
                alpha = int(140 * (1 - y / 350))
                ov_draw.line([(0, y), (W, y)], fill=(10, 10, 10, alpha))

            canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(canvas)

            # ── 3. Fonts ─────────────────────────────────────────────────────
            def font(size):
                if self.font_path:
                    return ImageFont.truetype(self.font_path, size)
                return ImageFont.load_default()

            # ── 4. Amber label (top-left small-caps) ─────────────────────────
            label = thumbnail_data.get("hook_phrase", "FOOTBALL HISTORY").upper()
            label_font = font(52)

            lx, ly = 50, 55
            self._draw_text_with_outline(draw, lx, ly, label, label_font,
                                          fill=(245, 166, 35), outline=(0, 0, 0), outline_width=4)

            # ── 5. Main title on dark-maroon bar ──────────────────────────────
            # Use main_title if present (new schema), fall back to supporting_fact for old scripts
            title = thumbnail_data.get("main_title") or thumbnail_data.get("supporting_fact", "FOOTBALL HISTORY")
            title = title.upper()
            title_font = font(78)

            # Wrap title to ~780px wide
            title_lines = self._wrap_text(title, title_font, max_width=760)

            line_h = 90  # approx line height
            bar_top = ly + 62
            bar_bottom = bar_top + (len(title_lines) * line_h) + 20
            bar_bottom = min(bar_bottom, H - 100)  # clamp

            # Dark maroon bar (semi-transparent) behind title
            bar_img = Image.new("RGBA", (W, bar_bottom - bar_top), (80, 10, 10, 210))
            canvas.paste(
                Image.fromarray(
                    self._to_rgba_array(bar_img), "RGBA"
                ).convert("RGB"),
                (0, bar_top),
            )
            # Re-init draw after paste
            draw = ImageDraw.Draw(canvas)

            ty = bar_top + 12
            for line in title_lines:
                self._draw_text_with_outline(draw, 50, ty, line, title_font,
                                              fill=(255, 255, 255), outline=(0, 0, 0), outline_width=6)
                bbox = draw.textbbox((50, ty), line, font=title_font)
                ty += (bbox[3] - bbox[1]) + 8
                if ty > bar_bottom - 10:
                    break

            # ── 6. Bottom maroon strip ────────────────────────────────────────
            strip_h = 72
            strip_top = H - strip_h
            strip_img = Image.new("RGBA", (W, strip_h), (100, 15, 15, 230))
            canvas.paste(
                Image.fromarray(self._to_rgba_array(strip_img), "RGBA").convert("RGB"),
                (0, strip_top)
            )
            draw = ImageDraw.Draw(canvas)

            subtitle = thumbnail_data.get("supporting_fact", "")
            # Convert to uppercase, trim long queries
            subtitle = subtitle.replace("_", " ").upper()
            if len(subtitle) > 60:
                subtitle = subtitle[:57] + "..."

            sub_font = font(36)
            draw.text(
                (W // 2, strip_top + strip_h // 2),
                subtitle,
                font=sub_font,
                fill=(255, 255, 255),
                anchor="mm"
            )

            # ── 7. Optional diagram composite (bottom-right, 70% opacity) ────
            if thumbnail_data.get("composite") and diagram_path and os.path.exists(diagram_path):
                try:
                    diagram = Image.open(diagram_path).convert("RGBA")
                    diagram = diagram.resize((240, 160), Image.Resampling.LANCZOS)
                    r, g, b, a = diagram.split()
                    a = a.point(lambda p: int(p * 0.7))
                    diagram.putalpha(a)
                    canvas_rgba = canvas.convert("RGBA")
                    canvas_rgba.paste(diagram, (W - 260, strip_top - 175), diagram)
                    canvas = canvas_rgba.convert("RGB")
                    draw = ImageDraw.Draw(canvas)
                except Exception as de:
                    logger.warning(f"Diagram composite failed: {de}")

            # ── 8. Save ───────────────────────────────────────────────────────
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            canvas.save(output_path, "JPEG", quality=95)
            logger.info(f"Football thumbnail saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate football thumbnail: {e}")
            return None

    def _draw_text_with_outline(self, draw, x, y, text, font, fill, outline, outline_width=4):
        """Draw text with solid outline for readability."""
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline)
        draw.text((x, y), text, font=font, fill=fill)
    
    def _crop_to_fill(self, img: Image.Image, target_size: tuple) -> Image.Image:
        """
        Crops image to fill target dimensions while preserving aspect ratio.
        Scales the smaller dimension to match target, then center-crops.
        """
        from PIL import ImageOps
        return ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)

    def _to_rgba_array(self, img_rgba):
        """Convert RGBA PIL image to numpy array for paste workaround."""
        import numpy as np
        return np.array(img_rgba)

    def _apply_cinematic_grade(self, img: Image.Image) -> Image.Image:
        """Applies cinematic grade: contrast(1.15) saturate(0.88)"""
        try:
            from PIL import ImageEnhance
            img = ImageEnhance.Contrast(img).enhance(1.15)
            img = ImageEnhance.Color(img).enhance(0.88)
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
                alpha = int(220 * (1 - (x / width)))
                draw.line([(x, 0), (x, height)], fill=(10, 10, 18, alpha))
            return gradient
        except Exception as e:
            logger.warning(f"Failed to create gradient overlay: {e}")
            return Image.new("RGBA", (width, height), (10, 10, 18, 150))

