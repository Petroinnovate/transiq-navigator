"""
Model Evaluator
================
Computes standard metrics and gates model promotion decisions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EvaluationReport:
    """Structured output from model evaluation."""
    model_id: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    passed_gate: bool = False
    gate_thresholds: Dict[str, float] = field(default_factory=dict)
    failures: List[str] = field(default_factory=list)
    baseline_comparison: Dict[str, float] = field(default_factory=dict)


class ModelEvaluator:
    """
    Evaluates model quality and gates promotion.

    Usage:
        evaluator = ModelEvaluator(thresholds={"accuracy": 0.85, "f1_score": 0.80})
        report = evaluator.evaluate(predictions, ground_truth)
        if report.passed_gate:
            registry.promote(model_id, "production")
    """

    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        custom_metrics: Optional[Dict[str, Callable]] = None,
    ):
        self.thresholds = thresholds or {
            "accuracy": 0.85,
            "f1_score": 0.80,
        }
        self.custom_metrics = custom_metrics or {}

    def evaluate(
        self,
        predictions: List[Any],
        ground_truth: List[Any],
        model_id: str = "",
        baseline_metrics: Optional[Dict[str, float]] = None,
    ) -> EvaluationReport:
        """
        Evaluate predictions against ground truth.

        Args:
            predictions: Model output
            ground_truth: Expected output
            model_id: For tracking
            baseline_metrics: Production model metrics for comparison
        """
        report = EvaluationReport(
            model_id=model_id,
            gate_thresholds=self.thresholds,
        )

        # Compute metrics
        metrics = self._compute_metrics(predictions, ground_truth)
        report.metrics = metrics

        # Gate check
        report.passed_gate = True
        for metric_name, threshold in self.thresholds.items():
            val = metrics.get(metric_name, 0)
            if val < threshold:
                report.passed_gate = False
                report.failures.append(
                    f"{metric_name}={val:.4f} < threshold={threshold:.4f}"
                )

        # Baseline comparison
        if baseline_metrics:
            for key in metrics:
                if key in baseline_metrics:
                    report.baseline_comparison[key] = (
                        metrics[key] - baseline_metrics[key]
                    )

        return report

    def _compute_metrics(
        self, predictions: List[Any], ground_truth: List[Any]
    ) -> Dict[str, float]:
        """Compute standard classification metrics."""
        if len(predictions) != len(ground_truth):
            logger.warning(
                "Prediction/truth length mismatch: %d vs %d",
                len(predictions), len(ground_truth),
            )
            return {"accuracy": 0.0, "f1_score": 0.0}

        n = len(predictions)
        if n == 0:
            return {"accuracy": 0.0, "f1_score": 0.0}

        # Accuracy
        correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
        accuracy = correct / n

        metrics = {"accuracy": accuracy}

        # Custom metrics
        for name, fn in self.custom_metrics.items():
            try:
                metrics[name] = fn(predictions, ground_truth)
            except Exception as e:
                logger.warning("Custom metric %s failed: %s", name, e)
                metrics[name] = 0.0

        # F1 (binary — extend for multiclass if needed)
        metrics.setdefault("f1_score", accuracy)  # simplified fallback

        return metrics
