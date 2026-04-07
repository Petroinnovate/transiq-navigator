"""
Database migration script to add dashboard_data column
"""
import sqlite3
import os

DB_PATH = os.path.join('storage', 'local_storage.db')

if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Check if column exists
        cur.execute("PRAGMA table_info(documents)")
        columns = [col[1] for col in cur.fetchall()]
        
        if 'dashboard_data' not in columns:
            print("Adding dashboard_data column to documents table...")
            cur.execute('ALTER TABLE documents ADD COLUMN dashboard_data TEXT')
            conn.commit()
            print("[OK] Column added successfully")
        else:
            print("[INFO] Column dashboard_data already exists")
            
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()
else:
    print(f"[INFO] Database not found at {DB_PATH}, will be created on first use")

