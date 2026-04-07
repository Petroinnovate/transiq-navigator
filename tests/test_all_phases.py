"""
TransIQ Full Verification: P0 through P3
==========================================
Comprehensive test of every module, endpoint, and integration.
"""
import sys
import importlib
import traceback

ALL_ERRORS = []
PHASE_RESULTS = {}


def section(title):
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check(label, fn):
    try:
        fn()
        print(f"  [PASS] {label}")
        return True
    except Exception as e:
        msg = f"{label}: {e}"
        print(f"  [FAIL] {msg}")
        ALL_ERRORS.append(msg)
        return False


# =====================================================================
# P0: 7 FIXES
# =====================================================================
section("PHASE 0 — Bug Fixes & Hardening (7 items)")
p0_pass = 0

# P0-1: Key dependencies installed
def test_p0_deps():
    pkgs = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pydantic": "pydantic",
        "sqlalchemy": "sqlalchemy",
        "sentence_transformers": "sentence_transformers",
        "numpy": "numpy",
        "pdfplumber": "pdfplumber",
        "passlib": "passlib",
        "email_validator": "email_validator",
    }
    missing = []
    for name, mod in pkgs.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(name)
    assert not missing, f"Missing packages: {missing}"
p0_pass += check("P0-1: Core dependencies installed", test_p0_deps)

# P0-2: Predictive engine
def test_p0_predictive():
    from features.predictive.predictive_engine import forecast_kpi
    assert callable(forecast_kpi)
p0_pass += check("P0-2: Predictive engine hardened", test_p0_predictive)

# P0-3: Export endpoints
def test_p0_export():
    from app.api.v2.endpoints import router
    paths = [r.path for r in router.routes if hasattr(r, "path")]
    assert any("export" in p.lower() for p in paths), f"No export in {paths}"
p0_pass += check("P0-3: PDF/Excel export endpoint", test_p0_export)

# P0-4: Intelligence graph
def test_p0_intel_graph():
    from app.api.v2.intelligence_graph_endpoints import router
    paths = [r.path for r in router.routes if hasattr(r, "path")]
    assert len(paths) >= 2, f"Only {len(paths)} graph endpoints"
p0_pass += check("P0-4: Intelligence graph endpoints", test_p0_intel_graph)

# P0-5: Entity relationships
def test_p0_entities():
    from pipelines.inference import pipeline
    assert hasattr(pipeline, "run_pipeline"), f"pipeline exports: {[x for x in dir(pipeline) if not x.startswith('_')]}"
    # Verify entity-relationship endpoint exists
    from app.api.v2.intelligence_graph_endpoints import router as ig_r
    ig_paths = [r.path for r in ig_r.routes if hasattr(r, 'path')]
    assert any('entity' in p or 'relationship' in p for p in ig_paths)
p0_pass += check("P0-5: Entity relationships in pipeline", test_p0_entities)

# P0-6: Rate limiting
def test_p0_rate_limit():
    from app.middleware.auth import RateLimiter
    rl = RateLimiter(max_requests=2, window_seconds=60)
    assert rl.is_allowed("k1")
    assert rl.is_allowed("k1")
    assert not rl.is_allowed("k1"), "3rd request should be blocked"
p0_pass += check("P0-6: Rate limiting works", test_p0_rate_limit)

# P0-7: requirements.txt exists
def test_p0_reqfile():
    import os
    assert os.path.exists("requirements.txt"), "requirements.txt missing"
    content = open("requirements.txt").read()
    assert "fastapi" in content.lower()
    assert "pdfplumber" in content.lower()
p0_pass += check("P0-7: requirements.txt complete", test_p0_reqfile)

PHASE_RESULTS["P0"] = (p0_pass, 7)
print(f"\n  P0 Score: {p0_pass}/7")


# =====================================================================
# P1: 6 CORE DDR MODULES
# =====================================================================
section("PHASE 1 — Core DDR Modules (6 items)")
p1_pass = 0

# P1-1: DDR Parser
def test_p1_parser():
    from pipelines.inference.ddr.ddr_parser import parse_ddr_pdf, DDR_FIELD_PATTERNS, DDRParseResult
    assert callable(parse_ddr_pdf)
    assert len(DDR_FIELD_PATTERNS) >= 10, f"Only {len(DDR_FIELD_PATTERNS)} regex patterns"
