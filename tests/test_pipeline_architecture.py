"""
Phase 14 — Pipeline Architecture Reorder tests.

Validates:
1. classify_all never skips — all sections get should_run=True
2. route_model does not reference DMAIC phase
3. execute_analysis uses uniform extraction (TIER2_PROMPT for all)
4. reprocess_weak uses _SYS_EXTRACT + _TIER2_PROMPT (uniform)
5. synthesize_phases builds global DMAIC (no dependency on brain.dmaic_groups)
6. map_dmaic is NOT called in orchestrator stage sequence
7. Tier breakdown no longer reports "skipped"
"""

import pytest
import types
from unittest.mock import patch, MagicMock
from dataclasses import field

import section_analyzer as sa


# ── helpers ──────────────────────────────────────────────────────────────

def _make_brain(n=5, scores=None):
    """Build a minimal DocumentBrain with n sections."""
    chunks = [f"[Page {i+1}] Content for page {i+1} with data." for i in range(n)]
    brain = sa.DocumentBrain(chunks, source_type="TEST")

    for i in range(n):
        sid = f"sec_{i}"
        node = sa.SectionNode(
            id=sid,
            title=f"Section {i}",
            text=chunks[i],
            depth=1,
            start_index=i + 1,
            end_index=i + 1,
        )
        node.score = (scores or [0.1, 0.3, 0.5, 0.7, 0.9])[i % n]
        node.tier = sa.classify_tier(node.score)
        brain.sections[sid] = node
    return brain


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1: classify_all never skips
# ═══════════════════════════════════════════════════════════════════════════

def test_classify_all_no_skips():
    brain = _make_brain(5, scores=[0.01, 0.05, 0.10, 0.14, 0.50])
    sa.classify_all(brain)
    for node in brain.iter_sections():
        assert node.execution["should_run"] is True, f"{node.id} was skipped"


def test_classify_all_lowest_score_still_processed():
    brain = _make_brain(3, scores=[0.001, 0.002, 0.003])
    sa.classify_all(brain)
    all_planned = (
        brain.execution_plan["tier1"]
        + brain.execution_plan["tier2"]
        + brain.execution_plan["tier3"]
    )
    assert len(all_planned) == 3, "All sections must be in execution plan"


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: route_model ignores DMAIC phase
# ═══════════════════════════════════════════════════════════════════════════

def test_route_model_no_dmaic_dependency():
    brain = _make_brain(1, scores=[0.5])
    node = list(brain.sections.values())[0]
    node.tier = 2
    node.score = 0.5
    node.dmaic_phase = "analyze"
    model = sa.route_model(node)
    # With dmaic_phase="analyze", old code returned "powerful".
    # New code ignores dmaic_phase — model based on score/tier only.
    assert model in ("cheap", "balanced", "powerful")
    # A score of 0.5 with tier 2 should NOT force "powerful" just because dmaic_phase is "analyze"
    assert model != "powerful" or node.score > 0.6


# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: execute_analysis uniform extraction
# ═══════════════════════════════════════════════════════════════════════════

