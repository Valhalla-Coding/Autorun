from .auth import auth_bp
from .services import services_bp
from .system import system_bp
from .github import github_bp
from .settings import settings_bp
from .ui import ui_bp


def register_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(github_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(ui_bp)  # must be last — catches all non-API paths
