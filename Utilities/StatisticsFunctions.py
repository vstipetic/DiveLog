"""
Statistics calculation functions for dive data.

These functions accept filtered dive lists (attrs-based Dive objects)
and return calculated statistics as Pydantic StatisticsResult objects.

Design Philosophy:
- Filtering (by year, location, buddy, etc.) is handled by FilterFunctions.py
- Statistics (averages, totals, counts) are calculated here
- Agent workflow: Filter dives -> Calculate statistics on filtered set
"""

import pickle
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict

from Utilities.ClassUtils.DiveClass import Dive
import Utilities.DecoFunctions as deco
from Utilities.FilterFunctions import dive_included_person, dive_people_names
from Utilities.Schemas.ToolOutputs import StatisticsResult


def load_all_dives(dive_folder: str = "Storage/Dives") -> List[Dive]:
    """Load all dive pickle files from storage.

    Args:
        dive_folder: Path to directory containing dive pickle files

    Returns:
        List of Dive objects
    """
    dives = []
    folder = Path(dive_folder)

    if not folder.exists():
        return dives

    for pickle_file in folder.glob("*.pickle"):
        try:
            with open(pickle_file, 'rb') as f:
                dive = pickle.load(f)
                dives.append(dive)
        except Exception as e:
            print(f"Error loading {pickle_file}: {e}")

    return dives


def average_depth(dives: List[Dive]) -> StatisticsResult:
    """Calculate average maximum depth across all dives.

    Args:
        dives: List of Dive objects (pre-filtered if needed)

    Returns:
        StatisticsResult with average depth in meters
    """
    if not dives:
        return StatisticsResult(
            stat_type="average_depth",
            value=0.0,
            unit="meters",
            context="No dives to analyze"
        )

    max_depths = []
    for dive in dives:
        if dive.timeline.depths:
            max_depths.append(max(dive.timeline.depths))

    if not max_depths:
        return StatisticsResult(
            stat_type="average_depth",
            value=0.0,
            unit="meters",
            context="No depth data available"
        )

    avg = sum(max_depths) / len(max_depths)
    return StatisticsResult(
        stat_type="average_depth",
        value=round(avg, 2),
        unit="meters",
        context=f"Average across {len(max_depths)} dives"
    )


def max_depth(dives: List[Dive]) -> StatisticsResult:
    """Find maximum depth across all dives.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with maximum depth in meters
    """
    if not dives:
        return StatisticsResult(
            stat_type="max_depth",
            value=0.0,
            unit="meters",
            context="No dives to analyze"
        )

    max_depths = []
    for dive in dives:
        if dive.timeline.depths:
            max_depths.append(max(dive.timeline.depths))

    if not max_depths:
        return StatisticsResult(
            stat_type="max_depth",
            value=0.0,
            unit="meters",
            context="No depth data available"
        )

    return StatisticsResult(
        stat_type="max_depth",
        value=round(max(max_depths), 2),
        unit="meters",
        context=f"Deepest dive out of {len(dives)} dives"
    )


def min_depth(dives: List[Dive]) -> StatisticsResult:
    """Find minimum maximum depth across all dives.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with minimum depth in meters
    """
    if not dives:
        return StatisticsResult(
            stat_type="min_depth",
            value=0.0,
            unit="meters",
            context="No dives to analyze"
        )

    max_depths = []
    for dive in dives:
        if dive.timeline.depths:
            max_depths.append(max(dive.timeline.depths))

    if not max_depths:
        return StatisticsResult(
            stat_type="min_depth",
            value=0.0,
            unit="meters",
            context="No depth data available"
        )

    return StatisticsResult(
        stat_type="min_depth",
        value=round(min(max_depths), 2),
        unit="meters",
        context=f"Shallowest dive out of {len(dives)} dives"
    )


