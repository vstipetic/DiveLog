# Changelog

All notable changes to DiveLog are documented in this file.

## [1.0.0] - 2024-12-24

### Added

**AI-Powered Statistics Agent**
- Natural language queries for dive statistics using LangChain
- Multi-LLM support: Google Gemini, OpenAI GPT, Anthropic Claude
- 15+ specialized tools for filtering, statistics, and search
- Chat history with context-aware responses

**Interactive Visualizations**
- Histogram, bar chart, pie chart, scatter plot support
- Altair-based rendering integrated with Streamlit
- Generate charts from natural language queries

**Modern Streamlit Web UI**
- **AI Chat Tab**: Natural language queries with quick stats dashboard
- **Import Dives Tab**: Single and bulk import with auto-extraction preview
- **Add Gear Tab**: Create masks, suits, gloves, boots
- 10 example query buttons
- Multi-provider API key detection and selection

**Enhanced Import System**
- Auto-extraction preview showing GPS, gas type, depth, duration
- Visual indicators for auto-extracted vs manual-input fields
- Bulk import with progress tracking and extraction summary
- .fit file preservation alongside dive data

**Tool Chaining**
- Filter operations automatically chain with statistics calculations
- Filter by date, depth, duration, buddy, location, temperature, CNS load, gas type
- Statistics calculated on filtered subsets

**Pydantic Schemas**
- Input validation for all LangChain tools
- Output schemas: FilterResult, StatisticsResult, DiveSummary
- Agent-friendly data models

### Changed
- Migrated from Poetry to uv for package management
- Updated LLM models: gemini-1.5-flash, gpt-4o-mini, claude-sonnet-4-20250514
- Streamlit app now serves as the sole UI (Tkinter apps removed)

### Fixed
- Fixed Pydantic/attrs incompatibility with ConfigDict
- Fixed statistics tool chaining bug (filtered results now used correctly)
- Fixed depth parsing (meters, not millimeters)
- Fixed duplicate filter function definitions
- Fixed attribute access bugs (basic_information -> basics)

### Removed
- Tkinter GUI applications (MainApp.py, AddDiveApp.py, AddGearApp.py)
- Obsolete planning documents (.claude/existing-code.md, .claude/next-steps.md)

---

## [0.1.0] - Initial Development

### Added
- Garmin .fit file parsing with fitparse
- Dive and gear data models using attrs
- Basic filtering functions
- Pickle serialization for data persistence
- Initial Tkinter GUI application

---

*Format based on [Keep a Changelog](https://keepachangelog.com/)*
