"""
Memory System — Episodic memory.

Records and retrieves full conversation episodes (query → tools → answer).
Thin layer over MemoryStore that adds formatting for LLM context injection.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from services.memory.store import MemoryStore

logger = logging.getLogger(__name__)


class EpisodicMemory:
    """Record and retrieve conversation episodes."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    # ── Write ──────────────────────────────────────────────────────────

    def record(
        self,
        query: str,
        tools_used: List[str],
        steps: List[Dict[str, Any]],
        final_answer: str,
        context: Dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> int:
        """Store a completed conversation as an episode."""
        return self._store.save_episode(
            query=query,
            tools_used=tools_used,
            steps=steps,
            final_answer=final_answer,
            context=context,
            session_id=session_id,
        )

    # ── Read ───────────────────────────────────────────────────────────

    def recall(
        self,
        query: str,
        *,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find past episodes relevant to *query* (keyword search)."""
        return self._store.search_episodes(query, limit=limit)

    def recent(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Return the most recent episodes regardless of query."""
        return self._store.recent_episodes(limit=limit)

    # ── Formatting for LLM context ─────────────────────────────────────

    def format_for_context(
        self,
        episodes: List[Dict[str, Any]],
        *,
        max_episodes: int = 3,
    ) -> str:
        """Format episodes into a text block for system-prompt injection.

        Returns an empty string if no episodes are provided.
        """
        if not episodes:
            return ""

        lines = ["PAST CONVERSATIONS (for reference):"]
        for ep in episodes[:max_episodes]:
            tools = ", ".join(ep.get("tools_used", [])) or "none"
            answer = (ep.get("final_answer") or "")[:300]
            lines.append(
                f"- Q: {ep['query']}\n"
                f"  Tools: {tools}\n"
                f"  A: {answer}"
            )
        return "\n".join(lines)

    @property
    def count(self) -> int:
        return self._store.episode_count()
