"""
LangChain tools for the dive statistics agent.

This package contains tool implementations that wrap the existing
FilterFunctions and StatisticsFunctions for use with LangChain agents.

IMPORTANT: Filter and search tools store their results in ToolState,
which allows subsequent statistics tools to operate on the filtered
subset instead of all dives.
"""

from Utilities.Tools.FilterTool import (
    FilterDivesByDepthTool,
    FilterDivesByDateTool,
    FilterDivesByDurationTool,
    FilterDivesByBuddyTool,
    FilterDivesByLocationTool,
    FilterDivesByDurationAtDepthTool,
)

from Utilities.Tools.StatisticsTool import (
    CalculateStatisticTool,
    CalculateTimeBelowDepthTool,
)

from Utilities.Tools.SearchTool import (
    SearchDivesTool,
    GetDiveSummaryTool,
    ListAllDivesTool,
)

from Utilities.Tools.ToolState import ToolState

__all__ = [
    # Filter tools
    "FilterDivesByDepthTool",
    "FilterDivesByDateTool",
    "FilterDivesByDurationTool",
    "FilterDivesByBuddyTool",
    "FilterDivesByLocationTool",
    "FilterDivesByDurationAtDepthTool",
    # Statistics tools
    "CalculateStatisticTool",
    "CalculateTimeBelowDepthTool",
    # Search tools
    "SearchDivesTool",
    "GetDiveSummaryTool",
    "ListAllDivesTool",
    # State management
    "ToolState",
]
