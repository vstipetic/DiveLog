# Next Steps: Agent System Implementation Plan

## Overview

This document outlines the detailed implementation plan for completing the statistics agent system. The agent will enable natural language queries about dive data using LangChain and a Pydantic-based tool architecture.

## Key Architectural Decisions

1. **Keep existing attrs-based Dive/Gear models** (pickle compatibility)
2. **Use Pydantic for agent layer** (LangChain tools, validation)
3. **Wrap existing FilterFunctions** (preserve GUI compatibility, add agent-friendly layer)
4. **Build Streamlit UI in parallel** (keep Tkinter working during migration)

## Implementation Phases

### Phase 1: Fix Existing Bugs (Priority: Critical) ✅ COMPLETED

#### 1.1 Fix and Refactor Filter Functions

**File**: `Utilities/FilterFunctions.py`

**Approach**: Fix bugs AND refactor for better design. The Tkinter GUI is early alpha and will be replaced by Streamlit, so we can break compatibility if it improves code quality.

**Issues to Fix**:
1. Duplicate `dive_was_longer_than` function (lines 11 and 32) - DELETE the duplicate
2. Incorrect attribute access: `dive_data.basic_information` → `dive_data.basics`
3. Function signatures could be improved (consider renaming for clarity)

**Refactoring Options**:
- Rename functions for clarity (e.g., `dive_exceeds_depth` vs `dive_was_deeper_than`)
- Add type hints if missing
- Improve docstrings
- Consider consolidating similar functions

**Why we can break GUI compatibility**:
- Tkinter GUI is early alpha
- Will be replaced by Streamlit soon
- Better to have clean code now than preserve technical debt
- Any GUI updates needed are minimal

**If GUI breaks**: Update the GUI code to use the new function signatures. This is acceptable.

#### 1.2 Resolve DiveFilterer Duplication

**Files**: `DiveFilterer.py` (root) and `Utilities/DiveFilterer.py`

**Action**: 
- Keep root `DiveFilterer.py` as the canonical implementation
- Remove or deprecate `Utilities/DiveFilterer.py`
- Update any imports if needed

### Phase 2: Pydantic Schemas & Statistics Functions (Priority: High) ✅ COMPLETED

#### 2.1 Create Schema Directory

**New Directory**: `Utilities/Schemas/`

**Purpose**: Pydantic models for agent layer (separate from attrs-based data models)

**Files to Create**:
- `__init__.py` - Package init
- `ToolInputs.py` - Input schemas for all tools
- `ToolOutputs.py` - Output schemas for tool results
- `AgentModels.py` - Agent-friendly representations of dives/gear

**Why Separate from Dive/Gear Classes?**
- Dive/Gear use attrs (pickle compatibility)
- Agent layer uses Pydantic (validation, LangChain integration)
- Conversion happens at tool boundary

#### 2.2 Implement Input Schemas

**File**: `Utilities/Schemas/ToolInputs.py`
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DepthFilterInput(BaseModel):
    """Filter dives by depth range."""
    min_depth_meters: float = Field(gt=0, description="Minimum depth in meters")
    max_depth_meters: Optional[float] = Field(None, ge=0, description="Maximum depth in meters")

class DateRangeInput(BaseModel):
    """Filter dives by date range."""
    start_date: datetime = Field(description="Start date (inclusive)")
    end_date: Optional[datetime] = Field(None, description="End date (inclusive)")

class GearFilterInput(BaseModel):
    """Filter dives by gear used."""
    gear_name: str = Field(description="Name of gear item")
    gear_type: Optional[str] = Field(None, description="Type: mask, suit, gloves, boots, bcd, fins")

class DurationFilterInput(BaseModel):
    """Filter dives by duration."""
    min_duration_minutes: float = Field(gt=0, description="Minimum duration in minutes")
    max_duration_minutes: Optional[float] = Field(None, description="Maximum duration in minutes")

