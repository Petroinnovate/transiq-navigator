"""End-to-end system test — simulates frontend data flows."""
import requests
import json

BASE = "http://localhost:8001"
h = {"X-API-Key": "transiq-dev-key-change-in-production-2026"}
passes = 0
fails = 0

def check(label, resp, expect_status=200):
    global passes, fails
    ok = resp.status_code == expect_status
    mark = "PASS" if ok else "FAIL"
    if ok:
        passes += 1
    else:
        fails += 1
    print(f"  [{mark}] {resp.status_code} {label}")
    return ok

print("=" * 60)
print("E2E TEST 1: Auth Flow")
print("=" * 60)
r = requests.post(f"{BASE}/auth/register", json={"email": "e2e@test.com", "password": "TestPass123!"}, headers=h)
# 200/201 new user, 400 already exists — both OK
if r.status_code in (200, 201, 400):
    passes += 1
    print(f"  [PASS] {r.status_code} Register")
else:
    fails += 1
    print(f"  [FAIL] {r.status_code} Register")

r = requests.post(f"{BASE}/auth/login", json={"email": "e2e@test.com", "password": "TestPass123!"}, headers=h)
check("Login", r)
if r.status_code == 200:
    token = r.json()["access_token"]
    ah = {"Authorization": f"Bearer {token}"}
    r2 = requests.get(f"{BASE}/auth/me", headers=ah)
    check("Auth/me (JWT)", r2)
    body = r2.json()
    assert "email" in body, f"Missing email field: {body.keys()}"

print()
print("=" * 60)
print("E2E TEST 2: Fleet Dashboard Flow")
print("=" * 60)
r = requests.get(f"{BASE}/api/v2/fleet/summary", headers=h)
check("Fleet Summary", r)
d = r.json()
# Verify KPIValue shape
assert isinstance(d.get("avg_rop_ft_hr"), dict), "avg_rop_ft_hr should be dict (KPIValue)"
assert "value" in d["avg_rop_ft_hr"], "avg_rop_ft_hr should have .value"
assert "report_date" in d, "Should have report_date, not date"
print(f"         rigs={d['total_rigs']} rop={d['avg_rop_ft_hr']['value']}")

r = requests.get(f"{BASE}/api/v2/fleet/npt-pareto", headers=h)
check("Fleet NPT Pareto", r)
r = requests.get(f"{BASE}/api/v2/fleet/spc/rop", headers=h)
check("Fleet SPC", r)
r = requests.get(f"{BASE}/api/v2/fleet/top-performers", headers=h)
check("Fleet Top Performers", r)
r = requests.get(f"{BASE}/api/v2/fleet/heatmap", headers=h)
check("Fleet Heatmap", r)

print()
print("=" * 60)
print("E2E TEST 3: Rig Detail Flow")
print("=" * 60)
r = requests.get(f"{BASE}/api/v2/rigs", headers=h)
check("Rig List", r)
rigs = r.json().get("rigs", [])
assert len(rigs) > 0, "Should have at least 1 rig"
rig = rigs[0]
rid = rig["rig_id"]
# Verify RigSummary shape
assert "rig_id" in rig, "Should have rig_id"
assert "well_id" in rig, "Should have well_id"
assert isinstance(rig.get("rop_ft_hr"), dict), "rop_ft_hr should be KPIValue dict"
print(f"         count={len(rigs)} first={rid}")

r = requests.get(f"{BASE}/api/v2/rigs/{rid}", headers=h)
check("Rig Detail", r)
rd = r.json()
# Verify RigDetail shape
assert "identity" in rd, "Should have identity"
assert "depth_summary" in rd, "Should have depth_summary"
assert "formation_tops" in rd, "Should have formation_tops"
assert rd["identity"]["rig_id"] == rid, "identity.rig_id should match"
ds = rd["depth_summary"]
assert "current_md_ft" in ds, "depth_summary should have current_md_ft"
assert isinstance(ds["current_md_ft"], dict), "current_md_ft should be KPIValue"
print(f"         identity.well_id={rd['identity']['well_id']} md={ds['current_md_ft']['value']}")

r = requests.get(f"{BASE}/api/v2/rigs/{rid}/timeline", headers=h)
check("Rig Timeline", r)
r = requests.get(f"{BASE}/api/v2/rigs/{rid}/npt", headers=h)
check("Rig NPT", r)
r = requests.get(f"{BASE}/api/v2/rigs/{rid}/survey", headers=h)
check("Rig Survey", r)
r = requests.get(f"{BASE}/api/v2/rigs/{rid}/mud", headers=h)
check("Rig Mud", r)
r = requests.get(f"{BASE}/api/v2/rigs/{rid}/personnel", headers=h)
check("Rig Personnel", r)
r = requests.get(f"{BASE}/api/v2/rigs/{rid}/bha", headers=h)
check("Rig BHA", r)
r = requests.get(f"{BASE}/api/v2/rigs/{rid}/hse", headers=h)
check("Rig HSE", r)
r = requests.get(f"{BASE}/api/v2/rigs/{rid}/foreman-remarks", headers=h)
check("Rig Foreman Remarks", r)
r = requests.get(f"{BASE}/api/v2/rigs/{rid}/kpis", headers=h)
check("Rig KPIs", r)

