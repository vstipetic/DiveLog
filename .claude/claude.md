# DiveLog Project Overview

## Project Description

DiveLog is a Python-based dive log management application with advanced search and statistics functionality. The main purpose is to extract statistics from dive logs and find interesting trends in diving data. The application parses Garmin dive computer `.fit` files and provides a GUI for managing dives, gear, and analyzing dive statistics.

### High-Level Architecture

The application follows a modular architecture with clear separation of concerns:

1. **GUI Layer** (Root directory)
   - `MainApp.py` - Main application window with menu and navigation
   - `AddDiveApp.py` - GUI for adding individual dives
   - `AddGearApp.py` - GUI for adding gear items
   - `DiveFilterer.py` - Filter utility (root level, appears to be a duplicate/alternative implementation)

2. **Business Logic Layer** (`Utilities/`)
   - `AddDive.py` - Core dive creation and serialization logic
   - `AddGear.py` - Core gear creation and serialization logic
   - `StatisticsAgent.py` - AI-powered statistics agent (currently stub implementation)
   - `DiveFilterer.py` - Dive filtering utilities
   - `FilterFunctions.py` - Individual filter predicate functions
   - `StatisticsFunctions.py` - Statistics calculation functions (currently empty)
   - `APIKeyDetector.py` - Environment variable detection for LLM API keys

3. **Data Model Layer** (`Utilities/ClassUtils/`)
   - `DiveClass.py` - Core dive data structures
   - `GearClasses.py` - Gear data structures

4. **Parser Layer** (`Utilities/Parsers/`)
   - `GarminDiveParser.py` - Garmin .fit file parser

5. **Storage Layer** (`Storage/`)
   - `Dives/` - Individual dive pickle files
   - `Dives/FitFiles/` - Original .fit files
   - `Gear/` - Gear pickle files
   - `BulkDives/` - Bulk imported dive files

### Import Workflows

**Manual Import** (via `AddDiveApp.py` → `add_dive()`):
- Single dive with full metadata enrichment
- Adds data NOT in .fit files: buddy, gear, weight, tank pressures, location details
- Output: Complete `Dive` object in `Storage/Dives/`
- Use when: Building comprehensive dive log with context

**Bulk Import** (via `MainApp.py` → `bulk_add_dives()`):
- Multiple .fit files from directory
- Parses ONLY .fit file data (timeline, GPS, gas mix, basic stats)
- NO metadata: People, Gear, Pressures, Location descriptions
- Output: Minimal `Dive` objects in `Storage/BulkDives/`
- Use when: Quick statistical analysis of large dive collections without detailed metadata

## Tech Stack

### Core Dependencies
- **Python**: >=3.11
- **fitparse**: >=1.2.0 - For parsing Garmin .fit files
- **attrs**: ^25.1.0 - For dataclass definitions
- **google-generativeai**: ^0.8.4 - For AI/LLM integration
- **tkinter** - Built-in GUI framework (Python standard library)
- **pathlib** - Path handling (Python standard library)
- **pickle** - Serialization format (Python standard library)

### Build System
- **Poetry** - Dependency management and packaging

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
- `DiveBasicInformation`: Duration (seconds), start_time, end_time (datetime objects)
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
   - Timeline extraction (depths, temperatures, N2/CNS loads)
   - Basic information extraction (duration, start/end times)
   - Location parsing (name, entry coordinates from GPS)
   - Gas type detection (air/nitrox/trimix)
   - People metadata (buddy, divemaster, group)

2. **Gear Management**
   - Gear creation for Mask, Suit, Gloves, Boots
   - Gear serialization/deserialization
   - Gear selection in dive creation

3. **GUI Applications**
   - Main application window with menu
   - Add Dive GUI with all metadata fields
   - Add Gear GUI with type-specific fields
   - Bulk import functionality
   - Statistics window with AI Query tab (UI only)

4. **Filtering System**
   - Filter functions: `dive_was_deeper_than`, `dive_was_shallower_than`, `dive_was_longer_than`, `dive_was_shorter_than`, `dive_was_after_date`, `dive_was_before_date`, `dive_was_between_dates`, `dive_was_between_times`, `dive_was_deeper_than_for_duration`, `dive_had_buddy`, `dive_was_at_location`, `dive_used_gas`
   - Filter utility functions in root `DiveFilterer.py`

5. **API Key Detection**
   - Environment variable scanning for OpenAI, Gemini, and Anthropic API keys

6. **Statistics Agent** (`Utilities/StatisticsAgent.py`)
   - Full LangChain agent implementation
   - Multi-LLM support (Gemini, OpenAI, Claude)
   - 10 specialized tools for filtering, statistics, and search
   - Natural language query processing
   - Chat history management

