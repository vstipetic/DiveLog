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
        normalized.append(
            {
                "activity_id": str(a.get("activityId")),
                "start_time": a.get("startTimeLocal") or a.get("startTimeGMT"),
                "name": a.get("activityName") or "Dive",
                "max_depth": a.get("maxDepth"),
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
    "already_imported",
    "download_fit",
    "GarminConnectAuthenticationError",
    "GarminConnectConnectionError",
    "GarminConnectTooManyRequestsError",
]
