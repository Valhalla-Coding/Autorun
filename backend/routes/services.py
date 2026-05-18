"""
AutoRun v3 - Services API Routes

CRUD + control for services. All data in SQLite via SQLAlchemy.
"""

import os
import re
import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request, g

import systemd_manager
from database import SessionLocal, Service, next_available_port
from git_updater import git_pull_and_restart
from routes.auth import require_auth

import logging
logger = logging.getLogger("autorun")

services_bp = Blueprint("services", __name__)

VALID_RESTART_POLICIES = {"always", "on-failure", "no"}
SERVICE_NAME_RE = re.compile(r"^[a-z0-9-]+$")


def _get_service_or_404(db, name):
    return db.query(Service).filter_by(name=name).first()


def _service_with_status(svc):
    try:
        status_info = systemd_manager.get_service_status(svc.name)
    except Exception:
        status_info = {"status": "unknown", "active": False, "pid": None, "uptime": "N/A", "memory_mb": 0.0}
    return {"name": svc.name, "config": svc.to_dict(), **status_info}


def _default_user():
    return os.environ.get("AUTORUN_USER", "autorun")


@services_bp.route("/api/services", methods=["GET"])
@require_auth
def list_services():
    db = g.db
    svcs = db.query(Service).order_by(Service.name).all()
    data = [_service_with_status(s) for s in svcs]
    return jsonify({"status": "success", "data": {
        "services": data,
        "total": len(data),
        "running": sum(1 for s in data if s["status"] == "running"),
        "stopped": sum(1 for s in data if s["status"] == "stopped"),
        "failed":  sum(1 for s in data if s["status"] == "failed"),
    }})


@services_bp.route("/api/services/<name>", methods=["GET"])
@require_auth
def get_service(name):
    svc = _get_service_or_404(g.db, name)
    if not svc:
        return jsonify({"status": "error", "error": {"message": f"Service '{name}' not found"}}), 404
    return jsonify({"status": "success", "data": _service_with_status(svc)})


@services_bp.route("/api/services", methods=["POST"])
@require_auth
def create_service():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "error": {"message": "Request body required"}}), 400

    name = data.get("name", "").strip()
    if not name:
        return jsonify({"status": "error", "error": {"message": "'name' is required"}}), 400
    if not SERVICE_NAME_RE.match(name):
        return jsonify({"status": "error", "error": {"message": "Name must be lowercase letters, numbers, hyphens"}}), 400
    if len(name) > 64:
        return jsonify({"status": "error", "error": {"message": "Name too long (max 64)"}}), 400

    folder = data.get("folder", "").strip()
    if not folder:
        return jsonify({"status": "error", "error": {"message": "'folder' is required"}}), 400

    db = g.db
    if db.query(Service).filter_by(name=name).first():
        return jsonify({"status": "error", "error": {"message": f"Service '{name}' already exists"}}), 409

    web_interface = bool(data.get("web_interface", False))
    port = data.get("port")
    if web_interface:
        if port is None:
            port = next_available_port(db)
        else:
            port = int(port)
            if not (5001 <= port <= 5999):
                return jsonify({"status": "error", "error": {"message": "Port must be 5001–5999"}}), 400
            conflict = db.query(Service).filter(Service.port == port).first()
            if conflict:
                return jsonify({"status": "error", "error": {"message": f"Port {port} used by '{conflict.name}'"}}), 409
    else:
        port = None

    url = data.get("url") or (f"/{name}" if web_interface else None)

    auto_restart = data.get("auto_restart", "always")
    if auto_restart not in VALID_RESTART_POLICIES:
        return jsonify({"status": "error", "error": {"message": f"auto_restart must be one of: {', '.join(VALID_RESTART_POLICIES)}"}}), 400

    svc = Service(
        name=name,
        description=data.get("description", ""),
        folder=folder,
        entrypoint=data.get("entrypoint", "run.py"),
        port=port,
        web_interface=web_interface,
        url=url,
        auto_restart=auto_restart,
        enabled=bool(data.get("enabled", True)),
        environment=data.get("environment", {}),
        depends_on=data.get("depends_on", []),
        github_url=data.get("github_url") or None,
        auto_update=bool(data.get("auto_update", False)),
    )

    if svc.github_url and not Path(svc.folder).exists():
        try:
            # Embed token in URL for non-interactive auth (systemd has no terminal)
            from routes.settings import get_setting
            token = get_setting(g.db, "github_token") or os.environ.get("GITHUB_TOKEN", "")
            clone_url = svc.github_url
            if token and clone_url.startswith("https://github.com/"):
                clone_url = clone_url.replace("https://", f"https://{token}@")
            env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
            clone = subprocess.run(["git", "clone", clone_url, svc.folder],
                                   capture_output=True, text=True, timeout=120, env=env)
            if clone.returncode != 0:
                return jsonify({"status": "error", "error": {"message": f"git clone failed: {clone.stderr.strip()}"}}), 500
            sha = subprocess.run(["git", "-C", svc.folder, "rev-parse", "HEAD"],
                                 capture_output=True, text=True)
            if sha.returncode == 0:
                svc.last_commit_sha = sha.stdout.strip()
        except subprocess.TimeoutExpired:
            return jsonify({"status": "error", "error": {"message": "git clone timed out"}}), 500
        except Exception as e:
            return jsonify({"status": "error", "error": {"message": f"Clone error: {e}"}}), 500

    db.add(svc)
    db.commit()
    db.refresh(svc)
    logger.info(f"Created service: {svc.name} (port={svc.port})")

    try:
        systemd_manager.write_service_file(svc, _default_user())
        systemd_manager.daemon_reload()
        if svc.enabled:
            systemd_manager.enable_service(svc.name, now=False)
    except Exception as e:
        logger.error(f"Systemd setup failed for '{svc.name}': {e}")
        return jsonify({"status": "error", "error": {"message": f"Saved but systemd failed: {e}"}}), 500

    return jsonify({"status": "success", "message": f"Service '{svc.name}' created (port {svc.port})", "data": svc.to_dict()}), 201


