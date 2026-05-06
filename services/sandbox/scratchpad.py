"""
Sandbox — Scratchpad Session.

Provides a persistent Python execution environment where state
(variables) carries over between calls::

    from services.sandbox.scratchpad import ScratchpadSession

    s = ScratchpadSession()
    r1 = s.execute("x = 42")
    r2 = s.execute("print(x * 2)")
    assert r2["output"].strip() == "84"

Each ``ScratchpadSession`` stores JSON-serialisable variables returned
by the subprocess and re-injects them into the next execution.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List


class ScratchpadSession:
    """Persistent scratchpad backed by subprocess execution.

    Parameters
    ----------
    session_id:
        Optional identifier.  Auto-generated if omitted.
    timeout:
        Default per-execution timeout in seconds.
    """

    def __init__(
        self,
        session_id: str | None = None,
        *,
        timeout: int = 5,
    ) -> None:
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.timeout = timeout
        self._state: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []

    # ── Execute ────────────────────────────────────────────────────────

    def execute(self, code: str) -> Dict[str, Any]:
        """Run *code* in the sandbox, carrying forward session state.

        Returns the standard executor result dict with keys:
        ``output``, ``error``, ``execution_time_ms``, ``variables``.
        """
        from services.sandbox.executor import execute_code

        result = execute_code(
            code,
            timeout=self.timeout,
            prior_state=self._state,
        )

        # Merge returned variables into persistent state
        new_vars = result.get("variables") or {}
        self._state.update(new_vars)

        self._history.append({
            "code": code,
            "result": result,
        })

        return result

    # ── Introspection ──────────────────────────────────────────────────

    @property
    def state(self) -> Dict[str, Any]:
        """Current session variables (copy)."""
        return dict(self._state)

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Ordered list of past executions."""
        return list(self._history)

    def reset(self) -> None:
        """Clear all state and history."""
        self._state.clear()
        self._history.clear()
