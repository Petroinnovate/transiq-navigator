"""
Model Metadata Store
====================
Structured metadata tracking for model lineage, training context, and provenance.
Extends the registry with rich queryable metadata.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelMetadata:
    """Rich metadata record for a registered model."""

    def __init__(self, data: Dict[str, Any]):
        self.model_id: str = data["model_id"]
        self.name: str = data["name"]
        self.version: str = data["version"]
        self.training_data_hash: Optional[str] = data.get("training_data_hash")
        self.training_data_size: int = data.get("training_data_size", 0)
        self.feature_columns: List[str] = data.get("feature_columns", [])
        self.hyperparameters: Dict[str, Any] = data.get("hyperparameters", {})
        self.training_duration_ms: float = data.get("training_duration_ms", 0)
        self.framework: str = data.get("framework", "custom")
        self.created_by: str = data.get("created_by", "system")
        self.created_at: str = data.get(
            "created_at", datetime.now(timezone.utc).isoformat()
        )
        self.description: str = data.get("description", "")
        self.parent_model_id: Optional[str] = data.get("parent_model_id")
        self.retrain_trigger: Optional[str] = data.get("retrain_trigger")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "version": self.version,
            "training_data_hash": self.training_data_hash,
            "training_data_size": self.training_data_size,
            "feature_columns": self.feature_columns,
            "hyperparameters": self.hyperparameters,
            "training_duration_ms": self.training_duration_ms,
            "framework": self.framework,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "description": self.description,
            "parent_model_id": self.parent_model_id,
            "retrain_trigger": self.retrain_trigger,
        }


class MetadataStore:
    """
    File-backed metadata store for model lineage tracking.

    Layout:
        storage_runtime/models/metadata/{model_id}.json
    """

    def __init__(self, metadata_dir: Path):
        self.metadata_dir = metadata_dir
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def save(self, metadata: ModelMetadata) -> None:
        """Persist metadata for a model version."""
        path = self.metadata_dir / f"{metadata.model_id}.json"
        path.write_text(
            json.dumps(metadata.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("Saved metadata for model %s", metadata.model_id)

    def load(self, model_id: str) -> Optional[ModelMetadata]:
        """Load metadata for a specific model."""
        path = self.metadata_dir / f"{model_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ModelMetadata(data)

    def list_all(self) -> List[ModelMetadata]:
        """List all model metadata records."""
        results = []
        for path in self.metadata_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                results.append(ModelMetadata(data))
            except Exception as e:
                logger.warning("Failed to load metadata %s: %s", path.name, e)
        return results

    def find_lineage(self, model_id: str) -> List[ModelMetadata]:
        """Trace the lineage chain (parent → grandparent → ...)."""
        chain = []
        current_id = model_id
        seen = set()

        while current_id and current_id not in seen:
            seen.add(current_id)
            meta = self.load(current_id)
            if not meta:
                break
            chain.append(meta)
            current_id = meta.parent_model_id

        return chain

    def find_by_trigger(self, trigger: str) -> List[ModelMetadata]:
        """Find all models retrained for a specific trigger reason."""
        return [
            m for m in self.list_all()
            if m.retrain_trigger == trigger
        ]
