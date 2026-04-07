"""Tests for transiq.regression."""
import pytest
from domain.transiq.regression import (
    pearson_r, r_squared, linear_regression, predict, residuals,
    multiple_regression,
)


class TestPearsonR:
    def test_perfect_positive(self):
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        assert abs(pearson_r(x, y) - 1.0) < 1e-10

    def test_perfect_negative(self):
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]
        assert abs(pearson_r(x, y) - (-1.0)) < 1e-10

    def test_no_correlation(self):
        x = [1, 2, 3, 4, 5]
        y = [5, 1, 4, 2, 3]
        r = pearson_r(x, y)
        assert abs(r) < 0.5


class TestRSquared:
    def test_perfect_fit(self):
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        assert abs(r_squared(x, y) - 1.0) < 1e-10


class TestLinearRegression:
    def test_known_line(self):
        # y = 2x + 1
        x = [1, 2, 3, 4, 5]
        y = [3, 5, 7, 9, 11]
        result = linear_regression(x, y)
        assert abs(result["slope"] - 2.0) < 1e-10
        assert abs(result["intercept"] - 1.0) < 1e-10
        assert abs(result["r_squared"] - 1.0) < 1e-10

    def test_predict(self):
        x = [1, 2, 3, 4, 5]
        y = [3, 5, 7, 9, 11]
        result = linear_regression(x, y)
        # predict(slope, intercept, x_new)
        pred = predict(result["slope"], result["intercept"], [6, 7])
        assert abs(pred[0] - 13.0) < 1e-10
        assert abs(pred[1] - 15.0) < 1e-10


class TestResiduals:
    def test_perfect_fit_zero_residuals(self):
        x = [1, 2, 3, 4, 5]
        y = [3, 5, 7, 9, 11]
        result = linear_regression(x, y)
        # residuals(x, y, slope, intercept)
        res = residuals(x, y, result["slope"], result["intercept"])
        for r in res:
            assert abs(r) < 1e-10


class TestMultipleRegression:
    def test_two_predictors(self):
        # y = 1 + 2*x1 + 3*x2
        X = [[1, 1], [2, 1], [1, 2], [2, 2], [3, 1], [1, 3]]
        y = [6, 8, 9, 11, 10, 12]
        result = multiple_regression(X, y)
        assert abs(result["intercept"] - 1.0) < 1e-6
        assert abs(result["slopes"][0] - 2.0) < 1e-6
        assert abs(result["slopes"][1] - 3.0) < 1e-6
