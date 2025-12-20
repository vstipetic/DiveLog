# Existing Code Documentation

## What's Already Implemented

### Core Data Models

#### Dive Class (`Utilities/ClassUtils/DiveClass.py`)

**Location**: `Utilities/ClassUtils/DiveClass.py`

**Framework**: Uses `attrs` library (NOT Pydantic)

**Classes**:
- `Dive` - Main dive data structure
- `DiveTimeline` - Time-series dive data
- `DiveBasicInformation` - Basic dive metadata
- `People` - People involved in dive
- `Location` - Dive location information
- `Gasses` - Gas mixture information
- `UsedGear` - Gear used during dive

**Key Attributes**:
- `Dive.timeline.depths`: List[float] - Depths in meters
- `Dive.timeline.timestamps`: List[float] - Seconds from dive start
- `Dive.basics.duration`: float - Dive duration in seconds
- `Dive.basics.start_time`: datetime - Dive start time
- `Dive.basics.end_time`: datetime - Dive end time
- `Dive.people.buddy`: str - Dive buddy name
- `Dive.people.group`: Set[str] - Group members
- `Dive.location.entry`: Optional[Tuple[float, float]] - GPS coordinates
- `Dive.gasses.gas`: str - 'air', 'nitrox', or 'trimix'
- `Dive.gasses.start_pressure`: int - Starting pressure in bar
- `Dive.gear.suit`: Suit object - Wetsuit/drysuit used

**DO NOT MODIFY**: The core data structure is stable. Any changes would break serialization compatibility. These classes use attrs and must remain attrs-based for pickle compatibility.

#### Gear Classes (`Utilities/ClassUtils/GearClasses.py`)

**Location**: `Utilities/ClassUtils/GearClasses.py`

**Framework**: Uses `attrs` library (NOT Pydantic)

**Classes**:
- `Gear` - Base gear class
- `Mask` - Diving mask
- `Suit` - Wetsuit/drysuit (thickness, size)
- `Gloves` - Diving gloves (thickness, GloveSize enum)
- `Boots` - Diving boots (thickness, size)
- `BCD` - Buoyancy Control Device (stub)
- `Fins` - Diving fins (stub)

**Enums**:
- `GloveSize`: S, M, L, XL
- `GearPieces`: Mask, Suit, Gloves, Boots, BCD, Fins

**Key Attributes**:
- `Gear.name`: str - Unique identifier
- `Gear.unique_id`: str - UUID4
- `Gear.total_dive_time`: int - Minutes underwater
- `Gear.number_of_dives`: int - Dive count
- `Gear.is_rental`: bool - Rental flag

**DO NOT MODIFY**: Gear structure is used throughout the application. Changes would require migration of existing pickle files. These classes use attrs and must remain attrs-based.

### Parsers

#### Garmin Dive Parser (`Utilities/Parsers/GarminDiveParser.py`)

**Location**: `Utilities/Parsers/GarminDiveParser.py`

**Functions**:
- `parse_garmin_dive(file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dive`
- `parse_timeline(fit_file: FitFile) -> tuple[DiveTimeline, datetime]`
- `parse_basic_info(timeline: DiveTimeline, start_time: datetime) -> DiveBasicInformation`
- `parse_people(metadata: Dict[str, Any]) -> People`
- `parse_location(fit_file: FitFile, metadata: Dict[str, Any]) -> Location`
- `determine_gas_type(oxygen: int, helium: int) -> str`
- `semicircles_to_degrees(semicircles: float) -> float`

**What It Does**:
- Parses Garmin .fit files using `fitparse` library
- Extracts timeline data (depths, temperatures, N2/CNS loads)
- Extracts GPS coordinates (entry only, exit not implemented)
- Determines gas type from O2/He percentages
- Creates complete `Dive` object from file and metadata

**Known Limitations**:
- Exit coordinates always None (not parsed from .fit file)
- Only supports Garmin .fit format
- Only processes first gas mixture (if multiple)

**DO NOT MODIFY**: This is the only parser implementation. Changes could break existing dive imports.

### Data Management

#### Add Dive (`Utilities/AddDive.py`)

**Location**: `Utilities/AddDive.py`

**Functions**:
- `add_dive(fit_file_path: str, output_path: str, ...) -> Dive`
  - Single dive import with full metadata
  - Accepts: buddy, divemaster, group, location details, gas pressures, gear references
  - Creates complete Dive object with enriched metadata
  
