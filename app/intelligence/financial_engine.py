"""
Financial Engine — Deterministic Financial Impact Calculator
=============================================================

Performs all financial calculations IN PYTHON — not LLM-dependent.
This eliminates hallucinated financial numbers and makes every $ figure
traceable, reproducible, and auditable.

Key functions:
  compute_deviation_score(kpi)       → 0-100 urgency score based on target gap
  compute_financial_impact(kpi)      → $ impact estimate from KPI deviation
  compute_kpi_financial_scores(kpis) → enrich all KPIs with deterministic scores
  compute_recommendation_roi(rec, kpis) → ROI estimate for a recommendation
  compute_portfolio_summary(kpis)    → aggregate financial view of all KPIs
"""
from __future__ import annotations

import logging
import os
import json
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain financial multipliers — configurable hierarchy:
#   well-level override  →  field-level override  →  global defaults
#
# Override via environment:
#   FINANCIAL_CATEGORY_OVERRIDES = '{"drilling": {"npt": 120000}}'
#   FINANCIAL_UNIT_OVERRIDES     = '{"bbl": 82.5}'
#
# Override at runtime via set_multiplier_overrides() for per-well / per-field.
# ---------------------------------------------------------------------------

# Global defaults
_DEFAULT_CATEGORY_MULTIPLIERS: Dict[str, float] = {
    "financial":    1.0,
    "safety":       50_000.0,
    "operations":   10_000.0,
    "efficiency":   5_000.0,
    "reliability":  8_000.0,
    "quality":      3_000.0,
    # DDR / Drilling categories
    "drilling":     25_000.0,   # Drilling ops deviation
    "npt":          120_000.0,  # Non-productive time $/day
    "mud":          8_000.0,    # Mud system deviations
    "hse":          60_000.0,   # HSE incidents
    "default":      2_000.0,
}

_DEFAULT_UNIT_MULTIPLIERS: Dict[str, float] = {
    "$":    1.0,
    "bbl":  70.0,
    "mcf":  3.5,
    "%":    10_000.0,
    "hrs":  5_000.0,
    "days": 50_000.0,
    "count": 15_000.0,
    "psi":  500.0,
    # DDR-specific units
    "ft":   200.0,      # Cost per foot drilled
    "ft/hr": 3_000.0,   # ROP deviation impact
    "ppg":  2_000.0,    # Mud weight deviation
    "gpm":  500.0,      # Flow rate deviation
    "default": 5_000.0,
}

# Runtime override layers (well → field → global)
_override_stack: Dict[str, Dict[str, Dict[str, float]]] = {
    "well": {},
    "field": {},
}


def set_multiplier_overrides(
    *,
    well_category: Optional[Dict[str, float]] = None,
    well_unit: Optional[Dict[str, float]] = None,
    field_category: Optional[Dict[str, float]] = None,
    field_unit: Optional[Dict[str, float]] = None,
) -> None:
    """Set per-well or per-field multiplier overrides (well > field > global)."""
    if well_category is not None:
        _override_stack["well"]["category"] = well_category
    if well_unit is not None:
        _override_stack["well"]["unit"] = well_unit
    if field_category is not None:
        _override_stack["field"]["category"] = field_category
    if field_unit is not None:
        _override_stack["field"]["unit"] = field_unit


def clear_multiplier_overrides() -> None:
    """Reset all runtime overrides back to global defaults."""
    _override_stack["well"].clear()
    _override_stack["field"].clear()


def _load_env_overrides() -> tuple:
    """Load one-time overrides from environment variables."""
    cat_env = os.environ.get("FINANCIAL_CATEGORY_OVERRIDES")
    unit_env = os.environ.get("FINANCIAL_UNIT_OVERRIDES")
    cat_ov: Dict[str, float] = {}
    unit_ov: Dict[str, float] = {}
    try:
        if cat_env:
            cat_ov = json.loads(cat_env)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Invalid FINANCIAL_CATEGORY_OVERRIDES env var — ignored")
    try:
        if unit_env:
            unit_ov = json.loads(unit_env)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Invalid FINANCIAL_UNIT_OVERRIDES env var — ignored")
    return cat_ov, unit_ov


_ENV_CAT_OVERRIDES, _ENV_UNIT_OVERRIDES = _load_env_overrides()


