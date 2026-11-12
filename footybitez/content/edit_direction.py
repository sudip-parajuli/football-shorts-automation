"""Grounded graphic briefs built from the words being narrated."""
import re


def graphic_brief(text):
    text = re.sub(r"[*_`]", "", str(text)).strip()
    words = text.split()
    if not words:
        raise ValueError("An editorial graphic requires narration")
    lower = text.lower()
    label = "THE STORY"
    if re.search(r"\b(board|manager|coach|vote|summit|sack|decision)\b", lower):
        label = "THE DECISION"
    elif re.search(r"\b(squad|selection|call.up|selected|injury|injured)\b", lower):
        label = "SQUAD WATCH"
    elif re.search(r"\b(transfer|contract|signing|agent|deal)\b", lower):
        label = "THE DEAL"
    elif re.search(r"\b(goal|goals|score|scored|match|won|win)\b", lower):
        label = "MATCHROOM"
    number = re.search(r"(?<!\w)(?:[£€$])?\d+(?:[.,:]\d+)*(?:%|m|bn)?(?!\w)", text)
    layout = "number" if number else "statement"
    if re.search(r"\b(if|whether|decide|decision|vote)\b", lower):
        layout = "decision"
    # All displayed factual text is a contiguous excerpt from this narration.
    detail = text
    actors = []
    for match in re.finditer(r"\b(board|manager|coach|club|fans|player|squad)\b", text, re.I):
        actor = match.group()
        identity = lambda value: 'coach' if value.casefold() in ('coach','manager') else value.casefold()
        if identity(actor) not in {identity(value) for value in actors}:
            actors.append(actor)
    status = re.search(r"\b(not announced|not confirmed|pending|discussion|discussing|vote|reported)\b", text, re.I)
    motif = ''
    for name, pattern in (
        ('contract', r'\b(contract|contracts|agreement|signing)\b'),
        ('trophy', r'\b(trophy|trophies|silverware|champion|champions)\b'),
        ('calendar', r'\b(schedule|deadline|calendar|season|retirement|retirements|farewell)\b'),
        ('recovery', r'\b(injury|injured|recovery|rehabilitation)\b'),
        ('passing', r'\b(pass|passes|passing|backpass|backpasses)\b'),
    ):
        if re.search(pattern, lower):
            motif = name
            break
    return {
        "motif": motif,
        "layout": layout,
        "label": label,
        "headline": " ".join(words[:7]),
        "detail": detail,
        "focus": number.group() if number else "",
        "actors": actors[:2],
        "status": status.group() if status else "",
    }
