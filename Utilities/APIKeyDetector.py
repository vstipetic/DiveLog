from pathlib import Path
from typing import Dict

from dotenv import dotenv_values


def _load_env_values() -> Dict[str, str]:
    """Read key/value pairs from project env files only."""
    project_root = Path(__file__).resolve().parent.parent
    env_values: Dict[str, str] = {}

    # Precedence: .env.local > .env
    for env_path in (
        project_root / ".env",
        project_root / ".env.local",
    ):
        if not env_path.exists():
            continue

        parsed_values = dotenv_values(env_path)
        for key, value in parsed_values.items():
            if isinstance(value, str) and value.strip():
                env_values[key] = value.strip()

    return env_values

def detect_api_keys() -> Dict[str, str]:
    """
    Scans project .env files for available LLM API keys.

    Returns:
        Dict[str, str]: Dictionary mapping service names to their API keys
    """
    env_values = _load_env_values()
    available_apis = {}

    openai_key = env_values.get("OPENAI_API_KEY")
    if openai_key:
        available_apis["OpenAI"] = openai_key

    gemini_key = env_values.get("GEMINI_API_KEY")
    if gemini_key:
        available_apis["Gemini"] = gemini_key

    anthropic_key = env_values.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        available_apis["Anthropic"] = anthropic_key

    openrouter_key = env_values.get("OPENROUTER_API_KEY")
    if openrouter_key:
        available_apis["OpenRouter"] = openrouter_key

    return available_apis 