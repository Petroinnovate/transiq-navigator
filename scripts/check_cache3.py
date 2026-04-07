import sqlite3, json, os

db = r'c:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master\cache_storage.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

cur.execute("SELECT key, length(value), expires_at FROM cache ORDER BY expires_at DESC")
rows = cur.fetchall()
for row in rows:
    print(f'key: {row[0]}  len: {row[1]}  exp: {row[2]}')

print()
print("--- Looking for LimitedMR or real PDF analysis ---")
cur.execute("SELECT key, value FROM cache ORDER BY expires_at DESC")
for key, val in cur.fetchall():
    try:
        d = json.loads(val)
        inner = d.get('dashboard', d)
        inner2 = inner.get('dashboard', inner) if isinstance(inner, dict) else inner
        title = inner2.get('title', '') if isinstance(inner2, dict) else ''
        kpis = len(inner2.get('kpis', [])) if isinstance(inner2, dict) else 0
        meta_title = inner2.get('meta', {}).get('title', '') if isinstance(inner2, dict) else ''
        source = inner2.get('meta', {}).get('sourceType', '') if isinstance(inner2, dict) else ''
        report_id = inner2.get('meta', {}).get('reportId', '') if isinstance(inner2, dict) else ''
        print(f'key={key[:50]} title="{title}" kpis={kpis} src={source} rid={report_id[:20]}')
    except Exception as e:
        print(f'key={key[:50]} parse error: {e}')

conn.close()
