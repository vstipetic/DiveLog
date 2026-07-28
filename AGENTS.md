# DiveLog

AI-powered dive log management (single Streamlit web app). See `README.md` for the full product overview and `.claude/claude.md` for development guidelines.

## Cursor Cloud specific instructions

- Package manager is `uv` (already installed on the VM and on `PATH` via `~/.bashrc`). Standard commands are documented in `README.md`; the update script runs `uv sync --extra dev` on startup so dependencies (including `pytest`) are ready.
- Run the app in dev mode: `uv run streamlit run streamlit_app.py`. It serves on port `8501`. In this headless VM, start it as `uv run streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true`.
- Non-obvious gotcha: the main UI (all three tabs) is gated on at least one LLM API key. Keys are read ONLY from a project-root `.env`/`.env.local` file (via `Utilities/APIKeyDetector.py`), NOT from shell env vars. With no key file present the app shows only a "missing API key" warning and no tabs. To load the UI you must create `.env` with one of `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY`. A dummy value is enough to render the UI and exercise the Import Dives / Add Gear tabs; a real key is required for the AI Chat features to actually work. `.env` is gitignored.
- There is no database. Persistence is local pickle files under `Storage/` (gitignored, auto-created at runtime: `Dives/`, `Gear/`, `BulkDives/`, `.garmin_tokens/`).
- No automated tests currently exist in the repo (a `dev` group with `pytest` is configured, but `uv run pytest` collects 0 tests). No linter/formatter is configured.
- Garmin import and AI Chat require real external credentials/keys and network access; they are optional for local development.