- `bulk_add_dives(fit_files_dir: str, output_dir: str) -> List[Dive]`
  - Multiple dive import from directory
  - Parses ONLY .fit file data (no metadata parameter)
  - Missing: People, Location details, Gas pressures, Gear associations
  - Use case: Quick statistical analysis of large dive collections

**Key Difference**: 
Manual import enriches .fit data with metadata. Bulk import is .fit-only parsing for volume analysis.

**What It Does**:
- Creates `Dive` objects from .fit files
- Loads gear objects from pickle files
- Serializes dives to pickle format
- Handles bulk imports from directory

**Serialization**:
- Uses Python `pickle` module
- Saves to `.pickle` files
- Gear objects are loaded and embedded in dive objects

**DO NOT MODIFY**: This is the core data creation logic. Changes would affect all dive creation.

#### Add Gear (`Utilities/AddGear.py`)

**Location**: `Utilities/AddGear.py`

**Functions**:
- `add_mask(name: str, output_path: str, ...) -> None`
- `add_suit(name: str, thickness: int, size: int, output_path: str, ...) -> None`
- `add_gloves(name: str, thickness: int, size: Gear.GloveSize, output_path: str, ...) -> None`
- `add_boots(name: str, thickness: int, size: int, output_path: str, ...) -> None`

**What It Does**:
- Creates gear objects
- Serializes to pickle files
- Initializes with default values (0 dives, 0 time)

**DO NOT MODIFY**: Core gear creation logic.

### Filtering System

#### Filter Functions (`Utilities/FilterFunctions.py`)

**Location**: `Utilities/FilterFunctions.py`

**Functions** (all accept `Dive`, return `bool`):
- `dive_was_deeper_than(dive_data, depth)` - Max depth > threshold
- `dive_was_shallower_than(dive_data, depth)` - Max depth < threshold
- `dive_was_longer_than(dive_data, time)` - Duration > threshold (seconds)
- `dive_was_shorter_than(dive_data, time)` - Duration < threshold (seconds)
- `dive_was_after_date(dive_data, date)` - Dive after date
- `dive_was_before_date(dive_data, date)` - Dive before date
- `dive_was_between_dates(dive_data, start_date, end_date)` - Dive in date range
- `dive_was_between_times(dive_data, start_time, end_time)` - Dive in time range
- `dive_was_deeper_than_for_duration(dive_data, depth, duration)` - Depth AND duration thresholds
- `dive_had_buddy(dive_data, buddy_name)` - Buddy name match (case-insensitive)
- `dive_was_at_location(dive_data, location_name)` - Location match (case-insensitive)
- `dive_used_gas(dive_data, gas_type)` - Gas type match

**Status**: ✅ All bugs fixed (duplicate function removed, attribute access corrected)

**CAN MODIFY**: Add new filter functions as needed. Wrapped by LangChain tools.

#### Dive Filterer (Root) (`DiveFilterer.py`)

**Location**: `DiveFilterer.py` (root directory)

**Functions**:
- `get_filter_function(filter_name: str) -> Callable` - Get filter function by name
- `filter_dives(dives, filter_names, filter_params) -> List[Dive]` - Apply multiple filters
- `apply_single_filter(dives, filter_name, **kwargs) -> List[Dive]` - Apply single filter

**Filter Map** (FILTER_MAP constant):
- 'deeper_than', 'shallower_than', 'longer_than', 'shorter_than'
- 'after_date', 'before_date', 'between_dates', 'between_times'
- 'deeper_than_for_duration', 'had_buddy', 'at_location', 'used_gas'

**Status**: ✅ Canonical implementation. `Utilities/DiveFilterer.py` was removed.

**CAN MODIFY**: Add new filter mappings when new filters are added.

### GUI Applications

#### Main Application (`MainApp.py`)

**Location**: `MainApp.py`

**Class**: `MainApplication(ttk.Frame)`

**Features**:
- Main menu with File and Statistics options
- Buttons for: Add New Dive, Bulk Import, Add New Gear, View Statistics
- Statistics window with tabs: AI Query, Basic Dive Stats, Basic Gear Stats
- API key selection dropdown in AI Query tab
- Chat interface for AI queries (UI only, not functional)

