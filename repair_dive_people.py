"""
Re-sync the buddy and the group on already-stored dives from Garmin Connect.

Supersedes ``repair_dive_buddies.py``, which only ever rewrote the buddy and
could add people to a group but never remove any. That rule protected names the
LLM enrichment pass found in freeform notes, but it breaks down once the Garmin
records themselves are curated: the stored group holds the model's guesses at
names ("Maksim", "Vito", "Darko K."), Garmin holds the real ones ("Maksim
Mazuryn", "Vitomir Seba", "Darko Kovacic"), and refusing to drop the guesses
leaves both - which is exactly what splits one diver's statistics in two.

So by default the group is MIRRORED from Garmin: whatever the buddy field and
the note's ``grupa:`` line say is what the dive ends up with. Removals are
reported in two classes so a dry run is readable:

  * name upgrades - the dropped name's parts are all prefixes of names Garmin
    kept ("Vito" -> "Vitomir Seba", "Demi Helena" -> "Demi Jurela" +
    "Helena Mikulic"). Nothing is lost; a partial name is replaced by a full one.
  * genuine drops - the dropped name matches nobody Garmin lists. These are
    people only the LLM ever knew about, from a note with no ``grupa:`` line.

Pass ``--keep-unmatched`` to hold on to the genuine drops while still taking
every upgrade, or ``--union`` for the old never-remove behaviour.

Only ``people.buddy`` and ``people.group`` are touched. Re-importing would fix
these too but would re-run the LLM over every note, shifting locations and
descriptions, and would discard gear and pressures added by hand.

Pickles are matched to Garmin activities by dive number, which Garmin imports
put at the front of the filename ("<dive number> - <name>.pickle").

Needs a cached Garmin session (log in once via the Import Dives tab).

Dry run (prints what would change, writes nothing):

    python repair_dive_people.py

Apply:

    python repair_dive_people.py --apply
"""

import argparse
import pickle
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from Utilities import GarminConnectClient as gc

# Garmin imports name pickles "<dive number> - <name>.pickle".
DIVE_NUMBER_RE = re.compile(r"^(\d+)\s*-\s*")

# Name parts, ignoring the abbreviating full stop in "Darko K.".
_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def dive_number_of(pickle_path: Path) -> Optional[int]:
    """Extract the Garmin dive number a pickle was named after."""
    match = DIVE_NUMBER_RE.match(pickle_path.stem)
    return int(match.group(1)) if match else None


def tokens(name: str) -> List[str]:
    """Split a name into lowercased alphabetic parts."""
    return [t.lower() for t in _TOKEN_RE.findall(name)]


# A nickname is not always a prefix of the formal name ("Kreso" for
# "Kresismir"), so sharing this many leading characters also counts as the same
# person. Four is enough to keep genuinely different names apart - "Darko" and
# "Dario" share only three, as do "Marko" and "Marija".
NICKNAME_PREFIX = 4


def _same_person(part: str, kept_token: str) -> bool:
    """True if a dropped name part and a kept one plainly denote one person."""
    if kept_token.startswith(part):
        return True
    shared = 0
    for a, b in zip(part, kept_token):
        if a != b:
            break
        shared += 1
    return shared >= NICKNAME_PREFIX


def is_upgraded_by(dropped: str, kept: Set[str]) -> bool:
    """
    True if every part of ``dropped`` is accounted for by a name in ``kept``.

    "Vito" is upgraded by "Vitomir Seba"; "Darko K." by "Darko Kovacic". A name
    the model welded together from two people ("Demi Helena") counts too, since
    its parts are covered by "Demi Jurela" and "Helena Mikulic" between them -
    nobody is lost, they are just told apart properly now.

    This only decides how a removal is *reported*, and which names
    ``--keep-unmatched`` holds on to. Mirror mode drops them either way.
    """
    dropped_tokens = tokens(dropped)
    if not dropped_tokens:
        return True
    kept_tokens = [t for name in kept for t in tokens(name)]
    return all(
        any(_same_person(part, k) for k in kept_tokens) for part in dropped_tokens
    )


