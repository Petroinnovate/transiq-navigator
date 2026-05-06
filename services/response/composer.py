"""
Response Composer — Merges tool results into a single structured response.

``compose_response()`` accepts the user query and a list of tool-step
results (as produced by the Agent Orchestrator or Chat Orchestrator) and
returns a canonical response dict::

    {
        "summary":          str,
        "insights":         [str, ...],
        "metrics":          {tool_name: {...}, ...},
        "recommendations":  [str, ...],
    }

An optional ``llm_generate_json`` callable can be passed to produce a
natural-language summary.  When absent (or when the LLM fails), a
deterministic fallback summary is generated.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from services.response.templates import empty_response
from services.response.formatter import format_tool_result

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────

def _extract_steps(tool_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalise input — handles both Agent-style and Chat-style step dicts.

    Agent steps have ``{"tool": str, "status": str, "result": ...}``.
    Chat steps have ``{"tool_name": str, "tool_result": {"status": ..., "result": ...}}``.
    This returns a uniform list of ``(tool_name, result_dict)`` pairs.
    """
    steps: List[Dict[str, Any]] = []
    for s in tool_results:
        # Agent Orchestrator shape
        if "tool" in s and "result" in s:
            if s.get("status") == "success" and s["result"] is not None:
                steps.append({"tool": s["tool"], "result": s["result"]})
            continue

        # Chat Orchestrator shape
        tool_name = s.get("tool_name")
        tr = s.get("tool_result")
        if isinstance(tr, dict) and tr.get("status") == "success" and tr.get("result") is not None:
            steps.append({"tool": tool_name, "result": tr["result"]})

    return steps


def _deduplicate_strings(items: List[str]) -> List[str]:
    """Remove exact duplicates while preserving order."""
    seen: set[str] = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _fallback_summary(
    query: str,
    formatted: Dict[str, Dict[str, Any]],
) -> str:
    """Build a mechanical summary when the LLM is unavailable."""
    parts = [f"Analysis for: {query}"]

    tool_labels = {
        "kpi_analysis": "KPI Analysis",
        "six_sigma_analysis": "Six Sigma Analysis",
        "predictive_forecast": "Predictive Forecast",
        "risk_analysis": "Risk Assessment",
    }

    for tool, section in formatted.items():
        label = tool_labels.get(tool, tool)
        # Pick one headline stat per tool
        if tool == "kpi_analysis":
            parts.append(f"{label}: {section.get('count', 0)} KPI(s) evaluated.")
        elif tool == "six_sigma_analysis":
            parts.append(
                f"{label}: sigma level {section.get('sigma_level', 'N/A')}, "
                f"data quality {section.get('data_quality_grade', 'N/A')}."
            )
        elif tool == "predictive_forecast":
            parts.append(
                f"{label}: trend {section.get('trend', 'unknown')}, "
                f"{section.get('forecast_steps', 0)} period(s) forecast."
            )
        elif tool == "risk_analysis":
            parts.append(
                f"{label}: risk level {section.get('risk_level', 'unknown')}."
            )
        else:
            parts.append(f"{label}: completed.")

    return " ".join(parts)


def _llm_summary(
    query: str,
    formatted: Dict[str, Dict[str, Any]],
    insights: List[str],
    recommendations: List[str],
    llm_generate_json: Callable[..., Dict[str, Any]],
) -> str:
    """Ask the LLM to synthesise a natural-language summary."""

    prompt = f"""\
You are TransIQ — an Industrial Decision Operating System.

The following structured analysis results were produced for the user's query.
Write a clear, concise executive summary (2-4 sentences) that:
  1. States the key finding.
  2. Highlights the most critical insight.
  3. Ends with the top recommendation.

Respond with ONLY valid JSON: {{"summary": "<your summary>"}}

USER QUERY: {query}

METRICS:
{json.dumps(formatted, default=str)}

KEY INSIGHTS:
{json.dumps(insights[:10], default=str)}

RECOMMENDATIONS:
{json.dumps(recommendations[:10], default=str)}"""

    try:
        llm_result = llm_generate_json(prompt, temperature=0.2, max_tokens=1024)
    except Exception:
        logger.warning("LLM summary call failed", exc_info=True)
        return ""

    raw = llm_result.get("response") if isinstance(llm_result, dict) else llm_result

    if isinstance(raw, dict):
        return raw.get("summary", raw.get("response", ""))
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed.get("summary", parsed.get("response", raw))
        except (json.JSONDecodeError, TypeError):
            pass
        return raw

    return ""


# ── Public API ─────────────────────────────────────────────────────────