**Methods**:
- `open_dive_adder()` - Opens AddDiveApp window
- `open_gear_adder()` - Opens AddGearApp window
- `show_statistics()` - Opens statistics window
- `bulk_import_dives()` - Bulk import dialog
- `populate_dive_stats()` - Placeholder (shows "coming soon")
- `populate_gear_stats()` - Placeholder (shows "coming soon")

**DO NOT MODIFY**: Main application structure. Only extend functionality. This will be deprecated when Streamlit app is complete.

#### Add Dive App (`AddDiveApp.py`)

**Location**: `AddDiveApp.py`

**Class**: `DiveAdderApp(ttk.Frame)`

**Features**:
- .fit file selection
- Output location and filename
- Gear selection (Mask, Suit, Gloves, Boots)
- Metadata fields (Buddy, Divemaster, Group)
- Location fields (Name, Description)
- Gas information (Start/End Pressure)

**DO NOT MODIFY**: UI structure is complete. Only add validation or new fields if needed. Will be ported to Streamlit.

#### Add Gear App (`AddGearApp.py`)

**Location**: `AddGearApp.py`

**Class**: `GearAdderApp(ttk.Frame)`

**Features**:
- Gear type selection (Mask, Suit, Gloves, Boots)
- Common fields (Name, Description, Rental checkbox)
- Type-specific fields (Thickness, Size)
- Save location and filename

**DO NOT MODIFY**: UI structure is complete. Will be ported to Streamlit.

### Statistics Agent (LangChain-Powered)

#### Statistics Agent (`Utilities/StatisticsAgent.py`)

**Location**: `Utilities/StatisticsAgent.py`

**Class**: `StatisticsAgent`

**Implementation** (Fully functional):
- `__init__(api_key: str, dive_folder: str, provider: str)` - Initializes agent with LLM
- `_load_dives()` - Loads all .pickle files from dive folder
- `_create_llm()` - Creates LLM instance (Gemini, OpenAI, or Claude)
- `_create_tools()` - Creates LangChain tool instances with dive data
- `_create_agent()` - Creates LangChain AgentExecutor
- `process_query(query: str) -> str` - Processes natural language queries
- `clear_history()` - Clears chat history
- `reload_dives()` - Reloads dives and recreates tools
- `get_quick_stats() -> str` - Returns quick summary statistics

**Supported LLM Providers**:
- `gemini` - Google Gemini (gemini-1.5-flash)
- `openai` - OpenAI (gpt-4o-mini)
- `claude` - Anthropic Claude (claude-sonnet-4-20250514)

**DO NOT MODIFY** core structure. Can extend with new tools or features.

### Pydantic Schemas (`Utilities/Schemas/`)

**Location**: `Utilities/Schemas/`

**Purpose**: Pydantic models for agent layer (separate from attrs-based data models)

#### ToolInputs.py
Input schemas for LangChain tools:
- `DepthFilterInput` - Filter by depth range
- `DateRangeInput` - Filter by date range
- `GearFilterInput` - Filter by gear used
- `DurationFilterInput` - Filter by duration
- `BuddyFilterInput` - Filter by buddy
- `LocationFilterInput` - Filter by location
- `DepthThresholdInput` - Depth threshold calculations
- `StatisticTypeInput` - Select statistic type
- `SearchQueryInput` - Text search input

#### ToolOutputs.py
Output schemas for tool results:
- `DiveSummary` - Agent-friendly dive summary with `from_dive()` converter
- `FilterResult` - Results from filtering operations
- `StatisticsResult` - Results from statistics calculations
- `GearSummary` - Agent-friendly gear summary with `from_gear()` converter

#### AgentModels.py
Agent-friendly representations:
- `DepthProfile` - Simplified depth profile with `from_dive()` converter
- `DiveDetails` - Extended dive information with `from_dive()` converter
- `QueryResponse` - Standardized response format

**DO NOT MODIFY** without updating dependent tools.

### LangChain Tools (`Utilities/Tools/`)

**Location**: `Utilities/Tools/`

**Purpose**: LangChain BaseTool implementations wrapping FilterFunctions and StatisticsFunctions

#### FilterTool.py
- `FilterDivesByDepthTool` - Filter dives by depth range
- `FilterDivesByDateTool` - Filter dives by date range
- `FilterDivesByDurationTool` - Filter dives by duration
- `FilterDivesByBuddyTool` - Filter dives by buddy name
- `FilterDivesByLocationTool` - Filter dives by location name

