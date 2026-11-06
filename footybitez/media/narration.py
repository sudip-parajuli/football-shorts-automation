"""Conversational UK narration settings and SSML, independent of providers."""
import html
import re

DEFAULT_GOOGLE_VOICE = "en-GB-Neural2-B"
DEFAULT_EDGE_VOICE = "en-GB-RyanNeural"


def narration_ssml(text):
    words = text.split()
    pieces = ["<speak><p><s>"]
    for index, word in enumerate(words):
        value = html.escape(word)
        if word.strip('.,!?') in {"VAR", "PSG", "FA"}:
            token = word.strip('.,!?')
            value = '<say-as interpret-as="characters">' + token + '</say-as>' + html.escape(word[len(token):])
        pieces.append(f'<mark name="w{index}"/>{value} ')
        if re.search(r"[.!?]$", word) and index < len(words) - 1:
            pieces.append("</s><s>")
    pieces.append("</s></p></speak>")
    return "".join(pieces)


def google_payload(text, voice=DEFAULT_GOOGLE_VOICE, rate=1.0):
    return {"input":{"ssml":narration_ssml(text)},
            "voice":{"languageCode":"-".join(voice.split('-')[:2]),"name":voice},
            "audioConfig":{"audioEncoding":"MP3","speakingRate":rate,"pitch":0.0},
            "enableTimePointing":["SSML_MARK"]}


def hume_payload(text, voice_id=None):
    utterance = {"text":text, "description":"A clear, conversational British football storyteller. Natural pauses, warm and engaged, no shouting.",
                 "speed":1.0, "trailing_silence":0.1}
    if voice_id:
        utterance["voice"] = {"id":voice_id}
    return {"utterances":[utterance],"format":{"type":"mp3"}}
