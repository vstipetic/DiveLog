"""
Dive filtering utilities.

This module provides functions for filtering lists of Dive objects
based on various criteria.
"""

from typing import List, Dict, Any, Callable
from Utilities.ClassUtils.DiveClass import Dive
from Utilities.FilterFunctions import (
    dive_was_deeper_than,
    dive_was_shallower_than,
    dive_was_longer_than,
    dive_was_shorter_than,
    dive_was_after_date,
    dive_was_before_date,
    dive_was_between_dates,
    dive_was_between_times,
    dive_was_deeper_than_for_duration,
    dive_had_buddy,
    dive_was_at_location,
    dive_used_gas,
)


# Map filter names to their corresponding functions
FILTER_MAP: Dict[str, Callable] = {
    'deeper_than': dive_was_deeper_than,
    'shallower_than': dive_was_shallower_than,
    'longer_than': dive_was_longer_than,
    'shorter_than': dive_was_shorter_than,
    'after_date': dive_was_after_date,
    'before_date': dive_was_before_date,
    'between_dates': dive_was_between_dates,
    'between_times': dive_was_between_times,
    'deeper_than_for_duration': dive_was_deeper_than_for_duration,
    'had_buddy': dive_had_buddy,
    'at_location': dive_was_at_location,
    'used_gas': dive_used_gas,
}


def get_filter_function(filter_name: str) -> Callable:
    """
    Returns the corresponding filter function based on the filter name.

    Args:
        filter_name: Name of the filter function to retrieve

    Returns:
        The corresponding filter function

    Raises:
        ValueError: If filter name is not recognized
    """
    if filter_name not in FILTER_MAP:
        raise ValueError(f"Filter function '{filter_name}' not found. "
                        f"Available filters: {list(FILTER_MAP.keys())}")

    return FILTER_MAP[filter_name]


def filter_dives(
    dives: List[Dive],
    filter_names: List[str],
    filter_params: Dict[str, Any] = None
) -> List[Dive]:
    """
    Filter a list of dives based on multiple filter conditions.

    Args:
        dives: List of dive objects to filter
        filter_names: List of filter function names to apply
        filter_params: Parameters for the filter functions

    Returns:
        Filtered list of dives that satisfy all conditions
    """
    if filter_params is None:
        filter_params = {}

    filtered_dives = dives.copy()

    for filter_name in filter_names:
        filter_func = get_filter_function(filter_name)
        filtered_dives = [
            dive for dive in filtered_dives
            if filter_func(dive, **filter_params)
        ]

    return filtered_dives


def apply_single_filter(
    dives: List[Dive],
    filter_name: str,
    **kwargs
) -> List[Dive]:
    """
    Apply a single filter to a list of dives.

    Args:
        dives: List of dive objects to filter
        filter_name: Name of the filter function to apply
        **kwargs: Arguments to pass to the filter function

    Returns:
        Filtered list of dives
    """
    filter_func = get_filter_function(filter_name)
    return [dive for dive in dives if filter_func(dive, **kwargs)]
