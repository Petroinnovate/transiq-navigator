"""Live API smoke test — hits the running backend on localhost:8001."""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests

BASE = "http://localhost:8001"

# Load API key
from core.config.settings import settings
KEY = settings.API_KEY or ""
HEADERS = {"X-API-Key": KEY} if KEY else {}

def test(name, fn):
    print(f"\n=== {name} ===")
    try:
        fn()
    except Exception as e:
        print(f"  [FAIL] {e}")

def health():
    r = requests.get(f"{BASE}/api/v2/health", headers=HEADERS, timeout=5)
    print(f"  Status: {r.status_code}")
    print(f"  Body: {json.dumps(r.json(), indent=2)[:300]}")
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    print("  [OK]")

def docs_list():
    r = requests.get(f"{BASE}/api/v2/documents", headers=HEADERS, timeout=5)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list):
            print(f"  Documents in DB: {len(data)}")
        elif isinstance(data, dict):
            items = data.get("documents", data.get("items", []))
            print(f"  Documents in DB: {len(items)}")
        print("  [OK]")
    else:
        print(f"  Body: {r.text[:200]}")

def upload_test():
    """Upload a small test file and track the entire pipeline."""
    # Create a small test CSV
    test_content = (
        "Month,Revenue,Costs,Profit,Defect_Rate\n"
        "Jan-2024,420000,310000,110000,2.3\n"
        "Feb-2024,435000,315000,120000,2.1\n"
        "Mar-2024,460000,320000,140000,1.9\n"
        "Apr-2024,445000,325000,120000,2.5\n"
        "May-2024,480000,330000,150000,1.7\n"
        "Jun-2024,510000,340000,170000,1.5\n"
        "Jul-2024,495000,345000,150000,1.8\n"
        "Aug-2024,520000,350000,170000,1.4\n"
        "Sep-2024,540000,355000,185000,1.3\n"
        "Oct-2024,530000,360000,170000,1.6\n"
        "Nov-2024,560000,365000,195000,1.2\n"
        "Dec-2024,580000,370000,210000,1.1\n"
    )

    test_path = os.path.join(os.path.dirname(__file__), "test_upload.csv")
    with open(test_path, "w") as f:
        f.write(test_content)

    print("  Uploading test_upload.csv...")
    with open(test_path, "rb") as f:
        r = requests.post(
            f"{BASE}/api/v2/generate",
            headers=HEADERS,
            files={"file": ("test_upload.csv", f, "text/csv")},
            timeout=30,
        )

    print(f"  Upload status: {r.status_code}")
    if r.status_code not in (200, 201, 202):
        print(f"  Error: {r.text[:300]}")
        return

    data = r.json()
    print(f"  Response: {json.dumps(data, indent=2)[:500]}")

    doc_id = data.get("doc_id") or data.get("document_id") or data.get("id")
    task_id = data.get("task_id")
    print(f"  doc_id: {doc_id}")
    print(f"  task_id: {task_id}")

    if not doc_id:
        print("  [WARN] No doc_id returned")
        return

    # Poll for completion (max 60s)
    print("  Waiting for processing...")
    for i in range(30):
        time.sleep(2)
        try:
            if task_id:
                r = requests.get(f"{BASE}/api/v2/tasks/{task_id}/status", headers=HEADERS, timeout=5)
            else:
                r = requests.get(f"{BASE}/api/v2/documents/{doc_id}", headers=HEADERS, timeout=5)

            if r.status_code == 200:
                status_data = r.json()
                status = status_data.get("status", "unknown")
                progress = status_data.get("progress", "?")
                stage = status_data.get("stage", "?")
                print(f"    [{i*2}s] status={status}, stage={stage}, progress={progress}")

                if status in ("completed", "failed"):
                    break
        except Exception as e:
            print(f"    [{i*2}s] poll error: {e}")

    # Fetch dashboard
    print("\n  Fetching dashboard...")
    r = requests.get(f"{BASE}/api/v2/documents/{doc_id}/dashboard", headers=HEADERS, timeout=10)
    print(f"  Dashboard status: {r.status_code}")
    if r.status_code == 200:
        db = r.json()
        dash = db.get("dashboard", db)
        title = dash.get("title", "?")
        kpis = dash.get("kpis", [])
        charts = dash.get("charts", [])
        insights = dash.get("insights", {})
        print(f"  Title: {title}")
        print(f"  KPIs: {len(kpis)}")
        for k in kpis[:3]:
            print(f"    - {k.get('title', '?')}: {k.get('value', '?')}")
        print(f"  Charts: {len(charts)}")
        print(f"  Insights present: {bool(insights)}")
        print("  [OK] Dashboard generated successfully!")
    else:
        print(f"  Dashboard error: {r.text[:300]}")

    # Cleanup
    try:
        os.remove(test_path)
    except:
        pass

# Run tests
test("1. Health Check", health)
test("2. Document List", docs_list)
test("3. Upload + Full Pipeline", upload_test)

print("\n" + "=" * 50)
print("LIVE SMOKE TEST COMPLETE")
print("=" * 50)
