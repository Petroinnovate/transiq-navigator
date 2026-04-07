"""
Live HTTP endpoint smoke test — hit every major route against the running server.
"""
import urllib.request
import json
import sys

BASE = "http://127.0.0.1:8099"
results = []


def hit(method, path, expect_codes=(200,), label=None, body_data=None):
    url = BASE + path
    tag = label or path
    try:
        if body_data:
            data = json.dumps(body_data).encode("utf-8")
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Content-Type", "application/json")
        else:
            req = urllib.request.Request(url, method=method)
        resp = urllib.request.urlopen(req, timeout=15)
        code = resp.getcode()
        body = json.loads(resp.read().decode())
        ok = code in expect_codes
        results.append((tag, code, ok))
        return body
    except urllib.error.HTTPError as e:
        code = e.code
        ok = code in expect_codes
        results.append((tag, code, ok))
        return None
    except Exception as e:
        results.append((tag, str(e), False))
        return None


print("=" * 70)
print("  LIVE HTTP ENDPOINT SMOKE TEST")
print("=" * 70)
print()

# ---- Root & Health ----
print("--- Root & Health ---")
body = hit("GET", "/")
if body:
    print("  Root: name=%s, version=%s" % (body.get("name"), body.get("version")))

body = hit("GET", "/health")
if body:
    print("  Health: status=%s" % body.get("status"))

body = hit("GET", "/api/v2/health", label="/api/v2/health", expect_codes=(200, 503))
if body:
    print("  V2 Health: status=%s" % body.get("status"))

# ---- OpenAPI docs ----
print("--- Docs ---")
hit("GET", "/openapi.json", label="OpenAPI spec")

# ---- Dashboard ----
print("--- Dashboard ---")
hit("GET", "/api/v2/dashboard/latest", label="Dashboard latest", expect_codes=(200, 404, 500))

# ---- Fleet endpoints (P2) ----
print("--- Fleet (P2) ---")
hit("GET", "/api/v2/fleet/summary", label="Fleet summary", expect_codes=(200,))
hit("GET", "/api/v2/fleet/npt-pareto", label="Fleet NPT Pareto", expect_codes=(200,))
hit("GET", "/api/v2/fleet/spc/rop", label="Fleet SPC ROP", expect_codes=(200, 404))

# ---- Rig endpoints (P2) ----
print("--- Rigs (P2) ---")
hit("GET", "/api/v2/rigs", label="Rig list", expect_codes=(200,))
hit("GET", "/api/v2/rigs/test-rig", label="Rig detail", expect_codes=(200, 404))
hit("GET", "/api/v2/rigs/test-rig/timeline", label="Rig timeline", expect_codes=(200, 404))
hit("GET", "/api/v2/rigs/test-rig/npt", label="Rig NPT", expect_codes=(200, 404))
hit("GET", "/api/v2/rigs/test-rig/survey", label="Rig survey", expect_codes=(200, 404))
hit("GET", "/api/v2/rigs/test-rig/mud", label="Rig mud", expect_codes=(200, 404))
hit("GET", "/api/v2/rigs/test-rig/personnel", label="Rig personnel", expect_codes=(200, 404))
hit("GET", "/api/v2/rigs/test-rig/bha", label="Rig BHA", expect_codes=(200, 404))
hit("GET", "/api/v2/rigs/test-rig/hse", label="Rig HSE", expect_codes=(200, 404))
hit("GET", "/api/v2/rigs/test-rig/foreman-remarks", label="Rig foreman", expect_codes=(200, 404))

# ---- Audit (P2) ----
print("--- Audit (P2) ---")
hit("GET", "/api/v2/audit/test-rig/depth", label="Audit trail", expect_codes=(200, 404))

# ---- DDR Core (P1/P2) ----
print("--- DDR Core ---")
hit("POST", "/api/v2/ddr/spc/fleet", label="DDR SPC Fleet (POST)",
    expect_codes=(200, 422),
    body_data={"rig_ids": ["rig1"], "metric": "rop", "values": {}})

# ---- Trend endpoints (P3) ----
print("--- Trends (P3) ---")
hit("GET", "/api/ddr/trends/depth-progress", label="Trend depth-progress", expect_codes=(200,))
hit("GET", "/api/ddr/trends/npt", label="Trend NPT", expect_codes=(200,))
hit("GET", "/api/ddr/trends/rop", label="Trend ROP", expect_codes=(200,))
hit("GET", "/api/ddr/trends/mud-weight", label="Trend mud-weight", expect_codes=(200,))
hit("GET", "/api/ddr/trends/hse", label="Trend HSE", expect_codes=(200,))
hit("GET", "/api/ddr/trends/compare?rig_ids=rig1,rig2", label="Trend compare", expect_codes=(200,))

# ---- Intelligence (P0) ----
print("--- Intelligence (P0) ---")
hit("GET", "/api/v2/intelligence/status", label="Intelligence status", expect_codes=(200,))

# ---- Summary ----
print()
print("=" * 70)
print("  RESULTS")
print("=" * 70)
passed = sum(1 for _, _, ok in results if ok)
failed = [(t, c) for t, c, ok in results if not ok]
for tag, code, ok in results:
    status = "PASS" if ok else "FAIL"
    print("  [%s] %4s  %s" % (status, code, tag))

print()
print("  HTTP Smoke Test: %d/%d endpoints responding correctly" % (passed, len(results)))
if failed:
    print("  FAILURES: %d" % len(failed))
    for t, c in failed:
        print("    - %s: %s" % (t, c))
    sys.exit(1)
else:
    print("  ALL ENDPOINTS LIVE AND RESPONDING.")
    sys.exit(0)
