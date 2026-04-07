"""
Drilling Analytics Engine — Oil & Gas Domain Module
====================================================

Extracts and computes key drilling KPIs:
  - NPT (Non-Productive Time) analysis and cost
  - ROP (Rate of Penetration) optimization
  - MTBF/MTTR equipment reliability
  - Well cost performance vs AFE
  - Mud system and torque/drag metrics

All calculations are deterministic — no LLM dependency.

Key functions:
  extract_drilling_kpis(kpis)       → filter drilling-specific KPIs from pool
  compute_npt_analysis(kpis)        → NPT metrics, costs, top causes
  compute_rop_metrics(kpis)         → ROP performance and optimization potential
  compute_reliability_metrics(kpis) → MTBF, MTTR, availability scores
  build_drilling_view(kpis, config) → full drilling analytics view
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Domain keyword patterns
# ---------------------------------------------------------------------------

_NPT_PATTERN = re.compile(
    r"\b(npt|non.?productive|downtime|stuck.?pipe|blowout|wellbore|kick|lost.?circ)\b",
    re.IGNORECASE,
)
_ROP_PATTERN = re.compile(
    r"\b(rop|rate.?of.?penetration|drilling.?speed|footage|bit|wob|weight.?on.?bit|rpm)\b",
    re.IGNORECASE,
)
_RELIABILITY_PATTERN = re.compile(
    r"\b(mtbf|mttr|mean.?time|failure|breakdown|availability|uptime|equipment|pump|"
    r"motor|bha|bottom.?hole|mud.?motor|rig)\b",
    re.IGNORECASE,
)
_COST_PATTERN = re.compile(
    r"\b(afe|cost.?per.?foot|well.?cost|opex|day.?rate|drilling.?cost|budget)\b",
    re.IGNORECASE,
)
_MUD_PATTERN = re.compile(
    r"\b(mud|rheology|viscosity|gel|fluid|density|ecd|equivalent.?circ)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Default config (all overridable)
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = {
    "cost_per_npt_hour": 15_000.0,      # $/hour of NPT (rig rate + services)
    "cost_per_foot_benchmark": 450.0,    # $/ft benchmark ROP cost
    "revenue_per_bbl": 70.0,            # $/bbl oil price
    "mtbf_target_hours": 500.0,          # Target MTBF in hrs
    "availability_target_pct": 95.0,    # Target rig availability %
    "rop_improvement_pct": 0.15,        # 15% ROP improvement potential
}


# ---------------------------------------------------------------------------
# KPI extraction
# ---------------------------------------------------------------------------

def extract_drilling_kpis(kpis: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
    """
    Classify KPIs into drilling sub-domains.
    Returns dict with keys: npt, rop, reliability, cost, mud, other_drilling
    """
    result: Dict[str, List[Dict]] = {
        "npt": [], "rop": [], "reliability": [], "cost": [], "mud": [], "other": []
    }

    for kpi in kpis:
        text = " ".join([
            str(kpi.get("title") or ""),
            str(kpi.get("description") or ""),
            str(kpi.get("unit") or ""),
        ])
        category = (kpi.get("category") or "").lower()

        if _NPT_PATTERN.search(text) or "npt" in category:
            result["npt"].append(kpi)
        elif _ROP_PATTERN.search(text) or "rop" in category:
            result["rop"].append(kpi)
        elif _RELIABILITY_PATTERN.search(text) or "reliability" in category:
            result["reliability"].append(kpi)
        elif _COST_PATTERN.search(text) or "cost" in category:
            result["cost"].append(kpi)
        elif _MUD_PATTERN.search(text):
            result["mud"].append(kpi)
        else:
            # Check if it's drilling-related at all
            if re.search(r"\b(well|drill|bore|formation|pore|casing|cementing|completion)\b", text, re.I):
                result["other"].append(kpi)

    return result


# ---------------------------------------------------------------------------
# NPT Analysis
# ---------------------------------------------------------------------------

def compute_npt_analysis(
    kpis: List[Dict[str, Any]],
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Compute NPT cost, % of total time, and top causes.
    """
    cfg = {**_DEFAULT_CONFIG, **(config or {})}
    cost_per_hour = cfg["cost_per_npt_hour"]

    npt_kpis = [k for k in kpis if _NPT_PATTERN.search(
        f"{k.get('title','')} {k.get('description','')}"
    )]

    total_npt_hours = 0.0
    total_npt_pct = 0.0
    cause_breakdown: List[Dict] = []

    for kpi in npt_kpis:
        val = kpi.get("value")
        unit = (kpi.get("unit") or "").lower()

        try:
            v = float(val)
        except (TypeError, ValueError):
            continue

        if "%" in unit or "pct" in unit or "percent" in unit:
            total_npt_pct += v
            # Assume % of 24hr day for a well drilling context
            hours_equiv = v / 100.0 * 24.0
            total_npt_hours += hours_equiv
        elif "hr" in unit or "hour" in unit:
            total_npt_hours += v
        else:
            # Treat as hours if unit is unclear
            total_npt_hours += v

        cause_breakdown.append({
            "cause": kpi.get("title", "Unknown"),
            "hours": round(
                v if ("hr" in unit or "hour" in unit) else v / 100.0 * 24.0, 2
            ),
            "cost_usd": round(
                (v if ("hr" in unit or "hour" in unit) else v / 100.0 * 24.0) * cost_per_hour, 2
            ),
        })

    total_npt_cost = round(total_npt_hours * cost_per_hour, 2)
    cause_breakdown.sort(key=lambda x: x["cost_usd"], reverse=True)

    return {
        "total_npt_hours": round(total_npt_hours, 2),
        "total_npt_pct": round(total_npt_pct, 2),
        "total_npt_cost_usd": total_npt_cost,
        "cost_per_hour_used": cost_per_hour,
        "top_causes": cause_breakdown[:5],
        "npt_kpi_count": len(npt_kpis),
    }


