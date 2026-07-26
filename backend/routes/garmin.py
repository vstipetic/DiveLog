"""Routes for the 'Import from Garmin' flow (login, MFA, fetch, import)."""

from flask import Blueprint, flash, redirect, request, url_for

from backend.services import garmin_service, progress
from backend.state import state

garmin_bp = Blueprint("garmin", __name__, url_prefix="/garmin")


def _garmin_redirect():
    return redirect(url_for("pages.import_page", mode="garmin"))


@garmin_bp.post("/login")
def login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    if not email or not password:
        flash("Enter both email and password.", "error")
        return _garmin_redirect()

    try:
        logged_in = garmin_service.begin_login(email, password)
    except Exception as e:
        flash(f"Login failed: {e}", "error")
        return _garmin_redirect()

    if logged_in:
        flash("Connected to Garmin Connect.", "success")
    else:
        flash("This account requires multi-factor authentication.", "info")
    return _garmin_redirect()


@garmin_bp.post("/mfa")
def mfa():
    code = request.form.get("mfa_code", "")
    try:
        garmin_service.finish_mfa(code)
        flash("Verified. Connected to Garmin Connect.", "success")
    except Exception as e:
        flash(f"MFA verification failed: {e}", "error")
    return _garmin_redirect()


@garmin_bp.post("/mfa/cancel")
def cancel_mfa():
    garmin_service.cancel_mfa()
    return _garmin_redirect()


@garmin_bp.post("/logout")
def logout():
    garmin_service.logout()
    return _garmin_redirect()


@garmin_bp.post("/fetch")
def fetch_dives():
    """Fetch diving activities in the selected date range."""
    default_start, default_end = garmin_service.default_date_range()
    start_date = request.form.get("start_date") or default_start
    end_date = request.form.get("end_date") or default_end

    try:
        dives = garmin_service.fetch_dives(start_date, end_date)
    except Exception as e:
        flash(f"Failed to fetch dives: {e}", "error")
        return _garmin_redirect()

    if not dives:
        flash("No diving activities found in that date range.", "warning")
    else:
        flash(f"Found {len(dives)} diving activities.", "success")
    return _garmin_redirect()


@garmin_bp.post("/import")
def import_selected():
    """Start downloading and importing the selected dives."""
    selected_ids = request.form.getlist("dive_ids")
    if not selected_ids:
        flash("No dives selected.", "warning")
        return _garmin_redirect()

    if state.garmin_client is None:
        flash("Not connected to Garmin Connect.", "error")
        return _garmin_redirect()

    if progress.job_running():
        flash("An import is already running. Wait for it to finish.", "warning")
        return _garmin_redirect()

    use_ai = request.form.get("use_ai") == "on"
    # Resolve display labels now, on the request thread, while the fetched dive
    # list is known to match the selection.
    labels = garmin_service.dive_labels()

    state.garmin_results = None
    state.import_job = progress.start_job(
        "garmin",
        len(selected_ids),
        lambda job: garmin_service.download_and_import(
            selected_ids, use_ai, job, labels
        ),
    )
    flash(f"Importing {len(selected_ids)} dives from Garmin...", "info")
    return _garmin_redirect()
