from typing import List, Dict, Any, Callable
from FilterFunctions import *  # Import all filter functions

def get_filter_function(filter_name: str) -> Callable:
    """
    Returns the corresponding filter function based on the filter name.
    
    Args:
        filter_name (str): Name of the filter function to retrieve
    
    Returns:
        Callable: The corresponding filter function
    """
    # This dictionary maps filter names to their corresponding functions
    filter_map = {
        'depth_filter': depth_filter,
        'duration_filter': duration_filter,
        # Add more filters as needed
    }
    
    if filter_name not in filter_map:
        raise ValueError(f"Filter function '{filter_name}' not found")
    
    return filter_map[filter_name]

def filter_dives(dives: List[Any], 
                filter_names: List[str], 
                filter_params: Dict[str, Any] = None) -> List[Any]:
    """
    Filter a list of dives based on multiple filter conditions.
    
    Args:
        dives (List[Any]): List of dive objects to filter
        filter_names (List[str]): List of filter function names to apply
        filter_params (Dict[str, Any], optional): Parameters for the filter functions
    
    Returns:
        List[Any]: Filtered list of dives that satisfy all conditions
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