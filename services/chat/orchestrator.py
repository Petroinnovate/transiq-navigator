"""
Chat Orchestrator — Core loop.

Accepts a user query, asks the LLM to decide which tool(s) to call,
executes them via the Tool Registry, and loops until the LLM emits a
``final_answer`` or the iteration limit is reached.

Usage::

    from services.chat.orchestrator import handle_chat
    result = handle_chat("What is the sigma level for these KPIs?", context={...})
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from services.tools import build_tool_schemas, dispatch_tool, make_call_counter
from services.chat.schemas import ChatResponse, ChatStep, LLMDecision

logger = logging.getLogger(__name__)

# Late-imported at first use to avoid circular-import issues
_obs_loaded = False


def _obs():  # noqa: ANN202
    """Lazy accessor for the observability sub-modules."""
    global _obs_loaded
    if not _obs_loaded:
        try:
            import services.observability.logger as _lg
            import services.observability.tracer as _tr
            import services.observability.metrics as _mt
            _obs.lg = _lg  # type: ignore[attr-defined]
            _obs.tr = _tr  # type: ignore[attr-defined]
            _obs.mt = _mt  # type: ignore[attr-defined]
        except Exception:
            _obs.lg = _obs.tr = _obs.mt = None  # type: ignore[attr-defined]
        _obs_loaded = True
    return _obs  # type: ignore[return-value]

# ── Safety limits ──────────────────────────────────────────────────────
MAX_ITERATIONS = 5


# ── System prompt builder ─────────────────────────────────────────────

def _build_system_prompt(tools_schema: List[Dict[str, Any]]) -> str:
    """Build the system prompt that instructs the LLM how to use tools."""

    tool_list = "\n".join(
        f"  - {t['name']}: {t['description']}"
        for t in tools_schema
    )

    return f"""\
You are TransIQ — an Industrial Decision Operating System.

You have access to the following tools:
{tool_list}

RULES:
1. Decide whether you need to call a tool or can answer directly.
2. Respond with ONLY valid JSON — no markdown, no explanation.
3. To call a tool, respond:
   {{"action": "tool_call", "tool_name": "<name>", "tool_input": {{...}}}}
4. To give a final answer, respond:
   {{"action": "final_answer", "response": "<your answer>"}}
