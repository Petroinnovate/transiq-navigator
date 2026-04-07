"""Integration tests for Document Coverage Engine (Phase 13)."""

from section_analyzer import (
    _extract_used_pages,
    _find_page_gaps,
    _collect_pages_recursive,
    DocumentBrain,
    SectionNode,
)


def _make_brain(total_pages, sections_data):
    """Helper: create a minimal DocumentBrain with specified chunks and section results."""
    chunks = [f"[Page {i+1}] Content for page {i+1}" for i in range(total_pages)]
    brain = DocumentBrain(chunks, source_type="TEST")

    for sid, sdata in sections_data.items():
        node = SectionNode(
            id=sid,
            title=sdata.get("title", f"Section {sid}"),
            text="",
            depth=0,
            start_index=sdata["start"],
            end_index=sdata["end"],
        )
        brain.sections[sid] = node
        brain.results["sections"][sid] = sdata.get("results", {})

    return brain


def test_full_coverage():
    """All pages referenced => GOOD coverage."""
    brain = _make_brain(10, {
        "S001": {
            "title": "Section 1", "start": 1, "end": 5,
            "results": {
                "keyFindings": [
                    {"finding": f"F{i}", "source_pages": [i]} for i in range(1, 6)
                ],
                "kpis": [], "risks": [],
            },
        },
        "S002": {
            "title": "Section 2", "start": 6, "end": 10,
            "results": {
                "keyFindings": [
                    {"finding": f"F{i}", "source_pages": [i]} for i in range(6, 11)
                ],
                "kpis": [], "risks": [],
            },
        },
    })
    cov = _extract_used_pages(brain)
    assert cov["total_pages"] == 10
    assert cov["used_page_count"] == 10
    assert cov["page_coverage_pct"] == 100.0
    assert cov["coverage_status"] == "GOOD"
    assert cov["unused_page_ranges"] == []
    print(f"  PASS: full coverage => {cov['page_coverage_pct']}% ({cov['coverage_status']})")


def test_partial_coverage():
    """~50% pages referenced => PARTIAL."""
    brain = _make_brain(20, {
        "S001": {
            "title": "Section 1", "start": 1, "end": 10,
            "results": {
                "keyFindings": [
                    {"finding": "F1", "source_pages": [1, 2, 3, 4, 5]},
                    {"finding": "F2", "source_pages": [6, 7, 8, 9, 10]},
                ],
                "kpis": [], "risks": [],
            },
        },
        "S002": {
            "title": "Section 2 (no data)", "start": 11, "end": 20,
            "results": {"keyFindings": [], "kpis": [], "risks": []},
        },
    })
    cov = _extract_used_pages(brain)
    assert cov["total_pages"] == 20
    assert cov["used_page_count"] == 10
    assert cov["page_coverage_pct"] == 50.0
    assert cov["coverage_status"] == "PARTIAL"
    assert len(cov["unused_page_ranges"]) > 0
    print(f"  PASS: partial coverage => {cov['page_coverage_pct']}% ({cov['coverage_status']})")
    print(f"         unused: {cov['unused_page_ranges']}")


def test_bad_coverage():
    """Only 3 of 100 pages => BAD."""
    brain = _make_brain(100, {
        "S001": {
            "title": "Tiny section", "start": 1, "end": 5,
            "results": {
                "keyFindings": [
                    {"finding": "F1", "source_pages": [1, 2, 3]},
                ],
                "kpis": [], "risks": [],
            },
        },
    })
    cov = _extract_used_pages(brain)
    assert cov["total_pages"] == 100
    assert cov["used_page_count"] == 3
    assert cov["page_coverage_pct"] == 3.0
    assert cov["coverage_status"] == "BAD"
    print(f"  PASS: bad coverage => {cov['page_coverage_pct']}% ({cov['coverage_status']})")


def test_zero_pages():
    """Empty document => 0% but no crash."""
    brain = _make_brain(0, {})
    cov = _extract_used_pages(brain)
    assert cov["total_pages"] == 0
    assert cov["used_page_count"] == 0
    assert cov["page_coverage_pct"] == 0.0
    assert cov["coverage_status"] == "BAD"
    print(f"  PASS: zero pages => {cov['page_coverage_pct']}% ({cov['coverage_status']})")


