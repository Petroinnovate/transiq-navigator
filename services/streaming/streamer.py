"""
Streaming Manager — Plugs into the existing WebSocket ``ConnectionManager``.

``StreamingManager`` wraps the global ``manager`` from
``app.websocket.handlers`` and provides a clean API for emitting events
during chat / agent orchestration.  If no WebSocket connection is active
(or the WebSocket layer is unreachable), every method is a silent no-op
so callers never need to guard.

Usage::

    from services.streaming import get_streaming_manager

    sm = get_streaming_manager("session-123")
    sm.emit_llm_start(iteration=1)
    sm.emit_tool_start("six_sigma_analysis", step=1)
    sm.emit_tool_end("six_sigma_analysis", step=1)
    sm.emit_final_response("Analysis complete.", tools_used=["six_sigma_analysis"])
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Generator, List, Optional

from services.streaming.event_types import (
    StreamEvent,
    final_response_event,
    llm_end_event,
    llm_start_event,
    llm_token_event,
    tool_end_event,
    tool_progress_event,
    tool_start_event,
)

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────

def _get_connection_manager():  # type: ignore[return]
    """Late-import the global ``manager`` so imports never fail."""
    try:
        from app.websocket.handlers import manager  # type: ignore[import-untyped]
        return manager
    except Exception:
        return None


def _fire_and_forget(coro):  # noqa: ANN001
    """Schedule *coro* on the running event loop if one exists.

    In a synchronous context (e.g. tests, CLI) this is a harmless no-op.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        # No running event loop — skip silently
        pass


# ── StreamingManager ──────────────────────────────────────────────────

class StreamingManager:
    """Thin façade over the WebSocket ConnectionManager.

    Parameters
    ----------
    session_id:
        The channel key used to route events to the correct WebSocket
        clients.  Typically a chat session id or document id.
    """

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        # Accumulates events even when no WS is active (useful for tests)
        self._buffer: List[Dict[str, Any]] = []

    # ── Core send ──────────────────────────────────────────────────────

    def send_event(self, event: StreamEvent) -> None:
        """Emit *event* over WebSocket (if connected) and buffer it."""
        payload = event.to_dict()
        self._buffer.append(payload)

        mgr = _get_connection_manager()
        if mgr is None:
            return

        # ``broadcast`` is async — schedule it non-blocking
        _fire_and_forget(mgr.broadcast(self._session_id, payload))

    # ── LLM lifecycle ──────────────────────────────────────────────────

    def emit_llm_start(self, *, iteration: int = 1) -> None:
        self.send_event(llm_start_event(iteration=iteration))

    def emit_llm_token(self, token: str, *, iteration: int = 1) -> None:
        self.send_event(llm_token_event(token, iteration=iteration))

    def emit_llm_end(self, *, iteration: int = 1, success: bool = True) -> None:
        self.send_event(llm_end_event(iteration=iteration, success=success))

    def stream_llm_tokens(
        self, generator: Generator[str, None, None], *, iteration: int = 1,
    ) -> str:
        """Consume a token generator, emit ``llm_token`` events, and return
        the concatenated full text."""
        chunks: list[str] = []
        for token in generator:
            chunks.append(token)
            self.emit_llm_token(token, iteration=iteration)
        return "".join(chunks)

    # ── Tool lifecycle ─────────────────────────────────────────────────

    def emit_tool_start(self, tool_name: str, *, step: int = 0) -> None:
        self.send_event(tool_start_event(tool_name, step=step))

    def emit_tool_progress(
        self,
        tool_name: str,
        status: str,
        *,
        step: int = 0,
        detail: Optional[str] = None,
    ) -> None:
        self.send_event(tool_progress_event(tool_name, status, step=step, detail=detail))

    def emit_tool_end(
        self, tool_name: str, *, step: int = 0, success: bool = True,
    ) -> None:
        self.send_event(tool_end_event(tool_name, step=step, success=success))

    def stream_tool_progress(self, tool_name: str, status: str) -> None:
        """Convenience alias matching the spec's ``stream_tool_progress``."""
        self.emit_tool_progress(tool_name, status)

    # ── Final response ─────────────────────────────────────────────────

    def emit_final_response(
        self, answer: str, *, tools_used: list[str] | None = None,
    ) -> None:
        self.send_event(final_response_event(answer, tools_used=tools_used))

    # ── Introspection ──────────────────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def events(self) -> List[Dict[str, Any]]:
        """Return a copy of all buffered events (newest last)."""
        return list(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()


# ── Module-level factory ───────────────────────────────────────────────

def get_streaming_manager(session_id: str) -> StreamingManager:
    """Return a ``StreamingManager`` for *session_id*.

    Every call returns a fresh instance so there is no global state to
    manage — the WebSocket ConnectionManager itself is the singleton.
    """
    return StreamingManager(session_id)
