"""Test 3-tier fallback chain with domain-aware heuristic dashboard."""
import sys
import json
import sqlite3
import os
sys.path.insert(0, '.')
from pipelines.processing.dashboard import DashboardGenerator

# ═══════════════════════════════════════════════════════════════════
# Test 1: Generic (financial) domain — deterministic extraction
# ═══════════════════════════════════════════════════════════════════
financial_chunks = [
    'Q3 2024 Financial Summary\nRevenue: $12.5M\nNet Income: $3.2M\nOperating Costs: $8.1M\nGross Margin: 74.3%',
    'Production Metrics\nEfficiency: 94.5%\nDefect Rate: 2.3%\nThroughput: 1,250 units per day\nDowntime: 4.2%',
    'Budget Analysis\nTotal Budget: $15M\nActual Spend: $13.8M\nVariance: 8.0%\nROI: 22.5%',
]

print("=== Test 1: Generic financial extraction ===")
result = DashboardGenerator._generate_heuristic_dashboard(financial_chunks, 'Q3_Report.pdf')
db = result['dashboard']
print(f"Title: {db['title']}")
print(f"KPIs: {len(db['kpis'])}, Charts: {len(db['charts'])}, Tables: {len(db['tables'])}")
assert len(db['kpis']) > 0
assert len(db['charts']) > 0
print("PASS")

# ═══════════════════════════════════════════════════════════════════
# Test 2: Drilling domain — heuristic extraction
# ═══════════════════════════════════════════════════════════════════
drilling_chunks = [
    'Daily Drilling Report — Rig: 088TE  Well: QTIF-790\nObjective: Development Drilling\nCurrent Depth: 23,695 ft\nROP: 12.4 ft/hr\nNPT: 23.0%',
    'Mud Weight: 92 pcf, CaCl brine\nWOB: 25 klbs\nTorque: 12,500 ft-lbs\nStandpipe Pressure: 3200 psi',
    '06:00-09:00 Circulating and conditioning hole. MW 92 PCF\n09:00-12:00 Drilling ahead at 150 ft\n16:00-19:00 Stuck pipe — differential pressure. Jarring operations.',
    'BHA configuration: 8-1/2" bit, MWD, RSS, 6-3/4" collars\nCasing: 9-5/8" set at 18,500 ft\nDays since spud: 115\nDaily footage: 250 ft',
]

print("\n=== Test 2: Drilling domain detection ===")
domain = DashboardGenerator._detect_domain(drilling_chunks)
print(f"Detected domain: {domain}")
assert domain == "drilling", f"FAIL: Expected 'drilling', got '{domain}'"

print("\n=== Test 3: Drilling metric extraction ===")
data = DashboardGenerator._extract_drilling_metrics(drilling_chunks)
print(f"Extracted: {json.dumps(data, indent=2, default=str)}")
assert data.get("rop") == 12.4, f"FAIL: ROP={data.get('rop')}"
assert data.get("npt") == 23.0, f"FAIL: NPT={data.get('npt')}"
assert data.get("depth") == 23695.0, f"FAIL: Depth={data.get('depth')}"
assert data.get("mud_weight") == 92.0, f"FAIL: MW={data.get('mud_weight')}"
assert data.get("wob") == 25.0, f"FAIL: WOB={data.get('wob')}"
assert data.get("rig_id") == "088TE", f"FAIL: rig_id={data.get('rig_id')}"
print("All drilling metrics extracted correctly")

print("\n=== Test 4: generate_heuristic_dashboard (drilling) ===")
result = DashboardGenerator._generate_heuristic_dashboard(drilling_chunks, 'DDR_088TE.pdf')
db = result['dashboard']
print(f"Title: {db['title']}")
print(f"KPIs: {len(db['kpis'])}")
for kpi in db['kpis']:
    print(f"  {kpi['title']}: {kpi['value']} ({kpi['change']})")
print(f"Charts: {len(db['charts'])}")
for c in db['charts']:
    print(f"  {c['title']} ({c['type']})")
print(f"Tables: {len(db['tables'])}")
assert len(db['kpis']) >= 5, f"FAIL: Only {len(db['kpis'])} KPIs"
assert "Operational Summary" in db['title'], f"FAIL: Title={db['title']}"
# Check NPT is flagged
npt_kpi = next((k for k in db['kpis'] if k['title'] == 'NPT'), None)
assert npt_kpi is not None, "FAIL: NPT KPI missing"
assert npt_kpi['changeType'] == 'negative', f"FAIL: NPT should be negative, got {npt_kpi['changeType']}"
print("PASS — drilling dashboard is domain-aware")