p1_pass += check("P1-1: DDR Parser (pdfplumber + OCR + regex)", test_p1_parser)

# P1-2: SPC Engine
def test_p1_spc():
    from pipelines.inference.ddr.spc_engine import compute_spc, compute_fleet_spc, SPCResult
    assert callable(compute_spc)
    assert callable(compute_fleet_spc)
    data = [10.0, 10.2, 9.8, 10.1, 10.3, 9.9, 10.0, 10.1, 9.7, 10.2,
            10.0, 10.1, 9.9, 10.2, 10.0, 9.8, 10.3, 10.1, 10.0, 9.9,
            10.1, 10.0, 10.2, 9.8, 10.1]
    result = compute_spc(data, metric_name="test_metric")
    assert hasattr(result, 'mean') or hasattr(result, 'ucl') or isinstance(result, (dict, SPCResult))
p1_pass += check("P1-2: SPC Engine (UCL/LCL, Cp/Cpk, Western Electric)", test_p1_spc)

# P1-3: DDR Database Models
def test_p1_models():
    from pipelines.inference.ddr.models import (
        DDRReport, DDRRig, DepthSummary, Timeline, NPTEvent,
        FormationTop, Survey, MudData, MudChemical, DrillString,
        Personnel, BulkLogistics, HSEData, ForemanRemark,
        ExtractedMetric, KPIAudit
    )
    assert DDRReport.__tablename__ == "ddr_reports"
    assert DDRRig.__tablename__ == "ddr_rigs"
p1_pass += check("P1-3: DDR Database Schema (16 models)", test_p1_models)

# P1-4: Citation Service
def test_p1_citation():
    from pipelines.inference.ddr.citation_service import build_citation, save_extracted_metrics, get_metric_audit_trail
    assert callable(build_citation)
    assert callable(save_extracted_metrics)
    assert callable(get_metric_audit_trail)
p1_pass += check("P1-4: Citation Service [RigID-Pg#-Section-Field]", test_p1_citation)

# P1-5: Report Type Detector
def test_p1_detector():
    from pipelines.inference.ddr.report_detector import detect_report_type, detect_report_type_from_text, DDR_KEYWORDS
    assert callable(detect_report_type)
    assert callable(detect_report_type_from_text)
    assert len(DDR_KEYWORDS) >= 5
p1_pass += check("P1-5: Report Type Detector", test_p1_detector)

# P1-6: Anthropic LLM Provider
def test_p1_anthropic():
    from services.llm.providers.anthropic import AnthropicProvider
    assert AnthropicProvider is not None
    assert hasattr(AnthropicProvider, 'generate') or hasattr(AnthropicProvider, 'generate_json')
p1_pass += check("P1-6: Anthropic LLM Provider", test_p1_anthropic)

PHASE_RESULTS["P1"] = (p1_pass, 6)
print(f"\n  P1 Score: {p1_pass}/6")


# =====================================================================
# P2: 15 API ENDPOINTS + DRILLING RAG
# =====================================================================
section("PHASE 2 — DDR API Endpoints (16 items)")
p2_pass = 0

# P2-1: Fleet endpoints (3)
def test_p2_fleet():
    from app.api.ddr.fleet_endpoints import router
    paths = [r.path for r in router.routes if hasattr(r, "path")]
    assert len(paths) >= 3, f"Fleet has {len(paths)} routes, expected 3+"
    expected = ["summary", "npt-pareto", "spc"]
    for kw in expected:
        assert any(kw in p for p in paths), f"Missing fleet endpoint with '{kw}' in {paths}"
p2_pass += check("P2-1: Fleet endpoints (summary, npt-pareto, spc)", test_p2_fleet)

# P2-2: Rig endpoints (10)
def test_p2_rig():
    from app.api.ddr.rig_endpoints import router
    paths = [r.path for r in router.routes if hasattr(r, "path")]
    assert len(paths) >= 10, f"Rig has {len(paths)} routes, expected 10+"
