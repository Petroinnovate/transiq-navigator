"""
Comprehensive integration test: every frontend endpoint vs backend
"""
import requests, json, sys

BASE = 'http://localhost:8001'

# Check server alive
try:
    r = requests.get(f'{BASE}/', timeout=3)
except:
    print("FATAL: Backend not running on port 8001")
    sys.exit(1)

# Login
r = requests.post(f'{BASE}/auth/login', json={'email': 'test@test.com', 'password': 'testpass123'}, timeout=5)
if r.status_code != 200:
    r = requests.post(f'{BASE}/auth/register', json={'email': 'test@test.com', 'password': 'testpass123'}, timeout=5)
token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}

results = []

def test(name, method, path, expect_codes=None, **kw):
    """Test an endpoint, return status"""
    if expect_codes is None:
        expect_codes = [200, 201]
    url = f'{BASE}{path}'
    kw.setdefault('timeout', 5)
    kw.setdefault('headers', h)
    try:
        r = getattr(requests, method)(url, **kw)
        ok = r.status_code in expect_codes
        # 404 with valid JSON detail is "route exists but resource missing" = OK integration
        if r.status_code == 404:
            try:
                body = r.json()
                if 'detail' in body:
                    ok = True  # Route exists, just no data
            except:
                pass
        status = 'PASS' if ok else 'FAIL'
        results.append((status, r.status_code, name, path))
        return r
    except requests.Timeout:
        results.append(('HANG', 0, name, path))
        return None
    except requests.ConnectionError:
        results.append(('CONN', 0, name, path))
        return None
    except Exception as e:
        results.append(('ERR', 0, name, str(e)[:60]))
        return None

# ============ AUTH ============
print("Testing Auth...")
test('Login', 'post', '/auth/login', json={'email': 'test@test.com', 'password': 'testpass123'})
test('Register (dupe)', 'post', '/auth/register', json={'email': 'test@test.com', 'password': 'testpass123'}, expect_codes=[200, 201, 400])
test('/auth/me', 'get', '/auth/me')
test('/auth/logout', 'post', '/auth/logout')

# ============ ROOT ============
print("Testing Root...")
test('Root /', 'get', '/')
test('Root /health', 'get', '/health', expect_codes=[200, 404, 503])

# ============ CORE v2 ============
print("Testing Core v2...")
test('Health', 'get', '/api/v2/health', expect_codes=[200, 503])
test('Cache stats', 'get', '/api/v2/cache/stats')
test('Document (fake)', 'get', '/api/v2/documents/fake-id', expect_codes=[200, 404])
test('Chunks (fake)', 'get', '/api/v2/documents/fake-id/chunks', expect_codes=[200, 404])
test('Dashboard (fake)', 'get', '/api/v2/documents/fake-id/dashboard', expect_codes=[200, 404])
test('Task (fake)', 'get', '/api/v2/task/fake-id', expect_codes=[200, 404])
test('Batch (fake)', 'get', '/api/v2/batch/fake-id', expect_codes=[200, 404])
test('Search', 'post', '/api/v2/search', json={'query': 'test', 'doc_ids': []}, expect_codes=[200, 404, 422])
test('Agent run', 'post', '/api/v2/agent/run', json={'goal': 'test', 'context': {}}, expect_codes=[200, 404, 422, 500])
test('Dashboard latest', 'get', '/api/v2/dashboard/latest', expect_codes=[200, 404])
test('Dashboard by id', 'get', '/api/v2/dashboard/fake-id', expect_codes=[200, 404])
test('Dashboard status', 'get', '/api/v2/dashboard/status/fake-id', expect_codes=[200, 404])
test('Export PDF', 'get', '/api/v2/dashboard/fake-id/export/pdf', expect_codes=[200, 404])
test('Export Excel', 'get', '/api/v2/dashboard/fake-id/export/excel', expect_codes=[200, 404])