def total_dive_time(dives: List[Dive]) -> StatisticsResult:
    """Calculate total dive time in minutes.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with total time in minutes
    """
    if not dives:
        return StatisticsResult(
            stat_type="total_dive_time",
            value=0.0,
            unit="minutes",
            context="No dives to analyze"
        )

    total_seconds = sum(dive.basics.duration for dive in dives)
    total_minutes = total_seconds / 60

    return StatisticsResult(
        stat_type="total_dive_time",
        value=round(total_minutes, 2),
        unit="minutes",
        context=f"Total across {len(dives)} dives ({total_minutes / 60:.1f} hours)"
    )


def dive_count(dives: List[Dive]) -> StatisticsResult:
    """Count total number of dives.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with count
    """
    return StatisticsResult(
        stat_type="dive_count",
        value=float(len(dives)),
        unit="dives",
        context=f"Total dives in dataset"
    )


def average_duration(dives: List[Dive]) -> StatisticsResult:
    """Calculate average dive duration.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with average duration in minutes
    """
    if not dives:
        return StatisticsResult(
            stat_type="average_duration",
            value=0.0,
            unit="minutes",
            context="No dives to analyze"
        )

    total_seconds = sum(dive.basics.duration for dive in dives)
    avg_minutes = (total_seconds / len(dives)) / 60

    return StatisticsResult(
        stat_type="average_duration",
        value=round(avg_minutes, 2),
        unit="minutes",
        context=f"Average across {len(dives)} dives"
    )


def longest_dive(dives: List[Dive]) -> StatisticsResult:
    """Find longest dive duration.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with longest duration in minutes
    """
    if not dives:
        return StatisticsResult(
            stat_type="longest_dive",
            value=0.0,
            unit="minutes",
            context="No dives to analyze"
        )

    max_duration = max(dive.basics.duration for dive in dives)

    return StatisticsResult(
        stat_type="longest_dive",
        value=round(max_duration / 60, 2),
        unit="minutes",
        context=f"Longest out of {len(dives)} dives"
    )


def shortest_dive(dives: List[Dive]) -> StatisticsResult:
    """Find shortest dive duration.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with shortest duration in minutes
    """
    if not dives:
        return StatisticsResult(
            stat_type="shortest_dive",
            value=0.0,
            unit="minutes",
            context="No dives to analyze"
        )

    min_duration = min(dive.basics.duration for dive in dives)

    return StatisticsResult(
        stat_type="shortest_dive",
        value=round(min_duration / 60, 2),
        unit="minutes",
        context=f"Shortest out of {len(dives)} dives"
    )


def deepest_dive(dives: List[Dive]) -> StatisticsResult:
    """Find deepest dive (alias for max_depth with different context).

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with deepest dive depth in meters
    """
    result = max_depth(dives)
    result.stat_type = "deepest_dive"
    return result


def shallowest_dive(dives: List[Dive]) -> StatisticsResult:
    """Find shallowest dive (alias for min_depth with different context).

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with shallowest dive depth in meters
    """
    result = min_depth(dives)
    result.stat_type = "shallowest_dive"
    return result


def time_below_depth(dives: List[Dive], depth_threshold: float) -> StatisticsResult:
    """Calculate total time spent below specified depth across all dives.

    Args:
        dives: List of Dive objects
        depth_threshold: Depth threshold in meters

    Returns:
        StatisticsResult with time in minutes
    """
    if not dives:
        return StatisticsResult(
            stat_type="time_below_depth",
            value=0.0,
            unit="minutes",
            context=f"No dives to analyze"
        )

    total_time_seconds = 0.0

    for dive in dives:
        if not dive.timeline.depths or not dive.timeline.timestamps:
            continue

        depths = dive.timeline.depths
        timestamps = dive.timeline.timestamps

        # Calculate time spent below threshold
        for i in range(len(depths) - 1):
            if depths[i] > depth_threshold:
                # Time between this sample and the next
                time_delta = timestamps[i + 1] - timestamps[i]
                total_time_seconds += time_delta

    total_minutes = total_time_seconds / 60

    return StatisticsResult(
        stat_type="time_below_depth",
        value=round(total_minutes, 2),
        unit="minutes",
        context=f"Time spent below {depth_threshold}m across {len(dives)} dives"
    )


