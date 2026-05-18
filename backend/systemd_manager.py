"""
AutoRun v3 - Systemd Integration Module

Handles systemd service file generation, systemctl command execution,
and service status management.
"""

import subprocess
from pathlib import Path
from typing import Optional, Dict
from dateutil.parser import parse as parse_datetime
from datetime import datetime


# Custom exceptions
class SystemdOperationError(Exception):
    """Raised when a systemd operation fails"""
    pass


def generate_service_file(service, user: str) -> str:
    """
    Generate systemd service file content from a Service model instance.

    Args:
        service: Service SQLAlchemy model (has name, description, folder,
                 entrypoint, port, environment, depends_on, auto_restart)
        user: System user to run the service as

    Returns:
        String content of systemd service file
    """
    # Build dependencies
    dependencies = []
    requires = []

    depends_on = getattr(service, 'depends_on', None) or []
    if depends_on:
        dependencies.extend([f"autorun-{dep}.service" for dep in depends_on])
        requires = dependencies.copy()

    after_line = "After=network.target" + (f" {' '.join(dependencies)}" if dependencies else "")
    requires_line = f"Requires={' '.join(requires)}" if requires else ""

    # Build environment variables
    env_lines = []
    port = getattr(service, 'port', None)
    if port is not None:
        env_lines.append(f'Environment="PORT={port}"')

    environment = getattr(service, 'environment', None) or {}
    for key, value in environment.items():
        env_lines.append(f'Environment="{key}={value}"')

    env_section = "\n".join(env_lines) if env_lines else ""

    entrypoint = getattr(service, 'entrypoint', 'run.py') or 'run.py'
    auto_restart = getattr(service, 'auto_restart', 'always') or 'always'
    description = getattr(service, 'description', None) or service.name

    content = f"""[Unit]
Description={description}
{after_line}
{requires_line if requires_line else ''}

[Service]
Type=simple
User={user}
WorkingDirectory={service.folder}
ExecStart=/usr/bin/python3 {entrypoint}
{env_section}
Restart={auto_restart}
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    return content


def _check_sudo_access() -> bool:
    """Check if we can write to /etc/systemd/system/ directly."""
    test_path = Path("/etc/systemd/system/.autorun_test")
    try:
        test_path.touch()
        test_path.unlink()
        return True
    except (PermissionError, OSError):
        return False


def execute_with_sudo(command: list) -> subprocess.CompletedProcess:
    """Execute command, prepending sudo if needed."""
    if not _check_sudo_access():
        command = ["sudo"] + command
    return subprocess.run(command, capture_output=True, text=True, check=False)


def write_service_file(service, user: str, dry_run: bool = False) -> Path:
    """
    Write systemd service file to /etc/systemd/system/

    Args:
        service: Service SQLAlchemy model
        user: System user to run service as
        dry_run: If True, only generate content without writing

    Returns:
        Path to the service file
    """
    content = generate_service_file(service, user)
    service_path = Path(f"/etc/systemd/system/autorun-{service.name}.service")

    if dry_run:
        print(f"[DRY RUN] Would write to {service_path}:")
        print(content)
        return service_path

    try:
        process = subprocess.run(
            ["sudo", "/bin/tee", str(service_path)],
            input=content,
            capture_output=True,
            text=True,
            check=False
        )

        if process.returncode != 0:
            raise SystemdOperationError(f"Failed to write service file: {process.stderr}")

        return service_path

    except SystemdOperationError:
        raise
    except Exception as e:
        raise SystemdOperationError(f"Failed to write service file {service_path}: {e}")


def delete_service_file(service_name: str) -> None:
    """Delete systemd service file from /etc/systemd/system/"""
    service_path = Path(f"/etc/systemd/system/autorun-{service_name}.service")

    if not service_path.exists():
        return

    result = execute_with_sudo(["/bin/rm", "-f", str(service_path)])

    if result.returncode != 0:
        raise SystemdOperationError(f"Failed to delete service file: {result.stderr}")


def daemon_reload() -> subprocess.CompletedProcess:
    """Run systemctl daemon-reload."""
    result = execute_with_sudo(["/bin/systemctl", "daemon-reload"])

    if result.returncode != 0:
        raise SystemdOperationError(f"daemon-reload failed: {result.stderr}")

    return result


def enable_service(service_name: str, now: bool = True) -> subprocess.CompletedProcess:
    """Enable (and optionally start) a service."""
    cmd = ["/bin/systemctl", "enable"]
    if now:
        cmd.append("--now")
    cmd.append(f"autorun-{service_name}.service")

    result = execute_with_sudo(cmd)

    if result.returncode != 0:
        raise SystemdOperationError(f"Failed to enable service: {result.stderr}")

    return result


def disable_service(service_name: str, now: bool = True) -> subprocess.CompletedProcess:
    """Disable (and optionally stop) a service."""
    cmd = ["/bin/systemctl", "disable"]
    if now:
        cmd.append("--now")
    cmd.append(f"autorun-{service_name}.service")

    result = execute_with_sudo(cmd)

    if result.returncode != 0:
        raise SystemdOperationError(f"Failed to disable service: {result.stderr}")

    return result


def start_service(service_name: str) -> subprocess.CompletedProcess:
    """Start a service."""
    result = execute_with_sudo(["/bin/systemctl", "start", f"autorun-{service_name}.service"])

    if result.returncode != 0:
        raise SystemdOperationError(f"Failed to start service: {result.stderr}")

    return result


def stop_service(service_name: str) -> subprocess.CompletedProcess:
    """Stop a service."""
    result = execute_with_sudo(["/bin/systemctl", "stop", f"autorun-{service_name}.service"])

    if result.returncode != 0:
        raise SystemdOperationError(f"Failed to stop service: {result.stderr}")

    return result


def restart_service(service_name: str) -> subprocess.CompletedProcess:
    """Restart a service."""
    result = execute_with_sudo(["/bin/systemctl", "restart", f"autorun-{service_name}.service"])

    if result.returncode != 0:
        raise SystemdOperationError(f"Failed to restart service: {result.stderr}")

    return result


def is_service_active(service_name: str) -> bool:
    """Check if a service is active (running)."""
    result = subprocess.run(
        ["/bin/systemctl", "is-active", f"autorun-{service_name}.service"],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def is_service_enabled(service_name: str) -> bool:
    """Check if a service is enabled to start on boot."""
    result = subprocess.run(
        ["/bin/systemctl", "is-enabled", f"autorun-{service_name}.service"],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def get_service_status(service_name: str) -> Dict[str, any]:
    """
    Get comprehensive service status from systemctl.

    Returns dict with: status, active, enabled, pid, uptime, memory_mb,
    exit_code, error_message.
    """
    result = subprocess.run(
        ["/bin/systemctl", "show", f"autorun-{service_name}.service", "--no-pager"],
        capture_output=True,
        text=True
    )

    props = {}
    for line in result.stdout.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            props[key] = value

    active_state = props.get("ActiveState", "unknown")
    sub_state = props.get("SubState", "unknown")
    unit_file_state = props.get("UnitFileState", "unknown")

    if active_state == "active" and sub_state == "running":
        status = "running"
    elif active_state == "failed":
        status = "failed"
    elif unit_file_state in ["disabled", "masked"]:
        status = "disabled"
    else:
        status = "stopped"

    main_pid = props.get("MainPID", "0")
    try:
        pid = int(main_pid) if main_pid != "0" else None
    except ValueError:
        pid = None

    uptime = "N/A"
    active_enter_timestamp = props.get("ActiveEnterTimestamp", "")
    if active_enter_timestamp:
        try:
            start_time = parse_datetime(active_enter_timestamp)
            delta = datetime.now(start_time.tzinfo) - start_time
            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if days > 0:
                uptime = f"{days}d {hours}h"
            elif hours > 0:
                uptime = f"{hours}h {minutes}m"
            elif minutes > 0:
                uptime = f"{minutes}m {seconds}s"
            else:
                uptime = f"{seconds}s"
        except Exception:
            uptime = "N/A"

    memory_current = props.get("MemoryCurrent", "[not set]")
    memory_mb = 0.0
    if memory_current not in ("[not set]", ""):
        try:
            memory_mb = int(memory_current) / (1024 * 1024)
        except ValueError:
            memory_mb = 0.0

    exit_code = None
    error_message = None

    if status == "failed":
        exec_main_status = props.get("ExecMainStatus", "0")
        try:
            exit_code = int(exec_main_status) if exec_main_status else None
        except ValueError:
            exit_code = None

        try:
            log_result = subprocess.run(
                ["/usr/bin/journalctl", "-u", f"autorun-{service_name}.service",
                 "-n", "20", "--no-pager", "-o", "short-precise"],
                capture_output=True,
                text=True,
                check=False
            )

            if log_result.returncode == 0 and log_result.stdout.strip():
                error_keywords = ['error', 'exception', 'failed', 'errno', 'traceback',
                                  'no such file', 'cannot', 'chdir', 'exit', 'status=']
                lines = log_result.stdout.splitlines()

                for line in reversed(lines):
                    if not line.strip():
                        continue
                    if any(kw in line.lower() for kw in error_keywords):
                        if ']:' in line:
                            idx = line.rfind(']:')
                            error_message = line[idx + 2:].strip()
                            break
                        elif ': ' in line:
                            parts = line.split(': ', 2)
                            error_message = parts[-1].strip()
                            break

                if not error_message and lines:
                    for line in reversed(lines):
                        if line.strip():
                            if ']:' in line:
                                idx = line.rfind(']:')
                                error_message = line[idx + 2:].strip()
                            elif ': ' in line:
                                parts = line.split(': ', 2)
                                error_message = parts[-1].strip()
                            break
        except Exception:
            pass

    return {
        "status": status,
        "active": active_state == "active",
        "enabled": unit_file_state == "enabled",
        "pid": pid,
        "uptime": uptime,
        "memory_mb": round(memory_mb, 2),
        "exit_code": exit_code,
        "error_message": error_message
    }


def service_exists(service_name: str) -> bool:
    """Check if a systemd service file exists."""
    return Path(f"/etc/systemd/system/autorun-{service_name}.service").exists()
