"""Fail before publishing missing, silent or malformed media."""
import json
import math
import re
import subprocess


def inspect_video(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
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
        ["ffmpeg", "-v", "info", "-i", str(path), "-af", "volumedetect", "-vn", "-f", "null", "-"],
        capture_output=True, text=True, check=True, timeout=600,
    )
    match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?|-inf) dB", analysis.stderr)
    if not match or float(match.group(1)) < -45:
        raise ValueError("Rendered audio is silent or too quiet; publishing blocked")
    return {"duration_seconds": duration, "mean_volume_db": float(match.group(1))}
