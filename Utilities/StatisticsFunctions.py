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