def average_temperature(dives: List[Dive]) -> StatisticsResult:
    """Calculate average water temperature across all dives.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with average temperature in Celsius
    """
    if not dives:
        return StatisticsResult(
            stat_type="average_temperature",
            value=0.0,
            unit="celsius",
            context="No dives to analyze"
        )

    all_temps = []
    for dive in dives:
        if dive.timeline.temperature:
            all_temps.extend(dive.timeline.temperature)

    if not all_temps:
        return StatisticsResult(
            stat_type="average_temperature",
            value=0.0,
            unit="celsius",
            context="No temperature data available"
        )

    avg = sum(all_temps) / len(all_temps)

    return StatisticsResult(
        stat_type="average_temperature",
        value=round(avg, 1),
        unit="celsius",
        context=f"Average across {len(dives)} dives"
    )


def dives_by_year(dives: List[Dive]) -> StatisticsResult:
    """Count dives grouped by year.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with breakdown by year
    """
    if not dives:
        return StatisticsResult(
            stat_type="dives_by_year",
            value=0.0,
            unit="dives",
            context="No dives to analyze"
        )

    year_counts: Dict[str, float] = defaultdict(float)
    for dive in dives:
        year = str(dive.basics.start_time.year)
        year_counts[year] += 1

    # Sort by year
    sorted_breakdown = dict(sorted(year_counts.items()))

    return StatisticsResult(
        stat_type="dives_by_year",
        value=float(len(dives)),
        unit="dives",
        breakdown=sorted_breakdown,
        context=f"Dives from {min(year_counts.keys())} to {max(year_counts.keys())}"
    )


def dives_by_month(dives: List[Dive]) -> StatisticsResult:
    """Count dives grouped by month.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with breakdown by month
    """
    if not dives:
        return StatisticsResult(
            stat_type="dives_by_month",
            value=0.0,
            unit="dives",
            context="No dives to analyze"
        )

    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    month_counts: Dict[str, float] = {name: 0 for name in month_names}
    for dive in dives:
        month = month_names[dive.basics.start_time.month - 1]
        month_counts[month] += 1

    # Remove months with 0 dives for cleaner output
    breakdown = {k: v for k, v in month_counts.items() if v > 0}

    return StatisticsResult(
        stat_type="dives_by_month",
        value=float(len(dives)),
        unit="dives",
        breakdown=breakdown,
        context=f"Distribution across months"
    )


def dives_by_location(dives: List[Dive]) -> StatisticsResult:
    """Count dives grouped by location.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with breakdown by location
    """
    if not dives:
        return StatisticsResult(
            stat_type="dives_by_location",
            value=0.0,
            unit="dives",
            context="No dives to analyze"
        )

    location_counts: Dict[str, float] = defaultdict(float)
    for dive in dives:
        location = dive.location.name or "Unknown"
        location_counts[location] += 1

    # Sort by count (descending)
    sorted_breakdown = dict(
        sorted(location_counts.items(), key=lambda x: x[1], reverse=True)
    )

    return StatisticsResult(
        stat_type="dives_by_location",
        value=float(len(dives)),
        unit="dives",
        breakdown=sorted_breakdown,
        context=f"Dives at {len(location_counts)} locations"
    )


def dives_by_buddy(dives: List[Dive]) -> StatisticsResult:
    """Count dives grouped by dive buddy.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with breakdown by buddy
    """
    if not dives:
        return StatisticsResult(
            stat_type="dives_by_buddy",
            value=0.0,
            unit="dives",
            context="No dives to analyze"
        )

    buddy_counts: Dict[str, float] = defaultdict(float)
    for dive in dives:
        buddy = dive.people.buddy or "Solo/Unknown"
        buddy_counts[buddy] += 1

    # Sort by count (descending)
    sorted_breakdown = dict(
        sorted(buddy_counts.items(), key=lambda x: x[1], reverse=True)
    )

    return StatisticsResult(
        stat_type="dives_by_buddy",
        value=float(len(dives)),
        unit="dives",
        breakdown=sorted_breakdown,
        context=f"Dives with {len(buddy_counts)} different buddies"
    )


