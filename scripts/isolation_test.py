"""Test each endpoint in isolation - skip known blockers"""
import requests, time, subprocess, signal, os, sys

BASE = 'http://localhost:8001'

# Wait for server to be ready
print("Waiting for server...")
for _ in range(30):
    try:
        requests.get(f'{BASE}/', timeout=2)
        print("Server ready!")
        break
    except:
        time.sleep(2)
else:
    print("FATAL: Server not ready after 60s")
    sys.exit(1)

# Login
r = requests.post(f'{BASE}/auth/login', json={'email':'test@test.com','password':'testpass123'}, timeout=5)
if r.status_code != 200:
    r = requests.post(f'{BASE}/auth/register', json={'email':'test@test.com','password':'testpass123'}, timeout=5)
token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}

# Tests grouped: first non-blocking, then suspected blockers
non_blocking_tests = [
    ('GET', '/api/v2/dashboard/latest', None),
    ('GET', '/api/v2/rigs', None),
    ('GET', '/api/v2/fleet/summary', None),
    ('GET', '/api/v2/fleet/npt-pareto', None),
    ('GET', '/api/v2/fleet/spc/rop', None),
    ('GET', '/api/v2/fleet/top-performers', None),
    ('GET', '/api/v2/fleet/heatmap', None),
    ('GET', '/api/v2/fleet/export', None),
    ('GET', '/api/v2/rigs/fake-id', None),
    ('GET', '/api/v2/rigs/fake-id/kpis', None),
    ('GET', '/api/v2/rigs/fake-id/timeline', None),
    ('GET', '/api/v2/rigs/fake-id/npt', None),
    ('GET', '/api/v2/rigs/fake-id/survey', None),
    ('GET', '/api/v2/rigs/fake-id/mud', None),
    ('GET', '/api/v2/rigs/fake-id/personnel', None),
    ('GET', '/api/v2/rigs/fake-id/bha', None),
    ('GET', '/api/v2/rigs/fake-id/bulk', None),
    ('GET', '/api/v2/rigs/fake-id/hse', None),
    ('GET', '/api/v2/rigs/fake-id/foreman-remarks', None),
    ('GET', '/api/v2/rigs/fake-id/well-design', None),
    ('GET', '/api/v2/rigs/fake-id/export', None),
    ('GET', '/api/v2/observability/health', None),
    ('GET', '/api/v2/observability/models', None),
    ('GET', '/api/v2/observability/features', None),
    ('GET', '/api/v2/observability/predictions', None),
    ('GET', '/api/v2/observability/drift', None),
    ('GET', '/api/v2/dashboard/fake-id', None),
    ('GET', '/api/v2/dashboard/status/fake-id', None),
    ('GET', '/api/v2/dashboard/fake-id/export/pdf', None),
    ('GET', '/api/v2/dashboard/fake-id/export/excel', None),
    ('GET', '/api/v2/ddr/reports', None),
    ('GET', '/api/v2/ddr/metrics/fake-id', None),
    ('GET', '/api/v2/audit/fake-id/depth', None),
    ('GET', '/api/v2/audit/changelog', None),
    ('GET', '/api/ddr/trends/rop', None),
    ('GET', '/api/ddr/trends/npt', None),
    ('GET', '/api/ddr/trends/depth-progress', None),
    ('POST', '/api/v2/six-sigma/analyze', {'values': [1,2,3,4,5], 'lsl': 0, 'usl': 6}),
    ('GET', '/api/v2/graph/entities/test-id', None),
    ('POST', '/api/v2/graph/entities/search', {'query': 'test'}),
    ('POST', '/api/v2/graph/entities/list', {}),
    ('GET', '/api/v2/graph/entities/test-id/related', None),
    ('POST', '/api/v2/graph/relationships/search', {'query': 'test'}),
    ('GET', '/api/v2/graph/relationships/test-id', None),
    ('POST', '/api/v2/graph/paths', {'source': 'a', 'target': 'b'}),
    ('POST', '/api/v2/graph/analytics/centrality', {}),
    ('GET', '/api/v2/intelligence/dmaic/test-kpi', None),
    ('GET', '/api/v2/intelligence/unified-recommendations/test-entity', None),
    ('GET', '/api/v2/intelligence/scenario/test-entity', None),
    ('GET', '/api/v2/intelligence/dashboard/test-kpi', None),
    ('GET', '/api/v2/intelligence/impact-network/test-kpi', None),
    ('GET', '/api/v2/intelligence/graph-network/test-entity', None),
    ('GET', '/api/v2/intelligence/cross-engine-analysis/test-entity', None),
]

# Blockers tested last (they may block event loop)
blocker_tests = [
    ('POST', '/api/v2/search', {'query': 'test', 'doc_ids': []}),
    ('POST', '/api/v2/agent/run', {'goal': 'test', 'context': {}}),
    ('POST', '/api/v2/intelligence/enrich-facts', {'facts': [], 'doc_id': 'test'}),
    ('POST', '/api/v2/intelligence/analyze-kpi-impact', {'kpi_name': 'test', 'kpi_value': 1.0, 'doc_id': 'test'}),
    ('GET', '/api/v2/health', None),
]

print("=" * 70)
print("NON-BLOCKING ENDPOINTS (should return quickly)")
print("=" * 70)

pass_count = 0
fail_count = 0
hang_count = 0

for method, path, body in non_blocking_tests:
    t = time.time()
    try:
        kw = {'headers': h, 'timeout': 8}
        if body:
            kw['json'] = body
        r = getattr(requests, method.lower())(f'{BASE}{path}', **kw)
        elapsed = time.time() - t
        status = r.status_code
        detail = ''
        try:
            j = r.json()
            if 'detail' in j:
                detail = f' - {str(j["detail"])[:50]}'
            elif 'error' in j:
                detail = f' - {str(j["error"])[:50]}'
        except:
            pass
        ok = status in [200, 201, 404, 422]
        # 401 = auth issue
        marker = 'PASS' if ok else ('AUTH' if status == 401 else 'FAIL')
        if ok: pass_count += 1
        else: fail_count += 1
        print(f'  {marker:4s} [{status}] {elapsed:4.1f}s {method:4s} {path}{detail}')
    except requests.Timeout:
        elapsed = time.time() - t
        hang_count += 1
        print(f'  HANG [---] {elapsed:4.1f}s {method:4s} {path}')
    except Exception as e:
        fail_count += 1
        print(f'  ERR  [---] {method:4s} {path}: {str(e)[:40]}')

print(f"\n  Summary: {pass_count} PASS, {fail_count} FAIL/AUTH, {hang_count} HANG\n")

print("=" * 70)
print("POTENTIALLY BLOCKING ENDPOINTS (Qdrant/LLM dependent)")
print("=" * 70)

for method, path, body in blocker_tests:
    t = time.time()
    try:
        kw = {'headers': h, 'timeout': 20}
        if body:
            kw['json'] = body
        r = getattr(requests, method.lower())(f'{BASE}{path}', **kw)
        elapsed = time.time() - t
        print(f'  [{r.status_code}] {elapsed:4.1f}s {method:4s} {path}')
    except requests.Timeout:
        elapsed = time.time() - t
        print(f'  HANG  {elapsed:4.1f}s {method:4s} {path}')
    except Exception as e:
        print(f'  ERR   {method:4s} {path}: {str(e)[:40]}')
