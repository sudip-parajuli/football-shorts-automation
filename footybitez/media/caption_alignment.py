"""Optional local Whisper alignment for voices without word boundaries."""
from difflib import SequenceMatcher
from functools import lru_cache
import logging
import os
from pathlib import Path
import re
import tempfile

from footybitez.video.short_timeline import align_words

logger = logging.getLogger(__name__)
_whisper_disabled = False


@lru_cache(maxsize=1)
def _whisper_model():
    from faster_whisper import WhisperModel
    cache = Path(os.getenv('WHISPER_CACHE_DIR', str(Path(tempfile.gettempdir()) / 'footybitez-whisper'))).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    return WhisperModel(os.getenv('WHISPER_ALIGNMENT_MODEL', 'base.en'),
                        device='cpu', compute_type='int8', download_root=str(cache))


def align_transcript(text, observed, duration):
    """Use the authored words and accept only matching acoustic anchors."""
    expected = text.split()
    clean = lambda word: re.sub(r'\W', '', word.casefold())
    matcher = SequenceMatcher(a=[clean(word) for word in expected],
                              b=[clean(word['word']) for word in observed], autojunk=False)
    anchors = []
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            word = observed[block.b + offset]
            anchors.append({'word': expected[block.a + offset], 'start': word['start'],
                            'duration': word['duration']})
    if len(anchors) < len(expected) * .65:
        return align_words(text, [], duration)[0], 'interpolated'
    return align_words(text, anchors, duration)[0], 'whisper_word_marks'


def fallback_timings(text, audio_path, duration):
    global _whisper_disabled
    if not _whisper_disabled and os.getenv('ENABLE_WHISPER_ALIGNMENT', 'true').lower() == 'true':
        try:
            segments, _ = _whisper_model().transcribe(audio_path, language='en',
                word_timestamps=True, beam_size=1, condition_on_previous_text=False)
            observed = [{'word': word.word.strip(), 'start': word.start,
                         'duration': word.end-word.start}
                        for segment in segments for word in (segment.words or [])]
            return align_transcript(text, observed, duration)
        except Exception as error:
            _whisper_disabled = True
            logger.warning('Whisper alignment unavailable (%s). Using reported approximate timing.', type(error).__name__)
    return align_words(text, [], duration)[0], 'interpolated'
