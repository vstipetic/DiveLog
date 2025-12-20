"""
Pydantic input schemas for LangChain tools.

These models define the expected input parameters for each tool,
providing validation and clear descriptions for the LLM.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DepthFilterInput(BaseModel):
    """Filter dives by depth range."""

    min_depth_meters: float = Field(
        gt=0,
        description="Minimum depth in meters"
    )
    max_depth_meters: Optional[float] = Field(
        None,
        ge=0,
        description="Maximum depth in meters (optional)"
    )


class DateRangeInput(BaseModel):
    """Filter dives by date range."""

    start_date: datetime = Field(
        description="Start date (inclusive)"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="End date (inclusive, optional)"
    )


class GearFilterInput(BaseModel):
    """Filter dives by gear used."""

    gear_name: str = Field(
        description="Name of gear item"
    )
    gear_type: Optional[str] = Field(
        None,
        description="Type: mask, suit, gloves, boots, bcd, fins"
    )


class DurationFilterInput(BaseModel):
    """Filter dives by duration."""

    min_duration_minutes: float = Field(
        gt=0,
        description="Minimum duration in minutes"
    )
    max_duration_minutes: Optional[float] = Field(
        None,
        description="Maximum duration in minutes (optional)"
    )


class BuddyFilterInput(BaseModel):
    """Filter dives by buddy."""

    buddy_name: str = Field(
        description="Name of dive buddy (partial match supported)"
    )


class LocationFilterInput(BaseModel):
    """Filter dives by location."""

    location_name: str = Field(
        description="Location name (partial match supported)"
    )


class DepthThresholdInput(BaseModel):
    """Input for depth threshold calculations."""

    depth_threshold_meters: float = Field(
        gt=0,
        description="Depth threshold in meters"
    )


class StatisticTypeInput(BaseModel):
    """Input for selecting a statistic type to calculate."""

    stat_type: str = Field(
        description="Type of statistic: average_depth, max_depth, min_depth, "
                   "total_dive_time, dive_count, average_duration, "
                   "longest_dive, shortest_dive, deepest_dive, shallowest_dive, "
                   "average_temperature"
    )


class SearchQueryInput(BaseModel):
    """Input for searching dives by text."""

    query: str = Field(
        description="Search query text"
    )
    search_field: str = Field(
        description="Field to search: location, buddy, description"
    )
