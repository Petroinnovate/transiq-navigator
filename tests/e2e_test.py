"""End-to-end test: upload CSV, verify dashboard response."""
import requests, time, json

csv_path = "test_cm.csv"
t0 = time.time()
print("Uploading test_cm.csv to POST /api/v2/generate ...")

print("(timeout set to 900s — pipeline makes many Gemini API calls)")
with open(csv_path, "rb") as f:
    r = requests.post(
        "http://localhost:8001/api/v2/generate",
        files={"file": ("test_cm.csv", f, "text/csv")},
        timeout=900,
    )

elapsed = round(time.time() - t0, 1)
print(f"HTTP {r.status_code} | {elapsed}s")

data = r.json()
print(f"doc_id   : {data.get('doc_id')}")
print(f"status   : {data.get('status')}")
print(f"message  : {data.get('message', '')[:80]}")

dash = data.get("dashboard", {})
if dash:
    print(f"Dashboard keys: {list(dash.keys())}")
    kpis = dash.get("kpis", [])
    print(f"KPIs: {len(kpis)}")
    if kpis:
        k = kpis[0]
        print(f"  First KPI: {k.get('title')} = {k.get('value')} {k.get('unit')}")
    charts = dash.get("charts", [])
    print(f"Charts: {len(charts)}")
    suggestions = dash.get("optimizationSuggestions", [])
    print(f"Suggestions: {len(suggestions)}")
    dmaic = dash.get("sixSigma", {}).get("dmaic", {})
    print(f"DMAIC phases populated: {[p for p in dmaic if dmaic[p]]}")
else:
    print("No dashboard key — checking top-level keys:", list(data.keys()))

meta = data.get("meta", {})
print(f"Confidence: {meta.get('confidenceOverall')}")
print(f"Quality score: {data.get('dashboard', {}).get('qualityScore', {}).get('overall_score')}")
print("PASS" if r.status_code == 200 else "FAIL")
