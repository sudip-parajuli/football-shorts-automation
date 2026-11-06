"""Conservative metadata matching before sending a candidate to vision."""
import html
import re
from urllib.parse import unquote

STOP = set("the a an of in on for to and or with why how does do is are every soccer football association men match action portrait national team".split())


def tokens(value):
    value = html.unescape(re.sub(r"<[^>]+>", " ", unquote(value))).lower()
    return {word.rstrip("s") for word in re.findall(r"[a-z]+|\d{4}", value) if word not in STOP and len(word) > 2}


def metadata_matches(query, title, description="", categories=""):
    wanted = tokens(query)
    # Categories often contain broad parent entities; identity/action must occur
    # in the actual filename or description, not a distant category alone.
    evidence = tokens(title + " " + description)
    if not wanted or not evidence:
        return False
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", query))
    if years and not years.issubset(evidence):
        return False
    matched = wanted & evidence
    return len(matched) >= min(2, len(wanted)) and len(matched) / len(wanted) >= 0.6
