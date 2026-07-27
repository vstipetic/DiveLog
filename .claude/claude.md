# DiveLog Project Overview

**Version:** 1.0.0

## Project Description

DiveLog is a Python-based dive log management application with advanced search and statistics functionality. The main purpose is to extract statistics from dive logs and find interesting trends in diving data. The application parses Garmin dive computer `.fit` files and provides a web UI (Flask backend + Jinja2 frontend) for managing dives, gear, and analyzing dive statistics with AI-powered natural language queries.

### High-Level Architecture

The application follows a modular architecture with clear separation of concerns:

1. **Backend Layer** (`backend/`, entry point `app.py`)
   - Flask application factory (`backend/__init__.py`)
   - `backend/state.py` - Server-side session state (agent instance, chat transcript, Garmin client)
   - `backend/services/` - Application logic wrapping `Utilities/` (chat/agent lifecycle, imports, Garmin, gear, settings)
   - `backend/services/progress.py` - Background `ImportJob` tracker; bulk/Garmin imports run on a worker thread and report per-file progress
   - `backend/security.py` - CSRF protection for every state-changing request
   - `backend/routes/` - HTML routes (AI Chat, Import Dives, Add Gear) plus a JSON chat API (`POST /api/chat`) and a progress endpoint (`GET /import/progress`)
   - `DiveFilterer.py` - Filter utility functions (root directory)

1b. **Frontend Layer** (`frontend/`)
   - `frontend/templates/` - Jinja2 templates (chat, import, gear pages + partials)
   - `frontend/static/` - CSS and JavaScript; agent-generated Altair charts are serialized to Vega-Lite JSON by the backend and rendered in the browser with vega-embed

2. **Business Logic Layer** (`Utilities/`)
   - `AddDive.py` - Core dive creation and serialization logic
   - `AddGear.py` - Core gear creation and serialization logic
   - `StatisticsAgent.py` - LangChain-based AI statistics agent
   - `FilterFunctions.py` - Individual filter predicate functions
   - `StatisticsFunctions.py` - Statistics calculation functions
   - `APIKeyDetector.py` - Environment variable detection for LLM API keys

3. **Data Model Layer** (`Utilities/ClassUtils/`) - **attrs-based**
   - `DiveClass.py` - Core dive data structures using attrs
   - `GearClasses.py` - Gear data structures using attrs

4. **Agent Schema Layer** (`Utilities/Schemas/`) - **Pydantic-based**
   - `ToolInputs.py` - Input validation schemas for LangChain tools
   - `ToolOutputs.py` - Output result schemas (FilterResult, StatisticsResult, DiveSummary)
   - `AgentModels.py` - Agent-friendly data models
   - `ChartSchemas.py` - Input schemas for chart visualization tools

5. **Agent Tools Layer** (`Utilities/Tools/`) - **LangChain + Pydantic**
   - `FilterTool.py` - Dive filtering tools (depth, date, duration, buddy, location, start time, temperature, CNS load, gas type)
   - `DurationAtDepthTool.py` - Filter for continuous time at depth
   - `StatisticsTool.py` - Statistics calculation tools
   - `SearchTool.py` - Search and listing tools
   - `ChartTools.py` - Visualization tools (histogram, bar chart, pie chart, scatter plot)
   - `ToolState.py` - Shared state for filter→statistics chaining
   - `ChartState.py` - Shared state for chart→UI rendering (backend serializes charts to Vega-Lite for the browser)

6. **Parser Layer** (`Utilities/Parsers/`)
   - `GarminDiveParser.py` - Garmin .fit file parser

7. **Storage Layer** (`Storage/`)
   - `Dives/` - Individual dive pickle files with full metadata
   - `Dives/FitFiles/` - Original .fit files for manual imports
   - `Gear/` - Gear pickle files
   - `BulkDives/` - Bulk imported dive files (minimal metadata)
   - `BulkDives/FitFiles/` - Original .fit files for bulk imports

### Import Workflows

