"""
Backfill decompression data into already-stored dives.

The parser gained ndl_time / next_stop_depth / next_stop_time /
time_to_surface, and had its nitrogen-loading field name corrected, but dives
imported before that are already on disk without them. Re-importing would
recover the data and *destroy* everything the .fit file does not contain --
buddy, group, dive site names, gear, tank pressures. So this rewrites only the
timeline series on each existing pickle and leaves the rest untouched.

Pickles are matched to their .fit file by dive start time, because Garmin
imports name the pickle "<dive number> - <name>.pickle" while the .fit keeps
the numeric activity id.

Dry run (prints what would change, writes nothing):

    python backfill_deco_data.py

Apply:

    python backfill_deco_data.py --apply
"""

import argparse
import pickle
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fitparse import FitFile

from Utilities.Parsers.GarminDiveParser import parse_timeline, parse_utc_offset

# Start times can differ by a hair between the stored value and a fresh parse.
MATCH_TOLERANCE = timedelta(seconds=2)

SERIES = ("ndl_time", "next_stop_depth", "next_stop_time", "time_to_surface")


def index_fit_files(fit_folder: Path) -> Dict[Path, List[datetime]]:
    """
    Map each .fit file to the start times a stored dive could carry.

    Dives are stored in the dive site's local time, but were stored in UTC
    before that was fixed, so both readings are candidates for a match.
    """
    index: Dict[Path, List[datetime]] = {}
    for fit_path in sorted(fit_folder.glob("*.fit")):
        try:
            fit_file = FitFile(str(fit_path))
            _, utc_start = parse_timeline(fit_file)
            candidates = [utc_start]
            offset = parse_utc_offset(fit_file)
            if offset:
                candidates.append(utc_start + offset)
            index[fit_path] = candidates
        except Exception as e:
            print(f"  ! could not read {fit_path.name}: {e}")
    return index


def find_match(
    start_time: datetime, index: Dict[Path, List[datetime]]
) -> Optional[Path]:
    """Find the .fit whose start time matches, within tolerance."""
    best: Optional[Tuple[Path, timedelta]] = None
    for fit_path, fit_starts in index.items():
        for fit_start in fit_starts:
            delta = abs(fit_start - start_time)
            if delta <= MATCH_TOLERANCE and (best is None or delta < best[1]):
                best = (fit_path, delta)
    return best[0] if best else None


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
        print(f"No FitFiles folder under {storage} - nothing to backfill from.")
        return 1

    pickles = sorted(storage.glob("*.pickle"))
    print(f"{len(pickles)} dives in {storage}")
    print(f"indexing .fit files in {fit_folder} ...")
    index = index_fit_files(fit_folder)
    print(f"indexed {len(index)} .fit files\n")

    updated: List[str] = []
    unmatched: List[str] = []
    unchanged: List[str] = []

    for pickle_path in pickles:
        try:
            with open(pickle_path, "rb") as fh:
                dive = pickle.load(fh)
        except Exception as e:
            print(f"  ! could not load {pickle_path.name}: {e}")
            unmatched.append(pickle_path.name)
            continue

        fit_path = find_match(dive.basics.start_time, index)
        if fit_path is None:
            unmatched.append(pickle_path.name)
            continue

        fresh, _ = parse_timeline(FitFile(str(fit_path)))

        # Only touch the timeline series. Everything else on the dive -- people,
        # location, gear, pressures -- is left exactly as stored.
        changes: List[str] = []

        if len(fresh.depths) != len(dive.timeline.depths):
            print(
                f"  ! {pickle_path.name}: sample count differs "
                f"({len(dive.timeline.depths)} stored vs {len(fresh.depths)} "
                f"in {fit_path.name}) - skipped"
            )
            unmatched.append(pickle_path.name)
            continue

        for name in SERIES:
            new_value = getattr(fresh, name)
            if new_value and not getattr(dive.timeline, name, None):
                setattr(dive.timeline, name, new_value)
                changes.append(name)

        # The nitrogen series was previously read from a field name Garmin does
        # not use, so stored dives have all zeroes where real data exists.
        if any(fresh.n2_load) and not any(dive.timeline.n2_load):
            dive.timeline.n2_load = fresh.n2_load
            changes.append("n2_load")

        if not changes:
            unchanged.append(pickle_path.name)
            continue

        updated.append(f"{pickle_path.name}  <- {fit_path.name}  [{', '.join(changes)}]")

        if args.apply:
            if not args.no_backup:
                shutil.copy2(pickle_path, pickle_path.with_suffix(".pickle.bak"))
            with open(pickle_path, "wb") as fh:
                pickle.dump(dive, fh)

    print(f"would update : {len(updated)}" if not args.apply else f"updated      : {len(updated)}")
    print(f"already fine : {len(unchanged)}")
    print(f"unmatched    : {len(unmatched)}")

    if updated:
        print("\nchanges:")
        for line in updated[:10]:
            print(f"  {line}")
        if len(updated) > 10:
            print(f"  ... and {len(updated) - 10} more")

    if unmatched:
        print("\nno matching .fit file (left untouched):")
        for name in unmatched[:10]:
            print(f"  {name}")
        if len(unmatched) > 10:
            print(f"  ... and {len(unmatched) - 10} more")

    if not args.apply and updated:
        print("\nDry run - nothing was written. Re-run with --apply to save.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
