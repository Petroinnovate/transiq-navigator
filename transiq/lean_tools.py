"""
Lean Tools — OEE, Takt time, cycle time, waste identification, Kaizen.

Covers ASQ Handbook Chapters 20, 23: Lean Enterprise, Lean Tools.

Functions
---------
calculate_oee          Overall Equipment Effectiveness
takt_time             Takt time calculation
cycle_time_analysis   Cycle time with value-add vs non-value-add
calculate_throughput  First-pass yield and rolled throughput yield
identify_waste        Categorise waste into 8 Lean waste types (DOWNTIME)
kaizen_event          Structure a Kaizen improvement event
value_stream_metrics  Lead time, process time, %VA
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from transiq.utils import validate_positive


def calculate_oee(
    availability: float,
    performance: float,
    quality: float,
) -> Dict[str, float]:
    """
    Overall Equipment Effectiveness.

    OEE = Availability × Performance × Quality

    All inputs are fractions (0–1) or percentages (0–100).
    If any input > 1, it's treated as a percentage and converted.

    Parameters
    ----------
    availability : Actual run time / Planned production time
    performance : (Ideal cycle time × Total pieces) / Run time
    quality : Good pieces / Total pieces

    Returns
    -------
    dict with availability, performance, quality (all as %), OEE %, rating
    """
    # Normalise to fraction
    a = availability / 100.0 if availability > 1.0 else availability
    p = performance / 100.0 if performance > 1.0 else performance
    q = quality / 100.0 if quality > 1.0 else quality

    for name, val in [("availability", a), ("performance", p), ("quality", q)]:
        if val < 0 or val > 1:
            raise ValueError(f"{name} must be 0–1 (or 0–100%), got {val}")

    oee = a * p * q

    # World-class benchmarks
    if oee >= 0.85:
        rating = "World Class"
    elif oee >= 0.65:
        rating = "Good"
    elif oee >= 0.40:
        rating = "Needs Improvement"
    else:
        rating = "Poor"

    return {
        "availability_pct": round(a * 100, 2),
        "performance_pct": round(p * 100, 2),
        "quality_pct": round(q * 100, 2),
        "OEE_pct": round(oee * 100, 2),
        "OEE_fraction": round(oee, 4),
        "rating": rating,
    }


def takt_time(
    available_time: float,
    demand: float,
    time_unit: str = "minutes",
) -> Dict[str, float]:
    """
    Takt Time = Available production time / Customer demand.

    Parameters
    ----------
    available_time : total available time in the given unit
    demand : number of units demanded in that period
    time_unit : label ("minutes", "seconds", "hours")
    """
    validate_positive(demand, "demand")
    tt = available_time / demand

    return {
        "takt_time": round(tt, 4),
        "time_unit": time_unit,
        "available_time": available_time,
        "demand": demand,
    }


def cycle_time_analysis(
    steps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Analyse cycle time with value-add (VA) vs non-value-add (NVA) breakdown.

    Parameters
    ----------
    steps : list of dicts with:
        - "name": step name
        - "time": duration
        - "type": "VA" | "NVA" | "BNVA" (business-NVA)

    Returns
    -------
    dict with total_time, va_time, nva_time, bnva_time, pct_va, pct_nva
    """
    total = sum(s["time"] for s in steps)
    va = sum(s["time"] for s in steps if s.get("type", "").upper() == "VA")
    nva = sum(s["time"] for s in steps if s.get("type", "").upper() == "NVA")
    bnva = sum(s["time"] for s in steps if s.get("type", "").upper() == "BNVA")

    return {
        "total_time": round(total, 4),
        "va_time": round(va, 4),
        "nva_time": round(nva, 4),
        "bnva_time": round(bnva, 4),
        "pct_va": round(va / total * 100, 2) if total > 0 else 0.0,
        "pct_nva": round(nva / total * 100, 2) if total > 0 else 0.0,
        "pct_bnva": round(bnva / total * 100, 2) if total > 0 else 0.0,
        "n_steps": len(steps),
    }


