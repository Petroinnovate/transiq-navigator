"""
KPI Intelligence Engine
=======================

Scores every KPI in the pool using a 5-factor weighted model:

  priorityScore =
      (financial   × 0.30)
    + (risk        × 0.25)
    + (deviation   × 0.20)
    + (trend       × 0.15)
    + (confidence  × 0.10)

Assigns visibility:
  ≥ 80  → primary    (display on main dashboard)
  ≥ 50  → secondary  (show on drill-down / expanded view)
  <  50  → hidden     (used for AI reasoning / charts only)

Also generates a human-readable `selectionReason` for the
"Why this KPI?" tooltip shown on cards.
"""
from __future__ import annotations

from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Sub-scores (each returns 0–100)
# ---------------------------------------------------------------------------

def _financial_score(kpi: Dict[str, Any]) -> float:
    """Score based on financial impact indicators."""
    base = kpi.get("financialImpactScore")
    if base is not None:
        try:
            return min(float(base), 100.0)
        except (TypeError, ValueError):
            pass
    # Infer from tier / category
    cat = (kpi.get("category") or kpi.get("priority") or "tier4").lower()
    if "tier1" in cat or cat == "finance":
        return 70.0
    if "tier2" in cat or cat == "safety":
        return 40.0
    if "tier3" in cat or cat == "operations":
        return 20.0
    return 5.0


def _risk_score(kpi: Dict[str, Any]) -> float:
    """Score based on risk / safety indicators."""
    base = kpi.get("riskScore")
    if base is not None:
        try:
            return min(float(base), 100.0)
        except (TypeError, ValueError):
            pass
    ct = (kpi.get("changeType") or "").lower()
    trend = (kpi.get("trend") or "").lower()
    status = (kpi.get("status") or "").lower()
    if status == "critical" or ct == "negative":
        return 75.0
    if status == "warning" or trend in ("down", "deteriorating"):
        return 50.0
    return 10.0


def _deviation_score(kpi: Dict[str, Any]) -> float:
    """Score: how far actual is from target (larger gap = higher urgency)."""
    base = kpi.get("deviationScore")
    if base is not None:
        try:
            return min(float(base), 100.0)
        except (TypeError, ValueError):
            pass
    value = kpi.get("value")
    target = kpi.get("target")
    if value is None or target is None:
        return 20.0
    try:
        t = float(target)
        if t == 0:
            return 20.0
        pct = abs(float(value) - t) / abs(t)
        return min(pct * 100.0, 100.0)
    except (TypeError, ValueError):
        return 20.0


def _trend_score(kpi: Dict[str, Any]) -> float:
    """Score: strength of trend signal (negative trends = higher urgency)."""
    base = kpi.get("trendScore")
    if base is not None:
        try:
            return min(float(base), 100.0)
        except (TypeError, ValueError):
            pass
    trend = (kpi.get("trend") or "").lower()
    ct = (kpi.get("changeType") or "").lower()
    if trend in ("deteriorating", "down") or ct == "negative":
        return 80.0
    if trend in ("improving", "up") or ct == "positive":
        return 60.0
    return 20.0


def _confidence_score(kpi: Dict[str, Any]) -> float:
    """Convert 0–1 confidence field to 0–100."""
    conf = kpi.get("confidence", 0.5)
    try:
        return max(0.0, min(float(conf) * 100.0, 100.0))
    except (TypeError, ValueError):
        return 50.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_priority_score(kpi: Dict[str, Any]) -> float:
    """
    Weighted priority score (0–100):
      Financial × 0.30  +  Risk × 0.25  +  Deviation × 0.20
      +  Trend × 0.15   +  Confidence × 0.10
    """
    score = (
        _financial_score(kpi)   * 0.30
        + _risk_score(kpi)      * 0.25
        + _deviation_score(kpi) * 0.20
        + _trend_score(kpi)     * 0.15
        + _confidence_score(kpi)* 0.10
    )
    return round(min(score, 100.0), 1)


def assign_visibility(score: float) -> str:
    """primary / secondary / hidden based on priority score."""
    if score >= 80:
        return "primary"
    if score >= 50:
        return "secondary"
    return "hidden"


def build_selection_reason(kpi: Dict[str, Any], score: float) -> str:
    """Human-readable explanation for the 'Why this KPI?' tooltip."""
    reasons: List[str] = []

    cat = (kpi.get("category") or "").capitalize()
    if cat:
        reasons.append(cat)

    ct = (kpi.get("changeType") or "").lower()
    trend = (kpi.get("trend") or "").lower()
    status = (kpi.get("status") or "").lower()

    if status == "critical":
        reasons.append("critical status")
    elif status == "warning":
        reasons.append("requires attention")

    if ct == "negative" or trend in ("deteriorating", "down"):
        reasons.append("negative trend")
    elif ct == "positive" or trend in ("improving", "up"):
        reasons.append("positive momentum")

    value = kpi.get("value")
    target = kpi.get("target")
    if value is not None and target is not None and target != 0:
        try:
            pct = (float(value) / float(target)) * 100
            if pct < 80:
                reasons.append(f"{pct:.0f}% of target")
            elif pct >= 100:
                reasons.append(f"exceeds target ({pct:.0f}%)")
        except (TypeError, ValueError):
            pass

    reasons_str = " · ".join(reasons) if reasons else "General metric"
    return f"Score {score:.0f}/100 — {reasons_str}"


def process_kpis(kpis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich every KPI in the pool with:
      - priorityScore  (0–100 weighted composite)
      - visibility     ("primary" | "secondary" | "hidden")
      - selectionReason (string for UI tooltip)

    Returns the pool sorted by priorityScore descending.
    """
    enriched: List[Dict[str, Any]] = []
    for kpi in kpis:
        score = compute_priority_score(kpi)
        enriched.append({
            **kpi,
            "priorityScore": score,
            "visibility":    assign_visibility(score),
            "selectionReason": build_selection_reason(kpi, score),
        })
    enriched.sort(key=lambda x: x["priorityScore"], reverse=True)
    return enriched