class BuddyFilterInput(BaseModel):
    """Filter dives by buddy."""
    buddy_name: str = Field(description="Name of dive buddy")

class LocationFilterInput(BaseModel):
    """Filter dives by location."""
    location_name: str = Field(description="Location name (partial match)")

class DepthThresholdInput(BaseModel):
    """Input for depth threshold calculations."""
    depth_threshold_meters: float = Field(gt=0, description="Depth threshold in meters")
```

#### 2.3 Implement Output Schemas

**File**: `Utilities/Schemas/ToolOutputs.py`
```python
from pydantic import BaseModel, Field
from typing import List, Tuple, Optional, Dict
from datetime import datetime

class DiveSummary(BaseModel):
    """Agent-friendly dive summary (not full Dive object)."""
    dive_id: str  # Could be filename or generated ID
    date: datetime
    max_depth_meters: float
    duration_minutes: float
    location: str
    buddy: Optional[str]
    
    @classmethod
    def from_dive(cls, dive, dive_id: str) -> 'DiveSummary':
        """Convert attrs Dive to Pydantic DiveSummary.
        
        Args:
            dive: attrs-based Dive object
            dive_id: Unique identifier for this dive
            
        Returns:
            Pydantic DiveSummary model
        """
        return cls(
            dive_id=dive_id,
            date=dive.basics.start_time,
            max_depth_meters=max(dive.timeline.depths) if dive.timeline.depths else 0.0,
            duration_minutes=dive.basics.duration / 60,
            location=dive.location.name,
            buddy=dive.people.buddy
        )

class FilterResult(BaseModel):
    """Results from filtering operation with metadata."""
    matching_dives: List[DiveSummary]
    total_count: int
    depth_range: Optional[Tuple[float, float]] = Field(None, description="(min_depth, max_depth) in meters")
    date_range: Optional[Tuple[datetime, datetime]] = Field(None, description="(earliest, latest) dive date")
    average_depth: Optional[float] = Field(None, description="Average max depth of matching dives")

class StatisticsResult(BaseModel):
    """Results from statistics calculation."""
    stat_type: str
    value: float
    unit: str  # "meters", "minutes", "dives", etc.
    breakdown: Optional[Dict[str, float]] = Field(None, description="For grouped statistics (e.g., by year, month, location)")

class GearSummary(BaseModel):
    """Agent-friendly gear summary."""
    gear_id: str
    name: str
    gear_type: str  # mask, suit, gloves, boots, bcd, fins
    total_dives: int
    total_dive_time_minutes: int
    
    @classmethod
    def from_gear(cls, gear, gear_id: str, gear_type: str) -> 'GearSummary':
        """Convert attrs Gear to Pydantic GearSummary."""
        return cls(
            gear_id=gear_id,
            name=gear.name,
            gear_type=gear_type,
            total_dives=gear.number_of_dives,
            total_dive_time_minutes=gear.total_dive_time
        )
```

#### 2.4 Implement Agent Models

**File**: `Utilities/Schemas/AgentModels.py`
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from Utilities.Schemas.ToolOutputs import DiveSummary

class DepthProfile(BaseModel):
    """Simplified depth profile for agent responses."""
    timestamps_seconds: List[float]
    depths_meters: List[float]
    max_depth: float
    average_depth: float

class DiveDetails(BaseModel):
    """Extended dive information for detailed queries."""
    summary: DiveSummary
    depth_profile: Optional[DepthProfile] = None
    gas_type: str
    start_pressure: int
    end_pressure: int
    buddy: Optional[str]
    divemaster: Optional[str]
    group_members: Optional[List[str]] = None
    
class QueryResponse(BaseModel):
    """Standardized response format for agent."""
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None
```

#### 2.5 Implement Statistics Functions

**File**: `Utilities/StatisticsFunctions.py`

**Purpose**: Calculate aggregate statistics on lists of dives. These functions accept filtered dive lists (filtering is handled by FilterFunctions.py) and return calculated statistics.

