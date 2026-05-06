"""
Response Templates — Defines the canonical output envelope and section schemas.

Every composed response follows the ``RESPONSE_TEMPLATE`` shape::

    {
        "summary":          str,
        "insights":         [str, ...],
        "metrics":          {tool_name: {...}, ...},
        "recommendations":  [str, ...],
    }

Section-level templates (``KPI_SECTION``, ``SIGMA_SECTION``, etc.) describe
the keys each formatter should produce.  They are *documentation*, not
runtime enforcers — formatters populate what is available from the raw
engine output.
"""
from __future__ import annotations

from typing import Any, Dict, List


# ── Canonical response envelope ────────────────────────────────────────

RESPONSE_TEMPLATE: Dict[str, Any] = {
    "summary": "",
    "insights": [],
    "metrics": {},
    "recommendations": [],
    "confidence": 0.0,
    "explanation": "",
}


def empty_response() -> Dict[str, Any]:
    """Return a fresh copy of the canonical response envelope."""
    return {
        "summary": "",
        "insights": [],
        "metrics": {},
        "recommendations": [],
        "confidence": 0.0,
        "explanation": "",
    }


# ── Per-tool section templates ─────────────────────────────────────────
# Describe the shape each formatter returns.  Actual values are filled
# by the corresponding ``format_*`` function in ``formatter.py``.

KPI_SECTION: Dict[str, Any] = {
    "count": 0,
    "top_kpis": [],          # [{name, value, unit, priority_score, visibility}, ...]
    "insights": [],
    "recommendations": [],
}

SIGMA_SECTION: Dict[str, Any] = {
    "sigma_level": "",
    "process_capability": "",
    "data_quality_grade": "",
    "root_causes": [],       # [{cause, severity, confidence}, ...]
    "ctq_count": 0,
    "insights": [],
    "recommendations": [],
}

PREDICTIVE_SECTION: Dict[str, Any] = {
    "trend": "",
    "slope": 0.0,
    "forecast_steps": 0,
    "models_used": [],
    "forecast": [],
    "insights": [],
    "recommendations": [],
}

RISK_SECTION: Dict[str, Any] = {
    "risk_level": "",
    "breach_predicted": False,
    "time_to_breach": None,
    "financial_risk": None,
    "decision": "",
    "insights": [],
    "recommendations": [],
}

# Map tool names → section template (for reference / iteration)
SECTION_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "kpi_analysis": KPI_SECTION,
    "six_sigma_analysis": SIGMA_SECTION,
    "predictive_forecast": PREDICTIVE_SECTION,
    "risk_analysis": RISK_SECTION,
}
