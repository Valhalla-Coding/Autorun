"""
AutoRun v3 - Auth Routes

POST /api/auth/login   — username + password → session token
POST /api/auth/logout  — invalidate token
GET  /api/auth/me      — return current user info
"""

from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, jsonify, request, g

from database import SessionLocal, User, UserSession

auth_bp = Blueprint("auth", __name__)


def get_token_from_request():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return request.cookies.get("autorun_token")


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return jsonify({"status": "error", "error": {"message": "Authentication required"}}), 401

        db = SessionLocal()
        session = db.query(UserSession).filter_by(token=token).first()

        if not session or session.is_expired:
            db.close()
            return jsonify({"status": "error", "error": {"message": "Invalid or expired session"}}), 401

        g.user = session.user
        g.db = db
        g.token = token

        try:
            return f(*args, **kwargs)
        finally:
            db.close()

    return decorated


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "error": {"message": "Request body required"}}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"status": "error", "error": {"message": "Username and password required"}}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({"status": "error", "error": {"message": "Invalid username or password"}}), 401

        session = UserSession.create(user_id=user.id)
        db.add(session)
        user.last_login = datetime.now(timezone.utc)
        db.commit()

        response = jsonify({
            "status": "success",
            "message": "Logged in successfully",
            "data": {
                "token": session.token,
                "user": user.to_dict(),
                "expires_at": session.expires_at.isoformat(),
            }
        })
        response.set_cookie(
            "autorun_token", session.token,
            httponly=True, samesite="Lax",
            max_age=30 * 24 * 3600
        )
        return response
    finally:
        db.close()


@auth_bp.route("/api/auth/logout", methods=["POST"])
@require_auth
def logout():
    db = g.db
    session = db.query(UserSession).filter_by(token=g.token).first()
    if session:
        db.delete(session)
        db.commit()
    response = jsonify({"status": "success", "message": "Logged out successfully"})
    response.delete_cookie("autorun_token")
    return response


@auth_bp.route("/api/auth/me", methods=["GET"])
@require_auth
def me():
    return jsonify({"status": "success", "data": {"user": g.user.to_dict()}})
