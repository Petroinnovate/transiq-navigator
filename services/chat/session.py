"""
Chat Session — Thin wrapper holding per-request state.

A ``ChatSession`` carries the user query, any caller-supplied context,
and an optional LLM override.  It delegates the actual loop to
``orchestrator.handle_chat``.

Usage::

    session = ChatSession(query="Forecast ROP for this well", context={"kpis": [...]})
    result  = session.run()          # dict with query, steps, final_answer, tools_used
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from services.chat.orchestrator import handle_chat

logger = logging.getLogger(__name__)


class ChatSession:
    """Encapsulates one chat request and its execution."""

    __slots__ = ("query", "context", "_llm_generate_json")

    def __init__(
        self,
        query: str,
        context: Dict[str, Any] | None = None,
        *,
        llm_generate_json: Optional[Callable[..., Dict[str, Any]]] = None,
    ) -> None:
        self.query = query
        self.context = context or {}
        self._llm_generate_json = llm_generate_json

    def run(self) -> Dict[str, Any]:
        """Execute the chat orchestration loop and return the result dict."""
        logger.info("ChatSession.run  query=%r", self.query[:80])
        return handle_chat(
            query=self.query,
            context=self.context,
            llm_generate_json=self._llm_generate_json,
        )
