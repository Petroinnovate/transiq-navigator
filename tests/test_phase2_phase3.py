"""
Tests — Phase 2 (Performance) + Phase 3 (UX Polish)

Covers:
  * Cache layer — hit/miss, TTL, eviction, stats
  * Parallel executor — dependency groups, speedup
  * Confidence scoring — multi-factor scoring
  * Explainability — step-by-step traceability
  * Response envelope — new fields present
"""
from __future__ import annotations

import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════
# 1. Cache Layer
# ═══════════════════════════════════════════════════════════════════════

from services.cache.cache import ToolCache


class TestToolCache:
    """In-memory result cache with TTL."""

    def test_put_and_get(self):
        cache = ToolCache()
        cache.put("kpi_analysis", {"kpis": [1]}, {"result": "ok"})
        assert cache.get("kpi_analysis", {"kpis": [1]}) == {"result": "ok"}

    def test_miss(self):
        cache = ToolCache()
        assert cache.get("kpi_analysis", {"kpis": [99]}) is None

    def test_ttl_expiration(self):
        cache = ToolCache(ttl_seconds=0)  # Immediate expiry
        cache.put("kpi_analysis", {"x": 1}, {"r": 1})
        # Entry should be expired
        time.sleep(0.01)
        assert cache.get("kpi_analysis", {"x": 1}) is None

    def test_different_inputs_different_keys(self):
        cache = ToolCache()
        cache.put("kpi_analysis", {"kpis": [1]}, {"r": "a"})
        cache.put("kpi_analysis", {"kpis": [2]}, {"r": "b"})
        assert cache.get("kpi_analysis", {"kpis": [1]}) == {"r": "a"}
        assert cache.get("kpi_analysis", {"kpis": [2]}) == {"r": "b"}

    def test_invalidate(self):
        cache = ToolCache()
        cache.put("tool", {"x": 1}, {"r": 1})
        assert cache.invalidate("tool", {"x": 1}) is True
        assert cache.get("tool", {"x": 1}) is None

    def test_invalidate_missing(self):
        cache = ToolCache()
        assert cache.invalidate("tool", {"x": 1}) is False

    def test_clear(self):
        cache = ToolCache()
        cache.put("a", {}, {"r": 1})
        cache.put("b", {}, {"r": 2})
        cache.clear()
        assert cache.size == 0

    def test_eviction_at_capacity(self):
        cache = ToolCache(max_entries=2)
        cache.put("a", {}, {"r": 1})
        cache.put("b", {}, {"r": 2})
        cache.put("c", {}, {"r": 3})
        # Oldest entry should be evicted
        assert cache.size == 2
        assert cache.get("c", {}) == {"r": 3}

    def test_stats(self):
        cache = ToolCache(ttl_seconds=60, max_entries=100)
        cache.put("kpi", {"x": 1}, {"r": 1})
        cache.get("kpi", {"x": 1})  # Hit
        cache.get("kpi", {"x": 1})  # Hit

        stats = cache.stats()
        assert stats["entries"] == 1
        assert stats["total_hits"] == 2
        assert stats["ttl_seconds"] == 60
        assert stats["max_entries"] == 100

    def test_size_property(self):
        cache = ToolCache()
        assert cache.size == 0
        cache.put("a", {}, {"r": 1})
        assert cache.size == 1

    def test_same_key_overwrites(self):
        cache = ToolCache()
        cache.put("tool", {"x": 1}, {"r": "old"})
        cache.put("tool", {"x": 1}, {"r": "new"})
        assert cache.get("tool", {"x": 1}) == {"r": "new"}
        assert cache.size == 1


# ═══════════════════════════════════════════════════════════════════════
# 2. Cache Integration with Dispatcher
# ═══════════════════════════════════════════════════════════════════════

