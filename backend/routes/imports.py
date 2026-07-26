"""Routes for the Import Dives tab (storage folder, single and bulk import)."""

import traceback
from pathlib import Path

from flask import Blueprint, flash, jsonify, redirect, request, url_for

from backend.services import chat_service, gear_service, import_service, progress
from backend.state import state

imports_bp = Blueprint("imports", __name__, url_prefix="/import")


def _import_redirect(mode=None):
    return redirect(url_for("pages.import_page", mode=mode or state.import_mode))


@imports_bp.post("/storage-folder")
def set_storage_folder():
    """Apply (and create if needed) the dive storage folder."""
    folder = request.form.get("storage_folder", "")
    try:
        import_service.apply_storage_folder(folder)
        flash(f"Storage folder updated to: {state.storage_folder}", "success")
    except Exception as e:
        flash(f"Failed to set storage folder: {e}", "error")
    return _import_redirect()


@imports_bp.post("/reload")
def reload_all_dives():
    """Clear the agent cache so dives are reloaded on next query."""
    chat_service.refresh_agent()
    message = "Agent cache cleared. Dives will be reloaded on next query."
    dive_count = import_service.count_dives()
    if dive_count is not None:
        message += f" Found {dive_count} dive files in storage folder."
    flash(message, "success")
    return _import_redirect()


# --- Single dive import -------------------------------------------------------

@imports_bp.post("/single/upload")
def upload_single():
    """Stage an uploaded .fit file and show its auto-extracted preview."""
    file = request.files.get("fit_file")
    if file is None or not file.filename:
        flash("Upload a .fit file to begin importing a dive.", "error")
        return _import_redirect("single")
    if not file.filename.lower().endswith(".fit"):
        flash("Only .fit files are supported.", "error")
        return _import_redirect("single")

    try:
        import_service.stage_single_upload(file)
        flash(f"File loaded: {file.filename}", "success")
    except Exception as e:
        flash(f"Failed to parse .fit file: {e}", "error")
    return _import_redirect("single")


@imports_bp.post("/single/cancel")
def cancel_single():
    """Discard the pending upload."""
    import_service.discard_pending_upload()
    return _import_redirect("single")


@imports_bp.post("/single/confirm")
def confirm_single():
    """Import the pending upload with the metadata form values."""
    form = request.form
    gear_items = gear_service.load_gear_items()

    def gear_path(field: str, gear_type: str):
        selected = form.get(field, "None")
        if selected == "None":
            return None
        return gear_items[gear_type].get(selected)

    try:
        details = import_service.import_single_dive(
            token=form.get("token", ""),
            location_name=form.get("location_name", ""),
            location_description=form.get("location_description", ""),
            buddy=form.get("buddy", ""),
            divemaster=form.get("divemaster", ""),
            group_input=form.get("group", ""),
            start_pressure=int(form.get("start_pressure", 200)),
            end_pressure=int(form.get("end_pressure", 50)),
            weights=float(form.get("weights", 0.0)),
            gear_paths={
                "suit": gear_path("suit", "Suit"),
                "mask": gear_path("mask", "Mask"),
                "gloves": gear_path("gloves", "Gloves"),
                "boots": gear_path("boots", "Boots"),
                "bcd": gear_path("bcd", "BCD"),
                "fins": gear_path("fins", "Fins"),
            },
        )
        depth_str = (
            f", max depth {details['max_depth']:.1f} m"
            if details["max_depth"] is not None
            else ""
        )
        flash(
            "Dive imported successfully! "
            f"Duration {details['duration_min']:.1f} min{depth_str}, "
            f"location: {details['location']}. Saved to: {details['output_path']}",
            "success",
        )
    except Exception as e:
        traceback.print_exc()
        flash(f"Failed to import dive: {e}", "error")
    return _import_redirect("single")


# --- Bulk import ---------------------------------------------------------------

@imports_bp.post("/bulk/scan")
def scan_bulk():
    """Scan a folder for .fit files and show the preview."""
    folder = request.form.get("fit_folder", "")
    try:
        import_service.scan_bulk_folder(folder)
        state.bulk_folder = folder.strip()
    except ValueError as e:
        state.bulk_folder = None
        flash(str(e), "error")
    return _import_redirect("bulk")


@imports_bp.post("/bulk/run")
def run_bulk():
    """Start importing all .fit files from the scanned folder."""
    folder = state.bulk_folder
    if not folder or not Path(folder).is_dir():
        flash("Scan a folder containing .fit files first.", "error")
        return _import_redirect("bulk")

    if progress.job_running():
        flash("An import is already running. Wait for it to finish.", "warning")
        return _import_redirect("bulk")

    copy_fit_files = request.form.get("copy_fit_files") == "on"
    total = import_service.count_fit_files(folder)

    # The import runs on a worker thread; the page polls /import/progress and
    # reloads itself when the job reports finished.
    state.bulk_results = None
    state.import_job = progress.start_job(
        "bulk",
        total,
        lambda job: import_service.run_bulk_import(folder, copy_fit_files, job),
    )
    flash(f"Importing {total} .fit files...", "info")
    return _import_redirect("bulk")


# --- Progress ------------------------------------------------------------------

@imports_bp.get("/progress")
def import_progress():
    """Snapshot of the running import, polled by frontend/static/js/import.js."""
    job = state.import_job
    return jsonify({"ok": True, "job": job.snapshot() if job else None})