# Audit trail
r = requests.get(f"{BASE}/api/v2/audit/{rid}/all", headers=h)
check("Audit Trail (all)", r)
r = requests.get(f"{BASE}/api/v2/audit/changelog", headers=h)
check("Audit Changelog", r)

print()
print("=" * 60)
print("E2E TEST 4: Dashboard + Intelligence Flow")
print("=" * 60)
r = requests.get(f"{BASE}/api/v2/dashboard/latest", headers=h)
check("Dashboard Latest", r)
d = r.json()
assert "meta" in d and "sixSigma" in d and "kpis" in d, f"Missing dashboard keys: {d.keys()}"

r = requests.get(f"{BASE}/api/v2/intelligence/dashboard/test-kpi", headers=h)
check("Intel Dashboard", r)
r = requests.get(f"{BASE}/api/v2/intelligence/impact-network/test-kpi", headers=h)
check("Impact Network", r)
r = requests.get(f"{BASE}/api/v2/intelligence/unified-recommendations/test-entity", headers=h)
check("Recommendations", r)
r = requests.get(f"{BASE}/api/v2/intelligence/graph-network/test-entity", headers=h)
check("Graph Network", r)
r = requests.get(f"{BASE}/api/v2/intelligence/cross-engine-analysis/test-entity", headers=h)
check("Cross-Engine Analysis", r)
r = requests.get(f"{BASE}/api/v2/intelligence/scenario/test-entity", headers=h)
check("Scenario", r)

# Intelligence POST endpoints
r = requests.post(f"{BASE}/api/v2/intelligence/enrich-facts", json={
    "facts": [{"subject": "pump", "predicate": "caused", "object": "failure", "confidence": 0.9}]
}, headers=h)
check("Enrich Facts", r)

print()
print("=" * 60)
print("E2E TEST 5: GraphRAG Flow")
print("=" * 60)
r = requests.post(f"{BASE}/api/v2/graph/entities/search", json={"query": "test", "limit": 5}, headers=h)
check("Entity Search", r)
r = requests.get(f"{BASE}/api/v2/graph/entities/test-id/related", headers=h)
check("Related Entities", r)
r = requests.post(f"{BASE}/api/v2/graph/relationships/search", json={"query": "test", "limit": 5}, headers=h)
check("Relationship Search", r)
r = requests.get(f"{BASE}/api/v2/graph/relationships/test-id", headers=h)
check("Entity Relationships", r)

print()
print("=" * 60)
print("E2E TEST 6: Observability Flow")
print("=" * 60)
for ep in ["health", "models", "features", "predictions", "drift"]:
    r = requests.get(f"{BASE}/api/v2/observability/{ep}", headers=h)
    check(f"Observability {ep}", r)

print()
print("=" * 60)
print("E2E TEST 7: DDR Trends")
print("=" * 60)
for m in ["rop", "npt", "depth-progress", "mud-weight", "hse"]:
    r = requests.get(f"{BASE}/api/ddr/trends/{m}", headers=h)
    check(f"Trend {m}", r)

print()
print("=" * 60)
print("E2E TEST 8: Six Sigma + Confusion Matrix")
print("=" * 60)
r = requests.post(f"{BASE}/api/v2/six-sigma/analyze", json={
    "data": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
    "usl": 12.0,
    "lsl": 0.0,
}, headers=h)
check("Six Sigma Analyze", r)

r = requests.post(f"{BASE}/api/v2/confusion-matrix", json={
    "y_true": [0, 1, 1, 0, 1],
    "y_pred": [0, 1, 0, 0, 1],
    "normalize": False,
    "use_case": "binary",
}, headers=h)
check("Confusion Matrix", r)

print()
print("=" * 60)
print("E2E TEST 9: DDR Ingestion")
print("=" * 60)
r = requests.get(f"{BASE}/api/v2/ddr/reports", headers=h)
check("DDR Reports List", r)
reports = r.json()
print(f"         reports count: {len(reports) if isinstance(reports, list) else reports}")

print()
print("=" * 60)
print("E2E TEST 10: Root Health")
print("=" * 60)
r = requests.get(f"{BASE}/health")
check("Root /health", r)
assert r.json()["status"] == "healthy"

print()
print("=" * 60)
print(f"RESULTS: {passes} PASS, {fails} FAIL out of {passes + fails} tests")
print("=" * 60)
