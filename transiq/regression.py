"""
Regression and Correlation analysis.

Covers ASQ Handbook Chapter 16: Exploratory Data Analysis, Regression.

Functions
---------
pearson_r           Pearson product-moment correlation coefficient
r_squared           Coefficient of determination R²
linear_regression   Simple linear regression (OLS) y = a + bx
multiple_regression Multiple linear regression (matrix form)
residuals           Compute residuals from a fitted model
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from transiq.statistics import mean as _mean, variance as _var, std_dev as _std
from transiq.utils import validate_numeric


def pearson_r(x: List[float], y: List[float]) -> float:
    """
    Pearson product-moment correlation coefficient.

    r = Σ(xᵢ - x̄)(yᵢ - ȳ) / √[Σ(xᵢ - x̄)² · Σ(yᵢ - ȳ)²]

    Returns value in [-1, 1].
    """
    xv = validate_numeric(x, "x", min_len=2)
    yv = validate_numeric(y, "y", min_len=2)
    if len(xv) != len(yv):
        raise ValueError("x and y must have same length")

    n = len(xv)
    mx, my = _mean(xv), _mean(yv)
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(xv, yv))
    ss_x = sum((xi - mx) ** 2 for xi in xv)
    ss_y = sum((yi - my) ** 2 for yi in yv)

    denom = math.sqrt(ss_x * ss_y)
    if denom == 0:
        return 0.0
    return cov / denom


def r_squared(x: List[float], y: List[float]) -> float:
    """Coefficient of determination R² = r²."""
    r = pearson_r(x, y)
    return r ** 2


def linear_regression(
    x: List[float],
    y: List[float],
) -> Dict[str, float]:
    """
    Simple linear regression: ŷ = a + bx  (OLS fit).

    Parameters
    ----------
    x, y : paired observations

    Returns
    -------
    dict with: slope (b), intercept (a), r, r_squared, std_err_slope,
    std_err_intercept, predictions, residuals
    """
    xv = validate_numeric(x, "x", min_len=2)
    yv = validate_numeric(y, "y", min_len=2)
    if len(xv) != len(yv):
        raise ValueError("x and y must have same length")

    n = len(xv)
    mx, my = _mean(xv), _mean(yv)

    ss_xy = sum((xi - mx) * (yi - my) for xi, yi in zip(xv, yv))
    ss_xx = sum((xi - mx) ** 2 for xi in xv)
    ss_yy = sum((yi - my) ** 2 for yi in yv)

    if ss_xx == 0:
        raise ValueError("No variation in x — cannot fit regression")

    # Slope and intercept
    b = ss_xy / ss_xx
    a = my - b * mx

    # Predictions and residuals
    y_hat = [a + b * xi for xi in xv]
    resid = [yi - yhi for yi, yhi in zip(yv, y_hat)]

    # R and R²
    r = pearson_r(xv, yv)
    r2 = r ** 2

    # Standard errors
    ss_res = sum(ri ** 2 for ri in resid)
    mse = ss_res / (n - 2) if n > 2 else 0.0
    se_b = math.sqrt(mse / ss_xx) if ss_xx > 0 and mse > 0 else 0.0
    se_a = math.sqrt(mse * (1.0 / n + mx ** 2 / ss_xx)) if ss_xx > 0 and mse > 0 else 0.0

    return {
        "slope": round(b, 8),
        "intercept": round(a, 8),
        "r": round(r, 6),
        "r_squared": round(r2, 6),
        "std_err_slope": round(se_b, 8),
        "std_err_intercept": round(se_a, 8),
        "n": n,
        "SS_regression": round(ss_yy - ss_res, 6),
        "SS_residual": round(ss_res, 6),
        "MSE": round(mse, 8),
    }


def predict(slope: float, intercept: float, x_new: List[float]) -> List[float]:
    """Predict y values from fitted regression: ŷ = a + bx."""
    return [intercept + slope * xi for xi in x_new]


def residuals(
    x: List[float],
    y: List[float],
    slope: float,
    intercept: float,
) -> List[float]:
    """Compute residuals: eᵢ = yᵢ - (a + bxᵢ)."""
    return [yi - (intercept + slope * xi) for xi, yi in zip(x, y)]


def multiple_regression(
    X: List[List[float]],
    y: List[float],
) -> Dict[str, object]:
    """
    Multiple linear regression via normal equations: β = (XᵀX)⁻¹Xᵀy.

    Parameters
    ----------
    X : list of lists, shape (n, p) — predictor matrix (no intercept column)
    y : response vector of length n

    Returns
    -------
    dict with: coefficients (including intercept), r_squared, residuals
    """
    n = len(y)
    p = len(X[0]) if X else 0

    # Add intercept column
    X_aug = [[1.0] + row for row in X]
    cols = p + 1

    # XᵀX
    XtX = [[0.0] * cols for _ in range(cols)]
    Xty = [0.0] * cols
    for i in range(n):
        for j in range(cols):
            Xty[j] += X_aug[i][j] * y[i]
            for k in range(cols):
                XtX[j][k] += X_aug[i][j] * X_aug[i][k]

    # Solve via Gaussian elimination (in-place)
    aug = [XtX[i][:] + [Xty[i]] for i in range(cols)]
    for col in range(cols):
        # Partial pivoting
        max_row = max(range(col, cols), key=lambda r: abs(aug[r][col]))
        aug[col], aug[max_row] = aug[max_row], aug[col]
        pivot = aug[col][col]
        if abs(pivot) < 1e-12:
            raise ValueError("Singular matrix — regression cannot be computed")
        for j in range(col, cols + 1):
            aug[col][j] /= pivot
        for i in range(cols):
            if i != col:
                factor = aug[i][col]
                for j in range(col, cols + 1):
                    aug[i][j] -= factor * aug[col][j]

    coefficients = [aug[i][cols] for i in range(cols)]

    # Predictions and R²
    y_hat = [sum(c * x for c, x in zip(coefficients, X_aug[i])) for i in range(n)]
    resid = [y[i] - y_hat[i] for i in range(n)]
    my = sum(y) / n
    ss_tot = sum((yi - my) ** 2 for yi in y)
    ss_res = sum(r ** 2 for r in resid)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        "coefficients": [round(c, 8) for c in coefficients],
        "intercept": round(coefficients[0], 8),
        "slopes": [round(c, 8) for c in coefficients[1:]],
        "r_squared": round(r2, 6),
        "n": n,
        "p": p,
    }
