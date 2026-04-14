import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv


def _load_env_file() -> None:
    """Load API keys from project-level .env file."""
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(dotenv_path=project_root / ".env", override=False)

def detect_api_keys() -> Dict[str, str]:
    """
    Scans .env-loaded environment values for available LLM API keys.

    Returns:
        Dict[str, str]: Dictionary mapping service names to their API keys
    """
    _load_env_file()
    available_apis = {}

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        available_apis["OpenAI"] = openai_key

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        available_apis["Gemini"] = gemini_key

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        available_apis["Anthropic"] = anthropic_key

    return available_apis 