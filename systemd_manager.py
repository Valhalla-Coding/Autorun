"""
AutoRun v2 - Systemd Integration Module

Handles systemd service file generation, systemctl command execution,
and service status management.
"""

import subprocess
from pathlib import Path
from typing import Optional, Dict
from dateutil.parser import parse as parse_datetime
from datetime import datetime
from config import ServiceConfig


# Custom exceptions
class SystemdOperationError(Exception):
    """Raised when a systemd operation fails"""
    pass


class PermissionError(Exception):
    """Raised when insufficient permissions to perform operation"""
    pass


def generate_service_file(service: ServiceConfig, user: str) -> str:
    """
    Generate systemd service file content from service configuration

    Args:
        service: ServiceConfig object
        user: System user to run the service as

    Returns:
        String content of systemd service file
    """
    # Build dependencies
    dependencies = []
    requires = []

    if service.depends_on:
        dependencies.extend([f"autorun-{dep}.service" for dep in service.depends_on])
        requires = dependencies.copy()

    after_line = "After=network.target" + (f" {' '.join(dependencies)}" if dependencies else "")
    requires_line = f"Requires={' '.join(requires)}" if requires else ""

    # Build environment variables
    env_lines = []
    if service.port is not None:
        env_lines.append(f'Environment="PORT={service.port}"')

    for key, value in service.environment.items():
        env_lines.append(f'Environment="{key}={value}"')

    env_section = "\n".join(env_lines) if env_lines else ""

    # Generate service file content
    content = f"""[Unit]
Description={service.description or service.name}
{after_line}
{requires_line if requires_line else ''}

[Service]
Type=simple
User={user}
WorkingDirectory={service.folder}
ExecStart=/usr/bin/python3 {service.folder}/{service.entrypoint}
{env_section}
Restart={service.auto_restart}
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    return content


def check_sudo_access() -> bool:
    """
    Check if we can write to /etc/systemd/system/

    Returns:
        True if we have access, False otherwise
    """
    test_path = Path("/etc/systemd/system/.autorun_test")
    try:
        test_path.touch()
        test_path.unlink()
        return True
    except (PermissionError, OSError):
        return False


def execute_with_sudo(command: list) -> subprocess.CompletedProcess:
    """
    Execute command with sudo if needed

    Args:
        command: List of command arguments

    Returns:
        CompletedProcess object
    """
    if not check_sudo_access():
        command = ["sudo"] + command

    return subprocess.run(command, capture_output=True, text=True, check=False)


def write_service_file(service: ServiceConfig, user: str, dry_run: bool = False) -> Path:
    """
    Write systemd service file to /etc/systemd/system/

    Args:
        service: ServiceConfig object
        user: System user to run service as
        dry_run: If True, only generate content without writing

    Returns:
        Path to the service file

    Raises:
        SystemdOperationError: If write fails
    """
    content = generate_service_file(service, user)
    service_path = service.service_path

    if dry_run:
        print(f"[DRY RUN] Would write to {service_path}:")
        print(content)
        return service_path

    try:
        # Write using sudo tee
        process = subprocess.run(
            ["sudo", "tee", str(service_path)],
            input=content,
            capture_output=True,
            text=True,
            check=False
        )

        if process.returncode != 0:
            raise SystemdOperationError(f"Failed to write service file: {process.stderr}")

        return service_path

    except Exception as e:
        raise SystemdOperationError(f"Failed to write service file {service_path}: {e}")


def delete_service_file(service_name: str) -> None:
    """
    Delete systemd service file from /etc/systemd/system/

    Args:
        service_name: Name of the service (without autorun- prefix)

    Raises:
        SystemdOperationError: If deletion fails
    """
    service_path = Path(f"/etc/systemd/system/autorun-{service_name}.service")

    if not service_path.exists():
        return  # Already deleted

    try:
        result = execute_with_sudo(["rm", "-f", str(service_path)])

        if result.returncode != 0:
            raise SystemdOperationError(f"Failed to delete service file: {result.stderr}")

    except Exception as e:
        raise SystemdOperationError(f"Failed to delete service file {service_path}: {e}")


def daemon_reload() -> subprocess.CompletedProcess:
    """
    Run systemctl daemon-reload to reload systemd configuration

    Returns:
        CompletedProcess object

    Raises:
        SystemdOperationError: If daemon-reload fails
    """
    result = execute_with_sudo(["systemctl", "daemon-reload"])

    if result.returncode != 0:
        raise SystemdOperationError(f"daemon-reload failed: {result.stderr}")

    return result


def enable_service(service_name: str, now: bool = True) -> subprocess.CompletedProcess:
    """
    Enable (and optionally start) a service

    Args:
        service_name: Name of the service (without autorun- prefix)
        now: If True, also start the service immediately

    Returns:
        CompletedProcess object
    """
    cmd = ["systemctl", "enable"]
    if now:
        cmd.append("--now")
    cmd.append(f"autorun-{service_name}.service")

    result = execute_with_sudo(cmd)

    if result.returncode != 0:
        raise SystemdOperationError(f"Failed to enable service: {result.stderr}")

    return result


def disable_service(service_name: str, now: bool = True) -> subprocess.CompletedProcess:
    """
    Disable (and optionally stop) a service

    Args:
        service_name: Name of the service (without autorun- prefix)
        now: If True, also stop the service immediately

    Returns:
        CompletedProcess object
    """
    cmd = ["systemctl", "disable"]
    if now:
        cmd.append("--now")
    cmd.append(f"autorun-{service_name}.service")

    result = execute_with_sudo(cmd)

    if result.returncode != 0:
        raise SystemdOperationError(f"Failed to disable service: {result.stderr}")

    return result


def start_service(service_name: str) -> subprocess.CompletedProcess:
    """
    Start a service

    Args:
        service_name: Name of the service (without autorun- prefix)

    Returns:
        CompletedProcess object
    """
    result = execute_with_sudo(["systemctl", "start", f"autorun-{service_name}.service"])

    if result.returncode != 0:
        raise SystemdOperationError(f"Failed to start service: {result.stderr}")

    return result


def stop_service(service_name: str) -> subprocess.CompletedProcess:
    """
    Stop a service

    Args:
        service_name: Name of the service (without autorun- prefix)

    Returns:
        CompletedProcess object
    """
    result = execute_with_sudo(["systemctl", "stop", f"autorun-{service_name}.service"])

    if result.returncode != 0:
        raise SystemdOperationError(f"Failed to stop service: {result.stderr}")

    return result


def restart_service(service_name: str) -> subprocess.CompletedProcess:
    """
    Restart a service

    Args:
        service_name: Name of the service (without autorun- prefix)

    Returns:
        CompletedProcess object
    """
    result = execute_with_sudo(["systemctl", "restart", f"autorun-{service_name}.service"])

    if result.returncode != 0:
        raise SystemdOperationError(f"Failed to restart service: {result.stderr}")

    return result


def is_service_active(service_name: str) -> bool:
    """
    Check if a service is active (running)

    Args:
        service_name: Name of the service (without autorun- prefix)

    Returns:
        True if active, False otherwise
    """
    result = subprocess.run(
        ["systemctl", "is-active", f"autorun-{service_name}.service"],
        capture_output=True,
        text=True
    )

    return result.returncode == 0


def is_service_enabled(service_name: str) -> bool:
    """
    Check if a service is enabled to start on boot

    Args:
        service_name: Name of the service (without autorun- prefix)

    Returns:
        True if enabled, False otherwise
    """
    result = subprocess.run(
        ["systemctl", "is-enabled", f"autorun-{service_name}.service"],
        capture_output=True,
        text=True
    )

    return result.returncode == 0


def get_service_status(service_name: str) -> Dict[str, any]:
    """
    Get comprehensive service status from systemctl

    Args:
        service_name: Name of the service (without autorun- prefix)

    Returns:
        Dictionary with status information:
        - status: str ('running', 'stopped', 'failed', 'disabled')
        - active: bool (is currently active)
        - enabled: bool (is enabled to start on boot)
        - pid: Optional[int] (main process ID)
        - uptime: str (human-readable uptime)
        - memory_mb: float (memory usage in MB)
    """
    # Get detailed status
    result = subprocess.run(
        ["systemctl", "show", f"autorun-{service_name}.service", "--no-pager"],
        capture_output=True,
        text=True
    )

    # Parse output into dictionary
    props = {}
    for line in result.stdout.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            props[key] = value

    # Determine status
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

    # Parse PID
    main_pid = props.get("MainPID", "0")
    try:
        pid = int(main_pid) if main_pid != "0" else None
    except ValueError:
        pid = None

    # Parse uptime
    uptime = "N/A"
    active_enter_timestamp = props.get("ActiveEnterTimestamp", "")
    if active_enter_timestamp and active_enter_timestamp != "":
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

    # Parse memory usage
    memory_current = props.get("MemoryCurrent", "[not set]")
    memory_mb = 0.0
    if memory_current != "[not set]" and memory_current != "":
        try:
            memory_bytes = int(memory_current)
            memory_mb = memory_bytes / (1024 * 1024)
        except ValueError:
            memory_mb = 0.0

    return {
        "status": status,
        "active": active_state == "active",
        "enabled": unit_file_state == "enabled",
        "pid": pid,
        "uptime": uptime,
        "memory_mb": round(memory_mb, 2)
    }


def service_exists(service_name: str) -> bool:
    """
    Check if a systemd service file exists

    Args:
        service_name: Name of the service (without autorun- prefix)

    Returns:
        True if service file exists, False otherwise
    """
    service_path = Path(f"/etc/systemd/system/autorun-{service_name}.service")
    return service_path.exists()
