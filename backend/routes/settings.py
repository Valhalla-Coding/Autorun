"""
AutoRun v3 - Settings Routes

GET  /api/settings        — return all settings (values masked if sensitive)
PUT  /api/settings        — upsert one or more key/value pairs
"""

from flask import Blueprint, jsonify, request, g
from database import Setting
from routes.auth import require_auth

import logging
logger = logging.getLogger("autorun")

settings_bp = Blueprint("settings", __name__)

SENSITIVE = {"github_token"}


def _mask(key, value):
    if key in SENSITIVE and value:
        return "•" * 8
    return value


@settings_bp.route("/api/settings", methods=["GET"])
@require_auth
def get_settings():
    rows = g.db.query(Setting).all()
    data = {r.key: _mask(r.key, r.value) for r in rows}
    return jsonify({"status": "success", "data": data})


@settings_bp.route("/api/settings", methods=["PUT"])
@require_auth
def update_settings():
    body = request.get_json()
    if not body or not isinstance(body, dict):
        return jsonify({"status": "error", "error": {"message": "JSON object required"}}), 400

    db = g.db
    for key, value in body.items():
        # Don't overwrite a real token with the masked placeholder
        if value == "•" * 8:
            continue
        row = db.query(Setting).filter_by(key=key).first()
        if row:
            row.value = value or None
        else:
            db.add(Setting(key=key, value=value or None))

    db.commit()
    return jsonify({"status": "success", "message": "Settings saved"})


def get_setting(db, key: str, fallback: str = None) -> str:
    """Helper used by other routes to read a setting."""
    row = db.query(Setting).filter_by(key=key).first()
    return row.value if row and row.value else fallback