def _resolve_category_multiplier(category: str) -> float:
    """Resolve multiplier: well → field → env → global default."""
    key = category.lower()
    # Well level
    well_cat = _override_stack["well"].get("category", {})
    if key in well_cat:
        return well_cat[key]
    # Field level
    field_cat = _override_stack["field"].get("category", {})
    if key in field_cat:
        return field_cat[key]
    # Env level
    if key in _ENV_CAT_OVERRIDES:
        return float(_ENV_CAT_OVERRIDES[key])
    # Global
    return _DEFAULT_CATEGORY_MULTIPLIERS.get(key, _DEFAULT_CATEGORY_MULTIPLIERS["default"])


def _resolve_unit_multiplier(unit: str) -> Optional[float]:
    """Resolve unit multiplier: well → field → env → global default. Returns None if unit not found."""
    key = unit.lower().strip()
    well_unit = _override_stack["well"].get("unit", {})
    if key in well_unit:
        return well_unit[key]
    field_unit = _override_stack["field"].get("unit", {})
    if key in field_unit:
        return field_unit[key]
    if key in _ENV_UNIT_OVERRIDES:
        return float(_ENV_UNIT_OVERRIDES[key])
    return _DEFAULT_UNIT_MULTIPLIERS.get(key)


# Backward-compatible aliases
_CATEGORY_MULTIPLIERS = _DEFAULT_CATEGORY_MULTIPLIERS
_UNIT_MULTIPLIERS = _DEFAULT_UNIT_MULTIPLIERS

