"""
Garmin Connect integration for DiveLog.

Downloads original ``.fit`` files for diving activities straight from a user's
Garmin Connect account, so they no longer have to manually export them from
Garmin Express / Connect. Downloaded files feed the *existing* import pipeline
(:func:`Utilities.Parsers.GarminDiveParser.parse_garmin_dive`) unchanged.

This uses the unofficial ``garminconnect`` library (built on ``garth``), which
performs the same mobile-SSO OAuth flow as the Garmin app. It is a
reverse-engineered API with no SLA and may break if Garmin changes auth. This is
fine for personal use.

Auth flow (two-step to accommodate MFA under Streamlit, which cannot block on a
stdin callback):

    client, state = begin_login(email, password)
    if state is not None:            # account has MFA enabled
        finish_mfa(client, state, code)
    # else: already authenticated (fresh login or resumed token cache)

After a successful login the garth token is cached under :data:`TOKEN_STORE`, so
subsequent runs resume without a password or MFA code (auto-refreshed for ~1yr).
"""

from __future__ import annotations

import io
import logging
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

logger = logging.getLogger(__name__)

# Where garth caches OAuth tokens. Lives under Storage/ which is git-ignored.
TOKEN_STORE = Path("Storage/.garmin_tokens")

# garth's login() returns this sentinel as the first element when MFA is needed.
_MFA_NEEDED = "needs_mfa"


def _token_store_path() -> str:
    """Absolute, resolved path to the token cache directory (created if absent)."""
    path = TOKEN_STORE.expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _persist_tokens(client: Garmin) -> None:
    """Save the garth OAuth tokens to disk so future runs skip re-login."""
    try:
        client.client.dump(_token_store_path())
    except Exception as exc:  # pragma: no cover - persistence is best-effort
        logger.warning("Failed to persist Garmin tokens: %s", exc)


def resume_session() -> Optional[Garmin]:
    """
    Try to restore a Garmin session from cached tokens, no credentials needed.

    Returns:
        An authenticated ``Garmin`` client, or ``None`` if there is no valid
        cached token (in which case the UI should show the login form).
    """
    if not TOKEN_STORE.exists() or not any(TOKEN_STORE.iterdir()):
        return None

    client = Garmin()
    try:
        client.login(_token_store_path())
        logger.info("Resumed Garmin session from cached tokens")
        return client
    except Exception as exc:
        logger.debug("Could not resume Garmin session from cache: %s", exc)
        return None


def begin_login(
    email: str, password: str
) -> Tuple[Garmin, Optional[Dict[str, Any]]]:
    """
    Start a credential login.

    Returns:
        ``(client, mfa_state)``:
            - ``mfa_state is None`` -> login completed (tokens persisted).
            - ``mfa_state`` is a dict -> account has MFA; call
              :func:`finish_mfa` with the emailed/app code to complete login.

    Raises:
        GarminConnectAuthenticationError: bad credentials / locked account.
        GarminConnectTooManyRequestsError: rate limited (HTTP 429).
        GarminConnectConnectionError: SSO unreachable / other transport error.
    """
    if not email or not password:
        raise GarminConnectAuthenticationError("Email and password are required")

    client = Garmin(email=email, password=password, return_on_mfa=True)
    mfa_status, state = client.login(_token_store_path())

    if mfa_status == _MFA_NEEDED:
        # Auth not complete yet; caller must supply the MFA code. Do NOT persist.
        return client, state

    # Clean login (or resumed from cache) - persist tokens for next time.
    _persist_tokens(client)
    return client, None


def finish_mfa(client: Garmin, mfa_state: Dict[str, Any], code: str) -> Garmin:
    """
    Complete an MFA login started by :func:`begin_login`.

    Args:
        client: the ``Garmin`` instance returned by :func:`begin_login`.
        mfa_state: the opaque state dict returned by :func:`begin_login`.
        code: the one-time MFA code from the user's email / authenticator.

    Returns:
        The now-authenticated ``Garmin`` client (tokens persisted).
    """
    if not code or not code.strip():
        raise GarminConnectAuthenticationError("MFA code is required")

    client.resume_login(mfa_state, code.strip())
    _persist_tokens(client)
    return client


