"""
Agent Orchestrator — Planner.

Uses the LLM to decompose a user query into an ordered list of tool
steps *before* any execution starts.  This is the "think first, act
second" layer that sits above the reactive chat loop.

Usage::

    from agents.orchestrator.planner import create_plan
    plan = create_plan("Forecast ROP and assess risk", context={...})
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from services.tools import build_tool_schemas, tool_names

logger = logging.getLogger(__name__)

# ── Safety limit ───────────────────────────────────────────────────────
MAX_PLAN_STEPS = 5


# ── Prompt ─────────────────────────────────────────────────────────────

def _build_planner_prompt(
    query: str,
    context: Dict[str, Any],
    tools_schema: List[Dict[str, Any]],
) -> str:
    tool_list = "\n".join(
        f"  - {t['name']}: {t['description']}\n"
        f"    input_schema: {json.dumps(t['input_schema'])}"
        for t in tools_schema
    )

    ctx_block = ""
    if context:
        ctx_block = f"\nCONTEXT:\n{json.dumps(context, default=str)}\n"

    return f"""\
You are TransIQ Planner — an Industrial Decision Operating System.

Your job is to create an execution plan for the given query.
You must decide which tools to call and in what order.

AVAILABLE TOOLS:
{tool_list}

RULES:
1. Return ONLY a JSON array of steps. No markdown, no explanation.
2. Each step is an object: {{"tool": "<tool_name>", "input": {{...}}, "reason": "<why>"}}
3. Maximum {MAX_PLAN_STEPS} steps.
4. Order matters: later steps may depend on earlier results.
5. Use ONLY tools from the list above. Never invent tool names.
6. If the query can be answered without any tools, return an empty array: []
7. Use the input_schema to build correct input for each tool.
8. If a step needs the output of a previous step, set its input to
   {{"$ref": "<step_index>"}} for that field — the executor will resolve it.
{ctx_block}
USER QUERY: {query}"""


# ── JSON parsing ───────────────────────────────────────────────────────

def _parse_plan_json(raw: str) -> Optional[List[Dict[str, Any]]]:
    """Extract a JSON array from the LLM response."""
    raw = raw.strip()

    # Strip markdown fences
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    # Direct array parse
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # Fallback: first [...] block
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(0))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


# ── Validation ─────────────────────────────────────────────────────────

def _sanitize_plan(raw_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop invalid steps, enforce max length, validate tool names."""
    valid_names = set(tool_names())
    sanitized: List[Dict[str, Any]] = []

    for step in raw_plan:
        if not isinstance(step, dict):
            continue
        name = step.get("tool")
        if not name or name not in valid_names:
            logger.warning("Planner produced unknown tool %r — skipping", name)
            continue
        sanitized.append({
            "tool": name,
            "input": step.get("input") or {},
            "reason": step.get("reason", ""),
        })
        if len(sanitized) >= MAX_PLAN_STEPS:
            break

    return sanitized


# ── Public API ─────────────────────────────────────────────────────────

def create_plan(
    query: str,
    context: Dict[str, Any] | None = None,
    *,
    llm_generate_json: Callable[..., Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """Ask the LLM to produce an ordered tool execution plan.

    Parameters
    ----------
    query:
        Natural-language user question.
    context:
        Caller-supplied data (KPIs, doc metadata, etc.).
    llm_generate_json:
        Callable returning the LLM factory envelope.  Defaults to
        ``LLMFactory.generate_json_with_fallback``.

    Returns
    -------
    List of ``{"tool": str, "input": dict, "reason": str}`` dicts.
    Empty list when the LLM decides no tools are needed or planning fails.
    """
    if context is None:
        context = {}

    if llm_generate_json is None:
        from services.llm.factory import LLMFactory
        llm_generate_json = LLMFactory.generate_json_with_fallback

    tools_schema = build_tool_schemas()
    prompt = _build_planner_prompt(query, context, tools_schema)

    # ── Call LLM ───────────────────────────────────────────────────────
    try:
        llm_result = llm_generate_json(prompt, temperature=0.15, max_tokens=4096)
    except Exception:
        logger.exception("Planner LLM call failed")
        return []

    raw_response = llm_result.get("response") if isinstance(llm_result, dict) else llm_result

    # All providers failed
    if isinstance(llm_result, dict) and llm_result.get("error") and not raw_response:
        logger.error("All LLM providers failed during planning: %s", llm_result["error"])
        return []

    # Parse
    if isinstance(raw_response, list):
        raw_plan = raw_response
    elif isinstance(raw_response, str):
        raw_plan = _parse_plan_json(raw_response)
    elif isinstance(raw_response, dict):
        # Some providers may wrap the array: {"steps": [...]}
        raw_plan = raw_response.get("steps") or raw_response.get("plan")
        if not isinstance(raw_plan, list):
            raw_plan = None
    else:
        raw_plan = None

    if raw_plan is None:
        logger.warning("Planner returned unparseable response")
        return []

    plan = _sanitize_plan(raw_plan)
    logger.info("Plan created: %d steps — %s", len(plan), [s["tool"] for s in plan])
    return plan
