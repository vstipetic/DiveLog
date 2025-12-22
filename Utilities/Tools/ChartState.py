"""
Shared state for passing chart specifications from tools to Streamlit.

This module provides a mechanism for chart tools to store their generated
Altair charts, which Streamlit then renders after the agent's text response.

Flow:
  1. Agent processes query, calls chart tool (e.g., plot_bar_chart)
  2. Chart tool creates Altair chart and stores in ChartState
  3. After agent returns, Streamlit reads ChartState and renders charts
  4. ChartState is cleared at start of next query
"""

from typing import Any, Dict, List, Optional


class ChartState:
    """
    Class-level shared state for storing chart specifications.

    Chart tools call add_chart() after creating an Altair chart.
    Streamlit calls get_charts() to retrieve and render all charts.

    The agent should call clear() at the start of each new query to reset state.
    """

    _charts: List[Dict[str, Any]] = []

    @classmethod
    def add_chart(
        cls,
        chart: Any,
        chart_type: str,
        title: str,
        description: Optional[str] = None
    ) -> None:
        """
        Store a chart specification for Streamlit to render.

        Args:
            chart: The Altair chart object
            chart_type: Type of chart (histogram, bar, pie, scatter)
            title: Chart title
            description: Optional description of what the chart shows
        """
        cls._charts.append({
            "chart": chart,
            "chart_type": chart_type,
            "title": title,
            "description": description
        })

    @classmethod
    def get_charts(cls) -> List[Dict[str, Any]]:
        """
        Get all stored chart specifications.

        Returns:
            List of chart specification dictionaries
        """
        return cls._charts.copy()

    @classmethod
    def has_charts(cls) -> bool:
        """Check if there are any charts stored."""
        return len(cls._charts) > 0

    @classmethod
    def clear(cls) -> None:
        """Clear all stored charts. Call at start of each new query."""
        cls._charts = []

    @classmethod
    def get_chart_count(cls) -> int:
        """Get count of stored charts."""
        return len(cls._charts)
