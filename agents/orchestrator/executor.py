"""
Agent Orchestrator — Executor.

Walks through a plan produced by the Planner, dispatching each step
via the Tool Registry.  Previous step outputs are accumulated and can
be referenced by later steps.

Usage::

    from agents.orchestrator.executor import execute_plan
    results = execute_plan(plan)
"""
from __future__ import annotations

import copy
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from services.tools import dispatch_tool, make_call_counter

logger = logging.getLogger(__name__)


# ── Reference resolution ───────────────────────────────────────────────

def _resolve_refs(
    tool_input: Dict[str, Any],
    previous_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Replace ``{"$ref": <index>}`` values with actual prior results.

    Only top-level values are checked.  If the referenced index is out of
    range or the referenced step failed, the value is left as-is.
    """
    resolved = copy.deepcopy(tool_input)
    for key, value in resolved.items():
        if isinstance(value, dict) and "$ref" in value:
            ref_idx = value["$ref"]
            if isinstance(ref_idx, int) and 0 <= ref_idx < len(previous_results):
                ref_result = previous_results[ref_idx]
                # Inject the successful result payload, or the raw dict
                if ref_result.get("status") == "success" and ref_result.get("result") is not None:
                    resolved[key] = ref_result["result"]
                else:
                    resolved[key] = ref_result
    return resolved


# ── Execution result per step ──────────────────────────────────────────

def _make_step_result(
    index: int,
    tool_name: str,
    tool_input: Dict[str, Any],
    dispatch_result: Dict[str, Any],
    reason: str = "",
) -> Dict[str, Any]:
    return {
        "step": index,
        "tool": tool_name,
        "input": tool_input,
        "reason": reason,
        "status": dispatch_result.get("status", "error"),
        "result": dispatch_result.get("result"),
        "error": dispatch_result.get("error"),
    }


# ── Public API ─────────────────────────────────────────────────────────

def execute_plan(
    plan: List[Dict[str, Any]],
    *,
    stop_on_failure: bool = True,
    streamer: Any | None = None,
) -> List[Dict[str, Any]]:
    """Execute a tool plan sequentially, passing context forward.

    Parameters
    ----------
    plan:
        Ordered list of ``{"tool": str, "input": dict, "reason": str}``
        as returned by ``create_plan()``.
    stop_on_failure:
        If ``True`` (default), halt execution after the first step that
        returns ``status == "error"``.
    streamer:
        Optional ``StreamingManager`` — emits ``tool_start`` /
        ``tool_end`` events for each plan step when provided.

    Returns
    -------
    List of per-step result dicts.  Each has:
    ``step, tool, input, reason, status, result, error``.
    """
    counter = make_call_counter()
    results: List[Dict[str, Any]] = []

    for idx, step in enumerate(plan):
        tool_name = step.get("tool", "")
        raw_input = step.get("input") or {}
        reason = step.get("reason", "")

        # Resolve $ref pointers to earlier results
        resolved_input = _resolve_refs(raw_input, results)

        logger.info(
            "Executor step %d/%d: %s",
            idx + 1, len(plan), tool_name,
        )

        if streamer:
            try:
                streamer.emit_tool_start(tool_name, step=idx)
            except Exception:
                pass

        dispatch_result = dispatch_tool(
            tool_name,
            resolved_input,
            counter=counter,
        )

        if streamer:
            _ok = dispatch_result.get("status") == "success"
            try:
                streamer.emit_tool_end(tool_name, step=idx, success=_ok)
            except Exception:
                pass

        step_result = _make_step_result(
            index=idx,
            tool_name=tool_name,
            tool_input=resolved_input,
            dispatch_result=dispatch_result,
            reason=reason,
        )
        results.append(step_result)

        # ── Stop on critical failure ───────────────────────────────────
        if stop_on_failure and step_result["status"] == "error":
            logger.warning(
                "Executor stopping at step %d due to error: %s",
                idx, step_result.get("error"),
            )
            break

    logger.info(
        "Executor finished: %d/%d steps completed",
        len(results), len(plan),
    )
    return results


# ── Parallel execution ─────────────────────────────────────────────────

def _find_parallel_groups(
    plan: List[Dict[str, Any]],
) -> List[List[int]]:
    """Partition plan indices into groups that can run in parallel.

    Steps that contain ``$ref`` to earlier steps must wait for those steps.
    Steps with no ``$ref`` (or only references to already-completed groups)
    can run concurrently.
    """
    groups: List[List[int]] = []
    completed: set[int] = set()

    remaining = list(range(len(plan)))

    while remaining:
        # Identify steps whose deps (if any) are all in `completed`
        runnable: List[int] = []
        for idx in remaining:
            raw_input = plan[idx].get("input") or {}
            deps = set()
            for v in raw_input.values():
                if isinstance(v, dict) and "$ref" in v:
                    ref = v["$ref"]
                    if isinstance(ref, int):
                        deps.add(ref)
            if deps <= completed:
                runnable.append(idx)

        if not runnable:
            # Avoid infinite loop — force remaining as sequential
            runnable = [remaining[0]]

        groups.append(runnable)
        completed.update(runnable)
        remaining = [i for i in remaining if i not in completed]

    return groups


def execute_plan_parallel(
    plan: List[Dict[str, Any]],
    *,
    stop_on_failure: bool = True,
    streamer: Any | None = None,
    max_workers: int = 4,
) -> List[Dict[str, Any]]:
    """Execute a tool plan with maximum parallelism where dependencies allow.

    Steps without ``$ref`` dependencies on each other run concurrently.
    Steps that reference earlier results wait for those to complete first.

    Parameters
    ----------
    plan:
        Same format as ``execute_plan``.
    stop_on_failure:
        Halt on first error (within or after a group).
    streamer:
        Optional ``StreamingManager``.
    max_workers:
        ThreadPool size for concurrent execution.

    Returns
    -------
    Ordered list of per-step result dicts (same structure as ``execute_plan``).
    """
    if not plan:
        return []

    groups = _find_parallel_groups(plan)
    counter = make_call_counter()
    results_by_idx: Dict[int, Dict[str, Any]] = {}
    failed = False

    for group in groups:
        if failed and stop_on_failure:
            break

        if len(group) == 1:
            # Single step — no threading overhead
            idx = group[0]
            step = plan[idx]
            result = _execute_single(
                idx, step, results_by_idx, counter, streamer,
            )
            results_by_idx[idx] = result
            if result["status"] == "error" and stop_on_failure:
                failed = True
        else:
            # Parallel group
            with ThreadPoolExecutor(max_workers=min(max_workers, len(group))) as pool:
                futures = {}
                for idx in group:
                    step = plan[idx]
                    fut = pool.submit(
                        _execute_single,
                        idx, step, results_by_idx, counter, streamer,
                    )
                    futures[fut] = idx

                for fut in as_completed(futures):
                    idx = futures[fut]
                    result = fut.result()
                    results_by_idx[idx] = result
                    if result["status"] == "error" and stop_on_failure:
                        failed = True

    # Return in plan order
    ordered = [results_by_idx[i] for i in sorted(results_by_idx)]
    logger.info(
        "Parallel executor finished: %d/%d steps completed",
        len(ordered), len(plan),
    )
    return ordered


def _execute_single(
    idx: int,
    step: Dict[str, Any],
    results_by_idx: Dict[int, Dict[str, Any]],
    counter: Any,
    streamer: Any | None,
) -> Dict[str, Any]:
    """Execute a single plan step (used by both sequential and parallel paths)."""
    tool_name = step.get("tool", "")
    raw_input = step.get("input") or {}
    reason = step.get("reason", "")

    # Build previous_results list for ref resolution
    previous_results = [
        results_by_idx.get(i, {}) for i in range(idx)
    ]
    resolved_input = _resolve_refs(raw_input, previous_results)

    logger.info("Executor step %d: %s", idx + 1, tool_name)

    if streamer:
        try:
            streamer.emit_tool_start(tool_name, step=idx)
        except Exception:
            pass

    dispatch_result = dispatch_tool(
        tool_name,
        resolved_input,
        counter=counter,
    )

    if streamer:
        _ok = dispatch_result.get("status") == "success"
        try:
            streamer.emit_tool_end(tool_name, step=idx, success=_ok)
        except Exception:
            pass

    return _make_step_result(
        index=idx,
        tool_name=tool_name,
        tool_input=resolved_input,
        dispatch_result=dispatch_result,
        reason=reason,
    )
