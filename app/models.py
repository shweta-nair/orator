from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from app import db


def _utcnow():
    # Stored as naive UTC (like datetime.utcnow) without the deprecated call.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso(dt):
    """ISO-8601 with an explicit UTC marker so browsers do not read it as local time."""
    return dt.isoformat() + "Z" if dt else None


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow)

    presentations = db.relationship(
        "Presentation", backref="owner", cascade="all, delete-orphan", lazy=True
    )

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    def to_dict(self):
        return {"id": self.id, "email": self.email, "name": self.name,
                "created_at": _iso(self.created_at)}


class Presentation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    scenario = db.Column(db.String(80), default="general")  # academic, news, flight, advertisement, speech, general
    script = db.Column(db.Text, nullable=False, default="")
    difficulty = db.Column(db.String(20), default="beginner")
    target_duration_minutes = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    attempts = db.relationship(
        "Attempt", backref="presentation", cascade="all, delete-orphan", lazy=True,
        order_by="Attempt.created_at",
    )

    def sorted_attempts(self):
        """Oldest first; id breaks ties between attempts created in the same instant."""
        return sorted(self.attempts, key=lambda a: (a.created_at, a.id))

    def latest_attempt(self):
        attempts = self.sorted_attempts()
        return attempts[-1] if attempts else None

    def to_dict(self, with_attempts=False):
        latest = self.latest_attempt()
        d = {
            "id": self.id, "title": self.title, "scenario": self.scenario,
            "script": self.script, "difficulty": self.difficulty,
            "target_duration_minutes": self.target_duration_minutes,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
            "attempt_count": len(self.attempts),
            "latest_attempt_id": latest.id if latest else None,
            "latest_score": latest.overall_score if latest else None,
        }
        if with_attempts:
            d["attempts"] = [a.summary() for a in self.sorted_attempts()]
        return d


class Attempt(db.Model):
    """One recorded + analysed practice run of a presentation.

    `metrics` holds the analysis result (format version 2, see
    fusion_service.build_report): transcript, overall, speech, visual.
    Everything the UI shows for an attempt - report, history, dashboard,
    progress - is read from here through summary()/to_dict().
    """
    id = db.Column(db.Integer, primary_key=True)
    presentation_id = db.Column(db.Integer, db.ForeignKey("presentation.id"), nullable=False)
    duration_seconds = db.Column(db.Float, default=0)
    metrics = db.Column(db.JSON, nullable=False, default=dict)
    feedback = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime, default=_utcnow)

    @property
    def status(self):
        return (self.metrics or {}).get("status", "completed")

    @property
    def overall_score(self):
        return ((self.metrics or {}).get("overall") or {}).get("score")

    def summary(self):
        """Compact row used by history, dashboard and progress."""
        m = self.metrics or {}
        speech = m.get("speech") or {}
        visual = m.get("visual") or {}
        p = self.presentation
        return {
            "id": self.id,
            "presentation_id": self.presentation_id,
            "presentation_title": p.title if p else None,
            "scenario": p.scenario if p else None,
            "duration_seconds": self.duration_seconds,
            "created_at": _iso(self.created_at),
            "status": self.status,
            "overall_score": self.overall_score,
            "script_accuracy": speech.get("script_accuracy"),
            "speaking_pace_wpm": speech.get("speaking_pace_wpm"),
            "fluency": speech.get("fluency"),
            "filler_words": speech.get("filler_words"),
            "eye_contact": visual.get("eye_contact"),
        }

    def to_dict(self, summary=False):
        if summary:
            return self.summary()
        m = self.metrics or {}
        p = self.presentation
        return {
            "id": self.id,
            "presentation_id": self.presentation_id,
            "presentation": {"id": p.id, "title": p.title, "scenario": p.scenario} if p else None,
            "duration_seconds": self.duration_seconds,
            "created_at": _iso(self.created_at),
            "status": self.status,
            "overall": m.get("overall") or {"score": None, "based_on": []},
            "speech": m.get("speech") or {},
            "visual": m.get("visual") or {},
            "transcript": m.get("transcript", ""),
            "feedback": self.feedback or [],
        }
