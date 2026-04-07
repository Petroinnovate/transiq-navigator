import sqlite3, json, os

db_paths = [
    r'c:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master\cache_storage.db',
    r'c:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master\storage\local_storage.db',
]

for p in db_paths:
    if os.path.exists(p):
        print(f'\n=== Found: {p} ===')
        conn = sqlite3.connect(p)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print('Tables:', tables)
        for tbl in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                cnt = cur.fetchone()[0]
                print(f'  {tbl}: {cnt} rows')
                # peek at schema
                cur.execute(f"PRAGMA table_info({tbl})")
                cols = [r[1] for r in cur.fetchall()]
                print(f'  cols: {cols}')
            except Exception as e:
                print(f'  error: {e}')
        
        # Try to find dashboard-related data
        for tbl in tables:
            try:
                cur.execute(f"SELECT * FROM {tbl} LIMIT 3")
                rows = cur.fetchall()
                for row in rows:
                    row_str = str(row)[:200]
                    if 'dashboard' in row_str.lower() or 'title' in row_str.lower() or 'kpi' in row_str.lower():
                        print(f'  MATCH in {tbl}: {row_str}')
            except:
                pass
        conn.close()
