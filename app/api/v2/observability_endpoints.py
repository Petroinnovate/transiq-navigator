"""
Observability API — System health, drift trends, model performance, pipeline latency.

Provides a real-time window into TransIQ Core Engine health:
  GET /api/v2/observability/health        → system-wide status
  GET /api/v2/observability/models        → model registry overview
  GET /api/v2/observability/features      → feature store status
  GET /api/v2/observability/predictions   → recent predictions + avg latency
  GET /api/v2/observability/drift         → drift status summary
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/observability", tags=["Observability"])


@router.get("/health", summary="System health overview")
def system_health() -> Dict[str, Any]:
    """Aggregate health status across all subsystems."""
    checks: Dict[str, Any] = {}

    # Database
    try:
        from services.db.session import SessionLocal
        if SessionLocal:
            db = SessionLocal()
            db.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
            db.close()
            checks["database"] = {"status": "ok"}
        else:
            checks["database"] = {"status": "degraded", "reason": "no session"}
    except Exception as e:
        checks["database"] = {"status": "error", "reason": str(e)}

    # Redis
    try:
        from services.workers.processor import redis_client
        if redis_client:
            redis_client.ping()
            checks["redis"] = {"status": "ok"}
        else:
            checks["redis"] = {"status": "unavailable"}
    except Exception:
        checks["redis"] = {"status": "unavailable"}

    # Celery
    try:
        from services.workers.processor import CELERY_AVAILABLE
        checks["celery"] = {"status": "ok" if CELERY_AVAILABLE else "unavailable"}
    except Exception:
        checks["celery"] = {"status": "unavailable"}

    # Model registry
    try:
        from models.registry import get_model_registry
        registry = get_model_registry()
        model_count = len(registry.list_models())
        prod_count = len(registry.list_models(stage="production"))
        checks["model_registry"] = {
            "status": "ok",
            "total_models": model_count,
            "production_models": prod_count,
        }
    except Exception as e:
        checks["model_registry"] = {"status": "error", "reason": str(e)}

    # Feature store
    try:
        from features.store import get_feature_registry
        feat_reg = get_feature_registry()
        all_features = feat_reg.list_all()
        stale = [f for f in all_features if f.is_stale]
        checks["feature_store"] = {
            "status": "ok",
            "total_feature_sets": len(all_features),
            "stale_feature_sets": len(stale),
        }
    except Exception as e:
        checks["feature_store"] = {"status": "error", "reason": str(e)}

    # Overall
    statuses = [v.get("status", "unknown") for v in checks.values()]
    if all(s in ("ok", "unavailable") for s in statuses):
        overall = "healthy"
    elif any(s == "error" for s in statuses):
        overall = "degraded"
    else:
        overall = "unknown"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }


@router.get("/models", summary="Model registry overview")
def model_overview() -> Dict[str, Any]:
    """List all models with stage, version, and metrics."""
    try:
        from models.registry import get_model_registry
        registry = get_model_registry()
        models = registry.list_models()
        return {
            "total": len(models),
            "models": [
                {
                    "model_id": m.model_id,
                    "name": m.name,
                    "version": m.version,
                    "stage": m.stage,
                    "metrics": m.metrics,
                    "created_at": m.created_at,
                    "tags": m.tags,
                }
                for m in sorted(models, key=lambda x: x.created_at, reverse=True)
            ],
        }
    except Exception as e:
        return {"total": 0, "models": [], "error": str(e)}


@router.get("/features", summary="Feature store status")
def feature_store_status() -> Dict[str, Any]:
    """List all feature sets with freshness status."""
    try:
        from features.store import get_feature_registry
        registry = get_feature_registry()
        features = registry.list_all()
        return {
            "total": len(features),
            "stale_count": sum(1 for f in features if f.is_stale),
            "features": [
                {
                    "name": f.name,
                    "version": f.version,
                    "columns": f.columns,
                    "row_count": f.row_count,
                    "stale": f.is_stale,
                    "created_at": f.created_at,
                    "staleness_hours": f.staleness_hours,
                    "source_pipeline": f.source_pipeline,
                }
                for f in sorted(features, key=lambda x: x.created_at, reverse=True)
            ],
        }
    except Exception as e:
        return {"total": 0, "stale_count": 0, "features": [], "error": str(e)}


@router.get("/predictions", summary="Recent predictions + latency stats")
def prediction_stats(limit: int = 100) -> Dict[str, Any]:
    """Recent prediction log entries with aggregate stats."""
    try:
        from pipelines.monitoring.prediction_logger import get_prediction_logger
        pred_logger = get_prediction_logger()
        records = pred_logger.get_recent(n=limit)

        if not records:
            return {"count": 0, "records": [], "stats": {}}

        latencies = [r.get("latency_ms", 0) for r in records if r.get("latency_ms")]
        confidences = [r.get("confidence", 0) for r in records if r.get("confidence")]

        stats = {}
        if latencies:
            stats["avg_latency_ms"] = round(sum(latencies) / len(latencies), 1)
            stats["p95_latency_ms"] = round(
                sorted(latencies)[int(len(latencies) * 0.95)], 1
            )
            stats["max_latency_ms"] = round(max(latencies), 1)
        if confidences:
            stats["avg_confidence"] = round(sum(confidences) / len(confidences), 4)
            stats["low_confidence_pct"] = round(
                sum(1 for c in confidences if c < 0.7) / len(confidences) * 100, 1
            )

        return {
            "count": len(records),
            "stats": stats,
            "recent": records[-10:],  # Last 10 only for response size
        }
    except Exception as e:
        return {"count": 0, "records": [], "stats": {}, "error": str(e)}


@router.get("/drift", summary="Drift monitoring status")
def drift_status() -> Dict[str, Any]:
    """Current drift signals from data and model monitors."""
    result: Dict[str, Any] = {"timestamp": datetime.now(timezone.utc).isoformat()}

    # Model drift: check production model metrics vs baseline
    try:
        from models.registry import get_model_registry
        registry = get_model_registry()

        production_models = registry.list_models(stage="production")
        model_status = []
        for pm in production_models:
            model_status.append({
                "name": pm.name,
                "version": pm.version,
                "model_id": pm.model_id,
                "metrics": pm.metrics,
                "created_at": pm.created_at,
            })
        result["production_models"] = model_status
    except Exception as e:
        result["production_models_error"] = str(e)

    # Prediction confidence trend
    try:
        from pipelines.monitoring.prediction_logger import get_prediction_logger
        records = get_prediction_logger().get_recent(n=200)
        confidences = [r.get("confidence", 0) for r in records if r.get("confidence")]

        if confidences:
            recent_50 = confidences[-50:]
            older_50 = confidences[:50] if len(confidences) > 50 else confidences

            result["confidence_trend"] = {
                "recent_avg": round(sum(recent_50) / len(recent_50), 4),
                "baseline_avg": round(sum(older_50) / len(older_50), 4),
                "sample_size": len(confidences),
                "degrading": (
                    sum(recent_50) / len(recent_50)
                    < sum(older_50) / len(older_50) - 0.05
                ) if older_50 else False,
            }
        else:
            result["confidence_trend"] = {"sample_size": 0, "degrading": False}
    except Exception as e:
        result["confidence_trend_error"] = str(e)

    # Feature staleness
    try:
        from features.store import get_feature_registry
        stale_features = get_feature_registry().get_stale()
        result["stale_features"] = [
            {"name": f.name, "version": f.version, "created_at": f.created_at}
            for f in stale_features
        ]
    except Exception as e:
        result["stale_features_error"] = str(e)

    return result
