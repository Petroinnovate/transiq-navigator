"""
Feature Store
=============
Formalized feature management: registry, loading, and versioning.

Ensures training/inference consistency by providing a single source
of truth for computed features.

Usage:
    from features.store import get_feature_registry, get_feature_loader

    # Register features after computation
    registry = get_feature_registry()
    registry.register("kpi_features", "1.0.0", data=kpi_scores)

    # Load features in pipeline
    loader = get_feature_loader()
    data = loader.load("kpi_features")
"""
from features.store.feature_registry import (
    FeatureRegistry,
    FeatureSetMeta,
    get_feature_registry,
)
from features.store.feature_loader import (
    FeatureLoader,
    get_feature_loader,
)
from features.store.feature_versioning import (
    compare_versions,
    list_versions,
)

__all__ = [
    "FeatureRegistry",
    "FeatureSetMeta",
    "get_feature_registry",
    "FeatureLoader",
    "get_feature_loader",
    "compare_versions",
    "list_versions",
]
