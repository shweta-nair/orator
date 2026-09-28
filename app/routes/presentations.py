from flask import Blueprint, request, jsonify
from app import db
from app.models import Presentation
from app.auth_utils import login_required

presentations_bp = Blueprint("presentations", __name__)

SCENARIOS = {"academic", "news", "flight", "advertisement", "speech", "general"}
DIFFICULTIES = {"beginner", "intermediate", "advanced"}
MAX_TARGET_MINUTES = 600


def _parse_target_minutes(value):
    """Blank -> (None, None); valid -> (minutes, None); invalid -> (None, error message)."""
    if value in (None, ""):
        return None, None
    try:
        minutes = float(value)
    except (TypeError, ValueError):
        return None, "Target duration must be a number of minutes."
    if not 0 < minutes <= MAX_TARGET_MINUTES:
        return None, f"Target duration must be between 0 and {MAX_TARGET_MINUTES} minutes."
    return minutes, None


@presentations_bp.get("")
@login_required
def list_presentations(user):
    items = Presentation.query.filter_by(user_id=user.id).order_by(Presentation.updated_at.desc()).all()
    return jsonify([p.to_dict() for p in items])


@presentations_bp.post("")
@login_required
def create_presentation(user):
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "invalid_input", "message": "Give your presentation a title."}), 400

    target, target_error = _parse_target_minutes(data.get("target_duration_minutes"))
    if target_error:
        return jsonify({"error": "invalid_input", "message": target_error}), 400

    p = Presentation(
        user_id=user.id,
        title=title,
        script=data.get("script", ""),
        target_duration_minutes=target,
        scenario=data.get("scenario") if data.get("scenario") in SCENARIOS else "general",
        difficulty=data.get("difficulty") if data.get("difficulty") in DIFFICULTIES else "beginner",
    )
    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201


def _get_owned_or_404(user, presentation_id):
    p = Presentation.query.filter_by(id=presentation_id, user_id=user.id).first()
    return p


@presentations_bp.get("/<int:presentation_id>")
@login_required
def get_presentation(user, presentation_id):
    p = _get_owned_or_404(user, presentation_id)
    if not p:
        return jsonify({"error": "not_found", "message": "Presentation not found."}), 404
    return jsonify(p.to_dict(with_attempts=True))


@presentations_bp.put("/<int:presentation_id>")
@login_required
def update_presentation(user, presentation_id):
    p = _get_owned_or_404(user, presentation_id)
    if not p:
        return jsonify({"error": "not_found", "message": "Presentation not found."}), 404
    data = request.get_json(silent=True) or {}
    if "title" in data and data["title"].strip():
        p.title = data["title"].strip()
    if "script" in data:
        p.script = data["script"]
    if "scenario" in data and data["scenario"] in SCENARIOS:
        p.scenario = data["scenario"]
    if "difficulty" in data and data["difficulty"] in DIFFICULTIES:
        p.difficulty = data["difficulty"]
    if "target_duration_minutes" in data:
        target, target_error = _parse_target_minutes(data["target_duration_minutes"])
        if target_error:
            return jsonify({"error": "invalid_input", "message": target_error}), 400
        p.target_duration_minutes = target
    db.session.commit()
    return jsonify(p.to_dict())


@presentations_bp.delete("/<int:presentation_id>")
@login_required
def delete_presentation(user, presentation_id):
    p = _get_owned_or_404(user, presentation_id)
    if not p:
        return jsonify({"error": "not_found", "message": "Presentation not found."}), 404
    db.session.delete(p)
    db.session.commit()
    return jsonify({"message": "Deleted."})
