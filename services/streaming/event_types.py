"""
Streaming Event Types — Structured event definitions for real-time updates.

All events follow the envelope::

    {"type": "<event_type>", "timestamp": "<ISO-8601>", "data": {...}}

Seven event types cover the full LLM + tool lifecycle:

  * ``llm_start`` / ``llm_token`` / ``llm_end``
  * ``tool_start`` / ``tool_progress`` / ``tool_end``
  * ``final_response``
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


# ── Constants ──────────────────────────────────────────────────────────
LLM_START = "llm_start"
LLM_TOKEN = "llm_token"
LLM_END = "llm_end"
TOOL_START = "tool_start"
TOOL_PROGRESS = "tool_progress"
TOOL_END = "tool_end"
FINAL_RESPONSE = "final_response"

ALL_EVENT_TYPES = frozenset(
    {LLM_START, LLM_TOKEN, LLM_END, TOOL_START, TOOL_PROGRESS, TOOL_END, FINAL_RESPONSE}
)


# ── Event dataclass ───────────────────────────────────────────────────

@dataclass(frozen=True)
class StreamEvent:
    """Immutable streaming event envelope."""

    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default="")

    def __post_init__(self) -> None:
        if not self.timestamp:
            # frozen=True: bypass with object.__setattr__
            object.__setattr__(
                self,
                "timestamp",
                datetime.now(timezone.utc).isoformat(),
            )

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "timestamp": self.timestamp, "data": self.data}


# ── Factory helpers ────────────────────────────────────────────────────

def llm_start_event(*, iteration: int = 1) -> StreamEvent:
    return StreamEvent(type=LLM_START, data={"iteration": iteration})


def llm_token_event(token: str, *, iteration: int = 1) -> StreamEvent:
    return StreamEvent(type=LLM_TOKEN, data={"token": token, "iteration": iteration})


def llm_end_event(*, iteration: int = 1, success: bool = True) -> StreamEvent:
    return StreamEvent(type=LLM_END, data={"iteration": iteration, "success": success})


def tool_start_event(tool_name: str, *, step: int = 0) -> StreamEvent:
    return StreamEvent(type=TOOL_START, data={"tool": tool_name, "step": step})


def tool_progress_event(
    tool_name: str, status: str, *, step: int = 0, detail: Optional[str] = None,
) -> StreamEvent:
    d: Dict[str, Any] = {"tool": tool_name, "status": status, "step": step}
    if detail is not None:
        d["detail"] = detail
    return StreamEvent(type=TOOL_PROGRESS, data=d)


def tool_end_event(
    tool_name: str, *, step: int = 0, success: bool = True,
) -> StreamEvent:
    return StreamEvent(
        type=TOOL_END,
        data={"tool": tool_name, "step": step, "success": success},
    )


def final_response_event(answer: str, *, tools_used: list[str] | None = None) -> StreamEvent:
    d: Dict[str, Any] = {"answer": answer}
    if tools_used:
        d["tools_used"] = tools_used
    return StreamEvent(type=FINAL_RESPONSE, data=d)
