"""
Six Sigma Analyzer — Main orchestrator.

Coordinates CTQ extraction, SPC capability, root-cause analysis, and
DMAIC assembly into a single structured output that replaces LLM-generated
Six Sigma text.

Usage:
    from features.six_sigma import run_six_sigma
    result = run_six_sigma(enriched_kpis)
    dashboard["sixSigma"] = result
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from features.six_sigma.ctq_mapper import extract_ctqs
from features.six_sigma.capability import assess_capability, aggregate_capability
from features.six_sigma.root_cause import identify_root_causes, try_graph_root_causes
from features.six_sigma.msa import assess_data_quality
from features.six_sigma.insights import build_dmaic_from_analysis

logger = logging.getLogger(__name__)


class SixSigmaAnalyzer:
    """
    Deterministic Six Sigma engine.

    Wraps existing SPC engine, KPI engine, and graph analytics —
    NO LLM calls. Produces structured sixSigma output for the dashboard.
    """

    def __init__(
        self,
        kpis: List[Dict[str, Any]],
        *,
        financial_threshold: float = 60,
        risk_threshold: float = 60,
    ):
        self.kpis = kpis
        self.financial_threshold = financial_threshold
        self.risk_threshold = risk_threshold

    def analyze(self) -> Dict[str, Any]:
        """
        Run full Six Sigma analysis pipeline:

          1. MSA — data quality assessment
          2. CTQ extraction from KPI pool
          3. Capability analysis per CTQ (using existing SPC engine)
          4. Aggregate capability → overall sigma
          5. Root-cause analysis (deterministic)
          6. DMAIC assembly

        Returns the complete sixSigma dict ready for dashboard injection.
        """
        # 1. Data quality
        data_quality = assess_data_quality(self.kpis)
        logger.info("MSA: grade=%s score=%.2f", data_quality["grade"], data_quality["overallScore"])

        # 2. CTQ extraction
        ctqs = extract_ctqs(
            self.kpis,
            financial_threshold=self.financial_threshold,
            risk_threshold=self.risk_threshold,
        )

        # 3. Per-CTQ capability
        capability_results: List[Dict[str, Any]] = []
        for ctq in ctqs:
            values = self._collect_values_for_ctq(ctq)
            if len(values) >= 2:
                cap = assess_capability(
                    values,
                    metric_name=ctq["name"],
                )
                capability_results.append(cap)

        # 4. Aggregate capability
        agg = aggregate_capability(capability_results)
        logger.info(
            "Aggregate capability: Cpk=%s sigma=%s status=%s",
            agg.get("overallCpk"), agg.get("overallSigma"), agg.get("overallStatus"),
        )

        # 5. Root causes
        root_causes = identify_root_causes(ctqs, capability_results, self.kpis)
        graph_causes = try_graph_root_causes(ctqs)
        all_causes = root_causes + graph_causes

        # 6. DMAIC assembly
        dmaic = build_dmaic_from_analysis(
            ctqs, capability_results, agg, all_causes, data_quality,
        )

        # Build final sixSigma object
        result: Dict[str, Any] = {
            "methodology": "DMAIC",
            "sigmaLevel": f"{agg['overallSigma']:.1f}σ" if agg["overallSigma"] is not None else "N/A",
            "sigmaNumeric": agg["overallSigma"],
            "defectRate": f"{agg.get('overallCpk', 0) or 0:.4f} Cpk" if agg.get("overallCpk") else "N/A",
            "processCapability": agg["overallStatus"],
            "statisticalValidity": data_quality["overallScore"] >= 0.6,
            "dmaic": dmaic,
            "ctq": [
                {
                    "name": c["name"],
                    "kpi_id": c["kpi_id"],
                    "value": c["value"],
                    "unit": c["unit"],
                    "target": c["target"],
                    "category": c["category"],
                    "financialImpactScore": c["financialImpactScore"],
                    "riskScore": c["riskScore"],
                }
                for c in ctqs
            ],
            "capability": {
                "overall": agg,
                "perMetric": [
                    {
                        "metric": cap["metric_name"],
                        "cp": cap.get("cp"),
                        "cpk": cap.get("cpk"),
                        "dpmo": cap.get("dpmo"),
                        "sigmaLevel": cap.get("sigmaLevel"),
                        "status": cap.get("status"),
                        "inControl": cap.get("inControl"),
                        "n": cap.get("n"),
                    }
                    for cap in capability_results
                ],
            },
            "rootCauses": [
                {
                    "cause": rc["cause"],
                    "type": rc["type"],
                    "severity": rc["severity"],
                    "confidence": rc["confidence"],
                    "evidence": rc.get("evidence", ""),
                }
                for rc in all_causes
            ],
            "dataQuality": data_quality,
        }

        logger.info(
            "Six Sigma analysis complete: %d CTQs, %d capabilities, %d root causes, sigma=%s",
            len(ctqs), len(capability_results), len(all_causes),
            agg.get("overallSigma"),
        )
        return result

    # ──────────────────────────────────────────────────────────────────────
    # Value Collection
    # ──────────────────────────────────────────────────────────────────────

    def _collect_values_for_ctq(self, ctq: Dict[str, Any]) -> List[float]:
        """
        Collect numeric values for a CTQ metric.

        Strategy (from richest to simplest):
          1. KPI has 'history' array → use directly
          2. KPI has 'value' + 'target' → synthesize a minimal series
          3. Multiple KPIs in same category → use their values as a series
        """
        ctq_name = ctq["name"]

        # Strategy 1: KPI history
        for kpi in self.kpis:
            name = kpi.get("title") or kpi.get("name", "")
            if name == ctq_name and kpi.get("history"):
                hist = kpi["history"]
                if isinstance(hist, list) and len(hist) >= 2:
                    return [float(v) for v in hist if v is not None]

        # Strategy 2: value + target → build minimal series by adding small variation
        value = ctq.get("value")
        target = ctq.get("target")
        if value is not None:
            val = float(value)
            if target is not None:
                tgt = float(target)
                # Synthesize 5-point series between value and target
                step = (tgt - val) / 4 if tgt != val else val * 0.02
                return [val - step, val - step / 2, val, val + step / 2, val + step]
            else:
                # Use category peers
                return self._peer_values(ctq)

        return []

    def _peer_values(self, ctq: Dict[str, Any]) -> List[float]:
        """Collect values from KPIs in the same category as a proxy series."""
        category = ctq.get("category", "")
        values: List[float] = []
        for kpi in self.kpis:
            if (kpi.get("category") or "").lower() == category:
                v = kpi.get("value")
                if v is not None:
                    try:
                        values.append(float(v))
                    except (TypeError, ValueError):
                        pass
        return values


def run_six_sigma(
    kpis: List[Dict[str, Any]],
    *,
    financial_threshold: float = 60,
    risk_threshold: float = 60,
) -> Dict[str, Any]:
    """
    Convenience entry point — run full Six Sigma analysis on enriched KPIs.

    Returns the sixSigma dict ready for dashboard injection.
    """
    analyzer = SixSigmaAnalyzer(
        kpis,
        financial_threshold=financial_threshold,
        risk_threshold=risk_threshold,
    )
    return analyzer.analyze()
