"""
AutoRun v3 - GitHub API Routes

Proxies GitHub repo lookups server-side (so the PAT never reaches the browser).
Token stored in a settings table (future) or env var for now.
"""

import json
import os
import re
import urllib.error
import urllib.request

from flask import Blueprint, jsonify, request
from routes.auth import require_auth

import logging
logger = logging.getLogger("autorun")

github_bp = Blueprint("github", __name__)


def fetch_repo_info(github_url: str, token: str = None) -> dict:
    match = re.search(r"github\.com[/:]([^/]+)/([^/\s]+)", github_url)
    if not match:
        raise ValueError("Not a valid GitHub URL")
    owner, repo = match.group(1), match.group(2).replace(".git", "")
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"User-Agent": "AutoRun/3.0"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(api_url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


@github_bp.route("/api/github/repo-info", methods=["GET"])
@require_auth
def repo_info():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"status": "error", "error": {"message": "url parameter required"}}), 400
    token = os.environ.get("GITHUB_TOKEN")
    try:
        data = fetch_repo_info(url, token)
        return jsonify({"status": "success", "data": {
            "name": data["name"],
            "full_name": data["full_name"],
            "description": data.get("description") or "",
            "private": data.get("private", False),
        }})
    except ValueError as e:
        return jsonify({"status": "error", "error": {"message": str(e)}}), 400
    except urllib.error.HTTPError as e:
        msgs = {401: "Auth failed — token invalid or expired", 404: "Repo not found — private? Add GITHUB_TOKEN env var"}
        return jsonify({"status": "error", "error": {"message": msgs.get(e.code, f"GitHub API {e.code}")}}), e.code
    except Exception as e:
        logger.error(f"GitHub repo-info error: {e}")
        return jsonify({"status": "error", "error": {"message": "Could not reach GitHub API"}}), 502