def dives_by_person(dives: List[Dive]) -> StatisticsResult:
    """Count dives grouped by every person present, not just the buddy.

    ``dives_by_buddy`` only counts the designated buddy, so anyone who was on
    the dive as part of the group is invisible to it. This counts each person
    once per dive across the buddy, divemaster and group fields.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with a breakdown by person
    """
    if not dives:
        return StatisticsResult(
            stat_type="dives_by_person",
            value=0.0,
            unit="dives",
            context="No dives to analyze"
        )

    person_counts: Dict[str, float] = defaultdict(float)
    solo_dives = 0

    for dive in dives:
        names = dive_people_names(dive)
        if not names:
            solo_dives += 1
            continue
        for name in names:
            person_counts[name] += 1

    if solo_dives:
        person_counts["Solo/Unknown"] = float(solo_dives)

    sorted_breakdown = dict(
        sorted(person_counts.items(), key=lambda x: x[1], reverse=True)
    )

    named_people = len([k for k in person_counts if k != "Solo/Unknown"])

    return StatisticsResult(
        stat_type="dives_by_person",
        value=float(len(dives)),
        unit="dives",
        breakdown=sorted_breakdown,
        context=(
            f"{named_people} different people across {len(dives)} dives "
            f"(counts any role: buddy, divemaster or group member)"
        )
    )


def most_common_dive_partner(dives: List[Dive]) -> StatisticsResult:
    """Find the person who appears on the most dives, in any role.

    Unlike ``most_common_buddy`` this counts group members too, so it answers
    "who do I actually dive with most often".

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with the most frequent dive partner and their count
    """
    if not dives:
        return StatisticsResult(
            stat_type="most_common_dive_partner",
            value=0.0,
            unit="dives",
            context="No dives to analyze"
        )

    person_counts: Dict[str, int] = defaultdict(int)
    for dive in dives:
        for name in dive_people_names(dive):
            person_counts[name] += 1

    if not person_counts:
        return StatisticsResult(
            stat_type="most_common_dive_partner",
            value=0.0,
            unit="dives",
            context="No people recorded on these dives"
        )

    partner_name, count = max(person_counts.items(), key=lambda x: x[1])

    return StatisticsResult(
        stat_type="most_common_dive_partner",
        value=float(count),
        unit="dives",
        context=f"Most common dive partner: {partner_name}",
        breakdown=dict(sorted(person_counts.items(), key=lambda x: x[1], reverse=True))
    )


def unique_dive_partners(dives: List[Dive]) -> StatisticsResult:
    """Count how many distinct people appear across the dives, in any role.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with the number of distinct people
    """
    if not dives:
        return StatisticsResult(
            stat_type="unique_dive_partners",
            value=0.0,
            unit="people",
            context="No dives to analyze"
        )

    person_counts: Dict[str, float] = defaultdict(float)
    for dive in dives:
        for name in dive_people_names(dive):
            person_counts[name] += 1

    return StatisticsResult(
        stat_type="unique_dive_partners",
        value=float(len(person_counts)),
        unit="people",
        breakdown=dict(sorted(person_counts.items(), key=lambda x: x[1], reverse=True)),
        context=f"{len(person_counts)} different people across {len(dives)} dives"
    )


