import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
logger = logging.getLogger(__name__)


def _ensure_schema():
    """Add columns introduced after the first release to an existing database
    (db.create_all() only creates missing tables, never missing columns)."""
    from sqlalchemy import inspect, text
    columns = {c["name"] for c in inspect(db.engine).get_columns("presentation")}
    if "target_duration_minutes" not in columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE presentation ADD COLUMN target_duration_minutes FLOAT"))
        logger.info("[DATABASE] Added presentation.target_duration_minutes")


def _upgrade_legacy_attempts():
    """Convert attempts saved by the previous version (different metric names,
    debug fields) into the current report format, once."""
    from app.models import Attempt
    from app.services import fusion_service
    upgraded = 0
    for attempt in Attempt.query.all():
        if (attempt.metrics or {}).get("version") == fusion_service.REPORT_VERSION:
            continue
        target = attempt.presentation.target_duration_minutes if attempt.presentation else None
        metrics, feedback = fusion_service.upgrade_legacy_metrics(attempt.metrics, attempt.duration_seconds, target)
        attempt.metrics = metrics
        attempt.feedback = feedback
        upgraded += 1
    if upgraded:
        db.session.commit()
        logger.info("[DATABASE] Upgraded %s older attempt(s) to the current report format", upgraded)


def create_app(config_overrides=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder="../frontend",
        static_url_path=""
    )
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", f"sqlite:///{os.path.join(app.instance_path, 'coach.db')}"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_SAMESITE="Lax",
        # Safety limit only. The browser uploads a single compressed WebM
        # (camera + microphone) and no frame images, so requests stay small.
        MAX_CONTENT_LENGTH=200 * 1024 * 1024,
    )
    if config_overrides:
        app.config.update(config_overrides)

    # Postgres URLs from some providers use postgres:// - SQLAlchemy needs postgresql://
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("postgres://"):
        app.config["SQLALCHEMY_DATABASE_URI"] = uri.replace("postgres://", "postgresql://", 1)

    db.init_app(app)
    # IMPORTANT: never leave this as CORS(app, supports_credentials=True) with
    # no origins list. Flask-CORS will then reflect back *any* request's
    # Origin header while also sending Access-Control-Allow-Credentials: true,
    # which lets any website read/write this API using a logged-in user's
    # session cookie. Only the origins below (or CORS_ORIGINS) are trusted.
    default_origins = "http://localhost:5000,http://127.0.0.1:5000"
    allowed_origins = [
        o.strip() for o in os.environ.get("CORS_ORIGINS", default_origins).split(",") if o.strip()
    ]
    CORS(app, supports_credentials=True, origins=allowed_origins)

    from app.routes.auth import auth_bp
    from app.routes.presentations import presentations_bp
    from app.routes.attempts import attempts_bp
    from app.routes.stats import stats_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(presentations_bp, url_prefix="/api/presentations")
    app.register_blueprint(attempts_bp, url_prefix="/api")
    app.register_blueprint(stats_bp, url_prefix="/api")

    @app.after_request
    def no_store_for_api(response):
        # API answers depend on the logged-in user and must never be reused
        # from the browser cache (e.g. after signing out).
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.errorhandler(404)
    def not_found(e):
        return {"error": "not_found", "message": "That resource doesn't exist."}, 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        logger.error("[413] Request exceeded MAX_CONTENT_LENGTH=%s bytes", app.config["MAX_CONTENT_LENGTH"])
        return jsonify({
            "error": "file_too_large",
            "message": "Recording is too large. Please try a shorter recording.",
            "max_mb": app.config["MAX_CONTENT_LENGTH"] / 1024 / 1024,
        }), 413

    @app.errorhandler(500)
    def server_error(e):
        return {"error": "server_error",
                "message": "The server had a problem. Check the server logs for details."}, 500

    with app.app_context():
        db.create_all()
        _ensure_schema()
        try:
            _upgrade_legacy_attempts()
        except Exception:
            db.session.rollback()
            logger.exception("[DATABASE] Could not upgrade older attempts; they will be left unchanged")

    @app.get("/")
    def home():
        return app.send_static_file("index.html")

    return app
