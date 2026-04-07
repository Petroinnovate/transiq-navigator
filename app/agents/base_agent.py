"""
BaseAgent — Abstract base class for all TransIQ specialized agents.
Each agent receives a context dict, calls the LLM, and returns its structured output.
"""
from __future__ import annotations
import json
import re
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Every agent must implement:
      - `name`  – human-readable label used in logs
      - `build_prompt(ctx)` – returns the prompt string
      - `parse_output(raw)` – extracts and validates JSON from raw LLM text
    """

    def __init__(self, llm_client, model: str = "gemini-2.5-flash"):
        self.client = llm_client
        self.model = model

    # ── Subclass contract ──────────────────────────────────────────────
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def build_prompt(self, ctx: Dict[str, Any]) -> str: ...

    # ── Default JSON extractor (can be overridden) ─────────────────────
    def parse_output(self, raw: str) -> Dict[str, Any]:
        raw = raw.strip()
        # 1. Try direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # 2. Extract first {...} block
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        logger.warning(f"[{self.name}] Could not parse JSON from output. Returning empty dict.")
        return {}

    # ── Execution entry point ──────────────────────────────────────────
    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        from google.genai.types import GenerateContentConfig   # lazy import

        prompt = self.build_prompt(ctx)
        logger.info(f"[{self.name}] Calling LLM ({self.model}) …")

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=0.15,
                    max_output_tokens=8192,
                    system_instruction=self._system_instruction(),
                ),
            )
            raw = response.text or ""
        except Exception as exc:
            logger.error(f"[{self.name}] LLM call failed: {exc}")
            return self._fallback()

        result = self.parse_output(raw)
        logger.info(f"[{self.name}] Completed. Keys: {list(result.keys())}")
        return result

    # ── Override in subclasses for custom system instructions ──────────
    def _system_instruction(self) -> str:
        return (
            "You are TransIQ — an Industrial Decision Operating System. "
            "You produce DECISIONS not insights. Every output is traceable, financially quantified, "
            "and auditable. NEVER say 'insights suggest' or 'data indicates'. "
            "ALWAYS use 'Decision:', 'Action Required:', 'Risk:' prefixes. "
            "Apply Six Sigma rigor. Include financial impact ($ or %) on every decision. "
            "Ensure every claim is traceable to a data source. "
            "Respond ONLY in valid JSON. No markdown fences, no explanation text."
        )

    def _fallback(self) -> Dict[str, Any]:
        return {}
