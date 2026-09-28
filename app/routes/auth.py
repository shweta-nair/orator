from flask import Blueprint, request, jsonify, session
from app import db
from app.models import User
from app.auth_utils import login_required, current_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    password = data.get("password") or ""

    if not email or not name or len(password) < 8:
        return jsonify({"error": "invalid_input",
                         "message": "Name, a valid email, and a password of at least 8 characters are required."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email_taken", "message": "An account with that email already exists."}), 409

    user = User(email=email, name=name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    session["user_id"] = user.id
    return jsonify(user.to_dict()), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid_credentials", "message": "Email or password is incorrect."}), 401
    session["user_id"] = user.id
    return jsonify(user.to_dict())


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out."})


@auth_bp.get("/me")
def me():
    user = current_user()
    if not user:
        return jsonify({"user": None})
    return jsonify({"user": user.to_dict()})