def count_dives_with_person(dives: List[Dive], person_name: str) -> StatisticsResult:
    """Count dives with a specific person, split by the role they held.

    Answers "how many dives did I do with X" without the caller having to
    decide up front whether X was the buddy or just in the group.

    Args:
        dives: List of Dive objects
        person_name: Name to search for (case-insensitive partial match)

    Returns:
        StatisticsResult whose value is the total dive count, with a breakdown
        by role and the matched names listed in the context
    """
    if not dives:
        return StatisticsResult(
            stat_type="count_dives_with_person",
            value=0.0,
            unit="dives",
            context="No dives to analyze"
        )

    as_buddy = 0
    as_divemaster = 0
    in_group_only = 0
    total = 0
    matched_names = set()

    for dive in dives:
        if not dive_included_person(dive, person_name, role="any"):
            continue

        total += 1
        buddy_match = dive_included_person(dive, person_name, role="buddy")
        dm_match = dive_included_person(dive, person_name, role="divemaster")

        if buddy_match:
            as_buddy += 1
        if dm_match:
            as_divemaster += 1
        if not buddy_match and not dm_match:
            in_group_only += 1

        needle = person_name.lower()
        matched_names.update(
            name for name in dive_people_names(dive) if needle in name.lower()
        )

    breakdown: Dict[str, float] = {
        "as buddy": float(as_buddy),
        "in group only": float(in_group_only),
    }
    if as_divemaster:
        breakdown["as divemaster"] = float(as_divemaster)

    if total == 0:
        context = f"No dives found with anyone matching '{person_name}'"
    else:
        context = (
            f"Matched: {', '.join(sorted(matched_names))} "
            f"(searched all of buddy, divemaster and group)"
        )

    return StatisticsResult(
        stat_type="count_dives_with_person",
        value=float(total),
        unit="dives",
        breakdown=breakdown,
        context=context
    )


def dives_by_deco_status(dives: List[Dive]) -> StatisticsResult:
    """Break dives down by whether they incurred a decompression obligation.

    Dives whose computer recorded no decompression data get their own bucket
    rather than being counted as clean profiles.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with a breakdown by decompression status
    """
    if not dives:
        return StatisticsResult(
            stat_type="dives_by_deco_status",
            value=0.0,
            unit="dives",
            context="No dives to analyze"
        )

    counts: Dict[str, float] = {
        "entered deco": 0.0,
        "stayed within NDL": 0.0,
        "no deco data recorded": 0.0,
    }

    for dive in dives:
        status = deco.dive_entered_deco(dive)
        if status is None:
            counts["no deco data recorded"] += 1
        elif status:
            counts["entered deco"] += 1
        else:
            counts["stayed within NDL"] += 1

    breakdown = {k: v for k, v in counts.items() if v}

    return StatisticsResult(
        stat_type="dives_by_deco_status",
        value=counts["entered deco"],
        unit="dives",
        breakdown=breakdown,
        context=(
            f"{counts['entered deco']:.0f} of {len(dives)} dives incurred a "
            "decompression obligation"
        )
    )


def max_deco_stop(dives: List[Dive]) -> StatisticsResult:
    """Longest required decompression stop across the dives, in minutes.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with the longest stop in minutes
    """
    stops = [
        (dive, deco.max_stop_seconds(dive))
        for dive in dives
    ]
    valid = [(d, s) for d, s in stops if s]

    if not valid:
        return StatisticsResult(
            stat_type="max_deco_stop",
            value=0.0,
            unit="minutes",
            context="No dive required a decompression stop"
        )

    dive, seconds = max(valid, key=lambda pair: pair[1])
    return StatisticsResult(
        stat_type="max_deco_stop",
        value=round(seconds / 60, 1),
        unit="minutes",
        context=(
            f"Longest stop on {dive.basics.start_time.strftime('%Y-%m-%d')} at "
            f"{dive.location.name or 'Unknown'} "
            f"({len(valid)} of {len(dives)} dives required a stop)"
        )
    )


def min_ndl_reached(dives: List[Dive]) -> StatisticsResult:
    """Closest any dive came to the no-decompression limit, in minutes.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with the lowest NDL reached in minutes
    """
    values = [
        (dive, deco.min_ndl_seconds(dive))
        for dive in dives
        if deco.has_ndl_data(dive)
    ]

    if not values:
        return StatisticsResult(
            stat_type="min_ndl_reached",
            value=0.0,
            unit="minutes",
            context="No dive recorded no-decompression-limit data"
        )

    dive, seconds = min(values, key=lambda pair: pair[1])
    return StatisticsResult(
        stat_type="min_ndl_reached",
        value=round(seconds / 60, 1),
        unit="minutes",
        context=(
            f"Lowest NDL on {dive.basics.start_time.strftime('%Y-%m-%d')} at "
            f"{dive.location.name or 'Unknown'} "
            f"({len(values)} of {len(dives)} dives recorded NDL)"
        )
    )


