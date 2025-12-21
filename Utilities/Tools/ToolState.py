"""
Shared state for tool chaining in the statistics agent.

This module provides a mechanism for filter tools to pass their filtered
results to statistics tools, enabling proper tool chaining like:
  1. filter_dives_by_date → stores filtered dives
  2. calculate_statistic → uses filtered dives (not all dives)

Without this, statistics tools would always operate on ALL dives,
ignoring any previous filtering.
"""

from typing import List, Optional
from Utilities.ClassUtils.DiveClass import Dive


class ToolState:
    """
    Class-level shared state for passing filtered dives between tools.

    Filter tools call set_filtered_dives() after filtering.
    Statistics tools call get_filtered_dives() to check for a filtered set.

    The agent should call clear() at the start of each new query to reset state.
    """

    _filtered_dives: Optional[List[Dive]] = None
    _filter_description: Optional[str] = None

    @classmethod
    def set_filtered_dives(cls, dives: List[Dive], description: str = "") -> None:
        """
        Store filtered dives for use by subsequent tools.

        Args:
            dives: List of filtered Dive objects
            description: Human-readable description of the filter applied
        """
        cls._filtered_dives = dives
        cls._filter_description = description

    @classmethod
    def get_filtered_dives(cls) -> Optional[List[Dive]]:
        """
        Get the currently stored filtered dives.

        Returns:
            List of filtered Dive objects, or None if no filter was applied
        """
        return cls._filtered_dives

    @classmethod
    def get_filter_description(cls) -> Optional[str]:
        """Get the description of the current filter."""
        return cls._filter_description

    @classmethod
    def has_filtered_dives(cls) -> bool:
        """Check if there are filtered dives stored."""
        return cls._filtered_dives is not None

    @classmethod
    def clear(cls) -> None:
        """Clear the stored filtered dives. Call at start of each new query."""
        cls._filtered_dives = None
        cls._filter_description = None

    @classmethod
    def get_dive_count(cls) -> int:
        """Get count of filtered dives, or 0 if none stored."""
        return len(cls._filtered_dives) if cls._filtered_dives else 0