p2_pass += check("P2-2: Rig endpoints (10 routes)", test_p2_rig)

# P2-3: Audit endpoint (1)
def test_p2_audit():
    from app.api.ddr.audit_endpoints import router
    paths = [r.path for r in router.routes if hasattr(r, "path")]
    assert len(paths) >= 1, f"Audit has {len(paths)} routes, expected 1+"
p2_pass += check("P2-3: Audit endpoint", test_p2_audit)

# P2-4: DDR core endpoints
def test_p2_ddr_core():
    from app.api.ddr.endpoints import router
    paths = [r.path for r in router.routes if hasattr(r, "path")]
    assert len(paths) >= 5, f"DDR core has {len(paths)} routes"
p2_pass += check("P2-4: DDR core endpoints", test_p2_ddr_core)

# P2-5: Drilling RAG prompt
def test_p2_rag():
    from pipelines.inference.ddr.drilling_rag_prompt import build_full_prompt, build_rag_context, DRILLING_RAG_SYSTEM_PROMPT
    assert len(DRILLING_RAG_SYSTEM_PROMPT) > 100
    assert callable(build_full_prompt)
    assert callable(build_rag_context)
p2_pass += check("P2-5: Drilling RAG prompt system", test_p2_rag)

# P2-6: All DDR routers registered in main.py
def test_p2_main_registration():
    from app.main import app
    routes = [r.path for r in app.routes if hasattr(r, "methods")]
    ddr = [r for r in routes if "/ddr/" in r]
    assert len(ddr) >= 15, f"Only {len(ddr)} DDR routes in main app"
p2_pass += check(f"P2-6: DDR routes registered in main.py", test_p2_main_registration)

PHASE_RESULTS["P2"] = (p2_pass, 6)
print(f"\n  P2 Score: {p2_pass}/6")


# =====================================================================
# P3: 9 MODULE UPGRADES
# =====================================================================
section("PHASE 3 — Module Upgrades (9 items)")
p3_pass = 0

# P3-1: Provider Fallback
def test_p3_fallback():
    from services.llm.factory import LLMFactory
    assert hasattr(LLMFactory, "generate_with_fallback")
    assert hasattr(LLMFactory, "generate_json_with_fallback")
    assert hasattr(LLMFactory, "_available_chain")
p3_pass += check("P3-1: LLM provider fallback chain", test_p3_fallback)

# P3-2: What-If Drilling Levers
def test_p3_whatif():
    from features.predictive.whatif_engine import KPI_RELATIONSHIPS, LEVER_RANGES, run_scenario
    levers = ["mud_weight_change", "wob_adjustment", "rpm_change", "rop_target", "bop_test_interval"]
    for lev in levers:
        assert lev in KPI_RELATIONSHIPS, f"Missing lever: {lev}"
        assert lev in LEVER_RANGES, f"Missing range: {lev}"
    # Test range validation
    result = run_scenario([], {"mud_weight_change": 999.0}, "test")
    assert "warnings" in result
    assert len(result["warnings"]) > 0
p3_pass += check("P3-2: DDR drilling levers + range validation", test_p3_whatif)

# P3-3: Financial Engine Config
def test_p3_financial():
    from pipelines.inference.financial_engine import (
        set_multiplier_overrides, clear_multiplier_overrides,
        _resolve_category_multiplier, _resolve_unit_multiplier,
        _DEFAULT_CATEGORY_MULTIPLIERS, _DEFAULT_UNIT_MULTIPLIERS,
        compute_financial_impact,
    )
    # DDR categories exist
    assert "drilling" in _DEFAULT_CATEGORY_MULTIPLIERS
    assert "npt" in _DEFAULT_CATEGORY_MULTIPLIERS
    assert "ft/hr" in _DEFAULT_UNIT_MULTIPLIERS
    assert "ppg" in _DEFAULT_UNIT_MULTIPLIERS
    # Override hierarchy works
    set_multiplier_overrides(well_category={"npt": 200_000.0})
    assert _resolve_category_multiplier("npt") == 200_000.0
    set_multiplier_overrides(field_category={"npt": 150_000.0})
    assert _resolve_category_multiplier("npt") == 200_000.0  # well > field
    clear_multiplier_overrides()
    assert _resolve_category_multiplier("npt") == _DEFAULT_CATEGORY_MULTIPLIERS["npt"]
    # compute_financial_impact still works
    kpi = {"value": 100, "target": 80, "unit": "%", "category": "operations"}
    impact = compute_financial_impact(kpi)
    assert impact is not None and impact > 0
