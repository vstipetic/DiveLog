"""JSON API for the chat interface."""

from flask import Blueprint, jsonify, request

from backend.services import chat_service
from backend.state import state

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@chat_bp.post("")
def post_message():
    """Process a user query through the StatisticsAgent."""
    data = request.get_json(silent=True) or {}
    query = (data.get("message") or "").strip()
    if not query:
        return jsonify({"ok": False, "error": "Empty message."}), 400

    try:
        assistant_message = chat_service.process_query(query)
    except RuntimeError as e:
        return jsonify({"ok": False, "error": str(e)}), 503

    return jsonify({"ok": True, "message": assistant_message})


@chat_bp.post("/clear")
def clear_chat():
    """Clear the transcript and the agent's conversational memory."""
    chat_service.clear_chat()
    return jsonify({"ok": True})


@chat_bp.get("/history")
def history():
    """Return the full transcript (used by the frontend on page load)."""
    return jsonify({"ok": True, "messages": state.messages})
