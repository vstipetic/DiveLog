"""
CSRF protection for state-changing requests.

DiveLog binds to localhost and has no login, which is exactly what makes it
CSRF-able: a cross-origin form POST needs no preflight, so any page open in the
user's browser could drive the app while it is running -- change the storage
folder, kick off an import from a path of its own choosing, or post credentials
to the Garmin login route. Streamlit enabled XSRF protection by default; this
module is the equivalent for the Flask backend.

The scheme is the standard synchronizer token:

* a random token is minted per browser session and kept in the signed session
  cookie (an attacker's page can make the browser *send* that cookie, but same
  origin policy stops it from *reading* the token);
* every unsafe request must echo the token back, in the ``_csrf_token`` form
  field for classic form posts or the ``X-CSRF-Token`` header for the JSON API;
* mismatches are rejected before the route ever runs.
"""

import hmac
import secrets
from typing import Optional

from flask import Flask, jsonify, request, session

SESSION_KEY = "csrf_token"
FORM_FIELD = "_csrf_token"
HEADER_NAME = "X-CSRF-Token"

# Methods that must not change server state, and so need no token.
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def csrf_token() -> str:
    """Return this session's CSRF token, minting one on first use."""
    token = session.get(SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[SESSION_KEY] = token
    return token


def _submitted_token() -> Optional[str]:
    """The token the client sent, from either the form body or the header."""
    return request.form.get(FORM_FIELD) or request.headers.get(HEADER_NAME)


def init_csrf(app: Flask) -> None:
    """Install the CSRF check and expose ``csrf_token()`` to templates."""

    @app.before_request
    def _require_csrf_token():
        if request.method in SAFE_METHODS:
            return None

        expected = session.get(SESSION_KEY)
        submitted = _submitted_token()
        if expected and submitted and hmac.compare_digest(expected, submitted):
            return None

        message = (
            "CSRF token missing or invalid. Reload the page and try again."
        )
        # The chat API is consumed by fetch(), so it gets JSON back rather than
        # Flask's HTML error page.
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": message}), 400
        return message, 400

    app.jinja_env.globals["csrf_token"] = csrf_token
