"""
Filter functions for dive data.

These functions accept attrs-based Dive objects and return boolean results.
They are used by both the filtering utilities and the agent tool layer.
"""

from Utilities.ClassUtils.DiveClass import Dive
import datetime
from typing import Optional


def dive_was_deeper_than(dive_data: Dive, depth: float) -> bool:
    """Check if dive maximum depth exceeded the specified depth.

    Args:
        dive_data: Dive object to check
        depth: Depth threshold in meters

    Returns:
        True if max depth > threshold
    """
    if not dive_data.timeline.depths:
        return False
    return max(dive_data.timeline.depths) > depth


def dive_was_shallower_than(dive_data: Dive, depth: float) -> bool:
    """Check if dive maximum depth was below the specified depth.

    Args:
        dive_data: Dive object to check
        depth: Depth threshold in meters

    Returns:
        True if max depth < threshold
    """
    if not dive_data.timeline.depths:
        return False
    return max(dive_data.timeline.depths) < depth


def dive_was_longer_than(dive_data: Dive, time: float) -> bool:
    """Check if dive duration exceeded the specified time.

    Args:
        dive_data: Dive object to check
        time: Duration threshold in seconds

    Returns:
        True if duration > threshold
    """
    return dive_data.basics.duration > time


def dive_was_shorter_than(dive_data: Dive, time: float) -> bool:
    """Check if dive duration was less than the specified time.

    Args:
        dive_data: Dive object to check
        time: Duration threshold in seconds

    Returns:
        True if duration < threshold
    """
    return dive_data.basics.duration < time


def dive_was_after_date(dive_data: Dive, date: datetime.datetime) -> bool:
    """Check if dive occurred after the specified date.

    Args:
        dive_data: Dive object to check
        date: Date threshold

    Returns:
        True if dive start time > date
    """
    return dive_data.basics.start_time > date


def dive_was_before_date(dive_data: Dive, date: datetime.datetime) -> bool:
    """Check if dive occurred before the specified date.

    Args:
        dive_data: Dive object to check
        date: Date threshold

    Returns:
        True if dive start time < date
    """
    return dive_data.basics.start_time < date


def dive_was_between_dates(
    dive_data: Dive,
    start_date: datetime.datetime,
    end_date: datetime.datetime
) -> bool:
    """Check if dive occurred between two dates (exclusive).

    Args:
        dive_data: Dive object to check
        start_date: Start of date range
        end_date: End of date range

    Returns:
        True if start_date < dive start time < end_date
    """
    return start_date < dive_data.basics.start_time < end_date


def dive_was_between_times(
    dive_data: Dive,
    start_time: datetime.datetime,
    end_time: datetime.datetime
) -> bool:
    """Check if dive occurred between two times (exclusive).

    Args:
        dive_data: Dive object to check
        start_time: Start of time range
        end_time: End of time range

    Returns:
        True if start_time < dive start time < end_time
    """
    return start_time < dive_data.basics.start_time < end_time


def dive_was_deeper_than_for_duration(
    dive_data: Dive,
    depth: float,
    duration: float
) -> bool:
    """Check if dive exceeded both depth and duration thresholds.

    Args:
        dive_data: Dive object to check
        depth: Depth threshold in meters
        duration: Duration threshold in seconds

    Returns:
        True if max depth > depth AND duration > duration threshold
    """
    if not dive_data.timeline.depths:
        return False
    return max(dive_data.timeline.depths) > depth and dive_data.basics.duration > duration


def dive_had_buddy(dive_data: Dive, buddy_name: str) -> bool:
    """Check if dive was with a specific buddy.

    Args:
        dive_data: Dive object to check
        buddy_name: Name of buddy to search for (case-insensitive)

    Returns:
        True if buddy matches
    """
    if not dive_data.people.buddy:
        return False
    return buddy_name.lower() in dive_data.people.buddy.lower()


def dive_was_at_location(dive_data: Dive, location_name: str) -> bool:
    """Check if dive was at a specific location.

    Args:
        dive_data: Dive object to check
        location_name: Name of location to search for (case-insensitive partial match)

    Returns:
        True if location matches
    """
    if not dive_data.location.name:
        return False
    return location_name.lower() in dive_data.location.name.lower()


def dive_used_gas(dive_data: Dive, gas_type: str) -> bool:
    """Check if dive used a specific gas type.

    Args:
        dive_data: Dive object to check
        gas_type: Gas type to check for ('air', 'nitrox', 'trimix')

    Returns:
        True if gas type matches
    """
    if not dive_data.gasses.gas:
        return False
    return dive_data.gasses.gas.lower() == gas_type.lower()
