"""
AutoRun v3 - Serves the React SPA.
"""

from pathlib import Path
from flask import Blueprint, send_from_directory

ui_bp = Blueprint("ui", __name__)
DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"


@ui_bp.route("/", defaults={"path": ""})
@ui_bp.route("/<path:path>")
def serve_spa(path):
    if path and (DIST_DIR / path).exists():
        return send_from_directory(str(DIST_DIR), path)
    return send_from_directory(str(DIST_DIR), "index.html")
