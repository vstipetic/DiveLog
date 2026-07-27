# Changelog

All notable changes to DiveLog are documented in this file.

## [Unreleased]

### Changed

**Frontend/backend separation (Flask + Jinja2)**
- The Streamlit monolith (`streamlit_app.py`) is replaced by a separated
  architecture: a Flask backend (`backend/`) and a Jinja2-rendered frontend
  (`frontend/templates/` + `frontend/static/`).
- Run with `uv run python app.py` and open `http://localhost:5000` (was
  `uv run streamlit run streamlit_app.py` on port 8501).
- The UI keeps the same three tabs (AI Chat, Import Dives, Add Gear), the same
  sidebar (provider/model selection, reload dives, clear chat), and the same
  import workflows (single dive with `.fit` preview, bulk folder import, and
  Import from Garmin with MFA support).
- The agent and its tool design are untouched: `StatisticsAgent`, all tools,
  and the `ToolState`/`ChartState` chaining work exactly as before. Charts
  still flow from the chart tools through `ChartState`; the backend now
  serializes them to Vega-Lite JSON and the browser renders them with
  vega-embed (same Altair charts as before).
- Chat runs over a small JSON API (`POST /api/chat`) consumed by the frontend;
  all other interactions are classic form posts rendered server-side.
- Dependencies: `streamlit` removed, `flask` added.

**Bulk and Garmin imports run in the background**
- Long imports no longer block the request. They run on a worker thread and
  the page shows a live progress bar, the file being processed, and a
  per-file status row (depth/duration/location on success, the error on
  failure) — restoring the progress feedback the Streamlit UI had, and adding
  a per-file result list that persists after the run finishes.
- Progress is polled from `GET /import/progress`; the page reloads itself into
  the results panel when the run completes. One import runs at a time.

### Fixed

- The agent is no longer rebuilt on every request. `get_agent()` compared a
  normalised `Path` against a raw string, which never matched on Windows, so
  each page load and each chat message constructed a fresh `StatisticsAgent` —
  re-reading every dive pickle and, worse, silently discarding the
  conversation history so follow-up questions lost all context.
- The Garmin date range no longer resets to the last-90-days default on every
  render. The selected range is kept in server state and echoed back into the
  form, so it survives the post/redirect after "Fetch dives".
- **The dive buddy is read from Garmin's buddy field again.** The optional LLM
  enrichment pass merged the buddy field and the note's `grupa:` roster into one
  list and took whichever name came first as the buddy, so a group member
  routinely displaced the real buddy, and dives with no buddy at all (the ones
  the user led) had one invented from the roster. On the reference log this was
  wrong for 17 of 78 dives. The buddy now comes from Garmin Connect's buddy
  field and nothing else — empty field, empty buddy — and the enrichment pass
  can only widen the group, never shrink it or name a buddy. `parse_people()`
  keeps `buddy` and `group` as separate fields but guarantees a designated buddy
  is also in the group, so a person search never has to consult both.
- `repair_dive_buddies.py` fixes the buddy on dives already on disk, re-reading
  the field from Garmin Connect and rewriting nothing else. Dry-run by default;
  pass `--apply` to write (backs each pickle up to `.pickle.bak`).
- **Dive times are stored in the dive site's local time.** Every timestamp in a
  `.fit` file is UTC, and the parser stored it verbatim, so a dive logged at
  18:16 in Egypt sat in the pickle as 16:16. All 78 dives in the reference log
  were affected (+1h to +3h). The offset now comes from the `.fit` file's own
  `activity` message, which records the same instant as both `timestamp` (UTC)
  and `local_timestamp` — no timezone database needed and already correct for
  daylight saving. Verified against Garmin Connect's `startTimeLocal`: all 78
  agree exactly. Times remain naive datetimes, so they stay comparable with
  everything else in the app.
- `DiveBasicInformation` gained three fields: `start_time_utc` / `end_time_utc`
  hold the same instants standardised to UTC — local time is what the diver
  logged and what every question about a dive means, but UTC is the only way to
  order dives from different time zones on one absolute timeline — and
  `utc_offset_hours` records how far ahead of UTC the site was. All three are
  `None` on dives imported before this change.
- `repair_dive_times.py` converts dives already on disk from UTC to local,
  rewriting only the start/end times. Dry-run by default; `--apply` to write.
- **Dives whose watch caught no GPS fix now get their coordinates from Garmin.**
  The entry position was read only from the `.fit` file's `start_position`, which
  the watch writes only when it had a lock at the instant the dive began — so
  dives that started before the fix landed were stored with no position at all
  (22 of 78 in the reference log). Garmin Connect holds a position for most of
  them regardless, including ones the diver corrected by hand in the app after
  the watch missed it, and `get_dive_metadata()` now returns it as
  `entry_coordinates` for the parser to use. Where both sources have a value they
  agree to within centimetres (the `.fit` reading is just rounded to six
  decimals), so preferring Garmin never contradicts the watch; a plain folder
  import has no metadata and still relies on the `.fit` alone.
- `repair_dive_coordinates.py` backfills the position on dives already on disk,
  rewriting only `location.entry`. Fills in missing coordinates by default;
  `--overwrite` also corrects stored positions that disagree with Garmin by more
  than `--tolerance` metres (default 1 m, so rounding never counts as a change).
  Dry-run by default; `--apply` to write. On the reference log this recovers 16
  of the 22 — the remaining 6 have no position in Garmin either.

### Security

- **CSRF protection** on every state-changing endpoint (`backend/security.py`).
  The app has no login and binds to localhost, so cross-origin form posts could
  previously drive it from any page open in the browser — changing the storage
  folder, starting an import, or posting to the Garmin login route. Requests
  that change state must now echo a per-session token (`_csrf_token` form field
  or `X-CSRF-Token` header). Streamlit had equivalent XSRF protection built in.
- **Chat markdown is sanitized** before rendering. `marked` passes raw HTML
  through, and agent responses quote free text from dive pickles and Garmin
  activity notes, so a crafted dive note could execute script in the page.
  Output now goes through DOMPurify, and rendering fails closed to plain text
  if the sanitizer is unavailable.
- The session cookie is now `HttpOnly` and `SameSite=Lax`.

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
