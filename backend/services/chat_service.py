"""
Chat service: owns the StatisticsAgent lifecycle and query processing.

The agent, its tools, and the ToolState/ChartState interaction are used
exactly as before (see Utilities/StatisticsAgent.py): the agent clears both
states at the start of each query, chart tools deposit Altair charts into
ChartState, and after the agent's text response the UI layer collects them.
The only difference from the Streamlit era is that charts are serialized to
Vega-Lite JSON here so the browser can render them with vega-embed.
"""

import json
from typing import Any, Dict, List, Optional

from Utilities.StatisticsAgent import StatisticsAgent
from Utilities.Tools.ChartState import ChartState

from backend.services import settings_service
from backend.state import state


def get_agent() -> Optional[StatisticsAgent]:
    """
    Create or return the cached agent for the current provider settings.

    Returns None when no API key is configured or agent creation fails.
    """
    if not settings_service.ensure_selection():
        return None

    if (
        state.agent is None
        or state.agent.api_key != state.api_key
        or state.agent.provider != state.provider
        or state.agent.model != state.model
        or str(state.agent.dive_folder) != state.storage_folder
    ):
        try:
            state.agent = StatisticsAgent(
                api_key=state.api_key,
                dive_folder=state.storage_folder,
                provider=state.provider,
                model=state.model,
            )
        except Exception as e:
            print(f"Failed to initialize agent: {e}")
            state.agent = None

    return state.agent


def refresh_agent() -> None:
    """Drop the cached agent so dives are reloaded on next use."""
    state.agent = None


def serialize_chart(chart_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a ChartState entry (holding a live Altair chart object) into a
    JSON-safe dict with a Vega-Lite spec the frontend can render.
    """
    chart = chart_spec.get("chart")
    spec = None
    if chart is not None:
        try:
            # to_json() uses Altair's encoder (handles numpy/pandas types).
            spec = json.loads(chart.to_json())
        except Exception as e:
            print(f"Failed to serialize chart '{chart_spec.get('title')}': {e}")
    return {
        "spec": spec,
        "chart_type": chart_spec.get("chart_type"),
        "title": chart_spec.get("title"),
        "description": chart_spec.get("description"),
    }


def process_query(query: str) -> Dict[str, Any]:
    """
    Process a user query through the agent and record it in the transcript.

    Returns the assistant message dict: {"role", "content", "charts"}.
    """
    with state.chat_lock:
        agent = get_agent()
        if agent is None:
            raise RuntimeError(
                "The AI agent is not available. Configure an API key in the sidebar."
            )

        state.messages.append({"role": "user", "content": query, "charts": []})

        # ChartState is cleared and populated by agent.process_query.
        try:
            response = agent.process_query(query)
        except Exception as e:
            response = f"Error: {str(e)}"

        charts = ChartState.get_charts() if ChartState.has_charts() else []
        serialized_charts = [serialize_chart(c) for c in charts]

        assistant_message = {
            "role": "assistant",
            "content": response,
            "charts": serialized_charts,
        }
        state.messages.append(assistant_message)
        return assistant_message


def clear_chat() -> None:
    """Clear the transcript and the agent's conversational memory."""
    state.messages = []
    if state.agent:
        state.agent.clear_history()


def get_quick_stats(agent: Optional[StatisticsAgent]) -> Optional[Dict[str, Any]]:
    """Compute the quick-stats cards shown above the chat."""
    if not agent or not agent.dives:
        return None

    total_dives = len(agent.dives)
    total_time = sum(d.basics.duration for d in agent.dives) / 60

    depths = [max(d.timeline.depths) for d in agent.dives if d.timeline.depths]
    avg_depth = sum(depths) / len(depths) if depths else 0
    max_depth = max(depths) if depths else 0

    return {
        "total_dives": total_dives,
        "total_time_hours": total_time / 60,
        "avg_depth": avg_depth,
        "max_depth": max_depth,
    }


EXAMPLE_QUERIES: List[str] = [
    "What's my average dive depth?",
    "How many dives did I do in 2024?",
    "Show me all dives deeper than 20 meters",
    "What's my total dive time?",
    "Who is my most common dive buddy?",
    "List my 5 deepest dives",
    "Plot the distribution of my dive depths",
    "Create a bar chart of dives by month",
    "Is there a relationship between depth and dive duration?",
    "Show a pie chart of dives by location",
]
