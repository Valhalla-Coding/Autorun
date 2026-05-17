"""
AutoRun v2 - Services API Routes

CRUD for service configuration and start/stop/restart/pull/enable/disable control.
"""

import re
import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

import config
import state
import systemd_manager
from git_updater import git_pull_and_restart

services_bp = Blueprint('services', __name__)


# ============================================================================
# Service CRUD
# ============================================================================

@services_bp.route('/api/services', methods=['GET'])
def list_services():
    services_data = []
    for svc in state.current_config.services:
        try:
            status_info = systemd_manager.get_service_status(svc.name)
            services_data.append({"name": svc.name, "config": svc.to_dict(), **status_info})
        except Exception as e:
            state.logger.error(f"Error getting status for service '{svc.name}': {e}")
            services_data.append({
                "name": svc.name, "config": svc.to_dict(),
                "status": "unknown", "active": False, "enabled": svc.enabled,
                "pid": None, "uptime": "N/A", "memory_mb": 0.0
            })

    total = len(services_data)
    return jsonify({
        "status": "success",
        "data": {
            "services": services_data,
            "total": total,
            "running": sum(1 for s in services_data if s['status'] == 'running'),
            "stopped": sum(1 for s in services_data if s['status'] == 'stopped'),
            "failed":  sum(1 for s in services_data if s['status'] == 'failed'),
        }
    })


@services_bp.route('/api/services/<service_name>', methods=['GET'])
def get_service(service_name: str):
    svc = state.find_service(service_name)
    status_info = systemd_manager.get_service_status(service_name)
    return jsonify({
        "status": "success",
        "data": {"name": svc.name, "config": svc.to_dict(), **status_info}
    })


@services_bp.route('/api/services', methods=['POST'])
def create_service():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "error": {"message": "Request body is required"}}), 400

    if 'name' not in data:
        return jsonify({"status": "error", "error": {"message": "Field 'name' is required"}}), 400

    service_name = data['name']
    if not re.match(r'^[a-z0-9-]+$', service_name):
        return jsonify({"status": "error", "error": {
            "message": "Invalid service name",
            "details": "Use only lowercase letters, numbers, and hyphens"
        }}), 400

    if len(service_name) > 64:
        return jsonify({"status": "error", "error": {"message": "Service name too long (max 64 characters)"}}), 400

    if 'folder' not in data:
        return jsonify({"status": "error", "error": {"message": "Field 'folder' is required"}}), 400

    data.setdefault('entrypoint', 'run.py')

    try:
        service = config.ServiceConfig(**data)
    except TypeError as e:
        return jsonify({"status": "error", "error": {"message": f"Invalid service configuration: {e}"}}), 400

    if service.name in [s.name for s in state.current_config.services]:
        return jsonify({"status": "error", "error": {"message": f"Service '{service.name}' already exists"}}), 409

    # Clone GitHub repo if URL provided and folder doesn't exist yet
    if service.github_url and not Path(service.folder).exists():
        try:
            clone = subprocess.run(
                ['git', 'clone', service.github_url, service.folder],
                capture_output=True, text=True, timeout=120
            )
            if clone.returncode != 0:
                return jsonify({"status": "error", "error": {"message": f"git clone failed: {clone.stderr.strip()}"}}), 500

            sha = subprocess.run(
                ['git', '-C', service.folder, 'rev-parse', 'HEAD'],
                capture_output=True, text=True
            )
            if sha.returncode == 0:
                service.last_commit_sha = sha.stdout.strip()

            state.logger.info(f"Cloned {service.github_url} → {service.folder}")
        except subprocess.TimeoutExpired:
            return jsonify({"status": "error", "error": {"message": "git clone timed out"}}), 500
        except Exception as e:
            return jsonify({"status": "error", "error": {"message": f"Clone error: {e}"}}), 500

    state.current_config.services.append(service)

    errors = config.validate_config(state.current_config, strict=False)
    if errors:
        state.current_config.services.remove(service)
        return jsonify({"status": "error", "error": {
            "message": "Configuration validation failed", "details": errors
        }}), 400

    config.save_config(state.current_config, state.CONFIG_PATH)
    state.logger.info(f"Created service: {service.name}")

    try:
        systemd_manager.write_service_file(service, state.current_config.metadata.default_user)
        systemd_manager.daemon_reload()
        if service.enabled:
            systemd_manager.enable_service(service.name, now=False)
    except Exception as e:
        state.logger.error(f"Failed to create systemd service: {e}")
        return jsonify({"status": "error", "error": {
            "message": f"Service saved but systemd setup failed: {e}",
            "hint": "Service is saved but may not be operational"
        }}), 500

    return jsonify({
        "status": "success",
        "message": f"Service '{service.name}' created successfully",
        "data": service.to_dict()
    }), 201


