import sqlite3, json

db = r'c:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master\cache_storage.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

cur.execute("SELECT value FROM cache WHERE key = 'dashboard:4d7545cd9400b34fa9f7941d669e7443'")
row = cur.fetchone()
if row:
    d = json.loads(row[0])
    inner = d.get('dashboard', d)
    inner2 = inner.get('dashboard', inner) if isinstance(inner, dict) else inner
    print('title:', inner2.get('title'))
    print('kpis:', len(inner2.get('kpis', [])))
    print('charts:', len(inner2.get('charts', [])))
    print()
    if inner2.get('kpis'):
        for k in inner2['kpis']:
            print(' KPI:', k.get('title'), '=', k.get('value'), k.get('unit'), '| target:', k.get('target'))
    print()
    if inner2.get('sixSigma'):
        ss = inner2['sixSigma']
        print('Six Sigma rootCauses:', ss.get('rootCauses', [])[:3])
    if inner2.get('insights'):
        ins = inner2['insights']
        print('alerts:', len(ins.get('alerts', [])))
    if inner2.get('optimizationSuggestions'):
        opts = inner2['optimizationSuggestions']
        print('optimizations:', len(opts))
        for o in opts[:2]:
            print(' OPT:', o.get('title'), '| impact:', o.get('impact'), '| savings:', o.get('savings'))
conn.close()
