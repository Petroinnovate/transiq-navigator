"""
Tool Registry — Package entry-point.

Importing this module registers the four built-in TransIQ tools:

  * ``six_sigma_analysis``
  * ``kpi_analysis``
  * ``predictive_forecast``
  * ``risk_analysis``

Public API re-exported here for convenience::

    from services.tools import dispatch_tool, list_tools, build_tool_schemas
"""
from __future__ import annotations

# Re-export public API so callers use ``from services.tools import ...``
from services.tools.schemas import ToolDef, ToolResult          # noqa: F401
from services.tools.registry import (                           # noqa: F401
    get_tool,
    list_tools,
    tool_names,
    build_tool_schemas,
)
from services.tools.dispatcher import (                         # noqa: F401
    dispatch_tool,
    make_call_counter,
    CallCounter,
    MAX_TOOL_CALLS_PER_REQUEST,
)
from services.tools.decorator import tool                       # noqa: F401

# ── Register built-in tools below ─────────────────────────────────────
# Each @tool wrapper delegates to the existing engine WITHOUT modifying it.

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. six_sigma_analysis
# ---------------------------------------------------------------------------
@tool(
    name="six_sigma_analysis",
    description=(
        "Run deterministic Six Sigma DMAIC analysis on a set of KPIs. "
        "Returns sigma level, Cp/Cpk, CTQs, root causes, and data quality."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "kpis": {
                "type": "array",
                "description": "List of enriched KPI dicts to analyse.",
            },
            "financial_threshold": {
                "type": "number",
                "description": "CTQ financial threshold (default 60).",
            },
            "risk_threshold": {
                "type": "number",
                "description": "CTQ risk threshold (default 60).",
            },
        },
        "required": ["kpis"],
    },
)
def handle_six_sigma(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from features.six_sigma import run_six_sigma

    return run_six_sigma(
        kpis=input_data["kpis"],
        financial_threshold=input_data.get("financial_threshold", 60),
        risk_threshold=input_data.get("risk_threshold", 60),
    )


# ---------------------------------------------------------------------------
# 2. kpi_analysis
# ---------------------------------------------------------------------------
@tool(
    name="kpi_analysis",
    description=(
        "Score and prioritise a KPI pool using the 5-factor weighted model. "
        "Returns enriched KPIs with priorityScore, visibility, and selectionReason."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "kpis": {
                "type": "array",
                "description": "Raw KPI dicts to score and rank.",
            },
        },
        "required": ["kpis"],
    },
)
def handle_kpi_analysis(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from features.kpi.kpi_engine import process_kpis

    enriched = process_kpis(kpis=input_data["kpis"])
    return {"kpis": enriched, "count": len(enriched)}


# ---------------------------------------------------------------------------
# 3. predictive_forecast
# ---------------------------------------------------------------------------
@tool(
    name="predictive_forecast",
    description=(
        "Forecast future values for a single KPI using an ensemble of models "
        "(Linear, ARIMA, Prophet, XGBoost). Requires at least 5 history points."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "kpi": {
                "type": "object",
                "description": (
                    "KPI dict with a 'history' key (list of floats). "
                    "Optional: name, title, unit, target."
                ),
            },
        },
        "required": ["kpi"],
    },
)
def handle_predictive_forecast(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from features.predictive.predictive_engine import forecast_kpi

    result = forecast_kpi(kpi=input_data["kpi"])
    if result is None:
        return {"forecast": None, "reason": "Insufficient history (min 5 points)"}
    return result


# ---------------------------------------------------------------------------
# 4. risk_analysis
# ---------------------------------------------------------------------------
@tool(
    name="risk_analysis",
    description=(
        "Detect risk level for a KPI given its forecast, and generate an "
        "executive-tone recommendation. Returns riskLevel, breachPredicted, "
        "timeToBreach, financialRisk, and decision text."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "kpi": {
                "type": "object",
                "description": (
                    "KPI dict with target, direction, and value fields."
                ),
            },
            "forecast_data": {
                "type": "object",
                "description": (
                    "ForecastResult from predictive_forecast (or null)."
                ),
            },
        },
        "required": ["kpi"],
    },
)
def handle_risk_analysis(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from features.risk.risk_engine import detect_risk, generate_decision

    kpi = input_data["kpi"]
    forecast_data = input_data.get("forecast_data")

    risk = detect_risk(kpi, forecast_data)
    decision = generate_decision(kpi, forecast_data, risk)

    return {
        "risk": risk,
        "decision": decision,
    }


logger.debug(
    "Built-in tools registered: %s",
    ", ".join(t.name for t in list_tools()),
)
