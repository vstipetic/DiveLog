"""Sidebar settings and quick actions."""

from flask import Blueprint, flash, redirect, request

from backend.services import chat_service, settings_service
from backend.state import state

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


def _back():
    return redirect(request.form.get("next") or request.referrer or "/")


@settings_bp.post("/provider")
def set_provider():
    """Apply the LLM provider / model selection from the sidebar."""
    settings_service.apply_selection(
        request.form.get("key_name"),
        request.form.get("openrouter_model"),
    )
    return _back()


@settings_bp.post("/reload-dives")
def reload_dives():
    """Reload dives from storage into the agent."""
    if state.agent:
        state.agent.reload_dives()
        flash("Dives reloaded!", "success")
    else:
        chat_service.refresh_agent()
        flash("Agent cache cleared. Dives will be reloaded on next query.", "info")
    return _back()


@settings_bp.post("/clear-chat")
def clear_chat():
    """Clear the chat transcript (sidebar quick action)."""
    chat_service.clear_chat()
    flash("Chat cleared.", "success")
    return _back()
