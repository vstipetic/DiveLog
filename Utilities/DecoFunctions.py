"""
Decompression accessors and predicates for dive data.

Everything here returns ``None`` for "not known" rather than a falsy number,
because two different populations of dive genuinely have no decompression data
and must not be reported as "did not enter deco":

* shallow dives, where the computer records no NDL at all;
* dives stored before these fields were parsed, whose pickles simply lack the
  attributes.

The second case is why every read goes through :func:`_series`, which uses
``getattr`` with a default: ``DiveTimeline`` is a non-slots attrs class, so an
older pickle unpickles happily but raises ``AttributeError`` on a field it was
never saved with. Callers should treat ``None`` as "unknown" and say so.

Units follow the .fit file: seconds for NDL, stop time and time-to-surface;
meters for the ceiling.
"""

from typing import List, Optional

from Utilities.ClassUtils.DiveClass import Dive

# Series that exist on DiveTimeline only for dives parsed after decompression
# support was added.
DECO_SERIES = ("ndl_time", "next_stop_depth", "next_stop_time", "time_to_surface")


def _series(dive: Dive, name: str) -> Optional[List[Optional[float]]]:
    """Read a timeline series, tolerating pickles saved before it existed."""
    values = getattr(dive.timeline, name, None)
    if not values:
        return None
    return values


def _present(values: Optional[List[Optional[float]]]) -> List[float]:
    """Drop the None entries from a series."""
    if not values:
        return []
    return [v for v in values if v is not None]


# =============================================================================
# AVAILABILITY
# =============================================================================

def has_deco_data(dive: Dive) -> bool:
    """True if the dive carries any decompression series at all."""
    return any(_series(dive, name) for name in DECO_SERIES)


def has_ndl_data(dive: Dive) -> bool:
    """True if the dive recorded no-decompression-limit samples."""
    return bool(_present(_series(dive, "ndl_time")))


# =============================================================================
# SCALAR SUMMARIES (None == unknown)
# =============================================================================

def min_ndl_seconds(dive: Dive) -> Optional[float]:
    """Lowest no-decompression limit reached, in seconds.

    0 means the dive ran out of no-stop time and incurred an obligation.
    """
    values = _present(_series(dive, "ndl_time"))
    return min(values) if values else None


def max_ceiling_meters(dive: Dive) -> Optional[float]:
    """Deepest decompression ceiling reached, in meters (0 == never any)."""
    values = _present(_series(dive, "next_stop_depth"))
    return max(values) if values else None


def max_stop_seconds(dive: Dive) -> Optional[float]:
    """Longest required decompression stop, in seconds (0 == never any)."""
    values = _present(_series(dive, "next_stop_time"))
    return max(values) if values else None


def max_time_to_surface_seconds(dive: Dive) -> Optional[float]:
    """Greatest total time-to-surface reached, in seconds."""
    values = _present(_series(dive, "time_to_surface"))
    return max(values) if values else None


def deco_duration_seconds(dive: Dive) -> Optional[float]:
    """
    How long the dive was under a decompression obligation, in seconds.

    Measured from the timeline itself -- the span of samples carrying a ceiling
    -- rather than from the stop time, which is the *required* stop at a moment
    and not a duration spent in deco.
    """
    ceilings = _series(dive, "next_stop_depth")
    if not ceilings:
        return None

    timestamps = dive.timeline.timestamps
    if not timestamps or len(timestamps) != len(ceilings):
        # Fall back to counting samples if the series are misaligned.
        return float(sum(1 for c in ceilings if c))

    total = 0.0
    for i, ceiling in enumerate(ceilings):
        if not ceiling:
            continue
        if i + 1 < len(timestamps):
            total += timestamps[i + 1] - timestamps[i]
    return total


# =============================================================================
# PREDICATES (None == unknown, so callers can report it separately)
# =============================================================================

def dive_entered_deco(dive: Dive) -> Optional[bool]:
    """
    Whether the dive incurred a decompression obligation.

    A ceiling appearing is the authoritative signal. NDL reaching zero is used
    as a fallback for computers that report NDL but no ceiling; on this log the
    two agree on every sample where a stop was required.

    Returns:
        True / False, or None when the dive has no decompression data
    """
    ceiling = max_ceiling_meters(dive)
    if ceiling is not None:
        return ceiling > 0

    ndl = min_ndl_seconds(dive)
    if ndl is not None:
        return ndl <= 0

    return None


def dive_deco_stop_at_least(dive: Dive, seconds: float) -> Optional[bool]:
    """Whether the dive required a decompression stop of at least ``seconds``."""
    stop = max_stop_seconds(dive)
    if stop is None:
        return None
    return stop >= seconds


def dive_ndl_fell_below(dive: Dive, seconds: float) -> Optional[bool]:
    """
    Whether the no-decompression limit ever dropped to ``seconds`` or less.

    This is the "how close did I get" question: ``seconds=300`` answers
    "on how many dives did I hit 5 minutes to decompression".
    """
    ndl = min_ndl_seconds(dive)
    if ndl is None:
        return None
    return ndl <= seconds


def describe_deco(dive: Dive) -> str:
    """One-line human-readable decompression summary, for tool output."""
    if not has_deco_data(dive):
        return "no decompression data recorded"

    entered = dive_entered_deco(dive)
    parts: List[str] = []

    ndl = min_ndl_seconds(dive)
    if ndl is not None:
        parts.append(f"min NDL {ndl / 60:.0f}min" if ndl else "NDL reached 0")

    if entered:
        ceiling = max_ceiling_meters(dive)
        stop = max_stop_seconds(dive)
        if ceiling:
            parts.append(f"ceiling {ceiling:.0f}m")
        if stop:
            parts.append(f"stop {stop / 60:.1f}min")
    elif entered is False:
        parts.append("no deco obligation")

    tts = max_time_to_surface_seconds(dive)
    if tts:
        parts.append(f"max TTS {tts / 60:.0f}min")

    return ", ".join(parts) if parts else "no decompression data recorded"
