"""Verify database schema"""
import sqlite3
import os

DB_PATH = os.path.join('storage', 'local_storage.db')

if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute('PRAGMA table_info(documents)')
    columns = cur.fetchall()
    
    print("Columns in documents table:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    col_names = [col[1] for col in columns]
    if 'dashboard_data' in col_names:
        print("\n[OK] dashboard_data column exists!")
    else:
        print("\n[ERROR] dashboard_data column missing!")
    
    conn.close()
else:
    print(f"[INFO] Database not found at {DB_PATH}")

