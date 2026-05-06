"""
Agent Orchestrator — Plan → Execute → Validate pipeline.

Ties together the Planner, Executor, and Validator into a single
``run_agent()`` call that returns a structured result compatible with
the Chat Orchestrator output format.

Usage::

    from agents.orchestrator import run_agent
    result = run_agent("Forecast ROP and assess risk", context={...})
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from agents.orchestrator.planner import create_plan
from agents.orchestrator.executor import execute_plan
from agents.orchestrator.validator import validate_results, summarise_results

logger = logging.getLogger(__name__)


def _generate_final_answer(
    query: str,
    summary: Dict[str, Any],
    llm_generate_json: Callable[..., Dict[str, Any]],
) -> str:
    """Ask the LLM to synthesise tool outputs into a human answer."""

    prompt = f"""\
You are TransIQ — an Industrial Decision Operating System.

The following tool results were collected for the user's query.
Synthesise them into a clear, actionable final answer.

RULES:
1. Respond with ONLY valid JSON: {{"answer": "<your final answer>"}}
2. Reference specific numbers from the tool outputs.
3. If some steps failed, acknowledge it and work with what succeeded.

USER QUERY: {query}

TOOL RESULTS:
{json.dumps(summary["outputs"], default=str)}

ERRORS (if any):
{json.dumps(summary["errors"], default=str)}"""

    try:
        llm_result = llm_generate_json(prompt, temperature=0.2, max_tokens=4096)
    except Exception:
        logger.exception("Final-answer LLM call failed")
        return _fallback_answer(summary)

    raw = llm_result.get("response") if isinstance(llm_result, dict) else llm_result

    if isinstance(raw, dict):
        return raw.get("answer", raw.get("response", str(raw)))
    if isinstance(raw, str):
        # Try to extract {"answer": "..."} from the string
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed.get("answer", parsed.get("response", raw))
        except (json.JSONDecodeError, TypeError):
            pass
        return raw

    return _fallback_answer(summary)


def _fallback_answer(summary: Dict[str, Any]) -> str:
    """Build a mechanical answer when the LLM is unavailable."""
    parts = [f"Completed {summary['steps_ok']}/{summary['steps_total']} analysis steps."]
    for out in summary["outputs"]:
        parts.append(f"- {out['tool']}: done")
    if summary["errors"]:
        parts.append(f"{summary['steps_failed']} step(s) had errors.")
    return " ".join(parts)


# ── Public API ─────────────────────────────────────────────────────────

def run_agent(
    query: str,
    context: Dict[str, Any] | None = None,
    *,
    llm_generate_json: Callable[..., Dict[str, Any]] | None = None,
    stop_on_failure: bool = True,
    streamer: Any | None = None,
) -> Dict[str, Any]:
    """Full Plan → Execute → Validate pipeline.

    Parameters
    ----------
    query:
        Natural-language user question.
    context:
        Supporting data (KPIs, doc metadata, etc.).
    llm_generate_json:
        LLM callable (defaults to ``LLMFactory.generate_json_with_fallback``).
    stop_on_failure:
        Halt execution on the first tool error.
    streamer:
        Optional ``StreamingManager`` — forwarded to the executor so
        ``tool_start`` / ``tool_end`` events are emitted per plan step.

    Returns
    -------
    ::

        {
            "query": str,
            "plan": [...],
            "steps": [...],
            "valid": bool,
            "final_answer": str,
            "tools_used": [str, ...],
        }
    """
    if context is None:
        context = {}

    if llm_generate_json is None:
        from services.llm.factory import LLMFactory
        llm_generate_json = LLMFactory.generate_json_with_fallback
    # ── Observability: start trace ─────────────────────────────────────
    trace = None
    _t0 = time.perf_counter()
    try:
        from services.observability import logger as obs_lg, metrics as obs_mt
        from services.observability.tracer import start_trace, end_trace
        trace = start_trace(query, component="agent_orchestrator")
        obs_lg.request(query, trace_id=trace.trace_id, component="agent_orchestrator")
        obs_mt.record_request("agent_orchestrator")
    except Exception:
        pass
    # ── 1. Plan ────────────────────────────────────────────────────────
    plan = create_plan(query, context, llm_generate_json=llm_generate_json)

    if not plan:
        # No tools needed — ask LLM for a direct answer
        direct = _generate_final_answer(
            query,
            {"ok": True, "steps_total": 0, "steps_ok": 0,
             "steps_failed": 0, "errors": [], "outputs": []},
            llm_generate_json,
        )
        return {
            "query": query,
            "plan": [],
            "steps": [],
            "valid": True,
            "final_answer": direct,
            "tools_used": [],
            "composed": None,
        }

    # ── 2. Execute ─────────────────────────────────────────────────────
    results = execute_plan(plan, stop_on_failure=stop_on_failure, streamer=streamer)

    # ── 3. Validate ────────────────────────────────────────────────────
    valid = validate_results(results)
    summary = summarise_results(results)

    # ── 3b. Compose structured response ────────────────────────────────
    composed: Dict[str, Any] | None = None
    if valid:
        try:
            from services.response.composer import compose_response

            composed = compose_response(
                query,
                results,
                llm_generate_json=llm_generate_json,
            )
        except Exception:
            logger.warning("Response composition failed", exc_info=True)

    # ── 4. Final answer ────────────────────────────────────────────────
    if valid:
        final_answer = _generate_final_answer(query, summary, llm_generate_json)
    else:
        final_answer = (
            "The analysis encountered errors in all steps and could not "
            "produce a reliable answer. Please check your input data."
        )

    # ── Collect tools used (de-duped, ordered) ─────────────────────────
    seen: set[str] = set()
    tools_used: List[str] = []
    for r in results:
        t = r.get("tool", "")
        if t and t not in seen:
            seen.add(t)
            tools_used.append(t)

    _result = {
        "query": query,
        "plan": plan,
        "steps": results,
        "valid": valid,
        "final_answer": final_answer,
        "tools_used": tools_used,
        "composed": composed,
    }

    # ── Observability: end trace + response log ────────────────────────
    _total_ms = (time.perf_counter() - _t0) * 1000
    try:
        obs_lg.response(trace_id=trace.trace_id if trace else "",
                        component="agent_orchestrator",
                        duration_ms=_total_ms,
                        tools_used=tools_used,
                        success=valid)
        obs_mt.record_latency("agent_orchestrator", _total_ms)
        if not valid:
            obs_mt.record_error("agent_orchestrator", "invalid_result")
        if trace:
            end_trace(trace.trace_id)
    except Exception:
        pass

    return _result