def _is_dive(activity: Dict[str, Any]) -> bool:
    """True if the activity is any kind of diving activity."""
    type_key = (activity.get("activityType") or {}).get("typeKey") or ""
    return "diving" in type_key.lower()


def list_dives(
    client: Garmin, start_date: str, end_date: str
) -> List[Dict[str, Any]]:
    """
    List diving activities between two dates (inclusive).

    Garmin's documented ``activitytype`` filter does not include diving, so we
    fetch everything in the range and filter client-side on the activity's
    ``activityType.typeKey``.

    Args:
        client: an authenticated ``Garmin`` client.
        start_date: inclusive start, ``"YYYY-MM-DD"``.
        end_date: inclusive end, ``"YYYY-MM-DD"``.

    Returns:
        Normalized dive dicts (newest first): ``activity_id``, ``start_time``,
        ``name``, ``max_depth`` (m, may be ``None``), ``duration`` (s, may be
        ``None``), ``type_key``.
    """
    activities = client.get_activities_by_date(start_date, end_date)
    dives = [a for a in activities if _is_dive(a)]

    normalized: List[Dict[str, Any]] = []
    for a in dives:
        dive_summary = a.get("summarizedDiveInfo") or {}
        normalized.append(
            {
                "activity_id": str(a.get("activityId")),
                "dive_number": a.get("diveNumber"),
                "start_time": a.get("startTimeLocal") or a.get("startTimeGMT"),
                "name": a.get("activityName") or "Dive",
                "location_name": a.get("locationName"),
                "max_depth": a.get("maxDepth") or dive_summary.get("maxDepth"),
                "duration": a.get("duration"),
                "type_key": (a.get("activityType") or {}).get("typeKey"),
            }
        )

    normalized.sort(key=lambda d: d.get("start_time") or "", reverse=True)
    logger.info(
        "Found %d diving activities between %s and %s (of %d total)",
        len(normalized),
        start_date,
        end_date,
        len(activities),
    )
    return normalized


def _as_int(value: Any) -> int:
    """Coerce a possibly-None/float pressure value to int (0 if missing)."""
    return int(value) if isinstance(value, (int, float)) else 0


# Matches a "grupa: name, name, ..." line (Croatian for "group") in a dive note,
# case-insensitive, anywhere in the (possibly multi-line) description.
_GROUP_LINE_RE = re.compile(r"^[ \t]*grupa[ \t]*:[ \t]*(.*)$", re.IGNORECASE | re.MULTILINE)

# Names within a group line are separated by commas, "&", or standalone " i "
# (Croatian "and").
_NAME_SEP_RE = re.compile(r"\s*,\s*|\s*&\s*|\s+i\s+", re.IGNORECASE)

# Garmin's default dive-activity names carry no location info; strip them so the
# remainder (if any) can be used as the dive-site name.
_DIVE_BOILERPLATE_RE = re.compile(
    r"\b(single|multi|ccr|gauge|apnea)[\s-]*gas?\s*dive\b|\bdive\b",
    re.IGNORECASE,
)


def _split_names(text: str) -> List[str]:
    """Split a free-text list of people into cleaned, de-duplicated names."""
    names = []
    for part in _NAME_SEP_RE.split(text or ""):
        name = part.strip()
        if name and name not in names:
            names.append(name)
    return names


def parse_group_from_note(description: Optional[str]) -> Tuple[List[str], Optional[str]]:
    """
    Extract a ``"grupa: ..."`` roster from a dive note.

    Args:
        description: the raw dive note (may be ``None``).

    Returns:
        ``(group_names, remaining_description)`` where ``group_names`` is the list
        of people named on the ``grupa:`` line(s), and ``remaining_description`` is
        the note with those lines removed (``None`` if nothing is left).
    """
    if not description:
        return [], description

    group_names: List[str] = []
    for match in _GROUP_LINE_RE.finditer(description):
        for name in _split_names(match.group(1)):
            if name not in group_names:
                group_names.append(name)

    remaining = _GROUP_LINE_RE.sub("", description)
    # Collapse blank lines left behind and trim.
    remaining = re.sub(r"\n{3,}", "\n\n", remaining).strip()

    return group_names, (remaining or None)


