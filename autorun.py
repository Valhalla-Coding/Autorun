"""
AutoRun v2 - Application Entry Point

Creates the Flask app, registers error handlers and blueprints, initialises
configuration, and starts the background Git update checker.
"""

import logging

from flask import Flask, jsonify

import config
import state
import systemd_manager
from git_updater import GitUpdateChecker
from routes import register_routes

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

register_routes(app)


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(state.AutoRunException)
def handle_autorun_error(e):
    return jsonify({"status": "error", "error": {"type": "NotFound", "message": str(e)}}), 404


@app.errorhandler(config.ConfigValidationError)
def handle_config_validation_error(e):
    return jsonify({"status": "error", "error": {"type": "ConfigValidationError", "message": str(e)}}), 400


@app.errorhandler(systemd_manager.SystemdOperationError)
def handle_systemd_operation_error(e):
    return jsonify({"status": "error", "error": {"type": "SystemdOperationError", "message": str(e)}}), 500


@app.errorhandler(systemd_manager.PermissionError)
def handle_permission_error(e):
    return jsonify({"status": "error", "error": {
        "type": "PermissionError",
        "message": str(e),
        "hint": "AutoRun may need sudo privileges. Check installation and sudoers configuration."
    }}), 403


@app.errorhandler(Exception)
def handle_generic_error(e):
    state.logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({"status": "error", "error": {"type": type(e).__name__, "message": str(e)}}), 500


# ============================================================================
# Initialisation
# ============================================================================

def init_app():
    try:
        if not state.CONFIG_PATH.exists():
            state.logger.info("Configuration file not found, creating default")
            state.current_config = config.create_default_config()
            config.save_config(state.current_config, state.CONFIG_PATH)
        else:
            state.logger.info(f"Loading configuration from {state.CONFIG_PATH}")
            state.current_config = config.load_config(state.CONFIG_PATH)

        errors = config.validate_config(state.current_config, strict=True)
        if errors:
            state.logger.warning("Configuration has validation errors:")
            for error in errors:
                state.logger.warning(f"  - {error}")

        state.logger.info(f"Loaded {len(state.current_config.services)} services")

        GitUpdateChecker().start()
        state.logger.info("Git update checker started (5-minute interval)")

    except Exception as e:
        state.logger.error(f"Failed to initialise application: {e}")
        raise


if __name__ == '__main__':
    init_app()
    port = state.current_config.metadata.dashboard_port if state.current_config else 80
    state.logger.info(f"Starting AutoRun v2 on port {port}")
    state.logger.info("Dashboard: http://localhost" + (f":{port}" if port != 80 else ""))
    app.run(host='0.0.0.0', port=port, debug=False)
