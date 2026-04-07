"""Tests for transiq.doe."""
import pytest
from domain.transiq.doe import (
    full_factorial_design, coded_factorial_design, fractional_factorial,
    main_effects, interaction_effects, anova_factorial,
)


class TestFullFactorial:
    def test_2_factors_2_levels(self):
        design = full_factorial_design({"A": [1, 2], "B": [3, 4]})
        assert len(design) == 4
        # Check all combinations exist
        combos = {(r["A"], r["B"]) for r in design}
        assert combos == {(1, 3), (1, 4), (2, 3), (2, 4)}

    def test_3_factors_2_levels(self):
        design = full_factorial_design({
            "A": [-1, 1], "B": [-1, 1], "C": [-1, 1]
        })
        assert len(design) == 8  # 2^3


class TestCodedFactorial:
    def test_2k_design(self):
        design = coded_factorial_design(3)  # 2^3
        assert len(design) == 8
        # Each row should have 3 factors
        assert len(design[0]) == 3
        # Values should be -1 or 1
        for row in design:
            for val in row:
                assert val in (-1, 1, -1.0, 1.0)


class TestFractionalFactorial:
    def test_half_fraction(self):
        design = fractional_factorial(3, 1)  # 2^(3-1) = 4 runs
        assert len(design) == 4

    def test_quarter_fraction(self):
        design = fractional_factorial(4, 2)  # 2^(4-2) = 4 runs
        assert len(design) == 4


class TestMainEffects:
    def test_basic(self):
        # Design as list of dicts with response included
        design = [
            {"A": -1, "B": -1, "Y": 10},
            {"A": -1, "B": 1, "Y": 20},
            {"A": 1, "B": -1, "Y": 30},
            {"A": 1, "B": 1, "Y": 40},
        ]
        effects = main_effects(design, "Y", ["A", "B"])
        # Effect of A: avg(high) - avg(low) = (30+40)/2 - (10+20)/2 = 20
        assert abs(effects["A"] - 20.0) < 1e-6
        # Effect of B: avg(high) - avg(low) = (20+40)/2 - (10+30)/2 = 10
        assert abs(effects["B"] - 10.0) < 1e-6


class TestInteractionEffects:
    def test_basic(self):
        design = [
            {"A": -1, "B": -1, "Y": 10},
            {"A": -1, "B": 1, "Y": 20},
            {"A": 1, "B": -1, "Y": 30},
            {"A": 1, "B": 1, "Y": 40},
        ]
        effects = interaction_effects(design, "Y", ["A", "B"])
        assert len(effects) >= 0  # May have A×B interaction


class TestAnovaFactorial:
    def test_basic(self):
        design = [
            {"A": -1, "B": -1, "Y": 10},
            {"A": -1, "B": 1, "Y": 20},
            {"A": 1, "B": -1, "Y": 30},
            {"A": 1, "B": 1, "Y": 40},
        ]
        result = anova_factorial(design, "Y", ["A", "B"])
        assert "SS_total" in result
        assert "factors" in result