**Design Philosophy**:
- Filtering (by year, location, buddy, etc.) → `FilterFunctions.py`
- Statistics (averages, totals, counts) → `StatisticsFunctions.py`
- Agent workflow: Filter dives → Calculate statistics on filtered set

**Functions to Implement**:
```python
from typing import List
from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Schemas.ToolOutputs import StatisticsResult

def load_all_dives(dive_folder: str = "Storage/Dives") -> List[Dive]:
    """Load all dive pickle files from storage.
    
    Args:
        dive_folder: Path to directory containing dive pickle files
        
    Returns:
        List of Dive objects
    """
    # Implementation: Load all .pickle files from dive_folder

def average_depth(dives: List[Dive]) -> StatisticsResult:
    """Calculate average maximum depth across all dives.
    
    Args:
        dives: List of Dive objects (pre-filtered if needed)
        
    Returns:
        StatisticsResult with average depth in meters
    """
    # Implementation: Average of max(dive.timeline.depths) for each dive

def max_depth(dives: List[Dive]) -> StatisticsResult:
    """Find maximum depth across all dives.
    
    Args:
        dives: List of Dive objects
        
    Returns:
        StatisticsResult with maximum depth in meters
    """
    # Implementation: Max of max(dive.timeline.depths) across all dives

def min_depth(dives: List[Dive]) -> StatisticsResult:
    """Find minimum depth across all dives.
    
    Args:
        dives: List of Dive objects
        
    Returns:
        StatisticsResult with minimum depth in meters
    """
    # Implementation: Min of max(dive.timeline.depths) across all dives

def total_dive_time(dives: List[Dive]) -> StatisticsResult:
    """Calculate total dive time in minutes.
    
    Args:
        dives: List of Dive objects
        
    Returns:
        StatisticsResult with total time in minutes
    """
    # Implementation: Sum of dive.basics.duration (convert seconds to minutes)

def dive_count(dives: List[Dive]) -> StatisticsResult:
    """Count total number of dives.
    
    Args:
        dives: List of Dive objects
        
    Returns:
        StatisticsResult with count
    """
    # Implementation: len(dives)

def average_duration(dives: List[Dive]) -> StatisticsResult:
    """Calculate average dive duration.
    
    Args:
        dives: List of Dive objects
        
    Returns:
        StatisticsResult with average duration in minutes
    """
    # Implementation: Average of dive.basics.duration (convert to minutes)

def longest_dive(dives: List[Dive]) -> StatisticsResult:
    """Find longest dive duration.
    
    Args:
        dives: List of Dive objects
        
    Returns:
        StatisticsResult with longest duration in minutes
    """
    # Implementation: Max of dive.basics.duration

def shortest_dive(dives: List[Dive]) -> StatisticsResult:
    """Find shortest dive duration.
    
    Args:
        dives: List of Dive objects
        
    Returns:
        StatisticsResult with shortest duration in minutes
    """
    # Implementation: Min of dive.basics.duration

def deepest_dive(dives: List[Dive]) -> StatisticsResult:
    """Find deepest dive (same as max_depth but returns full context).
    
    Args:
        dives: List of Dive objects
        
    Returns:
        StatisticsResult with deepest dive depth in meters
    """
    # Implementation: Same as max_depth (kept for semantic clarity)

def shallowest_dive(dives: List[Dive]) -> StatisticsResult:
    """Find shallowest dive.
    
    Args:
        dives: List of Dive objects
        
    Returns:
        StatisticsResult with shallowest dive depth in meters
    """
    # Implementation: Min of max(dive.timeline.depths)

def time_below_depth(dives: List[Dive], depth_threshold: float) -> StatisticsResult:
    """Calculate total time spent below specified depth across all dives.
    
    Args:
        dives: List of Dive objects
        depth_threshold: Depth threshold in meters
        
    Returns:
        StatisticsResult with time in minutes
    """
    # Implementation: Sum time where dive.timeline.depths > threshold
    # Use timestamps to calculate duration between depth samples

def average_temperature(dives: List[Dive]) -> StatisticsResult:
    """Calculate average water temperature across all dives.
    
    Args:
        dives: List of Dive objects
        
    Returns:
        StatisticsResult with average temperature in Celsius
    """
    # Implementation: Average of dive.timeline.temperatures values
```