def test_execute_analysis_uniform_source_type():
    """After execute_analysis, ALL sections should have _source_type='llm_uniform'."""
    brain = _make_brain(3, scores=[0.1, 0.5, 0.9])
    sa.classify_all(brain)
    sa.route_models(brain)

    # Mock _call_gemini_json to return a minimal valid result
    fake_result = {
        "keyPoints": [{"point": "test", "source_pages": [1]}],
        "metrics": [{"name": "m1", "value": "10", "source_pages": [1]}],
        "risks": [{"risk": "r1", "source_pages": [1]}],
        "confidence": 0.7,
    }
    with patch.object(sa, "_call_gemini_json", return_value=fake_result):
        sa.execute_analysis(brain, progress=lambda *a, **kw: None)

    for sid, sr in brain.results["sections"].items():
        assert sr.get("_source_type") == "llm_uniform", (
            f"{sid} has _source_type={sr.get('_source_type')}, expected 'llm_uniform'"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TEST 4: reprocess_weak uses uniform extraction
# ═══════════════════════════════════════════════════════════════════════════

def test_reprocess_weak_uses_sys_extract():
    """reprocess_weak should call _call_gemini_json with _SYS_EXTRACT."""
    brain = _make_brain(1, scores=[0.5])
    node = list(brain.sections.values())[0]
    node.analysis = {"confidence": 0.1, "keyFindings": []}  # weak result
    node.execution["model_tier"] = "balanced"
    brain.results["sections"][node.id] = node.analysis

    reprocessed_result = {
        "keyPoints": [{"point": "better", "source_pages": [1]}],
        "metrics": [{"name": "m1", "value": "20", "source_pages": [1]}],
        "risks": [{"risk": "r1", "source_pages": [1]}],
        "confidence": 0.8,
    }
    calls = []

    def capture_call(prompt, model=None, system_instruction=None, **kw):
        calls.append({"prompt": prompt, "system_instruction": system_instruction})
        return reprocessed_result

    with patch.object(sa, "_call_gemini_json", side_effect=capture_call):
        sa.reprocess_weak(brain)

    assert len(calls) == 1
    assert calls[0]["system_instruction"] == sa._SYS_EXTRACT, (
        "reprocess_weak must use _SYS_EXTRACT, not _SYS_TIER[1]"
    )


# ═══════════════════════════════════════════════════════════════════════════
# TEST 5: synthesize_phases is global (no brain.dmaic_groups dependency)
# ═══════════════════════════════════════════════════════════════════════════

def test_synthesize_phases_global_dmaic():
    """synthesize_phases should work even with empty dmaic_groups."""
    brain = _make_brain(3, scores=[0.5, 0.5, 0.5])
    # Populate sections with analysis results
    for node in brain.iter_sections():
        brain.results["sections"][node.id] = {
            "keyFindings": [{"finding": "test", "source_pages": [1]}],
            "kpis": [{"name": "kpi1", "value": "10", "source_pages": [1]}],
            "risks": [{"risk": "r1", "source_pages": [1]}],
            "confidence": 0.6,
            "_section_title": node.title,
        }

    # Explicitly clear dmaic_groups — synthesize_phases should NOT depend on them
    brain.dmaic_groups = {
        "define": [], "measure": [], "analyze": [],
        "improve": [], "control": [], "unassigned": [],
    }

    fake_synthesis = {
        "summary": "Phase synthesis",
        "keyFindings": [{"finding": "global", "source_pages": [1]}],
        "recommendations": [],
    }
    with patch.object(sa, "_call_gemini_json", return_value=fake_synthesis):
        sa.synthesize_phases(brain, progress=lambda *a, **kw: None)

    # Should produce results for all 5 DMAIC phases
    assert len(brain.results["dmaic"]) == 5, (
        f"Expected 5 DMAIC phases, got {len(brain.results['dmaic'])}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# TEST 6: orchestrator does NOT call map_dmaic
# ═══════════════════════════════════════════════════════════════════════════

def test_orchestrator_no_map_dmaic_call():
    """Verify map_dmaic is NOT in the orchestrator's stage sequence."""
    import inspect
    source = inspect.getsource(sa.generate_full_report_analysis)
    assert "map_dmaic(brain)" not in source, (
        "map_dmaic(brain) should be removed from orchestrator — "
        "DMAIC is now global in synthesize_phases()"
    )


# ═══════════════════════════════════════════════════════════════════════════
# TEST 7: tier breakdown has no "skipped" key
# ═══════════════════════════════════════════════════════════════════════════

def test_tier_breakdown_no_skipped():
    """The tier_breakdown dict should use 'total_uniform' instead of 'skipped'."""
    import inspect
    source = inspect.getsource(sa.generate_full_report_analysis)
    # The new code uses "total_uniform" and "tier3" (not "tier3_promoted" or "skipped")
    assert '"skipped"' not in source, "tier_breakdown should not have 'skipped' key"
    assert "total_uniform" in source, "tier_breakdown should report total_uniform"


# ═══════════════════════════════════════════════════════════════════════════
# TEST 8: Pre-synthesis guardrails exist in orchestrator
# ═══════════════════════════════════════════════════════════════════════════

def test_guardrails_in_orchestrator():
    """Orchestrator must record guardrails to brain.metadata before synthesis."""
    import inspect
    source = inspect.getsource(sa.generate_full_report_analysis)
    assert "_guardrails" in source, "Orchestrator must store _guardrails in metadata"
    assert "GUARDRAIL FAIL" in source, "Orchestrator must have GUARDRAIL FAIL checks"
    assert "coverage_pct" in source, "Orchestrator must compute coverage_pct in guardrails"


# ═══════════════════════════════════════════════════════════════════════════
# TEST 9: No top-K retrieval in section_analyzer
# ═══════════════════════════════════════════════════════════════════════════

def test_no_top_k_in_section_analyzer():
    """section_analyzer must NOT use any top-K / similarity retrieval."""
    import inspect
    source = inspect.getsource(sa)
    # These patterns indicate retrieval — forbidden in the report pipeline
    for forbidden in ["vector_db.search", "similarity_search", "retriever.get_relevant",
                      "hybrid_retrieval", "get_hybrid_retrieval"]:
        assert forbidden not in source, (
            f"FORBIDDEN: '{forbidden}' found in section_analyzer — "
            "report pipeline must NOT use top-K retrieval"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TEST 10: All sections produce results (no filtering)
# ═══════════════════════════════════════════════════════════════════════════

def test_all_sections_produce_results():
    """execute_analysis must produce a result for every section, never skip."""
    brain = _make_brain(5, scores=[0.01, 0.05, 0.3, 0.6, 0.9])
    sa.classify_all(brain)
    sa.route_models(brain)

    fake_result = {
        "keyPoints": [{"point": "test", "source_pages": [1]}],
        "metrics": [{"name": "m1", "value": "10", "source_pages": [1]}],
        "risks": [{"risk": "r1", "source_pages": [1]}],
        "confidence": 0.5,
    }
    with patch.object(sa, "_call_gemini_json", return_value=fake_result):
        sa.execute_analysis(brain, progress=lambda *a, **kw: None)

    # Every section must have a result — zero skips
    assert len(brain.results["sections"]) == 5, (
        f"Expected 5 section results, got {len(brain.results['sections'])} — "
        "some sections were skipped!"
    )


# ═══════════════════════════════════════════════════════════════════════════
# TEST 11: Group aggregation — single-section groups have source_pages
# ═══════════════════════════════════════════════════════════════════════════

def test_single_section_group_has_source_pages():
    """Single-section groups must extract source_pages from section items."""
    brain = _make_brain(10, scores=[0.5]*10)
    # Build a tree with 1 root node covering all sections
    brain.tree = [{"title": "Root", "start_index": 1, "end_index": 10}]
    # Populate section results with source_pages on items
    for node in brain.iter_sections():
        brain.results["sections"][node.id] = {
            "sectionTitle": node.title,
            "sectionSummary": "test",
            "keyFindings": [{"finding": "f1", "source_pages": [node.start_index]}],
            "kpis": [{"name": "k1", "value": "1", "source_pages": [node.start_index]}],
            "risks": [{"risk": "r1", "source_pages": [node.start_index]}],
            "confidence": 0.6,
            "confidence_level": "MEDIUM",
            "confidence_breakdown": {},
        }

    # Only 1 root group with 10 sections — will use LLM merge.
    # Instead, test with 2 roots each covering 1 section (to test single-section path)
    brain2 = _make_brain(2, scores=[0.5, 0.5])
    brain2.tree = [
        {"title": "Part A", "start_index": 1, "end_index": 1},
        {"title": "Part B", "start_index": 2, "end_index": 2},
    ]
    for node in brain2.iter_sections():
        brain2.results["sections"][node.id] = {
            "sectionTitle": node.title,
            "sectionSummary": "test",
            "keyFindings": [{"finding": "f1", "source_pages": [node.start_index]}],
            "kpis": [{"name": "k1", "value": "1", "source_pages": [node.start_index]}],
            "risks": [],
            "confidence": 0.6,
            "confidence_level": "MEDIUM",
            "confidence_breakdown": {},
        }

    # Force grouping by setting threshold low
    original_min = sa._MIN_SECTIONS_FOR_GROUPING
    sa._MIN_SECTIONS_FOR_GROUPING = 1
    try:
        sa.group_aggregate(brain2, progress=lambda *a, **kw: None)
    finally:
        sa._MIN_SECTIONS_FOR_GROUPING = original_min

    assert brain2.results["groups"] is not None
    for gk, gs in brain2.results["groups"].items():
        assert gs.get("source_pages"), (
            f"Group {gk} has empty source_pages — traceability broken"
        )
        assert gs.get("source_section_ids"), (
            f"Group {gk} missing source_section_ids"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TEST 12: Group aggregation — compact sections include source_pages
# ═══════════════════════════════════════════════════════════════════════════

def test_compact_section_has_source_pages():
    """_compact_section_for_merge must include source_pages from nested items."""
    sr = {
        "sectionTitle": "Test Section",
        "sectionSummary": "summary",
        "keyFindings": [
            {"finding": "f1", "source_pages": [5, 6]},
            {"finding": "f2", "source_pages": [7]},
        ],
        "kpis": [{"name": "k1", "value": "1", "source_pages": [5]}],
        "risks": [{"risk": "r1", "source_pages": [8]}],
        "confidence": 0.7,
        "confidence_level": "HIGH",
        "confidence_breakdown": {},
        "_source_tier": 2,
        "_source_type": "llm_uniform",
    }
    compact = sa._compact_section_for_merge(sr)
    assert "source_pages" in compact, "Compact section must include source_pages"
    assert sorted(compact["source_pages"]) == [5, 6, 7, 8], (
        f"Expected [5,6,7,8], got {compact['source_pages']}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# TEST 13: Group stats logged in brain.metadata
# ═══════════════════════════════════════════════════════════════════════════

def test_group_stats_in_metadata():
    """group_aggregate must populate brain.metadata['_group_stats']."""
    brain = _make_brain(3, scores=[0.5, 0.5, 0.5])
    brain.tree = [
        {"title": "A", "start_index": 1, "end_index": 1},
        {"title": "B", "start_index": 2, "end_index": 2},
        {"title": "C", "start_index": 3, "end_index": 3},
    ]
    for node in brain.iter_sections():
        brain.results["sections"][node.id] = {
            "sectionTitle": node.title,
            "sectionSummary": "test",
            "keyFindings": [{"finding": "f1", "source_pages": [node.start_index]}],
            "kpis": [],
            "risks": [],
            "confidence": 0.6,
            "confidence_level": "MEDIUM",
            "confidence_breakdown": {},
        }

    original_min = sa._MIN_SECTIONS_FOR_GROUPING
    sa._MIN_SECTIONS_FOR_GROUPING = 1
    try:
        sa.group_aggregate(brain, progress=lambda *a, **kw: None)
    finally:
        sa._MIN_SECTIONS_FOR_GROUPING = original_min

    stats = brain.metadata.get("_group_stats")
    assert stats is not None, "brain.metadata must have _group_stats"
    assert stats["total_groups"] == 3
    assert stats["avg_sections_per_group"] == 1.0
    assert stats["groups_missing_traceability"] == 0, (
        "All groups should have source_pages"
    )


# ═══════════════════════════════════════════════════════════════════════════
# TEST 14: Multi-section group merge — source_pages fallback
# ═══════════════════════════════════════════════════════════════════════════

def test_multi_section_merge_populates_source_pages():
    """_merge_group_batch must ensure source_pages even if LLM omits them."""
    section_results = [
        {
            "sectionTitle": f"Section {i}",
            "sectionSummary": "test",
            "keyFindings": [{"finding": f"f{i}", "source_pages": [i+1]}],
            "kpis": [{"name": f"k{i}", "value": str(i), "source_pages": [i+1]}],
            "risks": [],
            "financialImpact": {},
            "recommendations": [],
            "confidence": 0.6,
            "confidence_level": "MEDIUM",
            "confidence_breakdown": {},
            "pageRange": f"{i+1}-{i+1}",
            "_source_tier": 2,
            "_source_type": "llm_uniform",
        }
        for i in range(3)
    ]

    # Mock LLM to return result WITHOUT source_pages (simulates LLM omission)
    fake_merge = {
        "group_title": "Test Group",
        "section_count": 3,
        "summary": "merged",
        "merged_findings": [{"finding": "f1", "source_pages": [1]}],
        "aggregated_kpis": [{"name": "k1", "value": "1"}],
        "top_risks": [],
        "financial_impact": {"identified": False, "items": []},
        "recommendations": [],
        "confidence": 0.6,
        # NOTE: source_pages deliberately omitted to test fallback
    }
    with patch.object(sa, "_call_gemini_json", return_value=fake_merge):
        result = sa._merge_group_batch("Test Group", section_results, "1-3")

    assert result.get("source_pages"), (
        "source_pages must be populated even if LLM omits them"
    )
    # Should contain pages from all 3 sections
    assert 1 in result["source_pages"]
    assert 2 in result["source_pages"]
    assert 3 in result["source_pages"]


# ═══════════════════════════════════════════════════════════════════════════
# TEST 15-22: TRACEABILITY LIFECYCLE TESTS (Phase 17)
# ═══════════════════════════════════════════════════════════════════════════

# -- Test 15: Global traceability contract exists ---------------------

def test_traceability_contract_constants():
    """REQUIRED_TRACE_FIELDS and gate threshold must be defined."""
    assert hasattr(sa, "REQUIRED_TRACE_FIELDS")
    assert "source_pages" in sa.REQUIRED_TRACE_FIELDS
    assert hasattr(sa, "_TRACEABILITY_GATE_THRESHOLD")
    assert sa._TRACEABILITY_GATE_THRESHOLD >= 80


# -- Test 16: _validate_insight rejects items without source_pages -----

def test_validate_insight_rejects_missing_pages():
    """_validate_insight must reject items lacking source_pages."""
    assert sa._validate_insight({"insight": "test", "source_pages": [1, 2]}) is True
    assert sa._validate_insight({"insight": "test", "source_pages": []}) is False
    assert sa._validate_insight({"insight": "test"}) is False
    assert sa._validate_insight({}) is False
    assert sa._validate_insight("not a dict") is False


# -- Test 17: _inject_source_pages tags fallback items ----------------

def test_inject_source_pages_tags_fallback():
    """Items that receive fallback source_pages must be tagged _source_pages_fallback=True."""
    items = [
        {"finding": "real-trace", "source_pages": [5, 6]},
        {"finding": "no-trace"},  # will get fallback
    ]
    sa._inject_source_pages(items, [1, 2, 3])
    assert not items[0].get("_source_pages_fallback"), "Real items should not be tagged"
    assert items[1].get("_source_pages_fallback") is True, "Fallback items must be tagged"
    assert items[1]["source_pages"] == [1, 2, 3]


# -- Test 18: _inject_source_pages promotes source_reference first -----

def test_inject_source_pages_promotes_source_reference():
    """source_reference.source_pages (Tier 1 string) must be promoted before fallback."""
    items = [
        {"finding": "tier1", "source_reference": {"source_pages": "Pages 10-12"}},
    ]
    sa._inject_source_pages(items, [99, 100])
    assert items[0]["source_pages"] == [10, 11, 12], "Should promote Pages 10-12, not use fallback"
    assert not items[0].get("_source_pages_fallback"), "Promoted items are not fallback"


# -- Test 19: _count_untraceable counts correctly ----------------------

def test_count_untraceable():
    """_count_untraceable must count items without source_pages."""
    items = [
        {"finding": "a", "source_pages": [1]},
        {"finding": "b"},
        {"finding": "c", "source_pages": []},
        {"finding": "d", "source_pages": [3, 4]},
    ]
    assert sa._count_untraceable(items) == 2


# -- Test 20: _validate_dashboard_traceability covers all list fields --

def test_dashboard_traceability_covers_all_fields():
    """Dashboard validation must strip from sections, insights, AND optimizationSuggestions."""
    dashboard = {
        "dashboard": {
            "sections": [{
                "title": "Test",
                "keyFindings": [
                    {"finding": "good", "source_pages": [1]},
                    {"finding": "bad"},  # no source_pages
                ],
                "kpis": [],
                "risks": [],
                "recommendations": [
                    {"action": "bad-rec"},  # no source_pages
                ],
                "financialImpact": {
                    "items": [
                        {"description": "bad-fi"},  # no source_pages
                    ]
                },
            }],
            "kpis": [
                {"title": "top-bad"},  # no source_pages
            ],
            "insights": {
                "crossSectionCorrelations": [
                    {"insight": "corr-good", "source_pages": [5]},
                    {"insight": "corr-bad"},
                ],
                "crossPhaseInsights": [],
                "trends": [],
                "alerts": [],
                "recommendations": [],
            },
            "optimizationSuggestions": [{
                "title": "opt1",
                "domain_kpis": [{"name": "OEE"}],  # no source_pages
                "failure_modes": [
                    {"cause": "fouling", "source_pages": [10]},
                ],
            }],
        },
    }

    stats = sa._validate_dashboard_traceability(dashboard)
    assert stats["total_stripped"] >= 4, (
        f"Should strip at least 4 items (section.finding, rec, fi item, top kpi), got {stats['total_stripped']}"
    )

    # Verify survivors
    sec = dashboard["dashboard"]["sections"][0]
    assert len(sec["keyFindings"]) == 1
    assert sec["keyFindings"][0]["finding"] == "good"

    # Top KPIs should be empty
    assert len(dashboard["dashboard"]["kpis"]) == 0

    # Insights: only the one with source_pages survives
    ins = dashboard["dashboard"]["insights"]
    assert len(ins["crossSectionCorrelations"]) == 1


# -- Test 21: Traceability metrics distinguish real vs fallback --------

def test_traceability_metrics_real_vs_fallback():
    """Aggregation metrics must report real_traceability_pct separately from fallback."""
    # Build brain with mixed items
    brain = _make_brain(2, scores=[0.5, 0.5])
    for i, (sid, node) in enumerate(brain.sections.items()):
        node.analysis = {
            "sectionTitle": node.title,
            "keyFindings": [
                {"finding": "real", "source_pages": [i+1]},
                {"finding": "fallback", "source_pages": [i+1], "_source_pages_fallback": True},
            ],
            "kpis": [{"name": "k", "value": 1, "source_pages": [i+1]}],
            "risks": [],
            "confidence": 0.6,
        }
        brain.results["sections"][sid] = node.analysis

    # Count like the pipeline does
    total_items = 0
    real_source = 0
    fallback = 0
    for sr in brain.results["sections"].values():
        for key in ("keyFindings", "kpis", "risks"):
            for item in sr.get(key, []):
                if isinstance(item, dict):
                    total_items += 1
                    if sa._has_source_pages(item):
                        if item.get("_source_pages_fallback"):
                            fallback += 1
                        else:
                            real_source += 1

    assert total_items == 6  # 2 findings + 1 kpi per section * 2 sections
    assert real_source == 4  # 1 real finding + 1 kpi per section * 2
    assert fallback == 2     # 1 fallback finding per section * 2


# -- Test 22: Extraction tags fallback count on result ----------------

def test_extraction_normalize_tags_fallback_count():
    """_normalize_tier2 + fallback injection should leave _source_pages_fallback on items
    where LLM didn't provide source_pages."""
    result = {
        "keyPoints": [
            {"point": "has pages", "source_pages": [5]},
            {"point": "no pages"},  # will get fallback
        ],
        "metrics": [
            {"name": "m1", "value": 10, "unit": "%"},  # will get fallback
        ],
        "risks": [
            {"risk": "r1", "severity": "high"},  # will get fallback
        ],
        "sectionSummary": "test",
    }
    normalized = sa._normalize_tier2(result, "Test Section", 5, 10)

    # First finding should have real source_pages
    assert normalized["keyFindings"][0]["source_pages"] == [5]
    assert not normalized["keyFindings"][0].get("_source_pages_fallback")

    # Second finding should have fallback
    assert normalized["keyFindings"][1]["source_pages"] == [5, 6, 7, 8, 9, 10]

    # Risks should have fallback too (via _inject_source_pages)
    assert normalized["risks"][0]["source_pages"] == [5, 6, 7, 8, 9, 10]
    assert normalized["risks"][0].get("_source_pages_fallback") is True


# -- Test 23: Extraction assigns unique insight IDs -------------------

def test_normalize_tier2_assigns_insight_ids():
    """Every finding/KPI/risk should receive an insight_id at extraction boundary."""
    result = {
        "keyPoints": [{"point": "p1", "source_pages": [1]}],
        "metrics": [{"name": "m1", "value": 1, "unit": "%", "source_pages": [1]}],
        "risks": [{"risk": "r1", "severity": "high", "source_pages": [1]}],
    }
    normalized = sa._normalize_tier2(result, "T", 1, 1)

    assert normalized["keyFindings"][0].get("insight_id", "").startswith("find_")
    assert normalized["kpis"][0].get("insight_id", "").startswith("kpi_")
    assert normalized["risks"][0].get("insight_id", "").startswith("risk_")


# -- Test 24: Traceability index is built for drill-down --------------

def test_build_traceability_index_contains_items():
    """_build_traceability_index should index both group and section items by insight_id."""
    dashboard = {
        "dashboard": {
            "sections": [{
                "title": "S1",
                "keyFindings": [{"insight_id": "find_1001", "finding": "f", "source_pages": [2]}],
                "kpis": [],
                "risks": [],
            }]
        }
    }
    groups = {
        "g1": {
            "group_id": "grp_0001",
            "group_title": "G1",
            "source_section_ids": ["sec_1"],
            "merged_findings": [{"insight_id": "find_2001", "finding": "gf", "source_pages": [5]}],
            "aggregated_kpis": [],
            "top_risks": [],
        }
    }

    idx = sa._build_traceability_index(dashboard, groups)
    assert "find_1001" in idx
    assert "find_2001" in idx
    assert idx["find_2001"]["group_id"] == "grp_0001"
    assert idx["find_1001"]["section"] == "S1"


# -- Test 25: DMAIC items get supporting_groups -----------------------

def test_annotate_dmaic_supporting_groups():
    """DMAIC items should be annotated with supporting_groups by page overlap."""
    brain = _make_brain(1)
    brain.results["groups"] = {
        "g1": {
            "group_id": "grp_9001",
            "source_pages": [10, 11, 12],
        }
    }
    brain.results["dmaic"] = {
        "analyze": {
            "rootCauses": [
                {"cause": "pump wear", "source_pages": [11]},
            ]
        }
    }

    sa._annotate_dmaic_supporting_groups(brain)
    rc = brain.results["dmaic"]["analyze"]["rootCauses"][0]
    assert rc.get("supporting_groups") == ["grp_9001"]


# -- Test 26: Group aggregation writes group_id -----------------------

def test_group_aggregate_sets_group_id():
    """group_aggregate should emit group_id for each group summary."""
    brain = _make_brain(1)
    sid = next(iter(brain.sections.keys()))
    section_result = {
        "sectionTitle": "Section 1",
        "sectionSummary": "summary",
        "keyFindings": [{"finding": "f1", "source_pages": [1]}],
        "kpis": [{"title": "k1", "value": 1, "source_pages": [1]}],
        "risks": [],
        "financialImpact": {"identified": False, "items": []},
        "recommendations": [],
        "dmaicRelevance": {},
        "confidence": 0.7,
        "confidence_level": "MEDIUM",
        "confidence_breakdown": {},
    }
    brain.results["sections"][sid] = section_result
    brain.sections[sid].analysis = section_result

    fake_groups = {
        "group_a": {
            "title": "Group A",
            "section_ids": [sid],
            "page_range": [1, 1],
        }
    }

    with patch.object(sa, "_MIN_SECTIONS_FOR_GROUPING", 1), patch.object(sa, "_detect_groups", return_value=fake_groups):
        sa.group_aggregate(brain)

    out = brain.results["groups"]["group_a"]
    assert out.get("group_id", "").startswith("grp_")
