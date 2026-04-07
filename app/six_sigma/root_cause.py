"""
Root Cause — Deterministic root-cause analysis from KPI data.

Uses:
  - KPI deviation / trend analysis (no LLM)
  - SPC violations as causal signals
  - Correlation between CTQ metrics
  - Optionally: graph_analytics paths if available
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def identify_root_causes(
    ctqs: List[Dict[str, Any]],
    capability_results: List[Dict[str, Any]],
    kpis: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build deterministic root-cause list from CTQ + capability data.

    Root cause signals (ranked by confidence):
      1. SPC violations on a CTQ metric (direct evidence)
      2. CTQ with Cpk < 1.0 (process not capable)
      3. KPI with trend == "deteriorating" AND high riskScore
      4. Correlated deterioration across multiple KPIs in same category
    """
    causes: List[Dict[str, Any]] = []
    ctq_names = {c["name"] for c in ctqs}

    # 1. SPC violations → direct root cause signals
    for cap in capability_results:
        for violation in cap.get("violations", []):
            causes.append({
                "cause": f"{cap['metric_name']}: {violation['description']}",
                "type": "spc_violation",
                "metric": cap["metric_name"],
                "rule": violation["rule"],
                "severity": violation.get("severity", "warning"),
                "confidence": 0.90 if violation.get("severity") == "critical" else 0.75,
                "evidence": f"{len(violation.get('indices', []))} data points triggered {violation['rule']}",
            })

    # 2. Capability gaps (Cpk < 1.0)
    for cap in capability_results:
        cpk = cap.get("cpk")
        if cpk is not None and cpk < 1.0:
            sigma = cap.get("sigmaLevel") or 0
            causes.append({
                "cause": f"{cap['metric_name']}: Process not capable (Cpk={cpk:.2f}, σ={sigma:.1f})",
                "type": "capability_gap",
                "metric": cap["metric_name"],
                "cpk": cpk,
                "sigmaLevel": sigma,
                "severity": "critical" if cpk < 0.67 else "warning",
                "confidence": 0.85,
                "evidence": f"Cpk={cpk:.2f} below minimum 1.0 threshold",
            })

    # 3. Deteriorating CTQ KPIs
    for kpi in kpis:
        name = kpi.get("title") or kpi.get("name", "")
        trend = (kpi.get("trend") or kpi.get("changeType") or "").lower()
        risk = float(kpi.get("riskScore") or 0)
        if trend in ("deteriorating", "negative", "down") and risk >= 50 and name in ctq_names:
            causes.append({
                "cause": f"{name}: Deteriorating trend with risk score {risk:.0f}",
                "type": "trend_risk",
                "metric": name,
                "trend": trend,
                "riskScore": risk,
                "severity": "critical" if risk >= 80 else "warning",
                "confidence": 0.70,
                "evidence": f"Trend={trend}, riskScore={risk:.0f}",
            })

    # 4. Category-cluster deterioration
    category_issues: Dict[str, List[str]] = {}
    for kpi in kpis:
        trend = (kpi.get("trend") or kpi.get("changeType") or "").lower()
        if trend in ("deteriorating", "negative", "down"):
            cat = (kpi.get("category") or "other").lower()
            category_issues.setdefault(cat, []).append(kpi.get("title") or kpi.get("name", ""))

    for cat, metrics in category_issues.items():
        if len(metrics) >= 3:
            causes.append({
                "cause": f"Systemic deterioration in {cat}: {len(metrics)} metrics declining",
                "type": "category_cluster",
                "metric": cat,
                "affectedMetrics": metrics,
                "severity": "critical" if len(metrics) >= 5 else "warning",
                "confidence": 0.65,
                "evidence": f"{len(metrics)} KPIs deteriorating in category '{cat}'",
            })

    # Deduplicate by (type, metric) — keep highest confidence
    seen: Dict[str, Dict] = {}
    for c in causes:
        key = f"{c['type']}:{c['metric']}"
        if key not in seen or c["confidence"] > seen[key]["confidence"]:
            seen[key] = c
    deduped = sorted(seen.values(), key=lambda x: x["confidence"], reverse=True)

    logger.info("Root-cause analysis: %d causes identified", len(deduped))
    return deduped


def try_graph_root_causes(
    ctqs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Attempt graph-analytics root-cause paths. Falls back gracefully.
    """
    try:
        from app.processors.graph_rag.graph_analytics import find_paths
    except ImportError:
        return []

    graph_causes: List[Dict[str, Any]] = []
    entity_names = [c["name"] for c in ctqs[:5]]

    for i, src in enumerate(entity_names):
        for tgt in entity_names[i + 1:]:
            try:
                paths = find_paths(src, tgt, max_hops=3)
                if paths:
                    graph_causes.append({
                        "cause": f"Causal path: {src} → {tgt}",
                        "type": "graph_path",
                        "metric": src,
                        "target": tgt,
                        "pathLength": len(paths[0]) if paths else 0,
                        "severity": "info",
                        "confidence": 0.55,
                        "evidence": f"Graph path found between {src} and {tgt}",
                    })
            except Exception:
                pass

    return graph_causes
