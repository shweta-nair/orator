"""
Fusion service: speech metrics + visual metrics -> one overall score + feedback.

Pipeline (see README):

    recording -> speech features (transcript) ─┐
                                               ├─> feature fusion -> overall score -> feedback
    recording -> visual features (video)     ─┘

The fusion here is a transparent weighted average of the metrics that were
actually measured. If a metric is unavailable it is left out and the
remaining weights are re-normalised - it is never replaced by a default.

Keeping this in one module means a trained fusion model (e.g. an LSTM/GRU/
Transformer over per-frame features) can be added later behind `fuse()`
without touching the routes or the database format.
"""
import logging

logger = logging.getLogger(__name__)

# Report data format version stored in Attempt.metrics
REPORT_VERSION = 2

# Overall score weights (re-normalised over the metrics that exist).
WEIGHTS = {
    "script_accuracy": 0.30,
    "speaking_pace": 0.20,
    "fluency": 0.20,
    "eye_contact": 0.15,
    "filler_words": 0.15,
}

# Comfortable speaking range for a presentation, in words per minute.
TARGET_WPM_MIN = 120
TARGET_WPM_MAX = 150
PACE_POINTS_LOST_PER_WPM = 1.25   # score lost per WPM outside the range

# 0 fillers per 100 words -> 100 points, FILLER_RATE_FOR_ZERO or more -> 0 points.
FILLER_RATE_FOR_ZERO = 8.0


# --------------------------------------------------------------------------
# Component scores (all 0-100)
# --------------------------------------------------------------------------
def pace_score(wpm):
    if wpm is None:
        return None
    if wpm < TARGET_WPM_MIN:
        gap = TARGET_WPM_MIN - wpm
    elif wpm > TARGET_WPM_MAX:
        gap = wpm - TARGET_WPM_MAX
    else:
        gap = 0
    return max(0.0, 100.0 - gap * PACE_POINTS_LOST_PER_WPM)


def filler_score(filler_count, word_count):
    if filler_count is None or not word_count:
        return None
    rate_per_100_words = 100.0 * filler_count / word_count
    return max(0.0, 100.0 - rate_per_100_words * (100.0 / FILLER_RATE_FOR_ZERO))


def _component_scores(speech: dict, visual: dict) -> dict:
    speech = speech or {}
    visual = visual or {}
    scores = {
        "script_accuracy": speech.get("script_accuracy"),
        "speaking_pace": pace_score(speech.get("speaking_pace_wpm")),
        "fluency": speech.get("fluency"),
        "eye_contact": visual.get("eye_contact"),
        "filler_words": filler_score(speech.get("filler_words"), speech.get("word_count")),
    }
    return {name: value for name, value in scores.items() if value is not None}


def fuse(speech: dict, visual: dict) -> dict:
    """Combine the available metrics into one 0-100 score.

    Returns {"score": int | None, "based_on": [metric names used]}.
    """
    scores = _component_scores(speech, visual)
    if not scores:
        return {"score": None, "based_on": []}
    total_weight = sum(WEIGHTS[name] for name in scores)
    weighted = sum(WEIGHTS[name] * value for name, value in scores.items())
    overall = round(weighted / total_weight)
    logger.info("[FUSION] score=%s based_on=%s", overall, sorted(scores))
    return {"score": max(0, min(100, overall)), "based_on": sorted(scores, key=list(WEIGHTS).index)}


# --------------------------------------------------------------------------
# Feedback - every line is derived from a measured value
# --------------------------------------------------------------------------
def _format_minutes(seconds):
    total = int(round(seconds))
    return f"{total // 60}m {total % 60:02d}s"


