"""
Failure Mode and Effects Analysis (FMEA).

Risk Priority Number (RPN) = Severity × Occurrence × Detection.

Used in the Improve/Control phases of DMAIC to prioritise failure modes
for corrective action.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def compute_rpn(
    severity: int,
    occurrence: int,
    detection: int,
) -> Dict[str, int]:
    """
    Compute Risk Priority Number.

    RPN = Severity × Occurrence × Detection

    All inputs are 1–10 scale.
    RPN range: 1–1000.

    Parameters
    ----------
    severity   : 1 (no effect) to 10 (hazardous, no warning)
    occurrence : 1 (remote) to 10 (almost certain)
    detection  : 1 (certain detection) to 10 (no detection possible)
    """
    for name, val in [("severity", severity), ("occurrence", occurrence), ("detection", detection)]:
        if not 1 <= val <= 10:
            raise ValueError(f"{name} must be 1–10 (got {val})")

    rpn = severity * occurrence * detection

    # Risk level
    if rpn >= 200:
        risk_level = "High"
    elif rpn >= 80:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "severity": severity,
        "occurrence": occurrence,
        "detection": detection,
        "RPN": rpn,
        "risk_level": risk_level,
    }


def fmea_analysis(
    failure_modes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Perform FMEA analysis on a list of failure modes.

    Parameters
    ----------
    failure_modes : list of dicts with:
        - "mode": failure mode description
        - "effect": effect of failure
        - "cause": potential cause
        - "severity": 1–10
        - "occurrence": 1–10
        - "detection": 1–10
        - "current_controls": (optional) existing controls
        - "recommended_action": (optional) action to reduce risk

    Returns
    -------
    dict with: ranked failure modes (by RPN descending), summary statistics,
    high/medium/low counts.
    """
    results: List[Dict[str, Any]] = []

    for fm in failure_modes:
        rpn_result = compute_rpn(fm["severity"], fm["occurrence"], fm["detection"])
        results.append({
            "mode": fm.get("mode", ""),
            "effect": fm.get("effect", ""),
            "cause": fm.get("cause", ""),
            "current_controls": fm.get("current_controls", ""),
            "recommended_action": fm.get("recommended_action", ""),
            **rpn_result,
        })

    # Sort by RPN descending
    results.sort(key=lambda x: x["RPN"], reverse=True)

    high = sum(1 for r in results if r["risk_level"] == "High")
    medium = sum(1 for r in results if r["risk_level"] == "Medium")
    low = sum(1 for r in results if r["risk_level"] == "Low")
    rpn_values = [r["RPN"] for r in results]

    return {
        "failure_modes": results,
        "summary": {
            "total": len(results),
            "high_risk": high,
            "medium_risk": medium,
            "low_risk": low,
            "max_rpn": max(rpn_values) if rpn_values else 0,
            "avg_rpn": round(sum(rpn_values) / len(rpn_values), 1) if rpn_values else 0,
        },
    }


def sort_failure_modes(
    failure_modes: List[Dict[str, Any]],
    sort_by: str = "RPN",
) -> List[Dict[str, Any]]:
    """Sort failure modes by RPN (or severity, occurrence, detection)."""
    valid_keys = {"RPN", "severity", "occurrence", "detection"}
    if sort_by not in valid_keys:
        raise ValueError(f"sort_by must be one of {valid_keys}")
    return sorted(failure_modes, key=lambda x: x.get(sort_by, 0), reverse=True)
