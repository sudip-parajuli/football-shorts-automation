"""Word-anchored visual beats for Shorts. No equal-time paragraph slides."""
import math
import re


def clean_text(text):
    return re.sub(r"\\?\*", "", text).strip()


def align_words(text, timing, duration):
    words = clean_text(text).split()
    if not words or duration <= 0:
        raise ValueError("Narration and positive audio duration are required")
    normalize = lambda word: re.sub(r"\W", "", word.lower())
    anchors = {}
    cursor = 0
    for item in timing or []:
        if not isinstance(item, dict) or not isinstance(item.get("word"), str):
            continue
        try:
            start = float(item["start"])
        except (TypeError, ValueError, KeyError):
            continue
        if not math.isfinite(start) or not 0 <= start < duration:
            continue
        for index in range(cursor, min(len(words), cursor + 4)):
            if normalize(item["word"]) == normalize(words[index]):
                if not anchors or start >= max(anchors.values()):
                    anchors[index] = start
                    cursor = index + 1
                break
    exact = len(anchors) == len(words)
    anchors.setdefault(0, 0.0)
    anchors[len(words)] = duration
    starts = [0.0] * (len(words) + 1)
    indices = sorted(anchors)
    for left, right in zip(indices, indices[1:]):
        weights = [max(1, len(word.strip('.,!?'))) for word in words[left:right]]
        total = sum(weights)
        elapsed = 0
        for index, weight in zip(range(left, right), weights):
            starts[index] = anchors[left] + (anchors[right] - anchors[left]) * elapsed / total
            elapsed += weight
    starts[-1] = duration
    output = [{"word": word, "start": starts[index], "duration": max(0.001, starts[index + 1] - starts[index])}
              for index, word in enumerate(words)]
    return output, "word_marks" if exact else "interpolated"


def visual_theme(text, offset=0):
    """Select only a diagram whose actual drawing explains this spoken clause.

    No generic theme or rotation: a selection announcement, biography or result
    does not become a tactics/transfer story just because media is unavailable.
    """
    lower = text.lower()
    if re.search(r'\b(?:contract|contracts)\b',lower) and re.search(r'\b(?:negotiate|negotiates|negotiating|negotiation|sign|signs|signing|represent|represents)\b',lower):
        return 'contract'
    if re.search(r'\b(?:kit|shirt|jersey|kits|shirts|jerseys)\b',lower) and re.search(r'\b(?:design|designs|colour|color|colours|colors|stripes)\b',lower):
        return 'kit'
    return None


def plan_visual_beats(text, timing, duration, media=None, fps=24, offset=0):
    words, timing_source = align_words(text, timing, duration)
    groups = []
    first = 0
    for index, word in enumerate(words):
        count = index - first + 1
        spoken = word["start"] + word["duration"] - words[first]["start"]
        punctuation = bool(re.search(r"[.!?;:]$", word["word"]))
        if count >= 10 or (count >= 4 and (punctuation or spoken >= 3.2)):
            groups.append((first, index + 1))
            first = index + 1
    if first < len(words):
        if groups and len(words) - first < 3:
            groups[-1] = (groups[-1][0], len(words))
        else:
            groups.append((first, len(words)))
    total_frames = round(duration * fps)
    if total_frames < len(groups):
        raise ValueError("Audio is too short for the visual plan")
    boundaries = [0]
    for index, (start, _) in enumerate(groups[1:], 1):
        boundaries.append(min(total_frames - (len(groups) - index), max(boundaries[-1] + 1, round(words[start]["start"] * fps))))
    boundaries.append(total_frames)
    media = [path for path in (media or []) if path and not re.search(r"(?:^|[/\\])(?:editorial_|placeholder)", path)]
    scenes = []
    for index, (start, end) in enumerate(groups):
        phrase = " ".join(word["word"] for word in words[start:end])
        source = media[index % len(media)] if media else ""
        # Check the local sentence, not a different point elsewhere in the chunk.
        clauses = re.split(r'(?<=[.!?;])\s+', clean_text(text))
        local = next((clause for clause in clauses if phrase in clause), phrase)
        theme = visual_theme(local)
        kind = 'media' if source else 'diagram' if theme else 'unavailable'
        scenes.append({
            "from_frame": boundaries[index], "duration_frames": boundaries[index + 1] - boundaries[index],
            "headline": " ".join(word["word"] for word in words[start:min(end, start + 5)]),
            "narration_snippet": phrase, "theme": theme or '',
            "src": source, "kind": kind,
            "visual_reason": 'Relevant supplied photo/clip' if source else f'Explicit {theme} explanation in the spoken clause' if theme else 'No relevant asset or supported explanatory diagram',
            "word_start": start, "word_end": end,
        })
    return scenes, words, timing_source