5. After receiving a tool result you may call another tool or give a final answer.
6. Never invent tool names. Only use the tools listed above.
7. If no tool is needed, go directly to final_answer."""


def _build_user_message(
    query: str,
    context: Dict[str, Any],
    tool_history: List[Dict[str, Any]],
    memory_text: str = "",
) -> str:
    """Assemble the user message including context and prior tool results."""

    parts: List[str] = []

    # Inject memory context (episodes + learnings)
    if memory_text:
        parts.append(memory_text)
        parts.append("")

    # Inject caller-supplied context (KPIs, doc data, etc.)
    if context:
        parts.append("CONTEXT:")
        parts.append(json.dumps(context, default=str))
        parts.append("")

    # Append prior tool results so the LLM can reason over them
    if tool_history:
        parts.append("PREVIOUS TOOL RESULTS:")
        for entry in tool_history:
            parts.append(json.dumps(entry, default=str))
        parts.append("")

    parts.append(f"USER QUERY: {query}")
    return "\n".join(parts)


# ── JSON parsing with fallback ────────────────────────────────────────

def _parse_llm_json(raw: str) -> Optional[Dict[str, Any]]:
    """Best-effort extraction of a JSON object from the LLM response."""
    raw = raw.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    # Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Fallback: first {...} block
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _to_decision(parsed: Dict[str, Any]) -> LLMDecision:
    """Convert a parsed dict to an LLMDecision, applying defaults."""
    action = parsed.get("action", "final_answer")
    if action not in ("tool_call", "final_answer"):
        action = "final_answer"

    return LLMDecision(
        action=action,
        tool_name=parsed.get("tool_name"),
        tool_input=parsed.get("tool_input") or {},
        response=parsed.get("response"),
    )


# ── Main orchestrator ─────────────────────────────────────────────────

def handle_chat(
    query: str,
    context: Dict[str, Any] | None = None,
    *,
    llm_generate_json: Any | None = None,
    memory: Any | None = None,
    streamer: Any | None = None,
) -> Dict[str, Any]:
    """Run the chat orchestration loop.

    Parameters
    ----------
    query:
        Natural-language user question.
    context:
        Arbitrary dict of supporting data (KPIs, doc metadata, etc.).
    llm_generate_json:
        Callable ``(prompt: str) -> Dict[str, Any]`` that returns
        the LLM factory's structured result dict.  Defaults to
        ``LLMFactory.generate_json_with_fallback``.
    memory:
        Optional ``Cortex`` instance.  When provided, past episodes and
        learnings are injected into the prompt, and the completed
        conversation is stored as an episode.
    streamer:
        Optional ``StreamingManager`` instance.  When provided, real-time
        events are emitted for LLM calls, tool execution, and the final
        response.  Falls back to normal (non-streaming) behaviour when
        ``None``.

    Returns
    -------
    dict matching ChatResponse.to_dict().
    """
    if context is None:
        context = {}

    # Lazy-import so the module can be tested without a live LLM config
    if llm_generate_json is None:
        from services.llm.factory import LLMFactory
        llm_generate_json = LLMFactory.generate_json_with_fallback

    # ── Observability: start trace ─────────────────────────────────────
    _o = _obs()
    trace = None
    _t0 = time.perf_counter()
    try:
        if _o.tr:
            trace = _o.tr.start_trace(query, component="chat_orchestrator")
        if _o.lg:
            _o.lg.request(query, trace_id=trace.trace_id if trace else "",
                          component="chat_orchestrator")
        if _o.mt:
            _o.mt.record_request("chat_orchestrator")
    except Exception:
        pass

    tools_schema = build_tool_schemas()
    system_prompt = _build_system_prompt(tools_schema)
    tool_counter = make_call_counter()

    # ── Memory context injection ───────────────────────────────────────
    memory_text = ""
    if memory is not None:
        try:
            mem_ctx = memory.get_context(query)
            memory_text = mem_ctx.get("memory_text", "")
        except Exception:
            logger.warning("Memory context retrieval failed", exc_info=True)

    chat_response = ChatResponse(query=query)
    tool_history: List[Dict[str, Any]] = []

    for iteration in range(1, MAX_ITERATIONS + 1):
        # ── Build prompt ───────────────────────────────────────────────
        user_msg = _build_user_message(query, context, tool_history, memory_text)
        full_prompt = f"{system_prompt}\n\n{user_msg}"

        # ── Call LLM ───────────────────────────────────────────────────
        if streamer:
            try:
                streamer.emit_llm_start(iteration=iteration)
            except Exception:
                logger.debug("Streamer llm_start failed", exc_info=True)

        _llm_t0 = time.perf_counter()
        try:
            llm_result = llm_generate_json(full_prompt, temperature=0.15, max_tokens=4096)
        except Exception as _llm_exc:
            _llm_ms = (time.perf_counter() - _llm_t0) * 1000
            logger.exception("LLM call failed at iteration %d", iteration)
            try:
                if _o.lg:
                    _o.lg.capture_exception("chat_orchestrator.llm", _llm_exc,
                                            trace_id=trace.trace_id if trace else "")
                if _o.mt:
                    _o.mt.record_latency("llm", _llm_ms)
                    _o.mt.record_error("chat_orchestrator", "llm_failure")
                if trace:
                    trace.add_llm_call(status="error", duration_ms=_llm_ms, iteration=iteration)
            except Exception:
                pass
            if streamer:
                try:
                    streamer.emit_llm_end(iteration=iteration, success=False)
                except Exception:
                    pass
            chat_response.final_answer = "I'm unable to process your request right now."
            break

        _llm_ms = (time.perf_counter() - _llm_t0) * 1000
        try:
            if _o.lg:
                _o.lg.llm_call(status="success", duration_ms=_llm_ms,
                               iteration=iteration,
                               trace_id=trace.trace_id if trace else "")
            if _o.mt:
                _o.mt.record_latency("llm", _llm_ms)
            if trace:
                trace.add_llm_call(status="success", duration_ms=_llm_ms, iteration=iteration)
        except Exception:
            pass

        if streamer:
            try:
                streamer.emit_llm_end(iteration=iteration, success=True)
            except Exception:
                logger.debug("Streamer llm_end failed", exc_info=True)

        # Extract the actual response dict from the factory envelope
        raw_response = llm_result.get("response") if isinstance(llm_result, dict) else llm_result

        # If the factory returned an error (all providers failed)
        if isinstance(llm_result, dict) and llm_result.get("error") and not raw_response:
            logger.error("All LLM providers failed: %s", llm_result["error"])
            chat_response.final_answer = "I'm unable to process your request right now."
            break

        # Parse the LLM JSON into a decision
        if isinstance(raw_response, dict):
            parsed = raw_response
        elif isinstance(raw_response, str):
            parsed = _parse_llm_json(raw_response)
        else:
            parsed = None

        if parsed is None:
            logger.warning("Unparseable LLM response at iteration %d", iteration)
            chat_response.final_answer = "I'm unable to interpret the analysis result."
            break

        decision = _to_decision(parsed)

        # ── final_answer ───────────────────────────────────────────────
        if decision.action == "final_answer":
            step = ChatStep(
                step=iteration,
                action="final_answer",
                response=decision.response or "",
            )
            chat_response.steps.append(step)
            chat_response.final_answer = decision.response or ""
            break

        # ── tool_call ──────────────────────────────────────────────────
        _tool = decision.tool_name or ""
        if streamer:
            try:
                streamer.emit_tool_start(_tool, step=iteration)
            except Exception:
                logger.debug("Streamer tool_start failed", exc_info=True)

        _tool_t0 = time.perf_counter()
        tool_result = dispatch_tool(
            _tool,
            decision.tool_input or {},
            counter=tool_counter,
        )
        _tool_ms = (time.perf_counter() - _tool_t0) * 1000

        # ── Observability: tool call ───────────────────────────────────
        _tool_ok = tool_result.get("status") == "success"
        try:
            if _o.lg:
                _o.lg.tool_call(_tool, status=tool_result.get("status", "unknown"),
                                duration_ms=_tool_ms, step=iteration,
                                trace_id=trace.trace_id if trace else "")
            if _o.mt:
                _o.mt.record_latency(f"tool.{_tool}", _tool_ms)
                _o.mt.record_tool_usage(_tool)
                if not _tool_ok:
                    _o.mt.record_error("tool_dispatcher", _tool)
            if trace:
                trace.add_step(_tool, status=tool_result.get("status", "unknown"),
                               duration_ms=_tool_ms, step=iteration)
        except Exception:
            pass

        if streamer:
            try:
                streamer.emit_tool_end(_tool, step=iteration, success=_tool_ok)
            except Exception:
                logger.debug("Streamer tool_end failed", exc_info=True)

        step = ChatStep(
            step=iteration,
            action="tool_call",
            tool_name=decision.tool_name,
            tool_input=decision.tool_input,
            tool_result=tool_result,
        )
        chat_response.steps.append(step)

        if decision.tool_name:
            chat_response.tools_used.append(decision.tool_name)

        # Track for the next iteration's prompt
        tool_history.append({
            "tool": decision.tool_name,
            "input": decision.tool_input,
            "result": tool_result,
        })

    else:
        # Exhausted MAX_ITERATIONS without a final_answer
        chat_response.final_answer = (
            "I reached the maximum number of analysis steps. "
            "Here is what I found so far — please refine your question."
        )

    # De-duplicate tools_used while preserving order
    seen: set[str] = set()
    unique: List[str] = []
    for t in chat_response.tools_used:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    chat_response.tools_used = unique

    result = chat_response.to_dict()

    # ── Observability: end trace + response log ────────────────────────
    _total_ms = (time.perf_counter() - _t0) * 1000
    try:
        if _o.lg:
            _o.lg.response(trace_id=trace.trace_id if trace else "",
                           component="chat_orchestrator",
                           duration_ms=_total_ms,
                           tools_used=chat_response.tools_used,
                           success=bool(chat_response.final_answer))
        if _o.mt:
            _o.mt.record_latency("chat_orchestrator", _total_ms)
        if trace:
            _o.tr.end_trace(trace.trace_id)
    except Exception:
        pass

    # ── Streaming: emit final response ──────────────────────────────────
    if streamer:
        try:
            streamer.emit_final_response(
                chat_response.final_answer or "",
                tools_used=chat_response.tools_used,
            )
        except Exception:
            logger.debug("Streamer final_response failed", exc_info=True)

    # ── Memory: store episode + extract learnings ──────────────────────
    if memory is not None:
        try:
            memory.store_episode(result)
            memory.learn(result, llm_generate_json=llm_generate_json)
        except Exception:
            logger.warning("Memory storage failed", exc_info=True)

    return result