# ═══════════════════════════════════════════════════════════════════
# Test 5: _is_empty_dashboard
# ═══════════════════════════════════════════════════════════════════
print("\n=== Test 5: _is_empty_dashboard ===")
empty = {'dashboard': {'kpis': [], 'charts': [], 'tables': []}}
nonempty = {'dashboard': {'kpis': [{'id': 'x'}], 'charts': [], 'tables': []}}
assert DashboardGenerator._is_empty_dashboard(empty) == True
assert DashboardGenerator._is_empty_dashboard(nonempty) == False
print("PASS")

# ═══════════════════════════════════════════════════════════════════
# Test 6: Cache layer
# ═══════════════════════════════════════════════════════════════════
print("\n=== Test 6: Cache HIT / MISS ===")
from core.config.settings import settings
db_path = settings.DATABASE_URL.replace('sqlite:///', '')
test_doc_id = "__test_cache_doc__"
cached_dashboard = {
    "dashboard": {
        "title": "CACHED Dashboard",
        "kpis": [{"id": "kpi-cached-1", "title": "Cached Revenue", "value": "$999M"}],
        "charts": [{"id": "chart-cached-1", "type": "bar", "title": "Cached Chart", "data": [{"name": "X", "value": 1}]}],
        "tables": [],
    }
}
conn = sqlite3.connect(db_path)
conn.execute(
    "INSERT OR REPLACE INTO documents (id, user_id, metadata, dashboard_data, status, created_at, updated_at) "
    "VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
    (test_doc_id, "test", "{}", json.dumps(cached_dashboard), "completed"),
)
conn.commit()
conn.close()

cache_result = DashboardGenerator._get_cached_dashboard(test_doc_id)
assert cache_result is not None
assert cache_result['dashboard']['title'] == "CACHED Dashboard"
print("Cache HIT: PASS")

miss = DashboardGenerator._get_cached_dashboard(None)
assert miss is None
miss2 = DashboardGenerator._get_cached_dashboard("nonexistent_doc_999")
assert miss2 is None
print("Cache MISS: PASS")

# ═══════════════════════════════════════════════════════════════════
# Test 7: Full 3-tier chain
# ═══════════════════════════════════════════════════════════════════
print("\n=== Test 7: 3-tier fallback chain ===")
gen = DashboardGenerator.__new__(DashboardGenerator)

# Tier 1: cache
r = gen._get_fallback_dashboard('test.pdf', 'error', chunks=drilling_chunks, doc_id=test_doc_id)
assert r['dashboard']['title'] == "CACHED Dashboard"
print("Tier 1 (cache): PASS")

# Tier 2: heuristic (drilling)
r = gen._get_fallback_dashboard('DDR_088TE.pdf', 'error', chunks=drilling_chunks, doc_id=None)
assert "Operational Summary" in r['dashboard']['title']
assert any(k['title'] == 'ROP' for k in r['dashboard']['kpis'])
print(f"Tier 2 (drilling heuristic): {len(r['dashboard']['kpis'])} KPIs — PASS")

# Tier 2: heuristic (general)
r = gen._get_fallback_dashboard('Q3.pdf', 'error', chunks=financial_chunks, doc_id=None)
assert len(r['dashboard']['kpis']) > 0
print(f"Tier 2 (general heuristic): {len(r['dashboard']['kpis'])} KPIs — PASS")

# Tier 3: last resort (no chunks)
r = gen._get_fallback_dashboard('test.pdf', 'error', chunks=None, doc_id=None)
assert len(r['dashboard']['kpis']) >= 1
print(f"Tier 3 (last resort): {r['dashboard']['kpis'][0]['title']} — PASS")

# ═══════════════════════════════════════════════════════════════════
# Test 8: Empty cached dashboard skipped
# ═══════════════════════════════════════════════════════════════════
print("\n=== Test 8: Empty cache filtered ===")
empty_cached = {"dashboard": {"title": "Empty", "kpis": [], "charts": [], "tables": []}}
conn = sqlite3.connect(db_path)
conn.execute("UPDATE documents SET dashboard_data = ? WHERE id = ?", (json.dumps(empty_cached), test_doc_id))
conn.commit()
conn.close()
assert DashboardGenerator._get_cached_dashboard(test_doc_id) is None
print("PASS")

# ═══════════════════════════════════════════════════════════════════
# Test 9: Cache WRITE on valid AI result
# ═══════════════════════════════════════════════════════════════════
print("\n=== Test 9: Cache WRITE ===")
write_doc_id = "__test_cache_write__"
# Seed an empty document row
conn = sqlite3.connect(db_path)
conn.execute(
    "INSERT OR REPLACE INTO documents (id, user_id, metadata, dashboard_data, status, created_at, updated_at) "
    "VALUES (?, ?, ?, NULL, ?, datetime('now'), datetime('now'))",
    (write_doc_id, "test", "{}", "processing"),
)
conn.commit()
conn.close()

# Verify cache miss initially
assert DashboardGenerator._get_cached_dashboard(write_doc_id) is None
print("Initial cache miss: OK")

