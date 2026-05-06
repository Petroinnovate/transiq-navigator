"""Inspect the dashboard data for the last uploaded document."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests

BASE = "http://localhost:8001"
from core.config.settings import settings
KEY = settings.API_KEY or ""
HEADERS = {"X-API-Key": KEY} if KEY else {}

# Get latest dashboard
r = requests.get(f"{BASE}/api/v2/dashboard/latest", headers=HEADERS, timeout=10)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(json.dumps(data, indent=2, default=str)[:3000])
else:
    print(r.text[:500])

# Also check with doc_id
print("\n\n=== Checking specific doc ===")
r2 = requests.get(f"{BASE}/api/v2/documents", headers=HEADERS, timeout=10)
if r2.status_code == 200:
    docs = r2.json()
    if isinstance(docs, list) and docs:
        latest = docs[-1]
        did = latest.get("id", latest.get("doc_id", ""))
        print(f"Latest doc: {did}")
        r3 = requests.get(f"{BASE}/api/v2/documents/{did}/dashboard", headers=HEADERS, timeout=10)
        print(f"Dashboard status: {r3.status_code}")
        if r3.status_code == 200:
            dash = r3.json()
            print(json.dumps(dash, indent=2, default=str)[:3000])