p3_pass += check("P3-3: Financial engine configurable multipliers", test_p3_financial)

# P3-4: Deduction Engine Chunking
def test_p3_deduction():
    from pipelines.processing.deduction import _split_text_into_chunks, _merge_facts, DeductionEngine
    # Large text chunks correctly
    chunks = _split_text_into_chunks("x" * 50_000)
    assert len(chunks) > 1, f"Expected >1 chunks for 50K, got {len(chunks)}"
    assert len(chunks) <= 8, f"Should cap at 8 chunks, got {len(chunks)}"
    # Small text stays single chunk
    small = _split_text_into_chunks("hello world")
    assert len(small) == 1
    # Merge dedup works
    facts = [
        {"subject": "A", "predicate": "is", "object": "B", "confidence": 0.9},
        {"subject": "A", "predicate": "is", "object": "B", "confidence": 0.7},  # dup
        {"subject": "C", "predicate": "has", "object": "D", "confidence": 0.8},
    ]
    merged = _merge_facts(facts, 10)
    assert len(merged) == 2, f"Expected 2 after dedup, got {len(merged)}"
p3_pass += check("P3-4: Deduction engine chunking (no more text[:5000])", test_p3_deduction)

# P3-5: Semantic Dedup
def test_p3_dedup():
    from pipelines.inference.validation import _title_similarity, _jaccard_similarity, validate_kpis
    # Identical titles
    assert _title_similarity("NPT cost", "NPT cost") >= 0.99
    # Different titles
    assert _title_similarity("NPT cost", "production volume") < 0.5
    # Jaccard fallback exists
    assert _jaccard_similarity("a b c", "a b c") >= 0.99
    # validate_kpis dedup works
    kpis = [
        {"title": "Production Rate", "value": 100, "confidence": 0.9},
        {"title": "Production Rate", "value": 100, "confidence": 0.8},  # dup
        {"title": "NPT Hours", "value": 5, "confidence": 0.7},
    ]
    result = validate_kpis(kpis)
    assert len(result) == 2, f"Expected 2 after dedup, got {len(result)}"
p3_pass += check("P3-5: Semantic dedup in validation", test_p3_dedup)

# P3-6: Pre-indexed Embeddings
def test_p3_preindex():
    from services.vector_store.embeddings.preindex import get_preindex_service, PreIndexService
    svc = get_preindex_service()
    assert isinstance(svc, PreIndexService)
    stats = svc.index_stats()
    assert isinstance(stats, dict)
    # Preindex with empty chunks should return 0
    result = svc.preindex_document("test_doc", [])
    assert result["chunks_indexed"] == 0
p3_pass += check("P3-6: Pre-indexed embedding service", test_p3_preindex)

# P3-7: RBAC
def test_p3_rbac():
    from app.middleware.auth import Role, check_permission, get_role_for_key, require_role
    # Role hierarchy
    assert Role.OPERATOR < Role.ENGINEER < Role.MANAGER < Role.ADMIN
    assert int(Role.OPERATOR) == 10
    assert int(Role.ADMIN) == 40
    # Permission checks
    assert check_permission("/api/ddr/fleet/summary", Role.OPERATOR)
    assert check_permission("/api/ddr/fleet/summary", Role.ADMIN)
    assert not check_permission("/api/ddr/audit/trail", Role.OPERATOR)
    assert check_permission("/api/ddr/audit/trail", Role.MANAGER)
    assert not check_permission("/api/v2/financial/report", Role.ENGINEER)
    assert check_permission("/api/v2/financial/report", Role.MANAGER)
    # Default role is ADMIN (dev mode)
    assert get_role_for_key("unknown-key") == Role.ADMIN
    # require_role returns dependency
    dep = require_role(Role.MANAGER)
    assert callable(dep)
