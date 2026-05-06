"""
Chat Orchestrator — Data models.

Defines the structured types exchanged between the orchestrator,
the LLM, and the tool dispatcher.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── LLM decision ──────────────────────────────────────────────────────

@dataclass
class LLMDecision:
    """Parsed decision from the LLM's JSON response."""
    action: str                        # "tool_call" | "final_answer"
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    response: Optional[str] = None


# ── Per-step record ───────────────────────────────────────────────────

@dataclass
class ChatStep:
    """One step in the orchestrator loop (tool call or final answer)."""
    step: int
    action: str                        # "tool_call" | "final_answer"
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"step": self.step, "action": self.action}
        if self.tool_name is not None:
            d["tool_name"] = self.tool_name
        if self.tool_input is not None:
            d["tool_input"] = self.tool_input
        if self.tool_result is not None:
            d["tool_result"] = self.tool_result
        if self.response is not None:
            d["response"] = self.response
        return d


# ── Full chat response ────────────────────────────────────────────────

@dataclass
class ChatResponse:
    """Final structured output returned to the caller."""
    query: str
    steps: List[ChatStep] = field(default_factory=list)
    final_answer: str = ""
    tools_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "steps": [s.to_dict() for s in self.steps],
            "final_answer": self.final_answer,
            "tools_used": self.tools_used,
        }
