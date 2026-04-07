import json, sqlite3

conn = sqlite3.connect('local_storage.db')
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)

if 'processing_history' in tables:
    cur.execute("SELECT id, file_name, created_at FROM processing_history ORDER BY created_at DESC LIMIT 5")
    rows = cur.fetchall()
    print("Recent history:")
    for r in rows: print(" ", r)

    if rows:
        cur.execute("SELECT response FROM processing_history ORDER BY created_at DESC LIMIT 1")
        resp = cur.fetchone()
        if resp and resp[0]:
            data = json.loads(resp[0])
            dash = data.get('dashboard', data)
            inner = dash.get('dashboard', dash)
            secs = inner.get('sections', [])
            print(f"Sections in latest history: {len(secs)}")
            print(f"KPIs: {len(inner.get('kpis', []))}")
            if secs:
                for s in secs[:2]:
                    print(f"  Section: {s.get('title','?')} | dmaicPhase: {s.get('dmaicPhase')} | findings: {len(s.get('keyFindings',[]))}")

elif 'documents' in tables:
    cur.execute("SELECT id, file_name, created_at FROM documents ORDER BY created_at DESC LIMIT 5")
    rows = cur.fetchall()
    print("Recent documents:")
    for r in rows: print(" ", r)