**Implementation Notes**:
- All functions accept `List[Dive]` (attrs objects) as input
- All functions return `StatisticsResult` (Pydantic) as output
- Filtering by criteria (year, location, buddy) is NOT done here - agent uses FilterFunctions.py first
- Handle edge cases: empty lists, missing timeline data, None values
- Include comprehensive docstrings and type hints

### Phase 3: Tool System (Priority: High) ✅ COMPLETED

#### 3.1 Create Tools Directory

**New Directory**: `Utilities/Tools/`

**Files to Create**:
- `__init__.py`
- `BaseTool.py` - Base class for all tools (if needed)
- `FilterTool.py` - Dive filtering tool
- `StatisticsTool.py` - Statistics calculation tool
- `SearchTool.py` - Dive search tool

#### 3.2 Implement Filter Tool

**File**: `Utilities/Tools/FilterTool.py`

**Purpose**: LangChain tool for filtering dives

**Approach**: Wraps existing FilterFunctions, returns Pydantic models
```python
from typing import List, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Schemas.ToolInputs import DepthFilterInput, DateRangeInput, DurationFilterInput
from Utilities.Schemas.ToolOutputs import FilterResult, DiveSummary
from Utilities.FilterFunctions import (
    dive_was_deeper_than,
    dive_was_shallower_than,
    dive_was_longer_than,
    dive_was_shorter_than,
    dive_was_after_date,
    dive_was_before_date
)

class FilterDivesByDepthInput(BaseModel):
    """Input for filtering dives by depth."""
    min_depth: float = Field(description="Minimum depth in meters")
    max_depth: Optional[float] = Field(None, description="Maximum depth in meters (optional)")

class FilterDivesByDepthTool(BaseTool):
    name = "filter_dives_by_depth"
    description = "Filter dives by depth range. Returns dives where maximum depth is within specified range."
    args_schema = FilterDivesByDepthInput
    
    dives: List[Dive] = Field(default_factory=list)
    
    def _run(self, min_depth: float, max_depth: Optional[float] = None) -> FilterResult:
        """Filter dives by depth."""
        # Use existing filter functions
        filtered = [d for d in self.dives if dive_was_deeper_than(d, min_depth)]
        
        if max_depth is not None:
            filtered = [d for d in filtered if dive_was_shallower_than(d, max_depth)]
        
        if not filtered:
            return FilterResult(
                matching_dives=[],
                total_count=0,
                depth_range=None,
                date_range=None,
                average_depth=None
            )
        
        # Convert to summaries
        summaries = [DiveSummary.from_dive(d, f"dive_{i}") for i, d in enumerate(filtered)]
        
        # Calculate metadata
        depths = [s.max_depth_meters for s in summaries]
        dates = [s.date for s in summaries]
        
        return FilterResult(
            matching_dives=summaries,
            total_count=len(summaries),
            depth_range=(min(depths), max(depths)),
            date_range=(min(dates), max(dates)),
            average_depth=sum(depths) / len(depths)
        )

# Similar tools for other filters:
# - FilterDivesByDateTool
# - FilterDivesByDurationTool
# - FilterDivesByBuddyTool
# - FilterDivesByLocationTool
```

#### 3.3 Implement Statistics Tool

