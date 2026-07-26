"""
Repair the dive buddy on already-stored dives.

Imports used to let the optional LLM enrichment pass decide the buddy, picking
whichever name it happened to list first out of the merged buddy field + note
roster. That silently replaced the real buddy with a group member, and invented
a buddy for dives that never had one (the ones the user led). The buddy now
comes from Garmin Connect's own buddy field and nothing else.

Re-importing would fix it but would also re-run the LLM over every note, so
locations and descriptions would shift too. This instead rewrites only
``people.buddy`` on each existing pickle, re-reading the authoritative field
from Garmin Connect:

  * buddy field filled  -> its first name becomes the buddy, and is added to the
    group if missing
  * buddy field empty   -> the buddy is cleared

Nobody is ever removed from the group: it may legitimately contain people the
enrichment pass found in a freeform note.

Pickles are matched to Garmin activities by dive number, which Garmin imports
put at the front of the filename ("<dive number> - <name>.pickle").

Needs a cached Garmin session (log in once via the Import Dives tab).

Dry run (prints what would change, writes nothing):

    python repair_dive_buddies.py

Apply:

    python repair_dive_buddies.py --apply
"""

import argparse
import pickle
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from Utilities import GarminConnectClient as gc

# Garmin imports name pickles "<dive number> - <name>.pickle".
DIVE_NUMBER_RE = re.compile(r"^(\d+)\s*-\s*")


def dive_number_of(pickle_path: Path) -> Optional[int]:
    """Extract the Garmin dive number a pickle was named after."""
    match = DIVE_NUMBER_RE.match(pickle_path.stem)
    return int(match.group(1)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--storage",
        default="Storage/BulkDives",
        help="Folder holding the dive pickles (default: Storage/BulkDives)",
    )
    parser.add_argument(
        "--start-date",
        default="2000-01-01",
        help="Earliest date to list activities from (default: 2000-01-01)",
    )
    # Garmin's activity search returns nothing at all for a far-future end date,
    # so this has to stay within reach of the calendar.
    parser.add_argument(
        "--end-date",
        default=date.today().isoformat(),
        help="Latest date to list activities to (default: today)",
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
    if not storage.is_dir():
        print(f"Storage folder not found: {storage}")
        return 1

    client = gc.resume_session()
    if client is None:
        print(
            "No cached Garmin session. Log in once via the Import Dives tab, "
            "then re-run this script."
        )
        return 1

    pickles = sorted(storage.glob("*.pickle"))
    print(f"{len(pickles)} dives in {storage}")

    listed = gc.list_dives(client, args.start_date, args.end_date)
    by_number: Dict[int, str] = {}
    for row in listed:
        number = row.get("dive_number")
        if number is not None:
            by_number[int(number)] = row["activity_id"]
    print(f"{len(listed)} dives listed from Garmin ({len(by_number)} numbered)\n")

    fixed: List[str] = []
    cleared: List[str] = []
    unchanged: List[str] = []
    unmatched: List[str] = []

    for pickle_path in pickles:
        number = dive_number_of(pickle_path)
        activity_id = by_number.get(number) if number is not None else None
        if activity_id is None:
            unmatched.append(pickle_path.name)
            continue

        try:
            with open(pickle_path, "rb") as fh:
                dive = pickle.load(fh)
        except Exception as e:
            print(f"  ! could not load {pickle_path.name}: {e}")
            unmatched.append(pickle_path.name)
            continue

        try:
            metadata = gc.get_dive_metadata(client, activity_id)
        except Exception as e:
            print(f"  ! could not fetch metadata for {pickle_path.name}: {e}")
            unmatched.append(pickle_path.name)
            continue

        new_buddy = (metadata.get("buddy") or "").strip()
        old_buddy = (dive.people.buddy or "").strip()

        # The group only ever grows: it may hold people the enrichment pass
        # found in a freeform note, which Garmin's fields do not know about.
        group = set(dive.people.group or set())
        group_before = set(group)
        if new_buddy:
            group.add(new_buddy)

        if new_buddy == old_buddy and group == group_before:
            unchanged.append(pickle_path.name)
            continue

        line = f"{pickle_path.name[:40]:42} {old_buddy!r:22} -> {new_buddy!r}"
        if group - group_before:
            line += f"   +group {sorted(group - group_before)}"
        (cleared if new_buddy == "" else fixed).append(line)

        dive.people.buddy = new_buddy
        dive.people.group = group

        if args.apply:
            if not args.no_backup:
                shutil.copy2(pickle_path, pickle_path.with_suffix(".pickle.bak"))
            with open(pickle_path, "wb") as fh:
                pickle.dump(dive, fh)

    verb = "corrected" if args.apply else "would correct"
    print(f"{verb} to the buddy Garmin recorded : {len(fixed)}")
    print(f"invented buddy removed (had none)     : {len(cleared)}")
    print(f"already correct                       : {len(unchanged)}")
    print(f"not found in Garmin (left untouched)  : {len(unmatched)}")

    for title, rows in (("corrected", fixed), ("cleared", cleared)):
        if rows:
            print(f"\n{title}:")
            for line in rows:
                print(f"  {line}")

    if unmatched:
        print("\nno matching Garmin activity (left untouched):")
        for name in unmatched[:10]:
            print(f"  {name}")
        if len(unmatched) > 10:
            print(f"  ... and {len(unmatched) - 10} more")

    if not args.apply and (fixed or cleared):
        print("\nDry run - nothing was written. Re-run with --apply to save.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
