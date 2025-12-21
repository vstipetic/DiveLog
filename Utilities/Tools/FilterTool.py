"""
LangChain tools for filtering dives.

These tools wrap the existing FilterFunctions to provide
LangChain-compatible interfaces with Pydantic validation.
"""

from typing import List, Optional, Type
from datetime import datetime
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Schemas.ToolOutputs import FilterResult, DiveSummary
from Utilities.FilterFunctions import (
    dive_was_deeper_than,
    dive_was_shallower_than,
    dive_was_longer_than,
    dive_was_shorter_than,
    dive_was_after_date,
    dive_was_before_date,
    dive_had_buddy,
    dive_was_at_location,
)


class FilterDivesByDepthInput(BaseModel):
    """Input schema for filtering dives by depth."""

    min_depth: float = Field(
        description="Minimum depth in meters. Dives must be deeper than this value."
    )
    max_depth: Optional[float] = Field(
        None,
        description="Maximum depth in meters (optional). Dives must be shallower than this value."
    )


class FilterDivesByDepthTool(BaseTool):
    """Filter dives by depth range."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_depth"
    description: str = (
        "Filter dives by depth range. Returns dives where maximum depth is within "
        "the specified range. Use min_depth to find dives deeper than a threshold. "
        "Optionally use max_depth to limit the upper bound."
    )
    args_schema: Type[BaseModel] = FilterDivesByDepthInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(
        self,
        min_depth: float,
        max_depth: Optional[float] = None
    ) -> str:
        """Filter dives by depth and return formatted result."""
        # Apply depth filter
        filtered = [d for d in self.dives if dive_was_deeper_than(d, min_depth)]

        if max_depth is not None:
            filtered = [d for d in filtered if dive_was_shallower_than(d, max_depth)]

        # Build result
        result = self._build_filter_result(filtered)
        return self._format_result(result, min_depth, max_depth)

    def _build_filter_result(self, filtered: List[Dive]) -> FilterResult:
        """Build FilterResult from filtered dives."""
        if not filtered:
            return FilterResult(
                matching_dives=[],
                total_count=0,
                depth_range=None,
                date_range=None,
                average_depth=None
            )

        summaries = [
            DiveSummary.from_dive(d, f"dive_{i}")
            for i, d in enumerate(filtered)
        ]

        depths = [s.max_depth_meters for s in summaries]
        dates = [s.date for s in summaries]

        return FilterResult(
            matching_dives=summaries,
            total_count=len(summaries),
            depth_range=(min(depths), max(depths)),
            date_range=(min(dates), max(dates)),
            average_depth=sum(depths) / len(depths)
        )

    def _format_result(
        self,
        result: FilterResult,
        min_depth: float,
        max_depth: Optional[float]
    ) -> str:
        """Format result as a readable string for the agent."""
        if result.total_count == 0:
            if max_depth:
                return f"No dives found between {min_depth}m and {max_depth}m depth."
            return f"No dives found deeper than {min_depth}m."

        lines = [f"Found {result.total_count} dives:"]

        if max_depth:
            lines.append(f"- Depth range filter: {min_depth}m to {max_depth}m")
        else:
            lines.append(f"- Minimum depth filter: {min_depth}m")

        lines.append(f"- Actual depth range: {result.depth_range[0]:.1f}m to {result.depth_range[1]:.1f}m")
        lines.append(f"- Average max depth: {result.average_depth:.1f}m")
        lines.append(f"- Date range: {result.date_range[0].strftime('%Y-%m-%d')} to {result.date_range[1].strftime('%Y-%m-%d')}")

        # List first few dives
        lines.append("\nDive summaries:")
        for dive in result.matching_dives[:5]:
            lines.append(
                f"  - {dive.date.strftime('%Y-%m-%d')}: {dive.max_depth_meters:.1f}m, "
                f"{dive.duration_minutes:.0f}min at {dive.location}"
            )

        if result.total_count > 5:
            lines.append(f"  ... and {result.total_count - 5} more dives")

        return "\n".join(lines)


class FilterDivesByDateInput(BaseModel):
    """Input schema for filtering dives by date range."""

    start_date: str = Field(
        description="Start date in YYYY-MM-DD format. Dives must be after this date."
    )
    end_date: Optional[str] = Field(
        None,
        description="End date in YYYY-MM-DD format (optional). Dives must be before this date."
    )


class FilterDivesByDateTool(BaseTool):
    """Filter dives by date range."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_date"
    description: str = (
        "Filter dives by date range. Use start_date to find dives after a specific date. "
        "Optionally use end_date to limit the date range. Dates should be in YYYY-MM-DD format."
    )
    args_schema: Type[BaseModel] = FilterDivesByDateInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(
        self,
        start_date: str,
        end_date: Optional[str] = None
    ) -> str:
        """Filter dives by date and return formatted result."""
        # Parse dates
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            return f"Invalid start_date format: {start_date}. Use YYYY-MM-DD format."

        end_dt = None
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                return f"Invalid end_date format: {end_date}. Use YYYY-MM-DD format."

        # Apply date filter
        filtered = [d for d in self.dives if dive_was_after_date(d, start_dt)]

        if end_dt:
            filtered = [d for d in filtered if dive_was_before_date(d, end_dt)]

        # Build and format result
        result = self._build_filter_result(filtered)
        return self._format_result(result, start_date, end_date)

    def _build_filter_result(self, filtered: List[Dive]) -> FilterResult:
        """Build FilterResult from filtered dives."""
        if not filtered:
            return FilterResult(matching_dives=[], total_count=0)

        summaries = [
            DiveSummary.from_dive(d, f"dive_{i}")
            for i, d in enumerate(filtered)
        ]

        depths = [s.max_depth_meters for s in summaries]
        dates = [s.date for s in summaries]

        return FilterResult(
            matching_dives=summaries,
            total_count=len(summaries),
            depth_range=(min(depths), max(depths)) if depths else None,
            date_range=(min(dates), max(dates)) if dates else None,
            average_depth=sum(depths) / len(depths) if depths else None
        )

    def _format_result(
        self,
        result: FilterResult,
        start_date: str,
        end_date: Optional[str]
    ) -> str:
        """Format result as a readable string."""
        if result.total_count == 0:
            if end_date:
                return f"No dives found between {start_date} and {end_date}."
            return f"No dives found after {start_date}."

        lines = [f"Found {result.total_count} dives:"]

        if end_date:
            lines.append(f"- Date filter: {start_date} to {end_date}")
        else:
            lines.append(f"- After date: {start_date}")

        if result.average_depth:
            lines.append(f"- Average max depth: {result.average_depth:.1f}m")

        lines.append("\nDive summaries:")
        for dive in result.matching_dives[:5]:
            lines.append(
                f"  - {dive.date.strftime('%Y-%m-%d')}: {dive.max_depth_meters:.1f}m, "
                f"{dive.duration_minutes:.0f}min at {dive.location}"
            )

        if result.total_count > 5:
            lines.append(f"  ... and {result.total_count - 5} more dives")

        return "\n".join(lines)


