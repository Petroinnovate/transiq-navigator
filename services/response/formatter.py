"""
Response Formatter — Per-tool output → structured readable section.

Each ``format_*`` function accepts the raw engine result dict and returns
a section dict with ``insights`` and ``recommendations`` lists plus
tool-specific metrics.  The Composer merges these into the final envelope.

Functions never raise — if input is missing keys the formatter degrades
gracefully and returns whatever it can extract.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# ── Helpers ────────────────────────────────────────────────────────────

def _safe_get(d: Any, *keys: str, default: Any = None) -> Any:
    """Nested dict lookup that never raises."""
    curr = d
    for k in keys:
        if not isinstance(curr, dict):
            return default
        curr = curr.get(k, default)
    return curr


def _fmt_number(val: Any, decimals: int = 2) -> str:
    """Format a numeric value; pass through strings unchanged."""
    if isinstance(val, float):
        return f"{val:.{decimals}f}"
    if isinstance(val, int):
        return str(val)
    return str(val) if val is not None else "N/A"


# ===================================================================
# 1. KPI Analysis
# ===================================================================

def format_kpi(result: Dict[str, Any]) -> Dict[str, Any]:
    """Format output from ``kpi_analysis`` tool.

    Expected *result* shape::

        {"kpis": [{name, value, unit, priorityScore, visibility, selectionReason, ...}],
         "count": int}
    """
    kpis: list = result.get("kpis") or []
    count: int = result.get("count", len(kpis))

    top_kpis: List[Dict[str, Any]] = []
    insights: List[str] = []
    recommendations: List[str] = []

    for kpi in kpis[:10]:  # cap display at 10
        name = kpi.get("name") or kpi.get("title", "Unnamed KPI")
        entry: Dict[str, Any] = {
            "name": name,
            "value": kpi.get("value"),
            "unit": kpi.get("unit", ""),
            "priority_score": kpi.get("priorityScore"),
            "visibility": kpi.get("visibility", ""),
        }
        top_kpis.append(entry)

        reason = kpi.get("selectionReason")
        if reason:
            insights.append(f"{name}: {reason}")

    if count > 0:
        high = [k for k in kpis if (k.get("priorityScore") or 0) >= 80]
        if high:
            recommendations.append(
                f"Focus on {len(high)} high-priority KPI(s): "
                + ", ".join(k.get("name", "?") for k in high[:5])
                + "."
            )
        low_vis = [k for k in kpis if k.get("visibility") == "hidden"]
        if low_vis:
            insights.append(
                f"{len(low_vis)} KPI(s) flagged as hidden — review for relevance."
            )

    return {
        "count": count,
        "top_kpis": top_kpis,
        "insights": insights,
        "recommendations": recommendations,
    }


# ===================================================================
# 2. Six Sigma Analysis
# ===================================================================

def format_six_sigma(result: Dict[str, Any]) -> Dict[str, Any]:
    """Format output from ``six_sigma_analysis`` tool.

    Expected *result* shape::

        {"sigmaLevel": str, "processCapability": str, "dataQuality": {...},
         "rootCauses": [...], "ctq": [...], "capability": {...}, "dmaic": {...}}
    """
    insights: List[str] = []
    recommendations: List[str] = []

    sigma = result.get("sigmaLevel", "N/A")
    capability = result.get("processCapability", "N/A")
    dq = result.get("dataQuality") or {}
    dq_grade = dq.get("grade", "N/A")
    root_causes_raw = result.get("rootCauses") or []
    ctq_list = result.get("ctq") or []

    # ── Root causes ────────────────────────────────────────────────────
    root_causes: List[Dict[str, Any]] = []
    for rc in root_causes_raw[:10]:
        root_causes.append({
            "cause": rc.get("cause", "Unknown"),
            "severity": rc.get("severity", "unknown"),
            "confidence": rc.get("confidence"),
        })
        if rc.get("severity") in ("high", "critical"):
            recommendations.append(
                f"Address root cause: {rc.get('cause', 'Unknown')} "
                f"(severity: {rc.get('severity')})."
            )

    # ── Insights ───────────────────────────────────────────────────────
    insights.append(f"Process is operating at {sigma} sigma (capability: {capability}).")

    if dq_grade in ("D", "F"):
        insights.append(
            f"Data quality is rated {dq_grade} — results may be unreliable."
        )
        recommendations.append("Improve data quality before drawing conclusions.")

    if ctq_list:
        insights.append(f"{len(ctq_list)} Critical-to-Quality characteristics identified.")

    # DMAIC recommendations
    dmaic = result.get("dmaic") or {}
    improve = dmaic.get("improve") or {}
    for action in (improve.get("recommendedActions") or [])[:3]:
        recommendations.append(action)

    return {
        "sigma_level": sigma,
        "process_capability": capability,
        "data_quality_grade": dq_grade,
        "root_causes": root_causes,
        "ctq_count": len(ctq_list),
        "insights": insights,
        "recommendations": recommendations,
    }


# ===================================================================
# 3. Predictive Forecast
# ===================================================================

def format_predictive(result: Dict[str, Any]) -> Dict[str, Any]:
    """Format output from ``predictive_forecast`` tool.

    Expected *result* shape (success)::

        {"forecast": [float, ...], "trend": str, "slope": float,
         "models": {...}, "modelsUsed": [str], "modelScores": {...},
         "forecastSteps": int, "historyLength": int}

    Or insufficient-data::

        {"forecast": None, "reason": str}
    """
    insights: List[str] = []
    recommendations: List[str] = []

    forecast = result.get("forecast")

    # ── Insufficient data path ─────────────────────────────────────────
    if forecast is None:
        reason = result.get("reason", "No forecast available")
        return {
            "trend": "unknown",
            "slope": 0.0,
            "forecast_steps": 0,
            "models_used": [],
            "forecast": [],
            "insights": [reason],
            "recommendations": ["Collect more historical data (minimum 5 points)."],
        }

    trend = result.get("trend", "unknown")
    slope = result.get("slope", 0.0)
    models_used = result.get("modelsUsed") or []
    steps = result.get("forecastSteps", len(forecast))

    insights.append(
        f"Forecast trend is {trend} (slope {_fmt_number(slope, 4)}) "
        f"over {steps} period(s)."
    )
    insights.append(f"Ensemble built from {len(models_used)} model(s): {', '.join(models_used)}.")

    if trend == "down":
        recommendations.append(
            "KPI is trending downward — investigate contributing factors."
        )
    elif trend == "up":
        recommendations.append(
            "Positive trend detected — verify sustainability of current drivers."
        )

    return {
        "trend": trend,
        "slope": slope,
        "forecast_steps": steps,
        "models_used": models_used,
        "forecast": forecast,
        "insights": insights,
        "recommendations": recommendations,
    }


# ===================================================================
# 4. Risk Analysis
# ===================================================================

def format_risk(result: Dict[str, Any]) -> Dict[str, Any]:
    """Format output from ``risk_analysis`` tool.

    Expected *result* shape::

        {"risk": {"riskLevel": str, "breachPredicted": bool,
                  "timeToBreach": int|None, "financialRisk": float|None},
         "decision": str}
    """
    risk = result.get("risk") or {}
    decision = result.get("decision", "")

    risk_level = risk.get("riskLevel", "unknown")
    breach = risk.get("breachPredicted", False)
    ttb = risk.get("timeToBreach")
    fin = risk.get("financialRisk")

    insights: List[str] = []
    recommendations: List[str] = []

    insights.append(f"Risk level: {risk_level}.")
    if breach:
        ttb_str = f" in {ttb} period(s)" if ttb is not None else ""
        insights.append(f"Target breach predicted{ttb_str}.")
    if fin is not None:
        insights.append(f"Estimated financial exposure: ${_fmt_number(fin, 0)}.")

    if decision:
        recommendations.append(decision)

    if risk_level in ("high", "critical"):
        recommendations.append("Escalate to management for immediate review.")

    return {
        "risk_level": risk_level,
        "breach_predicted": breach,
        "time_to_breach": ttb,
        "financial_risk": fin,
        "decision": decision,
        "insights": insights,
        "recommendations": recommendations,
    }


# ── Dispatcher ─────────────────────────────────────────────────────────

_FORMATTERS: Dict[str, Any] = {
    "kpi_analysis": format_kpi,
    "six_sigma_analysis": format_six_sigma,
    "predictive_forecast": format_predictive,
    "risk_analysis": format_risk,
}


def format_tool_result(tool_name: str, result: Dict[str, Any]) -> Dict[str, Any] | None:
    """Route *result* to the correct formatter, or return ``None`` for unknown tools."""
    fn = _FORMATTERS.get(tool_name)
    if fn is None:
        return None
    try:
        return fn(result)
    except Exception:
        return None
