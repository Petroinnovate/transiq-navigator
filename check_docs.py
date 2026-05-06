import sqlite3

conn = sqlite3.connect(r'c:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master\local_storage.db')
cur = conn.cursor()

# List tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", cur.fetchall())

# Check documents
cur.execute("SELECT id, name FROM documents LIMIT 10")
rows = cur.fetchall()
print("\nDocuments:")
for r in rows:
    print(f"  id={r[0]}, name={r[1]}")

# Check rig_summaries
try:
    cur.execute("SELECT DISTINCT doc_id FROM rig_summaries LIMIT 10")
    rows = cur.fetchall()
    print("\nRig summaries doc_ids:", [r[0] for r in rows])
except Exception as e:
    print(f"\nrig_summaries error: {e}")

conn.close()
