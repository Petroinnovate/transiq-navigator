"""
CTQ Mapper — Extract Critical-to-Quality characteristics from KPI pool.

CTQ selection is deterministic:
  - High financialImpactScore (>= threshold)
  - High riskScore (>= threshold)
  - Category in operations / efficiency / reliability / quality / safety
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Categories considered quality-critical in Oil & Gas operations
_CTQ_CATEGORIES = {"operations", "efficiency", "reliability", "quality", "safety"}

# Default thresholds (can be overridden per-call)
DEFAULT_FINANCIAL_THRESHOLD = 60
DEFAULT_RISK_THRESHOLD = 60


def extract_ctqs(
    kpis: List[Dict[str, Any]],
    *,
    financial_threshold: float = DEFAULT_FINANCIAL_THRESHOLD,
    risk_threshold: float = DEFAULT_RISK_THRESHOLD,
    max_ctqs: int = 20,
) -> List[Dict[str, Any]]:
    """
    Select CTQ KPIs from the enriched pool.

    A KPI qualifies as CTQ if ANY of:
      1. financialImpactScore >= financial_threshold
      2. riskScore >= risk_threshold
      3. category is in _CTQ_CATEGORIES AND (financialImpactScore > 0 OR riskScore > 0)

    Returns list of CTQ dicts with metadata explaining selection reason.
    """
    ctqs: List[Dict[str, Any]] = []

    for kpi in kpis:
        fin_score = float(kpi.get("financialImpactScore") or 0)
        risk_score = float(kpi.get("riskScore") or 0)
        category = (kpi.get("category") or "").lower()
        reasons: List[str] = []

        if fin_score >= financial_threshold:
            reasons.append(f"financialImpactScore={fin_score:.0f} >= {financial_threshold}")
        if risk_score >= risk_threshold:
            reasons.append(f"riskScore={risk_score:.0f} >= {risk_threshold}")
        if category in _CTQ_CATEGORIES and (fin_score > 0 or risk_score > 0):
            if not reasons:
                reasons.append(f"category={category} with scores > 0")

        if reasons:
            ctqs.append({
                "kpi_id": kpi.get("id", ""),
                "name": kpi.get("title") or kpi.get("name", "Unknown KPI"),
                "value": kpi.get("value"),
                "unit": kpi.get("unit", ""),
                "target": kpi.get("target"),
                "category": category,
                "financialImpactScore": fin_score,
                "riskScore": risk_score,
                "selectionReasons": reasons,
            })

    # Sort by combined score descending, take top N
    ctqs.sort(key=lambda c: c["financialImpactScore"] + c["riskScore"], reverse=True)
    selected = ctqs[:max_ctqs]

    logger.info("CTQ mapper: %d/%d KPIs selected as CTQ", len(selected), len(kpis))
    return selected
