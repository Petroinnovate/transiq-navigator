"""
Model Drift Detector
====================
Monitors model output quality over time and flags degradation.

Supports:
  - Prediction distribution shift
  - Confidence score degradation
  - Latency regression
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelDriftReport:
    metric: str
    baseline_value: float
    current_value: float
    delta: float
    threshold: float
    drifted: bool
    details: Dict[str, Any] = field(default_factory=dict)


def detect_model_drift(
    baseline_metrics: Dict[str, float],
    current_metrics: Dict[str, float],
    thresholds: Optional[Dict[str, float]] = None,
) -> List[ModelDriftReport]:
    """
    Compare current model metrics against baseline.

    Args:
        baseline_metrics: metrics from last known-good model (e.g., {"accuracy": 0.92})
        current_metrics: metrics from current window
        thresholds: max acceptable degradation per metric (default: 5% for each)

    Returns:
        List of ModelDriftReport
    """
    if thresholds is None:
        thresholds = {k: 0.05 for k in baseline_metrics}

    reports = []
    for metric in sorted(set(baseline_metrics) | set(current_metrics)):
        baseline = baseline_metrics.get(metric, 0)
        current = current_metrics.get(metric, 0)
        threshold = thresholds.get(metric, 0.05)

        # Degradation = baseline - current (positive means worse)
        delta = baseline - current
        drifted = delta > threshold

        reports.append(ModelDriftReport(
            metric=metric,
            baseline_value=round(baseline, 4),
            current_value=round(current, 4),
            delta=round(delta, 4),
            threshold=threshold,
            drifted=drifted,
        ))

    drifted_count = sum(1 for r in reports if r.drifted)
    if drifted_count:
        logger.warning("Model drift detected in %d/%d metrics", drifted_count, len(reports))

    return reports


def detect_confidence_degradation(
    confidence_scores: List[float],
    min_avg_confidence: float = 0.7,
    min_high_confidence_pct: float = 0.5,
) -> ModelDriftReport:
    """
    Flag if average confidence drops below threshold.

    Args:
        confidence_scores: list of recent prediction confidence values [0-1]
        min_avg_confidence: minimum acceptable average confidence
        min_high_confidence_pct: minimum % of predictions with confidence > 0.8
    """
    if not confidence_scores:
        return ModelDriftReport(
            metric="average_confidence",
            baseline_value=min_avg_confidence,
            current_value=0.0,
            delta=min_avg_confidence,
            threshold=0.0,
            drifted=True,
            details={"reason": "no confidence scores available"},
        )

    avg = sum(confidence_scores) / len(confidence_scores)
    high_pct = sum(1 for c in confidence_scores if c > 0.8) / len(confidence_scores)

    drifted = avg < min_avg_confidence or high_pct < min_high_confidence_pct
    return ModelDriftReport(
        metric="average_confidence",
        baseline_value=min_avg_confidence,
        current_value=round(avg, 4),
        delta=round(min_avg_confidence - avg, 4),
        threshold=min_avg_confidence,
        drifted=drifted,
        details={
            "high_confidence_pct": round(high_pct, 4),
            "min_high_confidence_pct": min_high_confidence_pct,
            "sample_size": len(confidence_scores),
        },
    )
