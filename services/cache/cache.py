"""
Cache Layer — In-memory result caching for tool outputs.

Caches tool results keyed by ``(tool_name, input_hash)`` with TTL
expiration.  Designed to avoid recomputing identical analyses::

    from services.cache import ToolCache
    cache = ToolCache(ttl_seconds=300)
    cache.put("kpi_analysis", {"kpis": [...]}, result)
    cached = cache.get("kpi_analysis", {"kpis": [...]})

Thread-safe via a simple lock.  No external dependencies.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any, Dict, Optional

# ── Default configuration ──────────────────────────────────────────────
DEFAULT_TTL_SECONDS = 300  # 5 minutes
MAX_CACHE_ENTRIES = 200


class ToolCache:
    """In-memory cache for tool results with TTL expiration."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_entries: int = MAX_CACHE_ENTRIES,
    ) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._store: Dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()

    # ── Public API ─────────────────────────────────────────────────────

    def get(self, tool_name: str, tool_input: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return cached result or ``None`` if miss / expired."""
        key = self._make_key(tool_name, tool_input)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() - entry.created_at > self._ttl:
                del self._store[key]
                return None
            entry.hits += 1
            return entry.result

    def put(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        """Store a result.  Evicts oldest entry if at capacity."""
        key = self._make_key(tool_name, tool_input)
        with self._lock:
            if len(self._store) >= self._max and key not in self._store:
                self._evict_oldest()
            self._store[key] = _CacheEntry(
                result=result,
                created_at=time.monotonic(),
            )

    def invalidate(self, tool_name: str, tool_input: Dict[str, Any]) -> bool:
        """Remove a specific entry.  Returns ``True`` if found."""
        key = self._make_key(tool_name, tool_input)
        with self._lock:
            return self._store.pop(key, None) is not None

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._store.clear()

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        with self._lock:
            total_hits = sum(e.hits for e in self._store.values())
            return {
                "entries": len(self._store),
                "max_entries": self._max,
                "ttl_seconds": self._ttl,
                "total_hits": total_hits,
            }

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)

    # ── Internal ───────────────────────────────────────────────────────

    @staticmethod
    def _make_key(tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Deterministic cache key from tool name + input."""
        raw = json.dumps(
            {"tool": tool_name, "input": tool_input},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    def _evict_oldest(self) -> None:
        """Remove the oldest entry (by creation time)."""
        if not self._store:
            return
        oldest_key = min(self._store, key=lambda k: self._store[k].created_at)
        del self._store[oldest_key]


class _CacheEntry:
    __slots__ = ("result", "created_at", "hits")

    def __init__(self, result: Dict[str, Any], created_at: float) -> None:
        self.result = result
        self.created_at = created_at
        self.hits = 0
