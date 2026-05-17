"""
AutoRun v2 - GitHub API Routes

Proxies GitHub repo lookups server-side (so the PAT never reaches the browser)
and provides a settings endpoint to store/clear the token.
"""

import json
import re
import urllib.error
import urllib.request
from typing import Optional

from flask import Blueprint, jsonify, request

import config
import state

github_bp = Blueprint('github', __name__)


def fetch_repo_info(github_url: str, token: Optional[str] = None) -> dict:
    """Fetch repo metadata from the GitHub API. Raises urllib.error.HTTPError on failure."""
    match = re.search(r'github\.com[/:]([^/]+)/([^/\s]+)', github_url)
    if not match:
        raise ValueError("Not a valid GitHub URL")

    owner, repo = match.group(1), match.group(2).replace('.git', '')
    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    headers = {'User-Agent': 'AutoRun/2.0'}
    if token:
        headers['Authorization'] = f'token {token}'

    req = urllib.request.Request(api_url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


# ============================================================================
# Repo Info Proxy
# ============================================================================

@github_bp.route('/api/github/repo-info', methods=['GET'])
def repo_info():
    """Return name + description for a GitHub repo URL, using the stored PAT if set."""
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({"status": "error", "error": {"message": "url parameter is required"}}), 400

    token = state.current_config.metadata.github_token if state.current_config else None

    try:
        data = fetch_repo_info(url, token)
        return jsonify({
            "status": "success",
            "data": {
                "name":        data["name"],
                "full_name":   data["full_name"],
                "description": data.get("description") or "",
                "private":     data.get("private", False),
            }
        })
    except ValueError as e:
        return jsonify({"status": "error", "error": {"message": str(e)}}), 400
    except urllib.error.HTTPError as e:
        if e.code == 401:
            msg = "Authentication failed — your GitHub token may be invalid or expired"
        elif e.code == 404:
            msg = "Repository not found — is it private? Add a GitHub token below"
        else:
            msg = f"GitHub API returned {e.code}"
        return jsonify({"status": "error", "error": {"message": msg}}), e.code
    except Exception as e:
        state.logger.error(f"GitHub repo-info error: {e}")
        return jsonify({"status": "error", "error": {"message": "Could not reach GitHub API"}}), 502


# ============================================================================
# Token Settings
# ============================================================================

@github_bp.route('/api/settings/github-token', methods=['GET'])
def get_github_token():
    """Return whether a token is currently configured (never returns the value)."""
    token = state.current_config.metadata.github_token if state.current_config else None
    return jsonify({"status": "success", "data": {"configured": bool(token)}})


@github_bp.route('/api/settings/github-token', methods=['PUT'])
def set_github_token():
    """Save or clear the GitHub PAT."""
    data = request.get_json()
    token = (data.get('token') or '').strip() if data else ''

    state.current_config.metadata.github_token = token or None
    config.save_config(state.current_config, state.CONFIG_PATH)

    action = "saved" if token else "cleared"
    state.logger.info(f"GitHub token {action}")
    return jsonify({"status": "success", "message": f"GitHub token {action}"})
