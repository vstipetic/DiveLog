"""
LangChain tool for calculating dive statistics.

This tool wraps the StatisticsFunctions to provide a LangChain-compatible
interface for calculating various statistics about dives.
"""

from typing import List, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Schemas.ToolOutputs import StatisticsResult
import Utilities.StatisticsFunctions as stats


class CalculateStatisticInput(BaseModel):
    """Input schema for calculating statistics."""

    stat_type: str = Field(
        description=(
            "Type of statistic to calculate. Options: "
            "average_depth, max_depth, min_depth, total_dive_time, dive_count, "
            "average_duration, longest_dive, shortest_dive, deepest_dive, "
            "shallowest_dive, average_temperature, dives_by_year, dives_by_month, "
            "dives_by_location, dives_by_buddy, total_air_consumption, "
            "average_air_consumption_rate"
        )
    )


class CalculateStatisticTool(BaseTool):
    """Calculate statistics about dives."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "calculate_statistic"
    description: str = (
        "Calculate various statistics about dives. Use this tool to get aggregate "
        "information like average depth, total dive time, dive count, or breakdowns "
        "by year/month/location/buddy. Available statistics: average_depth, max_depth, "
        "min_depth, total_dive_time, dive_count, average_duration, longest_dive, "
        "shortest_dive, deepest_dive, shallowest_dive, average_temperature, "
        "dives_by_year, dives_by_month, dives_by_location, dives_by_buddy, "
        "total_air_consumption, average_air_consumption_rate"
    )
    args_schema: Type[BaseModel] = CalculateStatisticInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(self, stat_type: str) -> str:
        """Calculate the requested statistic and return formatted result."""
        try:
            result = stats.get_statistic(stat_type, self.dives)
            return self._format_result(result)
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


class CalculateTimeBelowDepthInput(BaseModel):
    """Input schema for calculating time below a specific depth."""

    depth_threshold: float = Field(
        description="Depth threshold in meters. Calculates total time spent below this depth."
    )


class CalculateTimeBelowDepthTool(BaseTool):
    """Calculate time spent below a specific depth."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "calculate_time_below_depth"
    description: str = (
        "Calculate the total time spent below a specific depth across all dives. "
        "Useful for understanding how much time was spent in deeper waters."
    )
    args_schema: Type[BaseModel] = CalculateTimeBelowDepthInput

    dives: List[Dive] = Field(default_factory=list)

    def _run(self, depth_threshold: float) -> str:
        """Calculate time below depth and return formatted result."""
        result = stats.time_below_depth(self.dives, depth_threshold)

        lines = [
            f"Time Below {depth_threshold}m: {result.value} {result.unit}",
        ]

        if result.context:
            lines.append(f"Context: {result.context}")

        # Convert to hours if more than 60 minutes
        if result.value > 60:
            hours = result.value / 60
            lines.append(f"That's approximately {hours:.1f} hours")

        return "\n".join(lines)
