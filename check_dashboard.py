import requests, json

doc_id = '58f3b86a-6de8-4f78-aa97-60ceab73587d'

r = requests.get(f'http://localhost:8001/api/v2/documents/{doc_id}/dashboard', timeout=30)
print(f'Status: {r.status_code}')
data = r.json()

with open('dashboard_output.json', 'w') as f:
    json.dump(data, f, indent=2)
print('Saved full response to dashboard_output.json')

if isinstance(data, dict):
    print(f'Top keys: {list(data.keys())}')
    meta = data.get('meta', {})
    print(f'Meta: {json.dumps(meta, indent=2)}')
    kpis = data.get('kpis', [])
    print(f'KPI count: {len(kpis)}')
    for k in kpis[:3]:
        name = k.get('name', '?')
        val = k.get('value', '?')
        unit = k.get('unit', '')
        print(f'  - {name}: {val} {unit}')
    charts = data.get('charts', [])
    print(f'Charts count: {len(charts)}')
    ss = data.get('sixSigma', {})
    sigma = ss.get('sigmaLevel', '?')
    print(f'Six Sigma level: {sigma}')
    insights = data.get('insights', {})
    alerts = insights.get('alerts', [])
    recs = insights.get('recommendations', [])
    print(f'Alerts: {len(alerts)}')
    print(f'Recommendations: {len(recs)}')
    opt = data.get('optimizationSuggestions', [])
    print(f'Optimization suggestions: {len(opt)}')
    ac = data.get('autoClassification', {})
    print(f'Auto classification: {json.dumps(ac, indent=2)}')
    pred = data.get('predictive', {})
    print(f'Predictive forecasts: {len(pred.get("forecast", []))}')
    widgets = data.get('widgets', {})
    print(f'Widgets: {json.dumps(widgets, indent=2)[:300]}')
else:
    print(f'Response: {str(data)[:500]}')