def test_per_section_breakdown():
    """Each section should report its own coverage."""
    brain = _make_brain(20, {
        "S001": {
            "title": "Rich section", "start": 1, "end": 10,
            "results": {
                "keyFindings": [{"finding": f"F{i}", "source_pages": [i]} for i in range(1, 11)],
                "kpis": [], "risks": [],
            },
        },
        "S002": {
            "title": "Empty section", "start": 11, "end": 20,
            "results": {"keyFindings": [], "kpis": [], "risks": []},
        },
    })
    cov = _extract_used_pages(brain)
    assert len(cov["per_section"]) == 2

    s1 = cov["per_section"][0]
    assert s1["pages_used"] == 10
    assert s1["coverage_pct"] == 100.0

    s2 = cov["per_section"][1]
    assert s2["pages_used"] == 0
    assert s2["coverage_pct"] == 0.0

    print(f"  PASS: per-section breakdown:")
    for s in cov["per_section"]:
        print(f"         {s['title']}: {s['pages_used']}/{s['pages_in_range']} = {s['coverage_pct']}%")


def test_find_page_gaps():
    """Gap finder should identify contiguous unused ranges."""
    used = {1, 2, 3, 7, 8, 15}
    total = 20
    gaps = _find_page_gaps(used, total)
    assert "Pages 4-6" in gaps
    assert "Pages 9-14" in gaps
    assert "Pages 16-20" in gaps
    print(f"  PASS: gaps found: {gaps}")


def test_financial_items_coverage():
    """Financial items with source_pages should count."""
    brain = _make_brain(10, {
        "S001": {
            "title": "Financial section", "start": 1, "end": 10,
            "results": {
                "keyFindings": [],
                "kpis": [],
                "risks": [],
                "financialImpact": {
                    "identified": True,
                    "items": [
                        {"description": "Cost saving", "amount": 50000, "source_pages": [3, 4, 5]},
                        {"description": "Capital", "amount": 100000, "source_pages": [8, 9]},
                    ],
                },
            },
        },
    })
    cov = _extract_used_pages(brain)
    assert cov["used_page_count"] == 5  # pages 3,4,5,8,9
    assert cov["page_coverage_pct"] == 50.0
    print(f"  PASS: financial items coverage => {cov['used_page_count']} pages used")


def test_collect_pages_recursive():
    """Recursive collector should find nested source_pages."""
    pages = set()
    obj = {
        "phase": "define",
        "problemStatement": "test",
        "source_pages": [1, 2],
        "nested": {
            "items": [
                {"finding": "x", "source_pages": [5, 6]},
                {"finding": "y"},
            ],
            "deep": {"source_pages": [10]},
        },
        "list_items": [
            {"source_pages": [15, 16]},
            "plain string",
        ],
    }
    _collect_pages_recursive(obj, pages)
    assert pages == {1, 2, 5, 6, 10, 15, 16}
    print(f"  PASS: recursive collection found {len(pages)} pages: {sorted(pages)}")


def test_out_of_range_pages_clamped():
    """Pages outside valid range should be excluded."""
    brain = _make_brain(10, {
        "S001": {
            "title": "Section 1", "start": 1, "end": 10,
            "results": {
                "keyFindings": [
                    {"finding": "F1", "source_pages": [1, 2, 999, -1, 0]},
                ],
                "kpis": [], "risks": [],
            },
        },
    })
    cov = _extract_used_pages(brain)
    assert cov["used_page_count"] == 2  # only 1,2 are valid
    print(f"  PASS: out-of-range clamped => {cov['used_page_count']} valid pages")


if __name__ == "__main__":
    tests = [
        ("Test 1: Full coverage (GOOD)", test_full_coverage),
        ("Test 2: Partial coverage", test_partial_coverage),
        ("Test 3: Bad coverage", test_bad_coverage),
        ("Test 4: Zero pages", test_zero_pages),
        ("Test 5: Per-section breakdown", test_per_section_breakdown),
        ("Test 6: Gap finder", test_find_page_gaps),
        ("Test 7: Financial items", test_financial_items_coverage),
        ("Test 8: Recursive collector", test_collect_pages_recursive),
        ("Test 9: Out-of-range clamped", test_out_of_range_pages_clamped),
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
            import traceback
            traceback.print_exc()
            failed += 1
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