**File**: `Utilities/Tools/StatisticsTool.py`
```python
from typing import List
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Schemas.ToolOutputs import StatisticsResult
import Utilities.StatisticsFunctions as stats

class CalculateStatisticInput(BaseModel):
    """Input for calculating statistics."""
    stat_type: str = Field(
        description="Type of statistic to calculate: average_depth, max_depth, total_time, dive_count, etc."
    )

class CalculateStatisticTool(BaseTool):
    name = "calculate_statistic"
    description = """Calculate various statistics about dives. 
    Supported statistics: average_depth, max_depth, total_time, dive_count, average_duration, 
    dives_by_year, dives_by_month, dives_by_location, dives_by_buddy."""
    args_schema = CalculateStatisticInput
    
    dives: List[Dive] = Field(default_factory=list)
    
    def _run(self, stat_type: str) -> StatisticsResult:
        """Calculate the requested statistic."""
        stat_functions = {
            "average_depth": stats.average_depth,
            "max_depth": stats.max_depth,
            "total_time": stats.total_dive_time,
            "dive_count": stats.dive_count,
            "average_duration": stats.average_duration,
            "dives_by_year": stats.dives_by_year,
            "dives_by_month": stats.dives_by_month,
            "dives_by_location": stats.dives_by_location,
            "dives_by_buddy": stats.dives_by_buddy,
        }
        
        if stat_type not in stat_functions:
            return StatisticsResult(
                stat_type=stat_type,
                value=0.0,
                unit="unknown",
                error=f"Unknown statistic type: {stat_type}"
            )
        
        return stat_functions[stat_type](self.dives)
```

#### 3.4 Implement Search Tool

**File**: `Utilities/Tools/SearchTool.py`
```python
from typing import List
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Schemas.ToolOutputs import FilterResult, DiveSummary

class SearchDivesInput(BaseModel):
    """Input for searching dives."""
    query: str = Field(description="Search query (location name, buddy name, etc.)")
    search_field: str = Field(description="Field to search: location, buddy, description")

class SearchDivesTool(BaseTool):
    name = "search_dives"
    description = "Search dives by text query in location, buddy, or description fields."
    args_schema = SearchDivesInput
    
    dives: List[Dive] = Field(default_factory=list)
    
    def _run(self, query: str, search_field: str) -> FilterResult:
        """Search dives by text."""
        query_lower = query.lower()
        filtered = []
        
        for dive in self.dives:
            if search_field == "location":
                if dive.location.name and query_lower in dive.location.name.lower():
                    filtered.append(dive)
            elif search_field == "buddy":
                if dive.people.buddy and query_lower in dive.people.buddy.lower():
                    filtered.append(dive)
            elif search_field == "description":
                if dive.location.description and query_lower in dive.location.description.lower():
                    filtered.append(dive)
        
        if not filtered:
            return FilterResult(
                matching_dives=[],
                total_count=0
            )
        
        summaries = [DiveSummary.from_dive(d, f"dive_{i}") for i, d in enumerate(filtered)]
        
        return FilterResult(
            matching_dives=summaries,
            total_count=len(summaries)
        )
```

### Phase 4: LangChain Agent Implementation (Priority: High) ✅ COMPLETED

#### 4.1 Update Statistics Agent

**File**: `Utilities/StatisticsAgent.py`

