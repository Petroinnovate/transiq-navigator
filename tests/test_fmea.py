"""Tests for transiq.fmea."""
import pytest
from domain.transiq.fmea import compute_rpn, fmea_analysis, sort_failure_modes


class TestComputeRPN:
    def test_basic(self):
        result = compute_rpn(8, 6, 4)
        assert result["RPN"] == 192

    def test_max(self):
        result = compute_rpn(10, 10, 10)
        assert result["RPN"] == 1000
        assert result["risk_level"] == "High"

    def test_min(self):
        result = compute_rpn(1, 1, 1)
        assert result["RPN"] == 1
        assert result["risk_level"] == "Low"


class TestFMEA:
    def test_basic(self):
        modes = [
            {
                "mode": "Seal failure",
                "effect": "Leak",
                "cause": "Wear",
                "severity": 8,
                "occurrence": 6,
                "detection": 4,
            },
            {
                "mode": "Corrosion",
                "effect": "Wall thinning",
                "cause": "H2S exposure",
                "severity": 9,
                "occurrence": 3,
                "detection": 5,
            },
        ]
        result = fmea_analysis(modes)
        assert "failure_modes" in result
        assert "summary" in result
        assert result["summary"]["total"] == 2
        # Sorted by RPN descending: 192 > 135
        assert result["failure_modes"][0]["RPN"] == 192

    def test_risk_levels(self):
        modes = [
            {"mode": "Low", "effect": "e", "cause": "c",
             "severity": 2, "occurrence": 1, "detection": 1},
            {"mode": "High", "effect": "e", "cause": "c",
             "severity": 10, "occurrence": 8, "detection": 7},
        ]
        result = fmea_analysis(modes)
        fmodes = result["failure_modes"]
        low = [m for m in fmodes if m["mode"] == "Low"][0]
        high = [m for m in fmodes if m["mode"] == "High"][0]
        assert low["risk_level"] == "Low"
        assert high["risk_level"] == "High"


class TestSortFailureModes:
    def test_sort_descending(self):
        modes = [
            {"mode": "A", "RPN": 100},
            {"mode": "B", "RPN": 300},
            {"mode": "C", "RPN": 200},
        ]
        sorted_modes = sort_failure_modes(modes)
        assert sorted_modes[0]["mode"] == "B"
        assert sorted_modes[1]["mode"] == "C"
        assert sorted_modes[2]["mode"] == "A"
