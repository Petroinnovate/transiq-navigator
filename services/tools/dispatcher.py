"""
Tool Registry — Dispatcher.

dispatch_tool() is the single entry-point for executing a tool by name.
It validates the tool exists, performs lightweight input-schema validation,
executes the handler with exception safety, and returns a ToolResult.

Safety:
  * MAX_TOOL_CALLS_PER_REQUEST is enforced by the caller (e.g. an agent
    loop).  A helper ``make_call_counter()`` is provided.
  * Each handler is wrapped in a blanket try/except so a failing tool
    never crashes the request.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict

from services.tools.registry import get_tool
from services.tools.schemas import ToolResult

logger = logging.getLogger(__name__)

# ── Safety limit ───────────────────────────────────────────────────────
MAX_TOOL_CALLS_PER_REQUEST = 25


class ToolCallLimitExceeded(Exception):
    """Raised when a request tries to dispatch more than the allowed max."""


class CallCounter:
    """Tracks tool invocations within a single request / agent loop."""

    __slots__ = ("_count", "_limit")

    def __init__(self, limit: int = MAX_TOOL_CALLS_PER_REQUEST) -> None:
        self._count = 0
        self._limit = limit

    def increment(self) -> None:
        self._count += 1
        if self._count > self._limit:
            raise ToolCallLimitExceeded(
                f"Tool call limit exceeded ({self._limit})"
            )

    @property
    def count(self) -> int:
        return self._count


def make_call_counter(limit: int = MAX_TOOL_CALLS_PER_REQUEST) -> CallCounter:
    """Create a fresh counter.  Pass it into ``dispatch_tool`` per request."""
    return CallCounter(limit)


# ── Schema validation (basic) ─────────────────────────────────────────

def _validate_input(input_data: Dict[str, Any], schema: Dict[str, Any]) -> str | None:
    """Return an error message if required fields are missing, else None.

    Only checks top-level ``required`` from the JSON-schema.  Full JSON-schema
    validation can be bolted on later without changing the interface.
    """
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    missing = [f for f in required if f not in input_data]
    if missing:
        return f"Missing required fields: {', '.join(missing)}"

    # Type spot-checks for documented property types
    for key, value in input_data.items():
        prop_schema = properties.get(key)
        if prop_schema is None:
            continue
        expected = prop_schema.get("type")
        if expected == "array" and not isinstance(value, list):
            return f"Field {key!r} must be an array"
        if expected == "number" and not isinstance(value, (int, float)):
            return f"Field {key!r} must be a number"
        if expected == "object" and not isinstance(value, dict):
            return f"Field {key!r} must be an object"
    return None


# ── Dispatch ───────────────────────────────────────────────────────────

def dispatch_tool(
    name: str,
    input_data: Dict[str, Any],
    *,
    counter: CallCounter | None = None,
    cache: Any | None = None,
) -> Dict[str, Any]:
    """Execute a registered tool and return a structured ToolResult dict.

    Parameters
    ----------
    name:
        Registered tool name.
    input_data:
        Arguments forwarded to the tool handler.
    counter:
        Optional ``CallCounter`` to enforce per-request limits.
    cache:
        Optional ``ToolCache`` instance for result caching.

    Returns
    -------
    dict with keys ``tool``, ``status``, and ``result`` or ``error``.
    """

    # ── Safety limit ───────────────────────────────────────────────────
    if counter is not None:
        try:
            counter.increment()
        except ToolCallLimitExceeded:
            return ToolResult(
                tool=name,
                status="error",
                error=f"Tool call limit exceeded ({MAX_TOOL_CALLS_PER_REQUEST})",
            ).to_dict()

    # ── Lookup ─────────────────────────────────────────────────────────
    tool_def = get_tool(name)
    if tool_def is None:
        return ToolResult(
            tool=name,
            status="error",
            error=f"Unknown tool: {name!r}",
        ).to_dict()

    # ── Input validation ───────────────────────────────────────────────
    err = _validate_input(input_data, tool_def.input_schema)
    if err:
        return ToolResult(
            tool=name,
            status="error",
            error=err,
        ).to_dict()

    # ── Cache lookup ───────────────────────────────────────────────────
    if cache is not None:
        try:
            cached = cache.get(name, input_data)
            if cached is not None:
                logger.debug("Cache HIT for tool %r", name)
                return ToolResult(tool=name, status="success", result=cached).to_dict()
        except Exception:
            pass

    # ── Execute with exception safety ──────────────────────────────────
    _t0 = time.perf_counter()
    try:
        result = tool_def.handler(input_data)
    except Exception as exc:
        _ms = (time.perf_counter() - _t0) * 1000
        logger.exception("Tool %r raised an exception", name)
        # ── Observability: error capture ──────────────────────────────
        try:
            from services.observability import logger as obs_logger, metrics
            obs_logger.capture_exception("tool_dispatcher", exc, extra={"tool": name})
            metrics.record_latency(f"tool.{name}", _ms)
            metrics.record_tool_usage(name)
            metrics.record_error("tool_dispatcher", name)
        except Exception:
            pass
        return ToolResult(
            tool=name,
            status="error",
            error=f"Tool {name!r} failed during execution",
        ).to_dict()

    _ms = (time.perf_counter() - _t0) * 1000
    # ── Observability: success ─────────────────────────────────────
    try:
        from services.observability import metrics
        metrics.record_latency(f"tool.{name}", _ms)
        metrics.record_tool_usage(name)
    except Exception:
        pass

    # ── Cache store ────────────────────────────────────────────────
    if cache is not None:
        try:
            cache.put(name, input_data, result)
        except Exception:
            pass

    return ToolResult(
        tool=name,
        status="success",
        result=result,
    ).to_dict()
