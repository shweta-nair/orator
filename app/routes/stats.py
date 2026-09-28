"""Read-only endpoints behind the Dashboard, History and Progress pages.

All three are built from the same stored Attempt rows (Attempt.summary()), so
a score can never differ between pages.
"""
from flask import Blueprint, jsonify

from app.models import Presentation, Attempt
from app.auth_utils import login_required
from app.services import stats_service, vision_service

stats_bp = Blueprint("stats", __name__)


def _user_attempt_summaries(user):
    """All of the user's attempts as summary dicts, oldest first."""
    attempts = (
        Attempt.query.join(Presentation, Attempt.presentation_id == Presentation.id)
        .filter(Presentation.user_id == user.id)
        .all()
    )
    attempts.sort(key=lambda a: (a.created_at, a.id))
    return [a.summary() for a in attempts]


@stats_bp.get("/dashboard")
@login_required
def dashboard(user):
    presentation_count = Presentation.query.filter_by(user_id=user.id).count()
    data = stats_service.dashboard_stats(_user_attempt_summaries(user), presentation_count)
    data["analysis_ready"] = vision_service.is_ready()
    return jsonify(data)


@stats_bp.get("/history")
@login_required
def history(user):
    """Every presentation with its attempts (newest attempt first)."""
    presentations = Presentation.query.filter_by(user_id=user.id).all()
    items = []
    for p in presentations:
        row = p.to_dict()
        row.pop("script", None)
        row["attempts"] = list(reversed([a.summary() for a in p.sorted_attempts()]))
        row["last_activity"] = row["attempts"][0]["created_at"] if row["attempts"] else row["created_at"]
        items.append(row)
    items.sort(key=lambda r: r["last_activity"], reverse=True)
    return jsonify({"presentations": items})


@stats_bp.get("/progress")
@login_required
def progress(user):
    return jsonify(stats_service.progress_stats(_user_attempt_summaries(user)))