#### StatisticsTool.py
- `CalculateStatisticTool` - Calculate various statistics (average_depth, max_depth, dive_count, etc.)
- `CalculateTimeBelowDepthTool` - Calculate time spent below a depth threshold

#### SearchTool.py
- `SearchDivesTool` - Search dives by text in location/buddy/description
- `GetDiveSummaryTool` - Get detailed summary of a specific dive
- `ListAllDivesTool` - List all dives with sorting options

**CAN MODIFY** to add new tools or improve existing ones.

### Statistics Functions (`Utilities/StatisticsFunctions.py`)

**Location**: `Utilities/StatisticsFunctions.py`

**Functions** (all accept `List[Dive]`, return `StatisticsResult`):
- `load_all_dives(dive_folder)` - Load all dive pickle files
- `average_depth(dives)` - Average maximum depth
- `max_depth(dives)` - Maximum depth across all dives
- `min_depth(dives)` - Minimum maximum depth
- `total_dive_time(dives)` - Total dive time in minutes
- `dive_count(dives)` - Count of dives
- `average_duration(dives)` - Average dive duration
- `longest_dive(dives)` - Longest dive duration
- `shortest_dive(dives)` - Shortest dive duration
- `deepest_dive(dives)` - Deepest dive (alias for max_depth)
- `shallowest_dive(dives)` - Shallowest dive (alias for min_depth)
- `time_below_depth(dives, threshold)` - Time spent below depth threshold
- `average_temperature(dives)` - Average water temperature
- `dives_by_year(dives)` - Count grouped by year
- `dives_by_month(dives)` - Count grouped by month
- `dives_by_location(dives)` - Count grouped by location
- `dives_by_buddy(dives)` - Count grouped by buddy
- `total_air_consumption(dives)` - Total air consumed
- `average_air_consumption_rate(dives)` - Average consumption rate

**Helper**:
- `STATISTICS_MAP` - Dictionary mapping stat names to functions
- `get_statistic(stat_type, dives)` - Get statistic by name

**CAN MODIFY** to add new statistics functions.

### Streamlit App (`streamlit_app.py`)

**Location**: `streamlit_app.py` (root)

**Purpose**: Modern web UI for AI-powered dive statistics queries

**Features**:
- API key detection and provider selection
- Chat interface for natural language queries
- Quick statistics cards
- Example query buttons
- Chat history management
- Dive reload functionality

**Run with**: `streamlit run streamlit_app.py`

**CAN MODIFY** to add new features or improve UI.

### API Key Detection

#### API Key Detector (`Utilities/APIKeyDetector.py`)

**Location**: `Utilities/APIKeyDetector.py`

**Function**: `detect_api_keys() -> Dict[str, str]`

**What It Does**:
- Scans environment variables for `OPENAI_API_KEY` and `GEMINI_API_KEY`
- Returns dictionary mapping service names to API keys
- Adds dummy 'Test API' if no keys found

**DO NOT MODIFY**: This is working correctly.

## Dependencies

### External Libraries

1. **fitparse** (>=1.2.0)
   - Used for: Parsing Garmin .fit files
   - Location: `Utilities/Parsers/GarminDiveParser.py`
   - **Required**: Yes, core functionality

2. **attrs** (^25.1.0)
   - Used for: Dataclass definitions
   - Location: All Dive/Gear class files
   - **Required**: Yes, core data models
   - **Note**: DO NOT replace with Pydantic (breaks pickle compatibility)

3. **google-generativeai** (^0.8.4)
   - Used for: LLM integration (planned)
   - Location: Not yet used
   - **Required**: For future agent implementation
   - **Note**: Will be wrapped with LangChain

4. **tkinter**
   - Used for: GUI
   - Location: All GUI files
   - **Required**: Yes, GUI functionality (Python standard library)
   - **Note**: Will be deprecated when Streamlit app is complete

5. **pickle**
   - Used for: Serialization
   - Location: All data management files
   - **Required**: Yes, data persistence (Python standard library)

### Python Version

- **Required**: Python >=3.11
- **Reason**: Type hints and modern features

## Known Limitations

1. ~~**Filter Functions Bugs**~~: ✅ FIXED
   - All attribute access errors fixed
   - Duplicate function removed

2. ~~**Statistics Agent**~~: ✅ IMPLEMENTED
   - Full LangChain agent with multi-LLM support
   - 10 tools for filtering, statistics, and search