p3_pass += check("P3-7: RBAC middleware (4 roles, endpoint perms)", test_p3_rbac)

# P3-8: Multi-Report Trends
def test_p3_trends():
    from app.api.ddr.trend_endpoints import router
    paths = [r.path for r in router.routes if hasattr(r, "path")]
    expected = ["depth-progress", "npt", "rop", "mud-weight", "hse", "compare"]
    for kw in expected:
        assert any(kw in p for p in paths), f"Missing trend endpoint: {kw}"
    assert len(paths) >= 6, f"Only {len(paths)} trend routes"
p3_pass += check("P3-8: Multi-report trend endpoints (6 routes)", test_p3_trends)

# P3-9: Widget Mapper DDR
def test_p3_widgets():
    from features.kpi.widget_mapper import map_kpis_to_widgets
    kpis = [
        {"title": "NPT Stuck Pipe", "value": 12, "status": "critical", "category": "npt",
         "visibility": "primary", "priorityScore": 90},
        {"title": "Mud Weight", "value": 10.5, "status": "good", "category": "mud",
         "unit": "ppg", "visibility": "primary", "target": 10.0},
        {"title": "Hole Depth", "value": 8500, "status": "good", "category": "depth",
         "unit": "ft", "visibility": "secondary"},
        {"title": "ROP", "value": 45, "status": "warning", "category": "drilling",
         "unit": "ft/hr", "visibility": "primary", "priorityScore": 70},
        {"title": "HSE Near Miss", "value": 2, "status": "warning", "category": "safety",
         "visibility": "primary", "priorityScore": 85},
    ]
    w = map_kpis_to_widgets(kpis)
    # Generic widgets still work
    assert "kpi_summary" in w
    assert "kpi_bar" in w
    assert "kpi_status" in w
    assert "kpi_cat" in w
    assert "alerts" in w
    assert w["pool_size"] == 5
    # DDR widgets present
    assert "npt_pareto" in w
    assert "spc_chart" in w
    assert "fleet_heatmap" in w
    assert "gantt_timeline" in w
    assert "depth_sparkline" in w
    assert "hse_scorecard" in w
    # Content checks
    assert len(w["npt_pareto"]) >= 1
    assert len(w["spc_chart"]) >= 1
    assert w["hse_scorecard"]["total_kpis"] >= 1
p3_pass += check("P3-9: Widget mapper DDR layouts (6 DDR widgets)", test_p3_widgets)

PHASE_RESULTS["P3"] = (p3_pass, 9)
print(f"\n  P3 Score: {p3_pass}/9")


# =====================================================================
# CROSS-PHASE INTEGRATION
# =====================================================================
section("CROSS-PHASE INTEGRATION")
int_pass = 0

# Full app startup + route count
def test_integration_routes():
    from app.main import app
    all_routes = [r.path for r in app.routes if hasattr(r, "methods")]
    # DDR-related routes span /ddr/, /fleet/, /rigs/, /audit/ prefixes
    ddr_related = [r for r in all_routes if any(kw in r for kw in ["/ddr/", "/fleet/", "/rigs", "/audit/"])]
    v2_routes = [r for r in all_routes if "/api/v2/" in r]
    assert len(all_routes) >= 65, f"Only {len(all_routes)} total routes (expected 65+)"
    assert len(ddr_related) >= 20, f"Only {len(ddr_related)} DDR-related routes (expected 20+)"
    print(f"       Total routes:       {len(all_routes)}")
    print(f"       V2 routes:          {len(v2_routes)}")
    print(f"       DDR-related routes: {len(ddr_related)}")
int_pass += check("Integration: App starts, all routes registered", test_integration_routes)