class FilterDivesByDurationInput(BaseModel):
    """Input schema for filtering dives by duration."""

    min_duration_minutes: float = Field(
        description="Minimum duration in minutes. Dives must be longer than this."
    )
    max_duration_minutes: Optional[float] = Field(
        None,
        description="Maximum duration in minutes (optional). Dives must be shorter than this."
    )


class FilterDivesByDurationTool(BaseTool):
    """Filter dives by duration."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_duration"
    description: str = (
        "Filter dives by duration. Use min_duration_minutes to find dives longer than "
        "a threshold. Optionally use max_duration_minutes to limit the upper bound."
    )
    args_schema: Type[BaseModel] = FilterDivesByDurationInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(
        self,
        min_duration_minutes: float,
        max_duration_minutes: Optional[float] = None
    ) -> str:
        """Filter dives by duration and return formatted result."""
        min_seconds = min_duration_minutes * 60

        filtered = [d for d in self.dives if dive_was_longer_than(d, min_seconds)]

        if max_duration_minutes is not None:
            max_seconds = max_duration_minutes * 60
            filtered = [d for d in filtered if dive_was_shorter_than(d, max_seconds)]

        if not filtered:
            if max_duration_minutes:
                return f"No dives found between {min_duration_minutes} and {max_duration_minutes} minutes."
            return f"No dives found longer than {min_duration_minutes} minutes."

        summaries = [
            DiveSummary.from_dive(d, f"dive_{i}")
            for i, d in enumerate(filtered)
        ]

        lines = [f"Found {len(summaries)} dives:"]
        if max_duration_minutes:
            lines.append(f"- Duration filter: {min_duration_minutes} to {max_duration_minutes} minutes")
        else:
            lines.append(f"- Minimum duration: {min_duration_minutes} minutes")

        durations = [s.duration_minutes for s in summaries]
        lines.append(f"- Duration range: {min(durations):.0f} to {max(durations):.0f} minutes")
        lines.append(f"- Average duration: {sum(durations)/len(durations):.0f} minutes")

        lines.append("\nDive summaries:")
        for dive in summaries[:5]:
            lines.append(
                f"  - {dive.date.strftime('%Y-%m-%d')}: {dive.duration_minutes:.0f}min, "
                f"{dive.max_depth_meters:.1f}m at {dive.location}"
            )

        if len(summaries) > 5:
            lines.append(f"  ... and {len(summaries) - 5} more dives")

        return "\n".join(lines)


class FilterDivesByBuddyInput(BaseModel):
    """Input schema for filtering dives by buddy."""

    buddy_name: str = Field(
        description="Name of the dive buddy to search for (partial match, case-insensitive)"
    )


class FilterDivesByBuddyTool(BaseTool):
    """Filter dives by dive buddy."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_buddy"
    description: str = (
        "Filter dives by dive buddy name. Searches for partial matches "
        "(case-insensitive). Use this to find dives with a specific person."
    )
    args_schema: Type[BaseModel] = FilterDivesByBuddyInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(self, buddy_name: str) -> str:
        """Filter dives by buddy and return formatted result."""
        filtered = [d for d in self.dives if dive_had_buddy(d, buddy_name)]

        if not filtered:
            return f"No dives found with buddy matching '{buddy_name}'."

        summaries = [
            DiveSummary.from_dive(d, f"dive_{i}")
            for i, d in enumerate(filtered)
        ]

        lines = [f"Found {len(summaries)} dives with buddy matching '{buddy_name}':"]

        # Show unique buddies found
        buddies = set(s.buddy for s in summaries if s.buddy)
        if buddies:
            lines.append(f"- Matching buddies: {', '.join(buddies)}")

        lines.append("\nDive summaries:")
        for dive in summaries[:5]:
            lines.append(
                f"  - {dive.date.strftime('%Y-%m-%d')}: {dive.max_depth_meters:.1f}m, "
                f"{dive.duration_minutes:.0f}min with {dive.buddy or 'Unknown'}"
            )

        if len(summaries) > 5:
            lines.append(f"  ... and {len(summaries) - 5} more dives")

        return "\n".join(lines)


