"""
Insights — Structured insight generation from Six Sigma analysis.

Converts capability / root-cause / CTQ data into actionable text
that replaces LLM-generated DMAIC prose.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def build_dmaic_from_analysis(
    ctqs: List[Dict[str, Any]],
    capability_results: List[Dict[str, Any]],
    aggregate: Dict[str, Any],
    root_causes: List[Dict[str, Any]],
    data_quality: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build the DMAIC structure deterministically from Six Sigma analysis.

    Returns a fully-populated DMAIC dict matching the dashboard schema.
    """
    # ── DEFINE ────────────────────────────────────────────────────────────
    sigma = aggregate.get("overallSigma")
    status = aggregate.get("overallStatus", "Unknown")
    n_ctqs = len(ctqs)

    top_ctq_names = [c["name"] for c in ctqs[:5]]
    problem = (
        f"Process operating at {sigma:.1f}σ ({status}). "
        f"{n_ctqs} critical-to-quality metrics identified."
        if sigma is not None
        else f"{n_ctqs} critical-to-quality metrics identified but insufficient data for sigma calculation."
    )

    financial_exposure = sum(c.get("financialImpactScore", 0) for c in ctqs)

    define = {
        "problemStatement": problem,
        "goal": f"Improve process capability to ≥ 4.0σ across {n_ctqs} CTQ metrics",
        "scope": "All identified CTQ metrics across operations",
        "stakeholders": ["Operations", "Engineering", "HSE", "Finance"],
        "ctqCharacteristics": top_ctq_names,
        "financialExposure": {"value": round(financial_exposure, 2), "unit": "score_points"},
    }

    # ── MEASURE ───────────────────────────────────────────────────────────
    baseline_metrics = []
    for cap in capability_results[:10]:
        cpk = cap.get("cpk")
        label = cap.get("metric_name", "")
        if cpk is not None:
            baseline_metrics.append(f"{label}: Cpk={cpk:.2f}")
        else:
            baseline_metrics.append(f"{label}: n={cap.get('n', 0)} (no spec limits)")

    measure = {
        "dataCollectionPlan": f"Analysed {aggregate.get('metricCount', 0)} metrics, {aggregate.get('validMetrics', 0)} with capability data",
        "measurementSystem": f"Data quality grade: {data_quality.get('grade', 'N/A')} (score: {data_quality.get('overallScore', 0):.2f})",
        "baselineMetrics": baseline_metrics,
        "dataQuality": {
            "completeness": data_quality.get("details", {}).get("completeness", 0),
            "accuracy": data_quality.get("details", {}).get("avgConfidence", 0),
            "reliability": data_quality.get("grade", "Unknown"),
        },
    }

    # ── ANALYZE ───────────────────────────────────────────────────────────
    root_cause_entries = [
        {"cause": rc["cause"], "confidence": rc["confidence"]}
        for rc in root_causes[:10]
    ]
    correlations = []
    for rc in root_causes:
        if rc.get("type") == "category_cluster":
            correlations.append(
                f"Cluster: {rc.get('metric', '')}: {', '.join(rc.get('affectedMetrics', [])[:3])}"
            )

    analyze = {
        "rootCauseAnalysis": root_cause_entries,
        "statisticalTests": [
            f"Western Electric Rules applied to {aggregate.get('metricCount', 0)} metrics",
            f"{aggregate.get('inControlCount', 0)}/{aggregate.get('metricCount', 0)} metrics in statistical control",
        ],
        "processMap": {
            "steps": ["Data Collection", "SPC Analysis", "Capability Assessment", "Root Cause Identification"],
            "bottlenecks": [rc["metric"] for rc in root_causes if rc.get("severity") == "critical"][:5],
        },
        "variationSources": [rc["cause"] for rc in root_causes if rc.get("type") == "spc_violation"][:5],
        "correlations": correlations,
    }

    # ── IMPROVE ───────────────────────────────────────────────────────────
    actions = []
    for rc in root_causes[:5]:
        sev = rc.get("severity", "warning")
        metric = rc.get("metric", "")
        if rc.get("type") == "capability_gap":
            actions.append(f"Improve process for {metric} to achieve Cpk ≥ 1.33")
        elif rc.get("type") == "spc_violation":
            actions.append(f"Investigate {rc.get('rule', '')} violation on {metric}")
        elif rc.get("type") == "trend_risk":
            actions.append(f"Reverse deteriorating trend on {metric}")
        else:
            actions.append(f"Address {sev} issue: {rc.get('cause', '')[:80]}")

    target_sigma = 4.0 if (sigma or 0) < 4.0 else 5.0
    lift = f"{(sigma or 0):.1f}σ → {target_sigma:.1f}σ"

    improve = {
        "solutions": actions,
        "pilotResults": [],
        "implementationPlan": {
            "phases": ["Quick Wins (30d)", "Process Stabilization (90d)", "Capability Improvement (180d)"],
            "resources": ["Process Engineers", "Data Analysts", "Operations Teams"],
            "timeline": "6 months",
            "risks": ["Incomplete root-cause resolution", "Resource constraints"],
        },
        "recommendedActions": actions,
        "expectedSigmaLift": lift,
    }

    # ── CONTROL ───────────────────────────────────────────────────────────
    monitored = [c["name"] for c in ctqs[:8]]
    control = {
        "controlPlan": {
            "metrics": monitored,
            "responsibilities": ["Process Owner", "Quality Engineer"],
            "frequency": "Daily SPC monitoring",
        },
        "monitoring": {
            "tools": ["SPC Control Charts", "Western Electric Rules", "Capability Trending"],
            "frequency": "Real-time / daily batch",
            "dashboards": ["Six Sigma Dashboard", "SPC Control Panel"],
        },
        "documentation": {
            "procedures": ["SPC monitoring SOP", "Out-of-control action plan"],
            "training": ["SPC fundamentals", "Control chart interpretation"],
            "auditTrail": True,
        },
        "sustainability": {
            "reviewSchedule": "Monthly capability review",
            "continuousImprovement": ["Track sigma trend", "Expand CTQ coverage"],
            "ownership": "Quality / Process Engineering",
        },
        "monitoringKPIs": monitored,
    }

    return {
        "define": define,
        "measure": measure,
        "analyze": analyze,
        "improve": improve,
        "control": control,
    }
