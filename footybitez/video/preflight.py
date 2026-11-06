"""Fail before publishing missing, silent or malformed media."""
import json
import math
import re
import shutil
import subprocess


def require_media_tools():
    tools = {name: shutil.which(name) for name in ("ffmpeg", "ffprobe")}
    missing = [name for name, path in tools.items() if not path]
    if missing:
        raise RuntimeError(
            "Missing media tools: " + ", ".join(missing) +
            ". Install the system ffmpeg package (includes ffprobe) and add both to PATH before generation."
        )
    return tools


def inspect_video(path):
    tools = require_media_tools()
    result = subprocess.run(
        [tools["ffprobe"], "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=True, timeout=60,
    )
    data = json.loads(result.stdout)
    duration = float(data.get("format", {}).get("duration", 0))
    streams = data.get("streams", [])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Rendered video has no valid duration")
    if not any(s.get("codec_type") == "video" for s in streams):
        raise ValueError("Rendered file has no video stream")
    if not any(s.get("codec_type") == "audio" for s in streams):
        raise ValueError("Rendered video has no audio stream")
    # Decode the full mix. Stream presence alone does not detect silent output.
    analysis = subprocess.run(
        [tools["ffmpeg"], "-v", "info", "-i", str(path), "-af", "volumedetect", "-vn", "-f", "null", "-"],
        capture_output=True, text=True, check=True, timeout=600,
    )
    match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?|-inf) dB", analysis.stderr)
    if not match or float(match.group(1)) < -45:
        raise ValueError("Rendered audio is silent or too quiet; publishing blocked")
    return {"duration_seconds": duration, "mean_volume_db": float(match.group(1))}
