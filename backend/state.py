"""
Server-side application state for DiveLog.

DiveLog is a local, single-user application (previously Streamlit, which kept
this state in ``st.session_state``). The Flask backend keeps the equivalent
state in a single module-level object: the live ``StatisticsAgent`` instance,
the chat transcript, the Garmin Connect client, and transient import state.

None of these objects are serializable (the agent holds LLM clients and
un-picklable tool objects; the Garmin client holds an OAuth session), so they
cannot live in a cookie-based Flask session. A process-wide state object is
the direct equivalent of the previous behaviour.
"""

import threading
from typing import Any, Dict, List, Optional


class AppState:
    """Mutable, process-wide state shared by all requests."""

    def __init__(self) -> None:
        # --- Chat ---------------------------------------------------------
        # Each message: {"role": "user"|"assistant", "content": str,
        #                "charts": [ {spec, chart_type, title, description} ]}
        self.messages: List[Dict[str, Any]] = []

        # --- Agent / LLM configuration -------------------------------------
        self.agent: Optional[Any] = None  # StatisticsAgent
        self.api_key: Optional[str] = None
        self.provider: Optional[str] = None
        self.model: Optional[str] = None
        # Which detected .env key (by display name) the user selected.
        self.selected_key_name: Optional[str] = None
        # Which OpenRouter model label the user selected.
        self.openrouter_model_label: Optional[str] = None

        # --- Storage / import ----------------------------------------------
        self.storage_folder: str = "Storage/BulkDives"
        self.import_mode: str = "single"  # single | bulk | garmin
        # Pending single-dive upload awaiting metadata confirmation:
        # {"token": str, "path": str, "filename": str, "preview": dict}
        self.pending_upload: Optional[Dict[str, Any]] = None
        # Last scanned bulk-import folder and last bulk import results.
        self.bulk_folder: Optional[str] = None
        self.bulk_results: Optional[Dict[str, Any]] = None

        # --- Garmin Connect --------------------------------------------------
        self.garmin_client: Optional[Any] = None
        self.garmin_pending_client: Optional[Any] = None
        self.garmin_mfa_state: Optional[Dict[str, Any]] = None
        self.garmin_dive_list: Optional[List[Dict[str, Any]]] = None
        self.garmin_results: Optional[Dict[str, Any]] = None

        # Agent queries mutate shared tool state (ToolState / ChartState),
        # so query processing is serialized with this lock.
        self.chat_lock = threading.Lock()


# The single shared instance used by all services and routes.
state = AppState()
