"""Integration tests for Evidence-Based Confidence Engine (Phase 12)."""

from section_analyzer import _compute_evidence_confidence, _compute_group_confidence

def test_empty_data():
    r = _compute_evidence_confidence([], [], [], [], set(), 10)
    assert r["confidence_level"] == "LOW", f"Expected LOW, got {r['confidence_level']}"
    assert r["confidence"] == 0.0, f"Expected 0.0, got {r['confidence']}"
    assert "confidence_breakdown" in r
    print(f"  PASS: empty data => confidence={r['confidence']}, level={r['confidence_level']}")

def test_rich_data():
    findings = [{"finding": f"F{i}", "source_pages": [i]} for i in range(15)]
    kpis = [{"name": f"KPI{i}", "value": i * 10, "source_pages": [i]} for i in range(8)]
    risks = [{"risk": f"R{i}"} for i in range(5)]
    financial = [{"description": f"FI{i}", "amount": i * 1000} for i in range(5)]
    pages = set(range(1, 11))
    r = _compute_evidence_confidence(findings, kpis, risks, financial, pages, 12)
    assert r["confidence_level"] == "HIGH", f"Expected HIGH, got {r['confidence_level']}"
    assert r["confidence"] > 0.75, f"Expected >0.75, got {r['confidence']}"
    print(f"  PASS: rich data => confidence={r['confidence']:.3f}, level={r['confidence_level']}")
    print(f"         breakdown: {r['confidence_breakdown']}")

def test_medium_data():
    # Need enough support + some density + decent coverage for MEDIUM (>0.50, <=0.75)
    findings = [{"finding": f"F{i}", "source_pages": [i]} for i in range(8)]
    kpis = [{"name": f"K{i}", "value": (i + 1) * 10} for i in range(3)]
    # 11 support items => 11/20 = 0.55 support
    # 3 KPIs with values => 3/15 = 0.2 density
    # pages from findings: {0..7}, total 12 => 8/12 = 0.67 coverage
    r = _compute_evidence_confidence(findings, kpis, [], [], set(), 12)
    assert r["confidence_level"] == "MEDIUM", f"Expected MEDIUM, got {r['confidence_level']} (conf={r['confidence']:.3f})"
    assert 0.50 < r["confidence"] <= 0.75
    print(f"  PASS: medium data => confidence={r['confidence']:.3f}, level={r['confidence_level']}")

def test_group_confidence():
    section_confs = [
        {
            "confidence": 0.9,
            "confidence_level": "HIGH",
            "confidence_breakdown": {
                "support_count": 15,
                "kpis_with_values": 5,
                "financial_with_amounts": 3,
                "pages_covered": 8,
                "total_pages_in_section": 10,
            },
        },
        {
            "confidence": 0.4,
            "confidence_level": "LOW",
            "confidence_breakdown": {
                "support_count": 3,
                "kpis_with_values": 0,
                "financial_with_amounts": 0,
                "pages_covered": 2,
                "total_pages_in_section": 10,
            },
        },
    ]
    r = _compute_group_confidence(section_confs)
    assert "confidence" in r and "confidence_level" in r and "confidence_breakdown" in r
    # Group aggregates breakdowns with higher caps — result should be positive
    assert r["confidence"] > 0.0, f"Expected positive confidence, got {r['confidence']}"
    print(f"         breakdown: {r['confidence_breakdown']}")
    # Group with mixed HIGH+LOW members should not be HIGH
    assert r["confidence_level"] != "HIGH", f"Mixed group should not be HIGH"
    print(f"  PASS: group confidence={r['confidence']:.3f}, level={r['confidence_level']}")

def test_zero_total_pages():
    """Edge case: total_pages_in_section = 0 should not crash."""
    r = _compute_evidence_confidence([{"finding": "x"}], [], [], [], {1}, 0)
    assert r["confidence"] >= 0
    print(f"  PASS: zero total pages => confidence={r['confidence']:.3f}")

def test_single_section_group():
    """Group with single member should reflect that member's confidence."""
    member = {
        "confidence": 0.8,
        "confidence_level": "HIGH",
        "confidence_breakdown": {
            "support_count": 10,
            "kpis_with_values": 4,
            "financial_with_amounts": 2,
            "pages_covered": 6,
            "total_pages_in_section": 8,
        },
    }
    r = _compute_group_confidence([member])
    assert r["confidence"] > 0, "Single-member group should have positive confidence"
    print(f"  PASS: single-member group => confidence={r['confidence']:.3f}")

def test_empty_group():
    """Empty group should return LOW."""
    r = _compute_group_confidence([])
    assert r["confidence_level"] == "LOW"
    assert r["confidence"] == 0.0
    print(f"  PASS: empty group => confidence={r['confidence']}, level={r['confidence_level']}")

if __name__ == "__main__":
    tests = [
        ("Test 1: Empty data", test_empty_data),
        ("Test 2: Rich data", test_rich_data),
        ("Test 3: Medium data", test_medium_data),
        ("Test 4: Group confidence", test_group_confidence),
        ("Test 5: Zero total pages", test_zero_total_pages),
        ("Test 6: Single section group", test_single_section_group),
        ("Test 7: Empty group", test_empty_group),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            print(f"{name}:")
            fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
