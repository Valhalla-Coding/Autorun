"""
AutoRun v3 - System API Routes
"""

import subprocess
import time
from pathlib import Path

from flask import Blueprint, jsonify, request, g, Response, stream_with_context

import systemd_manager
from database import Service, SessionLocal
from routes.auth import require_auth, get_user_from_token

import logging
logger = logging.getLogger("autorun")

system_bp = Blueprint("system", __name__)
ALLOWED_BROWSE_PATHS = ("/home", "/opt", "/srv", "/var/www", "/mnt")


def _allowed(path_str):
    return any(path_str == a or path_str.startswith(a + "/") for a in ALLOWED_BROWSE_PATHS)


@system_bp.route("/api/system/daemon-reload", methods=["POST"])
@require_auth
def daemon_reload():
    systemd_manager.daemon_reload()
    return jsonify({"status": "success", "message": "systemctl daemon-reload executed"})


@system_bp.route("/api/system/status", methods=["GET"])
@require_auth
def system_status():
    db = g.db
    svcs = db.query(Service).order_by(Service.name).all()
    data = []
    for svc in svcs:
        try:
            info = systemd_manager.get_service_status(svc.name)
            data.append({"name": svc.name, "status": info["status"]})
        except Exception:
            data.append({"name": svc.name, "status": "unknown"})
    return jsonify({"status": "success", "data": {
        "total_services": len(data),
        "running": sum(1 for s in data if s["status"] == "running"),
        "stopped": sum(1 for s in data if s["status"] == "stopped"),
        "failed":  sum(1 for s in data if s["status"] == "failed"),
        "services": data,
    }})


@system_bp.route("/api/health", methods=["GET"])
def health_check():
    import os, pwd
    try:
        system_user = os.environ.get("AUTORUN_USER") or pwd.getpwuid(os.getuid()).pw_name
    except Exception:
        system_user = "user"
    return jsonify({"status": "success", "message": "AutoRun v3 is running", "data": {"system_user": system_user}})


@system_bp.route("/api/browse/folders", methods=["GET"])
@require_auth
def browse_folders():
    start_path = request.args.get("path", str(Path.home()))
    try:
        path = Path(start_path).resolve()
        path_str = str(path)
        if not _allowed(path_str):
            return jsonify({"status": "error", "error": {"message": f"Access denied: {path_str}"}}), 403
        if not path.exists() or not path.is_dir():
            return jsonify({"status": "error", "error": {"message": "Path does not exist"}}), 400
        folders = []
        try:
            for i in sorted(path.iterdir()):
                if i.is_dir() and not i.name.startswith("."):
                    try:
                        has_children = any(c.is_dir() and not c.name.startswith(".") for c in i.iterdir())
                    except PermissionError:
                        has_children = False
                    folders.append({"name": i.name, "path": str(i), "has_children": has_children})
        except PermissionError:
            pass
        parent = str(path.parent) if path != path.parent else None
        return jsonify({"status": "success", "data": {"current_path": path_str, "parent": parent, "folders": folders}})
    except Exception as e:
        return jsonify({"status": "error", "error": {"message": str(e)}}), 500


@system_bp.route("/api/logs/stream", methods=["GET"])
def stream_logs():
    """
    SSE endpoint streaming journalctl output.
    Auth via ?token=<token> query param (EventSource can't set headers).
    Optional ?service=<name> to filter to a single service.
    """
    import json as _json

    token = request.args.get("token", "")
    user = get_user_from_token(token)
    if not user:
        return Response("Unauthorized", status=401)

    service_name = request.args.get("service", "").strip()

    def generate():
        cmd = ["/usr/bin/journalctl", "-f", "-n", "100", "--no-pager",
               "-o", "json", "--output-fields=MESSAGE,PRIORITY,_SYSTEMD_UNIT"]
        if service_name:
            cmd += ["-u", f"autorun-{service_name}.service"]
        else:
            cmd += ["-u", "autorun-*.service"]

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True)
            for raw_line in proc.stdout:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry = _json.loads(raw_line)
                    text = entry.get("MESSAGE", "")
                    priority = int(entry.get("PRIORITY", 6))
                    unit = entry.get("_SYSTEMD_UNIT", "")
                    svc = unit.replace("autorun-", "").replace(".service", "") if unit else ""
                    if priority <= 3:
                        level = "ERROR"
                    elif priority == 4:
                        level = "WARNING"
                    elif priority == 7:
                        level = "DEBUG"
                    else:
                        level = "INFO"
                    out = _json.dumps({
                        "text": text,
                        "level": level,
                        "service": svc,
                        "ts": entry.get("__REALTIME_TIMESTAMP", ""),
                    })
                except Exception:
                    out = _json.dumps({"text": raw_line, "level": "INFO", "ts": ""})
                yield f"data: {out}\n\n"
        except GeneratorExit:
            proc.terminate()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@system_bp.route("/api/browse/files", methods=["GET"])
@require_auth
def browse_files():
    folder_path = request.args.get("path")
    if not folder_path:
        return jsonify({"status": "error", "error": {"message": "path required"}}), 400
    try:
        path = Path(folder_path).resolve()
        if not path.exists() or not path.is_dir():
            return jsonify({"status": "error", "error": {"message": "Path does not exist"}}), 400
        files = []
        try:
            files = [{"name": i.name, "path": str(i)} for i in sorted(path.iterdir()) if i.is_file() and i.suffix == ".py"]
        except PermissionError:
            pass
        return jsonify({"status": "success", "data": {"folder": str(path), "files": files}})
    except Exception as e:
        return jsonify({"status": "error", "error": {"message": str(e)}}), 500
