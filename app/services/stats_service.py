"""
Aggregations shared by the Dashboard and Progress pages.

Pure functions over attempt summary dicts (see `Attempt.summary()`), so both
pages - and the report - are computed from the same stored attempt data.
Input lists must be in chronological order (oldest first).
"""


def _completed(attempts):
    return [a for a in attempts if a.get("status") == "completed" and a.get("overall_score") is not None]


def _average(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values)) if values else None


def dashboard_stats(attempts, presentation_count):
    done = _completed(attempts)
    latest = done[-1] if done else None
    return {
        "presentation_count": presentation_count,
        "practice_sessions": len(done),
        "latest_score": latest["overall_score"] if latest else None,
        "latest_attempt_id": latest["id"] if latest else None,
        "recent": list(reversed(done))[:5],
    }


def progress_stats(attempts):
    done = _completed(attempts)
    scores = [a["overall_score"] for a in done]
    return {
        "sessions": len(done),
        "average_score": _average(scores),
        "latest_score": scores[-1] if scores else None,
        "best_score": max(scores) if scores else None,
        "average_script_accuracy": _average(a.get("script_accuracy") for a in done),
        "average_speaking_pace_wpm": _average(a.get("speaking_pace_wpm") for a in done),
        "average_eye_contact": _average(a.get("eye_contact") for a in done),
        "average_fluency": _average(a.get("fluency") for a in done),
        "attempts": [dict(a, attempt_number=i + 1) for i, a in enumerate(done)],
    }
