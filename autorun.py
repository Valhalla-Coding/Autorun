"""
AutoRun v2 - Main Flask Application

Web dashboard and REST API for managing systemd services.
"""

from flask import Flask, jsonify, request, render_template, send_from_directory
from pathlib import Path
import config
import systemd_manager
from typing import Dict, Any
import logging
import re

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Configuration
CONFIG_PATH = Path("autorun.yaml")
current_config: config.AutoRunConfig = None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Custom exception handlers
class AutoRunException(Exception):
    """Base exception for AutoRun"""
    pass


@app.errorhandler(config.ConfigValidationError)
def handle_config_validation_error(e):
    """Handle configuration validation errors"""
    return jsonify({
        "status": "error",
        "error": {
            "type": "ConfigValidationError",
            "message": str(e)
        }
    }), 400


@app.errorhandler(systemd_manager.SystemdOperationError)
def handle_systemd_operation_error(e):
    """Handle systemd operation errors"""
    return jsonify({
        "status": "error",
        "error": {
            "type": "SystemdOperationError",
            "message": str(e)
        }
    }), 500


@app.errorhandler(systemd_manager.PermissionError)
def handle_permission_error(e):
    """Handle permission errors"""
    return jsonify({
        "status": "error",
        "error": {
            "type": "PermissionError",
            "message": str(e),
            "hint": "AutoRun may need sudo privileges. Check installation and sudoers configuration."
        }
    }), 403


@app.errorhandler(Exception)
def handle_generic_error(e):
    """Handle generic errors"""
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({
        "status": "error",
        "error": {
            "type": type(e).__name__,
            "message": str(e)
        }
    }), 500


def init_app():
    """Initialize application and load configuration"""
    global current_config

    try:
        if not CONFIG_PATH.exists():
            logger.info("Configuration file not found, creating default")
            current_config = config.create_default_config()
            config.save_config(current_config, CONFIG_PATH)
        else:
            logger.info(f"Loading configuration from {CONFIG_PATH}")
            current_config = config.load_config(CONFIG_PATH)

        # Validate configuration (strict mode for startup to show warnings)
        errors = config.validate_config(current_config, strict=True)
        if errors:
            logger.warning("Configuration has validation errors:")
            for error in errors:
                logger.warning(f"  - {error}")

        logger.info(f"Loaded {len(current_config.services)} services")

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise


def reload_config():
    """Reload configuration from disk"""
    global current_config
    current_config = config.load_config(CONFIG_PATH)
    logger.info("Configuration reloaded")


def find_service(service_name: str) -> config.ServiceConfig:
    """
    Find service by name in current configuration

    Args:
        service_name: Name of service to find

    Returns:
        ServiceConfig object

    Raises:
        AutoRunException: If service not found
    """
    for svc in current_config.services:
        if svc.name == service_name:
            return svc

    raise AutoRunException(f"Service '{service_name}' not found")


# ============================================================================
# Dashboard UI Routes
# ============================================================================