def total_air_consumption(dives: List[Dive]) -> StatisticsResult:
    """Calculate total air consumption across all dives.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with total bar consumed
    """
    if not dives:
        return StatisticsResult(
            stat_type="total_air_consumption",
            value=0.0,
            unit="bar",
            context="No dives to analyze"
        )

    total_bar = 0
    dives_with_data = 0

    for dive in dives:
        if dive.gasses.start_pressure > 0 and dive.gasses.end_pressure >= 0:
            consumed = dive.gasses.start_pressure - dive.gasses.end_pressure
            if consumed > 0:
                total_bar += consumed
                dives_with_data += 1

    return StatisticsResult(
        stat_type="total_air_consumption",
        value=float(total_bar),
        unit="bar",
        context=f"Total consumption across {dives_with_data} dives with pressure data"
    )


def average_air_consumption_rate(dives: List[Dive]) -> StatisticsResult:
    """Calculate average air consumption rate in bar per minute.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with average consumption rate
    """
    if not dives:
        return StatisticsResult(
            stat_type="average_air_consumption_rate",
            value=0.0,
            unit="bar/minute",
            context="No dives to analyze"
        )

    rates = []
    for dive in dives:
        if dive.gasses.start_pressure > 0 and dive.gasses.end_pressure >= 0:
            consumed = dive.gasses.start_pressure - dive.gasses.end_pressure
            duration_minutes = dive.basics.duration / 60
            if consumed > 0 and duration_minutes > 0:
                rates.append(consumed / duration_minutes)

    if not rates:
        return StatisticsResult(
            stat_type="average_air_consumption_rate",
            value=0.0,
            unit="bar/minute",
            context="No pressure data available"
        )

    avg_rate = sum(rates) / len(rates)

    return StatisticsResult(
        stat_type="average_air_consumption_rate",
        value=round(avg_rate, 2),
        unit="bar/minute",
        context=f"Average across {len(rates)} dives"
    )


def most_common_buddy(dives: List[Dive]) -> StatisticsResult:
    """Find the most common dive buddy.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with most common buddy name and count
    """
    if not dives:
        return StatisticsResult(
            stat_type="most_common_buddy",
            value=0.0,
            unit="dives",
            context="No dives to analyze"
        )

    buddy_counts: Dict[str, int] = defaultdict(int)
    for dive in dives:
        buddy = dive.people.buddy or "Solo/Unknown"
        buddy_counts[buddy] += 1

    if not buddy_counts:
        return StatisticsResult(
            stat_type="most_common_buddy",
            value=0.0,
            unit="dives",
            context="No buddy data available"
        )

    most_common = max(buddy_counts.items(), key=lambda x: x[1])
    buddy_name, count = most_common

    return StatisticsResult(
        stat_type="most_common_buddy",
        value=float(count),
        unit="dives",
        context=f"Most common buddy: {buddy_name}",
        breakdown=dict(sorted(buddy_counts.items(), key=lambda x: x[1], reverse=True))
    )


def most_visited_location(dives: List[Dive]) -> StatisticsResult:
    """Find the most visited dive location.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with most visited location and count
    """
    if not dives:
        return StatisticsResult(
            stat_type="most_visited_location",
            value=0.0,
            unit="dives",
            context="No dives to analyze"
        )

    location_counts: Dict[str, int] = defaultdict(int)
    for dive in dives:
        location = dive.location.name or "Unknown"
        location_counts[location] += 1

    if not location_counts:
        return StatisticsResult(
            stat_type="most_visited_location",
            value=0.0,
            unit="dives",
            context="No location data available"
        )

    most_visited = max(location_counts.items(), key=lambda x: x[1])
    location_name, count = most_visited

    return StatisticsResult(
        stat_type="most_visited_location",
        value=float(count),
        unit="dives",
        context=f"Most visited location: {location_name}",
        breakdown=dict(sorted(location_counts.items(), key=lambda x: x[1], reverse=True))
    )


