"""
AutoRun v3 - Application Entry Point
"""

import logging
import os

from flask import Flask, jsonify

import systemd_manager
from database import init_db, SessionLocal, Service
from git_updater import GitUpdateChecker
from routes import register_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("autorun")

app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("AUTORUN_SECRET_KEY", os.urandom(32))

register_routes(app)


@app.errorhandler(systemd_manager.SystemdOperationError)
def handle_systemd_error(e):
    return jsonify({"status": "error", "error": {"type": "SystemdOperationError", "message": str(e)}}), 500



@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "error": {"message": "Not found"}}), 404


@app.errorhandler(Exception)
def handle_generic_error(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({"status": "error", "error": {"type": type(e).__name__, "message": str(e)}}), 500


def init_app():
    init_db()
    logger.info("Database initialised")
    db = SessionLocal()
    try:
        count = db.query(Service).count()
        logger.info(f"{count} services in database")
    finally:
        db.close()
    GitUpdateChecker().start()
    logger.info("Git update checker started")


if __name__ == "__main__":
    init_app()
    port = int(os.environ.get("AUTORUN_PORT", 80))
    logger.info(f"Starting AutoRun v3 on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