# KPI title keywords → risk category for risk scoring
_SAFETY_KEYWORDS = re.compile(
    r"\b(incident|near.miss|trir|ltir|fatality|injury|safety|hazard|spill|fire|explosion|npt)\b",
    re.IGNORECASE,
)
_FINANCIAL_KEYWORDS = re.compile(
    r"\b(cost|revenue|opex|capex|ebitda|profit|loss|spend|budget|saving|roi|margin)\b",
    re.IGNORECASE,
)
_RELIABILITY_KEYWORDS = re.compile(
    r"\b(mtbf|mttr|availability|uptime|downtime|reliability|maintenance|breakdown|failure)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Core calculation functions
# ---------------------------------------------------------------------------

def compute_deviation_score(kpi: Dict[str, Any]) -> float:
    """
    Compute how far a KPI is from its target (0=on-target, 100=severely-off).
    Uses actual value vs target — purely deterministic.
    """
    value = kpi.get("value")
    target = kpi.get("target")

    if value is None or target is None:
        return 20.0  # neutral unknown

    try:
        v = float(value)
        t = float(target)
        if t == 0:
            return 20.0
        pct = abs(v - t) / abs(t)
        return round(min(pct * 100.0, 100.0), 1)
    except (TypeError, ValueError):
        return 20.0


def compute_financial_impact(kpi: Dict[str, Any]) -> Optional[float]:
    """
    Estimate annual $ financial impact of the KPI's deviation from target.

    Priority order:
      1. KPI unit is "$" → use value directly
      2. Unit-based multiplier (bbl, hrs, %)
      3. Category-based multiplier
      4. Default fallback

    Returns None if value is zero or None (avoids misleading $0).
    """
    value = kpi.get("value")
    target = kpi.get("target")

    if value is None:
        return None

    try:
        v = float(value)
        t = float(target) if target is not None else None
    except (TypeError, ValueError):
        return None

    if v == 0:
        return None

    unit = (kpi.get("unit") or "").lower().strip()
    category = (kpi.get("category") or "default").lower()

    # Determine the deviation amount
    deviation = abs(v - t) if t is not None else abs(v)

    # Unit-based multiplier (configurable: well → field → env → global)
    multiplier = _resolve_unit_multiplier(unit)
    if multiplier is None:
        # Try category-based (configurable hierarchy)
        multiplier = _resolve_category_multiplier(category)

    # Special case: already in dollars
    if unit in ("$", "usd", "m$", "k$"):
        if t is not None:
            return round(deviation, 2)
        return round(abs(v), 2)

    impact = deviation * multiplier
    return round(impact, 2)


def compute_risk_score(kpi: Dict[str, Any]) -> float:
    """
    Compute risk score (0-100) based on:
    - KPI title keywords (safety → higher)
    - Trend direction
    - Deviation from target
    - Existing riskScore if already set by LLM
    """
    # Honour LLM-provided score if present and non-zero
    existing = kpi.get("riskScore")
    if existing is not None:
        try:
            return min(float(existing), 100.0)
        except (TypeError, ValueError):
            pass

    title = kpi.get("title", "")
    score = 10.0

    if _SAFETY_KEYWORDS.search(title):
        score = max(score, 75.0)
    if _FINANCIAL_KEYWORDS.search(title):
        score = max(score, 50.0)
    if _RELIABILITY_KEYWORDS.search(title):
        score = max(score, 40.0)

    trend = (kpi.get("trend") or "").lower()
    ct = (kpi.get("changeType") or "").lower()
    if trend in ("deteriorating", "down") or ct == "negative":
        score = min(score + 20.0, 100.0)

    dev = compute_deviation_score(kpi)
    score = min(score + dev * 0.2, 100.0)

    return round(score, 1)


def compute_financial_impact_score(kpi: Dict[str, Any]) -> float:
    """
    Convert financial impact $ into a 0-100 score for ranking.
    Uses log scale so extreme values don't dominate.
    """
    import math
    impact = compute_financial_impact(kpi)
    if impact is None or impact <= 0:
        return 5.0
    # log scale: $1K=17, $10K=33, $100K=50, $1M=67, $10M=83, $100M=100
    score = min((math.log10(max(impact, 1)) / 8.0) * 100.0, 100.0)
    return round(score, 1)


def compute_kpi_financial_scores(kpis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich all KPIs with deterministic scores. Overwrites only if LLM left zeros.
    Returns enriched list (same order).
    """
    enriched = []
    for kpi in kpis:
        k = dict(kpi)

        dev_score = compute_deviation_score(k)
        fin_impact = compute_financial_impact(k)
        fin_score = compute_financial_impact_score(k)
        risk_score = compute_risk_score(k)

        # Only override zero / None values — preserve LLM-set non-zero scores
        if not k.get("deviationScore"):
            k["deviationScore"] = dev_score
        if not k.get("financialImpactScore"):
            k["financialImpactScore"] = fin_score
        if not k.get("riskScore"):
            k["riskScore"] = risk_score

        # Add computed financial impact in dollars
        k["computed_financial_impact_usd"] = fin_impact

        enriched.append(k)
    return enriched


def compute_recommendation_roi(rec: Dict[str, Any], kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute ROI for a recommendation by linking to the KPI it affects.

    rec fields used: kpi_id, target, financial_impact (optional)
    Returns: { roi, payback_months, annual_benefit, confidence }
    """
    kpi_id = rec.get("kpi_id") or rec.get("kpiId")
    linked_kpi = next(
        (k for k in kpis if k.get("id") == kpi_id or k.get("title") == kpi_id),
        None,
    )

    if linked_kpi:
        impact = compute_financial_impact(linked_kpi)
        if impact and impact > 0:
            # Assume implementation cost = 10% of annual benefit (conservative)
            implementation_cost = impact * 0.10
            roi = round((impact - implementation_cost) / max(implementation_cost, 1) * 100, 1)
            payback_months = round(implementation_cost / max(impact / 12, 1), 1)
            return {
                "annual_benefit_usd": impact,
                "implementation_cost_usd": round(implementation_cost, 2),
                "roi_percent": roi,
                "payback_months": payback_months,
                "confidence": linked_kpi.get("confidence", 0.7),
            }

    return {"annual_benefit_usd": None, "roi_percent": None, "payback_months": None, "confidence": 0.5}


def compute_portfolio_summary(kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate financial summary across all KPIs.
    Returns total at-risk value, breakdown by category, top 3 financial risks.
    """
    total_at_risk = 0.0
    by_category: Dict[str, float] = {}
    individual: List[Dict] = []

    for kpi in kpis:
        impact = compute_financial_impact(kpi)
        if impact and impact > 0:
            ct = (kpi.get("changeType") or "neutral").lower()
            direction = "at_risk" if ct == "negative" else "opportunity"
            total_at_risk += impact if direction == "at_risk" else 0

            cat = (kpi.get("category") or "general").lower()
            by_category[cat] = by_category.get(cat, 0.0) + impact

            individual.append({
                "title": kpi.get("title", "Unknown"),
                "impact_usd": impact,
                "direction": direction,
                "category": cat,
                "confidence": kpi.get("confidence", 0.5),
            })

    individual.sort(key=lambda x: x["impact_usd"], reverse=True)

    return {
        "total_at_risk_usd": round(total_at_risk, 2),
        "total_opportunity_usd": round(
            sum(x["impact_usd"] for x in individual if x["direction"] == "opportunity"), 2
        ),
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
        "top_financial_risks": individual[:5],
        "kpi_count_with_impact": len(individual),
    }
