"""
AutoRun v2 - Git Auto-Update

Background thread that polls GitHub for new commits and updates services,
plus the shared git pull + restart helper used by manual triggers too.
"""

import json
import re
import subprocess
import threading
import time
import urllib.request
from typing import Optional

import config
import state
import systemd_manager


def git_pull_and_restart(svc: config.ServiceConfig, new_sha: Optional[str] = None) -> dict:
    """Stop service, git pull, restart. Returns dict with stdout/stderr."""
    was_running = False
    try:
        was_running = systemd_manager.is_service_active(svc.name)
    except Exception:
        pass

    if was_running:
        try:
            systemd_manager.stop_service(svc.name)
        except Exception as e:
            raise RuntimeError(f"Failed to stop service before pull: {e}")

    result = subprocess.run(
        ['git', '-C', svc.folder, 'pull'],
        capture_output=True, text=True, timeout=120
    )

    if result.returncode != 0:
        if was_running:
            try:
                systemd_manager.start_service(svc.name)
            except Exception:
                pass
        raise RuntimeError(f"git pull failed: {result.stderr.strip()}")

    sha_to_store = new_sha
    if not sha_to_store:
        sha_result = subprocess.run(
            ['git', '-C', svc.folder, 'rev-parse', 'HEAD'],
            capture_output=True, text=True
        )
        if sha_result.returncode == 0:
            sha_to_store = sha_result.stdout.strip()

    if sha_to_store:
        svc.last_commit_sha = sha_to_store
    config.save_config(state.current_config, state.CONFIG_PATH)
    state.logger.info(f"Pulled '{svc.name}' successfully")

    if was_running:
        systemd_manager.start_service(svc.name)

    return {"stdout": result.stdout, "stderr": result.stderr}


class GitUpdateChecker(threading.Thread):
    """Polls GitHub every 5 minutes and auto-updates services that have it enabled."""

    INTERVAL = 300

    def __init__(self):
        super().__init__(daemon=True, name="GitUpdateChecker")

    def run(self):
        while True:
            time.sleep(self.INTERVAL)
            self._check_all()

    def _check_all(self):
        if not state.current_config:
            return
        for svc in list(state.current_config.services):
            if svc.github_url and svc.auto_update:
                try:
                    self._check_and_update(svc)
                except Exception as e:
                    state.logger.error(f"Auto-update error for '{svc.name}': {e}")

    def _remote_sha(self, github_url: str) -> Optional[str]:
        match = re.search(r'github\.com[/:]([^/]+)/([^/\s]+)', github_url)
        if not match:
            return None
        owner, repo = match.group(1), match.group(2).replace('.git', '')
        api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'AutoRun/2.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                return data[0]['sha'] if data else None
        except Exception:
            return None

    def _check_and_update(self, svc: config.ServiceConfig):
        remote_sha = self._remote_sha(svc.github_url)
        if not remote_sha or remote_sha == svc.last_commit_sha:
            return
        state.logger.info(f"New commit for '{svc.name}' ({remote_sha[:7]}), pulling...")
        git_pull_and_restart(svc, remote_sha)
