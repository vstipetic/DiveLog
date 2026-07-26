"""
Flask backend for DiveLog.

The backend owns all application logic (agent orchestration, dive import,
gear management, Garmin Connect integration) and exposes it through HTML
routes and a small JSON API. The frontend lives in ``frontend/`` and is
rendered with Jinja2 templates.

Run with: python app.py
"""

import os
import secrets
from pathlib import Path

from flask import Flask

from backend.utils import format_duration, format_surface_interval

# Repository root (the folder containing app.py, backend/ and frontend/).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def create_app() -> Flask:
    """Application factory: build and configure the Flask app."""
    app = Flask(
        __name__,
        template_folder=str(FRONTEND_DIR / "templates"),
        static_folder=str(FRONTEND_DIR / "static"),
    )

    # Only used for flash messages / session cookie signing. DiveLog is a
    # local, single-user app, so an ephemeral key is fine unless overridden.
    app.secret_key = os.environ.get("DIVELOG_SECRET_KEY") or secrets.token_hex(32)

    # .fit files are small; 64 MB gives generous headroom for uploads.
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024

    # Jinja filters shared by templates.
    app.jinja_env.filters["duration"] = format_duration
    app.jinja_env.filters["surface_interval"] = format_surface_interval

    # Sidebar data (provider list, current selection, dive counts) is needed
    # on every page, so it is injected as template context globally.
    from backend.services import settings_service

    @app.context_processor
    def inject_sidebar_context():
        return {"sidebar": settings_service.get_sidebar_context()}

    from backend.routes import register_blueprints
    register_blueprints(app)

    return app
