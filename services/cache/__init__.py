"""
Cache Layer — Package entry-point.

Provides a singleton ``tool_cache`` instance and re-exports::

    from services.cache import tool_cache
    result = tool_cache.get("kpi_analysis", {"kpis": [...]})
"""
from __future__ import annotations

from services.cache.cache import ToolCache, DEFAULT_TTL_SECONDS, MAX_CACHE_ENTRIES  # noqa: F401

# Singleton cache instance (shared across the application)
tool_cache = ToolCache()
