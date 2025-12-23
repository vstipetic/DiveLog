"""
LangChain tools for filtering dives.

These tools wrap the existing FilterFunctions to provide
LangChain-compatible interfaces with Pydantic validation.

IMPORTANT: All filter tools store their results in ToolState, making
the filtered dives available to subsequent statistics tools.
"""

from typing import List, Optional, Type
from datetime import datetime, time
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Schemas.ToolOutputs import FilterResult, DiveSummary
from Utilities.Tools.ToolState import ToolState
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


# =============================================================================
# DEPTH FILTER
# =============================================================================

class FilterDivesByDepthInput(BaseModel):
    """Input schema for filtering dives by depth."""

    min_depth: Optional[float] = Field(
        None,
        description="Minimum depth in meters (inclusive). Dives must be at least this deep."
    )
    max_depth: Optional[float] = Field(
        None,
        description="Maximum depth in meters (inclusive). Dives must be no deeper than this."
    )


class FilterDivesByDepthTool(BaseTool):
    """Filter dives by depth range."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_depth"
    description: str = (
        "Filter dives by depth range. Provide min_depth to find dives deeper than a threshold, "
        "max_depth to find shallower dives, or both for a range. "
        "Examples: min_depth=20 finds dives >=20m; max_depth=15 finds dives <=15m; "
        "min_depth=10, max_depth=20 finds dives between 10-20m. "
        "The filtered results are automatically available for subsequent statistics calculations."
    )
    args_schema: Type[BaseModel] = FilterDivesByDepthInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(
        self,
        min_depth: Optional[float] = None,
        max_depth: Optional[float] = None
    ) -> str:
        """Filter dives by depth and return formatted result."""
        if min_depth is None and max_depth is None:
            return "Please provide at least min_depth or max_depth parameter."

        filtered = list(self.dives)

        # Apply depth filters
        if min_depth is not None:
            filtered = [d for d in filtered if dive_was_deeper_than(d, min_depth)]

        if max_depth is not None:
            filtered = [d for d in filtered if dive_was_shallower_than(d, max_depth)]

        # Store filtered dives in shared state for statistics tools
        if min_depth is not None and max_depth is not None:
            filter_desc = f"depth {min_depth}m-{max_depth}m"
        elif min_depth is not None:
            filter_desc = f"depth >={min_depth}m"
        else:
            filter_desc = f"depth <={max_depth}m"
        ToolState.set_filtered_dives(filtered, filter_desc)

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
        min_depth: Optional[float],
        max_depth: Optional[float]
    ) -> str:
        """Format result as a readable string for the agent."""
        if result.total_count == 0:
            if min_depth is not None and max_depth is not None:
                return f"No dives found between {min_depth}m and {max_depth}m depth."
            elif min_depth is not None:
                return f"No dives found deeper than or equal to {min_depth}m."
            else:
                return f"No dives found shallower than or equal to {max_depth}m."

        lines = [f"Found {result.total_count} dives:"]

        if min_depth is not None and max_depth is not None:
            lines.append(f"- Depth range filter: {min_depth}m to {max_depth}m")
        elif min_depth is not None:
            lines.append(f"- Minimum depth filter: >={min_depth}m")
        else:
            lines.append(f"- Maximum depth filter: <={max_depth}m")

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


# =============================================================================
# DATE FILTER
# =============================================================================

class FilterDivesByDateInput(BaseModel):
    """Input schema for filtering dives by date range."""

    start_date: str = Field(
        description="Start date in YYYY-MM-DD format. Dives must be on or after this date."
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
        "Optionally use end_date to limit the date range. Dates should be in YYYY-MM-DD format. "
        "The filtered results are automatically available for subsequent statistics calculations."
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

        # Store filtered dives in shared state for statistics tools
        if end_date:
            filter_desc = f"date {start_date} to {end_date}"
        else:
            filter_desc = f"date after {start_date}"
        ToolState.set_filtered_dives(filtered, filter_desc)

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


# =============================================================================
# DURATION FILTER
# =============================================================================

class FilterDivesByDurationInput(BaseModel):
    """Input schema for filtering dives by duration."""

    min_duration_minutes: Optional[float] = Field(
        None,
        description="Minimum duration in minutes. Dives must be at least this long."
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
        "a threshold. Optionally use max_duration_minutes to limit the upper bound. "
        "The filtered results are automatically available for subsequent statistics calculations."
    )
    args_schema: Type[BaseModel] = FilterDivesByDurationInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(
        self,
        min_duration_minutes: Optional[float] = None,
        max_duration_minutes: Optional[float] = None
    ) -> str:
        """Filter dives by duration and return formatted result."""
        if min_duration_minutes is None and max_duration_minutes is None:
            return "Please provide at least min_duration_minutes or max_duration_minutes."

        filtered = list(self.dives)

        if min_duration_minutes is not None:
            min_seconds = min_duration_minutes * 60
            filtered = [d for d in filtered if dive_was_longer_than(d, min_seconds)]

        if max_duration_minutes is not None:
            max_seconds = max_duration_minutes * 60
            filtered = [d for d in filtered if dive_was_shorter_than(d, max_seconds)]

        # Store filtered dives in shared state for statistics tools
        if min_duration_minutes is not None and max_duration_minutes is not None:
            filter_desc = f"duration {min_duration_minutes}-{max_duration_minutes}min"
        elif min_duration_minutes is not None:
            filter_desc = f"duration >={min_duration_minutes}min"
        else:
            filter_desc = f"duration <={max_duration_minutes}min"
        ToolState.set_filtered_dives(filtered, filter_desc)

        if not filtered:
            if min_duration_minutes is not None and max_duration_minutes is not None:
                return f"No dives found between {min_duration_minutes} and {max_duration_minutes} minutes."
            elif min_duration_minutes is not None:
                return f"No dives found longer than {min_duration_minutes} minutes."
            else:
                return f"No dives found shorter than {max_duration_minutes} minutes."

        summaries = [
            DiveSummary.from_dive(d, f"dive_{i}")
            for i, d in enumerate(filtered)
        ]

        lines = [f"Found {len(summaries)} dives:"]
        if min_duration_minutes is not None and max_duration_minutes is not None:
            lines.append(f"- Duration filter: {min_duration_minutes} to {max_duration_minutes} minutes")
        elif min_duration_minutes is not None:
            lines.append(f"- Minimum duration: {min_duration_minutes} minutes")
        else:
            lines.append(f"- Maximum duration: {max_duration_minutes} minutes")

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


# =============================================================================
# BUDDY FILTER
# =============================================================================

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
        "(case-insensitive). Use this to find dives with a specific person. "
        "The filtered results are automatically available for subsequent statistics calculations."
    )
    args_schema: Type[BaseModel] = FilterDivesByBuddyInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(self, buddy_name: str) -> str:
        """Filter dives by buddy and return formatted result."""
        filtered = [d for d in self.dives if dive_had_buddy(d, buddy_name)]

        # Store filtered dives in shared state for statistics tools
        ToolState.set_filtered_dives(filtered, f"buddy '{buddy_name}'")

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


# =============================================================================
# LOCATION FILTER
# =============================================================================

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
        "(case-insensitive). Use this to find dives at a specific site. "
        "The filtered results are automatically available for subsequent statistics calculations."
    )
    args_schema: Type[BaseModel] = FilterDivesByLocationInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(self, location_name: str) -> str:
        """Filter dives by location and return formatted result."""
        filtered = [d for d in self.dives if dive_was_at_location(d, location_name)]

        # Store filtered dives in shared state for statistics tools
        ToolState.set_filtered_dives(filtered, f"location '{location_name}'")

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


# =============================================================================
# START TIME FILTER (NEW)
# =============================================================================

class FilterDivesByStartTimeInput(BaseModel):
    """Input schema for filtering dives by start time of day."""

    start_after: Optional[str] = Field(
        None,
        description="Minimum start time in HH:MM format (24-hour). Dives must start at or after this time."
    )
    start_before: Optional[str] = Field(
        None,
        description="Maximum start time in HH:MM format (24-hour). Dives must start before this time."
    )


class FilterDivesByStartTimeTool(BaseTool):
    """Filter dives by time of day they started."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_start_time"
    description: str = (
        "Filter dives by the time of day they started. Use start_after to find dives "
        "that started at or after a specific time, start_before for dives before a time, "
        "or both for a time range. Times should be in HH:MM format (24-hour). "
        "Example: start_after='13:00', start_before='16:00' finds afternoon dives. "
        "The filtered results are automatically available for subsequent statistics calculations."
    )
    args_schema: Type[BaseModel] = FilterDivesByStartTimeInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(
        self,
        start_after: Optional[str] = None,
        start_before: Optional[str] = None
    ) -> str:
        """Filter dives by start time and return formatted result."""
        if start_after is None and start_before is None:
            return "Please provide at least start_after or start_before parameter."

        # Parse times
        after_time = None
        before_time = None

        if start_after:
            try:
                parts = start_after.split(":")
                after_time = time(int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                return f"Invalid start_after format: {start_after}. Use HH:MM format."

        if start_before:
            try:
                parts = start_before.split(":")
                before_time = time(int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                return f"Invalid start_before format: {start_before}. Use HH:MM format."

        # Filter dives
        filtered = []
        for dive in self.dives:
            dive_time = dive.basics.start_time.time()
            if after_time is not None and dive_time < after_time:
                continue
            if before_time is not None and dive_time >= before_time:
                continue
            filtered.append(dive)

        # Store filtered dives in shared state
        if start_after and start_before:
            filter_desc = f"start time {start_after}-{start_before}"
        elif start_after:
            filter_desc = f"start time >={start_after}"
        else:
            filter_desc = f"start time <{start_before}"
        ToolState.set_filtered_dives(filtered, filter_desc)

        if not filtered:
            if start_after and start_before:
                return f"No dives found starting between {start_after} and {start_before}."
            elif start_after:
                return f"No dives found starting at or after {start_after}."
            else:
                return f"No dives found starting before {start_before}."

        summaries = [
            DiveSummary.from_dive(d, f"dive_{i}")
            for i, d in enumerate(filtered)
        ]

        lines = [f"Found {len(summaries)} dives:"]
        if start_after and start_before:
            lines.append(f"- Start time filter: {start_after} to {start_before}")
        elif start_after:
            lines.append(f"- Start time filter: at or after {start_after}")
        else:
            lines.append(f"- Start time filter: before {start_before}")

        # Show start time distribution
        start_times = [d.basics.start_time.strftime("%H:%M") for d in filtered]
        lines.append(f"- Earliest start: {min(start_times)}")
        lines.append(f"- Latest start: {max(start_times)}")

        lines.append("\nDive summaries:")
        for i, dive in enumerate(summaries[:5]):
            start_str = filtered[i].basics.start_time.strftime("%H:%M")
            lines.append(
                f"  - {dive.date.strftime('%Y-%m-%d')} {start_str}: {dive.max_depth_meters:.1f}m, "
                f"{dive.duration_minutes:.0f}min"
            )

        if len(summaries) > 5:
            lines.append(f"  ... and {len(summaries) - 5} more dives")

        return "\n".join(lines)


# =============================================================================
# TEMPERATURE FILTER (NEW)
# =============================================================================

class FilterDivesByTemperatureInput(BaseModel):
    """Input schema for filtering dives by water temperature."""

    min_temp: Optional[float] = Field(
        None,
        description="Minimum average water temperature in Celsius."
    )
    max_temp: Optional[float] = Field(
        None,
        description="Maximum average water temperature in Celsius."
    )


class FilterDivesByTemperatureTool(BaseTool):
    """Filter dives by water temperature."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_temperature"
    description: str = (
        "Filter dives by average water temperature. Use min_temp to find warmer dives, "
        "max_temp to find colder dives, or both for a temperature range. "
        "Temperature is in Celsius. "
        "The filtered results are automatically available for subsequent statistics calculations."
    )
    args_schema: Type[BaseModel] = FilterDivesByTemperatureInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(
        self,
        min_temp: Optional[float] = None,
        max_temp: Optional[float] = None
    ) -> str:
        """Filter dives by temperature and return formatted result."""
        if min_temp is None and max_temp is None:
            return "Please provide at least min_temp or max_temp parameter."

        filtered = []
        for dive in self.dives:
            if not dive.timeline.temperature:
                continue
            avg_temp = sum(dive.timeline.temperature) / len(dive.timeline.temperature)
            if min_temp is not None and avg_temp < min_temp:
                continue
            if max_temp is not None and avg_temp > max_temp:
                continue
            filtered.append(dive)

        # Store filtered dives in shared state
        if min_temp is not None and max_temp is not None:
            filter_desc = f"temperature {min_temp}°C-{max_temp}°C"
        elif min_temp is not None:
            filter_desc = f"temperature >={min_temp}°C"
        else:
            filter_desc = f"temperature <={max_temp}°C"
        ToolState.set_filtered_dives(filtered, filter_desc)

        if not filtered:
            if min_temp is not None and max_temp is not None:
                return f"No dives found with temperature between {min_temp}°C and {max_temp}°C."
            elif min_temp is not None:
                return f"No dives found with temperature >= {min_temp}°C."
            else:
                return f"No dives found with temperature <= {max_temp}°C."

        summaries = [
            DiveSummary.from_dive(d, f"dive_{i}")
            for i, d in enumerate(filtered)
        ]

        # Calculate avg temps for display
        avg_temps = []
        for dive in filtered:
            if dive.timeline.temperature:
                avg_temps.append(sum(dive.timeline.temperature) / len(dive.timeline.temperature))

        lines = [f"Found {len(summaries)} dives:"]
        if min_temp is not None and max_temp is not None:
            lines.append(f"- Temperature filter: {min_temp}°C to {max_temp}°C")
        elif min_temp is not None:
            lines.append(f"- Minimum temperature: {min_temp}°C")
        else:
            lines.append(f"- Maximum temperature: {max_temp}°C")

        if avg_temps:
            lines.append(f"- Temperature range: {min(avg_temps):.1f}°C to {max(avg_temps):.1f}°C")
            lines.append(f"- Average temperature: {sum(avg_temps)/len(avg_temps):.1f}°C")

        lines.append("\nDive summaries:")
        for i, dive in enumerate(summaries[:5]):
            if filtered[i].timeline.temperature:
                temp = sum(filtered[i].timeline.temperature) / len(filtered[i].timeline.temperature)
                lines.append(
                    f"  - {dive.date.strftime('%Y-%m-%d')}: {temp:.1f}°C, {dive.max_depth_meters:.1f}m, "
                    f"{dive.duration_minutes:.0f}min"
                )

        if len(summaries) > 5:
            lines.append(f"  ... and {len(summaries) - 5} more dives")

        return "\n".join(lines)


# =============================================================================
# CNS LOAD FILTER (NEW)
# =============================================================================

class FilterDivesByCNSLoadInput(BaseModel):
    """Input schema for filtering dives by CNS oxygen toxicity load."""

    max_cns_load: float = Field(
        description="Maximum CNS load percentage. Filters dives where max CNS stayed below this value."
    )


class FilterDivesByCNSLoadTool(BaseTool):
    """Filter dives by CNS oxygen toxicity load."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_cns_load"
    description: str = (
        "Filter dives by maximum CNS (Central Nervous System) oxygen toxicity load. "
        "Returns dives where the maximum CNS load stayed below the specified percentage. "
        "Example: max_cns_load=50 finds dives where CNS never exceeded 50%. "
        "The filtered results are automatically available for subsequent statistics calculations."
    )
    args_schema: Type[BaseModel] = FilterDivesByCNSLoadInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(self, max_cns_load: float) -> str:
        """Filter dives by CNS load and return formatted result."""
        filtered = []
        for dive in self.dives:
            if not dive.timeline.cns_load:
                # Include dives without CNS data (assume safe)
                filtered.append(dive)
                continue
            max_cns = max(dive.timeline.cns_load)
            if max_cns <= max_cns_load:
                filtered.append(dive)

        # Store filtered dives in shared state
        ToolState.set_filtered_dives(filtered, f"CNS <={max_cns_load}%")

        if not filtered:
            return f"No dives found with max CNS load <= {max_cns_load}%."

        summaries = [
            DiveSummary.from_dive(d, f"dive_{i}")
            for i, d in enumerate(filtered)
        ]

        # Calculate CNS stats
        cns_values = []
        for dive in filtered:
            if dive.timeline.cns_load:
                cns_values.append(max(dive.timeline.cns_load))

        lines = [f"Found {len(summaries)} dives with max CNS <= {max_cns_load}%:"]

        if cns_values:
            lines.append(f"- CNS range: {min(cns_values):.1f}% to {max(cns_values):.1f}%")
            lines.append(f"- Average max CNS: {sum(cns_values)/len(cns_values):.1f}%")

        lines.append("\nDive summaries:")
        for i, dive in enumerate(summaries[:5]):
            cns_str = ""
            if filtered[i].timeline.cns_load:
                cns_str = f", CNS {max(filtered[i].timeline.cns_load):.0f}%"
            lines.append(
                f"  - {dive.date.strftime('%Y-%m-%d')}: {dive.max_depth_meters:.1f}m, "
                f"{dive.duration_minutes:.0f}min{cns_str}"
            )

        if len(summaries) > 5:
            lines.append(f"  ... and {len(summaries) - 5} more dives")

        return "\n".join(lines)


# =============================================================================
# GAS TYPE FILTER (NEW)
# =============================================================================

class FilterDivesByGasTypeInput(BaseModel):
    """Input schema for filtering dives by gas type."""

    gas_type: str = Field(
        description="Gas type: 'air', 'nitrox', or 'trimix'"
    )


class FilterDivesByGasTypeTool(BaseTool):
    """Filter dives by breathing gas type."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_gas_type"
    description: str = (
        "Filter dives by breathing gas type. Valid gas types: 'air', 'nitrox', 'trimix'. "
        "The filtered results are automatically available for subsequent statistics calculations."
    )
    args_schema: Type[BaseModel] = FilterDivesByGasTypeInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(self, gas_type: str) -> str:
        """Filter dives by gas type and return formatted result."""
        gas_type_lower = gas_type.lower().strip()
        valid_types = ['air', 'nitrox', 'trimix']

        if gas_type_lower not in valid_types:
            return f"Invalid gas type: {gas_type}. Valid types: {', '.join(valid_types)}"

        filtered = [d for d in self.dives if d.gasses.gas.lower() == gas_type_lower]

        # Store filtered dives in shared state
        ToolState.set_filtered_dives(filtered, f"gas type '{gas_type}'")

        if not filtered:
            return f"No dives found using {gas_type}."

        summaries = [
            DiveSummary.from_dive(d, f"dive_{i}")
            for i, d in enumerate(filtered)
        ]

        lines = [f"Found {len(summaries)} dives using {gas_type}:"]

        depths = [s.max_depth_meters for s in summaries]
        lines.append(f"- Depth range: {min(depths):.1f}m to {max(depths):.1f}m")
        lines.append(f"- Average depth: {sum(depths)/len(depths):.1f}m")

        lines.append("\nDive summaries:")
        for dive in summaries[:5]:
            lines.append(
                f"  - {dive.date.strftime('%Y-%m-%d')}: {dive.max_depth_meters:.1f}m, "
                f"{dive.duration_minutes:.0f}min at {dive.location}"
            )

        if len(summaries) > 5:
            lines.append(f"  ... and {len(summaries) - 5} more dives")

        return "\n".join(lines)


# =============================================================================
# DURATION AT DEPTH FILTER
# =============================================================================

class FilterDivesByDurationAtDepthInput(BaseModel):
    """Input schema for filtering dives by continuous time at depth."""

    min_depth: float = Field(
        description="Minimum depth in meters. Filters for time spent at or below this depth."
    )
    min_duration: float = Field(
        description="Minimum continuous duration in minutes at that depth."
    )


class FilterDivesByDurationAtDepthTool(BaseTool):
    """
    Filter dives by continuous time spent at or below a specific depth.

    This tool finds dives where the diver maintained a depth at or below
    the threshold for a continuous period of at least the specified duration.

    Example uses:
    - "Find dives where I spent at least 5 continuous minutes below 30m"
    - "Show dives with extended bottom time at 20+ meters"
    - "Which dives had me at 40m or deeper for 3+ minutes?"
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_duration_at_depth"
    description: str = (
        "Filter dives where the diver spent at least X continuous minutes "
        "at or below a specific depth. Useful for finding dives with extended "
        "bottom time at depth. Provide min_depth (meters) and min_duration (minutes). "
        "The filtered results are automatically available for subsequent statistics calculations."
    )
    args_schema: Type[BaseModel] = FilterDivesByDurationAtDepthInput

    dives: List[Dive] = Field(default_factory=list)

    def _has_continuous_time_at_depth(
        self, dive: Dive, depth: float, duration_minutes: float
    ) -> bool:
        """
        Check if a dive has continuous time at or below the specified depth.

        Args:
            dive: Dive object to check
            depth: Minimum depth threshold in meters
            duration_minutes: Required continuous duration in minutes

        Returns:
            True if dive has the required continuous time at depth
        """
        if not dive.timeline.depths or not dive.timeline.timestamps:
            return False

        if len(dive.timeline.depths) != len(dive.timeline.timestamps):
            return False

        current_streak_seconds = 0.0
        duration_seconds = duration_minutes * 60

        for i in range(len(dive.timeline.depths) - 1):
            if dive.timeline.depths[i] >= depth:
                # Currently at or below target depth, add time to streak
                time_delta = dive.timeline.timestamps[i + 1] - dive.timeline.timestamps[i]
                current_streak_seconds += time_delta
                if current_streak_seconds >= duration_seconds:
                    return True
            else:
                # Above target depth, reset streak
                current_streak_seconds = 0.0

        return False

    def _run(self, min_depth: float, min_duration: float) -> str:
        """Filter dives by continuous time at depth."""
        if not self.dives:
            return "No dives available to filter."

        filtered = [
            dive for dive in self.dives
            if self._has_continuous_time_at_depth(dive, min_depth, min_duration)
        ]

        filter_desc = f"at least {min_duration} min continuous at {min_depth}m+"
        ToolState.set_filtered_dives(filtered, filter_desc)

        if not filtered:
            return (
                f"No dives found with at least {min_duration} continuous minutes "
                f"at or below {min_depth}m."
            )

        # Build summary
        lines = [
            f"Found {len(filtered)} dive(s) with at least {min_duration} "
            f"continuous minutes at or below {min_depth}m:",
            ""
        ]

        for dive in filtered[:10]:  # Show first 10
            date_str = dive.basics.start_time.strftime("%Y-%m-%d")
            location = dive.location.name if dive.location.name else "Unknown location"
            max_depth = max(dive.timeline.depths) if dive.timeline.depths else 0
            duration_min = dive.basics.duration / 60
            lines.append(
                f"  - {date_str} at {location}: {max_depth:.1f}m max, "
                f"{duration_min:.0f} min total"
            )

        if len(filtered) > 10:
            lines.append(f"  ... and {len(filtered) - 10} more")

        return "\n".join(lines)


# =============================================================================
# LABEL FILTERED DIVES (for scatter plot groupings)
# =============================================================================

class LabelFilteredDivesInput(BaseModel):
    """Input schema for labeling filtered dives."""

    label: str = Field(
        description="Label to assign to the currently filtered dives. "
                   "Use descriptive names like 'Summer', 'Deep dives', '2024 dives', etc."
    )


class LabelFilteredDivesTool(BaseTool):
    """
    Assign a label to the currently filtered dives for use in grouped scatter plots.

    This tool allows building custom groupings for scatter plots:
    1. Filter dives (e.g., by date for summer months)
    2. Label them (e.g., "Summer")
    3. Filter again (e.g., fall months)
    4. Label them (e.g., "Fall")
    5. Call scatter plot with use_labeled_groups=True

    Labels are cumulative until cleared (at the start of each new query).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "label_filtered_dives"
    description: str = (
        "Assign a label to the currently filtered dives for use in grouped scatter plots. "
        "Use this after filtering to create custom groupings (seasons, depth bands, etc.). "
        "Workflow: (1) filter → (2) label → (3) filter again → (4) label again → "
        "(5) plot_scatter with use_labeled_groups=True. "
        "Labels accumulate across calls until a new query starts."
    )
    args_schema: Type[BaseModel] = LabelFilteredDivesInput

    def _run(self, label: str) -> str:
        """Store the currently filtered dives with the given label."""
        if not ToolState.has_filtered_dives():
            return (
                "No filtered dives to label. First apply a filter "
                "(e.g., filter_dives_by_date) then call this tool."
            )

        dives = ToolState.get_filtered_dives()
        ToolState.add_labeled_group(label, dives)

        # Report existing groups
        groups = ToolState.get_labeled_groups()
        group_summary = ", ".join(f"'{k}' ({len(v)} dives)" for k, v in groups.items())

        return (
            f"Labeled {len(dives)} dives as '{label}'. "
            f"Current groups: {group_summary}. "
            f"Use plot_scatter with use_labeled_groups=True to visualize."
        )