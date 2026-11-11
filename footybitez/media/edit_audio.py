"""Quiet, original edit cues generated locally with a fixed waveform."""
import math
from pathlib import Path
import struct
import wave


def make_edit_sounds(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, frequency, duration in [('tick', 700, .055), ('accent', 160, .14)]:
        path = directory / f'edit_{name}.wav'
        sample_rate = 44100
        frames = []
        for index in range(round(duration * sample_rate)):
            seconds = index / sample_rate
            envelope = min(1, seconds / .004) * math.exp(-seconds * 40)
            sample = .15 * envelope * math.sin(2 * math.pi * frequency * seconds)
            frames.append(struct.pack('<h', round(sample * 32767)))
        with wave.open(str(path), 'wb') as output:
            output.setparams((1, 2, sample_rate, 0, 'NONE', 'not compressed'))
            output.writeframes(b''.join(frames))
        paths[name] = str(path)
    return paths


def plan_sound_cues(segments, fps=24):
    cues = []
    offset = 0
    last_frame = -fps * 4
    for segment in segments:
        for scene in segment['visual_scenes']:
            graphic = scene.get('graphic') or {}
            if graphic.get('layout') not in ('decision', 'number'):
                continue
            frame = offset + scene['from_frame']
            if frame - last_frame >= fps * 4 and len(cues) < 6:
                cues.append({'from_frame': frame, 'sound': 'accent' if graphic['layout']=='number' else 'tick'})
                last_frame = frame
        offset += round(segment['duration'] * fps)
    return cues
