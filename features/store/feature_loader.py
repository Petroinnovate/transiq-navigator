"""
Feature Loader
==============
Loads feature sets from the registry, validates schema consistency,
and provides a unified interface for training and inference pipelines.

Key guarantee: same feature loader used in training AND inference
→ eliminates training/serving skew.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from features.store.feature_registry import FeatureSetMeta, get_feature_registry

logger = logging.getLogger(__name__)


class FeatureLoader:
    """
    Loads and validates feature sets for pipeline consumption.

    Usage:
        loader = FeatureLoader()

        # Training: load + validate
        kpi_data = loader.load("kpi_features")

        # Inference: load same features (guaranteed consistent)
        kpi_data = loader.load("kpi_features")

        # Check freshness
        stale = loader.get_stale_features()
    """

    def __init__(self, registry=None):
        self._registry = registry or get_feature_registry()

    def load(
        self,
        name: str,
        version: Optional[str] = None,
        expected_columns: Optional[List[str]] = None,
    ) -> Any:
        """
        Load a feature set with optional schema validation.

        Args:
            name: Feature set name
            version: Specific version (default: latest)
            expected_columns: Validate these columns exist in the data

        Raises:
            ValueError: If feature set not found or schema mismatch
        """
        meta = self._registry.get(name, version)
        if not meta:
            raise ValueError(f"Feature set '{name}' not found in registry")

        if meta.is_stale:
            logger.warning(
                "Feature set '%s' v%s is stale (created %s, max age %sh). "
                "Consider recomputing.",
                name, meta.version, meta.created_at, meta.staleness_hours,
            )

        data = self._registry.load(name, version)

        # Schema validation
        if expected_columns and meta.columns:
            missing = set(expected_columns) - set(meta.columns)
            if missing:
                raise ValueError(
                    f"Feature set '{name}' missing expected columns: {missing}. "
                    f"Available: {meta.columns}"
                )

        logger.info(
            "Loaded feature set '%s' v%s (%d rows)",
            name, meta.version, meta.row_count,
        )
        return data

    def get_metadata(self, name: str, version: Optional[str] = None) -> Optional[FeatureSetMeta]:
        """Get metadata without loading data."""
        return self._registry.get(name, version)

    def get_stale_features(self) -> List[FeatureSetMeta]:
        """List all feature sets that need recomputation."""
        return self._registry.get_stale()

    def list_available(self) -> List[Dict[str, Any]]:
        """List all available feature sets with metadata."""
        return [
            {
                "name": m.name,
                "version": m.version,
                "columns": m.columns,
                "row_count": m.row_count,
                "stale": m.is_stale,
                "created_at": m.created_at,
            }
            for m in self._registry.list_all()
        ]


_loader: Optional[FeatureLoader] = None


def get_feature_loader() -> FeatureLoader:
    global _loader
    if _loader is None:
        _loader = FeatureLoader()
    return _loader
