"""
AutoRun v3 - Git Auto-Update

Background thread that polls GitHub for new commits and auto-updates
services that have auto_update=True. Also provides git_pull_and_restart()
used by manual pull triggers in the services route.
"""

import json
import logging
import os
import re
import subprocess
import threading
import time
import urllib.request
from typing import Optional

import systemd_manager
from database import SessionLocal, Service

logger = logging.getLogger("autorun.git_updater")

def _get_github_token() -> str:
    try:
        from database import SessionLocal, Setting
        db = SessionLocal()
        row = db.query(Setting).filter_by(key="github_token").first()
        db.close()
        if row and row.value:
            return row.value
    except Exception:
        pass
    return os.environ.get("GITHUB_TOKEN", "")


def git_pull_and_restart(service_name: str, new_sha: Optional[str] = None) -> dict:
    """
    Stop the named service, run git pull in its folder, then restart.

    Args:
        service_name: The service's name (from DB)
        new_sha: If already known, the new commit SHA (skips extra git call)

    Returns:
        dict with 'stdout' and 'stderr' from the git pull

    Raises:
        RuntimeError on failure
    """
    db = SessionLocal()
    try:
        svc = db.query(Service).filter_by(name=service_name).first()
        if not svc:
            raise RuntimeError(f"Service '{service_name}' not found in database")

        folder = svc.folder

        was_running = False
        try:
            was_running = systemd_manager.is_service_active(service_name)
        except Exception:
            pass

        if was_running:
            try:
                systemd_manager.stop_service(service_name)
            except Exception as e:
                raise RuntimeError(f"Failed to stop service before pull: {e}")

        token = _get_github_token()
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        # Set token via credential helper env so pull works without a terminal
        if token:
            env["GIT_ASKPASS"] = "echo"
            env["GIT_USERNAME"] = token
            env["GIT_PASSWORD"] = token

        result = subprocess.run(
            ['git', '-C', folder, 'pull'],
            capture_output=True, text=True, timeout=120, env=env
        )

        if result.returncode != 0:
            # Try to restart even if pull failed
            if was_running:
                try:
                    systemd_manager.start_service(service_name)
                except Exception:
                    pass
            raise RuntimeError(f"git pull failed: {result.stderr.strip()}")

        sha_to_store = new_sha
        if not sha_to_store:
            sha_result = subprocess.run(
                ['git', '-C', folder, 'rev-parse', 'HEAD'],
                capture_output=True, text=True
            )
            if sha_result.returncode == 0:
                sha_to_store = sha_result.stdout.strip()

        if sha_to_store:
            svc.last_commit_sha = sha_to_store
            db.commit()

        logger.info(f"Pulled '{service_name}' successfully")

        if was_running:
            systemd_manager.start_service(service_name)

        return {"stdout": result.stdout, "stderr": result.stderr}
    finally:
        db.close()


def _remote_sha(github_url: str) -> Optional[str]:
    """Fetch the latest commit SHA from GitHub API."""
    match = re.search(r'github\.com[/:]([^/]+)/([^/\s]+)', github_url)
    if not match:
        return None
    owner, repo = match.group(1), match.group(2).replace('.git', '')
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
    headers = {'User-Agent': 'AutoRun/3.0'}
    token = _get_github_token()
    if token:
        headers['Authorization'] = f'token {token}'
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data[0]['sha'] if data else None
    except Exception:
        return None


class GitUpdateChecker(threading.Thread):
    """Polls GitHub every 5 minutes and auto-updates services with auto_update=True."""

    INTERVAL = 300

    def __init__(self):
        super().__init__(daemon=True, name="GitUpdateChecker")

    def run(self):
        while True:
            time.sleep(self.INTERVAL)
            self._check_all()

    def _check_all(self):
        db = SessionLocal()
        try:
            services = db.query(Service).filter_by(auto_update=True).all()
            names_urls_shas = [
                (svc.name, svc.github_url, svc.last_commit_sha)
                for svc in services
                if svc.github_url
            ]
        finally:
            db.close()

        for name, github_url, last_sha in names_urls_shas:
            try:
                self._check_and_update(name, github_url, last_sha)
            except Exception as e:
                logger.error(f"Auto-update error for '{name}': {e}")

    def _check_and_update(self, service_name: str, github_url: str, last_sha: Optional[str]):
        remote_sha = _remote_sha(github_url)
        if not remote_sha or remote_sha == last_sha:
            return
        logger.info(f"New commit for '{service_name}' ({remote_sha[:7]}), pulling...")
        git_pull_and_restart(service_name, remote_sha)
