"""
LangChain tools for the dive statistics agent.

This package contains tool implementations that wrap the existing
FilterFunctions and StatisticsFunctions for use with LangChain agents.
"""

from Utilities.Tools.FilterTool import (
    FilterDivesByDepthTool,
    FilterDivesByDateTool,
    FilterDivesByDurationTool,
    FilterDivesByBuddyTool,
    FilterDivesByLocationTool,
)

from Utilities.Tools.StatisticsTool import (
    CalculateStatisticTool,
)

from Utilities.Tools.SearchTool import (
    SearchDivesTool,
)

__all__ = [
    # Filter tools
    "FilterDivesByDepthTool",
    "FilterDivesByDateTool",
    "FilterDivesByDurationTool",
    "FilterDivesByBuddyTool",
    "FilterDivesByLocationTool",
    # Statistics tools
    "CalculateStatisticTool",
    # Search tools
    "SearchDivesTool",
]
