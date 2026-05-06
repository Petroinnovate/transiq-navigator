"""
Observability — Structured Logger.

Emits JSON-structured log entries for requests, tool calls, errors, and
responses.  Sits alongside the existing ``core.logging.logger`` — it does
NOT replace it.  Instead it provides a thin API that callers use to emit
machine-parseable events::

    from services.observability import obs_logger

    obs_logger.tool_call("kpi_analysis", status="success", duration_ms=120)
    obs_logger.error("chat_orchestrator", error="LLM timeout", trace_id="abc")

All events are written through Python's standard ``logging`` module at
INFO level (errors at ERROR) in JSON format to the ``transiq.observability``
logger name.
"""
from __future__ import annotations

import json
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional


# ── Dedicated logger (does NOT touch the root logger) ──────────────────
_obs = logging.getLogger("transiq.observability")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit(level: int, event: Dict[str, Any]) -> None:
    """Write *event* as a single-line JSON string."""
    event.setdefault("timestamp", _now_iso())
    try:
        _obs.log(level, json.dumps(event, default=str))
    except Exception:
        # Never crash the caller
        pass


# ── Public API ─────────────────────────────────────────────────────────

def request(
    query: str,
    *,
    trace_id: str = "",
    component: str = "",
    extra: Dict[str, Any] | None = None,
) -> None:
    """Log an incoming request / query."""
    evt: Dict[str, Any] = {
        "event": "request",
        "query": query,
        "component": component,
    }
    if trace_id:
        evt["trace_id"] = trace_id
    if extra:
        evt.update(extra)
    _emit(logging.INFO, evt)


def tool_call(
    tool: str,
    *,
    status: str = "success",
    duration_ms: float = 0,
    trace_id: str = "",
    step: int | None = None,
    extra: Dict[str, Any] | None = None,
) -> None:
    """Log a tool invocation."""
    evt: Dict[str, Any] = {
        "event": "tool_call",
        "tool": tool,
        "status": status,
        "duration_ms": round(duration_ms, 2),
    }
    if trace_id:
        evt["trace_id"] = trace_id
    if step is not None:
        evt["step"] = step
    if extra:
        evt.update(extra)
    _emit(logging.INFO, evt)


def llm_call(
    *,
    status: str = "success",
    duration_ms: float = 0,
    iteration: int = 0,
    trace_id: str = "",
    extra: Dict[str, Any] | None = None,
) -> None:
    """Log an LLM call."""
    evt: Dict[str, Any] = {
        "event": "llm_call",
        "status": status,
        "duration_ms": round(duration_ms, 2),
    }
    if iteration:
        evt["iteration"] = iteration
    if trace_id:
        evt["trace_id"] = trace_id
    if extra:
        evt.update(extra)
    _emit(logging.INFO, evt)


def response(
    *,
    trace_id: str = "",
    component: str = "",
    duration_ms: float = 0,
    tools_used: list[str] | None = None,
    success: bool = True,
    extra: Dict[str, Any] | None = None,
) -> None:
    """Log a completed response."""
    evt: Dict[str, Any] = {
        "event": "response",
        "component": component,
        "success": success,
        "duration_ms": round(duration_ms, 2),
    }
    if trace_id:
        evt["trace_id"] = trace_id
    if tools_used:
        evt["tools_used"] = tools_used
    if extra:
        evt.update(extra)
    _emit(logging.INFO, evt)


def error(
    component: str,
    *,
    error_msg: str = "",
    error_type: str = "",
    trace_id: str = "",
    stack_trace: str = "",
    extra: Dict[str, Any] | None = None,
) -> None:
    """Log an error with optional stack trace, tagged by component."""
    evt: Dict[str, Any] = {
        "event": "error",
        "component": component,
        "error": error_msg,
    }
    if error_type:
        evt["error_type"] = error_type
    if trace_id:
        evt["trace_id"] = trace_id
    if stack_trace:
        evt["stack_trace"] = stack_trace
    if extra:
        evt.update(extra)
    _emit(logging.ERROR, evt)


def capture_exception(
    component: str,
    exc: BaseException,
    *,
    trace_id: str = "",
    extra: Dict[str, Any] | None = None,
) -> None:
    """Log an exception with its full stack trace, tagged by component."""
    error(
        component,
        error_msg=str(exc),
        error_type=type(exc).__name__,
        trace_id=trace_id,
        stack_trace=traceback.format_exc(),
        extra=extra,
    )
