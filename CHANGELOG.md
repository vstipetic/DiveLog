# Changelog

All notable changes to DiveLog are documented in this file.

## [Unreleased]

### Added

**Import from Garmin Connect**
- New "Import from Garmin" mode in the Import Dives tab: log into your Garmin
  Connect account and download dive `.fit` files directly, instead of manually
  exporting them.
- Uses the unofficial `garminconnect` library (mobile-SSO OAuth, same as the
  Garmin app). Supports multi-factor authentication.
- Login token is cached under `Storage/.garmin_tokens/`, so password/MFA are
  only needed on first login (auto-refreshed afterwards).
- Optional `GARMIN_EMAIL` / `GARMIN_PASSWORD` in `.env` pre-fill the login form.
- Pick a date range, select from the list of diving activities, and import.
  Already-imported dives are detected (by activity id) and skipped.
- Downloaded dives are enriched with metadata from the Garmin Connect activity
  record (not just the `.fit` file): **buddy**, **weight belt weight**,
  **location name**, and the dive **Note** (mapped to the location description).
  Tank pressures are read too when present (Garmin usually leaves them blank).
- Dives are saved as `<dive number> - <dive name>.pickle` (e.g.
  `24 - Single-Gas Dive.pickle`), matching how they appear in the Garmin app.
- Dive gear (suit/mask/etc.) is **not** available from Garmin for dive
  activities (its gear feature only covers shoes/bikes), so gear still needs to
  be added manually.
- **Group parsing**: the whole buddy group is now captured. Multiple names in
  Garmin's buddy field and any `grupa: name, name, ...` line in the Note are
  parsed into the dive's group set (which now also includes your primary buddy).
- **Entry type** (Shore/Boat) is stored on `Location.entry_type`.
- **Location inference**: the dive-site name is taken from the dive name (with
  Garmin's "Single-Gas Dive" boilerplate stripped), falling back to Garmin's
  location field — since dives are usually named after the site.
- The remaining dive **Note** (after structured lines like `grupa:` are removed)
  is stored on `Location.description` for later tooling.
- **Optional AI parsing**: with an LLM key configured, a checkbox in the Garmin
  import tab runs one LLM call per dive to extract the dive site, the full buddy
  group, and a cleaned note from the free-text name/note (handles Croatian).

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
