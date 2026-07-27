"""Blueprint registration for the DiveLog backend."""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    from backend.routes.pages import pages_bp
    from backend.routes.chat import chat_bp
    from backend.routes.settings import settings_bp
    from backend.routes.imports import imports_bp
    from backend.routes.garmin import garmin_bp
    from backend.routes.gear import gear_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(imports_bp)
    app.register_blueprint(garmin_bp)
    app.register_blueprint(gear_bp)
