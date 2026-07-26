"""
Tool for calculating dive statistics.

This tool wraps the StatisticsFunctions to provide a validated
interface for calculating various statistics about dives.

IMPORTANT: These tools check ToolState for filtered dives first. If a filter
tool was called previously in the same query, statistics will be calculated
on the filtered subset. Otherwise, statistics are calculated on all dives.
"""

from typing import List, Tuple, Type
from pydantic import BaseModel, Field, ConfigDict

from Utilities.LLMProvider import Tool

from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Schemas.ToolOutputs import StatisticsResult
from Utilities.Tools.ToolState import ToolState
import Utilities.StatisticsFunctions as stats


def _resolve_target_dives(all_dives: List[Dive]) -> Tuple[List[Dive], str]:
    """
    Pick the dives a statistic should run on.

    Returns the filtered subset stored by a preceding filter tool if there is
    one, otherwise every loaded dive, along with a note telling the agent which
    set was used so it can say so in its answer.
    """
    if ToolState.has_filtered_dives():
        target_dives = ToolState.get_filtered_dives()
        filter_desc = ToolState.get_filter_description()
        context_msg = f"(Calculated on {len(target_dives)} filtered dives"
        if filter_desc:
            context_msg += f": {filter_desc}"
        context_msg += ")"
        return target_dives, context_msg

    return all_dives, f"(Calculated on all {len(all_dives)} dives)"


class CalculateStatisticInput(BaseModel):
    """Input schema for calculating statistics."""

    stat_type: str = Field(
        description=(
            "Type of statistic to calculate. Options: "
            "average_depth, max_depth, min_depth, total_dive_time, dive_count, "
            "average_duration, longest_dive, shortest_dive, deepest_dive, "
            "shallowest_dive, average_temperature, dives_by_year, dives_by_month, "
            "dives_by_location, dives_by_buddy, dives_by_person, "
            "most_common_dive_partner, unique_dive_partners, total_air_consumption, "
            "average_air_consumption_rate, most_common_buddy, most_visited_location, "
            "average_max_depth_by_year, total_time_by_location, dives_by_gas_type, "
            "average_cns_load, max_cns_load. "
            "NOTE: the *_buddy statistics only count the designated dive buddy; "
            "dives_by_person / most_common_dive_partner / unique_dive_partners also "
            "count divemasters and group members, and are usually what the user means "
            "by 'who do I dive with'."
        )
    )