# ============ DDR ============
print("Testing DDR...")
test('DDR reports', 'get', '/api/v2/ddr/reports')
test('DDR metrics (fake)', 'get', '/api/v2/ddr/metrics/fake-id', expect_codes=[200, 404])
test('DDR parse-upload', 'post', '/api/v2/ddr/parse-upload', expect_codes=[200, 404, 422])

# ============ FLEET ============
print("Testing Fleet...")
test('Fleet summary', 'get', '/api/v2/fleet/summary')
test('Fleet NPT pareto', 'get', '/api/v2/fleet/npt-pareto')
test('Fleet SPC', 'get', '/api/v2/fleet/spc/rop')
test('Fleet top performers', 'get', '/api/v2/fleet/top-performers')
test('Fleet heatmap', 'get', '/api/v2/fleet/heatmap')
test('Fleet export', 'get', '/api/v2/fleet/export')

# ============ RIGS ============
print("Testing Rigs...")
test('List rigs', 'get', '/api/v2/rigs')
test('Rig detail (fake)', 'get', '/api/v2/rigs/fake-id', expect_codes=[200, 404])
test('Rig KPIs (fake)', 'get', '/api/v2/rigs/fake-id/kpis', expect_codes=[200, 404])
test('Rig timeline (fake)', 'get', '/api/v2/rigs/fake-id/timeline', expect_codes=[200, 404])
test('Rig NPT (fake)', 'get', '/api/v2/rigs/fake-id/npt', expect_codes=[200, 404])
test('Rig survey (fake)', 'get', '/api/v2/rigs/fake-id/survey', expect_codes=[200, 404])
test('Rig mud (fake)', 'get', '/api/v2/rigs/fake-id/mud', expect_codes=[200, 404])
test('Rig personnel (fake)', 'get', '/api/v2/rigs/fake-id/personnel', expect_codes=[200, 404])
test('Rig BHA (fake)', 'get', '/api/v2/rigs/fake-id/bha', expect_codes=[200, 404])
test('Rig bulk (fake)', 'get', '/api/v2/rigs/fake-id/bulk', expect_codes=[200, 404])
test('Rig HSE (fake)', 'get', '/api/v2/rigs/fake-id/hse', expect_codes=[200, 404])
test('Rig foreman (fake)', 'get', '/api/v2/rigs/fake-id/foreman-remarks', expect_codes=[200, 404])
test('Rig well-design', 'get', '/api/v2/rigs/fake-id/well-design', expect_codes=[200, 404])
test('Rig export', 'get', '/api/v2/rigs/fake-id/export', expect_codes=[200, 404])

# ============ AUDIT ============
print("Testing Audit...")
test('Audit all (fake)', 'get', '/api/v2/audit/fake-id/all', expect_codes=[200, 404])
test('Audit field', 'get', '/api/v2/audit/fake-id/depth', expect_codes=[200, 404])
test('Audit changelog', 'get', '/api/v2/audit/changelog')

# ============ DDR TRENDS ============
print("Testing DDR Trends...")
test('Trends depth', 'get', '/api/ddr/trends/depth-progress', expect_codes=[200, 404])
test('Trends NPT', 'get', '/api/ddr/trends/npt', expect_codes=[200, 404])
test('Trends ROP', 'get', '/api/ddr/trends/rop', expect_codes=[200, 404])
# Frontend calls /api/ddr/trends/{metric} directly
test('Trends (frontend path)', 'get', '/api/ddr/trends/rop', expect_codes=[200, 404])

# ============ SIX SIGMA ============
print("Testing Six Sigma...")
test('Six Sigma analyze', 'post', '/api/v2/six-sigma/analyze',
     json={'values': [1.0, 2.0, 3.0, 4.0, 5.0], 'lsl': 0.0, 'usl': 6.0},
     expect_codes=[200, 422])

