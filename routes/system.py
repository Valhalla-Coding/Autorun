"""
AutoRun v2 - System API Routes

System-level controls (reload, daemon-reload, status, health) and file browser.
"""

import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

import config
import state
import systemd_manager

system_bp = Blueprint('system', __name__)

ALLOWED_BROWSE_PATHS = ('/home', '/opt', '/srv', '/var/www', '/mnt')


# ============================================================================
# System Management
# ============================================================================

@system_bp.route('/api/system/reload', methods=['POST'])
def reload_config():
    try:
        state.reload_config()
        for svc in state.current_config.services:
            try:
                systemd_manager.write_service_file(svc, state.current_config.metadata.default_user)
            except Exception as e:
                state.logger.error(f"Failed to regenerate service file for '{svc.name}': {e}")
        systemd_manager.daemon_reload()
        state.logger.info("Configuration reloaded and systemd files regenerated")
        return jsonify({
            "status": "success",
            "message": "Configuration reloaded successfully",
            "data": {"services_count": len(state.current_config.services)}
        })
    except Exception as e:
        state.logger.error(f"Failed to reload configuration: {e}")
        raise


@system_bp.route('/api/system/daemon-reload', methods=['POST'])
def daemon_reload():
    systemd_manager.daemon_reload()
    state.logger.info("Executed systemctl daemon-reload")
    return jsonify({"status": "success", "message": "systemctl daemon-reload executed successfully"})


@system_bp.route('/api/system/status', methods=['GET'])
def system_status():
    services_data = []
    for svc in state.current_config.services:
        try:
            info = systemd_manager.get_service_status(svc.name)
            services_data.append({"name": svc.name, "status": info["status"]})
        except Exception:
            services_data.append({"name": svc.name, "status": "unknown"})

    total = len(services_data)
    return jsonify({
        "status": "success",
        "data": {
            "total_services": total,
            "running": sum(1 for s in services_data if s['status'] == 'running'),
            "stopped": sum(1 for s in services_data if s['status'] == 'stopped'),
            "failed":  sum(1 for s in services_data if s['status'] == 'failed'),
            "services": services_data,
        }
    })


@system_bp.route('/api/settings/dashboard-port', methods=['GET'])
def get_dashboard_port():
    port = state.current_config.metadata.dashboard_port if state.current_config else 8080
    return jsonify({"status": "success", "data": {"port": port}})


@system_bp.route('/api/settings/dashboard-port', methods=['PUT'])
def set_dashboard_port():
    data = request.get_json()
    if not data or 'port' not in data:
        return jsonify({"status": "error", "error": {"message": "port is required"}}), 400

    try:
        port = int(data['port'])
    except (ValueError, TypeError):
        return jsonify({"status": "error", "error": {"message": "port must be an integer"}}), 400

    if not (1 <= port <= 65535):
        return jsonify({"status": "error", "error": {"message": "port must be between 1 and 65535"}}), 400

    state.current_config.metadata.dashboard_port = port
    config.save_config(state.current_config, state.CONFIG_PATH)
    state.logger.info(f"Dashboard port changed to {port}, restarting autorun service")

    try:
        subprocess.Popen(['sudo', 'systemctl', 'restart', 'autorun.service'])
    except Exception as e:
        state.logger.warning(f"Could not restart autorun.service: {e}")

    return jsonify({
        "status": "success",
        "message": f"Port saved to {port}. The server is restarting — reconnect at the new port shortly."
    })


@system_bp.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "success",
        "message": "AutoRun v2 is running",
        "data": {
            "version": state.current_config.metadata.version if state.current_config else "unknown",
            "services_count": len(state.current_config.services) if state.current_config else 0,
        }
    })


# ============================================================================
# File / Folder Browser
# ============================================================================

def _check_allowed(path_str: str) -> bool:
    return any(path_str == a or path_str.startswith(a + '/') for a in ALLOWED_BROWSE_PATHS)


@system_bp.route('/api/browse/folders', methods=['GET'])
def browse_folders():
    start_path = request.args.get('path', str(Path.home()))
    try:
        path = Path(start_path).resolve()
        path_str = str(path)

        if not _check_allowed(path_str):
            return jsonify({"status": "error", "error": {"message": f"Access denied: {path_str}"}}), 403

        if not path.exists() or not path.is_dir():
            return jsonify({"status": "error", "error": {"message": "Path does not exist or is not a directory"}}), 400

        folders = []
        try:
            folders = [{"name": i.name, "path": str(i)}
                       for i in sorted(path.iterdir()) if i.is_dir() and not i.name.startswith('.')]
        except PermissionError:
            pass

        parent = str(path.parent) if path != path.parent else None
        return jsonify({
            "status": "success",
            "data": {"current_path": path_str, "parent": parent, "folders": folders}
        })
    except Exception as e:
        state.logger.error(f"Error browsing folders: {e}")
        return jsonify({"status": "error", "error": {"message": str(e)}}), 500


@system_bp.route('/api/browse/files', methods=['GET'])
def browse_files():
    folder_path = request.args.get('path')
    if not folder_path:
        return jsonify({"status": "error", "error": {"message": "Path parameter is required"}}), 400

    try:
        path = Path(folder_path).resolve()
        if not path.exists() or not path.is_dir():
            return jsonify({"status": "error", "error": {"message": "Path does not exist or is not a directory"}}), 400

        files = []
        try:
            files = [{"name": i.name, "path": str(i)}
                     for i in sorted(path.iterdir()) if i.is_file() and i.suffix == '.py']
        except PermissionError:
            pass

        return jsonify({"status": "success", "data": {"folder": str(path), "files": files}})
    except Exception as e:
        state.logger.error(f"Error browsing files: {e}")
        return jsonify({"status": "error", "error": {"message": str(e)}}), 500