# Write a valid dashboard
valid_dashboard = {
    "dashboard": {
        "title": "Written Dashboard",
        "kpis": [{"id": "k1", "title": "Revenue", "value": "$1M"}],
        "charts": [{"id": "c1", "type": "bar", "title": "Chart", "data": []}],
        "tables": [],
    }
}
DashboardGenerator._cache_dashboard(write_doc_id, valid_dashboard)

# Verify cache hit
cached = DashboardGenerator._get_cached_dashboard(write_doc_id)
assert cached is not None, "FAIL: Written dashboard not found in cache"
assert cached['dashboard']['title'] == "Written Dashboard"
print("Cache write + read back: PASS")

# Verify empty dashboard NOT written (should not overwrite)
empty_dashboard = {"dashboard": {"kpis": [], "charts": [], "tables": []}}
DashboardGenerator._cache_dashboard(write_doc_id, empty_dashboard)
cached2 = DashboardGenerator._get_cached_dashboard(write_doc_id)
assert cached2 is not None, "FAIL: Empty write should not have overwritten valid cache"
assert cached2['dashboard']['title'] == "Written Dashboard"
print("Empty dashboard write skipped: PASS")

# Verify None doc_id is safe
DashboardGenerator._cache_dashboard(None, valid_dashboard)  # Should not raise
print("None doc_id write safe: PASS")

# Cleanup
conn = sqlite3.connect(db_path)
conn.execute("DELETE FROM documents WHERE id IN (?, ?)", (test_doc_id, write_doc_id))
conn.commit()
conn.close()

# ═══════════════════════════════════════════════════════════════════
# Test 10: _validate_dashboard contract gate
# ═══════════════════════════════════════════════════════════════════
print("\n=== Test 10: _validate_dashboard contract ===")

def validate_contract(d):
    """Assert the dashboard contract: kpis and charts must be non-empty."""
    assert "dashboard" in d, "FAIL: missing 'dashboard' wrapper"
    db = d["dashboard"]
    assert "kpis" in db and len(db["kpis"]) > 0, f"FAIL: kpis empty ({db.get('kpis')})"
    assert "charts" in db and len(db["charts"]) > 0, f"FAIL: charts empty ({db.get('charts')})"
    return True

# Case A: Already valid — pass through unchanged
valid = {"dashboard": {"kpis": [{"id": "k1"}], "charts": [{"id": "c1"}]}}
result = DashboardGenerator._validate_dashboard(valid)
assert validate_contract(result)
assert result["dashboard"]["kpis"][0]["id"] == "k1"
print("  Valid dashboard passed through: PASS")

# Case B: Missing charts — injected
no_charts = {"dashboard": {"kpis": [{"id": "k1", "title": "Revenue"}], "charts": []}}
result = DashboardGenerator._validate_dashboard(no_charts)
assert validate_contract(result)
assert result["dashboard"]["charts"][0]["id"] == "chart-validate-1"
print("  Missing charts injected: PASS")

# Case C: Missing kpis — injected
no_kpis = {"dashboard": {"kpis": [], "charts": [{"id": "c1"}]}}
result = DashboardGenerator._validate_dashboard(no_kpis)
assert validate_contract(result)
assert result["dashboard"]["kpis"][0]["id"] == "kpi-validate-1"
print("  Missing kpis injected: PASS")

# Case D: Completely empty — both injected
empty = {"dashboard": {}}
result = DashboardGenerator._validate_dashboard(empty)
assert validate_contract(result)
print("  Empty dashboard filled: PASS")

# Case E: None input — handled gracefully
result = DashboardGenerator._validate_dashboard(None)
assert validate_contract(result)
print("  None input handled: PASS")

# Case F: Last-resort fallback passes contract
gen = DashboardGenerator.__new__(DashboardGenerator)
last_resort = gen._get_fallback_dashboard('test.pdf', 'error', chunks=None, doc_id=None)
validated = DashboardGenerator._validate_dashboard(last_resort)
assert validate_contract(validated)
print("  Last-resort + validate: PASS")

# Case G: Drilling heuristic passes contract
drilling_result = DashboardGenerator._generate_heuristic_dashboard(drilling_chunks, 'DDR.pdf')
validated = DashboardGenerator._validate_dashboard(drilling_result)
assert validate_contract(validated)
print("  Drilling heuristic + validate: PASS")

# Case H: Generic heuristic passes contract
generic_result = DashboardGenerator._generate_heuristic_dashboard(financial_chunks, 'Q3.pdf')
validated = DashboardGenerator._validate_dashboard(generic_result)
assert validate_contract(validated)
print("  Generic heuristic + validate: PASS")

print("\n" + "=" * 60)
print("ALL 10 TESTS PASSED — validate_dashboard contract verified")
print("ALL 9 TESTS PASSED — Cache read/write + domain-aware fallback validated")
