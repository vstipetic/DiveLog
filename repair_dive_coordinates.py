"""
Backfill entry GPS coordinates on already-stored dives.

Imports read the entry position from the ``.fit`` file's ``start_position``,
which the watch only writes when it had a GPS lock at the moment the dive
started. Drop in before the fix lands and the field is simply absent, so the
dive was stored with no coordinates at all - about a fifth of a real dive log.

Garmin Connect holds a position for most of those dives anyway, either derived
on upload or typed in by the diver afterwards, and imports now prefer it. This
applies the same correction to dives already on disk, rewriting only
``location.entry`` and leaving every other field untouched (re-importing would
also re-run the LLM over every note, shifting locations and descriptions).

By default only dives with *no* coordinates are filled in. Pass ``--overwrite``
to also update dives whose stored position disagrees with Garmin by more than
``--tolerance`` metres - useful after correcting a position by hand in the app.
Differences below that are just the ``.fit`` parser's six-decimal rounding and
are never counted as changes.

Pickles are matched to Garmin activities through their ``.fit`` file, whose
filename is the activity id, by comparing dive start times. Dives stored in
either UTC or local time match equally well, so this is safe to run before or
after ``repair_dive_times.py``.

Needs a cached Garmin session (log in once via the Import Dives tab).

Dry run (prints what would change, writes nothing):

    python repair_dive_coordinates.py

Apply:

    python repair_dive_coordinates.py --apply
"""

import argparse
import math
import pickle
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fitparse import FitFile

from Utilities import GarminConnectClient as gc
from Utilities.Parsers.GarminDiveParser import parse_timeline, parse_utc_offset

# Start times can differ by a hair between the stored value and a fresh parse.
MATCH_TOLERANCE = timedelta(seconds=2)


def index_fit_files(fit_folder: Path) -> Dict[str, List[datetime]]:
    """
    Map each .fit file's activity id to the start times a dive could be stored
    under: the raw UTC anchor, and the local time it converts to.
    """
    index: Dict[str, List[datetime]] = {}
    for fit_path in sorted(fit_folder.glob("*.fit")):
        try:
            fit_file = FitFile(str(fit_path))
            _, utc_start = parse_timeline(fit_file)
            candidates = [utc_start]
            offset = parse_utc_offset(fit_file)
            if offset is not None:
                candidates.append(utc_start + offset)
            index[fit_path.stem] = candidates
        except Exception as e:
            print(f"  ! could not read {fit_path.name}: {e}")
    return index


def find_activity_id(
    start_time: datetime, index: Dict[str, List[datetime]]
) -> Optional[str]:
    """Find the activity whose start time matches the stored one."""
    best: Optional[Tuple[str, timedelta]] = None
    for activity_id, candidates in index.items():
        for candidate in candidates:
            delta = abs(candidate - start_time)
            if delta <= MATCH_TOLERANCE and (best is None or delta < best[1]):
                best = (activity_id, delta)
    return best[0] if best else None


def metres_apart(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Rough distance between two nearby (lat, lon) pairs, in metres."""
    lat_m = (a[0] - b[0]) * 111_320
    lon_m = (a[1] - b[1]) * 111_320 * math.cos(math.radians(a[0]))
    return math.hypot(lat_m, lon_m)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--storage",
        default="Storage/BulkDives",
        help="Folder holding the dive pickles (default: Storage/BulkDives)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write the changes. Without this, nothing is modified.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Also correct dives whose stored position disagrees with Garmin.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1.0,
        help="Metres of disagreement to ignore as rounding (default: 1.0)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip copying each pickle to <name>.pickle.bak before writing.",
    )
    args = parser.parse_args()

    storage = Path(args.storage)
    fit_folder = storage / "FitFiles"

    if not storage.is_dir():
        print(f"Storage folder not found: {storage}")
        return 1
    if not fit_folder.is_dir():
        print(f"No FitFiles folder under {storage} - needed to identify activities.")
        return 1

    client = gc.resume_session()
    if client is None:
        print("No cached Garmin session. Log in once via the Import Dives tab.")
        return 1

    pickles = sorted(storage.glob("*.pickle"))
    print(f"{len(pickles)} dives in {storage}")
    print(f"indexing .fit files in {fit_folder} ...")
    index = index_fit_files(fit_folder)
    print(f"indexed {len(index)} .fit files\n")

    filled: List[str] = []
    corrected: List[str] = []
    differs: List[str] = []
    already_ok: List[str] = []
    no_garmin_coords: List[str] = []
    unmatched: List[str] = []

    for pickle_path in pickles:
        try:
            with open(pickle_path, "rb") as fh:
                dive = pickle.load(fh)
        except Exception as e:
            print(f"  ! could not load {pickle_path.name}: {e}")
            unmatched.append(pickle_path.name)
            continue

        stored = dive.location.entry

        # Prefer the UTC anchor when the dive carries one; either matches.
        start = getattr(dive.basics, "start_time_utc", None) or dive.basics.start_time
        activity_id = find_activity_id(start, index)
        if activity_id is None:
            unmatched.append(pickle_path.name)
            continue

        try:
            metadata = gc.get_dive_metadata(client, activity_id)
        except Exception as e:
            print(f"  ! Garmin lookup failed for {pickle_path.name}: {e}")
            unmatched.append(pickle_path.name)
            continue

        coords = metadata.get("entry_coordinates")
        if coords is None:
            if stored is None:
                no_garmin_coords.append(f"{pickle_path.name[:40]:42} "
                                        f"{dive.basics.start_time.date()}")
            else:
                already_ok.append(pickle_path.name)
            continue

        if stored is None:
            dive.location.entry = coords
            filled.append(f"{pickle_path.name[:40]:42} "
                          f"{dive.basics.start_time.date()}  -> {coords}")
        else:
            drift = metres_apart(tuple(stored), coords)
            if drift <= args.tolerance:
                already_ok.append(pickle_path.name)
                continue
            line = (f"{pickle_path.name[:40]:42} {dive.basics.start_time.date()}  "
                    f"{tuple(stored)} -> {coords}  ({drift:.0f} m)")
            if not args.overwrite:
                differs.append(line)
                continue
            dive.location.entry = coords
            corrected.append(line)

        if args.apply:
            if not args.no_backup:
                shutil.copy2(pickle_path, pickle_path.with_suffix(".pickle.bak"))
            with open(pickle_path, "wb") as fh:
                pickle.dump(dive, fh)

    verb = "filled in" if args.apply else "would fill in"
    print(f"{verb} missing coordinates      : {len(filled)}")
    if args.overwrite:
        verb = "corrected" if args.apply else "would correct"
        print(f"{verb} disagreeing coordinates  : {len(corrected)}")
    print(f"already correct                : {len(already_ok)}")
    print(f"still missing (none in Garmin) : {len(no_garmin_coords)}")
    print(f"no matching .fit / activity    : {len(unmatched)}")

    for title, lines in (
        ("filled in", filled),
        ("corrected", corrected),
        ("disagree with Garmin (re-run with --overwrite to apply)", differs),
        ("no coordinates in Garmin either (left untouched)", no_garmin_coords),
    ):
        if lines:
            print(f"\n{title}:")
            for line in lines:
                print(f"  {line}")

    if unmatched:
        print("\nunmatched (left untouched):")
        for name in unmatched[:10]:
            print(f"  {name}")
        if len(unmatched) > 10:
            print(f"  ... and {len(unmatched) - 10} more")

    if not args.apply and (filled or corrected):
        print("\nDry run - nothing was written. Re-run with --apply to save.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
