"""
Shared state for the most recently built geographic region.

Mirrors :class:`Utilities.Tools.ToolState.ToolState`. A 32-vertex circle is
~500 tokens of coordinates; round-tripping that through the model just so it
can hand it back to the next tool wastes context and gives the model a chance
to mangle the numbers. Instead ``build_region_polygon`` parks the ring here and
returns a short summary, and ``filter_dives_by_region`` picks it up when no
explicit polygon is passed.

The agent clears this at the start of each query, alongside ToolState.
"""

from typing import List, Optional, Tuple


class GeoRegionState:
    """Class-level holder for the last region built during a query."""

    _ring: Optional[List[Tuple[float, float]]] = None
    _description: Optional[str] = None

    @classmethod
    def set_region(cls, ring: List[Tuple[float, float]], description: str = "") -> None:
        """Store a region ring of (lat, lon) vertices."""
        cls._ring = list(ring)
        cls._description = description

    @classmethod
    def get_region(cls) -> Optional[List[Tuple[float, float]]]:
        """Get the stored ring, or None if no region has been built."""
        return cls._ring

    @classmethod
    def get_description(cls) -> Optional[str]:
        """Human-readable description of the stored region."""
        return cls._description

    @classmethod
    def has_region(cls) -> bool:
        """Check whether a region is stored."""
        return cls._ring is not None

    @classmethod
    def clear(cls) -> None:
        """Clear the stored region. Call at the start of each new query."""
        cls._ring = None
        cls._description = None
