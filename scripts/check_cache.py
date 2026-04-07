import sqlite3, json, os

db_paths = [
    r'c:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master\local_storage.db',
    r'c:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master\app\local_storage.db',
    r'c:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master\cache.db',
]

for p in db_paths:
    if os.path.exists(p):
        print(f'Found: {p}')
        conn = sqlite3.connect(p)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print('Tables:', [r[0] for r in cur.fetchall()])
        try:
            cur.execute("SELECT key, length(value), expires_at FROM cache ORDER BY expires_at DESC LIMIT 8")
            for row in cur.fetchall():
                print('  key:', row[0][:70], ' len:', row[1], ' exp:', row[2])
        except Exception as e:
            print('  cache error:', e)
        conn.close()
    else:
        print(f'Not found: {p}')