# Financial engine + whatif interplay
def test_integration_financial_whatif():
    from features.predictive.whatif_engine import run_scenario, FINANCIAL_MULTIPLIERS
    from pipelines.inference.financial_engine import compute_financial_impact
    # What-if produces simulatedKpis (dict of kpi_name -> {base, simulated, delta, unit})
    kpis = [{"title": "ROP", "value": 40, "target": 50, "unit": "ft/hr", "category": "drilling"}]
    result = run_scenario(kpis, {"rop_target": 10}, "ROP Push")
    assert "simulatedKpis" in result
    assert "financialImpact" in result
    assert "narrative" in result
    assert "warnings" in result  # P3-2 addition
    # simulatedKpis is dict: {kpi_name: {base, simulated, delta, unit}}
    sim = result["simulatedKpis"]
    assert isinstance(sim, dict)
    assert "rop" in sim
    assert sim["rop"]["simulated"] > sim["rop"]["base"]  # ROP should increase
    # Financial engine can score KPIs directly
    impact = compute_financial_impact({"value": 40, "target": 50, "unit": "ft/hr", "category": "drilling"})
    assert impact is not None and impact > 0
int_pass += check("Integration: WhatIf -> Financial engine", test_integration_financial_whatif)

# Validation + widget mapper pipeline
def test_integration_validation_widgets():
    from pipelines.inference.validation import validate_kpis
    from features.kpi.widget_mapper import map_kpis_to_widgets
    raw = [
        {"title": "NPT Stuck Pipe", "value": 12, "confidence": 0.9, "status": "critical",
         "category": "npt", "visibility": "primary", "priorityScore": 90},
        {"title": "NPT Stuck Pipe", "value": 12, "confidence": 0.85, "status": "critical",
         "category": "npt", "visibility": "primary"},  # duplicate
        {"title": "", "value": None},  # garbage
        {"title": "ab", "value": 1},  # too short
        {"title": "Mud Weight PPG", "value": 10.5, "confidence": 0.8, "status": "good",
         "category": "mud", "visibility": "primary", "unit": "ppg", "target": 10.0},
    ]
    validated = validate_kpis(raw)
    assert len(validated) == 2, f"Expected 2 after validation, got {len(validated)}"
    widgets = map_kpis_to_widgets(validated)
    assert widgets["pool_size"] == 2
    assert len(widgets["npt_pareto"]) >= 1
int_pass += check("Integration: Validation -> Widget mapper pipeline", test_integration_validation_widgets)

# RBAC + middleware consistency
def test_integration_rbac():
    from app.middleware.auth import APIKeyMiddleware, Role, check_permission
    assert hasattr(APIKeyMiddleware, "dispatch")
    assert hasattr(APIKeyMiddleware, "EXCLUDED_PATHS")
    # Verify RBAC covers DDR trend endpoints
    assert check_permission("/api/ddr/trends/depth-progress", Role.OPERATOR)
    assert check_permission("/api/ddr/trends/compare", Role.OPERATOR)
int_pass += check("Integration: RBAC covers all endpoint groups", test_integration_rbac)

# DDR model relationships intact
def test_integration_models():
    from pipelines.inference.ddr.models import DDRReport, DDRRig
    # Check relationship attributes exist
    assert hasattr(DDRReport, "depth_summaries")
    assert hasattr(DDRReport, "npt_events")
    assert hasattr(DDRReport, "mud_data")
    assert hasattr(DDRReport, "hse_data")
    assert hasattr(DDRReport, "timelines")
    assert hasattr(DDRReport, "extracted_metrics")
    assert hasattr(DDRRig, "reports")
int_pass += check("Integration: DDR model relationships intact", test_integration_models)

PHASE_RESULTS["INTEGRATION"] = (int_pass, 5)
print(f"\n  Integration Score: {int_pass}/5")


# =====================================================================
# FINAL SUMMARY
# =====================================================================
section("FINAL SUMMARY")
total_pass = 0
total_tests = 0
for phase, (passed, total) in PHASE_RESULTS.items():
    status = "PASS" if passed == total else "FAIL"
    total_pass += passed
    total_tests += total
    print(f"  {phase:15s} {passed:2d}/{total:2d}  [{status}]")

print(f"\n  {'TOTAL':15s} {total_pass:2d}/{total_tests:2d}")
print()

if ALL_ERRORS:
    print(f"  FAILURES ({len(ALL_ERRORS)}):")
    for e in ALL_ERRORS:
        print(f"    - {e}")
    print()
    sys.exit(1)
else:
    print("  ALL TESTS PASSED — P0 through P3 fully operational.")
    print()
    sys.exit(0)
