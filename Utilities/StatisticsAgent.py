"""
AI-powered statistics agent for natural language dive queries.

This module provides a LangChain-based agent that can answer natural language
questions about dive statistics using a set of specialized tools.

Supported LLM providers:
- Gemini (Google)
- OpenAI (GPT-5)
- Anthropic (Claude)
"""

import pickle
from pathlib import Path
from typing import List, Optional

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage

from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Tools.FilterTool import (
    FilterDivesByDepthTool,
    FilterDivesByDateTool,
    FilterDivesByDurationTool,
    FilterDivesByBuddyTool,
    FilterDivesByLocationTool,
    FilterDivesByStartTimeTool,
    FilterDivesByTemperatureTool,
    FilterDivesByCNSLoadTool,
    FilterDivesByGasTypeTool,
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
from Utilities.Tools.ChartState import ChartState
from Utilities.Tools.ChartTools import (
    PlotHistogramTool,
    PlotBarChartTool,
    PlotPieChartTool,
    PlotScatterTool,
)


# System prompt for the agent
SYSTEM_PROMPT = """You are a helpful dive log assistant. You have access to tools to filter, search,
and calculate statistics about the user's dive log data.

When answering questions about dives:

1. Use the appropriate tools to gather information
2. Provide clear, concise answers with specific numbers
3. Include relevant context (dates, locations, dive buddies, etc.)
4. Format depths in meters and times in minutes
5. If you can't find exact information, explain what you can provide

Available capabilities:
- Filter dives by: depth, date, duration, buddy, location, start time (morning/afternoon),
  water temperature, CNS oxygen toxicity load, gas type (air/nitrox/trimix),
  and continuous time at specific depth
- Calculate statistics: averages, totals, counts, breakdowns by time/location/buddy/gas
- Search for dives by text in various fields
- Get detailed information about specific dives
- List all dives with sorting options
- Create visualizations: histograms (depth/duration/temperature distributions),
  bar charts (dives by month/year/location/buddy), pie charts (proportional breakdowns),
  scatter plots (relationships between metrics like depth vs duration)

The user has {num_dives} dives in their log.

When a user asks a question:
- First understand what they're asking for
- Choose the right tool(s) to get the information
- Present the results in a friendly, readable format
- Offer to provide more details if relevant

VISUALIZATION TOOLS:

Bar and pie chart tools support two modes:
1. Auto-grouping: Use category_by to group by month, year, location, buddy, or gas_type
2. Custom data: Use custom_data with pre-computed counts for custom groupings

For custom groupings (seasons, depth bands, etc.), use the custom_data parameter:
- Filter dives multiple times to get counts for each category
- Pass the counts as custom_data: {{"category_name": count, ...}}
- Provide a descriptive title

Example workflow for "pie chart of dives by season":
1. Filter by date for each season and count results:
   - Winter (Dec-Feb): filter_dives_by_date → count
   - Spring (Mar-May): filter_dives_by_date → count
   - Summer (Jun-Aug): filter_dives_by_date → count
   - Fall (Sep-Nov): filter_dives_by_date → count
2. Call plot_pie_chart with custom_data={{"Winter": 5, "Spring": 10, "Summer": 20, "Fall": 8}}

Example workflow for "bar chart of dives by depth bands":
1. Filter by depth ranges and count:
   - 0-10m: filter_dives_by_depth(min=0, max=10) → count
   - 10-20m: filter_dives_by_depth(min=10, max=20) → count
   - 20-30m: filter_dives_by_depth(min=20, max=30) → count
   - 30+m: filter_dives_by_depth(min=30) → count
2. Call plot_bar_chart with custom_data={{"0-10m": 5, "10-20m": 12, "20-30m": 8, "30+m": 3}}

Examples of questions you can answer:
- "What's my average dive depth?"
- "How many dives did I do in 2024?"
- "Show me dives deeper than 30 meters"
- "What's my deepest dive?"
- "Who is my most common dive buddy?"
- "List my dives at [location]"
- "Show me morning dives (before 10am)"
- "Find dives in water colder than 15 degrees"
- "Show dives where I spent 5+ minutes at 30m depth"
- "What's my average CNS load on deep dives?"
- "How many nitrox dives have I done?"
- "Plot the distribution of my dive depths"
- "Show a bar chart of dives by month in 2024"
- "Is there a relationship between depth and dive duration?"
- "Create a pie chart of dives by location"
- "Show a pie chart of my dives by season"
- "Create a bar chart of dives by depth bands (0-10m, 10-20m, etc.)"
"""


class StatisticsAgent:
    """AI agent for querying dive statistics using natural language."""

    def __init__(
        self,
        api_key: str,
        dive_folder: str = "Storage/Dives",
        provider: str = "gemini"
    ):
        """Initialize the statistics agent.

        Args:
            api_key: API key for LLM provider
            dive_folder: Path to folder containing dive pickle files
            provider: LLM provider ('gemini', 'openai', or 'claude')
        """
        self.api_key = api_key
        self.dive_folder = Path(dive_folder)
        self.provider = provider
        self.dives: List[Dive] = []
        self.chat_history: List = []

        # Load dives
        self._load_dives()

        # Initialize LLM
        self.llm = self._create_llm()

        # Initialize tools
        self.tools = self._create_tools()

        # Create agent
        self.agent_executor = self._create_agent()

    def _load_dives(self) -> None:
        """Load all dive pickle files from storage."""
        self.dives = []

        if not self.dive_folder.exists():
            print(f"Dive folder does not exist: {self.dive_folder}")
            return

        for pickle_file in self.dive_folder.glob("*.pickle"):
            try:
                with open(pickle_file, 'rb') as f:
                    dive = pickle.load(f)
                    self.dives.append(dive)
            except Exception as e:
                print(f"Error loading {pickle_file}: {e}")

        print(f"Loaded {len(self.dives)} dives from {self.dive_folder}")

    def _create_llm(self):
        """Create LLM instance based on provider."""
        if self.provider == "gemini":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash",
                    google_api_key=self.api_key,
                    temperature=0,
                    convert_system_message_to_human=True
                )
            except ImportError:
                raise ImportError(
                    "langchain-google-genai is required for Gemini. "
                    "Install with: pip install langchain-google-genai"
                )

        elif self.provider == "openai":
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model="gpt-5-mini",
                    api_key=self.api_key,
                    temperature=1
                )
            except ImportError:
                raise ImportError(
                    "langchain-openai is required for OpenAI. "
                    "Install with: pip install langchain-openai"
                )

        elif self.provider == "claude":
            try:
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model="claude-sonnet-4-20250514",
                    api_key=self.api_key,
                    temperature=0
                )
            except ImportError:
                raise ImportError(
                    "langchain-anthropic is required for Claude. "
                    "Install with: pip install langchain-anthropic"
                )

        else:
            raise ValueError(
                f"Unknown provider: {self.provider}. "
                "Supported providers: 'gemini', 'openai', 'claude'"
            )

    def _create_tools(self):
        """Create tool instances with dive data."""
        return [
            # Filter tools - use dives field, store results in ToolState
            FilterDivesByDepthTool(dives=self.dives),
            FilterDivesByDateTool(dives=self.dives),
            FilterDivesByDurationTool(dives=self.dives),
            FilterDivesByBuddyTool(dives=self.dives),
            FilterDivesByLocationTool(dives=self.dives),
            FilterDivesByStartTimeTool(dives=self.dives),
            FilterDivesByTemperatureTool(dives=self.dives),
            FilterDivesByCNSLoadTool(dives=self.dives),
            FilterDivesByGasTypeTool(dives=self.dives),
            FilterDivesByDurationAtDepthTool(dives=self.dives),
            # Statistics tools - use all_dives as fallback, check ToolState first
            CalculateStatisticTool(all_dives=self.dives),
            CalculateTimeBelowDepthTool(all_dives=self.dives),
            # Search tools
            SearchDivesTool(dives=self.dives),
            GetDiveSummaryTool(dives=self.dives),
            ListAllDivesTool(dives=self.dives),
            # Chart tools - use all_dives, check ToolState first for filtered data
            PlotHistogramTool(all_dives=self.dives),
            PlotBarChartTool(all_dives=self.dives),
            PlotPieChartTool(all_dives=self.dives),
            PlotScatterTool(all_dives=self.dives),
        ]

    def _create_agent(self):
        """Create LangChain agent with tools."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        agent = create_tool_calling_agent(self.llm, self.tools, prompt)

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10
        )

    def process_query(self, query: str) -> str:
        """Process a natural language query about dives.

        Args:
            query: Natural language question about dives

        Returns:
            Natural language response with answer
        """
        if not self.dives:
            return (
                "No dives found in the dive log. Please add some dives first "
                "using the Add Dive feature."
            )

        # Clear any previous filter/chart state from prior queries
        ToolState.clear()
        ChartState.clear()

        try:
            result = self.agent_executor.invoke({
                "input": query,
                "num_dives": len(self.dives),
                "chat_history": self.chat_history
            })

            # Update chat history
            self.chat_history.append(HumanMessage(content=query))
            self.chat_history.append(AIMessage(content=result["output"]))

            # Keep chat history manageable
            if len(self.chat_history) > 20:
                self.chat_history = self.chat_history[-20:]

            return result["output"]

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(error_msg)
            return error_msg

    def clear_history(self) -> None:
        """Clear the chat history."""
        self.chat_history = []

    def reload_dives(self) -> None:
        """Reload dives from storage and recreate tools."""
        self._load_dives()
        self.tools = self._create_tools()
        self.agent_executor = self._create_agent()

    def get_quick_stats(self) -> str:
        """Get a quick summary of the dive log.

        Returns:
            Summary string with basic statistics
        """
        if not self.dives:
            return "No dives in the log."

        # Calculate basic stats
        total_dives = len(self.dives)
        total_time_min = sum(d.basics.duration for d in self.dives) / 60

        depths = []
        for dive in self.dives:
            if dive.timeline.depths:
                depths.append(max(dive.timeline.depths))

        avg_depth = sum(depths) / len(depths) if depths else 0
        max_depth = max(depths) if depths else 0

        # Date range
        dates = [d.basics.start_time for d in self.dives]
        first_dive = min(dates).strftime("%Y-%m-%d")
        last_dive = max(dates).strftime("%Y-%m-%d")

        return (
            f"Dive Log Summary:\n"
            f"- Total Dives: {total_dives}\n"
            f"- Total Dive Time: {total_time_min:.0f} minutes ({total_time_min/60:.1f} hours)\n"
            f"- Average Max Depth: {avg_depth:.1f}m\n"
            f"- Deepest Dive: {max_depth:.1f}m\n"
            f"- Date Range: {first_dive} to {last_dive}"
        )
