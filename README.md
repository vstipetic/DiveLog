# DiveLog

AI-powered dive log management with natural language statistics queries.

DiveLog is a Python application for managing your dive logs with advanced search, statistics, and AI-powered natural language queries. Import dives from Garmin dive computers, track your gear, and ask questions about your diving history in plain English.

## Features

### AI-Powered Queries
Ask questions about your dives in natural language:
- "What's my average dive depth?"
- "How many dives did I do in 2024?"
- "Show me all dives deeper than 30 meters"
- "Who is my most common dive buddy?"
- "What's my total dive time this year?"

### Interactive Visualizations
Generate charts from natural language:
- "Plot the distribution of my dive depths"
- "Show a bar chart of dives by month"
- "Create a pie chart of dives by location"
- "Is there a relationship between depth and dive duration?"

### Garmin .fit File Import
Parse dive data from Garmin dive computers:
- **Single dive import**: Full metadata with auto-extraction preview
- **Bulk import**: Quick import of multiple files for statistical analysis
- **Import from Garmin**: Log into Garmin Connect and download dive files directly (no manual export)
- Auto-extracts GPS coordinates, gas type, depth profiles, temperatures

### Gear Tracking
Manage your diving equipment:
- Track masks, suits, gloves, boots
- Associate gear with dives
- Mark rental vs owned equipment

## Installation

### Prerequisites
- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer

### Setup

1. Clone the repository:
```bash
git clone https://github.com/vstipetic/DiveLog.git
cd DiveLog
```

2. Install dependencies:
```bash
uv sync
```

3. Set up an API key for AI features (at least one required) using a local `.env` file:
```powershell
copy .env.example .env
```

Then edit `.env` and set one or more keys:
```env
# Option 1: Google Gemini (recommended - free tier available)
GEMINI_API_KEY=your-gemini-api-key

# Option 2: OpenAI
OPENAI_API_KEY=your-openai-api-key

# Option 3: Anthropic Claude
ANTHROPIC_API_KEY=your-anthropic-api-key
```

Optionally, to pre-fill the "Import from Garmin" login form, add your Garmin
Connect credentials to the same `.env` (these are optional — you can also type
them into the UI):

```bash
GARMIN_EMAIL=you@example.com
GARMIN_PASSWORD=your-garmin-password
```

## Usage

### Running the Application

```bash
uv run python app.py
```

Then open `http://localhost:5000` in your browser. The web interface has three tabs:

### AI Chat Tab
Ask questions about your dives in natural language. The AI agent can:
- Filter dives by depth, date, duration, buddy, location, temperature
- Calculate statistics (averages, totals, counts, breakdowns)
- Generate visualizations (histograms, bar charts, pie charts, scatter plots)

Quick stats are displayed at the top showing total dives, dive time, and depth statistics.

### Import Dives Tab
Import dives from Garmin .fit files:

**Single Dive Mode:**
- Upload a .fit file
- View auto-extracted data (depth, duration, GPS, gas type, etc.)
- Add manual metadata (buddy, location name, gear, tank pressures)
- Save to your dive log

**Bulk Import Mode:**
- Select a folder containing .fit files
- Preview files before import
- Import all files automatically with progress tracking
- View extraction summary

**Import from Garmin Mode:**
- Log into your Garmin Connect account (multi-factor auth supported)
- Uses the unofficial `garminconnect` library — the same login flow as the Garmin app
- Login token is cached under `Storage/.garmin_tokens/`, so you only enter your password (and MFA code) once
- Optionally pre-fill credentials with `GARMIN_EMAIL` / `GARMIN_PASSWORD` in `.env`
- Choose a date range, pick from your diving activities, and import — already-imported dives are skipped

### Add Gear Tab
Create and manage your diving equipment:
- Select gear type (Mask, Suit, Gloves, Boots)
- Enter name and description
- Set type-specific properties (thickness, size)
- Mark as rental equipment if applicable

## Project Structure

The application is split into a Flask backend and a Jinja2 frontend, on top of
a shared core (`Utilities/`) that also hosts the AI agent and its tools:

```
DiveLog/
├── app.py                    # Entry point (run this)
├── backend/                  # Flask backend
│   ├── state.py              # Server-side session state (agent, chat, Garmin)
│   ├── services/             # Application logic wrapping Utilities/
│   └── routes/               # HTML routes + JSON chat API
├── frontend/                 # Jinja2 frontend
│   ├── templates/            # Page templates (chat, import, gear)
│   └── static/               # CSS + JS (charts rendered with vega-embed)
├── Storage/
│   ├── Dives/                # Your dive files
│   ├── Gear/                 # Your gear files
│   └── BulkDives/            # Bulk imported dives
└── Utilities/                # Core logic + StatisticsAgent and agent tools
```

The AI chat uses a small JSON API (`POST /api/chat`); charts created by the
agent's chart tools are serialized to Vega-Lite and rendered in the browser.

## Supported Hardware

- **Garmin Descent Series**: Mk1, Mk2, Mk2i, Mk2s, Mk3, Mk3i, G1
- Any Garmin device that exports .fit dive files

## API Keys

DiveLog requires an LLM API key for AI features. Get one from:
- [Google AI Studio](https://aistudio.google.com/) - Gemini (free tier available)
- [OpenAI](https://platform.openai.com/) - GPT-4
- [Anthropic](https://console.anthropic.com/) - Claude

The app reads keys from the project-root `.env` file (loaded at runtime). It no longer depends on shell-exported environment variables.

## License

MIT License

## Contributing

Contributions welcome! See `.claude/CLAUDE.md` for development guidelines.
