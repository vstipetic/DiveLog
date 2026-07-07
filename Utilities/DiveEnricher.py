"""
Optional LLM enrichment of Garmin dive metadata.

Garmin dive names and notes are free-form (and often in Croatian): the dive-site
name may be embedded in the activity name, the buddy roster may be split between
the buddy field and a ``grupa:`` note line, and the note may mix structured info
with prose. The deterministic parsing in
:mod:`Utilities.GarminConnectClient` handles the common conventions; this module
optionally hands the same raw fields to an LLM for a smarter pass.

It is entirely optional: if no LLM provider is configured, or the call fails, the
caller keeps the deterministic metadata unchanged.

Usage:
    from Utilities.LLMProvider import create_provider
    provider = create_provider("gemini", api_key)
    metadata = enrich_metadata(metadata, provider)   # metadata from get_dive_metadata()
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from Utilities.LLMProvider import LLMProvider, SystemMessage, UserMessage

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """You extract structured metadata from scuba dive log entries.
The text comes from Garmin Connect and is often in Croatian.

You are given a dive's name, Garmin location field, buddy field, and a free-text
note. Return STRICT JSON (no markdown, no commentary) with exactly these keys:

  "location":    string | null  - the dive SITE name. Divers usually name the
                                   dive after the site. Prefer a specific site
                                   from the name/note over a broad town/area.
                                   Drop generic Garmin words like "Single-Gas
                                   Dive". null if genuinely unknown.
  "buddies":     string[]        - EVERY person who was on the dive, from the
                                   buddy field and any "grupa:" line in the note.
                                   Deduplicate. Empty list if none.
  "cleaned_note": string | null  - the note with structured bits removed (the
                                   "grupa:" roster, and anything that just repeats
                                   the location). Keep genuine remarks. null if
                                   nothing meaningful remains.

Do not invent people or places. Only use what appears in the input."""


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` / ``` ... ``` fences an LLM may wrap around JSON."""
    text = text.strip()
    if text.startswith("```"):
        # Drop the first fence line and any trailing fence.
        text = text.split("\n", 1)[-1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def enrich_metadata(
    metadata: Dict[str, Any], provider: LLMProvider
) -> Dict[str, Any]:
    """
    Refine a dive-metadata dict in place using an LLM.

    Reads the raw fields produced by
    :func:`Utilities.GarminConnectClient.get_dive_metadata`
    (``activity_name``, ``garmin_location_name``, ``raw_buddy``,
    ``raw_description``) and overrides ``location_name``, ``buddy``, ``group`` and
    ``location_description`` with the LLM's interpretation.

    On any error (no response, bad JSON, provider failure) the input metadata is
    returned unchanged, so this is always safe to call.

    Args:
        metadata: the dict from ``get_dive_metadata``.
        provider: an ``LLMProvider`` (from ``create_provider``).

    Returns:
        The same dict, possibly with refined fields.
    """
    user_payload = {
        "name": metadata.get("activity_name"),
        "location_field": metadata.get("garmin_location_name"),
        "buddy_field": metadata.get("raw_buddy"),
        "note": metadata.get("raw_description"),
    }

    try:
        response = provider.chat(
            [
                SystemMessage(_SYSTEM_PROMPT),
                UserMessage(json.dumps(user_payload, ensure_ascii=False)),
            ]
        )
        parsed = json.loads(_strip_code_fences(response.content))
    except Exception as exc:
        logger.warning(
            "LLM enrichment failed for dive %s (%s); keeping parsed metadata",
            metadata.get("dive_number") or metadata.get("activity_name"),
            exc,
        )
        return metadata

    location = parsed.get("location")
    if isinstance(location, str) and location.strip():
        metadata["location_name"] = location.strip()

    buddies = parsed.get("buddies")
    if isinstance(buddies, list):
        clean = [b.strip() for b in buddies if isinstance(b, str) and b.strip()]
        if clean:
            metadata["buddy"] = clean[0]
            metadata["group"] = set(clean)

    cleaned_note = parsed.get("cleaned_note")
    # Accept an explicit null (note fully consumed) or a non-empty string.
    if cleaned_note is None or isinstance(cleaned_note, str):
        metadata["location_description"] = (
            cleaned_note.strip() if isinstance(cleaned_note, str) and cleaned_note.strip()
            else None
        )

    return metadata


__all__ = ["enrich_metadata"]
