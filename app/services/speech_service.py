"""
Speech analysis service (transcript based).

This module never touches Flask (`request`, `session`) - routes call into it.
Everything here is computed from the recognised transcript and the prepared
script; nothing is estimated or defaulted:

    script_accuracy   how closely the spoken words match the prepared script
    speaking_pace_wpm spoken words / recording duration in minutes
    filler_words      um / uh / like / you know / actually / basically / so ...
    fluency           100 minus a penalty for fillers and repeated words

A metric that cannot be computed is returned as ``None`` (never 0 or a
placeholder), so the UI can simply leave it out.

Optional future extension: a trained speech model (wav2vec2, Whisper, ...)
could replace or add to these values without changing the return shape.
"""
import logging
import re
from collections import Counter
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

WORD_PATTERN = re.compile(r"[a-z0-9']+")

# Matched against the normalised (lower-case, punctuation-free) text.
FILLER_PATTERN = re.compile(r"\b(?:um+|uh+|erm+|er+|you know|like|actually|basically|so)\b")

# Recordings shorter than this are too short for a meaningful words-per-minute.
MIN_DURATION_FOR_WPM_SECONDS = 3.0


def normalize_words(text: str) -> list:
    """Lower-case, drop punctuation, normalise whitespace -> list of words."""
    text = (text or "").lower().replace("\u2019", "'").replace("\u2018", "'")
    return WORD_PATTERN.findall(text)


def _canonical_filler(token: str) -> str:
    if token.startswith("um"):
        return "um"
    if token.startswith("uh"):
        return "uh"
    if token.startswith("er"):
        return "er"
    return token


def _filler_counts(words: list) -> Counter:
    return Counter(_canonical_filler(m) for m in FILLER_PATTERN.findall(" ".join(words)))


def count_fillers(spoken_words: list, script_words: list) -> dict:
    """Filler words in the transcript.

    Words such as "like" or "so" are also ordinary vocabulary, so occurrences
    that the prepared script itself contains are not counted as fillers - only
    the extra ones the speaker added are.
    """
    spoken = _filler_counts(spoken_words)
    scripted = _filler_counts(script_words)
    extra = {}
    for word, count in spoken.items():
        surplus = count - scripted.get(word, 0)
        if surplus > 0:
            extra[word] = surplus
    return extra


def count_repeats(words: list) -> int:
    """Immediately repeated words ("the the", "is is")."""
    return sum(1 for i in range(1, len(words)) if words[i] == words[i - 1])


def script_accuracy(script_words: list, spoken_words: list):
    """0-100 similarity between the spoken words and the prepared script.

    Order-aware: words are aligned with difflib's SequenceMatcher, so saying
    the right words in the wrong place does not count. Skipped script words
    and extra ad-libbed words both lower the score (the matched words are
    divided by the longer of the two texts).
    """
    if not script_words or not spoken_words:
        return None
    matcher = SequenceMatcher(None, script_words, spoken_words, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    return round(100 * matched / max(len(script_words), len(spoken_words)))


def fluency_score(word_count: int, filler_total: int, repeats: int):
    """100 minus a length-normalised penalty for filler words and repeats."""
    if not word_count:
        return None
    per_100_words = 100.0 / word_count
    penalty = 8 * filler_total * per_100_words + 10 * repeats * per_100_words
    return round(max(0, min(100, 100 - penalty)))


def analyze_transcript(transcript: str, script: str, duration_seconds: float) -> dict:
    """Real, deterministic analysis of the recognised transcript.

    ``duration_seconds`` must be the actual recording duration (not the
    target duration).
    """
    spoken_words = normalize_words(transcript)
    script_words = normalize_words(script)
    word_count = len(spoken_words)

    if not word_count:
        logger.info("[SPEECH] No words in transcript - speech metrics unavailable")
        return {
            "word_count": 0,
            "script_accuracy": None,
            "speaking_pace_wpm": None,
            "fluency": None,
            "filler_words": None,
            "filler_breakdown": None,
        }

    wpm = None
    if duration_seconds and duration_seconds >= MIN_DURATION_FOR_WPM_SECONDS:
        wpm = round(word_count / (duration_seconds / 60.0))

    fillers = count_fillers(spoken_words, script_words)
    filler_total = sum(fillers.values())
    repeats = count_repeats(spoken_words)

    result = {
        "word_count": word_count,
        "script_accuracy": script_accuracy(script_words, spoken_words),
        "speaking_pace_wpm": wpm,
        "fluency": fluency_score(word_count, filler_total, repeats),
        "filler_words": filler_total,
        "filler_breakdown": fillers,
    }
    logger.info("[SPEECH] words=%s wpm=%s accuracy=%s fillers=%s fluency=%s",
                word_count, wpm, result["script_accuracy"], filler_total, result["fluency"])
    return result
