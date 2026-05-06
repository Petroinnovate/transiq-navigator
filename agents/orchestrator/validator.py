"""
Agent Orchestrator — Validator.

Inspects the list of execution results and decides whether the run
succeeded, partially succeeded, or failed.

Usage::

    from agents.orchestrator.validator import validate_results
    ok = validate_results(results)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def validate_results(results: List[Dict[str, Any]]) -> bool:
    """Return ``True`` if the execution produced usable output.

    Checks:
      1. Results list is non-empty.
      2. At least one step succeeded.
      3. No step has a ``None`` result when its status is "success".
    """
    if not results:
        logger.warning("Validation failed: empty results list")
        return False

    successes = [r for r in results if r.get("status") == "success"]

    if not successes:
        logger.warning(
            "Validation failed: all %d step(s) errored — %s",
            len(results),
            [r.get("error") for r in results],
        )
        return False

    # Flag success steps that returned None (suspicious but not fatal)
    hollow = [r for r in successes if r.get("result") is None]
    if hollow:
        logger.warning(
            "Validation warning: %d success step(s) returned None result",
            len(hollow),
        )

    logger.info(
        "Validation passed: %d/%d step(s) succeeded",
        len(successes), len(results),
    )
    return True


def summarise_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a concise summary dict suitable for the final-answer LLM call.

    Returns
    -------
    ``{"ok": bool, "steps_total": int, "steps_ok": int,
       "steps_failed": int, "errors": list, "outputs": list}``
    """
    successes = [r for r in results if r.get("status") == "success"]
    failures = [r for r in results if r.get("status") != "success"]

    return {
        "ok": len(successes) > 0,
        "steps_total": len(results),
        "steps_ok": len(successes),
        "steps_failed": len(failures),
        "errors": [
            {"step": r.get("step"), "tool": r.get("tool"), "error": r.get("error")}
            for r in failures
        ],
        "outputs": [
            {"step": r.get("step"), "tool": r.get("tool"), "result": r.get("result")}
            for r in successes
        ],
    }
