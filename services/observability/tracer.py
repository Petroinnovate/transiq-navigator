"""
Observability — Execution Tracer.

Tracks the full lifecycle of a query through the system::

    trace = start_trace(query="Forecast ROP")
    trace.add_step("kpi_analysis", duration_ms=80, status="success")
    trace.add_step("predictive_forecast", duration_ms=220, status="success")
    summary = end_trace(trace.trace_id)

Each ``Trace`` records:
  * ``trace_id``  — unique correlation id
  * ``query``     — original user query
  * ``steps``     — ordered list of step dicts with timing
  * ``tools_used``— de-duped tool names
  * ``start / end / duration_ms`` — wall-clock timing

Completed traces are kept in a bounded in-memory store
(``get_recent_traces``, ``get_trace``) for debugging.
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional


_MAX_STORED_TRACES = 200
_lock = threading.Lock()
_active: Dict[str, "Trace"] = {}
_completed: Deque["Trace"] = deque(maxlen=_MAX_STORED_TRACES)


# ── Trace dataclass ────────────────────────────────────────────────────

@dataclass
class Trace:
    """Mutable trace that accumulates steps during a request lifecycle."""

    trace_id: str
    query: str
    component: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    _start_ns: int = field(default=0, repr=False)
    _end_ns: int = field(default=0, repr=False)

    # ── Step tracking ──────────────────────────────────────────────────

    def add_step(
        self,
        tool: str,
        *,
        status: str = "success",
        duration_ms: float = 0,
        step: int | None = None,
        extra: Dict[str, Any] | None = None,
    ) -> None:
        entry: Dict[str, Any] = {
            "tool": tool,
            "status": status,
            "duration_ms": round(duration_ms, 2),
        }
        if step is not None:
            entry["step"] = step
        if extra:
            entry.update(extra)
        self.steps.append(entry)

    def add_llm_call(
        self,
        *,
        status: str = "success",
        duration_ms: float = 0,
        iteration: int = 0,
    ) -> None:
        entry: Dict[str, Any] = {
            "tool": "__llm__",
            "status": status,
            "duration_ms": round(duration_ms, 2),
        }
        if iteration:
            entry["iteration"] = iteration
        self.steps.append(entry)

    def add_error(
        self,
        component: str,
        error_msg: str,
        *,
        error_type: str = "",
    ) -> None:
        entry: Dict[str, Any] = {
            "component": component,
            "error": error_msg,
        }
        if error_type:
            entry["error_type"] = error_type
        self.errors.append(entry)

    # ── Computed properties ────────────────────────────────────────────

    @property
    def tools_used(self) -> List[str]:
        seen: set[str] = set()
        out: list[str] = []
        for s in self.steps:
            t = s.get("tool", "")
            if t and t != "__llm__" and t not in seen:
                seen.add(t)
                out.append(t)
        return out

    @property
    def duration_ms(self) -> float:
        if self._end_ns and self._start_ns:
            return (self._end_ns - self._start_ns) / 1_000_000
        return 0.0

    # ── Serialisation ──────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "component": self.component,
            "steps": list(self.steps),
            "tools_used": self.tools_used,
            "errors": list(self.errors),
            "duration_ms": round(self.duration_ms, 2),
        }


# ── Public API ─────────────────────────────────────────────────────────

def start_trace(
    query: str,
    *,
    component: str = "",
    trace_id: str | None = None,
) -> Trace:
    """Begin a new trace.  Returns the live ``Trace`` object."""
    tid = trace_id or uuid.uuid4().hex[:16]
    t = Trace(trace_id=tid, query=query, component=component)
    t._start_ns = time.perf_counter_ns()
    with _lock:
        _active[tid] = t
    return t


def end_trace(trace_id: str) -> Dict[str, Any]:
    """Finalise a trace and move it to the completed store.

    Returns the trace summary dict.  If ``trace_id`` is unknown, returns
    a minimal error dict.
    """
    with _lock:
        t = _active.pop(trace_id, None)
    if t is None:
        return {"trace_id": trace_id, "error": "unknown trace"}
    t._end_ns = time.perf_counter_ns()
    with _lock:
        _completed.append(t)
    return t.to_dict()


def get_trace(trace_id: str) -> Dict[str, Any] | None:
    """Retrieve a completed trace by id."""
    with _lock:
        # Check active first
        if trace_id in _active:
            return _active[trace_id].to_dict()
        for t in _completed:
            if t.trace_id == trace_id:
                return t.to_dict()
    return None


def get_recent_traces(limit: int = 20) -> List[Dict[str, Any]]:
    """Return up to *limit* most-recent completed traces (newest first)."""
    with _lock:
        traces = list(_completed)
    traces.reverse()
    return [t.to_dict() for t in traces[:limit]]


def _reset() -> None:
    """Clear all traces (for testing)."""
    with _lock:
        _active.clear()
        _completed.clear()