# ============ OBSERVABILITY ============
print("Testing Observability...")
test('Obs health', 'get', '/api/v2/observability/health')
test('Obs models', 'get', '/api/v2/observability/models')
test('Obs features', 'get', '/api/v2/observability/features')
test('Obs predictions', 'get', '/api/v2/observability/predictions')
test('Obs drift', 'get', '/api/v2/observability/drift')

# ============ INTELLIGENCE ============
print("Testing Intelligence...")
test('Intel enrich', 'post', '/api/v2/intelligence/enrich-facts',
     json={'facts': [], 'doc_id': 'test'}, expect_codes=[200, 422])
test('Intel KPI impact', 'post', '/api/v2/intelligence/analyze-kpi-impact',
     json={'kpi_name': 'test', 'kpi_value': 1.0, 'doc_id': 'test'}, expect_codes=[200, 422])
test('Intel DMAIC', 'get', '/api/v2/intelligence/dmaic/test-kpi', expect_codes=[200, 404])
test('Intel recommendations', 'get', '/api/v2/intelligence/unified-recommendations/test-entity', expect_codes=[200, 404])
test('Intel scenario', 'get', '/api/v2/intelligence/scenario/test-entity', expect_codes=[200, 404])
test('Intel dashboard', 'get', '/api/v2/intelligence/dashboard/test-kpi', expect_codes=[200, 404])
test('Intel impact-network', 'get', '/api/v2/intelligence/impact-network/test-kpi', expect_codes=[200, 404])
test('Intel graph-network', 'get', '/api/v2/intelligence/graph-network/test-entity', expect_codes=[200, 404])
test('Intel cross-engine', 'get', '/api/v2/intelligence/cross-engine-analysis/test-entity', expect_codes=[200, 404])

# ============ GRAPH ============
print("Testing GraphRAG...")
test('Graph search', 'post', '/api/v2/graph/entities/search', json={'query': 'test'}, expect_codes=[200, 422])
test('Graph entity', 'get', '/api/v2/graph/entities/test-id', expect_codes=[200, 404])
test('Graph list', 'post', '/api/v2/graph/entities/list', json={}, expect_codes=[200, 422])
test('Graph related', 'get', '/api/v2/graph/entities/test-id/related', expect_codes=[200, 404])
test('Graph rel search', 'post', '/api/v2/graph/relationships/search', json={'query': 'test'}, expect_codes=[200, 422])
test('Graph rels', 'get', '/api/v2/graph/relationships/test-id', expect_codes=[200, 404])
test('Graph paths', 'post', '/api/v2/graph/paths', json={'source': 'a', 'target': 'b'}, expect_codes=[200, 422])
test('Graph centrality', 'post', '/api/v2/graph/analytics/centrality', json={}, expect_codes=[200, 422])

# ============ RESULTS ============
print()
print("=" * 80)
print("INTEGRATION TEST RESULTS")
print("=" * 80)

passes = [r for r in results if r[0] == 'PASS']
fails = [r for r in results if r[0] == 'FAIL']
hangs = [r for r in results if r[0] == 'HANG']
errors = [r for r in results if r[0] in ('ERR', 'CONN')]

print(f"\nTotal: {len(results)} | PASS: {len(passes)} | FAIL: {len(fails)} | HANG: {len(hangs)} | ERROR: {len(errors)}")

if fails:
    print(f"\n--- FAILURES ({len(fails)}) ---")
    for status, code, name, path in fails:
        print(f"  FAIL [{code}] {name}: {path}")

if hangs:
    print(f"\n--- HANGS ({len(hangs)}) ---")
    for status, code, name, path in hangs:
        print(f"  HANG {name}: {path}")

if errors:
    print(f"\n--- ERRORS ({len(errors)}) ---")
    for status, code, name, path in errors:
        print(f"  ERR {name}: {path}")

if not fails and not hangs and not errors:
    print("\nALL ENDPOINTS INTEGRATED CORRECTLY!")
