import logging
import os
import tempfile
import json

from flask import Blueprint, request, jsonify

from app import db
from app.models import Presentation, Attempt
from app.auth_utils import login_required
from app.services import speech_service, vision_service, fusion_service

attempts_bp = Blueprint("attempts", __name__)
logger = logging.getLogger(__name__)


def _read_submission():
    """Return (payload_dict, video_file_or_None).

    Preferred request: multipart/form-data with
        payload  JSON string  {"transcript": "...", "duration_seconds": 66.2}
        video    the MediaRecorder file (camera + microphone in one WebM)
    A plain JSON body (transcript + duration only, no video) is also accepted.
    """
    if request.content_type and "multipart/form-data" in request.content_type:
        payload = json.loads(request.form.get("payload", "{}"))
        return payload, request.files.get("video")
    return (request.get_json(silent=True) or {}), None


@attempts_bp.post("/presentations/<int:presentation_id>/attempts")
@login_required
def submit_attempt(user, presentation_id):
    """Analyse a recording and save the result as an Attempt.

        recording -> speech metrics + visual metrics -> fusion -> score -> feedback -> database
    """
    p = Presentation.query.filter_by(id=presentation_id, user_id=user.id).first()
    if not p:
        return jsonify({"error": "not_found", "message": "Presentation not found."}), 404

    try:
        payload, video_file = _read_submission()
        transcript = str(payload.get("transcript") or "")
        duration_seconds = float(payload.get("duration_seconds") or 0)
    except (ValueError, TypeError, json.JSONDecodeError):
        return jsonify({"error": "invalid_payload", "message": "The recording data was not valid."}), 400
    if duration_seconds < 0:
        duration_seconds = 0

    logger.info("[ATTEMPT] user=%s presentation=%s duration=%.1fs transcript_words=%s video=%s",
                user.id, p.id, duration_seconds, len(transcript.split()), bool(video_file))

    video_path = None
    try:
        # ---- speech (transcript based)
        speech = speech_service.analyze_transcript(transcript, p.script, duration_seconds)

        # ---- visual (OpenCV samples ~1 frame/second from the recorded video)
        visual, visual_failed = {}, False
        if video_file:
            try:
                fd, video_path = tempfile.mkstemp(suffix=".webm")
                os.close(fd)
                video_file.save(video_path)
                visual = vision_service.analyze_video(video_path, duration_seconds)
            except Exception:
                logger.exception("[VISION] Analysis failed")
                visual, visual_failed = {}, True

        # ---- fusion + feedback
        metrics, feedback = fusion_service.build_report(
            transcript, speech, visual, duration_seconds, p.target_duration_minutes, visual_failed)

        if metrics["overall"]["score"] is None:
            return jsonify({
                "error": "nothing_measured",
                "message": "Nothing could be measured from this recording. Check that your microphone "
                           "is working and your face is visible to the camera, then try again.",
            }), 422

        # ---- persist: the database is the single source of truth for every page
        attempt = Attempt(presentation_id=p.id, duration_seconds=duration_seconds,
                          metrics=metrics, feedback=feedback)
        db.session.add(attempt)
        db.session.commit()
        logger.info("[ATTEMPT] saved id=%s score=%s", attempt.id, metrics["overall"]["score"])
        return jsonify(attempt.to_dict()), 201
    except Exception:
        db.session.rollback()
        logger.exception("[ATTEMPT] Analysis failed for presentation=%s", presentation_id)
        return jsonify({"error": "analysis_failed",
                        "message": "Analysis failed. Check the server logs for details."}), 500
    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                logger.warning("[ATTEMPT] Could not delete temporary video %s", video_path)


@attempts_bp.get("/presentations/<int:presentation_id>/attempts")
@login_required
def list_attempts(user, presentation_id):
    p = Presentation.query.filter_by(id=presentation_id, user_id=user.id).first()
    if not p:
        return jsonify({"error": "not_found", "message": "Presentation not found."}), 404
    return jsonify([a.summary() for a in p.sorted_attempts()])


@attempts_bp.get("/attempts/<int:attempt_id>")
@login_required
def get_attempt(user, attempt_id):
    a = Attempt.query.join(Presentation, Attempt.presentation_id == Presentation.id).filter(
        Attempt.id == attempt_id, Presentation.user_id == user.id
    ).first()
    if not a:
        return jsonify({"error": "not_found", "message": "Attempt not found."}), 404
    return jsonify(a.to_dict())