def infer_location_name(activity_name: Optional[str], garmin_location: Optional[str]) -> str:
    """
    Infer the dive-site name, preferring the dive name over Garmin's location.

    The user names dives after the site, so an informative name (anything left
    after stripping Garmin's boilerplate like "Single-Gas Dive") wins. When the
    name is pure boilerplate, fall back to Garmin's ``locationName``.

    Args:
        activity_name: the dive/activity name.
        garmin_location: Garmin Connect's ``locationName`` field.

    Returns:
        The inferred dive-site name (``""`` if nothing usable is available).
    """
    stripped = _DIVE_BOILERPLATE_RE.sub("", activity_name or "")
    stripped = re.sub(r"\s+", " ", stripped).strip(" -")
    if stripped:
        return stripped
    return (garmin_location or "").strip()


def get_dive_metadata(client: Garmin, activity_id: str) -> Dict[str, Any]:
    """
    Fetch per-dive metadata from the Garmin Connect activity record.

    Most dive metadata does NOT live in the ``.fit`` file - it is entered in the
    Garmin app and stored in the cloud. This calls ``get_activity`` (one request)
    and returns a dict whose keys line up with what
    :func:`Utilities.Parsers.GarminDiveParser.parse_garmin_dive` accepts as its
    ``metadata`` argument, plus a few display-only fields.

    Populated in practice: ``dive_number``, ``activity_name``, ``location_name``
    (inferred from the dive name, see :func:`infer_location_name`), ``buddy``
    (Garmin's buddy field only - empty when the user designated nobody) and
    ``group`` (the buddy field plus any ``"grupa: ..."`` note line, see
    :func:`parse_group_from_note`), ``weights`` (weight belt, kg),
    ``location_description`` (the dive *Note* minus structured lines), and
    ``entry_type`` (Shore/Boat). The raw ``garmin_location_name``,
    ``raw_description`` and ``raw_buddy`` are also returned for optional LLM
    enrichment and future tooling.

    Rarely populated (Garmin stores the field but users seldom fill it): tank
    ``start_pressure`` / ``end_pressure`` - divers often type these into the Note
    instead. Dive gear (suit/mask/etc.) is not exposed for dive activities, so it
    stays ``None`` and must be added manually.

    Args:
        client: an authenticated ``Garmin`` client.
        activity_id: the Garmin activity id.

    Returns:
        Metadata dict (all keys always present; values may be ``None``/empty).
    """
    act = client.get_activity(activity_id)
    dive_info = act.get("diveInfo") or {}
    metadata_dto = act.get("metadataDTO") or {}
    gases = dive_info.get("diveGases") or []
    first_gas = gases[0] if gases else {}
    activity_name = act.get("activityName")
    raw_description = act.get("description")  # the app's "Note" field

    # The BUDDY comes from Garmin's own buddy field and nowhere else. It is the
    # only place the user designates a buddy, so it is authoritative: when it is
    # empty there was no buddy (e.g. dives the user led), and a name pulled from
    # the note's group roster must never be promoted into it.
    #
    # Garmin stores buddies in one free-text field, often comma-separated. The
    # first is the primary buddy; all of them belong to the group as well.
    buddy_names = _split_names(dive_info.get("buddy") or "")
    primary_buddy = buddy_names[0] if buddy_names else ""

    # Pull a "grupa: ..." roster out of the note and strip it from the text.
    note_group, remaining_note = parse_group_from_note(raw_description)

    # The GROUP is everyone on the dive: the buddy field plus the grupa line.
    # Buddy and group stay separate fields, but a designated buddy is always in
    # the group too, so a person search never has to consult both.
    group = set(buddy_names) | set(note_group)

    return {
        # --- accepted by parse_garmin_dive(metadata=...) ---
        "location_name": infer_location_name(activity_name, act.get("locationName")),
        "location_description": remaining_note,
        "buddy": primary_buddy,
        "group": group,
        # Names from the authoritative buddy field, kept so later passes (the
        # optional LLM enrichment) can widen the group without overwriting them.
        "buddy_names": buddy_names,
        "weights": dive_info.get("weight") or 0.0,
        "start_pressure": _as_int(first_gas.get("tankStartingPressure")),
        "end_pressure": _as_int(first_gas.get("tankEndingPressure")),
        "entry_type": dive_info.get("entryType"),
        # --- display / naming only ---
        "dive_number": metadata_dto.get("diveNumber"),
        "activity_name": activity_name,
        # --- raw fields kept for optional LLM enrichment / future tools ---
        "garmin_location_name": act.get("locationName"),
        "raw_description": raw_description,
        "raw_buddy": dive_info.get("buddy"),
    }


