"""
Memory System — Cortex (executive coordinator).

Orchestrates episodic memory and learnings to:
  1. Build memory context for LLM prompt injection  (``get_context``)
  2. Store completed episodes                        (``store_episode``)
  3. Trigger learning extraction after each episode  (``learn``)

The Cortex is the only class external code needs to interact with.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from services.memory.store import MemoryStore
from services.memory.episodes import EpisodicMemory
from services.memory.hippocampus import Hippocampus

logger = logging.getLogger(__name__)

# Max characters of memory text injected into the prompt
_MAX_CONTEXT_CHARS = 3000


class Cortex:
    """Executive coordinator for the memory system."""

    def __init__(self, store: MemoryStore | None = None) -> None:
        self._store = store or MemoryStore()
        self.episodes = EpisodicMemory(self._store)
        self.hippocampus = Hippocampus(self._store)

    # ── 1. Retrieve context for prompt injection ───────────────────────

    def get_context(self, query: str) -> Dict[str, Any]:
        """Build a memory context dict to inject before the LLM call.

        Returns
        -------
        ::

            {
                "memory_text": str,   # formatted text for the system prompt
                "episodes": [...],    # raw episode dicts
                "learnings": [...],   # raw learning dicts
            }

        ``memory_text`` is capped at ``_MAX_CONTEXT_CHARS`` to bound
        token usage.
        """
        # Retrieve relevant episodes (keyword match)
        episodes = self.episodes.recall(query, limit=3)

        # Retrieve relevant learnings + all rules (always-on)
        relevant_learnings = self.hippocampus.recall(query, limit=5)
        rules = self.hippocampus.all_rules(limit=10)

        # Merge & deduplicate learnings (rules first, then relevant)
        seen_ids: set[int] = set()
        merged_learnings: List[Dict[str, Any]] = []
        for item in rules + relevant_learnings:
            lid = item.get("id")
            if lid and lid not in seen_ids:
                seen_ids.add(lid)
                merged_learnings.append(item)

        # Format
        ep_text = self.episodes.format_for_context(episodes)
        lr_text = self.hippocampus.format_for_context(merged_learnings)

        parts = [p for p in (lr_text, ep_text) if p]
        memory_text = "\n\n".join(parts)

        # Truncate to budget
        if len(memory_text) > _MAX_CONTEXT_CHARS:
            memory_text = memory_text[:_MAX_CONTEXT_CHARS] + "\n[... memory truncated]"

        return {
            "memory_text": memory_text,
            "episodes": episodes,
            "learnings": merged_learnings,
        }

    # ── 2. Store a completed episode ───────────────────────────────────

    def store_episode(self, chat_result: Dict[str, Any]) -> int:
        """Persist a chat result as an episode.

        Parameters
        ----------
        chat_result:
            The dict returned by ``handle_chat()`` or ``run_agent()``.
            Expected keys: query, tools_used, steps, final_answer.

        Returns
        -------
        The episode row id.
        """
        return self.episodes.record(
            query=chat_result.get("query", ""),
            tools_used=chat_result.get("tools_used", []),
            steps=chat_result.get("steps", []),
            final_answer=chat_result.get("final_answer", ""),
        )

    # ── 3. Learn from an episode ───────────────────────────────────────

    def learn(
        self,
        chat_result: Dict[str, Any],
        *,
        llm_generate_json: Callable[..., Dict[str, Any]] | None = None,
    ) -> List[Dict[str, Any]]:
        """Extract and store learnings from a completed chat result.

        Uses the LLM if provided; otherwise falls back to heuristic
        extraction.  Returns the list of saved learnings.
        """
        return self.hippocampus.extract_learnings(
            chat_result,
            llm_generate_json=llm_generate_json,
        )

    # ── Convenience -----------------------------------------------------

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "episodes": self.episodes.count,
            "learnings": self.hippocampus.count,
        }

    def close(self) -> None:
        self._store.close()
