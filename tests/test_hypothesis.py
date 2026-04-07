"""Tests for transiq.hypothesis."""
import pytest
from transiq.hypothesis import (
    z_test, t_test_one_sample, t_test_two_sample, t_test_paired,
    chi2_goodness_of_fit, chi2_independence, f_test_variance,
    anova_oneway,
)


class TestZTest:
    def test_known_result(self):
        # 25 samples with mean=105 vs population 100, sigma=15 → z≈1.667
        data = [105.0] * 25  # synthetic: all equal to 105
        result = z_test(data, 100, 15)
        assert abs(result["z_statistic"] - (105 - 100) / (15 / 25**0.5)) < 0.01
        assert result["p_value"] < 0.10

    def test_no_difference(self):
        data = [100.0] * 25
        result = z_test(data, 100, 15)
        assert abs(result["z_statistic"]) < 1e-10


class TestTTestOneSample:
    def test_basic(self):
        data = [5.1, 4.9, 5.0, 5.2, 4.8, 5.1, 5.0, 4.9]
        result = t_test_one_sample(data, 5.0)
        assert "t_statistic" in result
        assert "p_value" in result
        assert "df" in result
        assert result["df"] == 7

    def test_significant_difference(self):
        data = [10, 11, 12, 13, 14, 15]
        result = t_test_one_sample(data, 5.0)
        assert result["p_value"] < 0.001


class TestTTestTwoSample:
    def test_equal_means(self):
        a = [5.0, 5.1, 4.9, 5.0, 5.1]
        b = [5.0, 5.0, 5.1, 4.9, 5.0]
        result = t_test_two_sample(a, b)
        assert abs(result["t_statistic"]) < 1.0
        assert result["p_value"] > 0.05

    def test_different_means(self):
        a = [10, 11, 12, 13, 14]
        b = [1, 2, 3, 4, 5]
        result = t_test_two_sample(a, b)
        assert result["p_value"] < 0.001


class TestTTestPaired:
    def test_basic(self):
        before = [200, 210, 190, 220, 205]
        after = [180, 195, 185, 200, 190]
        result = t_test_paired(before, after)
        assert result["df"] == 4
        assert result["t_statistic"] > 0  # before > after


class TestChi2GoodnessOfFit:
    def test_uniform(self):
        observed = [25, 25, 25, 25]
        expected = [25, 25, 25, 25]
        result = chi2_goodness_of_fit(observed, expected)
        assert abs(result["chi2_statistic"]) < 1e-10

    def test_significant(self):
        observed = [50, 10, 10, 30]
        expected = [25, 25, 25, 25]
        result = chi2_goodness_of_fit(observed, expected)
        assert result["chi2_statistic"] > 10
        assert result["p_value"] < 0.05


class TestChi2Independence:
    def test_basic(self):
        table = [[10, 20], [30, 40]]
        result = chi2_independence(table)
        assert "chi2_statistic" in result
        assert "p_value" in result
        assert result["df"] == 1


class TestFTest:
    def test_equal_variance(self):
        a = [5.0, 5.1, 4.9, 5.0, 5.1]
        b = [5.0, 5.0, 5.1, 4.9, 5.0]
        result = f_test_variance(a, b)
        assert result["p_value"] > 0.05

    def test_different_variance(self):
        a = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        b = [4.9, 5.0, 5.1, 5.0, 5.0, 5.1, 4.9, 5.0, 5.0, 5.1]
        result = f_test_variance(a, b)
        assert result["f_statistic"] > 1.0


class TestANOVA:
    def test_no_difference(self):
        result = anova_oneway([5, 5, 5], [5, 5, 5], [5, 5, 5])
        # F should be 0 or near 0 when all groups identical
        assert result["F_statistic"] == 0.0 or result["p_value"] > 0.99

    def test_significant_difference(self):
        result = anova_oneway([1, 2, 3], [10, 11, 12], [20, 21, 22])
        assert result["F_statistic"] > 10
        assert result["p_value"] < 0.01
        assert result["df_between"] == 2
        assert result["df_within"] == 6
