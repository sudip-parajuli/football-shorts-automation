import os
import random
from PIL import Image, ImageDraw, ImageFont

class ImageManager:
    def __init__(self, image_dir="footybitez/media/images"):
        self.image_dir = image_dir
        os.makedirs(image_dir, exist_ok=True)

    def get_random_image(self):
        """Returns the path to a random image in the directory."""
        files = [f for f in os.listdir(self.image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not files:
            # Create a placeholder if no images exist
            return self._create_placeholder_image()
        return os.path.join(self.image_dir, random.choice(files))

    def _create_placeholder_image(self):
        """Creates a simple placeholder image for testing."""
        path = os.path.join(self.image_dir, "placeholder.jpg")
        img = Image.new('RGB', (1080, 1920), color = (73, 109, 137))
        d = ImageDraw.Draw(img)
        # We can't easily rely on system fonts being present, so we'll just draw a rectangle
        # or minimal text if a default font works.
        d.text((10,10), "FootyBitez Placeholder", fill=(255,255,0))
        img.save(path)
        return path

if __name__ == "__main__":
    im = ImageManager()
    print(f"Selected Image: {im.get_random_image()}")