class CalculateStatisticTool(Tool):
    """
    Calculate statistics about dives.

    This tool automatically uses filtered dives if a filter tool was called
    previously in the same query. Otherwise, it calculates on all loaded dives.

    Example query flow:
      1. User asks: "How many dives did I do in 2024?"
      2. Agent calls: filter_dives_by_date(start_date="2024-01-01", end_date="2024-12-31")
         → Stores 9 filtered dives in ToolState
      3. Agent calls: calculate_statistic(stat_type="dive_count")
         → Uses the 9 filtered dives, returns "Dive Count: 9"
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "calculate_statistic"
    description: str = (
        "Calculate various statistics about dives. This tool automatically operates on "
        "filtered dives if a filter was applied previously (e.g., filter_dives_by_date). "
        "Otherwise, it calculates on all dives. Available statistics: average_depth, "
        "max_depth, min_depth, total_dive_time, dive_count, average_duration, longest_dive, "
        "shortest_dive, deepest_dive, shallowest_dive, average_temperature, "
        "dives_by_year, dives_by_month, dives_by_location, dives_by_buddy, "
        "dives_by_person, most_common_dive_partner, unique_dive_partners, "
        "total_air_consumption, average_air_consumption_rate, most_common_buddy, "
        "most_visited_location, average_max_depth_by_year, total_time_by_location, "
        "dives_by_gas_type, average_cns_load, max_cns_load. "
        "TIP: Call a filter tool first if you want statistics on a subset of dives. "
        "TIP: prefer dives_by_person / most_common_dive_partner over the *_buddy "
        "versions - they count everyone on the dive, not just the designated buddy."
    )
    args_schema: Type[BaseModel] = CalculateStatisticInput

    # All dives (fallback when no filter applied)
    all_dives: List[Dive] = Field(default_factory=list)

    def run(self, stat_type: str) -> str:
        """Calculate the requested statistic and return formatted result."""
        target_dives, context_msg = _resolve_target_dives(self.all_dives)

        try:
            result = stats.get_statistic(stat_type, target_dives)
            formatted = self._format_result(result)
            return f"{formatted}\n{context_msg}"
        except ValueError as e:
            return str(e)

    def _format_result(self, result: StatisticsResult) -> str:
        """Format StatisticsResult as a readable string."""
        lines = [f"{result.stat_type.replace('_', ' ').title()}: {result.value} {result.unit}"]

        if result.context:
            lines.append(f"Context: {result.context}")

        if result.breakdown:
            lines.append("\nBreakdown:")
            for key, value in result.breakdown.items():
                lines.append(f"  - {key}: {value:.0f}")

        return "\n".join(lines)


class CountDivesWithPersonInput(BaseModel):
    """Input schema for counting dives with a specific person."""

    person_name: str = Field(
        description="Name of the person to count dives with (partial match, case-insensitive)"
    )


class CountDivesWithPersonTool(Tool):
    """
    Count dives with a specific person, split by the role they held.

    Answers "how many dives did I do with X" in one call, without the caller
    having to know whether X was recorded as the buddy or only in the group.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "count_dives_with_person"
    description: str = (
        "Count how many dives were done with a specific person, searching the dive "
        "buddy, the divemaster AND the dive group, and reporting the split between "
        "them. This is the direct way to answer 'how many dives did I do with X'. "
        "Prefer it over filter_dives_by_buddy + dive_count, which only counts dives "
        "where the person was the designated buddy and so undercounts anyone who "
        "was in the group. Operates on filtered dives if a filter was applied "
        "previously, otherwise on all dives."
    )
    args_schema: Type[BaseModel] = CountDivesWithPersonInput

    # All dives (fallback when no filter applied)
    all_dives: List[Dive] = Field(default_factory=list)

    def run(self, person_name: str) -> str:
        """Count dives with the person and return formatted result."""
        if not person_name or not person_name.strip():
            return "Please provide a person_name to search for."

        target_dives, context_msg = _resolve_target_dives(self.all_dives)
        result = stats.count_dives_with_person(target_dives, person_name.strip())

        if result.value == 0:
            return f"{result.context}.\n{context_msg}"

        lines = [
            f"Dives with '{person_name.strip()}': {result.value:.0f} dives",
            f"Context: {result.context}",
            "",
            "Breakdown by role:",
        ]
        for role, count in result.breakdown.items():
            lines.append(f"  - {role}: {count:.0f}")
        lines.append(context_msg)

        return "\n".join(lines)


class CalculateTimeBelowDepthInput(BaseModel):
    """Input schema for calculating time below a specific depth."""

    depth_threshold: float = Field(
        description="Depth threshold in meters. Calculates total time spent below this depth."
    )


class CalculateTimeBelowDepthTool(Tool):
    """
    Calculate time spent below a specific depth.

    This tool automatically uses filtered dives if a filter tool was called
    previously in the same query. Otherwise, it calculates on all loaded dives.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "calculate_time_below_depth"
    description: str = (
        "Calculate the total time spent below a specific depth. This tool automatically "
        "operates on filtered dives if a filter was applied previously. Otherwise, it "
        "calculates across all dives. Useful for understanding time in deeper waters."
    )
    args_schema: Type[BaseModel] = CalculateTimeBelowDepthInput

    # All dives (fallback when no filter applied)
    all_dives: List[Dive] = Field(default_factory=list)

    def run(self, depth_threshold: float) -> str:
        """Calculate time below depth and return formatted result."""
        target_dives, context_msg = _resolve_target_dives(self.all_dives)

        result = stats.time_below_depth(target_dives, depth_threshold)

        lines = [
            f"Time Below {depth_threshold}m: {result.value} {result.unit}",
        ]

        if result.context:
            lines.append(f"Context: {result.context}")

        # Convert to hours if more than 60 minutes
        if result.value > 60:
            hours = result.value / 60
            lines.append(f"That's approximately {hours:.1f} hours")

        lines.append(context_msg)

        return "\n".join(lines)