**Single Dive Import** (via the "Import Dives" tab → `add_dive()`):
- Single dive with full metadata enrichment
- Auto-extracts: GPS coordinates, gas type, all timeline data
- Manual input for: location name, buddy, gear, weight, tank pressures, location description
- Output: Complete `Dive` object in `Storage/Dives/`
- Use when: Building comprehensive dive log with context

**Bulk Import** (via the "Import Dives" tab → `bulk_add_dives()`):
- Multiple .fit files from directory - **fully automated, zero manual input required**
- Auto-extracts ALL available data from .fit files (see "Auto-Extraction" section below)
- Empty fields: People, Gear, Pressures, Location descriptions (not in .fit files)
- Output: `Dive` objects with auto-extracted metadata in `Storage/BulkDives/`
- Use when: Quick statistical analysis of large dive collections

**Import from Garmin** (via the "Import Dives" tab → `Utilities/GarminConnectClient.py`):
- Logs into Garmin Connect and downloads dive `.fit` files directly — no manual export needed
- Uses the unofficial `garminconnect` library (mobile-SSO OAuth, same flow as the Garmin app; supports MFA)
- Login token cached under `Storage/.garmin_tokens/` (git-ignored); password/MFA only needed on first login
- Optional `GARMIN_EMAIL` / `GARMIN_PASSWORD` in `.env` pre-fill the login form (detected via `detect_garmin_credentials()`)
- Flow: `begin_login()`/`finish_mfa()` → `list_dives()` (filters activities client-side on `activityType.typeKey` containing "diving") → `download_fit()` (extracts the `.fit` from Garmin's ORIGINAL zip) → existing `parse_garmin_dive()`
- Dedup: `already_imported()` skips dives whose `activityId` pickle/`.fit` already exists in the storage folder
- `get_dive_metadata()` also supplies `entry_coordinates`, so dives whose `.fit` has no start position still get a location (see ".fit File Auto-Extraction")
- Empty fields: same as Bulk Import (no buddy/gear/pressures) — enrich later via Single Dive import
- Use when: Pulling dives straight from Garmin without touching Garmin Express

### .fit File Auto-Extraction

The parser (`GarminDiveParser.py`) extracts extensive data from Garmin .fit files:

**Auto-Extracted (stored in Dive object):**
- `Location.entry` - GPS coordinates from session data (start_position_lat/long).
  The watch only writes this when it had a fix at the instant the dive started, so
  it is absent for a sizeable minority of dives. A Garmin import fills those in
  from Garmin Connect's `summaryDTO.startLatitude/startLongitude`, which also
  carries positions the diver corrected by hand in the app; when both sources have
  a value they agree to within centimetres, and Garmin's wins
- `Gasses.gas` - Gas type (air/nitrox/trimix) based on O2/He percentages from dive_gas message
- `DiveTimeline` - All depth, temperature, N2/CNS load data from record messages
- `DiveBasicInformation` - Duration, start/end times. `.fit` timestamps are UTC, so
  the parser shifts them into the dive site's local time using the offset the file's
  `activity` message records (`local_timestamp` - `timestamp`), and keeps that offset
  in `utc_offset_hours`

**Auto-Extracted (available via `get_fit_file_metadata()` but not stored in Dive class):**
- `dive_number` - Sequential dive number from dive_summary message
- `avg_depth`, `max_depth` - Pre-computed by dive computer
- `bottom_time`, `surface_interval` - Time data from dive_summary
- `water_type` - Salt/fresh water from dive_settings
- `avg_temperature`, `max_temperature` - Water temperature from session
- `avg_heart_rate`, `max_heart_rate` - Heart rate data from session
- `gf_low`, `gf_high` - Gradient factor settings from dive_settings
- `total_calories` - Calories burned from session

**NOT in .fit files (require manual input):**
- **Location name** - Not stored in .fit files (filename-based extraction is unreliable)
- Location description
- Buddy, divemaster, group members
- **Tank start/end pressures** - Surprisingly NOT stored by Garmin!
- Gear selection (suit, mask, gloves, boots, BCD, fins)
- Weight belt weight

**Helper Functions:**
- `get_fit_file_metadata(file_path)` - Returns dict with `auto_extracted` and `needs_manual_input` sections
- `preview_fit_file(file_path)` - Alias for `get_fit_file_metadata()`

## Tech Stack

### Core Dependencies
- **Python**: >=3.11
- **fitparse**: >=1.2.0 - For parsing Garmin .fit files
- **attrs**: ^25.1.0 - For data model definitions (storage layer)
- **pydantic**: ^2.x - For agent schema validation (LangChain tools)
- **langchain**: For AI agent framework
- **langchain-google-genai**: Google Gemini LLM integration
- **langchain-openai**: OpenAI GPT integration
- **langchain-anthropic**: Anthropic Claude integration
- **flask**: Web backend framework (Jinja2 templates render the frontend)
- **pickle** - Serialization format (Python standard library)

### Build System
- **uv** - Fast Python package installer and resolver

### Dual-Library Data Model Strategy

The project uses two different libraries for data modeling, each optimized for its use case:

#### attrs (Storage Layer)
- Used in: `Utilities/ClassUtils/DiveClass.py`, `Utilities/ClassUtils/GearClasses.py`
- Purpose: Define core data structures for dives and gear
- Serialization: Python pickle for persistence
- Rationale: Lightweight, fast, minimal boilerplate for simple data containers

```python
from attr import dataclass

@dataclass
class Dive:
    people: People
    basics: DiveBasicInformation
    timeline: DiveTimeline
    # ... stored as pickle files
```

#### Pydantic (Agent Layer)
- Used in: `Utilities/Schemas/`, `Utilities/Tools/`
- Purpose: Input/output validation for LangChain tools
- Rationale: Required by LangChain for tool argument schemas; provides runtime validation

```python
from pydantic import BaseModel, Field

class FilterDivesByDepthInput(BaseModel):
    min_depth: float = Field(description="Minimum depth in meters")
    max_depth: Optional[float] = Field(None, description="Maximum depth")
```

#### Bridging attrs and Pydantic

LangChain tools that hold attrs objects (like `List[Dive]`) must configure Pydantic to accept arbitrary types:

```python
from pydantic import ConfigDict

class FilterDivesByDepthTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    dives: List[Dive] = Field(default_factory=list)  # attrs objects
```

Without `arbitrary_types_allowed=True`, Pydantic silently ignores attrs objects during initialization, resulting in empty lists.

## Data Models

### Dive Data Structure

The core `Dive` class (`Utilities/ClassUtils/DiveClass.py`) contains:

```python
@dataclass
class Dive:
    people: People              # Buddy, divemaster, group
    basics: DiveBasicInformation # Duration, start_time, end_time
    timeline: DiveTimeline      # Depths, temperatures, N2/CNS loads, timestamps
    location: Location          # Name, entry/exit coordinates, description
    gasses: Gasses              # Gas type, start/end pressure
    gear: UsedGear              # Suit, mask, gloves, boots, BCD, fins, weights
```

**Nested Structures:**

- `DiveTimeline`: Lists of depths (meters), temperatures (Celsius), N2 loads, CNS loads, and timestamps (seconds from start)
- `DiveBasicInformation`: Duration (seconds), start_time, end_time (naive datetimes in the dive site's **local** time — the time the watch was showing underwater), start_time_utc, end_time_utc (Optional[datetime], the same instants standardised to UTC, for ordering dives across time zones), utc_offset_hours (Optional[float], hours ahead of UTC). The three optional fields are `None` on dives imported before local time was recorded
- `People`: buddy (str), divemaster (Optional[str]), group (Optional[Set[str]])
- `Location`: name (str), entry (Optional[Tuple[float, float]]), exit (Optional[Tuple[float, float]]), description (Optional[str])
- `Gasses`: gas (str: 'air'|'nitrox'|'trimix'), start_pressure (int), end_pressure (int)
- `UsedGear`: suit (Suit), weights (float), mask (Optional[Mask]), gloves (Optional[Gloves]), boots (Optional[Boots]), bcd (Optional[BCD]), fins (Optional[Fins])

### Gear Data Structure

Base `Gear` class (`Utilities/ClassUtils/GearClasses.py`) contains:
- `name`: str - Unique identifier
- `unique_id`: str - UUID4 generated automatically
- `total_dive_time`: int - Minutes underwater
- `number_of_dives`: int - Count of dives
- `description`: Optional[str]
- `is_rental`: bool - Excluded from statistics if True

**Gear Types:**
- `Mask` - No additional fields
- `Suit` - thickness (int, mm), size (int)
- `Gloves` - thickness (int, mm), size (GloveSize enum: S/M/L/XL)
- `Boots` - thickness (int, mm), size (int)
- `BCD` - Stub implementation (to be implemented)
- `Fins` - Stub implementation (to be implemented)

## Serialization Format

### File Format
- **Format**: Python pickle (binary)
- **Extension**: `.pickle`
- **Location**: 
  - Dives: `Storage/Dives/*.pickle`
  - Gear: `Storage/Gear/*.pickle`
  - Bulk imports: `Storage/BulkDives/*.pickle`

### Serialization Details
- All `Dive` and `Gear` objects are serialized using Python's `pickle` module
- Gear objects are loaded from pickle files and embedded in `Dive` objects
- Original `.fit` files are preserved alongside dive pickle files in `Storage/Dives/FitFiles/`

## Current Implementation Status

### ✅ Fully Implemented

1. **Dive Parsing**
   - Garmin .fit file parsing (`Utilities/Parsers/GarminDiveParser.py`)
   - Timeline extraction (depths in meters, temperatures, N2/CNS loads)
   - Basic information extraction (duration, start/end times)
   - Location parsing (name, entry coordinates from GPS)
   - Gas type detection (air/nitrox/trimix)
   - People metadata (buddy, divemaster, group)

2. **Gear Management**
   - Gear creation for Mask, Suit, Gloves, Boots
   - Gear serialization/deserialization
   - Gear selection in dive creation

3. **Web UI** (`backend/` + `frontend/`, entry point `app.py`)
   - **AI Chat Tab**: Natural language queries with LLM-powered responses
     - Quick statistics display (total dives, time, avg/max depth)
     - Example query buttons (10 pre-built queries)
     - Chart rendering (Altair charts serialized to Vega-Lite, rendered with vega-embed)
   - **Import Dives Tab**: Complete dive import functionality
     - Storage folder selection (default: `Storage/BulkDives`)
     - **Single dive import**: Shows auto-extracted data preview (depth, duration, gas, GPS, etc.)
     - **Bulk import**: Fully automated with extraction summary, shows GPS coordinates extracted
     - Visual indicators for auto-extracted vs manual-input fields
     - Gear selection dropdowns (loaded from `Storage/Gear/`)
     - Refresh functionality to reload dives into agent
   - **Add Gear Tab**: Create new gear items
     - Supports Mask, Suit, Gloves, Boots
     - Type-specific fields (thickness, size)
     - Rental gear flag
     - Existing gear display
   - Multi-provider support (Gemini, OpenAI, Claude)

4. **Filtering System**
   - Filter functions: `dive_was_deeper_than`, `dive_was_shallower_than`, `dive_was_longer_than`, `dive_was_shorter_than`, `dive_was_after_date`, `dive_was_before_date`, `dive_was_between_dates`, `dive_was_between_times`, `dive_was_deeper_than_for_duration`, `dive_had_buddy`, `dive_was_at_location`, `dive_used_gas`
   - Filter utility functions in root `DiveFilterer.py`

5. **API Key Detection**
   - Environment variable scanning for OpenAI, Gemini, and Anthropic API keys

6. **Statistics Agent** (`Utilities/StatisticsAgent.py`)
   - Full LangChain agent implementation
   - Multi-LLM support (Gemini, OpenAI, Claude)
   - 15 specialized tools for filtering, statistics, and search
   - Natural language query processing
   - Chat history management

7. **Statistics Functions** (`Utilities/StatisticsFunctions.py`)
   - 18+ statistics functions implemented
   - Averages, totals, counts, breakdowns by time/location/buddy
   - All return Pydantic StatisticsResult

8. **Pydantic Schemas** (`Utilities/Schemas/`)
   - ToolInputs.py - Input validation schemas
   - ToolOutputs.py - Output result schemas (FilterResult, StatisticsResult, DiveSummary)
   - AgentModels.py - Agent-friendly data models

9. **LangChain Tools** (`Utilities/Tools/`)
    - FilterTool.py - 10 filtering tools (depth, date, duration, buddy, location, start time, temperature, CNS load, gas type, duration at depth)
    - StatisticsTool.py - 2 statistics tools (calculate_statistic, time_below_depth)
    - SearchTool.py - 3 search tools (search_dives, get_dive_summary, list_all_dives)
    - ChartTools.py - 4 visualization tools (plot_histogram, plot_bar_chart, plot_pie_chart, plot_scatter)
    - ToolState.py - Shared state for tool chaining (filter → statistics/charts)
    - ChartState.py - Shared state for chart rendering (tools → UI)
    - All tools use `ConfigDict(arbitrary_types_allowed=True)` for attrs compatibility

### Tool Chaining via ToolState

Filter tools and statistics tools are connected via `ToolState`, a shared state mechanism:

1. **Filter tools** (e.g., `filter_dives_by_date`) store their filtered results in `ToolState`
2. **Statistics tools** (e.g., `calculate_statistic`) check `ToolState` first:
   - If filtered dives exist → calculate on filtered subset
   - Otherwise → calculate on all dives
3. **StatisticsAgent** clears `ToolState` at the start of each new query

Example flow for "How many dives in 2024?":
```
1. Agent calls: filter_dives_by_date("2024-01-01", "2024-12-31")
   → Stores 9 filtered dives in ToolState
2. Agent calls: calculate_statistic("dive_count")
   → Reads from ToolState, returns "Dive Count: 9 dives"
```

Without this mechanism, statistics would incorrectly operate on ALL dives instead of filtered subsets.

### 🚧 Partially Implemented

1. **Location Parsing**
   - Entry coordinates extracted from .fit files, falling back to Garmin Connect
     when the watch caught no fix at the start of the dive
   - Exit coordinates not implemented (always None). Garmin Connect does expose
     `summaryDTO.endLatitude/endLongitude` for roughly half of dives, so this is
     now fillable the same way `entry` is

### ❌ Not Implemented

1. **BCD and Fins Gear Types**
   - Class definitions exist but are stubs

2. **Advanced Features**
   - Data export functionality (CSV, PDF reports)

## File Structure

```
DiveLog/
├── app.py                        # Entry point (Flask app; AI Chat + Import Dives + Add Gear)
├── backend/                      # Flask backend
│   ├── __init__.py               # Application factory
│   ├── state.py                  # Server-side session state
│   ├── security.py               # CSRF token issuing + validation
│   ├── utils.py                  # Formatting helpers (also Jinja filters)
│   ├── services/                 # chat, imports, Garmin, gear, settings, progress
│   └── routes/                   # Page routes + JSON chat API + progress endpoint
├── frontend/                     # Jinja2 frontend
│   ├── templates/                # base, chat, import (+ partials), gear
│   └── static/                   # css/style.css, js/chat.js, js/gear.js, js/import.js
├── DiveFilterer.py               # Root-level filter utilities
├── explorer.ipynb                # Jupyter notebook (exploration/testing)
├── pyproject.toml                # uv/pip dependencies
├── uv.lock                       # uv lock file
├── README.md                     # Project readme
├── CHANGELOG.md                  # Version history
├── Storage/
│   ├── Dives/                    # Individual dive pickle files (with metadata)
│   │   ├── *.pickle              # Dive objects (attrs-based)
│   │   └── FitFiles/             # Original .fit files
│   ├── Gear/                     # Gear pickle files
│   │   └── *.pickle              # Gear objects (attrs-based)
│   └── BulkDives/                # Bulk imported dives (minimal metadata)
│       ├── *.pickle              # Dive objects (attrs-based)
│       └── FitFiles/             # Original .fit files
└── Utilities/
    ├── AddDive.py                 # Dive creation logic (add_dive, bulk_add_dives)
    ├── AddGear.py                 # Gear creation logic
    ├── StatisticsAgent.py         # LangChain AI agent (multi-LLM support)
    ├── FilterFunctions.py         # Filter predicate functions (12 functions)
    ├── StatisticsFunctions.py     # Statistics calculation functions (18+ functions)
    ├── APIKeyDetector.py          # API key detection (OpenAI, Gemini, Anthropic)
    ├── ClassUtils/                # Data models (attrs-based, for storage)
    │   ├── DiveClass.py           # Dive, DiveTimeline, People, Location, etc.
    │   └── GearClasses.py         # Gear, Mask, Suit, Gloves, Boots, BCD, Fins
    ├── Parsers/
    │   └── GarminDiveParser.py    # Garmin .fit parser (depths in meters)
    ├── Schemas/                   # Agent schemas (Pydantic-based, for LangChain)
    │   ├── __init__.py
    │   ├── ToolInputs.py          # Input validation schemas
    │   ├── ToolOutputs.py         # FilterResult, StatisticsResult, DiveSummary
    │   ├── AgentModels.py         # Agent-friendly data models
    │   └── ChartSchemas.py        # Chart tool input schemas
    └── Tools/                     # LangChain tools (Pydantic + attrs bridge)
        ├── __init__.py
        ├── FilterTool.py          # 10 filtering tools (uses ConfigDict)
        ├── StatisticsTool.py      # 2 statistics tools (uses ConfigDict)
        ├── SearchTool.py          # 3 search tools (uses ConfigDict)
        ├── ChartTools.py          # 4 visualization tools (Altair charts)
        ├── ToolState.py           # Shared state for filter→statistics chaining
        └── ChartState.py          # Shared state for chart→UI rendering
```

## Query Examples

The agent system supports natural language queries like:

**Statistics & Filtering:**
- "What's my average dive depth?"
- "Show me all dives deeper than 30 meters"
- "How many dives did I do in 2023?"
- "What's my deepest dive?"
- "Show me dives where I used my 7mm suit"
- "What's the longest dive I've done?"
- "Find all dives with buddy 'John'"
- "What's my total dive time this year?"

**Visualizations (Altair charts rendered in the browser via Vega-Lite):**
- "Plot the distribution of my dive depths"
- "Show a bar chart of dives by month"
- "Create a pie chart of dives by location"
- "Is there a relationship between depth and dive duration?" (scatter plot)
- "Show me a histogram of dive temperatures"
- "Plot dives by year for my deep dives (>20m)"

## Future Enhancements

1. **Gear Types**
   - Complete BCD and Fins gear types (currently stubs)

2. **Data Parsing**
   - Implement exit coordinate parsing from .fit files
   - Multi-format support (beyond Garmin)

3. **Statistics**
   - Additional statistics functions (SAC rate analysis, temperature trends)
   - Gear usage statistics and tracking

4. **Export & Visualization**
   - Export functionality (CSV, PDF reports)
   - Additional chart types (time series, heatmaps)

## Known Limitations

v1.0 is feature-complete for core functionality. Minor limitations:

- Exit coordinates not parsed from .fit files (always None)
- BCD and Fins gear types are stubs (not fully implemented)
- Tank pressures are not stored in Garmin .fit files (requires manual entry)