@app.route('/')
def dashboard():
    """Serve dashboard HTML"""
    return render_template('base.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)


# ============================================================================
# Component Rendering Routes (HTMX)
# ============================================================================

@app.route('/components/service-card/<service_name>')
def render_service_card(service_name: str):
    """
    Render a single service card component

    Args:
        service_name: Name of the service

    Returns:
        Rendered HTML fragment for HTMX
    """
    try:
        svc = find_service(service_name)
        status_info = systemd_manager.get_service_status(service_name)

        service_data = {
            "name": svc.name,
            "config": svc.to_dict(),
            **status_info
        }

        return render_template('components/service_card.html', service=service_data)
    except Exception as e:
        logger.error(f"Error rendering service card for '{service_name}': {e}")
        # Return error card
        return f'''
        <div class="service-card status-error" data-service="{service_name}">
            <div class="card-body">
                <p class="service-error">Failed to load service: {str(e)}</p>
            </div>
        </div>
        ''', 500


@app.route('/components/services-grid')
def render_services_grid():
    """
    Render all service cards for the services grid

    Returns:
        Rendered HTML fragments for all services
    """
    services_html = []

    for svc in current_config.services:
        try:
            status_info = systemd_manager.get_service_status(svc.name)
            service_data = {
                "name": svc.name,
                "config": svc.to_dict(),
                **status_info
            }

            card_html = render_template('components/service_card.html', service=service_data)
            services_html.append(card_html)
        except Exception as e:
            logger.error(f"Error rendering card for service '{svc.name}': {e}")
            # Add error card
            services_html.append(f'''
            <div class="service-card status-error" data-service="{svc.name}">
                <div class="card-body">
                    <p class="service-error">Failed to load {svc.name}: {str(e)}</p>
                </div>
            </div>
            ''')

    return '\n'.join(services_html)


@app.route('/components/modal/service-form')
def render_service_form_modal():
    """
    Render service form modal (add or edit)

    Query params:
        mode: 'add' or 'edit'
        service_name: Name of service (required for edit mode)

    Returns:
        Rendered modal HTML fragment
    """
    mode = request.args.get('mode', 'add')
    service_name = request.args.get('service_name')

    service_data = None
    if mode == 'edit' and service_name:
        try:
            svc = find_service(service_name)
            status_info = systemd_manager.get_service_status(service_name)
            service_data = {
                "name": svc.name,
                "config": svc.to_dict(),
                **status_info
            }
        except Exception as e:
            logger.error(f"Error loading service for edit: {e}")

    return render_template('components/modals/service_form.html', mode=mode, service=service_data)


@app.route('/components/modal/delete-confirm/<service_name>')
def render_delete_confirm_modal(service_name: str):
    """
    Render delete confirmation modal

    Args:
        service_name: Name of service to delete

    Returns:
        Rendered modal HTML fragment
    """
    return render_template('components/modals/delete_confirm.html', service_name=service_name)


@app.route('/components/modal/file-browser')
def render_file_browser_modal():
    """
    Render file/folder browser modal

    Query params:
        type: 'folder' or 'file'
        path: Current path to browse (optional, defaults to home)

    Returns:
        Rendered modal HTML fragment with directory listing
    """
    from pathlib import Path

    browser_type = request.args.get('type', 'folder')
    start_path = request.args.get('path', str(Path.home()))

    try:
        path = Path(start_path).resolve()

        # Security: Don't allow browsing outside reasonable paths
        allowed_paths = ('/home', '/opt', '/srv', '/var/www', '/mnt')
        path_str = str(path)

        is_allowed = any(
            path_str == allowed or path_str.startswith(allowed + '/')
            for allowed in allowed_paths
        )

        if not is_allowed:
            return render_template('components/modals/file_browser.html',
                                 browser_type=browser_type,
                                 current_path=path_str,
                                 parent=None,
                                 items=[],
                                 error="Access denied to this path"), 403

        if not path.exists() or not path.is_dir():
            return render_template('components/modals/file_browser.html',
                                 browser_type=browser_type,
                                 current_path=path_str,
                                 parent=None,
                                 items=[],
                                 error="Path does not exist"), 400

        # List items based on type
        items = []
        try:
            if browser_type == 'file':
                # List Python files
                for item in sorted(path.iterdir()):
                    if item.is_file() and item.suffix == '.py':
                        items.append({"name": item.name, "path": str(item)})
            else:
                # List directories
                for item in sorted(path.iterdir()):
                    if item.is_dir() and not item.name.startswith('.'):
                        items.append({"name": item.name, "path": str(item)})
        except PermissionError:
            pass

        # Add parent directory if not at root
        parent = None
        if path != path.parent:
            parent = str(path.parent)

        return render_template('components/modals/file_browser.html',
                             browser_type=browser_type,
                             current_path=str(path),
                             parent=parent,
                             items=items)

    except Exception as e:
        logger.error(f"Error rendering file browser: {e}")
        return render_template('components/modals/file_browser.html',
                             browser_type=browser_type,
                             current_path=start_path,
                             parent=None,
                             items=[],
                             error=str(e)), 500


# ============================================================================
# Service Management API
# ============================================================================

@app.route('/api/services', methods=['GET'])
def list_services():
    """
    Get list of all services with current status

    Returns:
        JSON with services list and statistics
    """
    services_data = []

    for svc in current_config.services:
        try:
            # Get systemd status
            status_info = systemd_manager.get_service_status(svc.name)

            services_data.append({
                "name": svc.name,
                "config": svc.to_dict(),
                **status_info
            })
        except Exception as e:
            logger.error(f"Error getting status for service '{svc.name}': {e}")
            # Return partial status if systemd query fails
            services_data.append({
                "name": svc.name,
                "config": svc.to_dict(),
                "status": "unknown",
                "active": False,
                "enabled": svc.enabled,
                "pid": None,
                "uptime": "N/A",
                "memory_mb": 0.0
            })

    # Calculate statistics
    total = len(services_data)
    running = sum(1 for s in services_data if s['status'] == 'running')
    stopped = sum(1 for s in services_data if s['status'] == 'stopped')
    failed = sum(1 for s in services_data if s['status'] == 'failed')

    return jsonify({
        "status": "success",
        "data": {
            "services": services_data,
            "total": total,
            "running": running,
            "stopped": stopped,
            "failed": failed
        }
    })


@app.route('/api/services/<service_name>', methods=['GET'])
def get_service(service_name: str):
    """
    Get specific service details

    Args:
        service_name: Name of the service

    Returns:
        JSON with service details and status
    """
    svc = find_service(service_name)
    status_info = systemd_manager.get_service_status(service_name)

    return jsonify({
        "status": "success",
        "data": {
            "name": svc.name,
            "config": svc.to_dict(),
            **status_info
        }
    })


@app.route('/api/services', methods=['POST'])
def create_service():
    """
    Create a new service

    Request body should contain service configuration fields

    Returns:
        JSON with created service details
    """
    data = request.get_json()

    if not data:
        return jsonify({
            "status": "error",
            "error": {"message": "Request body is required"}
        }), 400

    # Validate required fields
    if 'name' not in data:
        return jsonify({
            "status": "error",
            "error": {"message": "Field 'name' is required"}
        }), 400

    # Validate service name format (must be systemd-compatible)
    service_name = data['name']
    if not re.match(r'^[a-z0-9-]+$', service_name):
        return jsonify({
            "status": "error",
            "error": {
                "message": "Invalid service name",
                "details": "Service name must contain only lowercase letters, numbers, and hyphens"
            }
        }), 400

    if len(service_name) > 64:
        return jsonify({
            "status": "error",
            "error": {"message": "Service name too long (max 64 characters)"}
        }), 400

    if 'folder' not in data:
        return jsonify({
            "status": "error",
            "error": {"message": "Field 'folder' is required"}
        }), 400

    if 'entrypoint' not in data:
        data['entrypoint'] = 'run.py'  # Default

    # Create service config object
    try:
        service = config.ServiceConfig(**data)
    except TypeError as e:
        return jsonify({
            "status": "error",
            "error": {"message": f"Invalid service configuration: {e}"}
        }), 400

    # Check if service already exists
    existing_names = [s.name for s in current_config.services]
    if service.name in existing_names:
        return jsonify({
            "status": "error",
            "error": {"message": f"Service '{service.name}' already exists"}
        }), 409

    # Add to configuration
    current_config.services.append(service)

    # Validate entire configuration (non-strict mode - allow missing folders/files)
    errors = config.validate_config(current_config, strict=False)
    if errors:
        # Remove the service we just added
        current_config.services.remove(service)
        return jsonify({
            "status": "error",
            "error": {
                "message": "Configuration validation failed",
                "details": errors
            }
        }), 400

    # Save configuration
    config.save_config(current_config, CONFIG_PATH)
    logger.info(f"Created service: {service.name}")

    # Generate systemd service file
    try:
        systemd_manager.write_service_file(service, current_config.metadata.default_user)
        systemd_manager.daemon_reload()

        # Enable if configured
        if service.enabled:
            systemd_manager.enable_service(service.name, now=False)

        logger.info(f"Generated systemd service file for: {service.name}")
    except Exception as e:
        logger.error(f"Failed to create systemd service: {e}")
        # Service is still in config, but systemd setup failed
        return jsonify({
            "status": "error",
            "error": {
                "message": f"Service created in configuration but systemd setup failed: {e}",
                "hint": "Service is saved but may not be operational"
            }
        }), 500

    return jsonify({
        "status": "success",
        "message": f"Service '{service.name}' created successfully",
        "data": service.to_dict()
    }), 201


@app.route('/api/services/<service_name>', methods=['PUT'])
def update_service(service_name: str):
    """
    Update an existing service configuration

    Args:
        service_name: Name of service to update

    Returns:
        JSON with updated service details
    """
    svc = find_service(service_name)
    data = request.get_json()

    if not data:
        return jsonify({
            "status": "error",
            "error": {"message": "Request body is required"}
        }), 400

    # Update fields
    for key, value in data.items():
        if hasattr(svc, key) and key != 'name':  # Don't allow name changes
            setattr(svc, key, value)

    # Validate configuration (non-strict mode - allow missing folders/files)
    errors = config.validate_config(current_config, strict=False)
    if errors:
        return jsonify({
            "status": "error",
            "error": {
                "message": "Configuration validation failed",
                "details": errors
            }
        }), 400

    # Save configuration
    config.save_config(current_config, CONFIG_PATH)
    logger.info(f"Updated service: {service_name}")

    # Regenerate systemd service file
    try:
        systemd_manager.write_service_file(svc, current_config.metadata.default_user)
        systemd_manager.daemon_reload()
        logger.info(f"Regenerated systemd service file for: {service_name}")
    except Exception as e:
        logger.error(f"Failed to update systemd service: {e}")
        return jsonify({
            "status": "error",
            "error": {"message": f"Configuration updated but systemd setup failed: {e}"}
        }), 500

    return jsonify({
        "status": "success",
        "message": f"Service '{service_name}' updated successfully",
        "data": svc.to_dict()
    })


@app.route('/api/services/<service_name>', methods=['DELETE'])
def delete_service(service_name: str):
    """
    Delete a service

    Args:
        service_name: Name of service to delete

    Returns:
        JSON with success message
    """
    svc = find_service(service_name)

    # Stop service if running
    try:
        if systemd_manager.is_service_active(service_name):
            systemd_manager.stop_service(service_name)
    except Exception as e:
        logger.warning(f"Failed to stop service before deletion: {e}")

    # Disable service
    try:
        if systemd_manager.is_service_enabled(service_name):
            systemd_manager.disable_service(service_name, now=False)
    except Exception as e:
        logger.warning(f"Failed to disable service before deletion: {e}")

    # Delete systemd service file
    try:
        systemd_manager.delete_service_file(service_name)
        systemd_manager.daemon_reload()
    except Exception as e:
        logger.error(f"Failed to delete systemd service file: {e}")

    # Remove from configuration
    current_config.services.remove(svc)
    config.save_config(current_config, CONFIG_PATH)
    logger.info(f"Deleted service: {service_name}")

    return jsonify({
        "status": "success",
        "message": f"Service '{service_name}' deleted successfully"
    })


# ============================================================================
# Service Control API
# ============================================================================

@app.route('/api/services/<service_name>/start', methods=['POST'])
def start_service_endpoint(service_name: str):
    """Start a service"""
    find_service(service_name)  # Verify service exists

    systemd_manager.start_service(service_name)
    logger.info(f"Started service: {service_name}")

    # Get updated status
    status_info = systemd_manager.get_service_status(service_name)

    return jsonify({
        "status": "success",
        "message": f"Service '{service_name}' started",
        "data": status_info
    })


@app.route('/api/services/<service_name>/stop', methods=['POST'])
def stop_service_endpoint(service_name: str):
    """Stop a service"""
    find_service(service_name)  # Verify service exists

    systemd_manager.stop_service(service_name)
    logger.info(f"Stopped service: {service_name}")

    # Get updated status
    status_info = systemd_manager.get_service_status(service_name)

    return jsonify({
        "status": "success",
        "message": f"Service '{service_name}' stopped",
        "data": status_info
    })


@app.route('/api/services/<service_name>/restart', methods=['POST'])
def restart_service_endpoint(service_name: str):
    """Restart a service"""
    find_service(service_name)  # Verify service exists

    systemd_manager.restart_service(service_name)
    logger.info(f"Restarted service: {service_name}")

    # Get updated status
    status_info = systemd_manager.get_service_status(service_name)

    return jsonify({
        "status": "success",
        "message": f"Service '{service_name}' restarted",
        "data": status_info
    })


@app.route('/api/services/<service_name>/enable', methods=['POST'])
def enable_service_endpoint(service_name: str):
    """Enable a service to start on boot"""
    svc = find_service(service_name)

    systemd_manager.enable_service(service_name, now=False)
    logger.info(f"Enabled service: {service_name}")

    # Update config
    svc.enabled = True
    config.save_config(current_config, CONFIG_PATH)

    return jsonify({
        "status": "success",
        "message": f"Service '{service_name}' enabled"
    })


@app.route('/api/services/<service_name>/disable', methods=['POST'])
def disable_service_endpoint(service_name: str):
    """Disable a service from starting on boot"""
    svc = find_service(service_name)

    systemd_manager.disable_service(service_name, now=False)
    logger.info(f"Disabled service: {service_name}")

    # Update config
    svc.enabled = False
    config.save_config(current_config, CONFIG_PATH)

    return jsonify({
        "status": "success",
        "message": f"Service '{service_name}' disabled"
    })


# ============================================================================
# System Management API
# ============================================================================

@app.route('/api/system/reload', methods=['POST'])
def reload_config_endpoint():
    """
    Reload configuration from disk and regenerate all systemd files
    """
    try:
        reload_config()

        # Regenerate all systemd service files
        for svc in current_config.services:
            try:
                systemd_manager.write_service_file(svc, current_config.metadata.default_user)
            except Exception as e:
                logger.error(f"Failed to regenerate service file for '{svc.name}': {e}")

        systemd_manager.daemon_reload()
        logger.info("Configuration reloaded and systemd files regenerated")

        return jsonify({
            "status": "success",
            "message": "Configuration reloaded successfully",
            "data": {
                "services_count": len(current_config.services)
            }
        })

    except Exception as e:
        logger.error(f"Failed to reload configuration: {e}")
        raise


@app.route('/api/system/daemon-reload', methods=['POST'])
def daemon_reload_endpoint():
    """
    Run systemctl daemon-reload
    """
    systemd_manager.daemon_reload()
    logger.info("Executed systemctl daemon-reload")

    return jsonify({
        "status": "success",
        "message": "systemctl daemon-reload executed successfully"
    })


@app.route('/api/system/status', methods=['GET'])
def system_status():
    """
    Get overall system status
    """
    services_data = []

    for svc in current_config.services:
        try:
            status_info = systemd_manager.get_service_status(svc.name)
            services_data.append({
                "name": svc.name,
                "status": status_info["status"]
            })
        except Exception:
            services_data.append({
                "name": svc.name,
                "status": "unknown"
            })

    total = len(services_data)
    running = sum(1 for s in services_data if s['status'] == 'running')
    stopped = sum(1 for s in services_data if s['status'] == 'stopped')
    failed = sum(1 for s in services_data if s['status'] == 'failed')

    return jsonify({
        "status": "success",
        "data": {
            "total_services": total,
            "running": running,
            "stopped": stopped,
            "failed": failed,
            "services": services_data
        }
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        "status": "success",
        "message": "AutoRun v2 is running",
        "data": {
            "version": current_config.metadata.version if current_config else "unknown",
            "services_count": len(current_config.services) if current_config else 0
        }
    })


@app.route('/api/browse/folders', methods=['GET'])
def browse_folders():
    """
    Browse folders for service configuration

    Query params:
        path: Optional starting path (defaults to user home)
    """
    from pathlib import Path
    import os

    start_path = request.args.get('path', str(Path.home()))

    try:
        path = Path(start_path).resolve()

        # Security: Don't allow browsing outside reasonable paths
        # Allow /home and its subdirectories, /opt, /srv, /var/www
        allowed_paths = ('/home', '/opt', '/srv', '/var/www', '/mnt')
        path_str = str(path)

        # Check if path is exactly an allowed path or starts with an allowed path + /
        is_allowed = any(
            path_str == allowed or path_str.startswith(allowed + '/')
            for allowed in allowed_paths
        )

        if not is_allowed:
            return jsonify({
                "status": "error",
                "error": {"message": f"Access denied to this path: {path_str}"}
            }), 403

        if not path.exists() or not path.is_dir():
            return jsonify({
                "status": "error",
                "error": {"message": "Path does not exist or is not a directory"}
            }), 400

        # List directories
        folders = []
        try:
            for item in sorted(path.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    folders.append({
                        "name": item.name,
                        "path": str(item)
                    })
        except PermissionError:
            pass

        # Add parent directory if not at root
        parent = None
        if path != path.parent:
            parent = str(path.parent)

        return jsonify({
            "status": "success",
            "data": {
                "current_path": str(path),
                "parent": parent,
                "folders": folders
            }
        })

    except Exception as e:
        logger.error(f"Error browsing folders: {e}")
        return jsonify({
            "status": "error",
            "error": {"message": str(e)}
        }), 500


@app.route('/api/browse/files', methods=['GET'])
def browse_files():
    """
    Browse Python files in a folder

    Query params:
        path: Folder path to browse
    """
    from pathlib import Path

    folder_path = request.args.get('path')
    if not folder_path:
        return jsonify({
            "status": "error",
            "error": {"message": "Path parameter is required"}
        }), 400

    try:
        path = Path(folder_path).resolve()

        if not path.exists() or not path.is_dir():
            return jsonify({
                "status": "error",
                "error": {"message": "Path does not exist or is not a directory"}
            }), 400

        # List Python files
        files = []
        try:
            for item in sorted(path.iterdir()):
                if item.is_file() and item.suffix == '.py':
                    files.append({
                        "name": item.name,
                        "path": str(item)
                    })
        except PermissionError:
            pass

        return jsonify({
            "status": "success",
            "data": {
                "folder": str(path),
                "files": files
            }
        })

    except Exception as e:
        logger.error(f"Error browsing files: {e}")
        return jsonify({
            "status": "error",
            "error": {"message": str(e)}
        }), 500


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == '__main__':
    init_app()

    port = current_config.metadata.dashboard_port if current_config else 80

    logger.info(f"Starting AutoRun v2 on port {port}")
    logger.info("Dashboard: http://localhost" + (f":{port}" if port != 80 else ""))

    app.run(host='0.0.0.0', port=port, debug=False)
