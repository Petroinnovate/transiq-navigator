"""Tests for transiq.lean_tools."""
import pytest
from transiq.lean_tools import (
    calculate_oee, takt_time, cycle_time_analysis,
    calculate_throughput, identify_waste, kaizen_event,
    value_stream_metrics,
)


class TestOEE:
    def test_perfect_oee(self):
        result = calculate_oee(
            availability=1.0, performance=1.0, quality=1.0
        )
        assert abs(result["OEE_fraction"] - 1.0) < 1e-10
        assert result["rating"] == "World Class"

    def test_typical_oee(self):
        result = calculate_oee(
            availability=0.90, performance=0.95, quality=0.99
        )
        expected = 0.90 * 0.95 * 0.99
        assert abs(result["OEE_fraction"] - expected) < 1e-3

    def test_keys(self):
        result = calculate_oee(0.9, 0.95, 0.99)
        assert "availability_pct" in result
        assert "OEE_pct" in result
        assert "rating" in result


class TestTaktTime:
    def test_basic(self):
        result = takt_time(available_time=480, demand=240)
        assert abs(result["takt_time"] - 2.0) < 1e-10

    def test_returns_dict(self):
        result = takt_time(available_time=480, demand=240)
        assert "takt_time" in result
        assert "time_unit" in result


class TestCycleTime:
    def test_basic(self):
        steps = [
            {"name": "Step1", "time": 10, "type": "VA"},
            {"name": "Step2", "time": 12, "type": "NVA"},
            {"name": "Step3", "time": 11, "type": "VA"},
        ]
        result = cycle_time_analysis(steps)
        assert "total_time" in result
        assert result["total_time"] == 33
        assert result["va_time"] == 21


class TestThroughput:
    def test_single_step(self):
        result = calculate_throughput([0.95])
        assert abs(result["RTY"] - 0.95) < 1e-10

    def test_multi_step(self):
        result = calculate_throughput([0.95, 0.90, 0.99])
        expected_rty = 0.95 * 0.90 * 0.99
        assert abs(result["RTY"] - expected_rty) < 1e-10


class TestIdentifyWaste:
    def test_known_waste(self):
        observations = [
            {"description": "Waiting for approval", "category": "W"},
            {"description": "Rework defective parts", "category": "D"},
        ]
        result = identify_waste(observations)
        assert "counts" in result
        assert result["total_observations"] == 2


class TestKaizen:
    def test_basic(self):
        result = kaizen_event(
            problem="High defect rate",
            current_state={"defect_rate": 0.05},
            target_state={"defect_rate": 0.01},
            team=["Alice", "Bob"],
        )
        assert "problem_statement" in result
        assert "phases" in result


class TestVSM:
    def test_basic(self):
        # value_stream_metrics(process_time, lead_time)
        result = value_stream_metrics(45, 225)
        assert result["process_time"] == 45
        assert result["lead_time"] == 225
        assert result["pce"] > 0
        assert abs(result["pce"] - 45/225) < 1e-10
