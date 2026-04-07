"""
Training Pipeline Orchestrator
==============================
End-to-end flow: data → features → train → evaluate → register model.

This is a **deterministic pipeline** (no LLM). Agents should NOT be called here.
Agents may request retraining or modify hyperparams via the orchestration layer,
but this pipeline itself is fully automated.

Feature dependencies (from features/):
  - features.kpi: KPI scoring and normalization
  - features.risk: Risk factor computation
  - features.predictive: Forecasting features
  - features.six_sigma: Process capability metrics
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from models.registry import get_model_registry

logger = logging.getLogger(__name__)


@dataclass
class TrainingResult:
    model_name: str
    version: str
    model_id: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    duration_ms: float = 0
    stage: str = "staging"
    success: bool = True
    error: Optional[str] = None


class TrainingPipeline:
    """
    Orchestrates the full training flow:

    1. Load & validate data
    2. Feature engineering (KPI scoring, risk calc, etc.)
    3. Train model (or deterministic scoring calibration)
    4. Evaluate on holdout set
    5. Register in model registry (staging)
    6. Auto-promote if metrics exceed thresholds
    """

    def __init__(
        self,
        model_name: str = "transiq_scorer",
        version: str = "1.0.0",
        auto_promote: bool = False,
        promote_thresholds: Optional[Dict[str, float]] = None,
    ):
        self.model_name = model_name
        self.version = version
        self.auto_promote = auto_promote
        self.promote_thresholds = promote_thresholds or {
            "accuracy": 0.85,
            "f1_score": 0.80,
        }
        self._registry = get_model_registry()

    def run(
        self,
        train_data: Any,
        eval_data: Optional[Any] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> TrainingResult:
        """Execute the full training pipeline."""
        start = time.time()
        result = TrainingResult(model_name=self.model_name, version=self.version)

        try:
            # Step 1: Feature engineering
            logger.info("[training] Step 1/4: Feature engineering...")
            features = self._extract_features(train_data, parameters)

            # Step 2: Train
            logger.info("[training] Step 2/4: Training model...")
            model_artifact = self._train(features, parameters)

            # Step 3: Evaluate
            logger.info("[training] Step 3/4: Evaluating...")
            metrics = self._evaluate(model_artifact, eval_data or train_data)
            result.metrics = metrics

            # Step 4: Register
            logger.info("[training] Step 4/4: Registering model...")
            mv = self._registry.register(
                name=self.model_name,
                version=self.version,
                metrics=metrics,
                parameters=parameters or {},
                artifact_path=model_artifact.get("path") if isinstance(model_artifact, dict) else None,
            )
            result.model_id = mv.model_id
            result.stage = mv.stage

            # Auto-promote if exceeds thresholds
            if self.auto_promote and self._meets_thresholds(metrics):
                self._registry.promote(mv.model_id, "production")
                result.stage = "production"
                logger.info("[training] Auto-promoted to production (metrics passed thresholds)")

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error("[training] Pipeline failed: %s", e)

        result.duration_ms = (time.time() - start) * 1000
        return result

    def _extract_features(self, data: Any, params: Optional[Dict] = None) -> Any:
        """
        Feature engineering using the features/ layer.

        Override in subclass for custom feature pipelines.
        Default implementation wires into TransIQ feature modules.
        """
        features = {"raw": data}
        try:
            from features.kpi.kpi_engine import process_kpis
            if isinstance(data, list) and data and isinstance(data[0], dict):
                features["kpi_scores"] = process_kpis(data)
        except Exception as e:
            logger.debug("[training] KPI features skipped: %s", e)

        try:
            from features.risk.risk_engine import detect_risk
            features["risk_detection"] = detect_risk
        except Exception as e:
            logger.debug("[training] Risk features skipped: %s", e)

        return features

    def _train(self, features: Any, params: Optional[Dict] = None) -> Any:
        """Override in subclass for actual model training."""
        return {"model": "base", "features": features}

    def _evaluate(self, model_artifact: Any, eval_data: Any) -> Dict[str, float]:
        """Override in subclass for real evaluation."""
        return {"accuracy": 0.0, "f1_score": 0.0}

    def _meets_thresholds(self, metrics: Dict[str, float]) -> bool:
        """Check if metrics exceed promotion thresholds."""
        return all(
            metrics.get(k, 0) >= v
            for k, v in self.promote_thresholds.items()
        )
