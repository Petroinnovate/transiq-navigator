"""
Tool Registry — Global store.

Maintains a module-level dictionary of ``ToolDef`` objects keyed by name.
Thread-safe for reads (tools are registered at import time, then read-only
during request handling).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from services.tools.schemas import ToolDef

logger = logging.getLogger(__name__)

# ── Global registry ────────────────────────────────────────────────────
_REGISTRY: Dict[str, ToolDef] = {}


def register_tool(tool_def: ToolDef) -> None:
    """Add a tool to the global registry.

    Raises ``ValueError`` if a tool with the same name already exists.
    """
    if tool_def.name in _REGISTRY:
        raise ValueError(f"Tool already registered: {tool_def.name!r}")
    _REGISTRY[tool_def.name] = tool_def
    logger.debug("Registered tool %r", tool_def.name)


def get_tool(name: str) -> Optional[ToolDef]:
    """Return a registered tool by name, or ``None``."""
    return _REGISTRY.get(name)


def list_tools() -> List[ToolDef]:
    """Return all registered tools (insertion-ordered)."""
    return list(_REGISTRY.values())


def tool_names() -> List[str]:
    """Return the names of all registered tools."""
    return list(_REGISTRY.keys())


def build_tool_schemas() -> List[Dict]:
    """Return JSON-serialisable schema list for LLM function-calling."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
        }
        for t in _REGISTRY.values()
    ]


def _reset() -> None:
    """Clear registry (for testing only)."""
    _REGISTRY.clear()