def resolve_group(
    stored: Set[str], garmin: Set[str], mode: str
) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
    """
    Work out the new group.

    Returns ``(new_group, added, upgrades, genuine_drops)``, where the two drop
    sets describe what leaving ``stored`` behind would cost.
    """
    added = garmin - stored
    removed = stored - garmin
    upgrades = {n for n in removed if is_upgraded_by(n, garmin)}
    genuine = removed - upgrades

    if mode == "union":
        return stored | garmin, added, set(), set()
    if mode == "keep-unmatched":
        return garmin | genuine, added, upgrades, set()
    return set(garmin), added, upgrades, genuine


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
        "--keep-unmatched",
        action="store_true",
        help="Take every name upgrade, but keep people Garmin does not list.",
    )
    parser.add_argument(
        "--union",
        action="store_true",
        help="Never remove anyone from a group (the old behaviour).",
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

    if args.union and args.keep_unmatched:
        print("--union and --keep-unmatched are mutually exclusive.")
        return 1
    mode = "union" if args.union else "keep-unmatched" if args.keep_unmatched else "mirror"

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
    print(f"{len(pickles)} dives in {storage}   (group mode: {mode})")

    listed = gc.list_dives(client, args.start_date, args.end_date)
    by_number: Dict[int, str] = {}
    for row in listed:
        number = row.get("dive_number")
        if number is not None:
            by_number[int(number)] = row["activity_id"]
    print(f"{len(listed)} dives listed from Garmin ({len(by_number)} numbered)\n")

    changed: List[str] = []
    upgrade_notes: List[str] = []
    drop_notes: List[str] = []
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

        old_buddy = (dive.people.buddy or "").strip()
        new_buddy = (metadata.get("buddy") or "").strip()

        stored_group = {n.strip() for n in (dive.people.group or set()) if n.strip()}
        garmin_group = {n.strip() for n in (metadata.get("group") or set()) if n.strip()}

        new_group, added, upgrades, drops = resolve_group(
            stored_group, garmin_group, mode
        )

        # A designated buddy is always part of the group.
        if new_buddy:
            new_group = new_group | {new_buddy}

        if new_buddy == old_buddy and new_group == stored_group:
            unchanged.append(pickle_path.name)
            continue

        label = pickle_path.name[:38]
        line = f"{label:40}"
        if new_buddy != old_buddy:
            line += f" buddy {old_buddy!r} -> {new_buddy!r}"
        if added:
            line += f"  +{sorted(added)}"
        if upgrades:
            line += f"  -{sorted(upgrades)}"
        changed.append(line)

        if upgrades:
            upgrade_notes.append(f"{label:40} {sorted(upgrades)} -> covered by "
                                 f"{sorted(garmin_group)}")
        if drops:
            drop_notes.append(f"{label:40} {sorted(drops)}  "
                              f"(garmin lists {sorted(garmin_group) or 'nobody'})")

        dive.people.buddy = new_buddy
        dive.people.group = new_group

        if args.apply:
            if not args.no_backup:
                shutil.copy2(pickle_path, pickle_path.with_suffix(".pickle.bak"))
            with open(pickle_path, "wb") as fh:
                pickle.dump(dive, fh)

    verb = "updated" if args.apply else "would update"
    print(f"{verb} buddy/group : {len(changed)}")
    print(f"already correct       : {len(unchanged)}")
    print(f"not found in Garmin   : {len(unmatched)}")

    if changed:
        print("\nchanges:")
        for line in changed:
            print(f"  {line}")

    if upgrade_notes:
        print(f"\nname upgrades ({len(upgrade_notes)} dives) - partial names "
              f"replaced by the full ones, nothing lost:")
        for line in upgrade_notes:
            print(f"  {line}")

    if drop_notes:
        title = "people Garmin does not list"
        title += " (KEPT, --keep-unmatched)" if mode == "keep-unmatched" else " (DROPPED)"
        print(f"\n{title} - only the LLM ever knew about these:")
        for line in drop_notes:
            print(f"  {line}")
        if mode == "mirror":
            print("  re-run with --keep-unmatched to hold on to them.")

    if unmatched:
        print("\nno matching Garmin activity (left untouched):")
        for name in unmatched[:10]:
            print(f"  {name}")
        if len(unmatched) > 10:
            print(f"  ... and {len(unmatched) - 10} more")

    if not args.apply and changed:
        print("\nDry run - nothing was written. Re-run with --apply to save.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
