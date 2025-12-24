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

    Note: Uses None + lazy initialization instead of mutable default [] to avoid
    issues with Python's class machinery and Streamlit's module reloading.
    """

    _charts: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Ensure _charts is initialized."""
        if cls._charts is None:
            cls._charts = []

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
        cls._ensure_initialized()
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
        cls._ensure_initialized()
        return cls._charts.copy()

    @classmethod
    def has_charts(cls) -> bool:
        """Check if there are any charts stored."""
        return cls._charts is not None and len(cls._charts) > 0

    @classmethod
    def clear(cls) -> None:
        """Clear all stored charts. Call at start of each new query."""
        cls._charts = []

    @classmethod
    def get_chart_count(cls) -> int:
        """Get count of stored charts."""
        cls._ensure_initialized()
        return len(cls._charts)
