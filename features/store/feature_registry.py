"""
Feature Registry
================
Tracks computed features: schema, version, lineage, and staleness.

Each feature set gets a registered entry with:
  - name, version, columns, dtype info
  - source pipeline that produced it
  - timestamp, row count, hash
  - staleness window (max age before recomputation)

This ensures training and inference always use *the same* feature
definitions — the #1 cause of training/serving skew.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent.parent  # Backend/
DEFAULT_STORE_DIR = _ROOT / "data" / "feature_store"


class FeatureSetMeta:
    """Metadata for a registered feature set."""

    def __init__(self, data: Dict[str, Any]):
        self.name: str = data["name"]
        self.version: str = data.get("version", "1.0.0")
        self.columns: List[str] = data.get("columns", [])
        self.dtypes: Dict[str, str] = data.get("dtypes", {})
        self.row_count: int = data.get("row_count", 0)
        self.data_hash: str = data.get("data_hash", "")
        self.source_pipeline: str = data.get("source_pipeline", "")
        self.created_at: str = data.get(
            "created_at", datetime.now(timezone.utc).isoformat()
        )
        self.staleness_hours: float = data.get("staleness_hours", 24.0)
        self.tags: Dict[str, str] = data.get("tags", {})

    @property
    def is_stale(self) -> bool:
        """Check if the feature set exceeds its staleness window."""
        try:
            created = datetime.fromisoformat(self.created_at)
            age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
            return age_hours > self.staleness_hours
        except Exception:
            return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "columns": self.columns,
            "dtypes": self.dtypes,
            "row_count": self.row_count,
            "data_hash": self.data_hash,
            "source_pipeline": self.source_pipeline,
            "created_at": self.created_at,
            "staleness_hours": self.staleness_hours,
            "tags": self.tags,
        }


class FeatureRegistry:
    """
    File-backed feature registry.

    Layout:
        data/feature_store/
        ├── registry.json             # index of all feature sets
        ├── kpi_features_v1.0.0.json  # serialized feature data
        └── risk_features_v1.0.0.json
    """

    def __init__(self, store_dir: Optional[Path] = None):
        self.store_dir = Path(store_dir) if store_dir else DEFAULT_STORE_DIR
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.store_dir / "registry.json"
        self._index: List[Dict[str, Any]] = self._load_index()

    def _load_index(self) -> List[Dict[str, Any]]:
        if self._index_path.exists():
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        return []

    def _save_index(self):
        self._index_path.write_text(
            json.dumps(self._index, indent=2, default=str),
            encoding="utf-8",
        )

    def register(
        self,
        name: str,
        version: str,
        data: Any,
        columns: Optional[List[str]] = None,
        dtypes: Optional[Dict[str, str]] = None,
        source_pipeline: str = "",
        staleness_hours: float = 24.0,
        tags: Optional[Dict[str, str]] = None,
    ) -> FeatureSetMeta:
        """
        Register a computed feature set.

        Args:
            name: Feature set name (e.g. 'kpi_features')
            version: Semantic version
            data: The actual feature data (list of dicts, or any serializable)
            columns: Column names (auto-detected from data if list of dicts)
            dtypes: Column type hints
            source_pipeline: Which pipeline produced this
            staleness_hours: Max age before considered stale
            tags: Arbitrary metadata
        """
        # Auto-detect columns from data
        if columns is None and isinstance(data, list) and data and isinstance(data[0], dict):
            columns = list(data[0].keys())

        # Compute hash for deduplication
        data_json = json.dumps(data, sort_keys=True, default=str)
        data_hash = hashlib.sha256(data_json.encode()).hexdigest()[:16]

        row_count = len(data) if hasattr(data, '__len__') else 0

        meta = FeatureSetMeta({
            "name": name,
            "version": version,
            "columns": columns or [],
            "dtypes": dtypes or {},
            "row_count": row_count,
            "data_hash": data_hash,
            "source_pipeline": source_pipeline,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "staleness_hours": staleness_hours,
            "tags": tags or {},
        })

        # Save feature data
        data_path = self.store_dir / f"{name}_v{version}.json"
        data_path.write_text(data_json, encoding="utf-8")

        # Update index (replace if same name+version exists)
        self._index = [
            r for r in self._index
            if not (r["name"] == name and r["version"] == version)
        ]
        self._index.append(meta.to_dict())
        self._save_index()

        logger.info(
            "Registered feature set %s v%s (%d rows, hash=%s)",
            name, version, row_count, data_hash,
        )
        return meta

    def get(self, name: str, version: Optional[str] = None) -> Optional[FeatureSetMeta]:
        """Get metadata for a feature set. Latest version if not specified."""
        candidates = [r for r in self._index if r["name"] == name]
        if version:
            candidates = [r for r in candidates if r["version"] == version]
        if not candidates:
            return None
        # Latest by created_at
        candidates.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return FeatureSetMeta(candidates[0])

    def load(self, name: str, version: Optional[str] = None) -> Any:
        """Load the actual feature data from disk."""
        meta = self.get(name, version)
        if not meta:
            raise ValueError(f"Feature set not found: {name} v{version}")

        data_path = self.store_dir / f"{name}_v{meta.version}.json"
        if not data_path.exists():
            raise FileNotFoundError(f"Feature data file missing: {data_path}")

        return json.loads(data_path.read_text(encoding="utf-8"))

    def list_all(self, include_stale: bool = True) -> List[FeatureSetMeta]:
        """List all registered feature sets."""
        results = [FeatureSetMeta(r) for r in self._index]
        if not include_stale:
            results = [r for r in results if not r.is_stale]
        return results

    def get_stale(self) -> List[FeatureSetMeta]:
        """Get all feature sets that need recomputation."""
        return [FeatureSetMeta(r) for r in self._index if FeatureSetMeta(r).is_stale]


# ── Singleton ──────────────────────────────────────────────────────
_registry: Optional[FeatureRegistry] = None


def get_feature_registry() -> FeatureRegistry:
    global _registry
    if _registry is None:
        _registry = FeatureRegistry()
    return _registry
