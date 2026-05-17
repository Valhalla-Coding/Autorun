from .ui import ui_bp
from .services import services_bp
from .system import system_bp
from .github import github_bp


def register_routes(app):
    app.register_blueprint(ui_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(github_bp)