**Complete Rewrite with LangChain**:
```python
from pathlib import Path
from typing import List, Optional
import pickle

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Tools.FilterTool import FilterDivesByDepthTool
from Utilities.Tools.StatisticsTool import CalculateStatisticTool
from Utilities.Tools.SearchTool import SearchDivesTool

class StatisticsAgent:
    """AI agent for querying dive statistics using natural language."""
    
    def __init__(self, api_key: str, dive_folder: str = "Storage/Dives", provider: str = "gemini"):
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
        
        # Load dives
        self._load_dives()
        
        # Initialize LLM
        self.llm = self._create_llm()
        
        # Initialize tools
        self.tools = self._create_tools()
        
        # Create agent
        self.agent_executor = self._create_agent()
    
    def _load_dives(self):
        """Load all dive pickle files from storage."""
        self.dives = []
        
        for pickle_file in self.dive_folder.glob("*.pickle"):
            try:
                with open(pickle_file, 'rb') as f:
                    dive = pickle.load(f)
                    self.dives.append(dive)
            except Exception as e:
                print(f"Error loading {pickle_file}: {e}")
        
        print(f"Loaded {len(self.dives)} dives")
    
    def _create_llm(self):
        """Create LLM based on provider."""
        if self.provider == "gemini":
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",
                google_api_key=self.api_key,
                temperature=0
            )
        elif self.provider == "openai":
            return ChatOpenAI(
                model="gpt-4",
                api_key=self.api_key,
                temperature=0
            )
        elif self.provider == "claude":
            return ChatAnthropic(
                model="claude-sonnet-4-20250514",
                api_key=self.api_key,
                temperature=0
            )
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _create_tools(self):
        """Create tool instances with dive data."""
        return [
            FilterDivesByDepthTool(dives=self.dives),
            CalculateStatisticTool(dives=self.dives),
            SearchDivesTool(dives=self.dives)
        ]
    
    def _create_agent(self):
        """Create LangChain agent with tools."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful dive log assistant. You have access to tools to filter, search, 
            and calculate statistics about the user's dives. When answering questions:
            
            1. Use the appropriate tools to gather information
            2. Provide clear, concise answers with specific numbers
            3. Include relevant context (dates, locations, etc.)
            4. Format depths in meters and times in minutes
            5. If you can't find exact information, explain what you can provide
            
            The user has {num_dives} dives in their log."""),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True
        )
    
    def process_query(self, query: str) -> str:
        """Process a natural language query about dives.
        
        Args:
            query: Natural language question about dives
            
        Returns:
            Natural language response with answer
        """
        try:
            result = self.agent_executor.invoke({
                "input": query,
                "num_dives": len(self.dives)
            })
            return result["output"]
        except Exception as e:
            return f"Error processing query: {str(e)}"
```

### Phase 5: Streamlit UI (Priority: Medium) ✅ COMPLETED

#### 5.1 Create Streamlit App

**New File**: `streamlit_app.py`

**Initial Implementation** (AI Query tab only):
```python
import streamlit as st
import os
from Utilities.StatisticsAgent import StatisticsAgent
from Utilities.APIKeyDetector import detect_api_keys

st.set_page_config(page_title="DiveLog", layout="wide")

st.title("🤿 DiveLog - Dive Statistics Assistant")

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    
    # API Key detection
    api_keys = detect_api_keys()
    
    if api_keys:
        selected_api = st.selectbox("Select LLM Provider", list(api_keys.keys()))
        api_key = api_keys[selected_api]
        
        # Map service names to provider codes
        provider_map = {
            "OpenAI": "openai",
            "Gemini": "gemini",
            "Test API": "gemini"  # Default
        }
        provider = provider_map.get(selected_api, "gemini")
    else:
        st.error("No API keys found in environment variables")
        st.stop()
    
    st.divider()
    st.caption(f"Using {selected_api}")

# Initialize agent (with caching)
@st.cache_resource
def get_agent(_api_key, _provider):
    return StatisticsAgent(_api_key, dive_folder="Storage/Dives", provider=_provider)

agent = get_agent(api_key, provider)

st.info(f"📊 Loaded {len(agent.dives)} dives from your log")

# Chat interface
st.subheader("Ask about your dives")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to know about your dives?"):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your dives..."):
            response = agent.process_query(prompt)
        st.markdown(response)
    
    # Add assistant response to chat
    st.session_state.messages.append({"role": "assistant", "content": response})

# Example queries
with st.expander("Example Questions"):
    st.markdown("""
    - What's my average dive depth?
    - How many dives did I do in 2024?
    - Show me all dives deeper than 30 meters
    - What's my total dive time?
    - Who is my most common dive buddy?
    - How much time have I spent below 20 meters?
    """)
```