class FilterDivesByLocationInput(BaseModel):
    """Input schema for filtering dives by location."""

    location_name: str = Field(
        description="Location name to search for (partial match, case-insensitive)"
    )


class FilterDivesByLocationTool(BaseTool):
    """Filter dives by location."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_location"
    description: str = (
        "Filter dives by location name. Searches for partial matches "
        "(case-insensitive). Use this to find dives at a specific site."
    )
    args_schema: Type[BaseModel] = FilterDivesByLocationInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(self, location_name: str) -> str:
        """Filter dives by location and return formatted result."""
        filtered = [d for d in self.dives if dive_was_at_location(d, location_name)]

        if not filtered:
            return f"No dives found at location matching '{location_name}'."

        summaries = [
            DiveSummary.from_dive(d, f"dive_{i}")
            for i, d in enumerate(filtered)
        ]

        lines = [f"Found {len(summaries)} dives at location matching '{location_name}':"]

        # Show unique locations found
        locations = set(s.location for s in summaries)
        if locations:
            lines.append(f"- Matching locations: {', '.join(locations)}")

        depths = [s.max_depth_meters for s in summaries]
        lines.append(f"- Depth range: {min(depths):.1f}m to {max(depths):.1f}m")
        lines.append(f"- Average depth: {sum(depths)/len(depths):.1f}m")

        lines.append("\nDive summaries:")
        for dive in summaries[:5]:
            lines.append(
                f"  - {dive.date.strftime('%Y-%m-%d')}: {dive.max_depth_meters:.1f}m, "
                f"{dive.duration_minutes:.0f}min"
            )

        if len(summaries) > 5:
            lines.append(f"  ... and {len(summaries) - 5} more dives")

        return "\n".join(lines)
