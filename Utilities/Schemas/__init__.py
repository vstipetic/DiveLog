"""
Pydantic schemas for the agent layer.

This package contains Pydantic models used for:
- Tool inputs (validation of tool parameters)
- Tool outputs (structured results from tools)
- Agent models (agent-friendly representations of dive data)

Note: The core Dive/Gear classes use attrs for pickle compatibility.
Pydantic is used only in the agent layer for LangChain integration.
"""

from Utilities.Schemas.ToolInputs import (
    DepthFilterInput,
    DateRangeInput,
    GearFilterInput,
    DurationFilterInput,
    BuddyFilterInput,
    LocationFilterInput,
    DepthThresholdInput,
)

from Utilities.Schemas.ToolOutputs import (
    DiveSummary,
    FilterResult,
    StatisticsResult,
    GearSummary,
)

from Utilities.Schemas.AgentModels import (
    DepthProfile,
    DiveDetails,
    QueryResponse,
)

__all__ = [
    # Input schemas
    "DepthFilterInput",
    "DateRangeInput",
    "GearFilterInput",
    "DurationFilterInput",
    "BuddyFilterInput",
    "LocationFilterInput",
    "DepthThresholdInput",
    # Output schemas
    "DiveSummary",
    "FilterResult",
    "StatisticsResult",
    "GearSummary",
    # Agent models
    "DepthProfile",
    "DiveDetails",
    "QueryResponse",
]
