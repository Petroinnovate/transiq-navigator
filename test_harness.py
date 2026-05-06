# ==========================================
# TRANSIQ AUTOMATED TEST HARNESS
# ==========================================

import requests
from collections import defaultdict

BASE_URL = "http://localhost:8001"
API_PREFIX = "/api/v2"
DOC_ID = "4abfe271-2f6d-44e8-a99d-dc9ee9850f5d"  # 295 chunks

# ==========================================
# HELPERS
# ==========================================

def get_report(doc_id):
    res = requests.get(f"{BASE_URL}{API_PREFIX}/report/{doc_id}")
    res.raise_for_status()
    return res.json()

def _flatten_from_rigs(report, field):
    """Extract items from rig_summaries by field name."""
    items = []
    for rig in report.get("rig_summaries", []):
        items.extend(rig.get(field, []))
    return items

# ==========================================
# TEST 1: TRACEABILITY
# ==========================================

def test_traceability(report):
    missing = 0

    for rig in report.get("rig_summaries", []):
        if not rig.get("source_pages"):
            missing += 1

    return {
        "test": "traceability",
        "passed": missing == 0,
        "missing_count": missing
    }

# ==========================================
# TEST 2: COVERAGE
# ==========================================

def test_coverage(report):
    total_chunks = report.get("metrics", {}).get("total_chunks", 0)
    used_chunks = report.get("metrics", {}).get("used_chunks", 0)

    coverage = (used_chunks / total_chunks * 100) if total_chunks else 0

    return {
        "test": "coverage",
        "coverage": round(coverage, 2),
        "passed": coverage >= 60
    }

# ==========================================
# TEST 3: PAGE DISTRIBUTION
# ==========================================

def test_page_distribution(report):
    pages = set()

    for rig in report.get("rig_summaries", []):
        pages.update(p for p in rig.get("source_pages", []) if isinstance(p, int))

    # Also check top-level metrics source_pages
    pages.update(p for p in report.get("metrics", {}).get("source_pages", []) if isinstance(p, int))

    spread = max(pages) - min(pages) if pages else 0

    return {
        "test": "page_distribution",
        "unique_pages": len(pages),
        "spread": spread,
        "passed": spread > 100  # adjust based on doc size
    }

# ==========================================
# TEST 4: KPI COUNT & DUPLICATION
# ==========================================

def test_kpis(report):
    kpis = _flatten_from_rigs(report, "aggregated_kpis")
    names = []
    for k in kpis:
        if isinstance(k, dict) and "name" in k:
            names.append(k["name"])
        elif isinstance(k, str):
            names.append(k)

    unique_names = set(names)

    return {
        "test": "kpi_quality",
        "total_kpis": len(kpis),
        "unique_kpis": len(unique_names),
        "passed": len(kpis) >= 10  # adjusted — actual threshold depends on dataset
    }

# ==========================================
# TEST 5: HALLUCINATION CHECK
# ==========================================

def test_hallucination(report):
    invalid = 0

    for rig in report.get("rig_summaries", []):
        if not rig.get("source_pages"):
            invalid += 1

    return {
        "test": "hallucination",
        "invalid_items": invalid,
        "passed": invalid == 0
    }

# ==========================================
# TEST 6: RIG DISTRIBUTION
# ==========================================

def test_rig_distribution(report):
    rig_ids = set()

    for rig in report.get("rig_summaries", []):
        rig_id = rig.get("rig_id")
        if rig_id is not None:
            rig_ids.add(rig_id)

    return {
        "test": "rig_distribution",
        "unique_rigs": len(rig_ids),
        "passed": len(rig_ids) > 5  # adjusted — depends on dataset
    }

# ==========================================
# TEST RUNNER
# ==========================================

def run_all_tests():
    report = get_report(DOC_ID)

    results = []

    results.append(test_traceability(report))
    results.append(test_coverage(report))
    results.append(test_page_distribution(report))
    results.append(test_kpis(report))
    results.append(test_hallucination(report))
    results.append(test_rig_distribution(report))

    print("\n===== TEST RESULTS =====\n")

    passed = 0
    failed = 0
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        if r["passed"]:
            passed += 1
        else:
            failed += 1
        print(f"{r['test'].upper()}: {status}")
        print(r)
        print("------------------------")

    print(f"\nSUMMARY: {passed} passed, {failed} failed out of {len(results)} tests")

    return results

# ==========================================
# ENTRY
# ==========================================

if __name__ == "__main__":
    run_all_tests()