def dive_filename(
    dive_number: Optional[int], activity_name: Optional[str], activity_id: str
) -> str:
    """
    Build a filesystem-safe pickle stem like ``"24 - Single-Gas Dive"``.

    Mirrors how dives are labelled in the Garmin app (``<dive number> <name>``).
    Falls back to the activity id when there is no dive number, guaranteeing a
    unique, collision-free filename.

    Args:
        dive_number: Garmin's sequential dive number (may be ``None``).
        activity_name: the activity/dive name (may be ``None``).
        activity_id: unique Garmin activity id, used as a fallback.

    Returns:
        A sanitized filename stem (no extension), safe on Windows and POSIX.
    """
    # Sanitize the name first: drop characters invalid in Windows filenames,
    # collapse whitespace, and trim trailing dots/spaces.
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", activity_name or "")
    name = re.sub(r"\s+", " ", name).strip().rstrip(".").strip()

    if dive_number is not None and name:
        return f"{dive_number} - {name}"
    if dive_number is not None:
        return str(dive_number)
    if name:
        return name
    # No number and no usable name -> fall back to the unique activity id.
    return str(activity_id)


def already_imported(activity_id: str, storage_folder: str) -> bool:
    """
    True if this Garmin activity has already been imported into ``storage_folder``.

    Dedup key is the activity id, which we use as the ``.fit``/pickle filename,
    so an import is detectable without any extra bookkeeping.
    """
    storage = Path(storage_folder)
    return (
        (storage / f"{activity_id}.pickle").exists()
        or (storage / "FitFiles" / f"{activity_id}.fit").exists()
    )


def download_fit(client: Garmin, activity_id: str, dest_dir: str) -> Path:
    """
    Download an activity's original ``.fit`` file into ``dest_dir``.

    Garmin returns the ORIGINAL export as a ZIP of raw bytes containing the
    ``.fit``; we extract it and name it ``{activity_id}.fit`` so it doubles as
    the dedup key (see :func:`already_imported`).

    Args:
        client: an authenticated ``Garmin`` client.
        activity_id: the Garmin activity id (as returned by :func:`list_dives`).
        dest_dir: directory to write the ``.fit`` into (created if absent).

    Returns:
        Path to the written ``.fit`` file.

    Raises:
        GarminConnectInvalidFileFormatError-style / ValueError: if the download
        does not contain a ``.fit`` member.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    data = client.download_activity(
        activity_id, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL
    )

    out_path = dest / f"{activity_id}.fit"

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        fit_members = [n for n in zf.namelist() if n.lower().endswith(".fit")]
        if not fit_members:
            raise ValueError(
                f"No .fit file in Garmin download for activity {activity_id} "
                f"(members: {zf.namelist()})"
            )
        with zf.open(fit_members[0]) as src, open(out_path, "wb") as dst:
            dst.write(src.read())

    logger.info("Downloaded activity %s -> %s", activity_id, out_path)
    return out_path


__all__ = [
    "TOKEN_STORE",
    "resume_session",
    "begin_login",
    "finish_mfa",
    "list_dives",
    "get_dive_metadata",
    "parse_group_from_note",
    "infer_location_name",
    "dive_filename",
    "already_imported",
    "download_fit",
    "GarminConnectAuthenticationError",
    "GarminConnectConnectionError",
    "GarminConnectTooManyRequestsError",
]
