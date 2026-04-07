"""Tests for transiq.dashboard."""
import pytest
from domain.transiq.dashboard import compute_metrics
from domain.transiq import statistics, process_capability


def test_compute_metrics_basic():
    data = [2.0, 4.0, 6.0]
    result = compute_metrics(data)
    assert isinstance(result, dict)
    # Mean should be 4.0 for [2,4,6]
    assert pytest.approx(result['mean'], rel=1e-9) == statistics.mean(data)
    # Cp for USL=10, LSL=0, sigma=2 is (10-0)/(6*2) = 0.8333...
    expected_cp = process_capability.cp(10, 0, 2)
    assert pytest.approx(result['cp'], rel=1e-9) == expected_cp


def test_compute_metrics_single():
    data = [5.0]
    result = compute_metrics(data)
    assert result['mean'] == 5.0


def test_compute_metrics_empty():
    data = []
    with pytest.raises((ZeroDivisionError, ValueError)):
        compute_metrics(data)
