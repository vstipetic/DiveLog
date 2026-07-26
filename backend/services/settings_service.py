"""
LLM provider / API-key settings.

Mirrors the old Streamlit sidebar: detect API keys from .env, let the user
pick a provider (and an OpenRouter model when applicable), and expose the
current selection to the rest of the backend.
"""

from typing import Dict, Optional

from Utilities.APIKeyDetector import detect_api_keys

from backend.state import state


# Display label -> OpenRouter model id (same choices as the Streamlit UI).
OPENROUTER_MODELS: Dict[str, str] = {
    "Gemini 3 Flash": "google/gemini-3-flash-preview",
    "GPT-5 mini": "openai/gpt-5-mini",
    "Claude Haiku": "anthropic/claude-3.5-haiku",
}

# Which detected key to select when the user has not picked one.
PREFERRED_DEFAULT_KEY = "OpenRouter"

# Provider code -> (display label, default model shown in the sidebar).
PROVIDER_INFO = {
    "gemini": ("Google Gemini", "gemini-1.5-flash"),
    "openai": ("OpenAI", "gpt-5-mini"),
    "claude": ("Anthropic Claude", "claude-sonnet-4-20250514"),
    "openrouter": ("OpenRouter", None),  # model chosen by the user
}


def get_provider_from_key_name(key_name: str) -> str:
    """Map API key name to provider code."""
    provider_map = {
        "OpenAI": "openai",
        "Gemini": "gemini",
        "Claude": "claude",
        "Anthropic": "claude",
        "OpenRouter": "openrouter",
    }
    for name, provider in provider_map.items():
        if name.lower() in key_name.lower():
            return provider
    return "gemini"  # Default


def default_key_name(api_keys: Dict[str, str]) -> Optional[str]:
    """
    Pick which detected key to use before the user chooses one.

    OpenRouter wins when it is configured: a single key reaches models from
    every provider, so it is the most useful starting point. Otherwise the
    detection order from APIKeyDetector applies.
    """
    for key_name in api_keys:
        if PREFERRED_DEFAULT_KEY.lower() in key_name.lower():
            return key_name
    return next(iter(api_keys), None)


def apply_selection(key_name: Optional[str], openrouter_model_label: Optional[str]) -> None:
    """Apply the user's provider selection from the sidebar form."""
    api_keys = detect_api_keys()
    if not api_keys:
        return

    if key_name not in api_keys:
        key_name = default_key_name(api_keys)

    state.selected_key_name = key_name
    provider = get_provider_from_key_name(key_name)

    model = None
    if provider == "openrouter":
        if openrouter_model_label not in OPENROUTER_MODELS:
            openrouter_model_label = next(iter(OPENROUTER_MODELS))
        state.openrouter_model_label = openrouter_model_label
        model = OPENROUTER_MODELS[openrouter_model_label]

    # The agent itself is (re)created lazily by chat_service when the
    # key/provider/model differ from the cached agent's configuration.
    state.api_key = api_keys[key_name]
    state.provider = provider
    state.model = model


def ensure_selection() -> bool:
    """
    Make sure a provider is selected if any API key is available.

    Returns True when an API key is configured, False otherwise.
    """
    api_keys = detect_api_keys()
    if not api_keys:
        return False

    if state.selected_key_name not in api_keys:
        apply_selection(default_key_name(api_keys), state.openrouter_model_label)
    return True


def get_sidebar_context() -> Dict:
    """Build the context dict consumed by the sidebar template."""
    api_keys = detect_api_keys()
    ensure_selection()

    provider = state.provider
    if provider == "openrouter":
        current_model = state.model or "openai/gpt-5-mini"
    else:
        current_model = PROVIDER_INFO.get(provider, (None, "Unknown"))[1]

    return {
        "api_key_names": list(api_keys.keys()),
        "selected_key_name": state.selected_key_name,
        "provider": provider,
        "provider_label": PROVIDER_INFO.get(provider, ("Unknown", None))[0],
        "current_model": current_model,
        "openrouter_models": list(OPENROUTER_MODELS.keys()),
        "openrouter_model_label": state.openrouter_model_label
        or next(iter(OPENROUTER_MODELS)),
        "has_api_key": bool(api_keys),
        "storage_folder": state.storage_folder,
    }