@services_bp.route('/api/services/<service_name>', methods=['PUT'])
def update_service(service_name: str):
    svc = state.find_service(service_name)
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "error": {"message": "Request body is required"}}), 400

    for key, value in data.items():
        if hasattr(svc, key) and key != 'name':
            setattr(svc, key, value)

    errors = config.validate_config(state.current_config, strict=False)
    if errors:
        return jsonify({"status": "error", "error": {
            "message": "Configuration validation failed", "details": errors
        }}), 400

    config.save_config(state.current_config, state.CONFIG_PATH)
    state.logger.info(f"Updated service: {service_name}")

    try:
        systemd_manager.write_service_file(svc, state.current_config.metadata.default_user)
        systemd_manager.daemon_reload()
    except Exception as e:
        state.logger.error(f"Failed to update systemd service: {e}")
        return jsonify({"status": "error", "error": {
            "message": f"Configuration updated but systemd setup failed: {e}"
        }}), 500

    return jsonify({
        "status": "success",
        "message": f"Service '{service_name}' updated successfully",
        "data": svc.to_dict()
    })


@services_bp.route('/api/services/<service_name>', methods=['DELETE'])
def delete_service(service_name: str):
    svc = state.find_service(service_name)

    try:
        if systemd_manager.is_service_active(service_name):
            systemd_manager.stop_service(service_name)
    except Exception as e:
        state.logger.warning(f"Failed to stop service before deletion: {e}")

    try:
        if systemd_manager.is_service_enabled(service_name):
            systemd_manager.disable_service(service_name, now=False)
    except Exception as e:
        state.logger.warning(f"Failed to disable service before deletion: {e}")

    try:
        systemd_manager.delete_service_file(service_name)
        systemd_manager.daemon_reload()
    except Exception as e:
        state.logger.error(f"Failed to delete systemd service file: {e}")

    state.current_config.services.remove(svc)
    config.save_config(state.current_config, state.CONFIG_PATH)
    state.logger.info(f"Deleted service: {service_name}")

    return jsonify({"status": "success", "message": f"Service '{service_name}' deleted successfully"})


# ============================================================================
# Service Control
# ============================================================================

@services_bp.route('/api/services/<service_name>/start', methods=['POST'])
def start_service(service_name: str):
    state.find_service(service_name)
    systemd_manager.start_service(service_name)
    state.logger.info(f"Started service: {service_name}")
    return jsonify({
        "status": "success",
        "message": f"Service '{service_name}' started",
        "data": systemd_manager.get_service_status(service_name)
    })


@services_bp.route('/api/services/<service_name>/stop', methods=['POST'])
def stop_service(service_name: str):
    state.find_service(service_name)
    systemd_manager.stop_service(service_name)
    state.logger.info(f"Stopped service: {service_name}")
    return jsonify({
        "status": "success",
        "message": f"Service '{service_name}' stopped",
        "data": systemd_manager.get_service_status(service_name)
    })


@services_bp.route('/api/services/<service_name>/restart', methods=['POST'])
def restart_service(service_name: str):
    state.find_service(service_name)
    systemd_manager.restart_service(service_name)
    state.logger.info(f"Restarted service: {service_name}")
    return jsonify({
        "status": "success",
        "message": f"Service '{service_name}' restarted",
        "data": systemd_manager.get_service_status(service_name)
    })


@services_bp.route('/api/services/<service_name>/pull', methods=['POST'])
def pull_service(service_name: str):
    svc = state.find_service(service_name)
    if not svc.github_url:
        return jsonify({"status": "error", "error": {
            "message": f"Service '{service_name}' has no GitHub URL configured"
        }}), 400
    try:
        output = git_pull_and_restart(svc)
        state.logger.info(f"Manually pulled service: {service_name}")
        return jsonify({
            "status": "success",
            "message": f"Service '{service_name}' pulled and restarted",
            "data": {"commit": svc.last_commit_sha, **output}
        })
    except RuntimeError as e:
        return jsonify({"status": "error", "error": {"message": str(e)}}), 500


@services_bp.route('/api/services/<service_name>/enable', methods=['POST'])
def enable_service(service_name: str):
    svc = state.find_service(service_name)
    systemd_manager.enable_service(service_name, now=False)
    svc.enabled = True
    config.save_config(state.current_config, state.CONFIG_PATH)
    state.logger.info(f"Enabled service: {service_name}")
    return jsonify({"status": "success", "message": f"Service '{service_name}' enabled"})


@services_bp.route('/api/services/<service_name>/disable', methods=['POST'])
def disable_service(service_name: str):
    svc = state.find_service(service_name)
    systemd_manager.disable_service(service_name, now=False)
    svc.enabled = False
    config.save_config(state.current_config, state.CONFIG_PATH)
    state.logger.info(f"Disabled service: {service_name}")
    return jsonify({"status": "success", "message": f"Service '{service_name}' disabled"})
