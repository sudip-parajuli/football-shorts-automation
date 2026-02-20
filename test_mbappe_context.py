import logging
from footybitez.content.script_generator import ScriptGenerator

logging.basicConfig(level=logging.INFO)

generator = ScriptGenerator()
context = generator._fetch_context("Kylian Mbappe")
with open("mbappe_context.txt", "w", encoding="utf-8") as f:
    f.write(context)
print("Context written to mbappe_context.txt")
