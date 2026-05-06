"""
Tool Registry — Decorator.

Provides the ``@tool`` decorator that registers a handler into the
global registry at import time.

Usage::

    @tool(
        name="six_sigma_analysis",
        description="Run deterministic Six Sigma DMAIC analysis.",
        input_schema={
            "type": "object",
            "properties": { ... },
            "required": [...]
        },
    )
    def handle_six_sigma(input: dict) -> dict:
        ...
"""
from __future__ import annotations

from typing import Any, Callable, Dict

from services.tools.schemas import ToolDef
from services.tools.registry import register_tool


def tool(
    name: str,
    description: str,
    input_schema: Dict[str, Any],
) -> Callable:
    """Decorator that registers a function as a dispatchable tool."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        tool_def = ToolDef(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=fn,
        )
        register_tool(tool_def)
        return fn

    return decorator
