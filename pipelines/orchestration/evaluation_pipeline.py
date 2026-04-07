"""
Evaluation Pipeline Orchestrator
================================
End-to-end flow: predictions → metrics → compare → report.

Used for:
  - Model quality assessment
  - A/B comparison between model versions
  - Six Sigma process capability evaluation
  - Confusion matrix generation
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models.registry import get_model_registry

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    model_name: str = ""
    model_version: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    comparison: Optional[Dict[str, Any]] = None
    duration_ms: float = 0
    passed: bool = False
    thresholds: Dict[str, float] = field(default_factory=dict)


class EvaluationPipeline:
    """
    Orchestrates model evaluation:

    1. Load model predictions (or run inference)
    2. Compute metrics (accuracy, F1, precision, recall, etc.)
    3. Compare against baseline / previous version
    4. Generate evaluation report
    5. Gate: pass/fail based on thresholds
    """

    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
    ):
        self.thresholds = thresholds or {
            "accuracy": 0.85,
            "f1_score": 0.80,
        }
        self._registry = get_model_registry()

    def run(
        self,
        predictions: List[Any],
        ground_truth: List[Any],
        model_name: str = "",
        model_version: str = "",
    ) -> EvaluationResult:
        """Execute evaluation pipeline."""
        start = time.time()
        result = EvaluationResult(
            model_name=model_name,
            model_version=model_version,
            thresholds=self.thresholds,
        )

        try:
            # Step 1: Compute metrics
            metrics = self._compute_metrics(predictions, ground_truth)
            result.metrics = metrics

            # Step 2: Compare with production baseline
            baseline = self._get_baseline(model_name)
            if baseline:
                result.comparison = self._compare(metrics, baseline)

            # Step 3: Gate check
            result.passed = all(
                metrics.get(k, 0) >= v for k, v in self.thresholds.items()
            )

        except Exception as e:
            logger.error("[evaluation] Failed: %s", e)

        result.duration_ms = (time.time() - start) * 1000
        return result

    def _compute_metrics(self, predictions: List, ground_truth: List) -> Dict[str, float]:
        """Compute evaluation metrics. Override for domain-specific metrics."""
        if not predictions or not ground_truth:
            return {}
        correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
        total = len(ground_truth)
        return {
            "accuracy": correct / total if total > 0 else 0,
            "total_samples": float(total),
        }

    def _get_baseline(self, model_name: str) -> Optional[Dict[str, float]]:
        """Get metrics from current production model."""
        prod = self._registry.get_production(model_name)
        return prod.metrics if prod else None

    def _compare(self, current: Dict[str, float], baseline: Dict[str, float]) -> Dict[str, Any]:
        """Compare current metrics against baseline."""
        comparison = {}
        all_keys = set(current) | set(baseline)
        for k in all_keys:
            cur = current.get(k, 0)
            base = baseline.get(k, 0)
            comparison[k] = {
                "current": cur,
                "baseline": base,
                "delta": cur - base,
                "improved": cur >= base,
            }
        return comparison
