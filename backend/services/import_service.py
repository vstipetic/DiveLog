"""
Dive import service: storage folder management, single-dive import with
.fit preview, and bulk folder import. Wraps the untouched Utilities layer
(AddDive, GarminDiveParser).
"""

import os
import pickle
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from Utilities.AddDive import add_dive
from Utilities.Parsers.GarminDiveParser import parse_garmin_dive, get_fit_file_metadata

from backend.services.chat_service import refresh_agent
from backend.state import state


def apply_storage_folder(folder: str) -> None:
    """Set (and create if needed) the dive storage folder."""
    folder = folder.strip()
    if not folder:
        raise ValueError("Storage folder cannot be empty.")
    Path(folder).mkdir(parents=True, exist_ok=True)
    state.storage_folder = folder
    refresh_agent()


def count_dives() -> Optional[int]:
    """Number of dive pickle files in the current storage folder."""
    storage_path = Path(state.storage_folder)
    if not storage_path.exists():
        return None
    return len(list(storage_path.glob("*.pickle")))


# --- Single dive import -----------------------------------------------------

def stage_single_upload(file_storage) -> Dict[str, Any]:
    """
    Save an uploaded .fit file to a temp location and parse its preview.

    The pending upload (temp path + preview) is kept in server state until the
    user confirms the import with the metadata form, or cancels.
    """
    discard_pending_upload()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp_file:
        file_storage.save(tmp_file)
        tmp_path = tmp_file.name

    try:
        preview = get_fit_file_metadata(tmp_path)
    except Exception:
        os.unlink(tmp_path)
        raise

    pending = {
        "token": uuid.uuid4().hex,
        "path": tmp_path,
        "filename": file_storage.filename,
        "preview": preview,
    }
    state.pending_upload = pending
    return pending


def discard_pending_upload() -> None:
    """Delete the pending upload's temp file and clear it from state."""
    pending = state.pending_upload
    state.pending_upload = None
    if pending:
        try:
            os.unlink(pending["path"])
        except OSError:
            pass


def import_single_dive(
    token: str,
    location_name: str,
    location_description: Optional[str],
    buddy: str,
    divemaster: Optional[str],
    group_input: str,
    start_pressure: int,
    end_pressure: int,
    weights: float,
    gear_paths: Dict[str, Optional[str]],
) -> Dict[str, Any]:
    """
    Import the pending upload as a dive with the supplied metadata.

    Returns a details dict for display (duration, max depth, output path).
    """
    pending = state.pending_upload
    if pending is None or pending["token"] != token:
        raise ValueError("No pending upload found. Please upload the .fit file again.")

    storage_path = Path(state.storage_folder)
    storage_path.mkdir(parents=True, exist_ok=True)
    output_filename = Path(pending["filename"]).stem + ".pickle"
    output_path = storage_path / output_filename

    group = None
    if group_input.strip():
        group = set(name.strip() for name in group_input.split(",") if name.strip())

    dive = add_dive(
        fit_file_path=pending["path"],
        output_path=str(output_path),
        location_name=location_name,
        location_description=location_description if location_description else None,
        buddy=buddy,
        divemaster=divemaster if divemaster else None,
        group=group,
        start_pressure=int(start_pressure),
        end_pressure=int(end_pressure),
        suit=gear_paths.get("suit"),
        weights=float(weights),
        mask=gear_paths.get("mask"),
        gloves=gear_paths.get("gloves"),
        boots=gear_paths.get("boots"),
        bcd=gear_paths.get("bcd"),
        fins=gear_paths.get("fins"),
        copy_fit_file=True,
    )

    discard_pending_upload()
    refresh_agent()

    return {
        "duration_min": dive.basics.duration / 60,
        "max_depth": max(dive.timeline.depths) if dive.timeline.depths else None,
        "location": location_name or "Unknown",
        "output_path": str(output_path),
    }


# --- Bulk import -------------------------------------------------------------

def scan_bulk_folder(folder: str) -> Dict[str, Any]:
    """
    Scan a folder for .fit files and preview the first 10.

    Returns {"folder", "files": [names], "previews": [...], "extra_count"}.
    Raises ValueError when the folder is invalid or empty.
    """
    folder = folder.strip()
    if not folder:
        raise ValueError("Enter a folder path to scan for .fit files.")

    folder_path = Path(folder)
    if not folder_path.exists():
        raise ValueError(f"Folder does not exist: {folder}")
    if not folder_path.is_dir():
        raise ValueError(f"Path is not a folder: {folder}")

    fit_files = sorted(folder_path.glob("*.fit"))
    if not fit_files:
        raise ValueError(f"No .fit files found in: {folder}")

    previews = []
    for fit_file in fit_files[:10]:
        entry = {"name": fit_file.name, "summary": None}
        try:
            preview = get_fit_file_metadata(str(fit_file))
            auto_data = preview["auto_extracted"]
            depth = auto_data.get("max_depth", 0)
            duration = auto_data.get("duration", 0) / 60
            gas = auto_data.get("gas_type", "air")
            entry["summary"] = (
                f"Max depth: {depth:.1f}m, Duration: {duration:.0f}min, Gas: {gas}"
            )
        except Exception:
            entry["summary"] = "(preview failed)"
        previews.append(entry)

    return {
        "folder": folder,
        "total": len(fit_files),
        "previews": previews,
        "extra_count": max(0, len(fit_files) - 10),
    }


def run_bulk_import(folder: str, copy_fit_files: bool) -> Dict[str, Any]:
    """
    Import every .fit file from ``folder`` into the storage folder.

    Returns a results dict: success/error counts, GPS extraction count, and
    per-file errors.
    """
    folder_path = Path(folder)
    fit_files = sorted(folder_path.glob("*.fit"))

    storage_path = Path(state.storage_folder)
    storage_path.mkdir(parents=True, exist_ok=True)

    success_count = 0
    error_count = 0
    errors: List[Dict[str, str]] = []
    gps_extracted = 0

    for fit_file in fit_files:
        try:
            preview = get_fit_file_metadata(str(fit_file))
            auto_data = preview["auto_extracted"]
            if auto_data.get("entry_coordinates"):
                gps_extracted += 1

            output_path = storage_path / f"{fit_file.stem}.pickle"

            dive = parse_garmin_dive(str(fit_file))
            with open(output_path, "wb") as f:
                pickle.dump(dive, f)

            if copy_fit_files:
                fit_files_dest = storage_path / "FitFiles"
                fit_files_dest.mkdir(exist_ok=True)
                shutil.copy2(fit_file, fit_files_dest / fit_file.name)

            success_count += 1
        except Exception as e:
            error_count += 1
            errors.append({"filename": fit_file.name, "error": str(e)})

    refresh_agent()

    return {
        "success_count": success_count,
        "error_count": error_count,
        "gps_extracted": gps_extracted,
        "errors": errors,
    }
