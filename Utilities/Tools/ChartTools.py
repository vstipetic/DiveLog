"""
LangChain tools for creating dive data visualizations.

These tools create Altair charts and store them in ChartState for
Streamlit to render alongside text responses.

All chart tools respect ToolState: if a filter was applied, charts are
generated from the filtered subset; otherwise from all dives.
"""

from typing import Dict, List, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict
import pandas as pd
import altair as alt

from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Tools.ToolState import ToolState
from Utilities.Tools.ChartState import ChartState
from Utilities.Schemas.ChartSchemas import (
    PlotHistogramInput,
    PlotBarChartInput,
    PlotPieChartInput,
    PlotScatterInput,
)


# Valid metric options for extraction
VALID_METRICS = {"depth", "duration", "temperature", "cns_load"}

# Valid category options for grouping
VALID_CATEGORIES = {"month", "year", "location", "buddy", "gas_type"}

# Categories valid for pie charts (not too many categories)
VALID_PIE_CATEGORIES = {"location", "buddy", "gas_type"}


def _extract_metric(dive: Dive, metric: str) -> Optional[float]:
    """Extract a metric value from a dive."""
    if metric == "depth":
        return max(dive.timeline.depths) if dive.timeline.depths else None
    elif metric == "duration":
        return dive.basics.duration / 60 if dive.basics.duration else None
    elif metric == "temperature":
        temps = [t for t in dive.timeline.temperatures if t is not None]
        return sum(temps) / len(temps) if temps else None
    elif metric == "cns_load":
        cns = [c for c in dive.timeline.cns_loads if c is not None and c > 0]
        return max(cns) if cns else None
    return None


def _extract_category(dive: Dive, category: str) -> Optional[str]:
    """Extract a category value from a dive."""
    if category == "month":
        return dive.basics.start_time.strftime("%B") if dive.basics.start_time else None
    elif category == "year":
        return str(dive.basics.start_time.year) if dive.basics.start_time else None
    elif category == "location":
        return dive.location.name if dive.location.name else "Unknown"
    elif category == "buddy":
        return dive.people.buddy if dive.people.buddy else "Solo/Unknown"
    elif category == "gas_type":
        return dive.gasses.gas if dive.gasses.gas else "Unknown"
    return None


def _get_target_dives(all_dives: List[Dive]) -> tuple[List[Dive], str]:
    """Get target dives (filtered or all) and context message."""
    if ToolState.has_filtered_dives():
        target_dives = ToolState.get_filtered_dives()
        filter_desc = ToolState.get_filter_description()
        context = f"Using {len(target_dives)} filtered dives"
        if filter_desc:
            context += f" ({filter_desc})"
    else:
        target_dives = all_dives
        context = f"Using all {len(target_dives)} dives"
    return target_dives, context


