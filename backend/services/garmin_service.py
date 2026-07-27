"""
Garmin Connect service: login (with MFA), dive listing, and download/import.

Wraps Utilities.GarminConnectClient unchanged; the two-step MFA flow maps
directly onto two HTTP endpoints instead of two Streamlit reruns.
"""

import pickle
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from Utilities import GarminConnectClient
from Utilities.Parsers.GarminDiveParser import parse_garmin_dive

from backend.services.chat_service import refresh_agent
from backend.services.progress import ImportJob
from backend.state import state
from backend.utils import format_duration


def is_authenticated() -> bool:
    """True when a Garmin client is available (resuming from cache if possible)."""
    if state.garmin_client is None:
        resumed = GarminConnectClient.resume_session()
        if resumed is not None:
            state.garmin_client = resumed
    return state.garmin_client is not None


def mfa_pending() -> bool:
    return state.garmin_mfa_state is not None


def begin_login(email: str, password: str) -> bool:
    """
    Start a Garmin login. Returns True when fully logged in, False when an
    MFA code is required (state is kept until finish_mfa/cancel_mfa).
    """
    client, mfa_state = GarminConnectClient.begin_login(email, password)
    if mfa_state is not None:
        state.garmin_pending_client = client
        state.garmin_mfa_state = mfa_state
        return False
    state.garmin_client = client
    return True


def finish_mfa(code: str) -> None:
    """Complete a pending MFA login with the one-time code."""
    client = state.garmin_pending_client
    GarminConnectClient.finish_mfa(client, state.garmin_mfa_state, code)
    state.garmin_client = client
    state.garmin_mfa_state = None
    state.garmin_pending_client = None


def cancel_mfa() -> None:
    state.garmin_mfa_state = None
    state.garmin_pending_client = None


def logout() -> None:
    state.garmin_client = None
    state.garmin_mfa_state = None
    state.garmin_pending_client = None
    state.garmin_dive_list = None
    state.garmin_results = None


def default_date_range() -> Tuple[str, str]:
    """The range the fetch form starts on before the user picks one: last 90 days."""
    today = date.today()
    return (
        (today - timedelta(days=90)).strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d"),
    )


def current_date_range() -> Tuple[str, str]:
    """The range to render in the form: the user's last choice, else the default."""
    default_start, default_end = default_date_range()
    return (
        state.garmin_start_date or default_start,
        state.garmin_end_date or default_end,
    )


def fetch_dives(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Fetch diving activities in the date range and keep them in state."""
    # Remembered so the form redisplays the user's range instead of snapping
    # back to the default after the post/redirect.
    state.garmin_start_date = start_date
    state.garmin_end_date = end_date
    dives = GarminConnectClient.list_dives(state.garmin_client, start_date, end_date)
    state.garmin_dive_list = dives
    return dives


def dive_display_rows() -> List[Dict[str, Any]]:
    """
    Build display rows for the fetched dives: label text and whether the
    dive was already imported (pre-unchecked in the UI, like Streamlit).
    """
    dives = state.garmin_dive_list or []
    rows = []
    for dive in dives:
        activity_id = dive["activity_id"]
        imported = GarminConnectClient.already_imported(
            activity_id, state.storage_folder
        )

        start = dive.get("start_time") or "?"
        depth = dive.get("max_depth")
        duration = dive.get("duration")
        depth_str = f"{depth:.1f}m" if isinstance(depth, (int, float)) else "?"
        dur_str = format_duration(duration) if duration else "?"
        dive_number = dive.get("dive_number")
        num_str = f"#{dive_number} " if dive_number is not None else ""
        location = dive.get("location_name")
        loc_str = f" @ {location}" if location else ""
        label = (
            f"{num_str}{dive.get('name', 'Dive')}{loc_str} — "
            f"{start} ({depth_str}, {dur_str})"
        )

        rows.append(
            {"activity_id": activity_id, "label": label, "imported": imported}
        )
    return rows


def _get_llm_provider():
    """Build an LLMProvider from the sidebar's configured key, or None."""
    if not state.api_key or not state.provider:
        return None
    try:
        from Utilities.LLMProvider import create_provider
        return create_provider(state.provider, state.api_key, model=state.model)
    except Exception:
        return None


def ai_parsing_available() -> bool:
    return _get_llm_provider() is not None


def dive_labels() -> Dict[str, str]:
    """Map activity id -> display label for the dives currently fetched."""
    return {row["activity_id"]: row["label"] for row in dive_display_rows()}


def download_and_import(
    selected_ids: List[str],
    use_ai: bool,
    job: Optional[ImportJob] = None,
    labels: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Download selected dives' .fit files and run them through the parser.

    When ``use_ai`` is set (and an LLM key is configured), each dive's
    metadata is refined with one LLM call (Utilities.DiveEnricher).

    When ``job`` is given, each dive's start and outcome is reported to it so
    the page can show live progress. ``labels`` supplies human-readable names
    for the progress list (activity ids on their own are meaningless).
    """
    client = state.garmin_client
    provider = _get_llm_provider() if use_ai else None
    labels = labels or {}

    storage_path = Path(state.storage_folder)
    fit_files_dest = storage_path / "FitFiles"
    fit_files_dest.mkdir(parents=True, exist_ok=True)

    success_count = 0
    error_count = 0
    errors: List[Dict[str, str]] = []
    items: List[Dict[str, str]] = []

    for activity_id in selected_ids:
        name = labels.get(activity_id, f"Activity {activity_id}")
        if job is not None:
            job.start_item(name)

        try:
            # 1. Download the original .fit (named by activity id -> dedup anchor).
            fit_path = GarminConnectClient.download_fit(
                client, activity_id, str(fit_files_dest)
            )

            # 2. Pull cloud-only metadata (buddy, weight, note, location, ...).
            metadata = GarminConnectClient.get_dive_metadata(client, activity_id)

            # 2b. Optionally refine the free-text fields with an LLM.
            if provider is not None:
                from Utilities.DiveEnricher import enrich_metadata
                metadata = enrich_metadata(metadata, provider)

            # 3. Parse the .fit, enriched with the Garmin Connect metadata.
            dive = parse_garmin_dive(str(fit_path), metadata)

            # 4. Save the pickle named "<dive number> - <name>", like the app.
            stem = GarminConnectClient.dive_filename(
                metadata.get("dive_number"),
                metadata.get("activity_name"),
                activity_id,
            )
            output_path = storage_path / f"{stem}.pickle"
            with open(output_path, "wb") as f:
                pickle.dump(dive, f)

            success_count += 1
            detail = _describe_dive(dive, metadata)
            items.append({"name": name, "status": "success", "detail": detail})
            if job is not None:
                job.record(name, True, detail)
        except Exception as e:
            error_count += 1
            errors.append({"activity_id": activity_id, "error": str(e)})
            items.append({"name": name, "status": "error", "detail": str(e)})
            if job is not None:
                job.record(name, False, str(e))

    refresh_agent()

    return {
        "success_count": success_count,
        "error_count": error_count,
        "errors": errors,
        "items": items,
    }


def _describe_dive(dive, metadata: Dict[str, Any]) -> str:
    """One-line summary of an imported dive, for the per-file status list."""
    depth = max(dive.timeline.depths) if dive.timeline.depths else None
    depth_str = f"{depth:.1f}m" if depth is not None else "?"
    duration_str = format_duration(dive.basics.duration)
    location = metadata.get("location_name") or dive.location.name
    loc_str = f" @ {location}" if location else ""
    return f"{depth_str}, {duration_str}{loc_str}"
