"""
Feature Versioning
==================
Tracks lineage of feature set versions — which pipeline produced which
version, and what changed between versions.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from features.store.feature_registry import get_feature_registry

logger = logging.getLogger(__name__)


class FeatureVersionDiff:
    """Captures what changed between two feature set versions."""

    def __init__(
        self,
        name: str,
        old_version: str,
        new_version: str,
        added_columns: List[str],
        removed_columns: List[str],
        row_count_delta: int,
        data_hash_changed: bool,
    ):
        self.name = name
        self.old_version = old_version
        self.new_version = new_version
        self.added_columns = added_columns
        self.removed_columns = removed_columns
        self.row_count_delta = row_count_delta
        self.data_hash_changed = data_hash_changed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "added_columns": self.added_columns,
            "removed_columns": self.removed_columns,
            "row_count_delta": self.row_count_delta,
            "data_hash_changed": self.data_hash_changed,
        }


def compare_versions(name: str, old_version: str, new_version: str) -> FeatureVersionDiff:
    """Compare two versions of a feature set."""
    registry = get_feature_registry()
    old = registry.get(name, old_version)
    new = registry.get(name, new_version)

    if not old or not new:
        raise ValueError(f"Cannot compare: {name} v{old_version} or v{new_version} not found")

    old_cols = set(old.columns)
    new_cols = set(new.columns)

    return FeatureVersionDiff(
        name=name,
        old_version=old_version,
        new_version=new_version,
        added_columns=sorted(new_cols - old_cols),
        removed_columns=sorted(old_cols - new_cols),
        row_count_delta=new.row_count - old.row_count,
        data_hash_changed=old.data_hash != new.data_hash,
    )


def list_versions(name: str) -> List[Dict[str, Any]]:
    """List all versions of a feature set, newest first."""
    registry = get_feature_registry()
    all_sets = registry.list_all()
    versions = [m for m in all_sets if m.name == name]
    versions.sort(key=lambda m: m.created_at, reverse=True)
    return [
        {
            "version": m.version,
            "created_at": m.created_at,
            "row_count": m.row_count,
            "data_hash": m.data_hash,
            "stale": m.is_stale,
        }
        for m in versions
    ]
