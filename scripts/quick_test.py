"""Quick endpoint test to diagnose hangs"""
import requests, time

BASE = 'http://localhost:8001'

# Login
r = requests.post(f'{BASE}/auth/login', json={'email':'test@test.com','password':'testpass123'}, timeout=5)
if r.status_code != 200:
    r = requests.post(f'{BASE}/auth/register', json={'email':'test@test.com','password':'testpass123'}, timeout=5)
token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}

tests = [
    ('GET', '/api/v2/health', None),
    ('GET', '/api/v2/dashboard/latest', None),
    ('GET', '/api/v2/rigs', None),
    ('GET', '/api/v2/fleet/summary', None),
    ('GET', '/api/v2/observability/health', None),
    ('GET', '/api/v2/graph/entities/test-id', None),
    ('POST', '/api/v2/search', {'query': 'test', 'doc_ids': []}),
    ('GET', '/api/ddr/trends/rop', None),
    ('POST', '/api/v2/six-sigma/analyze', {'values': [1,2,3,4,5], 'lsl': 0, 'usl': 6}),
    ('GET', '/api/v2/ddr/reports', None),
    ('GET', '/api/v2/audit/fake-id/depth', None),
    ('POST', '/api/v2/intelligence/enrich-facts', {'facts': [], 'doc_id': 'test'}),
]

for method, path, body in tests:
    t = time.time()
    try:
        kw = {'headers': h, 'timeout': 15}
        if body:
            kw['json'] = body
        r = getattr(requests, method.lower())(f'{BASE}{path}', **kw)
        elapsed = time.time() - t
        detail = ''
        try:
            j = r.json()
            if 'detail' in j:
                detail = f' - {str(j["detail"])[:60]}'
        except:
            pass
        print(f'{elapsed:5.1f}s [{r.status_code}] {method} {path}{detail}')
    except requests.Timeout:
        elapsed = time.time() - t
        print(f'{elapsed:5.1f}s [HANG ] {method} {path}')
    except Exception as e:
        elapsed = time.time() - t
        print(f'{elapsed:5.1f}s [ERR  ] {method} {path}: {e}')
