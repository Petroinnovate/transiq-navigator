"""
TransIQ Model Registry
======================
Simple file-based model versioning. Tracks model metadata, promotes
models through staging → production, and provides a lookup API.

For production scale, swap with MLflow or similar.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent.parent  # Backend/
DEFAULT_REGISTRY_DIR = _ROOT / "storage_runtime" / "models"


class ModelVersion:
    """Immutable snapshot of a registered model."""

    def __init__(self, data: Dict[str, Any]):
        self.model_id: str = data["model_id"]
        self.name: str = data["name"]
        self.version: str = data["version"]
        self.stage: str = data.get("stage", "staging")  # staging | production | archived
        self.created_at: str = data["created_at"]
        self.metrics: Dict[str, float] = data.get("metrics", {})
        self.parameters: Dict[str, Any] = data.get("parameters", {})
        self.artifact_path: Optional[str] = data.get("artifact_path")
        self.tags: Dict[str, str] = data.get("tags", {})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "version": self.version,
            "stage": self.stage,
            "created_at": self.created_at,
            "metrics": self.metrics,
            "parameters": self.parameters,
            "artifact_path": self.artifact_path,
            "tags": self.tags,
        }


class ModelRegistry:
    """
    File-based model registry.

    Layout:
        storage_runtime/models/
        ├── registry.json          # index of all versions
        ├── staging/               # pre-production artifacts
        ├── production/            # promoted artifacts
        └── archived/              # retired artifacts
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_REGISTRY_DIR
        self._ensure_dirs()
        self._index_path = self.base_dir / "registry.json"
        self._index: List[Dict[str, Any]] = self._load_index()

    # ── Directory setup ────────────────────────────────────────────
    def _ensure_dirs(self):
        for sub in ["staging", "production", "archived", "metadata"]:
            (self.base_dir / sub).mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> List[Dict[str, Any]]:
        if self._index_path.exists():
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        return []

    def _save_index(self):
        self._index_path.write_text(
            json.dumps(self._index, indent=2, default=str),
            encoding="utf-8",
        )

    # ── Register ───────────────────────────────────────────────────
    def register(
        self,
        name: str,
        version: str,
        metrics: Optional[Dict[str, float]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        artifact_path: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> ModelVersion:
        """Register a new model version in staging."""
        model_id = str(uuid.uuid4())[:8]
        record = {
            "model_id": model_id,
            "name": name,
            "version": version,
            "stage": "staging",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics or {},
            "parameters": parameters or {},
            "artifact_path": artifact_path,
            "tags": tags or {},
        }

        # Copy artifact to staging if provided
        if artifact_path and os.path.exists(artifact_path):
            dest = self.base_dir / "staging" / f"{model_id}_{name}_{version}"
            dest.mkdir(parents=True, exist_ok=True)
            if os.path.isdir(artifact_path):
                shutil.copytree(artifact_path, dest / "artifact", dirs_exist_ok=True)
            else:
                shutil.copy2(artifact_path, dest / os.path.basename(artifact_path))
            record["artifact_path"] = str(dest)

        # Save metadata
        meta_path = self.base_dir / "metadata" / f"{model_id}.json"
        meta_path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")

        self._index.append(record)
        self._save_index()
        logger.info("Registered model %s v%s (id=%s) → staging", name, version, model_id)
        return ModelVersion(record)

    # ── Promote ────────────────────────────────────────────────────
    def promote(self, model_id: str, to_stage: str = "production") -> ModelVersion:
        """Promote a model from staging → production (or production → archived)."""
        record = self._find(model_id)
        if not record:
            raise ValueError(f"Model {model_id} not found")

        old_stage = record["stage"]
        record["stage"] = to_stage

        # Move artifact directory
        old_dir = self.base_dir / old_stage / f"{model_id}_{record['name']}_{record['version']}"
        new_dir = self.base_dir / to_stage / f"{model_id}_{record['name']}_{record['version']}"
        if old_dir.exists():
            shutil.move(str(old_dir), str(new_dir))
            record["artifact_path"] = str(new_dir)

        # Update metadata
        meta_path = self.base_dir / "metadata" / f"{model_id}.json"
        meta_path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
        self._save_index()

        logger.info("Promoted model %s: %s → %s", model_id, old_stage, to_stage)
        return ModelVersion(record)

    # ── Query ──────────────────────────────────────────────────────
    def get(self, model_id: str) -> Optional[ModelVersion]:
        record = self._find(model_id)
        return ModelVersion(record) if record else None

    def list_models(
        self,
        name: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> List[ModelVersion]:
        results = self._index
        if name:
            results = [r for r in results if r["name"] == name]
        if stage:
            results = [r for r in results if r["stage"] == stage]
        return [ModelVersion(r) for r in results]

    def get_production(self, name: str) -> Optional[ModelVersion]:
        """Get the latest production model for a given name."""
        candidates = [
            r for r in self._index
            if r["name"] == name and r["stage"] == "production"
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda r: r["created_at"], reverse=True)
        return ModelVersion(candidates[0])

    # ── Internal ───────────────────────────────────────────────────
    def _find(self, model_id: str) -> Optional[Dict[str, Any]]:
        for r in self._index:
            if r["model_id"] == model_id:
                return r
        return None


# ── Singleton ──────────────────────────────────────────────────────
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