7. **Statistics Functions** (`Utilities/StatisticsFunctions.py`)
   - 18+ statistics functions implemented
   - Averages, totals, counts, breakdowns by time/location/buddy
   - All return Pydantic StatisticsResult

8. **Pydantic Schemas** (`Utilities/Schemas/`)
   - ToolInputs.py - Input validation schemas
   - ToolOutputs.py - Output result schemas
   - AgentModels.py - Agent-friendly data models

9. **LangChain Tools** (`Utilities/Tools/`)
   - FilterTool.py - Dive filtering tools
   - StatisticsTool.py - Statistics calculation tools
   - SearchTool.py - Search and listing tools

10. **Streamlit UI** (`streamlit_app.py`)
    - Modern web interface for AI queries
    - Chat-based interaction
    - Quick statistics display
    - Multi-provider support

### 🚧 Partially Implemented

1. **Location Parsing**
   - Entry coordinates extracted from .fit files
   - Exit coordinates not implemented (always None)

### ❌ Not Implemented

1. **BCD and Fins Gear Types**
   - Class definitions exist but are stubs

2. **Basic Statistics Display in Tkinter**
   - `populate_dive_stats()` and `populate_gear_stats()` methods are placeholders
   - (Replaced by Streamlit UI)

3. **Advanced Features**
   - Trend analysis visualizations
   - Data export functionality

## File Structure

```
DiveLog/
├── MainApp.py                    # Main Tkinter GUI application
├── AddDiveApp.py                 # Add dive GUI
├── AddGearApp.py                 # Add gear GUI
├── DiveFilterer.py               # Root-level filter utilities
├── streamlit_app.py              # Streamlit web UI for AI queries
├── explorer.ipynb                # Jupyter notebook (exploration/testing)
├── pyproject.toml                # Poetry dependencies
├── README.md                     # Project readme
├── Storage/
│   ├── Dives/                    # Individual dive pickle files
│   │   ├── *.pickle              # Dive objects
│   │   └── FitFiles/             # Original .fit files
│   ├── Gear/                     # Gear pickle files
│   │   └── *.pickle              # Gear objects
│   └── BulkDives/                # Bulk imported dives
│       └── *.pickle
└── Utilities/
    ├── AddDive.py                 # Dive creation logic
    ├── AddGear.py                 # Gear creation logic
    ├── StatisticsAgent.py         # LangChain AI agent
    ├── FilterFunctions.py         # Filter predicate functions
    ├── StatisticsFunctions.py     # Statistics calculation functions
    ├── APIKeyDetector.py          # API key detection
    ├── ClassUtils/
    │   ├── DiveClass.py           # Dive data models (attrs)
    │   └── GearClasses.py         # Gear data models (attrs)
    ├── Parsers/
    │   └── GarminDiveParser.py    # Garmin .fit parser
    ├── Schemas/                   # Pydantic schemas for agent layer
    │   ├── __init__.py
    │   ├── ToolInputs.py          # Input validation schemas
    │   ├── ToolOutputs.py         # Output result schemas
    │   └── AgentModels.py         # Agent-friendly data models
    └── Tools/                     # LangChain tool implementations
        ├── __init__.py
        ├── FilterTool.py          # Dive filtering tools
        ├── StatisticsTool.py      # Statistics calculation tools
        └── SearchTool.py          # Search and listing tools
```

## Query Examples

The agent system supports natural language queries like:

- "What's my average dive depth?"
- "Show me all dives deeper than 30 meters"
- "How many dives did I do in 2023?"
- "What's my deepest dive?"
- "Show me dives where I used my 7mm suit"
- "What's the longest dive I've done?"
- "Find all dives with buddy 'John'"
- "What's my total dive time this year?"

## Implementation Priorities

1. **High Priority**
   - Complete StatisticsAgent with tool system
   - Implement LLM integration (OpenAI/Gemini)
   - Create query parsing and execution engine
   - Implement basic statistics functions

2. **Medium Priority**
   - Complete BCD and Fins gear types
   - Implement exit coordinate parsing
   - Add populate_dive_stats() and populate_gear_stats() implementations
   - Error handling and validation

3. **Low Priority**
   - Advanced trend analysis
   - Export functionality
   - Data visualization
   - Multi-format support (beyond Garmin)

## Known Issues

All major bugs have been fixed:

1. ~~**Filter Functions Bug**~~: ✅ FIXED - Duplicate function removed
2. ~~**Attribute Access Bug**~~: ✅ FIXED - All `basic_information` changed to `basics`
3. ~~**Duplicate Files**~~: ✅ FIXED - `Utilities/DiveFilterer.py` removed, root version is canonical
4. ~~**Import Path Issue**~~: ✅ FIXED - No longer relevant

**Remaining Issues:**
- Exit coordinates not parsed from .fit files (always None)
- BCD and Fins gear types are stubs

