"""
Progress tracking for long-running imports.

Bulk and Garmin imports walk a list of files one at a time and can easily run
for minutes. Doing that inline in the request handler leaves the browser on a
blank page until the very end, with no feedback and a real timeout risk -- the
Streamlit UI had a progress bar and a per-file status line, and this is the
equivalent.

An import now runs on a worker thread that reports into an :class:`ImportJob`.
The page polls ``GET /import/progress`` for a snapshot: overall counts, the
item being processed right now, and the outcome of every item finished so far.
The worker only touches ``backend.state`` and the filesystem, never the Flask
request context.
"""

import threading
import traceback
from typing import Any, Callable, Dict, List, Optional


class ImportJob:
    """Thread-safe progress record for a single import run."""

    def __init__(self, kind: str, total: int) -> None:
        self.kind = kind  # "bulk" | "garmin"
        self.total = total

        self._lock = threading.Lock()
        self._current: Optional[str] = None
        self._items: List[Dict[str, str]] = []
        self._finished = False
        self._results: Optional[Dict[str, Any]] = None

    # --- worker-thread side --------------------------------------------------

    def start_item(self, name: str) -> None:
        """Mark ``name`` as the item currently being processed."""
        with self._lock:
            self._current = name

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        """Record the outcome of one item."""
        with self._lock:
            self._items.append(
                {
                    "name": name,
                    "status": "success" if ok else "error",
                    "detail": detail,
                }
            )
            self._current = None

    def finish(self, results: Optional[Dict[str, Any]]) -> None:
        """Mark the run complete and attach its summary."""
        with self._lock:
            self._current = None
            self._results = results
            self._finished = True

    # --- request-thread side -------------------------------------------------

    @property
    def finished(self) -> bool:
        with self._lock:
            return self._finished

    @property
    def results(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._results

    def snapshot(self) -> Dict[str, Any]:
        """A JSON-safe view of the run, for the progress endpoint."""
        with self._lock:
            done = len(self._items)
            return {
                "kind": self.kind,
                "total": self.total,
                "done": done,
                "current": self._current,
                "finished": self._finished,
                "percent": round(100 * done / self.total) if self.total else 100,
                "success_count": sum(
                    1 for item in self._items if item["status"] == "success"
                ),
                "error_count": sum(
                    1 for item in self._items if item["status"] == "error"
                ),
                "items": list(self._items),
            }


def start_job(
    kind: str, total: int, work: Callable[[ImportJob], Optional[Dict[str, Any]]]
) -> ImportJob:
    """
    Run ``work(job)`` on a daemon thread and return the job immediately.

    Whatever ``work`` returns becomes the job's results dict. An unhandled
    exception is captured as the results' ``fatal_error`` so the page can show
    it instead of the run appearing to hang forever.
    """
    job = ImportJob(kind, total)

    def _run() -> None:
        try:
            job.finish(work(job))
        except Exception as e:
            traceback.print_exc()
            job.finish(
                {
                    "success_count": 0,
                    "error_count": 0,
                    "errors": [],
                    "items": [],
                    "fatal_error": str(e),
                }
            )

    threading.Thread(target=_run, name=f"divelog-import-{kind}", daemon=True).start()
    return job


# --- lifecycle helpers tying jobs to the shared app state ---------------------

def job_running() -> bool:
    """True while an import is in flight (only one runs at a time)."""
    from backend.state import state

    return state.import_job is not None and not state.import_job.finished


def harvest_finished_job() -> None:
    """
    Move a completed job's results into the slot its page renders from.

    Called when the import page is rendered, so the results panel appears on
    the first load after the worker thread finishes.
    """
    from backend.state import state

    job = state.import_job
    if job is None or not job.finished:
        return

    if job.kind == "bulk":
        state.bulk_results = job.results
    else:
        state.garmin_results = job.results
    state.import_job = None
