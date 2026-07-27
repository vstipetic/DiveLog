"""
Backfill dive gear from Garmin Connect's web UI into existing dive pickles.

Dive gear (suit/mask/fins/...) is not available through the Garmin API - only on
the logged-in website. This CLI drives a real browser (Playwright) to read the
gear each dive used and writes it into your stored dives.

One-time setup:
    uv pip install playwright
    uv run playwright install chromium
    uv run python scrape_garmin_gear.py --login      # log into Garmin once

Then backfill:
    uv run python scrape_garmin_gear.py --storage Storage/BulkDives
    uv run python scrape_garmin_gear.py --storage Storage/BulkDives --use-ai   # LLM type mapping

It matches each downloaded .fit (named by activity id) to its dive pickle by
start time, creates/reuses gear objects in Storage/Gear/, and attaches them to
each dive's UsedGear (leaving the already-parsed weight untouched).
"""

from __future__ import annotations

import argparse
import pickle
import re
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from fitparse import FitFile

from Utilities import GarminGearScraper as Scraper
from Utilities.ClassUtils.GearClasses import (
    BCD,
    Boots,
    Fins,
    Gloves,
    GloveSize,
    Mask,
    Suit,
)

_GEAR_FOLDER = Path("Storage/Gear")


def _fit_start_time(fit_path: Path):
    """Read a .fit file's session start time (fast: one message)."""
    fit = FitFile(str(fit_path))
    for session in fit.get_messages("session"):
        return session.get_value("start_time")
    for record in fit.get_messages("record"):  # fallback
        return record.get_value("timestamp")
    return None


def _safe_stem(name: str) -> str:
    """Filesystem-safe pickle stem for a gear name."""
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", name)
    return re.sub(r"\s+", " ", stem).strip() or "gear"


def _make_gear(category: str, item: dict):
    """Instantiate the right DiveLog Gear subclass from a scraped item."""
    common = dict(
        name=item["name"],
        total_dive_time=Scraper.parse_total_minutes(item.get("total_time")),
        number_of_dives=Scraper.parse_dive_count(item.get("dives")),
        description="Imported from Garmin Connect",
        is_rental=False,
        unique_id=str(uuid4()),
    )
    if category == "suit":
        return Suit(thickness=0, size=0, **common)
    if category == "mask":
        return Mask(**common)
    if category == "gloves":
        return Gloves(thickness=0, size=GloveSize.M, **common)
    if category == "boots":
        return Boots(thickness=0, size=0, **common)
    if category == "bcd":
        return BCD(**common)
    if category == "fins":
        return Fins(**common)
    return None


def _load_or_create_gear(category: str, item: dict, registry: Dict[str, object]):
    """Return a shared gear object for this name, creating+saving it once."""
    name = item.get("name")
    if not name or not category:
        return None
    if name in registry:
        return registry[name]

    path = _GEAR_FOLDER / f"{_safe_stem(name)}.pickle"
    if path.exists():
        # Reuse gear the user (or a previous run) already created.
        with open(path, "rb") as f:
            gear = pickle.load(f)
    else:
        gear = _make_gear(category, item)
        if gear is None:
            return None
        _GEAR_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(gear, f)

    registry[name] = gear
    return gear


def backfill(storage: Path, use_ai: bool, headless: bool, limit: Optional[int]) -> None:
    """Scrape gear for every downloaded dive and attach it to the pickles."""
    fit_dir = storage / "FitFiles"
    fit_files = sorted(fit_dir.glob("*.fit"))
    if limit:
        fit_files = fit_files[:limit]
    if not fit_files:
        print(f"No .fit files in {fit_dir}")
        return

    # Map activity id -> the dive pickle, by matching start times.
    pickles = {}
    for p in storage.glob("*.pickle"):
        with open(p, "rb") as f:
            pickles[p] = pickle.load(f)
    by_start = {d.basics.start_time: p for p, d in pickles.items()}

    activity_ids = [f.stem for f in fit_files]
    aid_start = {f.stem: _fit_start_time(f) for f in fit_files}

    provider = _build_provider() if use_ai else None
    if use_ai and provider is None:
        print("--use-ai requested but no LLM key found; continuing without it.")

    def _progress(done, total, aid, items):
        names = ", ".join(f"{i['name']} [{i.get('category')}]" for i in items) or "(none)"
        print(f"[{done}/{total}] activity {aid}: {names}")

    print(f"Scraping gear for {len(activity_ids)} dives...")
    scraped = Scraper.scrape_gear(
        activity_ids, headless=headless, provider=provider, progress=_progress
    )

    registry: Dict[str, object] = {}
    attached = 0
    skipped = []
    for aid, items in scraped.items():
        start = aid_start.get(aid)
        dive_path = by_start.get(start)
        if dive_path is None:
            skipped.append(aid)
            continue
        dive = pickles[dive_path]
        for it in items:
            category = it.get("category")
            gear = _load_or_create_gear(category, it, registry)
            if gear is not None:
                setattr(dive.gear, category, gear)
        with open(dive_path, "wb") as f:
            pickle.dump(dive, f)
        if items:
            attached += 1

    print(f"\nDone. Attached gear to {attached} dives; "
          f"{len(registry)} distinct gear items in {_GEAR_FOLDER}.")
    if skipped:
        print(f"Could not match {len(skipped)} activities to a dive pickle: "
              f"{', '.join(skipped[:10])}{'...' if len(skipped) > 10 else ''}")


def _build_provider():
    """Build an LLM provider from .env keys, or None."""
    from Utilities.APIKeyDetector import detect_api_keys
    from Utilities.LLMProvider import create_provider

    keys = detect_api_keys()
    order = [("OpenAI", "openai"), ("Gemini", "gemini"),
             ("Anthropic", "claude"), ("OpenRouter", "openrouter")]
    for label, name in order:
        if keys.get(label):
            return create_provider(name, keys[label])
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", action="store_true",
                        help="Open a browser to log into Garmin (one-time).")
    parser.add_argument("--storage", default="Storage/BulkDives",
                        help="Folder with dive pickles + FitFiles/ (default: Storage/BulkDives)")
    parser.add_argument("--use-ai", action="store_true",
                        help="Use an LLM to classify unknown gear types.")
    parser.add_argument("--show-browser", action="store_true",
                        help="Run the scrape with a visible browser (debug).")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only process the first N dives (for testing).")
    args = parser.parse_args()

    if args.login:
        Scraper.login()
        return

    backfill(
        storage=Path(args.storage),
        use_ai=args.use_ai,
        headless=not args.show_browser,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
