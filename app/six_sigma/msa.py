"""
Measurement System Analysis (MSA) — data quality confidence scoring.

Evaluates how trustworthy the input data is before Six Sigma conclusions
are drawn.  Purely deterministic — no LLM.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def assess_data_quality(
    kpis: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Score overall data quality from KPI metadata.

    Checks:
      1. Confidence distribution (avg, min, % above 0.7)
      2. Missing values (target, unit, value)
      3. Source traceability (source_reference present)
    """
    if not kpis:
        return {
            "overallScore": 0.0,
            "grade": "F",
            "issues": ["No KPIs available for analysis"],
            "details": {},
        }

    total = len(kpis)

    # Confidence
    confidences = [float(k.get("confidence") or 0) for k in kpis]
    avg_conf = sum(confidences) / total
    min_conf = min(confidences)
    high_conf_pct = sum(1 for c in confidences if c >= 0.7) / total * 100

    # Completeness
    missing_value = sum(1 for k in kpis if k.get("value") is None)
    missing_unit = sum(1 for k in kpis if not k.get("unit"))
    missing_target = sum(1 for k in kpis if k.get("target") is None)
    completeness = 1.0 - (missing_value / total)

    # Traceability
    has_source = sum(1 for k in kpis if k.get("source_reference"))
    traceability = has_source / total

    # Weighted score
    score = (avg_conf * 0.40) + (completeness * 0.35) + (traceability * 0.25)
    score = round(min(1.0, max(0.0, score)), 2)

    # Grade
    grade = (
        "A" if score >= 0.90 else
        "B" if score >= 0.75 else
        "C" if score >= 0.60 else
        "D" if score >= 0.40 else "F"
    )

    issues: List[str] = []
    if avg_conf < 0.6:
        issues.append(f"Low average confidence ({avg_conf:.2f})")
    if missing_value > 0:
        issues.append(f"{missing_value} KPIs missing value")
    if traceability < 0.5:
        issues.append(f"Only {traceability*100:.0f}% KPIs have source traceability")

    return {
        "overallScore": score,
        "grade": grade,
        "issues": issues,
        "details": {
            "avgConfidence": round(avg_conf, 3),
            "minConfidence": round(min_conf, 3),
            "highConfidencePct": round(high_conf_pct, 1),
            "completeness": round(completeness, 3),
            "traceability": round(traceability, 3),
            "totalKpis": total,
            "missingValues": missing_value,
            "missingUnits": missing_unit,
            "missingTargets": missing_target,
        },
    }
