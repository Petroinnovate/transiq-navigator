import requests, json
r = requests.post('http://localhost:8001/auth/login', json={'email':'test@test.com','password':'testpass123'}, timeout=5)
token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}
r = requests.get('http://localhost:8001/api/v2/documents/e43dee59-740d-4872-a31d-cf43c47d411a/dashboard', headers=h, timeout=10)
dj = r.json()

print("=== KPIs ===")
for k in dj.get('kpis', [])[:5]:
    print(json.dumps(k, indent=2))

print("\n=== Charts ===")
for c in dj.get('charts', [])[:3]:
    chart_summary = {key: c[key] for key in ['title', 'type'] if key in c}
    print(json.dumps(chart_summary, indent=2))