def average_max_depth_by_year(dives: List[Dive]) -> StatisticsResult:
    """Calculate average maximum depth grouped by year.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with breakdown of avg depth by year
    """
    if not dives:
        return StatisticsResult(
            stat_type="average_max_depth_by_year",
            value=0.0,
            unit="meters",
            context="No dives to analyze"
        )

    year_depths: Dict[str, List[float]] = defaultdict(list)
    for dive in dives:
        if dive.timeline.depths:
            year = str(dive.basics.start_time.year)
            year_depths[year].append(max(dive.timeline.depths))

    if not year_depths:
        return StatisticsResult(
            stat_type="average_max_depth_by_year",
            value=0.0,
            unit="meters",
            context="No depth data available"
        )

    # Calculate average for each year
    breakdown = {}
    for year, depths in sorted(year_depths.items()):
        breakdown[year] = round(sum(depths) / len(depths), 1)

    # Overall average
    all_depths = [d for depths in year_depths.values() for d in depths]
    overall_avg = sum(all_depths) / len(all_depths) if all_depths else 0

    return StatisticsResult(
        stat_type="average_max_depth_by_year",
        value=round(overall_avg, 2),
        unit="meters",
        breakdown=breakdown,
        context=f"Yearly depth trends from {min(year_depths.keys())} to {max(year_depths.keys())}"
    )


def total_time_by_location(dives: List[Dive]) -> StatisticsResult:
    """Calculate total dive time grouped by location.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with breakdown of time by location in minutes
    """
    if not dives:
        return StatisticsResult(
            stat_type="total_time_by_location",
            value=0.0,
            unit="minutes",
            context="No dives to analyze"
        )

    location_times: Dict[str, float] = defaultdict(float)
    for dive in dives:
        location = dive.location.name or "Unknown"
        location_times[location] += dive.basics.duration / 60  # Convert to minutes

    # Sort by time (descending)
    sorted_breakdown = dict(
        sorted(location_times.items(), key=lambda x: x[1], reverse=True)
    )

    total_minutes = sum(location_times.values())

    return StatisticsResult(
        stat_type="total_time_by_location",
        value=round(total_minutes, 2),
        unit="minutes",
        breakdown={k: round(v, 1) for k, v in sorted_breakdown.items()},
        context=f"Time at {len(location_times)} locations ({total_minutes / 60:.1f} hours total)"
    )


def dives_by_gas_type(dives: List[Dive]) -> StatisticsResult:
    """Count dives grouped by gas type (air, nitrox, trimix).

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with breakdown by gas type
    """
    if not dives:
        return StatisticsResult(
            stat_type="dives_by_gas_type",
            value=0.0,
            unit="dives",
            context="No dives to analyze"
        )

    gas_counts: Dict[str, float] = defaultdict(float)
    for dive in dives:
        gas_type = dive.gasses.gas or "Unknown"
        gas_counts[gas_type] += 1

    # Sort by count (descending)
    sorted_breakdown = dict(
        sorted(gas_counts.items(), key=lambda x: x[1], reverse=True)
    )

    return StatisticsResult(
        stat_type="dives_by_gas_type",
        value=float(len(dives)),
        unit="dives",
        breakdown=sorted_breakdown,
        context=f"Gas type distribution across {len(dives)} dives"
    )