#### 5.2 Add Additional Tabs (Later)

**Tabs to add**:
- Add Dive (port from Tkinter)
- Add Gear (port from Tkinter)
- Statistics Dashboard (visualizations)

### Phase 6: Testing (Priority: Medium)

#### 6.1 Create Test Directory

**New Directory**: `tests/`

**Files**:
- `__init__.py`
- `conftest.py` - Pytest fixtures
- `test_filter_functions.py`
- `test_statistics_functions.py`
- `test_tools.py`
- `test_schemas.py`
- `test_agent.py`

#### 6.2 Create Test Fixtures

**File**: `tests/conftest.py`
```python
import pytest
from datetime import datetime
from Utilities.ClassUtils.DiveClass import (
    Dive, DiveTimeline, DiveBasicInformation, 
    People, Location, Gasses, UsedGear
)
from Utilities.ClassUtils.GearClasses import Suit, Mask

@pytest.fixture
def sample_dive():
    """Create a sample dive for testing."""
    timeline = DiveTimeline(
        depths=[0, 5, 10, 15, 20, 25, 30, 25, 20, 15, 10, 5, 0],
        temperatures=[20.0] * 13,
        n2_loads=[0] * 13,
        cns_loads=[0] * 13,
        timestamps=[i * 60 for i in range(13)]  # One minute intervals
    )
    
    basics = DiveBasicInformation(
        duration=12 * 60,  # 12 minutes
        start_time=datetime(2024, 1, 15, 10, 0),
        end_time=datetime(2024, 1, 15, 10, 12)
    )
    
    people = People(buddy="John Doe", divemaster=None, group=set())
    location = Location(name="Test Site", entry=None, exit=None, description=None)
    gasses = Gasses(gas="air", start_pressure=200, end_pressure=150)
    
    suit = Suit(name="Test Suit", unique_id="suit-1", thickness=5, size=10)
    gear = UsedGear(suit=suit, weights=5.0)
    
    return Dive(
        people=people,
        basics=basics,
        timeline=timeline,
        location=location,
        gasses=gasses,
        gear=gear
    )

@pytest.fixture
def sample_dives():
    """Create multiple sample dives."""
    # Create 3 different dives with varying depths and dates
    # ... implementation
    pass
```

#### 6.3 Test Filter Functions

**File**: `tests/test_filter_functions.py`
```python
import pytest
from datetime import datetime
from Utilities.FilterFunctions import (
    dive_was_deeper_than,
    dive_was_longer_than,
    dive_was_after_date
)

def test_dive_was_deeper_than(sample_dive):
    """Test depth filtering."""
    assert dive_was_deeper_than(sample_dive, 20.0) == True
    assert dive_was_deeper_than(sample_dive, 35.0) == False

def test_dive_was_longer_than(sample_dive):
    """Test duration filtering."""
    assert dive_was_longer_than(sample_dive, 10 * 60) == True  # 10 minutes
    assert dive_was_longer_than(sample_dive, 15 * 60) == False  # 15 minutes

def test_dive_was_after_date(sample_dive):
    """Test date filtering."""
    assert dive_was_after_date(sample_dive, datetime(2024, 1, 1)) == True
    assert dive_was_after_date(sample_dive, datetime(2024, 2, 1)) == False
```

#### 6.4 Test Statistics Functions

**File**: `tests/test_statistics_functions.py`
```python
import pytest
from Utilities.StatisticsFunctions import average_depth, dive_count, total_dive_time

def test_average_depth(sample_dives):
    """Test average depth calculation."""
    result = average_depth(sample_dives)
    assert result.stat_type == "average_depth"
    assert result.unit == "meters"
    assert result.value > 0

def test_dive_count(sample_dives):
    """Test dive counting."""
    result = dive_count(sample_dives)
    assert result.stat_type == "dive_count"
    assert result.value == len(sample_dives)

def test_total_dive_time(sample_dives):
    """Test total time calculation."""
    result = total_dive_time(sample_dives)
    assert result.stat_type == "total_dive_time"
    assert result.unit == "minutes"
```

