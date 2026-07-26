"""
Convert already-stored dive times from UTC to the dive site's local time.

Every timestamp in a .fit file is UTC, and the parser stored it verbatim, so a
dive logged at 18:16 in Egypt sat in the pickle as 16:16. The parser now shifts
times into local time using the offset the .fit file itself records; this does
the same to dives already on disk.

Only ``basics.start_time`` and ``basics.end_time`` are rewritten (plus the new
``basics.utc_offset_hours``). The timeline is a series of elapsed seconds, so it
is unaffected. Everything else on the dive is left untouched.

Pickles are matched to their .fit file by dive start time, so this is safe to
re-run: a dive that already holds local time no longer matches its file's UTC
anchor, and dives carrying an offset are skipped outright.

Dry run (prints what would change, writes nothing):

    python repair_dive_times.py

Apply:

    python repair_dive_times.py --apply
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


def index_fit_files(fit_folder: Path) -> Dict[Path, Tuple[datetime, Optional[timedelta]]]:
    """Map each .fit file to its UTC start time and the local offset it records."""
    index: Dict[Path, Tuple[datetime, Optional[timedelta]]] = {}
    for fit_path in sorted(fit_folder.glob("*.fit")):
        try:
            fit_file = FitFile(str(fit_path))
            _, utc_start = parse_timeline(fit_file)
            index[fit_path] = (utc_start, parse_utc_offset(fit_file))
        except Exception as e:
            print(f"  ! could not read {fit_path.name}: {e}")
    return index


def find_match(
    start_time: datetime,
    index: Dict[Path, Tuple[datetime, Optional[timedelta]]],
) -> Optional[Path]:
    """Find the .fit whose UTC start time matches the stored (still-UTC) time."""
    best: Optional[Tuple[Path, timedelta]] = None
    for fit_path, (utc_start, _) in index.items():
        delta = abs(utc_start - start_time)
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
        print(f"No FitFiles folder under {storage} - the offset lives in the .fit.")
        return 1

    pickles = sorted(storage.glob("*.pickle"))
    print(f"{len(pickles)} dives in {storage}")
    print(f"indexing .fit files in {fit_folder} ...")
    index = index_fit_files(fit_folder)
    print(f"indexed {len(index)} .fit files\n")

    updated: List[str] = []
    already_local: List[str] = []
    no_offset: List[str] = []
    unmatched: List[str] = []

    for pickle_path in pickles:
        try:
            with open(pickle_path, "rb") as fh:
                dive = pickle.load(fh)
        except Exception as e:
            print(f"  ! could not load {pickle_path.name}: {e}")
            unmatched.append(pickle_path.name)
            continue

        # A dive that already carries an offset has been converted.
        if getattr(dive.basics, "utc_offset_hours", None) is not None:
            already_local.append(pickle_path.name)
            continue

        fit_path = find_match(dive.basics.start_time, index)
        if fit_path is None:
            unmatched.append(pickle_path.name)
            continue

        _, offset = index[fit_path]
        if offset is None:
            no_offset.append(pickle_path.name)
            continue

        old_start = dive.basics.start_time
        dive.basics.start_time = old_start + offset
        dive.basics.end_time = dive.basics.end_time + offset
        dive.basics.utc_offset_hours = offset.total_seconds() / 3600

        updated.append(
            f"{pickle_path.name[:38]:40} {old_start} -> {dive.basics.start_time}  "
            f"({dive.basics.utc_offset_hours:+.0f}h)"
        )

        if args.apply:
            if not args.no_backup:
                shutil.copy2(pickle_path, pickle_path.with_suffix(".pickle.bak"))
            with open(pickle_path, "wb") as fh:
                pickle.dump(dive, fh)

    verb = "converted" if args.apply else "would convert"
    print(f"{verb} to local time            : {len(updated)}")
    print(f"already local (has an offset)  : {len(already_local)}")
    print(f"no offset in the .fit          : {len(no_offset)}")
    print(f"no matching .fit               : {len(unmatched)}")

    if updated:
        print("\nchanges:")
        for line in updated:
            print(f"  {line}")

    for title, names in (("no offset recorded", no_offset), ("unmatched", unmatched)):
        if names:
            print(f"\n{title} (left untouched):")
            for name in names[:10]:
                print(f"  {name}")
            if len(names) > 10:
                print(f"  ... and {len(names) - 10} more")

    if not args.apply and updated:
        print("\nDry run - nothing was written. Re-run with --apply to save.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