def generate_feedback(speech: dict, visual: dict, duration_seconds=None, target_minutes=None,
                      visual_failed=False) -> list:
    speech = speech or {}
    visual = visual or {}
    notes = []

    # ---- speaking pace
    wpm = speech.get("speaking_pace_wpm")
    if wpm is not None:
        if wpm < TARGET_WPM_MIN:
            gap = TARGET_WPM_MIN - wpm
            degree = "slightly below" if gap <= 15 else "below"
            notes.append(f"Your speaking pace ({wpm} WPM) was {degree} the {TARGET_WPM_MIN}-{TARGET_WPM_MAX} WPM target range.")
        elif wpm > TARGET_WPM_MAX:
            gap = wpm - TARGET_WPM_MAX
            degree = "slightly above" if gap <= 15 else "above"
            notes.append(f"Your speaking pace ({wpm} WPM) was {degree} the {TARGET_WPM_MIN}-{TARGET_WPM_MAX} WPM target range.")
        else:
            notes.append(f"Your speaking pace ({wpm} WPM) was within the {TARGET_WPM_MIN}-{TARGET_WPM_MAX} WPM target range.")

    # ---- script accuracy
    accuracy = speech.get("script_accuracy")
    if accuracy is not None:
        if accuracy >= 85:
            notes.append(f"Your script coverage was strong ({accuracy}% match with the prepared script).")
        elif accuracy >= 60:
            notes.append(f"You followed most of your script ({accuracy}% match). Check which parts you skipped or reworded.")
        else:
            notes.append(f"Only {accuracy}% of what you said matched the prepared script. "
                         "Practise the full script, or check the transcript in case speech recognition missed words.")

    # ---- filler words
    fillers = speech.get("filler_words")
    if fillers is not None:
        if fillers == 0:
            notes.append("No common filler words were detected in your transcript.")
        else:
            top = sorted((speech.get("filler_breakdown") or {}).items(), key=lambda item: -item[1])[:2]
            detail = ", ".join(f"'{word}' x{count}" for word, count in top)
            rate = 100.0 * fillers / max(1, speech.get("word_count") or 1)
            advice = " Try pausing silently instead." if rate >= 3 else ""
            notes.append(f"{fillers} filler word{'s' if fillers != 1 else ''} detected ({detail}).{advice}")

    # ---- visual
    face = visual.get("face_detection")
    eye = visual.get("eye_contact")
    if face is not None and face < 60:
        notes.append(f"Your face was detected in only {face}% of the sampled frames. "
                     "Better lighting and a camera at eye level make the visual analysis more reliable.")
    if eye is not None:
        if eye >= 75:
            notes.append("You maintained camera engagement during most sampled frames.")
        elif eye >= 40:
            notes.append(f"You were facing the camera in about {eye}% of sampled frames; try to look at the camera more consistently.")
        else:
            notes.append(f"You were facing the camera in only {eye}% of sampled frames; try to face the camera more.")

    gesture = visual.get("gesture_activity")
    if gesture == "low":
        notes.append("Gesture activity was low; natural hand movement can help emphasise key points.")
    elif gesture == "high":
        notes.append("Gesture activity was high; make sure your movement supports your message.")

    # ---- duration vs target
    if duration_seconds and target_minutes:
        target_seconds = target_minutes * 60.0
        unit = "minute" if target_minutes == 1 else "minutes"
        if abs(duration_seconds - target_seconds) <= 0.15 * target_seconds:
            notes.append(f"You finished close to your {target_minutes:g}-minute target ({_format_minutes(duration_seconds)}).")
        else:
            notes.append(f"Your presentation lasted {_format_minutes(duration_seconds)} against a target of {target_minutes:g} {unit}.")

    # ---- data-availability notes
    if speech.get("word_count") in (0, None):
        notes.append("No speech was recognised in this recording, so the score uses visual metrics only. "
                     "Live speech recognition works in Chrome and Edge.")
    if visual_failed:
        notes.append("The recording could not be analysed visually, so the score uses speech metrics only.")
    elif face == 0:
        notes.append("No face was detected in the sampled frames, so eye contact could not be estimated.")

    return notes


# --------------------------------------------------------------------------
# Report assembly + legacy upgrade
# --------------------------------------------------------------------------
def build_report(transcript, speech, visual, duration_seconds=None, target_minutes=None, visual_failed=False):
    """Return (metrics_dict_to_store, feedback_list)."""
    speech = speech or {}
    visual = visual or {}
    overall = fuse(speech, visual)
    metrics = {
        "version": REPORT_VERSION,
        "status": "completed" if overall["score"] is not None else "no_data",
        "transcript": transcript or "",
        "overall": overall,
        "speech": speech,
        "visual": visual,
    }
    feedback = generate_feedback(speech, visual, duration_seconds, target_minutes, visual_failed)
    return metrics, feedback


def upgrade_legacy_metrics(old: dict, duration_seconds=None, target_minutes=None):
    """Convert an attempt stored by the previous version of the app (with keys
    like `script_accuracy_pct` / `eye_contact_proxy_pct`, a debug `stages`
    block, an unavailable `temporal` block ...) to the current clean format.

    Only measured values are carried over. The old gesture level is dropped
    because it was computed from frames that were far apart. The overall
    score and feedback are recomputed with the current formula so every page
    shows one consistent number.
    """
    old = old or {}
    old_speech = old.get("speech") or {}
    old_visual = old.get("visual") or {}

    speech = {
        "word_count": old_speech.get("word_count"),
        "script_accuracy": old_speech.get("script_accuracy_pct"),
        "speaking_pace_wpm": old_speech.get("wpm"),
        "fluency": old_speech.get("fluency"),
        "filler_words": old_speech.get("filler_total"),
        "filler_breakdown": old_speech.get("filler_breakdown"),
    }
    visual = {
        "frames_analyzed": old_visual.get("frames_analyzed"),
        "face_detection": old_visual.get("face_detection_rate_pct"),
        "eye_contact": old_visual.get("eye_contact_proxy_pct"),
        "gesture_activity": None,
    }
    visual_failed = bool(old_visual.get("error")) or not old_visual
    if visual_failed:
        visual = {}
    return build_report(old.get("transcript", ""), speech, visual, duration_seconds, target_minutes,
                        visual_failed=visual_failed)
