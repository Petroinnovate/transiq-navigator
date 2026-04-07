import json, os

result_path = os.path.join(os.environ.get('TEMP', '/tmp'), 'transiq_result.json')
with open(result_path, encoding='utf-8-sig') as f:
    j = json.load(f)

d = j['dashboard']['dashboard']
meta = j['dashboard']['meta']
ac = j['dashboard']['autoClassification']

print('=' * 60)
print('  ANALYSIS: LimitedMR10022024.pdf')
print('=' * 60)
print('Title       :', d['title'])
print('Description :', d.get('description', '')[:150])
print('Report Type :', ac['reportType'])
print('Asset Scope :', ac['assetScope'])
print('Decision    :', ac['decisionLevel'])
print('Confidence  :', meta['confidenceOverall'])
print('Readiness   :', meta['decisionReadinessScore'])

print()
print('=== KPIs ===')
for k in d['kpis']:
    print(f"  {k['title']}: {k['value']} {k['unit']} | {k['trend']} | {k['change']}")

print()
print('=== SIX SIGMA ===')
ss = d['sixSigma']
print('  Sigma Level :', ss['sigmaLevel'])
print('  Defect Rate :', ss['defectRate'])
print('  Capability  :', ss['processCapability'])

print()
print('=== DMAIC - DEFINE ===')
define = ss['dmaic']['define']
stmt = define.get('problemStatement', '')
print('  Problem:', stmt[:250] if isinstance(stmt, str) else json.dumps(stmt)[:250])
fe = define.get('financialExposure', {})
print(f"  Financial Exposure: {fe.get('unit','$')}{fe.get('value',0):,}")
print('  CTQs:')
for c in define.get('ctqs', []):
    print(f'    - {c}')

print()
print('=== DMAIC - MEASURE ===')
measure = ss['dmaic']['measure']
print('  Data Confidence:', measure.get('dataConfidence', 'N/A'))
print('  Baseline Metrics:')
for m in measure.get('baselineMetrics', []):
    print(f'    - {m}')

print()
print('=== DMAIC - ROOT CAUSES ===')
for rc in ss['dmaic']['analyze'].get('rootCauses', []):
    if isinstance(rc, dict):
        conf = rc.get('confidence', 0)
        cause = rc.get('cause', str(rc))
    else:
        conf = '?'
        cause = str(rc)
    print(f'  [{int(float(conf)*100) if isinstance(conf, (int,float)) else conf}%] {cause[:150]}')

print()
print('=== DMAIC - IMPROVE ===')
for a in ss['dmaic']['improve'].get('recommendedActions', []):
    print(f'  - {str(a)[:150]}')

print()
print('=== DMAIC - CONTROL ===')
ctrl = ss['dmaic']['control']
print('  Monitoring KPIs:')
for k in ctrl.get('monitoringKPIs', []):
    print(f'    - {k}')

print()
print('=== CHARTS ===')
for c in d['charts']:
    print(f"  [{c['type']}] {c['title']} (size={c.get('size','?')})")

print()
print('=== OPTIMIZATION SUGGESTIONS ===')
for o in d.get('optimizationSuggestions', []):
    conf = o['confidence']
    if isinstance(conf, float):
        conf_str = f'{conf*100:.0f}%'
    else:
        conf_str = str(conf)
    sav = o['savings']
    print(f"  [{o['impact'].upper()}] {o['title']}")
    print(f"    Saves: {sav['percentage']} ({sav['unit']}{sav['value']:,} {sav['timeframe']}) | conf={conf_str}")

print()
print('=== FORECASTS ===')
for fc in d['predictive']['forecast']:
    print(f"  {fc['metric']} | {fc['timeframe']} | risk={fc['risk']} | conf={fc['confidence']}")

print()
print('=== WHAT-IF SCENARIOS ===')
for s in d['predictive'].get('whatIfScenarios', []):
    print(f"  Action: {s['action'][:100]}")
    print(f"  Impact: {s['impact'][:80]} | Delta: ${s.get('financialDelta',0):,}")

print()
print('=== ALERTS ===')
for a in d['insights']['alerts']:
    print(f"  [{a['severity'].upper()}] {a['message']}")
    if a.get('action'):
        print(f"    Action: {a['action']}")

print()
print('=== TRENDS ===')
for t in d['insights'].get('trends', []):
    print(f'  - {t}')

print()
print('=== RECOMMENDATIONS ===')
for r in d['insights'].get('recommendations', []):
    print(f'  - {str(r)[:150]}')

print()
print('=== EXECUTIVE SUMMARY ===')
print(d['insights']['summary'])

print()
print('=== TABLES ===')
for t in d.get('tables', []):
    print(f"  {t['title']} ({len(t.get('data',[]))} rows, {len(t.get('columns',[]))} cols)")
