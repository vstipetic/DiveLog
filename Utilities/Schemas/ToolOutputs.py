"""
Pydantic output schemas for LangChain tools.

These models define the structured output from tools,
enabling consistent responses and easy serialization.
"""

from pydantic import BaseModel, Field
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime


class DiveSummary(BaseModel):
    """Agent-friendly dive summary (not full Dive object)."""

    dive_id: str = Field(description="Unique identifier for the dive")
    date: datetime = Field(description="Date and time of the dive")
    max_depth_meters: float = Field(description="Maximum depth reached in meters")
    duration_minutes: float = Field(description="Dive duration in minutes")
    location: str = Field(description="Dive location name")
    buddy: Optional[str] = Field(None, description="Dive buddy name")

    @classmethod
    def from_dive(cls, dive: Any, dive_id: str) -> 'DiveSummary':
        """Convert attrs Dive to Pydantic DiveSummary.

        Args:
            dive: attrs-based Dive object
            dive_id: Unique identifier for this dive

        Returns:
            Pydantic DiveSummary model
        """
        max_depth = max(dive.timeline.depths) if dive.timeline.depths else 0.0

        return cls(
            dive_id=dive_id,
            date=dive.basics.start_time,
            max_depth_meters=max_depth,
            duration_minutes=dive.basics.duration / 60,
            location=dive.location.name or "Unknown",
            buddy=dive.people.buddy
        )


class FilterResult(BaseModel):
    """Results from filtering operation with metadata."""

    matching_dives: List[DiveSummary] = Field(
        default_factory=list,
        description="List of dives matching the filter criteria"
    )
    total_count: int = Field(
        description="Total number of matching dives"
    )
    depth_range: Optional[Tuple[float, float]] = Field(
        None,
        description="(min_depth, max_depth) in meters of matching dives"
    )
    date_range: Optional[Tuple[datetime, datetime]] = Field(
        None,
        description="(earliest, latest) dive date of matching dives"
    )
    average_depth: Optional[float] = Field(
        None,
        description="Average max depth of matching dives in meters"
    )

    model_config = {"arbitrary_types_allowed": True}


class StatisticsResult(BaseModel):
    """Results from statistics calculation."""

    stat_type: str = Field(
        description="Type of statistic calculated"
    )
    value: float = Field(
        description="The calculated statistic value"
    )
    unit: str = Field(
        description="Unit of measurement (meters, minutes, dives, celsius, etc.)"
    )
    breakdown: Optional[Dict[str, float]] = Field(
        None,
        description="For grouped statistics (e.g., by year, month, location)"
    )
    context: Optional[str] = Field(
        None,
        description="Additional context about the statistic"
    )


class GearSummary(BaseModel):
    """Agent-friendly gear summary."""

    gear_id: str = Field(description="Unique identifier for the gear")
    name: str = Field(description="Gear item name")
    gear_type: str = Field(description="Type: mask, suit, gloves, boots, bcd, fins")
    total_dives: int = Field(description="Number of dives with this gear")
    total_dive_time_minutes: int = Field(description="Total underwater time in minutes")
    is_rental: bool = Field(False, description="Whether this is rental gear")

    @classmethod
    def from_gear(cls, gear: Any, gear_id: str, gear_type: str) -> 'GearSummary':
        """Convert attrs Gear to Pydantic GearSummary.

        Args:
            gear: attrs-based Gear object
            gear_id: Unique identifier for this gear
            gear_type: Type of gear (mask, suit, etc.)

        Returns:
            Pydantic GearSummary model
        """
        return cls(
            gear_id=gear_id,
            name=gear.name,
            gear_type=gear_type,
            total_dives=gear.number_of_dives,
            total_dive_time_minutes=gear.total_dive_time,
            is_rental=gear.is_rental
        )
