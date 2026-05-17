"""
AutoRun v2 - UI Routes

Dashboard page and HTMX component fragment endpoints.
"""

from pathlib import Path

from flask import Blueprint, render_template, request, send_from_directory

import state
import systemd_manager

ui_bp = Blueprint('ui', __name__)


# ============================================================================
# Dashboard
# ============================================================================

@ui_bp.route('/')
def dashboard():
    return render_template('base.html')


@ui_bp.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


# ============================================================================
# HTMX Component Fragments
# ============================================================================

@ui_bp.route('/components/service-card/<service_name>')
def render_service_card(service_name: str):
    try:
        svc = state.find_service(service_name)
        status_info = systemd_manager.get_service_status(service_name)
        service_data = {"name": svc.name, "config": svc.to_dict(), **status_info}
        return render_template('components/service_card.html', service=service_data)
    except Exception as e:
        state.logger.error(f"Error rendering service card for '{service_name}': {e}")
        return f'''
        <div class="service-card status-error" data-service="{service_name}">
            <div class="card-body">
                <p class="service-error">Failed to load service: {str(e)}</p>
            </div>
        </div>
        ''', 500


@ui_bp.route('/components/services-grid')
def render_services_grid():
    services_html = []
    for svc in state.current_config.services:
        try:
            status_info = systemd_manager.get_service_status(svc.name)
            service_data = {"name": svc.name, "config": svc.to_dict(), **status_info}
            services_html.append(render_template('components/service_card.html', service=service_data))
        except Exception as e:
            state.logger.error(f"Error rendering card for service '{svc.name}': {e}")
            services_html.append(f'''
            <div class="service-card status-error" data-service="{svc.name}">
                <div class="card-body">
                    <p class="service-error">Failed to load {svc.name}: {str(e)}</p>
                </div>
            </div>
            ''')
    return '\n'.join(services_html)


@ui_bp.route('/components/modal/service-form')
def render_service_form_modal():
    mode = request.args.get('mode', 'add')
    service_name = request.args.get('service_name')

    service_data = None
    if mode == 'edit' and service_name:
        try:
            svc = state.find_service(service_name)
            status_info = systemd_manager.get_service_status(service_name)
            service_data = {"name": svc.name, "config": svc.to_dict(), **status_info}
        except Exception as e:
            state.logger.error(f"Error loading service for edit: {e}")

    return render_template('components/modals/service_form.html', mode=mode, service=service_data)


@ui_bp.route('/components/modal/delete-confirm/<service_name>')
def render_delete_confirm_modal(service_name: str):
    return render_template('components/modals/delete_confirm.html', service_name=service_name)


@ui_bp.route('/components/modal/file-browser')
def render_file_browser_modal():
    browser_type = request.args.get('type', 'folder')
    start_path = request.args.get('path', str(Path.home()))

    def error_response(msg, code=500):
        return render_template(
            'components/modals/file_browser.html',
            browser_type=browser_type, current_path=start_path,
            parent=None, items=[], error=msg
        ), code

    try:
        path = Path(start_path).resolve()
        path_str = str(path)

        allowed_paths = ('/home', '/opt', '/srv', '/var/www', '/mnt')
        if not any(path_str == a or path_str.startswith(a + '/') for a in allowed_paths):
            return error_response("Access denied to this path", 403)

        if not path.exists() or not path.is_dir():
            return error_response("Path does not exist", 400)

        items = []
        try:
            if browser_type == 'file':
                items = [{"name": i.name, "path": str(i)}
                         for i in sorted(path.iterdir()) if i.is_file() and i.suffix == '.py']
            else:
                items = [{"name": i.name, "path": str(i)}
                         for i in sorted(path.iterdir()) if i.is_dir() and not i.name.startswith('.')]
        except PermissionError:
            pass

        parent = str(path.parent) if path != path.parent else None
        return render_template('components/modals/file_browser.html',
                               browser_type=browser_type, current_path=path_str,
                               parent=parent, items=items)
    except Exception as e:
        state.logger.error(f"Error rendering file browser: {e}")
        return error_response(str(e))
