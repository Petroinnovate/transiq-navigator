"""Tests for transiq.statistics."""
import math
import pytest
from transiq.statistics import (
    mean, variance, std_dev, median, mode, percentile, range_, iqr,
    pdf_normal, cdf_normal, z_score, inverse_normal,
    pmf_binomial, cdf_binomial, pmf_poisson, cdf_poisson,
    pdf_exponential, cdf_exponential,
)


class TestDescriptive:
    def test_mean(self):
        assert mean([1, 2, 3, 4, 5]) == 3.0

    def test_variance_population(self):
        assert variance([2, 4, 4, 4, 5, 5, 7, 9]) == 4.0

    def test_variance_sample(self):
        v = variance([2, 4, 4, 4, 5, 5, 7, 9], ddof=1)
        assert abs(v - 4.571428) < 1e-4

    def test_std_dev(self):
        assert abs(std_dev([2, 4, 4, 4, 5, 5, 7, 9]) - 2.0) < 1e-10

    def test_median_odd(self):
        assert median([1, 3, 5]) == 3.0

    def test_median_even(self):
        assert median([1, 2, 3, 4]) == 2.5

    def test_mode_single(self):
        assert mode([1, 2, 2, 3]) == [2.0]

    def test_mode_multiple(self):
        assert mode([1, 1, 2, 2, 3]) == [1.0, 2.0]

    def test_percentile_50(self):
        assert abs(percentile([1, 2, 3, 4, 5], 50) - 3.0) < 1e-10

    def test_range(self):
        assert range_([3, 7, 2, 9]) == 7.0

    def test_iqr(self):
        data = list(range(1, 101))
        q = iqr(data)
        assert abs(q - 50.0) < 1.0  # approx


class TestNormal:
    def test_pdf_at_mean(self):
        p = pdf_normal(0.0, 0.0, 1.0)
        assert abs(p - 0.39894228) < 1e-6

    def test_cdf_at_zero(self):
        assert abs(cdf_normal(0.0) - 0.5) < 1e-10

    def test_cdf_at_minus_inf(self):
        assert cdf_normal(-10.0) < 1e-10

    def test_cdf_at_plus_inf(self):
        assert cdf_normal(10.0) > 1.0 - 1e-10

    def test_z_score(self):
        assert abs(z_score(75, 70, 10) - 0.5) < 1e-10

    def test_inverse_normal(self):
        # Φ⁻¹(0.975) ≈ 1.96
        z = inverse_normal(0.975)
        assert abs(z - 1.96) < 0.02


class TestBinomial:
    def test_pmf(self):
        # P(X=3 | n=10, p=0.5) ≈ 0.1172
        assert abs(pmf_binomial(3, 10, 0.5) - 0.1171875) < 1e-6

    def test_cdf(self):
        # P(X<=5 | n=10, p=0.5) = 0.623046875
        assert abs(cdf_binomial(5, 10, 0.5) - 0.623046875) < 1e-6


class TestPoisson:
    def test_pmf(self):
        # P(X=3 | λ=2) ≈ 0.1804
        assert abs(pmf_poisson(3, 2.0) - 0.18045) < 1e-4

    def test_cdf(self):
        # P(X<=3 | λ=2) ≈ 0.8571
        assert abs(cdf_poisson(3, 2.0) - 0.8571) < 1e-3


class TestExponential:
    def test_pdf(self):
        assert abs(pdf_exponential(1.0, 1.0) - math.exp(-1)) < 1e-10

    def test_cdf(self):
        assert abs(cdf_exponential(1.0, 1.0) - (1 - math.exp(-1))) < 1e-10

    def test_cdf_negative(self):
        assert cdf_exponential(-1.0, 1.0) == 0.0
