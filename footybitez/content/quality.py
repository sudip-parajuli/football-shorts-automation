"""Deterministic editorial checks shared by generation and rendering."""
import re


def contains_term(text, term):
    # Do not reject 'teammate' for MMA, 'command' for woman, or 'summary'.
    return bool(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.I))


QUERY_STOPWORDS = set("a an the and or to of for with in on at by is are was were this that it their its they them as from so can cannot would could should not".split())
QUERY_DESCRIPTORS = set("football soccer illustration diagram tactical pitch rule explain explained explainer action photo portrait kit shirt jersey launch passing pass defender attacker goalkeeper referee animation formation concept example".split())


def visual_query_errors(query, narration, context):
    words = lambda value: {word.rstrip("s") for word in re.findall(r"\w+", value.lower())}
    allowed = words(context + " " + narration) | words(" ".join(QUERY_STOPWORDS | QUERY_DESCRIPTORS))
    if not words(query).issubset(allowed):
        return ["visual query adds unsupported terms"]
    return []


def grounding_errors(data, context):
    """Validate application-attached source passages, without case-based NER."""
    normalize = lambda value: " ".join(re.findall(r"\w+", value.lower()))
    evidence = normalize(context)
    errors = []
    for index, segment in enumerate(data.get("segments", [])):
        quotes = segment.get("source_quotes") or [segment.get("source_quote", "")]
        if not isinstance(quotes, list) or not quotes or any(
            not isinstance(quote, str) or len(re.findall(r"\w+", quote)) < 6 or normalize(quote) not in evidence
            for quote in quotes
        ):
            errors.append(f"Segment {index + 1} needs an exact research quote of at least six words")
            continue
        cited_text = " ".join(quotes)
        numbers = set(re.findall(r"\d+(?:[.,]\d+)?", segment["text"]))
        if not numbers.issubset(set(re.findall(r"\d+(?:[.,]\d+)?", cited_text))):
            errors.append(f"Segment {index + 1} adds numbers/dates absent from its evidence")
        for error in visual_query_errors(segment.get("visual_keyword", ""), segment["text"], context):
            errors.append(f"Segment {index + 1} {error}")
    return errors


FILLER = (
    "here is a crazy fact about", "is a true legend of football",
    "their story inspires millions", "you won't believe this fact",
    "in this video we will", "welcome back to the channel",
)


def short_errors(data):
    if not isinstance(data, dict):
        return ["Script must be an object"]
    segments = data.get("segments")
    if not isinstance(segments, list) or not 2 <= len(segments) <= 8:
        return ["Require 2–8 substantive segments"]
    if not isinstance(data.get("hook"), str) or not data["hook"].strip():
        return ["Missing hook"]
    if not isinstance(data.get("outro", ""), str):
        return ["Outro must be text"]
    texts = []
    for seg in segments:
        if not isinstance(seg, dict) or not isinstance(seg.get("text"), str):
            return ["Every segment needs narration text"]
        if len(seg["text"].split()) < 8:
            return ["Segment too thin to explain a fact"]
        if not isinstance(seg.get("visual_keyword"), str) or len(seg["visual_keyword"].split()) < 3:
            return ["Every segment needs a specific visual query"]
        texts.append(seg["text"])
    narration = " ".join([data["hook"], *texts, data.get("outro", "")]).strip()
    errors = []
    if not 65 <= len(narration.split()) <= 170:
        errors.append("Short narration must be 65–170 words")
    if len(data["hook"].split()) > 16:
        errors.append("Hook must be at most 16 words")
    if any(phrase in narration.lower() for phrase in FILLER):
        errors.append("Generic fallback or introductory filler")
    normalized = [re.sub(r"\W+", " ", t.lower()).strip() for t in texts]
    if len(set(normalized)) != len(normalized):
        errors.append("Repeated narration")
    if not errors:
        data["full_text"] = narration
    return errors


def documentary_errors(data):
    if not isinstance(data, dict) or not isinstance(data.get("title"), str) or not data["title"].strip():
        return ["Missing documentary title"]
    chapters = data.get("chapters")
    if not isinstance(chapters, list) or len(chapters) != 3:
        return ["Require three chapters"]
    errors = []
    total_words = 0
    for chapter in chapters:
        if not isinstance(chapter, dict) or not isinstance(chapter.get("script"), str):
            return ["Missing chapter narration"]
        text = chapter["script"]
        total_words += len(text.split())
        scenes = chapter.get("visual_scenes")
        if not isinstance(scenes, list) or len(scenes) < 6:
            errors.append("Each chapter needs at least six planned visual beats")
            continue
        clean = lambda value: re.sub(r"\W+", " ", value.lower()).strip()
        cursor = 0
        narration = clean(text)
        for scene in scenes:
            snippet = scene.get("narration_snippet", "") if isinstance(scene, dict) else ""
            if not isinstance(snippet, str) or not snippet.strip():
                errors.append("Missing narration snippet")
                break
            index = narration.find(clean(snippet), cursor)
            if index < 0:
                errors.append("Scene snippets must quote narration in speaking order")
                break
            if narration[cursor:index].strip():
                errors.append("Scene plan skips narration between visual beats")
                break
            cursor = index + len(clean(snippet))
        if narration[cursor:].strip():
            errors.append("Scene plan must cover the end of chapter narration")
    if not 550 <= total_words <= 1300:
        errors.append("Documentary narration must be 550–1300 words")
    return errors
