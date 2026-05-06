"""
Sandbox — Package entry-point.

Importing this module registers the ``python_sandbox`` tool in the
TransIQ tool registry, making it callable via ``dispatch_tool()``::

    from services.sandbox import ScratchpadSession
    # or via the tool system:
    from services.tools import dispatch_tool
    result = dispatch_tool("python_sandbox", {"code": "print(1+1)"})

Public API re-exported for convenience.
"""
from __future__ import annotations

from services.sandbox.safety import validate_code, BLOCKED_MODULES   # noqa: F401
from services.sandbox.executor import execute_code                   # noqa: F401
from services.sandbox.scratchpad import ScratchpadSession            # noqa: F401

# ── Register python_sandbox tool ──────────────────────────────────────

from typing import Any, Dict
from services.tools.decorator import tool


@tool(
    name="python_sandbox",
    description=(
        "Execute Python code in a secure subprocess sandbox. "
        "Supports basic math, data manipulation, string operations, "
        "and print statements.  No file I/O, networking, or OS access."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute in the sandbox.",
            },
        },
        "required": ["code"],
    },
)
def handle_python_sandbox(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Stateless sandbox execution via the tool registry."""
    code = input_data["code"]

    # Validate first (fast fail)
    violations = validate_code(code)
    if violations:
        return {
            "output": "",
            "error": f"Code rejected: {'; '.join(violations)}",
            "execution_time_ms": 0,
            "variables": {},
        }

    return execute_code(code, timeout=5)
