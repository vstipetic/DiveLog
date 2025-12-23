"""
Shared state for tool chaining in the statistics agent.

This module provides a mechanism for filter tools to pass their filtered
results to statistics tools, enabling proper tool chaining like:
  1. filter_dives_by_date → stores filtered dives
  2. calculate_statistic → uses filtered dives (not all dives)

Additionally supports labeled groups for scatter plots with custom groupings:
  1. filter_dives_by_date (summer months) → stores filtered dives
  2. label_filtered_dives("Summer") → saves with label
  3. filter_dives_by_date (fall months) → stores filtered dives
  4. label_filtered_dives("Fall") → saves with label
  5. plot_scatter(..., use_labeled_groups=True) → plots with color coding

Without this, statistics tools would always operate on ALL dives,
ignoring any previous filtering.
"""

from typing import Dict, List, Optional
from Utilities.ClassUtils.DiveClass import Dive


class ToolState:
    """
    Class-level shared state for passing filtered dives between tools.

    Filter tools call set_filtered_dives() after filtering.
    Statistics tools call get_filtered_dives() to check for a filtered set.

    Labeled groups can be created via add_labeled_group() for scatter plots
    that need custom groupings (seasons, depth bands, etc.).

    The agent should call clear() at the start of each new query to reset state.
    """

    _filtered_dives: Optional[List[Dive]] = None
    _filter_description: Optional[str] = None
    _labeled_groups: Optional[Dict[str, List[Dive]]] = None

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
        """Clear the stored filtered dives and labeled groups. Call at start of each new query."""
        cls._filtered_dives = None
        cls._filter_description = None
        cls._labeled_groups = None

    @classmethod
    def get_dive_count(cls) -> int:
        """Get count of filtered dives, or 0 if none stored."""
        return len(cls._filtered_dives) if cls._filtered_dives else 0

    # --- Labeled Groups API (for scatter plots with custom groupings) ---

    @classmethod
    def add_labeled_group(cls, label: str, dives: List[Dive]) -> None:
        """
        Store a labeled group of dives for use in scatter plots.

        Args:
            label: Name for this group (e.g., "Summer", "Deep dives")
            dives: List of Dive objects for this group
        """
        if cls._labeled_groups is None:
            cls._labeled_groups = {}
        cls._labeled_groups[label] = list(dives)

    @classmethod
    def get_labeled_groups(cls) -> Dict[str, List[Dive]]:
        """
        Get all labeled dive groups.

        Returns:
            Dict mapping labels to lists of dives
        """
        if cls._labeled_groups is None:
            return {}
        return cls._labeled_groups.copy()

    @classmethod
    def has_labeled_groups(cls) -> bool:
        """Check if there are any labeled groups stored."""
        return cls._labeled_groups is not None and len(cls._labeled_groups) > 0

    @classmethod
    def get_labeled_group_count(cls) -> int:
        """Get the number of labeled groups."""
        if cls._labeled_groups is None:
            return 0
        return len(cls._labeled_groups)

    @classmethod
    def clear_labeled_groups(cls) -> None:
        """Clear only the labeled groups (keeps filtered dives)."""
        cls._labeled_groups = None
