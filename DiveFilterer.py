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
    dive_was_deeper_than_for_duration
)

def get_filter_function(filter_name: str) -> Callable:
    """
    Returns the corresponding filter function based on the filter name.
    
    Args:
        filter_name (str): Name of the filter function to retrieve
    
    Returns:
        Callable: The corresponding filter function
    """
    filter_map = {
        'deeper_than': dive_was_deeper_than,
        'shallower_than': dive_was_shallower_than,
        'longer_than': dive_was_longer_than,
        'shorter_than': dive_was_shorter_than,
        'after_date': dive_was_after_date,
        'before_date': dive_was_before_date,
        'between_dates': dive_was_between_dates,
        'between_times': dive_was_between_times,
        'deeper_than_for_duration': dive_was_deeper_than_for_duration
    }
    
    if filter_name not in filter_map:
        raise ValueError(f"Filter function '{filter_name}' not found")
    
    return filter_map[filter_name]

def filter_dives(dives: List[Dive], 
                filter_names: List[str], 
                filter_params: Dict[str, Any] = None) -> List[Dive]:
    """
    Filter a list of dives based on multiple filter conditions.
    
    Args:
        dives (List[Dive]): List of dive objects to filter
        filter_names (List[str]): List of filter function names to apply
        filter_params (Dict[str, Any], optional): Parameters for the filter functions
    
    Returns:
        List[Dive]: Filtered list of dives that satisfy all conditions
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