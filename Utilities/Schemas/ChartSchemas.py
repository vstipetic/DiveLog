"""
Pydantic input schemas for chart visualization tools.

These models define the expected input parameters for each chart tool,
providing validation and clear descriptions for the LLM.
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional


class PlotHistogramInput(BaseModel):
    """Input for plotting a histogram of dive metrics."""

    metric: str = Field(
        description="Metric to plot distribution of. Options: 'depth' (max depth in meters), "
                   "'duration' (dive time in minutes), 'temperature' (average water temp in Celsius)"
    )
    bin_count: Optional[int] = Field(
        default=10,
        ge=3,
        le=50,
        description="Number of histogram bins (default: 10, range: 3-50)"
    )


class PlotBarChartInput(BaseModel):
    """Input for plotting a bar chart of dive counts by category.

    Two modes:
    1. Auto-grouping: Provide category_by to automatically group dives
    2. Custom data: Provide custom_data dict with pre-computed counts
    """

    category_by: Optional[str] = Field(
        default=None,
        description="Auto-group dives by: 'month', 'year', 'location', 'buddy', 'gas_type'. "
                   "Leave empty if providing custom_data."
    )
    custom_data: Optional[Dict[str, int]] = Field(
        default=None,
        description="Pre-computed category counts as {category_name: count}. "
                   "Use this for custom groupings like seasons, depth bands, etc. "
                   "Example: {'Winter': 5, 'Spring': 10, 'Summer': 20, 'Fall': 8}"
    )
    title: Optional[str] = Field(
        default=None,
        description="Custom chart title. If not provided, auto-generated from category_by."
    )


class PlotPieChartInput(BaseModel):
    """Input for plotting a pie chart showing dive proportions.

    Two modes:
    1. Auto-grouping: Provide category_by to automatically group dives
    2. Custom data: Provide custom_data dict with pre-computed counts
    """

    category_by: Optional[str] = Field(
        default=None,
        description="Auto-group dives by: 'location', 'buddy', 'gas_type'. "
                   "Leave empty if providing custom_data."
    )
    custom_data: Optional[Dict[str, int]] = Field(
        default=None,
        description="Pre-computed category counts as {category_name: count}. "
                   "Use this for custom groupings like seasons, depth bands, etc. "
                   "Example: {'Winter': 5, 'Spring': 10, 'Summer': 20, 'Fall': 8}"
    )
    title: Optional[str] = Field(
        default=None,
        description="Custom chart title. If not provided, auto-generated from category_by."
    )


class PlotScatterInput(BaseModel):
    """Input for plotting a scatter plot showing relationship between two metrics."""

    x_metric: str = Field(
        description="Metric for X-axis. Options: 'depth' (max depth in meters), "
                   "'duration' (dive time in minutes), 'temperature' (avg water temp), "
                   "'cns_load' (max CNS toxicity percentage)"
    )
    y_metric: str = Field(
        description="Metric for Y-axis. Options: 'depth' (max depth in meters), "
                   "'duration' (dive time in minutes), 'temperature' (avg water temp), "
                   "'cns_load' (max CNS toxicity percentage)"
    )