### Phase 7: Error Handling & Polish (Priority: Low)

#### 7.1 Add Input Validation

- Validate depth values (> 0)
- Validate date ranges
- Check for empty dive lists
- Handle missing fields gracefully

#### 7.2 Improve Error Messages

- User-friendly messages in Streamlit
- Detailed logging for debugging
- Suggestions for fixing errors

#### 7.3 Add Data Validation

**Optional File**: `Utilities/Validators/DiveValidator.py`
```python
from Utilities.ClassUtils.DiveClass import Dive

def validate_dive(dive: Dive) -> tuple[bool, list[str]]:
    """Validate dive data integrity.
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required fields
    if not dive.timeline.depths:
        errors.append("Missing depth data")
    
    if dive.basics.duration <= 0:
        errors.append("Invalid duration")
    
    # Check data consistency
    if dive.timeline.depths and max(dive.timeline.depths) <= 0:
        errors.append("Invalid depth values")
    
    return len(errors) == 0, errors
```

## Dependencies to Add

Update `pyproject.toml`:
```toml
[tool.poetry.dependencies]
python = "^3.11"
fitparse = "^1.2.0"
attrs = "^25.1.0"

# LangChain and LLM providers
langchain = "^0.3.0"
langchain-core = "^0.3.0"
langchain-google-genai = "^2.0.0"
langchain-openai = "^0.2.0"
langchain-anthropic = "^0.3.0"

# Pydantic for schemas
pydantic = "^2.0.0"

# Streamlit for UI
streamlit = "^1.40.0"

# Optional: visualization
matplotlib = { version = "^3.8.0", optional = true }
plotly = { version = "^5.18.0", optional = true }

[tool.poetry.group.dev.dependencies]
pytest = "^7.0.0"
pytest-cov = "^4.0.0"
```

## Implementation Timeline

**Week 1: Foundation**
- Day 1-2: Fix bugs (Phase 1)
- Day 3-5: Create Pydantic schemas (Phase 2.1-2.3)
- Day 6-7: Implement statistics functions (Phase 2.4-2.5)

**Week 2: Tools & Agent**
- Day 8-10: Create tool implementations (Phase 3)
- Day 11-14: Build LangChain agent (Phase 4)

**Week 3: UI & Testing**
- Day 15-17: Create Streamlit app (Phase 5)
- Day 18-21: Add tests (Phase 6)

**Week 4: Polish**
- Day 22-24: Error handling (Phase 7)
- Day 25-28: Documentation and refinement

## Success Criteria

✅ **Phase 1 Complete**:
- All filter function bugs fixed
- Tests pass for filter functions

✅ **Phase 2 Complete**:
- Pydantic schemas created and validated
- All statistics functions implemented
- Functions accept attrs Dive, return Pydantic results

✅ **Phase 3 Complete**:
- All tools implemented as LangChain tools
- Tools properly wrap existing functions
- Pydantic validation works

✅ **Phase 4 Complete**:
- Agent processes natural language queries
- Multi-LLM support works (Gemini, OpenAI, Claude)
- Tool calling functions correctly

✅ **Phase 5 Complete**:
- Streamlit UI displays chat interface
- Agent integration works in UI
- Chat history persists during session

✅ **Phase 6 Complete**:
- Test suite covers all new code
- All tests pass
- >80% code coverage

## Notes

- **Preserve pickle compatibility**: Never change attrs-based Dive/Gear classes
- **Use Pydantic only for agent layer**: Keep clear boundary between storage and agent
- **Fix and simplify, GUI will adap**: Existing filtering functions should be simplified and prepared for agentic use. GUI will adapt
- **Test incrementally**: Don't move to next phase until current tests pass
- **Document as you go**: Add docstrings to all new functions
