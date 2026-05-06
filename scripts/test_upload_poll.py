"""Upload and poll with proper wait time"""
import requests, time, io, json

BASE = 'http://localhost:8001'

# Login
r = requests.post(f'{BASE}/auth/login', json={'email': 'test@test.com', 'password': 'testpass123'}, timeout=5)
token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}

# Upload with realistic data
csv_data = (
    'Well,Depth_ft,ROP_fthr,WOB_klb,RPM,Torque_klbft,FlowRate_gpm,SPP_psi\n'
    'Well_A1,5000,120,25,150,12,500,2800\n'
    'Well_A1,5500,95,30,140,15,520,3100\n'
    'Well_A2,6000,85,28,130,18,480,3500\n'
    'Well_A2,6500,110,22,160,10,510,2900\n'
    'Well_A3,7000,75,35,120,20,490,3800\n'
)

r = requests.post(
    f'{BASE}/api/v2/generate',
    files={'file': ('drilling_data.csv', io.BytesIO(csv_data.encode()), 'text/csv')},
    headers=h, timeout=10
)
data = r.json()
doc_id = data['doc_id']
task_id = data['task_id']
print(f'Uploaded: doc_id={doc_id}')
print(f'Polling every 10s for up to 120s...')

for i in range(12):
    time.sleep(10)
    elapsed = (i + 1) * 10
    try:
        rt = requests.get(f'{BASE}/api/v2/task/{task_id}', headers=h, timeout=5)
        if rt.status_code == 200:
            tj = rt.json()
            status = tj.get('status', '?')
            progress = tj.get('progress', '?')
            stage = tj.get('stage', '?')
            print(f'  [{elapsed}s] task: status={status}, progress={progress}, stage={stage}')
            if status in ('completed', 'failed'):
                if status == 'failed':
                    print(f'  ERROR: {tj.get("error", "unknown")}')
                break
        else:
            print(f'  [{elapsed}s] task endpoint: {rt.status_code}')
    except Exception as e:
        print(f'  [{elapsed}s] poll error: {e}')

# Final dashboard check
print()
print('=== Final Dashboard Check ===')
rd = requests.get(f'{BASE}/api/v2/documents/{doc_id}/dashboard', headers=h, timeout=10)
dj = rd.json()
status = dj.get('status', 'none')
kpis = dj.get('kpis', [])
charts = dj.get('charts', [])
print(f'status={status}, kpis={len(kpis)}, charts={len(charts)}')

if kpis:
    print('Sample KPIs:')
    for k in kpis[:5]:
        label = k.get('label', '?')
        value = k.get('value', '?')
        print(f'  - {label}: {value}')
else:
    print('NO KPIs generated - LLM might be returning errors')
    # Check insights
    insights = dj.get('insights', {})
    summary = insights.get('summary', '')
    if summary:
        print(f'Insights summary: {summary[:200]}')
