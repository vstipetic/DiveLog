"""
Pydantic models for agent responses.

These models provide structured representations of dive data
optimized for agent communication and LLM understanding.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
from Utilities.Schemas.ToolOutputs import DiveSummary


class DepthProfile(BaseModel):
    """Simplified depth profile for agent responses."""

    timestamps_seconds: List[float] = Field(
        description="Time points in seconds from dive start"
    )
    depths_meters: List[float] = Field(
        description="Depth at each time point in meters"
    )
    max_depth: float = Field(
        description="Maximum depth reached in meters"
    )
    average_depth: float = Field(
        description="Average depth during the dive in meters"
    )

    @classmethod
    def from_dive(cls, dive: Any) -> 'DepthProfile':
        """Create DepthProfile from a Dive object.

        Args:
            dive: attrs-based Dive object

        Returns:
            DepthProfile instance
        """
        depths = dive.timeline.depths or []
        timestamps = dive.timeline.timestamps or []

        return cls(
            timestamps_seconds=timestamps,
            depths_meters=depths,
            max_depth=max(depths) if depths else 0.0,
            average_depth=sum(depths) / len(depths) if depths else 0.0
        )


class DiveDetails(BaseModel):
    """Extended dive information for detailed queries."""

    summary: DiveSummary = Field(
        description="Basic dive summary information"
    )
    depth_profile: Optional[DepthProfile] = Field(
        None,
        description="Detailed depth profile data"
    )
    gas_type: str = Field(
        description="Type of breathing gas (air, nitrox, trimix)"
    )
    start_pressure: int = Field(
        description="Starting tank pressure in bar"
    )
    end_pressure: int = Field(
        description="Ending tank pressure in bar"
    )
    air_consumption: Optional[float] = Field(
        None,
        description="Air consumption in bar per minute (if calculable)"
    )
    buddy: Optional[str] = Field(
        None,
        description="Dive buddy name"
    )
    divemaster: Optional[str] = Field(
        None,
        description="Divemaster name"
    )
    group_members: Optional[List[str]] = Field(
        None,
        description="Other group members on the dive"
    )
    min_temperature: Optional[float] = Field(
        None,
        description="Minimum water temperature in Celsius"
    )
    max_temperature: Optional[float] = Field(
        None,
        description="Maximum water temperature in Celsius"
    )

    @classmethod
    def from_dive(cls, dive: Any, dive_id: str, include_profile: bool = False) -> 'DiveDetails':
        """Create DiveDetails from a Dive object.

        Args:
            dive: attrs-based Dive object
            dive_id: Unique identifier for this dive
            include_profile: Whether to include the full depth profile

        Returns:
            DiveDetails instance
        """
        summary = DiveSummary.from_dive(dive, dive_id)
        profile = DepthProfile.from_dive(dive) if include_profile else None

        # Calculate air consumption
        duration_minutes = dive.basics.duration / 60
        pressure_used = dive.gasses.start_pressure - dive.gasses.end_pressure
        air_consumption = pressure_used / duration_minutes if duration_minutes > 0 else None

        # Temperature range
        temps = dive.timeline.temperature or []
        min_temp = min(temps) if temps else None
        max_temp = max(temps) if temps else None

        # Group members
        group = list(dive.people.group) if dive.people.group else None

        return cls(
            summary=summary,
            depth_profile=profile,
            gas_type=dive.gasses.gas,
            start_pressure=dive.gasses.start_pressure,
            end_pressure=dive.gasses.end_pressure,
            air_consumption=air_consumption,
            buddy=dive.people.buddy,
            divemaster=dive.people.divemaster,
            group_members=group,
            min_temperature=min_temp,
            max_temperature=max_temp
        )


class QueryResponse(BaseModel):
    """Standardized response format for agent."""

    success: bool = Field(
        description="Whether the query was processed successfully"
    )
    message: str = Field(
        description="Human-readable response message"
    )
    data: Optional[dict] = Field(
        None,
        description="Structured data from the query (if applicable)"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if query failed"
    )

    @classmethod
    def success_response(cls, message: str, data: dict = None) -> 'QueryResponse':
        """Create a successful query response."""
        return cls(success=True, message=message, data=data)

    @classmethod
    def error_response(cls, error: str) -> 'QueryResponse':
        """Create an error query response."""
        return cls(success=False, message="Query failed", error=error)