class TestDispatcherCache:
    """Cache integration in dispatch_tool."""

    def test_cache_hit_returns_cached(self):
        from services.tools.dispatcher import dispatch_tool

        cache = ToolCache()
        # Pre-populate cache
        cache.put("kpi_analysis", {"kpis": [{"name": "ROP"}]}, {"kpis": [{"name": "ROP", "priorityScore": 90}], "count": 1})

        result = dispatch_tool(
            "kpi_analysis",
            {"kpis": [{"name": "ROP"}]},
            cache=cache,
        )
        assert result["status"] == "success"
        assert result["result"]["count"] == 1

    def test_cache_miss_calls_engine(self):
        from services.tools.dispatcher import dispatch_tool

        cache = ToolCache()
        result = dispatch_tool(
            "kpi_analysis",
            {"kpis": [{"name": "ROP", "value": 85, "target": 100}]},
            cache=cache,
        )
        assert result["status"] == "success"
        # Should now be cached
        assert cache.size == 1

    def test_no_cache_still_works(self):
        """dispatch_tool works without cache parameter (backward compat)."""
        from services.tools.dispatcher import dispatch_tool

        result = dispatch_tool("kpi_analysis", {"kpis": [{"name": "ROP"}]})
        assert result["status"] == "success"


# ═══════════════════════════════════════════════════════════════════════
# 3. Parallel Executor
# ═══════════════════════════════════════════════════════════════════════

from agents.orchestrator.executor import (
    execute_plan_parallel,
    _find_parallel_groups,
)

TEST_KPIS = [
    {
        "name": "ROP", "value": 85, "target": 100, "unit": "ft/hr",
        "financialImpactScore": 88, "riskScore": 65, "trend": "up",
        "confidence": 0.92, "category": "drilling",
    },
]


class TestParallelGroups:
    """Dependency analysis for parallel execution."""

    def test_independent_steps(self):
        """Steps without refs can all run in parallel."""
        plan = [
            {"tool": "kpi_analysis", "input": {"kpis": TEST_KPIS}},
            {"tool": "six_sigma_analysis", "input": {"kpis": TEST_KPIS}},
        ]
        groups = _find_parallel_groups(plan)
        assert len(groups) == 1  # Single group (both independent)
        assert sorted(groups[0]) == [0, 1]

    def test_dependent_steps(self):
        """Steps with $ref must run after their dependencies."""
        plan = [
            {"tool": "kpi_analysis", "input": {"kpis": TEST_KPIS}},
            {"tool": "six_sigma_analysis", "input": {"kpis": {"$ref": 0}}},
        ]
        groups = _find_parallel_groups(plan)
        assert len(groups) == 2  # Sequential: [0] then [1]
        assert groups[0] == [0]
        assert groups[1] == [1]

    def test_mixed_deps(self):
        """Some steps independent, some dependent."""
        plan = [
            {"tool": "kpi_analysis", "input": {"kpis": TEST_KPIS}},
            {"tool": "predictive_forecast", "input": {"kpi": TEST_KPIS[0]}},
            {"tool": "six_sigma_analysis", "input": {"kpis": {"$ref": 0}}},
        ]
        groups = _find_parallel_groups(plan)
        # Steps 0 and 1 can run in parallel, step 2 depends on step 0
        assert len(groups) == 2
        assert sorted(groups[0]) == [0, 1]
        assert groups[1] == [2]

    def test_empty_plan(self):
        groups = _find_parallel_groups([])
        assert groups == []


class TestParallelExecution:
    """Parallel executor produces same results as sequential."""

    def test_parallel_independent_tools(self):
        """Two independent tools run and produce results."""
        plan = [
            {"tool": "kpi_analysis", "input": {"kpis": TEST_KPIS}, "reason": "Score"},
            {"tool": "six_sigma_analysis", "input": {"kpis": TEST_KPIS}, "reason": "Sigma"},
        ]

        results = execute_plan_parallel(plan)
        assert len(results) == 2
        assert results[0]["tool"] == "kpi_analysis"
        assert results[1]["tool"] == "six_sigma_analysis"
        # Both should succeed
        success_count = sum(1 for r in results if r["status"] == "success")
        assert success_count == 2

    def test_parallel_with_deps(self):
        """Dependent step gets real result from earlier step."""
        plan = [
            {"tool": "kpi_analysis", "input": {"kpis": TEST_KPIS}, "reason": "Score"},
            {"tool": "six_sigma_analysis", "input": {"kpis": {"$ref": 0}}, "reason": "Use scored KPIs"},
        ]

        results = execute_plan_parallel(plan)
        assert len(results) == 2
        assert results[0]["status"] == "success"

    def test_parallel_stop_on_failure(self):
        plan = [
            {"tool": "nonexistent", "input": {}, "reason": "Will fail"},
            {"tool": "kpi_analysis", "input": {"kpis": TEST_KPIS}, "reason": "Score"},
        ]

        results = execute_plan_parallel(plan, stop_on_failure=True)
        # Should stop after first group if failure detected
        assert any(r["status"] == "error" for r in results)

    def test_parallel_empty_plan(self):
        results = execute_plan_parallel([])
        assert results == []