class PlotHistogramTool(BaseTool):
    """
    Create a histogram showing the distribution of a dive metric.

    Supports metrics: depth (max depth), duration (dive time),
    temperature (average water temp).

    This tool respects previous filters - if a filter was applied,
    the histogram shows only filtered dives.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "plot_histogram"
    description: str = (
        "Create a histogram showing the distribution of dive metrics. "
        "Use this to visualize how values are spread across your dives. "
        "Metrics: 'depth' (max depth in meters), 'duration' (time in minutes), "
        "'temperature' (water temp in Celsius). "
        "Optionally specify bin_count (3-50, default 10). "
        "This tool respects any previously applied filters."
    )
    args_schema: Type[BaseModel] = PlotHistogramInput

    all_dives: List[Dive] = Field(default_factory=list)

    def _run(self, metric: str, bin_count: Optional[int] = 10) -> str:
        """Create histogram and store in ChartState."""
        metric = metric.lower()
        if metric not in VALID_METRICS:
            return f"Invalid metric '{metric}'. Choose from: {', '.join(VALID_METRICS)}"

        target_dives, context = _get_target_dives(self.all_dives)

        if not target_dives:
            return "No dives available to plot."

        # Extract metric values
        values = []
        for dive in target_dives:
            val = _extract_metric(dive, metric)
            if val is not None:
                values.append(val)

        if not values:
            return f"No valid {metric} data found in the dives."

        # Create DataFrame
        metric_labels = {
            "depth": "Max Depth (m)",
            "duration": "Duration (min)",
            "temperature": "Temperature (°C)",
            "cns_load": "CNS Load (%)"
        }
        label = metric_labels.get(metric, metric.title())

        df = pd.DataFrame({label: values})

        # Create Altair histogram
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X(f"{label}:Q", bin=alt.Bin(maxbins=bin_count or 10), title=label),
            y=alt.Y("count()", title="Number of Dives"),
            tooltip=[alt.Tooltip(f"{label}:Q", bin=alt.Bin(maxbins=bin_count or 10)), "count()"]
        ).properties(
            title=f"Distribution of {label}",
            width=500,
            height=300
        ).interactive()

        # Store in ChartState
        ChartState.add_chart(
            chart=chart,
            chart_type="histogram",
            title=f"Distribution of {label}",
            description=f"Histogram showing {metric} distribution across {len(values)} dives"
        )

        return f"Created histogram of {metric} distribution. {context}. Showing {len(values)} data points."


class PlotBarChartTool(BaseTool):
    """
    Create a bar chart showing dive counts grouped by category.

    Two modes:
    1. Auto-grouping: Provide category_by to automatically group dives
    2. Custom data: Provide custom_data dict with pre-computed counts

    This tool respects previous filters when using auto-grouping.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "plot_bar_chart"
    description: str = (
        "Create a bar chart showing dive counts by category. "
        "Two modes: (1) Auto-group using category_by: 'month', 'year', 'location', 'buddy', 'gas_type'. "
        "(2) Custom data: pass custom_data dict like {'Winter': 5, 'Spring': 10} for custom groupings "
        "(seasons, depth bands, etc). Optionally provide a custom title. "
        "Auto-grouping respects any previously applied filters."
    )
    args_schema: Type[BaseModel] = PlotBarChartInput

    all_dives: List[Dive] = Field(default_factory=list)

    def _run(
        self,
        category_by: Optional[str] = None,
        custom_data: Optional[Dict[str, int]] = None,
        title: Optional[str] = None
    ) -> str:
        """Create bar chart and store in ChartState."""
        # Validate inputs - need either category_by or custom_data
        if custom_data is None and category_by is None:
            return "Please provide either category_by for auto-grouping or custom_data for custom groupings."

        # Mode 1: Custom data provided - use it directly
        if custom_data is not None:
            if not custom_data:
                return "custom_data is empty. Provide at least one category with a count."

            # Create DataFrame from custom data
            counts = pd.DataFrame([
                {"Category": k, "Count": v} for k, v in custom_data.items()
            ])

            # Use provided title or generate one
            chart_title = title or "Custom Category Distribution"
            category_label = "Category"

            # Sort by count descending
            counts = counts.sort_values("Count", ascending=False)

            # Create Altair bar chart
            chart = alt.Chart(counts).mark_bar().encode(
                x=alt.X("Category:N", title=category_label, sort=list(counts["Category"])),
                y=alt.Y("Count:Q", title="Number of Dives"),
                tooltip=["Category", "Count"]
            ).properties(
                title=chart_title,
                width=500,
                height=300
            ).interactive()

            # Store in ChartState
            ChartState.add_chart(
                chart=chart,
                chart_type="bar",
                title=chart_title,
                description=f"Bar chart with custom data: {len(counts)} categories"
            )

            total_count = counts["Count"].sum()
            return f"Created bar chart '{chart_title}' with custom data. {len(counts)} categories, {total_count} total dives."

        # Mode 2: Auto-grouping by category_by
        category_by = category_by.lower()
        if category_by not in VALID_CATEGORIES:
            return f"Invalid category '{category_by}'. Choose from: {', '.join(VALID_CATEGORIES)}"

        target_dives, context = _get_target_dives(self.all_dives)

        if not target_dives:
            return "No dives available to plot."

        # Extract categories
        categories = []
        for dive in target_dives:
            cat = _extract_category(dive, category_by)
            if cat is not None:
                categories.append(cat)

        if not categories:
            return f"No valid {category_by} data found in the dives."

        # Create DataFrame with counts
        df = pd.DataFrame({"Category": categories})
        counts = df["Category"].value_counts().reset_index()
        counts.columns = ["Category", "Count"]

        # Sort appropriately
        if category_by == "month":
            month_order = ["January", "February", "March", "April", "May", "June",
                          "July", "August", "September", "October", "November", "December"]
            counts["sort_key"] = counts["Category"].apply(
                lambda x: month_order.index(x) if x in month_order else 99
            )
            counts = counts.sort_values("sort_key").drop("sort_key", axis=1)
        elif category_by == "year":
            counts = counts.sort_values("Category")
        else:
            counts = counts.sort_values("Count", ascending=False)

        # Create Altair bar chart
        category_label = category_by.replace("_", " ").title()
        chart_title = title or f"Dives by {category_label}"

        chart = alt.Chart(counts).mark_bar().encode(
            x=alt.X("Category:N", title=category_label, sort=list(counts["Category"])),
            y=alt.Y("Count:Q", title="Number of Dives"),
            tooltip=["Category", "Count"]
        ).properties(
            title=chart_title,
            width=500,
            height=300
        ).interactive()

        # Store in ChartState
        ChartState.add_chart(
            chart=chart,
            chart_type="bar",
            title=chart_title,
            description=f"Bar chart showing dive counts by {category_by}"
        )

        return f"Created bar chart showing dives by {category_by}. {context}. Found {len(counts)} categories."


