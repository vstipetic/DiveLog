"""HTML page routes (rendered with Jinja2 templates from frontend/)."""

from pathlib import Path

from flask import Blueprint, render_template, request

from Utilities.APIKeyDetector import detect_garmin_credentials

from backend.services import (
    chat_service,
    garmin_service,
    gear_service,
    import_service,
    progress,
)
from backend.state import state

pages_bp = Blueprint("pages", __name__)

IMPORT_MODES = ("single", "bulk", "garmin")


@pages_bp.route("/")
def chat_page():
    """AI Chat tab."""
    agent = chat_service.get_agent()
    return render_template(
        "chat.html",
        active_tab="chat",
        agent_available=agent is not None,
        dive_count=len(agent.dives) if agent else 0,
        quick_stats=chat_service.get_quick_stats(agent),
        example_queries=chat_service.EXAMPLE_QUERIES,
        messages=state.messages,
    )


@pages_bp.route("/import")
def import_page():
    """Import Dives tab (single / bulk / Garmin modes)."""
    mode = request.args.get("mode")
    if mode in IMPORT_MODES:
        state.import_mode = mode
    mode = state.import_mode

    # A worker thread may have finished since the last render; move its results
    # into the slot the results panel reads from before building the context.
    progress.harvest_finished_job()
    import_job = state.import_job

    storage_path = Path(state.storage_folder)

    context = {
        "active_tab": "import",
        "mode": mode,
        "storage_folder": state.storage_folder,
        "storage_folder_exists": storage_path.exists(),
        "dive_count": import_service.count_dives(),
        "import_job": import_job.snapshot() if import_job else None,
    }

    if mode == "single":
        context["pending_upload"] = state.pending_upload
        context["gear_items"] = gear_service.load_gear_items()
    elif mode == "bulk":
        bulk_scan = None
        if state.bulk_folder:
            try:
                bulk_scan = import_service.scan_bulk_folder(state.bulk_folder)
            except ValueError:
                state.bulk_folder = None
        context["bulk_folder"] = state.bulk_folder or ""
        context["bulk_scan"] = bulk_scan
        # Bulk results are shown once after the import completes.
        context["bulk_results"] = state.bulk_results
        state.bulk_results = None
    elif mode == "garmin":
        authenticated = garmin_service.is_authenticated()
        context["garmin_authenticated"] = authenticated
        context["garmin_mfa_pending"] = garmin_service.mfa_pending()
        context["garmin_credentials"] = detect_garmin_credentials()
        start_date, end_date = garmin_service.current_date_range()
        context["garmin_start_date"] = start_date
        context["garmin_end_date"] = end_date
        if authenticated:
            context["garmin_dives"] = (
                garmin_service.dive_display_rows()
                if state.garmin_dive_list is not None
                else None
            )
            context["ai_parsing_available"] = garmin_service.ai_parsing_available()
        # Garmin results are shown once after the import completes.
        context["garmin_results"] = state.garmin_results
        state.garmin_results = None

    return render_template("import.html", **context)


@pages_bp.route("/gear")
def gear_page():
    """Add Gear tab."""
    gear_items = gear_service.load_gear_items()
    total_gear = sum(len(items) for items in gear_items.values())
    return render_template(
        "gear.html",
        active_tab="gear",
        gear_types=gear_service.GEAR_TYPES,
        glove_sizes=gear_service.GLOVE_SIZES,
        gear_items=gear_items,
        total_gear=total_gear,
    )