@services_bp.route("/api/services/<name>", methods=["PUT"])
@require_auth
def update_service(name):
    db = g.db
    svc = _get_service_or_404(db, name)
    if not svc:
        return jsonify({"status": "error", "error": {"message": f"Service '{name}' not found"}}), 404

    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "error": {"message": "Request body required"}}), 400

    if "port" in data:
        new_port = data["port"]
        if new_port is not None:
            new_port = int(new_port)
            conflict = db.query(Service).filter(Service.port == new_port, Service.id != svc.id).first()
            if conflict:
                return jsonify({"status": "error", "error": {"message": f"Port {new_port} used by '{conflict.name}'"}}), 409
        svc.port = new_port

    for key in {"description", "folder", "entrypoint", "web_interface", "url",
                "auto_restart", "enabled", "environment", "depends_on", "github_url", "auto_update"}:
        if key in data:
            setattr(svc, key, data[key])

    if "auto_restart" in data and data["auto_restart"] not in VALID_RESTART_POLICIES:
        return jsonify({"status": "error", "error": {"message": f"auto_restart must be: {', '.join(VALID_RESTART_POLICIES)}"}}), 400

    db.commit()
    db.refresh(svc)

    try:
        systemd_manager.write_service_file(svc, _default_user())
        systemd_manager.daemon_reload()
    except Exception as e:
        return jsonify({"status": "error", "error": {"message": f"Config saved but systemd failed: {e}"}}), 500

    return jsonify({"status": "success", "message": f"Service '{name}' updated", "data": svc.to_dict()})


@services_bp.route("/api/services/<name>", methods=["DELETE"])
@require_auth
def delete_service(name):
    db = g.db
    svc = _get_service_or_404(db, name)
    if not svc:
        return jsonify({"status": "error", "error": {"message": f"Service '{name}' not found"}}), 404

    for fn in [systemd_manager.stop_service, lambda n: systemd_manager.disable_service(n, now=False)]:
        try: fn(name)
        except Exception: pass

    try:
        systemd_manager.delete_service_file(name)
        systemd_manager.daemon_reload()
    except Exception as e:
        logger.error(f"Failed to delete systemd file: {e}")

    db.delete(svc)
    db.commit()
    return jsonify({"status": "success", "message": f"Service '{name}' deleted"})


@services_bp.route("/api/services/<name>/start", methods=["POST"])
@require_auth
def start_service(name):
    if not _get_service_or_404(g.db, name):
        return jsonify({"status": "error", "error": {"message": f"Service '{name}' not found"}}), 404
    systemd_manager.start_service(name)
    return jsonify({"status": "success", "message": f"'{name}' started", "data": systemd_manager.get_service_status(name)})


@services_bp.route("/api/services/<name>/stop", methods=["POST"])
@require_auth
def stop_service(name):
    if not _get_service_or_404(g.db, name):
        return jsonify({"status": "error", "error": {"message": f"Service '{name}' not found"}}), 404
    systemd_manager.stop_service(name)
    return jsonify({"status": "success", "message": f"'{name}' stopped", "data": systemd_manager.get_service_status(name)})


@services_bp.route("/api/services/<name>/restart", methods=["POST"])
@require_auth
def restart_service(name):
    if not _get_service_or_404(g.db, name):
        return jsonify({"status": "error", "error": {"message": f"Service '{name}' not found"}}), 404
    systemd_manager.restart_service(name)
    return jsonify({"status": "success", "message": f"'{name}' restarted", "data": systemd_manager.get_service_status(name)})


@services_bp.route("/api/services/<name>/pull", methods=["POST"])
@require_auth
def pull_service(name):
    svc = _get_service_or_404(g.db, name)
    if not svc:
        return jsonify({"status": "error", "error": {"message": f"Service '{name}' not found"}}), 404
    if not svc.github_url:
        return jsonify({"status": "error", "error": {"message": "No GitHub URL configured"}}), 400
    try:
        output = git_pull_and_restart(name)
        g.db.refresh(svc)
        return jsonify({"status": "success", "message": f"'{name}' pulled and restarted", "data": {"commit": svc.last_commit_sha, **output}})
    except RuntimeError as e:
        return jsonify({"status": "error", "error": {"message": str(e)}}), 500


@services_bp.route("/api/services/<name>/enable", methods=["POST"])
@require_auth
def enable_service(name):
    svc = _get_service_or_404(g.db, name)
    if not svc:
        return jsonify({"status": "error", "error": {"message": f"Service '{name}' not found"}}), 404
    systemd_manager.enable_service(name, now=False)
    svc.enabled = True
    g.db.commit()
    return jsonify({"status": "success", "message": f"'{name}' enabled"})


@services_bp.route("/api/services/<name>/disable", methods=["POST"])
@require_auth
def disable_service(name):
    svc = _get_service_or_404(g.db, name)
    if not svc:
        return jsonify({"status": "error", "error": {"message": f"Service '{name}' not found"}}), 404
    systemd_manager.disable_service(name, now=False)
    svc.enabled = False
    g.db.commit()
    return jsonify({"status": "success", "message": f"'{name}' disabled"})