class PlotPieChartTool(BaseTool):
    """
    Create a pie chart showing proportional breakdown of dives.

    Two modes:
    1. Auto-grouping: Provide category_by to automatically group dives
    2. Custom data: Provide custom_data dict with pre-computed counts

    This tool respects previous filters when using auto-grouping.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "plot_pie_chart"
    description: str = (
        "Create a pie chart showing proportional breakdown of dives. "
        "Two modes: (1) Auto-group using category_by: 'location', 'buddy', 'gas_type'. "
        "(2) Custom data: pass custom_data dict like {'Winter': 5, 'Spring': 10} for custom groupings "
        "(seasons, depth bands, etc). Optionally provide a custom title. "
        "Auto-grouping respects any previously applied filters."
    )
    args_schema: Type[BaseModel] = PlotPieChartInput

    all_dives: List[Dive] = Field(default_factory=list)

    def _run(
        self,
        category_by: Optional[str] = None,
        custom_data: Optional[Dict[str, int]] = None,
        title: Optional[str] = None
    ) -> str:
        """Create pie chart and store in ChartState."""
        # Validate inputs - need either category_by or custom_data
        if custom_data is None and category_by is None:
            return "Please provide either category_by for auto-grouping or custom_data for custom groupings."

        # Mode 1: Custom data provided - use it directly
        if custom_data is not None:
            if not custom_data:
                return "custom_data is empty. Provide at least one category with a count."

            # Create DataFrame from custom data
            counts = pd.DataFrame([
                {"Category": k, "Count": v} for k, v in custom_data.items()
            ])

            # Limit to top 8 categories for readability, group rest as "Other"
            if len(counts) > 8:
                counts = counts.sort_values("Count", ascending=False)
                top_counts = counts.head(7)
                other_count = counts.tail(-7)["Count"].sum()
                other_row = pd.DataFrame({"Category": ["Other"], "Count": [other_count]})
                counts = pd.concat([top_counts, other_row], ignore_index=True)

            # Use provided title or generate one
            chart_title = title or "Custom Category Proportions"
            category_label = "Category"

            # Create Altair pie chart (using arc mark)
            chart = alt.Chart(counts).mark_arc(innerRadius=50).encode(
                theta=alt.Theta("Count:Q", title="Dives"),
                color=alt.Color("Category:N", title=category_label),
                tooltip=["Category", "Count"]
            ).properties(
                title=chart_title,
                width=400,
                height=400
            )

            # Store in ChartState
            ChartState.add_chart(
                chart=chart,
                chart_type="pie",
                title=chart_title,
                description=f"Pie chart with custom data: {len(counts)} categories"
            )

            total_count = counts["Count"].sum()
            return f"Created pie chart '{chart_title}' with custom data. {len(counts)} categories, {total_count} total dives."

        # Mode 2: Auto-grouping by category_by
        category_by = category_by.lower()
        if category_by not in VALID_PIE_CATEGORIES:
            return f"Invalid category '{category_by}'. Choose from: {', '.join(VALID_PIE_CATEGORIES)}"

        target_dives, context = _get_target_dives(self.all_dives)

        if not target_dives:
            return "No dives available to plot."

        # Extract categories
        categories = []
        for dive in target_dives:
            cat = _extract_category(dive, category_by)
            if cat is not None:
                categories.append(cat)

        if not categories:
            return f"No valid {category_by} data found in the dives."

        # Create DataFrame with counts
        df = pd.DataFrame({"Category": categories})
        counts = df["Category"].value_counts().reset_index()
        counts.columns = ["Category", "Count"]

        # Limit to top 8 categories for readability, group rest as "Other"
        if len(counts) > 8:
            top_counts = counts.head(7)
            other_count = counts.tail(-7)["Count"].sum()
            other_row = pd.DataFrame({"Category": ["Other"], "Count": [other_count]})
            counts = pd.concat([top_counts, other_row], ignore_index=True)

        # Create Altair pie chart (using arc mark)
        category_label = category_by.replace("_", " ").title()
        chart_title = title or f"Dives by {category_label}"

        chart = alt.Chart(counts).mark_arc(innerRadius=50).encode(
            theta=alt.Theta("Count:Q", title="Dives"),
            color=alt.Color("Category:N", title=category_label),
            tooltip=["Category", "Count"]
        ).properties(
            title=chart_title,
            width=400,
            height=400
        )

        # Store in ChartState
        ChartState.add_chart(
            chart=chart,
            chart_type="pie",
            title=chart_title,
            description=f"Pie chart showing dive proportions by {category_by}"
        )

        return f"Created pie chart showing dives by {category_by}. {context}. Found {len(counts)} categories."


class PlotScatterTool(BaseTool):
    """
    Create a scatter plot showing relationship between two metrics.

    Supports metrics: depth, duration, temperature, cns_load.

    This tool respects previous filters - if a filter was applied,
    the chart shows only filtered dives.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "plot_scatter"
    description: str = (
        "Create a scatter plot to explore relationships between two dive metrics. "
        "Use this to investigate correlations (e.g., depth vs duration). "
        "Metrics: 'depth' (max depth in meters), 'duration' (time in minutes), "
        "'temperature' (water temp in Celsius), 'cns_load' (CNS toxicity %). "
        "This tool respects any previously applied filters."
    )
    args_schema: Type[BaseModel] = PlotScatterInput

    all_dives: List[Dive] = Field(default_factory=list)

    def _run(self, x_metric: str, y_metric: str) -> str:
        """Create scatter plot and store in ChartState."""
        x_metric = x_metric.lower()
        y_metric = y_metric.lower()

        if x_metric not in VALID_METRICS:
            return f"Invalid x_metric '{x_metric}'. Choose from: {', '.join(VALID_METRICS)}"
        if y_metric not in VALID_METRICS:
            return f"Invalid y_metric '{y_metric}'. Choose from: {', '.join(VALID_METRICS)}"

        target_dives, context = _get_target_dives(self.all_dives)

        if not target_dives:
            return "No dives available to plot."

        # Extract both metrics for each dive
        data = []
        for dive in target_dives:
            x_val = _extract_metric(dive, x_metric)
            y_val = _extract_metric(dive, y_metric)
            if x_val is not None and y_val is not None:
                # Also include date for tooltip
                date_str = dive.basics.start_time.strftime("%Y-%m-%d") if dive.basics.start_time else "Unknown"
                location = dive.location.name if dive.location.name else "Unknown"
                data.append({
                    "x": x_val,
                    "y": y_val,
                    "date": date_str,
                    "location": location
                })

        if not data:
            return f"No dives with valid {x_metric} and {y_metric} data found."

        if len(data) == 1:
            return f"Only 1 dive with valid data found. Need at least 2 dives for a scatter plot."

        # Create DataFrame
        metric_labels = {
            "depth": "Max Depth (m)",
            "duration": "Duration (min)",
            "temperature": "Temperature (°C)",
            "cns_load": "CNS Load (%)"
        }
        x_label = metric_labels.get(x_metric, x_metric.title())
        y_label = metric_labels.get(y_metric, y_metric.title())

        df = pd.DataFrame(data)
        df.columns = [x_label, y_label, "Date", "Location"]

        # Create Altair scatter plot
        chart = alt.Chart(df).mark_circle(size=60).encode(
            x=alt.X(f"{x_label}:Q", title=x_label),
            y=alt.Y(f"{y_label}:Q", title=y_label),
            tooltip=[x_label, y_label, "Date", "Location"]
        ).properties(
            title=f"{y_label} vs {x_label}",
            width=500,
            height=400
        ).interactive()

        # Store in ChartState
        ChartState.add_chart(
            chart=chart,
            chart_type="scatter",
            title=f"{y_label} vs {x_label}",
            description=f"Scatter plot comparing {x_metric} and {y_metric}"
        )

        return f"Created scatter plot of {y_metric} vs {x_metric}. {context}. Showing {len(data)} data points."
