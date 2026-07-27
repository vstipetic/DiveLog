"""
Normalise stray whitespace in the text fields of already-stored dives.

A name typed as "Maja  Orlovic" costs nothing in the Garmin app but stops
equalling "Maja Orlovic" everywhere downstream: it becomes a second entry in a
group set, a separate bar on a per-buddy chart, and a person search that finds
one dive instead of ten. The same goes for a stray tab, a trailing space, or a
non-breaking space pasted in from somewhere else.

Imports now normalise names and location names on the way in (see
``normalise_whitespace`` in ``Utilities/GarminConnectClient.py``), so this is
for data stored before that, or edited by hand. It reads nothing from Garmin -
it only tidies what is already on disk.

Every run of whitespace becomes a single space and the ends are trimmed, across:

  * ``people.buddy``, ``people.divemaster``, and every name in ``people.group``
  * ``location.name``

Dive notes (``location.description``) are prose written across several lines, so
they keep their line breaks: only stray horizontal whitespace is removed, blank
runs collapse to one, and the ends are trimmed.

Collapsing a group can merge two entries into one ("Maja  Orlovic" and
"Maja Orlovic" become the same person), which is the point; the summary says
when it happens. Nothing else about the dive is touched.

Dry run (prints what would change, writes nothing):

    python repair_dive_whitespace.py

Apply:

    python repair_dive_whitespace.py --apply
"""

import argparse
import pickle
import re
import shutil
import sys
from pathlib import Path
from typing import List, Optional

from Utilities.GarminConnectClient import normalise_whitespace


def clean(value: Optional[str]) -> Optional[str]:
    """Normalise a name-like field to one line, leaving None as None."""
    if value is None:
        return None
    return normalise_whitespace(value)


def clean_multiline(value: Optional[str]) -> Optional[str]:
    """
    Tidy a free-text field WITHOUT flattening it.

    Dive notes are written as several lines and the breaks carry the meaning -
    a gas reading, then a sighting list, then a paragraph about the site. So
    only horizontal runs are collapsed, per line; newlines survive. Runs of
    blank lines collapse to one, and the ends are trimmed.
    """
    if value is None:
        return None
    lines = [" ".join(line.split()) for line in value.splitlines()]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


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
    if not storage.is_dir():
        print(f"Storage folder not found: {storage}")
        return 1

    pickles = sorted(storage.glob("*.pickle"))
    print(f"{len(pickles)} dives in {storage}\n")

    changed: List[str] = []
    merged: List[str] = []
    unreadable: List[str] = []

    for pickle_path in pickles:
        try:
            with open(pickle_path, "rb") as fh:
                dive = pickle.load(fh)
        except Exception as e:
            print(f"  ! could not load {pickle_path.name}: {e}")
            unreadable.append(pickle_path.name)
            continue

        edits: List[str] = []
        label = pickle_path.name[:38]

        # Names and the site name are single-line values, so they collapse
        # fully. The note is prose written across several lines, so it keeps its
        # breaks and only loses stray horizontal whitespace.
        for owner, field, tidy in (
            (dive.people, "buddy", clean),
            (dive.people, "divemaster", clean),
            (dive.location, "name", clean),
            (dive.location, "description", clean_multiline),
        ):
            before = getattr(owner, field, None)
            if not isinstance(before, str):
                continue
            after = tidy(before)
            if after != before:
                setattr(owner, field, after)
                edits.append(f"{field} {before!r} -> {after!r}")

        group_before = set(dive.people.group or set())
        group_after = {clean(n) for n in group_before if isinstance(n, str)}
        group_after = {n for n in group_after if n}
        if group_after != group_before:
            dive.people.group = group_after
            gone = sorted(group_before - group_after)
            edits.append(f"group {gone} -> {sorted(group_after)}")
            # Two spellings collapsing into one entry is a merge, not a loss.
            if len(group_after) < len(group_before):
                merged.append(
                    f"{label:40} {len(group_before)} -> {len(group_after)} names"
                )

        if not edits:
            continue

        changed.append(f"{label:40} " + "; ".join(edits))

        if args.apply:
            if not args.no_backup:
                shutil.copy2(pickle_path, pickle_path.with_suffix(".pickle.bak"))
            with open(pickle_path, "wb") as fh:
                pickle.dump(dive, fh)

    verb = "tidied" if args.apply else "would tidy"
    print(f"{verb}          : {len(changed)}")
    print(f"already clean   : {len(pickles) - len(changed) - len(unreadable)}")
    if unreadable:
        print(f"unreadable      : {len(unreadable)}")

    if changed:
        print("\nchanges:")
        for line in changed:
            print(f"  {line}")

    if merged:
        print("\ngroups where two spellings collapsed into one person:")
        for line in merged:
            print(f"  {line}")

    if not args.apply and changed:
        print("\nDry run - nothing was written. Re-run with --apply to save.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
