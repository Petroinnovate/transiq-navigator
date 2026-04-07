"""
Retraining Pipeline
===================
Monitors drift signals and triggers model retraining when thresholds are breached.

Flow:
  1. Check drift metrics (data drift + model drift)
  2. If drift exceeds threshold → trigger retraining
  3. Retrain using TrainingPipeline
  4. Evaluate new model vs production baseline
  5. Auto-promote if new model is better
  6. Log retraining decision and outcome

This is a **deterministic pipeline** — agents do NOT participate here.
Agents may *request* retraining via the orchestration layer, but the
actual retrain flow is fully automated.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from models.registry import get_model_registry
from pipelines.monitoring.data_drift import population_stability_index
from pipelines.monitoring.model_drift import detect_model_drift

logger = logging.getLogger(__name__)


@dataclass
class RetrainingDecision:
    """Captures why retraining was triggered (or skipped)."""
    triggered: bool = False
    reason: str = ""
    data_drift_score: float = 0.0
    model_drift_score: float = 0.0
    thresholds: Dict[str, float] = field(default_factory=dict)


@dataclass
class RetrainingResult:
    """Full outcome of a retraining cycle."""
    decision: RetrainingDecision = field(default_factory=RetrainingDecision)
    old_model_id: Optional[str] = None
    new_model_id: Optional[str] = None
    old_metrics: Dict[str, float] = field(default_factory=dict)
    new_metrics: Dict[str, float] = field(default_factory=dict)
    promoted: bool = False
    promotion_gate: str = ""  # "passed" | "rejected:reason" | "shadow"
    duration_ms: float = 0
    success: bool = True
    error: Optional[str] = None


class PromotionGuardrail:
    """
    Gating logic for model promotion.

    Rules (ALL must pass for auto-promote):
      1. New model must beat current on primary metric by min_improvement
      2. New model must NOT regress on any metric by more than max_regression
      3. New model must meet absolute minimum thresholds
      4. If shadow_mode=True, register as shadow (no promote) for manual review
    """

    def __init__(
        self,
        min_improvement: float = 0.02,
        max_regression: float = 0.01,
        absolute_thresholds: Optional[Dict[str, float]] = None,
        primary_metric: str = "accuracy",
        shadow_mode: bool = False,
    ):
        self.min_improvement = min_improvement
        self.max_regression = max_regression
        self.absolute_thresholds = absolute_thresholds or {"accuracy": 0.70}
        self.primary_metric = primary_metric
        self.shadow_mode = shadow_mode

    def evaluate(
        self, old_metrics: Dict[str, float], new_metrics: Dict[str, float]
    ) -> tuple[bool, str]:
        """
        Evaluate whether the new model should be promoted.

        Returns:
            (should_promote: bool, reason: str)
        """
        if self.shadow_mode:
            return False, "shadow: new model registered for shadow testing only"

        # Gate 1: Absolute minimum thresholds
        for metric, threshold in self.absolute_thresholds.items():
            val = new_metrics.get(metric, 0)
            if val < threshold:
                return False, (
                    f"rejected: {metric}={val:.4f} below absolute minimum {threshold:.4f}"
                )

        # Gate 2: No baseline → auto-promote
        if not old_metrics:
            return True, "passed: no baseline (first model)"

        # Gate 3: Primary metric improvement
        old_primary = old_metrics.get(self.primary_metric, 0)
        new_primary = new_metrics.get(self.primary_metric, 0)
        if new_primary < old_primary + self.min_improvement:
            return False, (
                f"rejected: {self.primary_metric} improvement "
                f"{new_primary - old_primary:+.4f} < required {self.min_improvement:.4f}"
            )

        # Gate 4: No regression on any tracked metric
        for metric in old_metrics:
            old_val = old_metrics[metric]
            new_val = new_metrics.get(metric, 0)
            regression = old_val - new_val
            if regression > self.max_regression:
                return False, (
                    f"rejected: {metric} regressed by {regression:.4f} "
                    f"> max allowed {self.max_regression:.4f}"
                )

        return True, "passed: all gates cleared"


class RetrainingPipeline:
    """
    Automated retraining loop:

    1. Evaluate drift (data distribution shift + model output degradation)
    2. Decide whether to retrain
    3. Execute training pipeline
    4. Compare new model vs production baseline
    5. Promote if improvement ≥ min_improvement
    """

    def __init__(
        self,
        model_name: str = "transiq_scorer",
        data_drift_threshold: float = 0.20,
        model_drift_threshold: float = 0.15,
        min_improvement: float = 0.02,
        max_regression: float = 0.01,
        auto_promote: bool = True,
        shadow_mode: bool = False,
        absolute_thresholds: Optional[Dict[str, float]] = None,
        primary_metric: str = "accuracy",
    ):
        self.model_name = model_name
        self.data_drift_threshold = data_drift_threshold
        self.model_drift_threshold = model_drift_threshold
        self.auto_promote = auto_promote

        self._registry = get_model_registry()
        self._guardrail = PromotionGuardrail(
            min_improvement=min_improvement,
            max_regression=max_regression,
            absolute_thresholds=absolute_thresholds or {"accuracy": 0.70},
            primary_metric=primary_metric,
            shadow_mode=shadow_mode,
        )

    # ── Public API ─────────────────────────────────────────────────

    def check_and_retrain(
        self,
        current_data: Any,
        baseline_data: Any,
        train_fn: Optional[Callable] = None,
        eval_fn: Optional[Callable] = None,
    ) -> RetrainingResult:
        """
        Full retraining cycle: drift check → retrain → evaluate → promote.

        Args:
            current_data: Recent data for drift comparison
            baseline_data: Training-time reference data
            train_fn: Callable(data) → model_artifact. Override for custom training.
            eval_fn: Callable(model, data) → metrics dict. Override for custom eval.

        Returns:
            RetrainingResult with full decision + outcome details.
        """
        start = time.time()
        result = RetrainingResult()

        try:
            # Step 1: Check drift
            decision = self._evaluate_drift(current_data, baseline_data)
            result.decision = decision

            if not decision.triggered:
                logger.info(
                    "[retrain] No drift detected (data=%.3f, model=%.3f). Skipping.",
                    decision.data_drift_score,
                    decision.model_drift_score,
                )
                result.duration_ms = (time.time() - start) * 1000
                return result

            logger.info(
                "[retrain] Drift detected! data=%.3f (threshold=%.3f), "
                "model=%.3f (threshold=%.3f). Triggering retraining.",
                decision.data_drift_score, self.data_drift_threshold,
                decision.model_drift_score, self.model_drift_threshold,
            )

            # Step 2: Get current production baseline
            prod = self._registry.get_production(self.model_name)
            if prod:
                result.old_model_id = prod.model_id
                result.old_metrics = prod.metrics

            # Step 3: Retrain
            logger.info("[retrain] Step 3: Training new model...")
            model_artifact = self._train(current_data, train_fn)

            # Step 4: Evaluate
            logger.info("[retrain] Step 4: Evaluating new model...")
            new_metrics = self._evaluate(model_artifact, current_data, eval_fn)
            result.new_metrics = new_metrics

            # Step 5: Register and compare
            version = self._next_version()
            mv = self._registry.register(
                name=self.model_name,
                version=version,
                metrics=new_metrics,
                tags={"trigger": decision.reason},
            )
            result.new_model_id = mv.model_id

            # Step 6: Promotion guardrail
            should_promote, gate_reason = self._guardrail.evaluate(
                result.old_metrics, new_metrics
            )
            result.promotion_gate = gate_reason

            if self.auto_promote and should_promote:
                self._registry.promote(mv.model_id, "production")
                # Archive old production model
                if prod:
                    self._registry.promote(prod.model_id, "archived")
                result.promoted = True
                logger.info(
                    "[retrain] Model promoted to production (id=%s): %s",
                    mv.model_id, gate_reason,
                )
            else:
                logger.info(
                    "[retrain] Model NOT promoted: %s", gate_reason
                )

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error("[retrain] Pipeline failed: %s", e)

        result.duration_ms = (time.time() - start) * 1000
        return result

    # ── Drift evaluation ───────────────────────────────────────────

    def _evaluate_drift(self, current_data: Any, baseline_data: Any) -> RetrainingDecision:
        """Compute drift scores and decide whether to retrain."""
        decision = RetrainingDecision(
            thresholds={
                "data_drift": self.data_drift_threshold,
                "model_drift": self.model_drift_threshold,
            }
        )

        # Data drift (PSI-based)
        try:
            if isinstance(baseline_data, list) and isinstance(current_data, list):
                data_score = population_stability_index(baseline_data, current_data)
            else:
                data_score = 0.0
            decision.data_drift_score = data_score
        except Exception as e:
            logger.warning("[retrain] Data drift check failed: %s", e)
            decision.data_drift_score = 0.0

        # Model drift (output quality)
        try:
            prod = self._registry.get_production(self.model_name)
            if prod and prod.metrics:
                reports = detect_model_drift(prod.metrics, {})
                drifted_count = sum(1 for r in reports if r.drifted)
                model_score = drifted_count / max(len(reports), 1)
            else:
                model_score = 0.0
            decision.model_drift_score = model_score
        except Exception as e:
            logger.warning("[retrain] Model drift check failed: %s", e)
            decision.model_drift_score = 0.0

        # Trigger if either exceeds threshold
        data_drifted = decision.data_drift_score > self.data_drift_threshold
        model_drifted = decision.model_drift_score > self.model_drift_threshold

        if data_drifted and model_drifted:
            decision.triggered = True
            decision.reason = "data_drift + model_drift"
        elif data_drifted:
            decision.triggered = True
            decision.reason = "data_drift"
        elif model_drifted:
            decision.triggered = True
            decision.reason = "model_drift"
        else:
            decision.reason = "no_drift"

        return decision

    # ── Training + evaluation ──────────────────────────────────────

    def _train(self, data: Any, train_fn: Optional[Callable] = None) -> Any:
        """Train a new model. Override via train_fn or subclass."""
        if train_fn:
            return train_fn(data)
        # Default: return placeholder (subclass for real training)
        return {"model": "retrained", "data_size": len(data) if hasattr(data, '__len__') else 0}

    def _evaluate(self, model: Any, data: Any, eval_fn: Optional[Callable] = None) -> Dict[str, float]:
        """Evaluate model. Override via eval_fn or subclass."""
        if eval_fn:
            return eval_fn(model, data)
        return {"accuracy": 0.0, "f1_score": 0.0}

    def _next_version(self) -> str:
        """Auto-increment version string."""
        models = self._registry.list_models(name=self.model_name)
        if not models:
            return "1.0.0"

        # Parse latest version and bump patch
        latest = max(models, key=lambda m: m.created_at)
        parts = latest.version.split(".")
        try:
            parts[-1] = str(int(parts[-1]) + 1)
            return ".".join(parts)
        except ValueError:
            return f"{latest.version}.1"
