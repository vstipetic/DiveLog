"""
LangChain tool for searching dives.

This tool provides text-based search capabilities for finding dives
by location, buddy, or description.

IMPORTANT: Search tools store their results in ToolState, making
the found dives available to subsequent statistics tools.
"""

from typing import List, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Schemas.ToolOutputs import FilterResult, DiveSummary
from Utilities.Tools.ToolState import ToolState


class SearchDivesInput(BaseModel):
    """Input schema for searching dives."""

    query: str = Field(
        description="Search query text (case-insensitive, partial match)"
    )
    search_field: str = Field(
        description="Field to search in: 'location', 'buddy', or 'description'"
    )


class SearchDivesTool(BaseTool):
    """Search dives by text in various fields.

    This tool automatically stores search results in ToolState, making
    them available for subsequent statistics calculations.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "search_dives"
    description: str = (
        "Search dives by text query in location, buddy, or description fields. "
        "Use search_field to specify which field to search. "
        "The search is case-insensitive and supports partial matches. "
        "The search results are automatically available for subsequent statistics calculations."
    )
    args_schema: Type[BaseModel] = SearchDivesInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(self, query: str, search_field: str) -> str:
        """Search dives and return formatted result."""
        search_field = search_field.lower()

        if search_field not in ["location", "buddy", "description"]:
            return f"Invalid search_field: {search_field}. Use 'location', 'buddy', or 'description'."

        query_lower = query.lower()
        filtered = []

        for dive in self.dives:
            if search_field == "location":
                if dive.location.name and query_lower in dive.location.name.lower():
                    filtered.append(dive)
            elif search_field == "buddy":
                if dive.people.buddy and query_lower in dive.people.buddy.lower():
                    filtered.append(dive)
            elif search_field == "description":
                if dive.location.description and query_lower in dive.location.description.lower():
                    filtered.append(dive)

        # Store search results in shared state for statistics tools
        ToolState.set_filtered_dives(filtered, f"search '{query}' in {search_field}")

        if not filtered:
            return f"No dives found with '{query}' in {search_field} field."

        return self._format_result(filtered, query, search_field)

    def _format_result(
        self,
        filtered: List[Dive],
        query: str,
        search_field: str
    ) -> str:
        """Format search results as a readable string."""
        summaries = [
            DiveSummary.from_dive(d, f"dive_{i}")
            for i, d in enumerate(filtered)
        ]

        lines = [f"Found {len(summaries)} dives with '{query}' in {search_field}:"]

        # Show unique values found in the searched field
        if search_field == "location":
            locations = set(s.location for s in summaries)
            lines.append(f"- Matching locations: {', '.join(locations)}")
        elif search_field == "buddy":
            buddies = set(s.buddy for s in summaries if s.buddy)
            lines.append(f"- Matching buddies: {', '.join(buddies)}")

        lines.append("\nDive summaries:")
        for dive in summaries[:5]:
            buddy_str = f" with {dive.buddy}" if dive.buddy else ""
            lines.append(
                f"  - {dive.date.strftime('%Y-%m-%d')}: {dive.max_depth_meters:.1f}m, "
                f"{dive.duration_minutes:.0f}min at {dive.location}{buddy_str}"
            )

        if len(summaries) > 5:
            lines.append(f"  ... and {len(summaries) - 5} more dives")

        return "\n".join(lines)


class GetDiveSummaryInput(BaseModel):
    """Input schema for getting a dive summary."""

    dive_index: int = Field(
        description="Index of the dive to get details for (0-based)"
    )


class GetDiveSummaryTool(BaseTool):
    """Get detailed summary of a specific dive."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "get_dive_summary"
    description: str = (
        "Get detailed information about a specific dive by its index. "
        "Use this after filtering or searching to get more details about a particular dive."
    )
    args_schema: Type[BaseModel] = GetDiveSummaryInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(self, dive_index: int) -> str:
        """Get dive summary and return formatted result."""
        if dive_index < 0 or dive_index >= len(self.dives):
            return f"Invalid dive index: {dive_index}. Valid range: 0 to {len(self.dives) - 1}"

        dive = self.dives[dive_index]

        # Build detailed summary
        lines = [f"Dive #{dive_index} Details:"]
        lines.append(f"- Date: {dive.basics.start_time.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"- Duration: {dive.basics.duration / 60:.0f} minutes")

        if dive.timeline.depths:
            max_depth = max(dive.timeline.depths)
            avg_depth = sum(dive.timeline.depths) / len(dive.timeline.depths)
            lines.append(f"- Max Depth: {max_depth:.1f}m")
            lines.append(f"- Average Depth: {avg_depth:.1f}m")

        lines.append(f"- Location: {dive.location.name or 'Unknown'}")

        if dive.location.description:
            lines.append(f"- Description: {dive.location.description}")

        lines.append(f"- Buddy: {dive.people.buddy or 'Not specified'}")

        if dive.people.divemaster:
            lines.append(f"- Divemaster: {dive.people.divemaster}")

        if dive.people.group:
            lines.append(f"- Group: {', '.join(dive.people.group)}")

        lines.append(f"- Gas: {dive.gasses.gas}")
        lines.append(f"- Tank Pressure: {dive.gasses.start_pressure} -> {dive.gasses.end_pressure} bar")

        if dive.gasses.start_pressure > 0 and dive.gasses.end_pressure >= 0:
            consumed = dive.gasses.start_pressure - dive.gasses.end_pressure
            duration_min = dive.basics.duration / 60
            if duration_min > 0:
                rate = consumed / duration_min
                lines.append(f"- Air Consumption: {rate:.1f} bar/minute")

        if dive.timeline.temperature:
            min_temp = min(dive.timeline.temperature)
            max_temp = max(dive.timeline.temperature)
            lines.append(f"- Temperature: {min_temp}°C to {max_temp}°C")

        if dive.gear.suit:
            lines.append(f"- Suit: {dive.gear.suit.name}")

        if dive.gear.weights:
            lines.append(f"- Weights: {dive.gear.weights}kg")

        return "\n".join(lines)


class ListAllDivesInput(BaseModel):
    """Input schema for listing all dives."""

    limit: int = Field(
        default=10,
        description="Maximum number of dives to list (default: 10)"
    )
    sort_by: str = Field(
        default="date",
        description="Sort order: 'date' (newest first), 'depth' (deepest first), or 'duration' (longest first)"
    )


class ListAllDivesTool(BaseTool):
    """List all dives with sorting options."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "list_all_dives"
    description: str = (
        "List all dives with optional sorting. Use this to get an overview of all dives. "
        "Sort options: 'date' (newest first), 'depth' (deepest first), 'duration' (longest first)."
    )
    args_schema: Type[BaseModel] = ListAllDivesInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(self, limit: int = 10, sort_by: str = "date") -> str:
        """List dives and return formatted result."""
        if not self.dives:
            return "No dives in the log."

        # Sort dives
        sorted_dives = list(enumerate(self.dives))

        if sort_by == "date":
            sorted_dives.sort(key=lambda x: x[1].basics.start_time, reverse=True)
        elif sort_by == "depth":
            sorted_dives.sort(
                key=lambda x: max(x[1].timeline.depths) if x[1].timeline.depths else 0,
                reverse=True
            )
        elif sort_by == "duration":
            sorted_dives.sort(key=lambda x: x[1].basics.duration, reverse=True)
        else:
            return f"Invalid sort_by: {sort_by}. Use 'date', 'depth', or 'duration'."

        # Limit results
        limited = sorted_dives[:limit]

        lines = [f"Showing {len(limited)} of {len(self.dives)} dives (sorted by {sort_by}):"]
        lines.append("")

        for idx, dive in limited:
            max_depth = max(dive.timeline.depths) if dive.timeline.depths else 0
            duration = dive.basics.duration / 60
            date_str = dive.basics.start_time.strftime('%Y-%m-%d')

            lines.append(
                f"[{idx}] {date_str}: {max_depth:.1f}m, {duration:.0f}min - {dive.location.name or 'Unknown'}"
            )

        if len(self.dives) > limit:
            lines.append(f"\n... and {len(self.dives) - limit} more dives")

        return "\n".join(lines)
