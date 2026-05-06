"""
Memory System — Hippocampus (learnings extraction & retrieval).

Extracts durable behavioural patterns from completed episodes and
stores them as learnings that inform future interactions.

Learning kinds:
  preference  — "User prefers KPI analysis before prediction"
  pattern     — "Well X frequently triggers high-risk alerts"
  rule        — "Always check data quality before sigma analysis"
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from services.memory.store import MemoryStore

logger = logging.getLogger(__name__)


class Hippocampus:
    """Extract and retrieve learned patterns from episodes."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    # ── Write (manual) ─────────────────────────────────────────────────

    def record_learning(
        self,
        kind: str,
        text: str,
        source: str | None = None,
        confidence: float = 1.0,
    ) -> int:
        """Manually record a learning."""
        if kind not in ("preference", "pattern", "rule"):
            kind = "pattern"
        return self._store.save_learning(
            kind=kind, text=text, source=source, confidence=confidence,
        )

    # ── Write (LLM-assisted extraction) ────────────────────────────────

    def extract_learnings(
        self,
        episode: Dict[str, Any],
        *,
        llm_generate_json: Callable[..., Dict[str, Any]] | None = None,
    ) -> List[Dict[str, Any]]:
        """Use the LLM to extract learnings from a completed episode.

        Returns the list of learnings that were saved.
        Falls back to heuristic extraction if LLM is unavailable.
        """
        if llm_generate_json is not None:
            return self._extract_via_llm(episode, llm_generate_json)
        return self._extract_heuristic(episode)

    def _extract_via_llm(
        self,
        episode: Dict[str, Any],
        llm_generate_json: Callable[..., Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        prompt = f"""\
Analyse the following conversation and extract useful learnings.

CONVERSATION:
  Query: {episode.get('query', '')}
  Tools used: {json.dumps(episode.get('tools_used', []))}
  Answer: {(episode.get('final_answer', '') or '')[:500]}

Return ONLY a JSON array of learnings.  Each item:
  {{"kind": "preference|pattern|rule", "text": "<the learning>", "confidence": 0.0-1.0}}

If there are no useful learnings, return an empty array: []"""

        try:
            result = llm_generate_json(prompt, temperature=0.1, max_tokens=2048)
        except Exception:
            logger.exception("LLM extraction failed — falling back to heuristic")
            return self._extract_heuristic(episode)

        raw = result.get("response") if isinstance(result, dict) else result

        # Parse
        learnings_list: List[Dict[str, Any]] | None = None
        if isinstance(raw, list):
            learnings_list = raw
        elif isinstance(raw, str):
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    learnings_list = parsed
            except (json.JSONDecodeError, TypeError):
                pass

        if not learnings_list:
            return self._extract_heuristic(episode)

        saved: List[Dict[str, Any]] = []
        for item in learnings_list:
            if not isinstance(item, dict) or not item.get("text"):
                continue
            kind = item.get("kind", "pattern")
            if kind not in ("preference", "pattern", "rule"):
                kind = "pattern"
            row_id = self._store.save_learning(
                kind=kind,
                text=item["text"],
                source=str(episode.get("id", "")),
                confidence=min(max(float(item.get("confidence", 0.8)), 0.0), 1.0),
            )
            saved.append({"id": row_id, "kind": kind, "text": item["text"]})

        logger.info("Extracted %d learnings via LLM", len(saved))
        return saved

    def _extract_heuristic(self, episode: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simple heuristic extraction when LLM is unavailable."""
        saved: List[Dict[str, Any]] = []
        tools = episode.get("tools_used", [])

        # Record tool ordering preferences
        if len(tools) >= 2:
            ordering = " → ".join(tools)
            text = f"User query led to tool sequence: {ordering}"
            row_id = self._store.save_learning(
                kind="pattern",
                text=text,
                source=str(episode.get("id", "")),
                confidence=0.6,
            )
            saved.append({"id": row_id, "kind": "pattern", "text": text})

        return saved

    # ── Read ───────────────────────────────────────────────────────────

    def recall(
        self,
        query: str,
        *,
        kind: str | None = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find learnings relevant to *query*."""
        return self._store.search_learnings(query, kind=kind, limit=limit)

    def all_rules(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return all rule-type learnings (always-on context)."""
        return self._store.all_learnings(kind="rule", limit=limit)

    def all_preferences(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._store.all_learnings(kind="preference", limit=limit)

    # ── Formatting ─────────────────────────────────────────────────────

    def format_for_context(
        self,
        learnings: List[Dict[str, Any]],
        *,
        max_items: int = 10,
    ) -> str:
        """Format learnings as a text block for prompt injection."""
        if not learnings:
            return ""

        lines = ["LEARNED PATTERNS (apply when relevant):"]
        for item in learnings[:max_items]:
            kind_label = item.get("kind", "pattern").upper()
            lines.append(f"- [{kind_label}] {item['text']}")
        return "\n".join(lines)

    @property
    def count(self) -> int:
        return self._store.learning_count()
