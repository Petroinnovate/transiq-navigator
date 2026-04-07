"""Tests for transiq.msa."""
import pytest
from domain.transiq.msa import gage_rr_anova, precision_to_tolerance


class TestGageRR:
    def test_known_data(self):
        # 3D: measurements[part][operator][replicate]
        # 3 parts, 2 operators, 2 replicates
        measurements = [
            # Part 0
            [[10.0, 10.1], [10.1, 10.0]],
            # Part 1
            [[20.0, 20.1], [20.2, 20.0]],
            # Part 2
            [[30.0, 30.2], [30.1, 30.0]],
        ]
        result = gage_rr_anova(measurements)
        assert "variance_components" in result
        assert "ndc" in result
        assert result["ndc"] >= 1

    def test_perfect_measurement(self):
        # All measurements identical per part → repeatability = 0
        measurements = [
            [[10.0, 10.0], [10.0, 10.0]],
            [[20.0, 20.0], [20.0, 20.0]],
        ]
        result = gage_rr_anova(measurements)
        assert result["variance_components"]["Repeatability"] == 0.0

    def test_rating(self):
        # Large operator variation
        measurements = [
            [[10.0, 10.0], [15.0, 15.0]],
            [[20.0, 20.0], [25.0, 25.0]],
        ]
        result = gage_rr_anova(measurements)
        assert result["rating"] in ["Acceptable", "Marginal", "Unacceptable"]


class TestPrecisionToTolerance:
    def test_basic(self):
        # %P/T = (6 * grr_sd) / tolerance * 100
        result = precision_to_tolerance(0.5, 10.0)
        expected = (6 * 0.5) / 10.0 * 100  # = 30.0
        assert abs(result - expected) < 1e-10
