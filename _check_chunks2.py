import sqlite3
from core.config.settings import settings
conn = sqlite3.connect(settings.DATABASE_URL.replace('sqlite:///',''))
cur = conn.cursor()
cur.execute("""
    SELECT d.id, COUNT(c.id) as cnt 
    FROM documents d 
    LEFT JOIN chunks c ON d.id = c.doc_id 
    WHERE d.status = 'completed' 
    GROUP BY d.id ORDER BY cnt DESC LIMIT 1
""")
row = cur.fetchone()
if row:
    doc_id = row[0]
    print(f"Best doc: {doc_id} with {row[1]} chunks")
    cur.execute("SELECT chunk_text FROM chunks WHERE doc_id = ? ORDER BY chunk_index LIMIT 3", (doc_id,))
    for i, r in enumerate(cur.fetchall()):
        print(f"\n--- Chunk {i} ---")
        print((r[0] or "EMPTY")[:600])
conn.close()
