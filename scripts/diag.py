"""Full end-to-end diagnostic for TransIQ"""
import requests, sys, time, io

BASE = 'http://localhost:8001'

# Wait for server to be ready
for i in range(10):
    try:
        r = requests.get(f'{BASE}/', timeout=3)
        print(f'Server ready (attempt {i+1})')
        break
    except:
        if i < 9:
            time.sleep(2)
        else:
            print('Server not responding after 20s')
            sys.exit(1)

def test(name, method, url, **kw):
    kw.setdefault('timeout', 8)
    try:
        r = getattr(requests, method)(url, **kw)
        status = 'PASS' if r.status_code < 400 else 'FAIL'
        print(f'{status} [{r.status_code}] {name}')
        if r.status_code >= 400:
            print(f'  Body: {r.text[:200]}')
        return r
    except requests.Timeout:
        print(f'HANG [timeout] {name} <--- PROBLEM')
        return None
    except Exception as e:
        print(f'ERR  {name}: {e}')
        return None

print()
print('=== Auth Flow ===')
r = test('Login', 'post', f'{BASE}/auth/login', json={'email': 'test@test.com', 'password': 'testpass123'})
if not r or r.status_code != 200:
    r = test('Register', 'post', f'{BASE}/auth/register', json={'email': 'newuser2@test.com', 'password': 'testpass123'})
    if r and r.status_code in (200, 201):
        token = r.json()['access_token']
    else:
        print('AUTH BROKEN')
        sys.exit(1)
else:
    token = r.json()['access_token']

h = {'Authorization': f'Bearer {token}'}
r_me = test('/auth/me', 'get', f'{BASE}/auth/me', headers=h)
if r_me:
    print(f'  /auth/me response: {r_me.text[:200]}')

print()
print('=== Upload ===')
csv_data = 'Well,Depth,ROP,WOB\nA1,5000,120,25\nA2,6000,90,30'
r = test('Upload', 'post', f'{BASE}/api/v2/generate',
         files={'file': ('test.csv', io.BytesIO(csv_data.encode()), 'text/csv')},
         headers=h)

if r and r.status_code == 200:
    d = r.json()
    doc_id = d['doc_id']
    task_id = d['task_id']
    print(f'  doc_id={doc_id}')
    print('  Waiting 5s for processing...')
    time.sleep(5)

    print()
    print('=== Polling (what frontend does) ===')
    r_task = test('Task status', 'get', f'{BASE}/api/v2/task/{task_id}', headers=h)
    if r_task:
        tj = r_task.json()
        print(f'  task status={tj.get("status")}, progress={tj.get("progress")}')

    r_dash = test('Dashboard', 'get', f'{BASE}/api/v2/documents/{doc_id}/dashboard', headers=h)
    if r_dash:
        dj = r_dash.json()
        print(f'  Dashboard top keys: {list(dj.keys())[:8]}')
        print(f'  status field: {dj.get("status")}')
        print(f'  kpis count: {len(dj.get("kpis", []))}')
        print(f'  charts count: {len(dj.get("charts", []))}')

print()
print('=== DONE ===')