3. ~~**Statistics Functions**~~: ✅ IMPLEMENTED
   - 18+ statistics functions implemented
   - All return Pydantic StatisticsResult

4. **Location Parsing**:
   - Exit coordinates not parsed (always None)

5. **Gear Types**:
   - BCD and Fins are stubs only

6. **Serialization**:
   - Uses pickle (not human-readable)
   - No versioning or migration support
   - Python version dependent
   - attrs-based (cannot change to Pydantic without breaking existing files)

7. **Error Handling**:
   - Improved in agent layer
   - Core data layer has minimal error handling

## What NOT to Modify

### Critical Files (Breaking Changes)

1. **`Utilities/ClassUtils/DiveClass.py`**
   - Changing structure breaks pickle deserialization
   - Uses attrs (do not convert to Pydantic)
   - Only add optional fields with defaults

2. **`Utilities/ClassUtils/GearClasses.py`**
   - Same pickle compatibility concerns
   - Uses attrs (do not convert to Pydantic)
   - Only extend, don't modify existing fields

3. **`Utilities/Parsers/GarminDiveParser.py`**
   - Only parser implementation
   - Changes break existing dives

4. **`Utilities/AddDive.py` and `Utilities/AddGear.py`**
   - Core data creation logic
   - Changes affect all new data

### Stable Interfaces

1. **GUI Classes** (`MainApp.py`, `AddDiveApp.py`, `AddGearApp.py`)
   - UI structure is complete
   - Only extend functionality
   - Will be deprecated when Streamlit is complete

2. **Filter System** (`DiveFilterer.py`, `FilterFunctions.py`)
   - Working filter implementation
   - Fix bugs but maintain signatures
   - Will be wrapped by agent-friendly tool layer

3. **Storage Structure** (`Storage/` directory)
   - Existing pickle files must remain readable
   - Don't change file naming or location

## What CAN Be Modified

### Safe to Extend/Modify

1. **`Utilities/StatisticsAgent.py`**
   - Currently stub, needs complete rewrite with LangChain
   - Add Pydantic schemas for tool integration
   - Safe to completely overhaul

2. **`Utilities/StatisticsFunctions.py`**
   - Empty file, ready for implementation
   - Should accept attrs Dive objects
   - Should return Pydantic result models

3. **`Utilities/FilterFunctions.py`**
   - Has bugs that need fixing
   - Simplify signatures as needed, GUI will be adapted to them
   - Will be wrapped by Pydantic-based tool layer

4. **GUI Code**
   - Can add features
   - Will eventually be deprecated for Streamlit

## Serialization Details

### Pickle Format

- **Protocol**: Default Python pickle protocol
- **Compatibility**: Python version dependent
- **Structure**: Direct serialization of attrs dataclass objects
- **Gear References**: Gear objects are loaded from pickle files and embedded in Dive objects

### File Organization

- **Dives**: `Storage/Dives/*.pickle`
- **Gear**: `Storage/Gear/*.pickle`
- **Bulk**: `Storage/BulkDives/*.pickle`
- **Original Files**: `Storage/Dives/FitFiles/*.fit`

### Data Loading

- Dives are loaded by scanning directory for `.pickle` files
- No index or database
- No lazy loading
- All dives loaded into memory

## Testing Considerations

- No test files found in codebase
- No test framework configured
- Manual testing only
- Explorer notebook (`explorer.ipynb`) may contain test code
- **Recommended**: Add pytest for new agent/tool code

## Data Model Conversion Strategy

### Storage Layer (attrs)
```python
# Existing - DO NOT CHANGE
from attrs import define

@define
class Dive:
    timeline: DiveTimeline
    basics: DiveBasicInformation
    # ...
```

### Agent Layer (Pydantic)
```python
# New - CREATE FOR AGENT
from pydantic import BaseModel

class DiveSummary(BaseModel):
    dive_id: str
    max_depth_meters: float
    duration_minutes: float
    
    @classmethod
    def from_dive(cls, dive: Dive, dive_id: str) -> 'DiveSummary':
        """Convert attrs Dive to Pydantic summary."""
        return cls(
            dive_id=dive_id,
            max_depth_meters=max(dive.timeline.depths),
            duration_minutes=dive.basics.duration / 60
        )
```

**Conversion happens at tool boundary** - tools receive attrs Dive objects, return Pydantic models.