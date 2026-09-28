from functools import wraps
from flask import session, jsonify
from app.models import User


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({"error": "unauthorized", "message": "Log in to continue."}), 401
        kwargs["user"] = user
        return fn(*args, **kwargs)
    return wrapper
