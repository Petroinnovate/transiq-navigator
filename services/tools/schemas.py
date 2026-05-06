"""
Tool Registry — Data models.

Defines the ToolDef dataclass (name, description, input_schema, handler)
and the structured ToolResult returned by every dispatch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass(frozen=True)
class ToolDef:
    """Immutable definition of a registered tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Any]


@dataclass
class ToolResult:
    """Structured output from tool dispatch."""
    tool: str
    status: str                        # "success" | "error"
    result: Optional[Dict[str, Any]] = field(default=None)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"tool": self.tool, "status": self.status}
        if self.result is not None:
            d["result"] = self.result
        if self.error is not None:
            d["error"] = self.error
        return d
