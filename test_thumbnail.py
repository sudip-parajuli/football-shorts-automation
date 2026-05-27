"""Quick thumbnail render test — runs standalone, no pipeline needed."""
import sys, os
sys.path.insert(0, '.')

from footybitez.media.thumbnail_generator import ThumbnailGenerator

# Use one of the real wiki images already on disk
BACKGROUND = "remotion-video/public/assets/images/wiki_4286737115650893507.jpg"

thumbnail_data = {
    "hook_phrase": "THE TIKI-TAKA REVOLUTION:",
    "main_title": "BARCELONA'S TOTAL DOMINATION EXPLAINED",
    "supporting_fact": "POSSESSION FOOTBALL REDEFINED",
    "background_query": "Barcelona football tiki-taka passing",
    "background_type": "real_image",
    "composite": False,
}

gen = ThumbnailGenerator()
result = gen.generate_football_thumbnail(
    thumbnail_data=thumbnail_data,
    background_path=BACKGROUND,
    output_path="remotion-video/public/thumbnail_test.jpg"
)
print(f"Saved: {result}")
