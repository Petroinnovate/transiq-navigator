import sqlite3, json
from core.config.settings import settings
db_path = settings.DATABASE_URL.replace('sqlite:///', '')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, status FROM documents WHERE status = 'completed' LIMIT 3")
for row in cur.fetchall():
    doc_id = row['id']
    cur2 = conn.cursor()
    cur2.execute('SELECT COUNT(*) as cnt FROM chunks WHERE doc_id = ?', (doc_id,))
    cnt = cur2.fetchone()['cnt']
    print(f"doc_id={doc_id} status={row['status']} chunks={cnt}")
    if cnt > 0:
        cur2.execute('SELECT content FROM chunks WHERE doc_id = ? LIMIT 2', (doc_id,))
        for c in cur2.fetchall():
            text = (c['content'] or 'EMPTY')[:400]
            print(f"  chunk: {text}")
        print()
conn.close()