def average_cns_load(dives: List[Dive]) -> StatisticsResult:
    """Calculate average maximum CNS oxygen toxicity load.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with average CNS percentage
    """
    if not dives:
        return StatisticsResult(
            stat_type="average_cns_load",
            value=0.0,
            unit="%",
            context="No dives to analyze"
        )

    max_cns_values = []
    for dive in dives:
        if dive.timeline.cns_load:
            max_cns_values.append(max(dive.timeline.cns_load))

    if not max_cns_values:
        return StatisticsResult(
            stat_type="average_cns_load",
            value=0.0,
            unit="%",
            context="No CNS data available"
        )

    avg_cns = sum(max_cns_values) / len(max_cns_values)
    max_cns = max(max_cns_values)

    return StatisticsResult(
        stat_type="average_cns_load",
        value=round(avg_cns, 1),
        unit="%",
        context=f"Average max CNS across {len(max_cns_values)} dives (highest: {max_cns:.1f}%)"
    )


def max_cns_load(dives: List[Dive]) -> StatisticsResult:
    """Find the maximum CNS oxygen toxicity load across all dives.

    Args:
        dives: List of Dive objects

    Returns:
        StatisticsResult with maximum CNS percentage
    """
    if not dives:
        return StatisticsResult(
            stat_type="max_cns_load",
            value=0.0,
            unit="%",
            context="No dives to analyze"
        )

    max_cns_values = []
    for dive in dives:
        if dive.timeline.cns_load:
            max_cns_values.append(max(dive.timeline.cns_load))

    if not max_cns_values:
        return StatisticsResult(
            stat_type="max_cns_load",
            value=0.0,
            unit="%",
            context="No CNS data available"
        )

    return StatisticsResult(
        stat_type="max_cns_load",
        value=round(max(max_cns_values), 1),
        unit="%",
        context=f"Maximum CNS load out of {len(max_cns_values)} dives"
    )


# Map of all available statistics functions
STATISTICS_MAP = {
    "average_depth": average_depth,
    "max_depth": max_depth,
    "min_depth": min_depth,
    "total_dive_time": total_dive_time,
    "total_time": total_dive_time,  # Alias
    "dive_count": dive_count,
    "count": dive_count,  # Alias
    "average_duration": average_duration,
    "longest_dive": longest_dive,
    "shortest_dive": shortest_dive,
    "deepest_dive": deepest_dive,
    "shallowest_dive": shallowest_dive,
    "average_temperature": average_temperature,
    "dives_by_year": dives_by_year,
    "dives_by_month": dives_by_month,
    "dives_by_location": dives_by_location,
    "dives_by_buddy": dives_by_buddy,
    "total_air_consumption": total_air_consumption,
    "average_air_consumption_rate": average_air_consumption_rate,
    # People statistics that count group members, not just the buddy.
    # (count_dives_with_person is not here: it takes a name argument, so it is
    # exposed through its own tool, like time_below_depth.)
    # Decompression, straight from the dive computer's own recorded values.
    "dives_by_deco_status": dives_by_deco_status,
    "max_deco_stop": max_deco_stop,
    "min_ndl_reached": min_ndl_reached,
    "dives_by_person": dives_by_person,
    "most_common_dive_partner": most_common_dive_partner,
    "unique_dive_partners": unique_dive_partners,
    # New statistics
    "most_common_buddy": most_common_buddy,
    "most_visited_location": most_visited_location,
    "average_max_depth_by_year": average_max_depth_by_year,
    "total_time_by_location": total_time_by_location,
    "dives_by_gas_type": dives_by_gas_type,
    "average_cns_load": average_cns_load,
    "max_cns_load": max_cns_load,
}


def get_statistic(stat_type: str, dives: List[Dive]) -> StatisticsResult:
    """Get a statistic by name.

    Args:
        stat_type: Name of the statistic to calculate
        dives: List of Dive objects

    Returns:
        StatisticsResult for the requested statistic

    Raises:
        ValueError: If stat_type is not recognized
    """
    if stat_type not in STATISTICS_MAP:
        available = list(STATISTICS_MAP.keys())
        raise ValueError(f"Unknown statistic type: {stat_type}. Available: {available}")

    return STATISTICS_MAP[stat_type](dives)