def compose_response(
    query: str,
    tool_results: List[Dict[str, Any]],
    *,
    llm_generate_json: Callable[..., Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Merge tool outputs into a unified structured response.

    Parameters
    ----------
    query:
        Original user query.
    tool_results:
        List of step-result dicts as produced by Agent or Chat Orchestrator.
    llm_generate_json:
        Optional LLM callable for natural-language summarisation.

    Returns
    -------
    Canonical response dict with ``summary``, ``insights``, ``metrics``,
    ``recommendations``.
    """
    response = empty_response()

    # ── 1. Extract successful results ──────────────────────────────────
    steps = _extract_steps(tool_results)

    if not steps:
        response["summary"] = f"No tool results available for: {query}"
        return response

    # ── 2. Format each tool's output ───────────────────────────────────
    formatted: Dict[str, Dict[str, Any]] = {}
    all_insights: List[str] = []
    all_recommendations: List[str] = []

    for step in steps:
        tool_name = step["tool"]
        section = format_tool_result(tool_name, step["result"])
        if section is None:
            # Unknown tool — store raw result under metrics
            formatted[tool_name] = step["result"]
            continue

        formatted[tool_name] = section

        all_insights.extend(section.pop("insights", []))
        all_recommendations.extend(section.pop("recommendations", []))

    # ── 3. De-duplicate ────────────────────────────────────────────────
    all_insights = _deduplicate_strings(all_insights)
    all_recommendations = _deduplicate_strings(all_recommendations)

    # ── 4. Summary ─────────────────────────────────────────────────────
    summary = ""
    if llm_generate_json is not None:
        summary = _llm_summary(
            query, formatted, all_insights, all_recommendations, llm_generate_json,
        )

    if not summary:
        summary = _fallback_summary(query, formatted)

    # ── 5. Confidence score ──────────────────────────────────────────
    confidence = _compute_confidence(steps, formatted)

    # ── 6. Explainability ──────────────────────────────────────────
    explanation = _build_explanation(steps, formatted)

    # ── 7. Assemble ────────────────────────────────────────────────────
    response["summary"] = summary
    response["insights"] = all_insights
    response["metrics"] = formatted
    response["recommendations"] = all_recommendations
    response["confidence"] = confidence
    response["explanation"] = explanation

    return response


# ── Confidence scoring ──────────────────────────────────────────────────

def _compute_confidence(
    steps: List[Dict[str, Any]],
    formatted: Dict[str, Dict[str, Any]],
) -> float:
    """Compute a 0.0–1.0 confidence score based on data quality + coverage.

    Factors:
      * Tool coverage: how many of the 4 engines contributed
      * Data quality: grade from Six Sigma MSA (if available)
      * Model agreement: forecast model count (if available)
    """
    scores: List[float] = []

    # Factor 1 — Tool coverage (more tools = more confidence)
    tool_count = len(steps)
    coverage = min(tool_count / 4.0, 1.0)  # Max at 4 tools
    scores.append(coverage)

    # Factor 2 — Data quality from Six Sigma (if present)
    sigma = formatted.get("six_sigma_analysis", {})
    dq_score = sigma.get("data_quality_score")
    if isinstance(dq_score, (int, float)):
        scores.append(min(dq_score / 100.0, 1.0))

    dq_grade = sigma.get("data_quality_grade", "")
    if dq_grade and not isinstance(dq_score, (int, float)):
        grade_map = {"A": 0.95, "B": 0.80, "C": 0.65, "D": 0.45, "F": 0.20}
        scores.append(grade_map.get(dq_grade.upper(), 0.5))

    # Factor 3 — Forecast model agreement (more models = more confidence)
    pred = formatted.get("predictive_forecast", {})
    models_count = pred.get("models_used_count")
    if isinstance(models_count, (int, float)) and models_count > 0:
        scores.append(min(models_count / 4.0, 1.0))

    if not scores:
        return 0.5  # Default when no data

    return round(sum(scores) / len(scores), 2)


# ── Explainability ──────────────────────────────────────────────────────

def _build_explanation(
    steps: List[Dict[str, Any]],
    formatted: Dict[str, Dict[str, Any]],
) -> str:
    """Generate a human-readable explanation of how conclusions were reached.

    This gives industrial users traceability into the analysis process.
    """
    parts: List[str] = []

    parts.append(
        f"This conclusion is based on {len(steps)} analysis step(s):"
    )

    for step in steps:
        tool = step["tool"]
        if tool == "kpi_analysis":
            count = formatted.get("kpi_analysis", {}).get("count", "?")
            parts.append(f"- KPI scoring evaluated {count} metric(s)")
        elif tool == "six_sigma_analysis":
            sigma = formatted.get("six_sigma_analysis", {})
            level = sigma.get("sigma_level", "N/A")
            grade = sigma.get("data_quality_grade", "N/A")
            parts.append(
                f"- Six Sigma DMAIC analysis yielded sigma level {level} "
                f"with data quality grade {grade}"
            )
        elif tool == "predictive_forecast":
            pred = formatted.get("predictive_forecast", {})
            trend = pred.get("trend", "unknown")
            models = pred.get("models_used_count", 0)
            parts.append(
                f"- Predictive forecast (trend: {trend}) used {models} model(s)"
            )
        elif tool == "risk_analysis":
            risk = formatted.get("risk_analysis", {})
            level = risk.get("risk_level", "unknown")
            parts.append(f"- Risk assessment classified as {level}")
        else:
            parts.append(f"- {tool} completed")

    return " ".join(parts)