# ═══════════════════════════════════════════════════════════════════════
# 4. Confidence Scoring
# ═══════════════════════════════════════════════════════════════════════

from services.response.composer import compose_response


class TestConfidenceScoring:
    """Confidence score in composed responses."""

    def test_confidence_present(self):
        """Composed response includes confidence field."""
        steps = [
            {
                "step": 0,
                "tool": "kpi_analysis",
                "status": "success",
                "result": {"kpis": [{"name": "ROP", "priorityScore": 90}], "count": 1},
                "error": None,
            },
        ]

        resp = compose_response("Test", steps)
        assert "confidence" in resp
        assert isinstance(resp["confidence"], float)
        assert 0.0 <= resp["confidence"] <= 1.0

    def test_more_tools_higher_confidence(self):
        """More tools contributing → higher confidence."""
        single = [
            {"tool": "kpi_analysis", "status": "success",
             "result": {"kpis": [{"name": "ROP", "priorityScore": 90}], "count": 1}},
        ]
        multi = [
            {"tool": "kpi_analysis", "status": "success",
             "result": {"kpis": [{"name": "ROP", "priorityScore": 90}], "count": 1}},
            {"tool": "six_sigma_analysis", "status": "success",
             "result": {"sigmaLevel": "3.2σ", "dataQuality": {"grade": "B", "overallScore": 78}}},
        ]

        conf_single = compose_response("Q", single)["confidence"]
        conf_multi = compose_response("Q", multi)["confidence"]
        assert conf_multi >= conf_single

    def test_empty_steps_default_confidence(self):
        """No successful steps → default 0.0 confidence."""
        resp = compose_response("Q", [])
        assert resp["confidence"] == 0.0


# ═══════════════════════════════════════════════════════════════════════
# 5. Explainability
# ═══════════════════════════════════════════════════════════════════════

class TestExplainability:
    """Explanation field describes analysis process."""

    def test_explanation_present(self):
        steps = [
            {"tool": "kpi_analysis", "status": "success",
             "result": {"kpis": [{"name": "ROP"}], "count": 1}},
        ]
        resp = compose_response("Q", steps)
        assert "explanation" in resp
        assert isinstance(resp["explanation"], str)
        assert len(resp["explanation"]) > 0

    def test_explanation_mentions_tools(self):
        steps = [
            {"tool": "kpi_analysis", "status": "success",
             "result": {"kpis": [], "count": 0}},
            {"tool": "six_sigma_analysis", "status": "success",
             "result": {"sigmaLevel": "3σ", "dataQuality": {"grade": "A"}}},
        ]
        resp = compose_response("Q", steps)
        assert "KPI" in resp["explanation"]
        assert "Six Sigma" in resp["explanation"]

    def test_explanation_step_count(self):
        steps = [
            {"tool": "kpi_analysis", "status": "success",
             "result": {"kpis": [], "count": 0}},
        ]
        resp = compose_response("Q", steps)
        assert "1 analysis step" in resp["explanation"]


# ═══════════════════════════════════════════════════════════════════════
# 6. Response Envelope Completeness
# ═══════════════════════════════════════════════════════════════════════

class TestResponseEnvelope:
    """All response fields present and correct types."""

    def test_full_envelope_keys(self):
        from services.response.templates import empty_response

        resp = empty_response()
        assert "summary" in resp
        assert "insights" in resp
        assert "metrics" in resp
        assert "recommendations" in resp
        assert "confidence" in resp
        assert "explanation" in resp

    def test_composed_has_all_keys(self):
        steps = [
            {"tool": "kpi_analysis", "status": "success",
             "result": {"kpis": [{"name": "ROP", "priorityScore": 85}], "count": 1}},
        ]
        resp = compose_response("Q", steps)

        assert isinstance(resp["summary"], str)
        assert isinstance(resp["insights"], list)
        assert isinstance(resp["metrics"], dict)
        assert isinstance(resp["recommendations"], list)
        assert isinstance(resp["confidence"], float)
        assert isinstance(resp["explanation"], str)