def calculate_throughput(
    stage_yields: List[float],
) -> Dict[str, float]:
    """
    First-pass yield (FPY) and Rolled Throughput Yield (RTY).

    FPY = fraction good at each stage (no rework)
    RTY = product of all stage FPYs

    Parameters
    ----------
    stage_yields : list of yields per stage, each in (0, 1]
    """
    rty = 1.0
    for y in stage_yields:
        if y <= 0 or y > 1:
            raise ValueError(f"Each stage yield must be in (0, 1], got {y}")
        rty *= y

    return {
        "stage_yields": [round(y, 6) for y in stage_yields],
        "RTY": round(rty, 6),
        "RTY_pct": round(rty * 100, 4),
        "DPMO_equivalent": round((1 - rty) * 1_000_000, 1),
        "n_stages": len(stage_yields),
    }


# 8 wastes of Lean (DOWNTIME mnemonic)
_WASTE_CATEGORIES = {
    "D": "Defects",
    "O": "Overproduction",
    "W": "Waiting",
    "N": "Non-utilized talent",
    "T": "Transportation",
    "I": "Inventory",
    "M": "Motion",
    "E": "Extra-processing",
}


def identify_waste(
    observations: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Classify waste observations into 8 Lean waste categories (DOWNTIME).

    Parameters
    ----------
    observations : list of dicts with:
        - "description": text description
        - "category": one of D/O/W/N/T/I/M/E

    Returns
    -------
    dict with category counts, details, and Pareto ordering
    """
    counts: Dict[str, int] = {k: 0 for k in _WASTE_CATEGORIES}
    details: Dict[str, List[str]] = {k: [] for k in _WASTE_CATEGORIES}

    for obs in observations:
        cat = obs.get("category", "").upper()
        if cat in _WASTE_CATEGORIES:
            counts[cat] += 1
            details[cat].append(obs.get("description", ""))

    total = sum(counts.values())
    pareto = sorted(counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "counts": {_WASTE_CATEGORIES[k]: v for k, v in counts.items()},
        "pareto_order": [{"waste": _WASTE_CATEGORIES[k], "count": v, "pct": round(v / total * 100, 1) if total > 0 else 0.0} for k, v in pareto],
        "total_observations": total,
        "details": {_WASTE_CATEGORIES[k]: v for k, v in details.items()},
    }


def kaizen_event(
    problem: str,
    current_state: Dict[str, Any],
    target_state: Dict[str, Any],
    team: List[str],
    duration_days: int = 5,
) -> Dict[str, Any]:
    """
    Structure a Kaizen (rapid improvement) event.

    Returns
    -------
    dict with event charter, gap analysis, and action template
    """
    gap = {}
    for key in current_state:
        if key in target_state:
            try:
                gap[key] = {
                    "current": current_state[key],
                    "target": target_state[key],
                    "gap": round(float(target_state[key]) - float(current_state[key]), 4),
                }
            except (TypeError, ValueError):
                gap[key] = {
                    "current": current_state[key],
                    "target": target_state[key],
                    "gap": "N/A",
                }

    return {
        "problem_statement": problem,
        "current_state": current_state,
        "target_state": target_state,
        "gap_analysis": gap,
        "team": team,
        "duration_days": duration_days,
        "phases": [
            {"day": 1, "activity": "Define scope and problem statement"},
            {"day": 2, "activity": "Map current state and collect data"},
            {"day": 3, "activity": "Analyse root causes"},
            {"day": 4, "activity": "Implement improvements"},
            {"day": 5, "activity": "Verify results and standardise"},
        ],
    }


def value_stream_metrics(
    process_time: float,
    lead_time: float,
) -> Dict[str, float]:
    """
    Value stream efficiency metrics.

    PCE = Process Cycle Efficiency = Process Time / Lead Time
    """
    if lead_time <= 0:
        raise ValueError("lead_time must be positive")

    pce = process_time / lead_time

    return {
        "process_time": round(process_time, 4),
        "lead_time": round(lead_time, 4),
        "pce": round(pce, 4),
        "pce_pct": round(pce * 100, 2),
        "wait_time": round(lead_time - process_time, 4),
        "rating": "Lean" if pce >= 0.25 else "Typical" if pce >= 0.05 else "Poor",
    }
