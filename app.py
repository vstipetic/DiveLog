"""
DiveLog application entry point.

Backend: Flask (backend/), Frontend: Jinja2 templates + static assets (frontend/).

Run with: python app.py  (or: flask --app app run)
Then open http://localhost:5000
"""

import os

from backend import create_app

app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("DIVELOG_HOST", "127.0.0.1"),
        port=int(os.environ.get("DIVELOG_PORT", "5000")),
        debug=os.environ.get("DIVELOG_DEBUG", "").lower() in ("1", "true", "yes"),
    )
