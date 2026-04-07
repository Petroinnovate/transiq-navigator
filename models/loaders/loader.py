"""
Model Loader
=============
Loads trained model artifacts from the registry into memory.
Supports lazy loading, caching, and version pinning.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from models.registry import ModelRegistry, ModelVersion, get_model_registry

logger = logging.getLogger(__name__)


class ModelLoader:
    """
    Loads model artifacts from the registry.

    Usage:
        loader = ModelLoader()
        model = loader.load("transiq_scorer")           # latest production
        model = loader.load("transiq_scorer", "1.2.3")  # specific version
    """

    def __init__(self, registry: Optional[ModelRegistry] = None):
        self._registry = registry or get_model_registry()
        self._cache: Dict[str, Any] = {}

    def load(
        self,
        name: str,
        version: Optional[str] = None,
        force_reload: bool = False,
    ) -> Any:
        """
        Load a model artifact.

        Args:
            name: Model name in registry
            version: Specific version (default: latest production)
            force_reload: Bypass cache

        Returns:
            Loaded model artifact (dict, object, or whatever was registered)

        Raises:
            ValueError: If no matching model found
        """
        cache_key = f"{name}:{version or 'production'}"

        if not force_reload and cache_key in self._cache:
            logger.debug("Cache hit for %s", cache_key)
            return self._cache[cache_key]

        # Resolve model version
        mv = self._resolve(name, version)
        if not mv:
            raise ValueError(
                f"No model found: name={name}, version={version}"
            )

        # Load artifact
        artifact = self._load_artifact(mv)
        self._cache[cache_key] = artifact
        logger.info("Loaded model %s v%s (id=%s)", name, mv.version, mv.model_id)
        return artifact

    def _resolve(self, name: str, version: Optional[str]) -> Optional[ModelVersion]:
        """Resolve a model version from the registry."""
        if version:
            candidates = self._registry.list_models(name=name)
            for mv in candidates:
                if mv.version == version:
                    return mv
            return None
        # Default: latest production
        return self._registry.get_production(name)

    def _load_artifact(self, mv: ModelVersion) -> Any:
        """
        Load the artifact for a model version.

        Override this method for custom deserialization (pickle, ONNX, etc.)
        """
        if not mv.artifact_path:
            logger.warning("No artifact path for model %s", mv.model_id)
            return {"model_id": mv.model_id, "metrics": mv.metrics}

        path = Path(mv.artifact_path)
        if not path.exists():
            logger.warning("Artifact path does not exist: %s", path)
            return {"model_id": mv.model_id, "metrics": mv.metrics}

        # Return path for now — subclass for pickle/ONNX/etc.
        return {"model_id": mv.model_id, "artifact_path": str(path), "metrics": mv.metrics}

    def clear_cache(self) -> None:
        """Clear all cached models."""
        self._cache.clear()


_loader: Optional[ModelLoader] = None


def get_model_loader() -> ModelLoader:
    """Singleton model loader."""
    global _loader
    if _loader is None:
        _loader = ModelLoader()
    return _loader