# ---------------------------------------------------------------------------
# ROP Analysis
# ---------------------------------------------------------------------------

def compute_rop_metrics(
    kpis: List[Dict[str, Any]],
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Compute ROP performance vs benchmark and optimization potential.
    """
    cfg = {**_DEFAULT_CONFIG, **(config or {})}

    rop_kpis = [k for k in kpis if _ROP_PATTERN.search(
        f"{k.get('title','')} {k.get('description','')}"
    )]

    actual_rops: List[float] = []
    target_rops: List[float] = []

    for kpi in rop_kpis:
        val = kpi.get("value")
        tgt = kpi.get("target")
        try:
            actual_rops.append(float(val))
        except (TypeError, ValueError):
            pass
        try:
            target_rops.append(float(tgt))
        except (TypeError, ValueError):
            pass

    if not actual_rops:
        return {
            "average_rop": None,
            "target_rop": None,
            "gap_pct": None,
            "optimization_potential_usd": None,
            "rop_kpi_count": len(rop_kpis),
        }

    avg_rop = sum(actual_rops) / len(actual_rops)
    avg_target = sum(target_rops) / len(target_rops) if target_rops else None

    gap_pct = None
    opt_potential = None
    if avg_target and avg_target > 0:
        gap_pct = round((avg_target - avg_rop) / avg_target * 100, 1)
        # If behind target, there's optimization potential
        if avg_rop < avg_target:
            improvement = avg_target * cfg["rop_improvement_pct"]
            # $ saving = (improved time / current time - 1) * day_rate equivalent
            opt_potential = round(improvement * cfg["cost_per_foot_benchmark"] * 100, 2)

    return {
        "average_rop_ft_hr": round(avg_rop, 2),
        "target_rop_ft_hr": round(avg_target, 2) if avg_target else None,
        "gap_pct": gap_pct,
        "optimization_potential_usd": opt_potential,
        "rop_kpi_count": len(rop_kpis),
    }


# ---------------------------------------------------------------------------
# Reliability Metrics
# ---------------------------------------------------------------------------

def compute_reliability_metrics(kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute MTBF, MTTR, and availability from reliability KPIs.
    """
    rel_kpis = [k for k in kpis if _RELIABILITY_PATTERN.search(
        f"{k.get('title','')} {k.get('description','')}"
    )]

    mtbf_values: List[float] = []
    mttr_values: List[float] = []
    availability_values: List[float] = []

    for kpi in rel_kpis:
        title = (kpi.get("title") or "").lower()
        val = kpi.get("value")
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue

        if "mtbf" in title:
            mtbf_values.append(v)
        elif "mttr" in title:
            mttr_values.append(v)
        elif any(x in title for x in ["availability", "uptime"]):
            availability_values.append(v)

    avg_mtbf = round(sum(mtbf_values) / len(mtbf_values), 1) if mtbf_values else None
    avg_mttr = round(sum(mttr_values) / len(mttr_values), 1) if mttr_values else None
    avg_avail = round(sum(availability_values) / len(availability_values), 1) if availability_values else None

    # Compute availability from MTBF/MTTR if not directly available
    if avg_avail is None and avg_mtbf and avg_mttr and avg_mttr > 0:
        avg_avail = round(avg_mtbf / (avg_mtbf + avg_mttr) * 100, 1)

    target_avail = _DEFAULT_CONFIG["availability_target_pct"]
    availability_gap = round(target_avail - avg_avail, 1) if avg_avail is not None else None

    return {
        "average_mtbf_hours": avg_mtbf,
        "average_mttr_hours": avg_mttr,
        "average_availability_pct": avg_avail,
        "target_availability_pct": target_avail,
        "availability_gap_pct": availability_gap,
        "reliability_kpi_count": len(rel_kpis),
    }


# ---------------------------------------------------------------------------
# Full drilling view
# ---------------------------------------------------------------------------

def build_drilling_view(
    kpis: List[Dict[str, Any]],
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Build complete drilling analytics view from KPI pool.
    Returns self-contained drilling section for the frontend.
    """
    classified = extract_drilling_kpis(kpis)
    npt = compute_npt_analysis(kpis, config)
    rop = compute_rop_metrics(kpis, config)
    reliability = compute_reliability_metrics(kpis)

    total_drilling_kpis = sum(len(v) for v in classified.values())

    score = 50  # Default neutral
    reasons: List[str] = []

    # Adjust score based on findings
    if npt["total_npt_pct"] and npt["total_npt_pct"] > 15:
        score -= 20
        reasons.append(f"NPT at {npt['total_npt_pct']:.1f}% — above 15% threshold")
    elif npt["total_npt_pct"] and npt["total_npt_pct"] < 5:
        score += 20

    if reliability["availability_gap_pct"] is not None:
        if reliability["availability_gap_pct"] > 5:
            score -= 15
            reasons.append(f"Availability gap {reliability['availability_gap_pct']:.1f}%")
        elif reliability["availability_gap_pct"] <= 0:
            score += 15

    if rop["gap_pct"] is not None:
        if rop["gap_pct"] > 20:
            score -= 10
            reasons.append(f"ROP is {rop['gap_pct']:.1f}% below target")

    score = max(0, min(100, score))

    return {
        "performance_score": score,
        "performance_notes": reasons,
        "npt_analysis": npt,
        "rop_metrics": rop,
        "reliability_metrics": reliability,
        "kpi_classification": {k: len(v) for k, v in classified.items()},
        "total_drilling_kpis": total_drilling_kpis,
        "classified_kpis": classified,
    }
