"""Optional mood manifest; never invent permission to use an audio track."""
import json
import logging
from pathlib import Path


def select_music(mood="neutral", directory="footybitez/music"):
    manifest = Path(directory) / "manifest.json"
    if not manifest.exists():
        logging.getLogger(__name__).warning("No music manifest: using narration without background music")
        return None
    tracks = json.loads(manifest.read_text(encoding="utf-8"))
    candidates = []
    for track in tracks:
        path = (Path(directory) / track.get("file", "")).resolve()
        if (Path(directory).resolve() in path.parents and path.is_file()
                and track.get("rights_confirmed") is True
                and mood in track.get("moods", [])):
            candidates.append(str(path))
    # Stable selection keeps previews reproducible.
    return sorted(candidates)[0] if candidates else None
