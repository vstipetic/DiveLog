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
    FilterDivesByPersonTool,
    FilterDivesByLocationTool,
    FilterDivesByStartTimeTool,
    FilterDivesByTemperatureTool,
    FilterDivesByCNSLoadTool,
    FilterDivesByGasTypeTool,
    FilterDivesByDurationAtDepthTool,
    LabelFilteredDivesTool,
)

from Utilities.Tools.StatisticsTool import (
    CalculateStatisticTool,
    CalculateTimeBelowDepthTool,
    CountDivesWithPersonTool,
)

from Utilities.Tools.SearchTool import (
    SearchDivesTool,
    GetDiveSummaryTool,
    ListAllDivesTool,
)

from Utilities.Tools.GeoTools import (
    BuildRegionPolygonTool,
    FilterDivesByRegionTool,
)

from Utilities.Tools.DecoTools import (
    FilterDivesByDecoStatusTool,
    FilterDivesByNDLTool,
)

from Utilities.Tools.ToolState import ToolState
from Utilities.Tools.ChartState import ChartState
from Utilities.Tools.GeoState import GeoRegionState

from Utilities.Tools.ChartTools import (
    PlotHistogramTool,
    PlotBarChartTool,
    PlotPieChartTool,
    PlotScatterTool,
)

__all__ = [
    # Filter tools
    "FilterDivesByDepthTool",
    "FilterDivesByDateTool",
    "FilterDivesByDurationTool",
    "FilterDivesByBuddyTool",
    "FilterDivesByPersonTool",
    "FilterDivesByLocationTool",
    "FilterDivesByStartTimeTool",
    "FilterDivesByTemperatureTool",
    "FilterDivesByCNSLoadTool",
    "FilterDivesByGasTypeTool",
    "FilterDivesByDurationAtDepthTool",
    "LabelFilteredDivesTool",
    # Geographic tools
    "BuildRegionPolygonTool",
    "FilterDivesByRegionTool",
    # Decompression tools
    "FilterDivesByDecoStatusTool",
    "FilterDivesByNDLTool",
    # Statistics tools
    "CalculateStatisticTool",
    "CalculateTimeBelowDepthTool",
    "CountDivesWithPersonTool",
    # Search tools
    "SearchDivesTool",
    "GetDiveSummaryTool",
    "ListAllDivesTool",
    # State management
    "ToolState",
    "ChartState",
    "GeoRegionState",
    # Chart tools
    "PlotHistogramTool",
    "PlotBarChartTool",
    "PlotPieChartTool",
    "PlotScatterTool",
]
