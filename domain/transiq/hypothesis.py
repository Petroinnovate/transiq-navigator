"""
Hypothesis testing functions.

Covers ASQ Handbook Chapter 17: Hypothesis Testing.

Tests
-----
z_test               One-sample z-test (known σ)
t_test_one_sample    One-sample t-test (unknown σ)
t_test_two_sample    Two-sample t-test (independent)
t_test_paired        Paired t-test
chi2_goodness_of_fit Chi-square goodness-of-fit
chi2_independence    Chi-square test of independence
f_test_variance      F-test for equality of variances
anova_oneway         One-way ANOVA (F-test)
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from domain.transiq.statistics import mean as _mean, variance as _var, std_dev as _std, cdf_normal
from domain.transiq.utils import validate_numeric


# ---------------------------------------------------------------------------
# Helper: approximate t-distribution and F-distribution CDFs
# Uses normal approximation for large df; exact for small df via
# regularised incomplete beta function approximation.
# ---------------------------------------------------------------------------

def _beta_cf(a: float, b: float, x: float, max_iter: int = 200) -> float:
    """Continued-fraction evaluation for regularised incomplete beta."""
    tiny = 1e-30
    f = 1.0
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    f = d
    for m in range(1, max_iter + 1):
        # even step
        num = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
        d = 1.0 + num * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + num / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        f *= d * c
        # odd step
        num = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + num / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        f *= delta
        if abs(delta - 1.0) < 1e-10:
            break
    return f


def _regularised_beta(x: float, a: float, b: float) -> float:
    """Regularised incomplete beta function I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    ln_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log(1.0 - x) - ln_beta) / a
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_cf(a, b, x)
    else:
        return 1.0 - (math.exp(a * math.log(x) + b * math.log(1 - x) - ln_beta) / b) * _beta_cf(b, a, 1 - x)


def _cdf_t(t_val: float, df: float) -> float:
    """CDF of Student's t-distribution with df degrees of freedom."""
    x = df / (df + t_val * t_val)
    ib = _regularised_beta(x, df / 2.0, 0.5)
    return 0.5 * (1.0 + (1.0 - ib) * (1.0 if t_val >= 0 else -1.0))


def _cdf_f(f_val: float, df1: float, df2: float) -> float:
    """CDF of F-distribution with (df1, df2) degrees of freedom."""
    if f_val <= 0:
        return 0.0
    x = df1 * f_val / (df1 * f_val + df2)
    return _regularised_beta(x, df1 / 2.0, df2 / 2.0)


def _cdf_chi2(x: float, df: float) -> float:
    """CDF of chi-square distribution (chi2 = gamma(df/2, 2))."""
    if x <= 0:
        return 0.0
    return _regularised_beta(x / (x + df), df / 2.0, 0.5) if x < df else \
        1.0 - _regularised_beta(df / (x + df), 0.5, df / 2.0) if x != df else \
        _regularised_beta(0.5, df / 2.0, 0.5)


def _upper_incomplete_gamma(s: float, x: float) -> float:
    """Lower regularised incomplete gamma P(s,x) via series expansion."""
    if x < 0:
        return 0.0
    if x == 0:
        return 0.0
    ap = s
    total = 1.0 / s
    term = 1.0 / s
    for _ in range(300):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * 1e-12:
            break
    return total * math.exp(-x + s * math.log(x) - math.lgamma(s))


def cdf_chi2(x: float, df: int) -> float:
    """CDF of chi-square distribution using lower regularised incomplete gamma."""
    if x <= 0:
        return 0.0
    return _upper_incomplete_gamma(df / 2.0, x / 2.0)


# ---------------------------------------------------------------------------
# z-test (known population σ)
# ---------------------------------------------------------------------------

def z_test(
    data: List[float],
    mu_0: float,
    sigma: float,
    alternative: str = "two-sided",
) -> Dict[str, float]:
    """
    One-sample z-test for population mean (σ known).

    H₀: μ = μ₀
    H₁: μ ≠ μ₀ (or < or >)

    Parameters
    ----------
    data : sample values
    mu_0 : hypothesised mean
    sigma : known population σ
    alternative : "two-sided" | "less" | "greater"
    """
    vals = validate_numeric(data, "data")
    n = len(vals)
    x_bar = _mean(vals)
    z = (x_bar - mu_0) / (sigma / math.sqrt(n))

    if alternative == "two-sided":
        p_value = 2.0 * (1.0 - cdf_normal(abs(z)))
    elif alternative == "less":
        p_value = cdf_normal(z)
    elif alternative == "greater":
        p_value = 1.0 - cdf_normal(z)
    else:
        raise ValueError(f"alternative must be 'two-sided', 'less', or 'greater'")

    return {
        "z_statistic": round(z, 6),
        "p_value": round(p_value, 8),
        "x_bar": round(x_bar, 6),
        "n": n,
        "mu_0": mu_0,
        "sigma": sigma,
        "alternative": alternative,
    }


# ---------------------------------------------------------------------------
# t-tests
# ---------------------------------------------------------------------------

def t_test_one_sample(
    data: List[float],
    mu_0: float,
    alternative: str = "two-sided",
) -> Dict[str, float]:
    """
    One-sample t-test (σ unknown).

    t = (x̄ - μ₀) / (s / √n),  df = n - 1
    """
    vals = validate_numeric(data, "data", min_len=2)
    n = len(vals)
    x_bar = _mean(vals)
    s = _std(vals, ddof=1)
    if s == 0:
        raise ValueError("Sample standard deviation is zero — cannot compute t-test")
    t = (x_bar - mu_0) / (s / math.sqrt(n))
    df = n - 1

    if alternative == "two-sided":
        p_value = 2.0 * (1.0 - _cdf_t(abs(t), df))
    elif alternative == "less":
        p_value = _cdf_t(t, df)
    elif alternative == "greater":
        p_value = 1.0 - _cdf_t(t, df)
    else:
        raise ValueError(f"alternative must be 'two-sided', 'less', or 'greater'")

    return {
        "t_statistic": round(t, 6),
        "p_value": round(max(0.0, min(1.0, p_value)), 8),
        "df": df,
        "x_bar": round(x_bar, 6),
        "s": round(s, 6),
        "n": n,
        "mu_0": mu_0,
        "alternative": alternative,
    }


def t_test_two_sample(
    data1: List[float],
    data2: List[float],
    equal_var: bool = True,
    alternative: str = "two-sided",
) -> Dict[str, float]:
    """
    Two-sample t-test (independent samples).

    If equal_var=True: pooled variance (Student's t-test).
    If equal_var=False: Welch's t-test (unequal variances).
    """
    v1 = validate_numeric(data1, "data1", min_len=2)
    v2 = validate_numeric(data2, "data2", min_len=2)
    n1, n2 = len(v1), len(v2)
    x1, x2 = _mean(v1), _mean(v2)
    s1, s2 = _var(v1, ddof=1), _var(v2, ddof=1)

    if equal_var:
        # Pooled variance
        sp2 = ((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2)
        se = math.sqrt(sp2 * (1.0 / n1 + 1.0 / n2))
        df = n1 + n2 - 2
    else:
        # Welch's approximation
        se = math.sqrt(s1 / n1 + s2 / n2)
        if se == 0:
            raise ValueError("Both samples have zero variance")
        num = (s1 / n1 + s2 / n2) ** 2
        den = (s1 / n1) ** 2 / (n1 - 1) + (s2 / n2) ** 2 / (n2 - 1)
        df = num / den

    if se == 0:
        raise ValueError("Standard error is zero — cannot compute t-test")
    t = (x1 - x2) / se

    if alternative == "two-sided":
        p_value = 2.0 * (1.0 - _cdf_t(abs(t), df))
    elif alternative == "less":
        p_value = _cdf_t(t, df)
    elif alternative == "greater":
        p_value = 1.0 - _cdf_t(t, df)
    else:
        raise ValueError("alternative must be 'two-sided', 'less', or 'greater'")

    return {
        "t_statistic": round(t, 6),
        "p_value": round(max(0.0, min(1.0, p_value)), 8),
        "df": round(df, 2),
        "x1_bar": round(x1, 6),
        "x2_bar": round(x2, 6),
        "n1": n1,
        "n2": n2,
        "alternative": alternative,
    }


def t_test_paired(
    data1: List[float],
    data2: List[float],
    alternative: str = "two-sided",
) -> Dict[str, float]:
    """
    Paired t-test (matched samples).

    Computes differences dᵢ = x1ᵢ - x2ᵢ and performs one-sample t-test on d.
    """
    v1 = validate_numeric(data1, "data1")
    v2 = validate_numeric(data2, "data2")
    if len(v1) != len(v2):
        raise ValueError("Paired samples must have equal length")
    diffs = [a - b for a, b in zip(v1, v2)]
    result = t_test_one_sample(diffs, mu_0=0.0, alternative=alternative)
    result["mean_diff"] = round(_mean(diffs), 6)
    return result


# ---------------------------------------------------------------------------
# Chi-square tests
# ---------------------------------------------------------------------------

def chi2_goodness_of_fit(
    observed: List[int],
    expected: List[float],
) -> Dict[str, float]:
    """
    Chi-square goodness-of-fit test.

    χ² = Σ (Oᵢ - Eᵢ)² / Eᵢ,  df = k - 1
    """
    if len(observed) != len(expected):
        raise ValueError("observed and expected must have same length")
    k = len(observed)
    chi2 = sum((o - e) ** 2 / e for o, e in zip(observed, expected) if e > 0)
    df = k - 1
    p_value = 1.0 - cdf_chi2(chi2, df)

    return {
        "chi2_statistic": round(chi2, 6),
        "p_value": round(max(0.0, min(1.0, p_value)), 8),
        "df": df,
    }


def chi2_independence(
    contingency_table: List[List[int]],
) -> Dict[str, float]:
    """
    Chi-square test of independence on a contingency table.

    Parameters
    ----------
    contingency_table : list of lists (rows × columns of observed counts)

    Returns chi2, p_value, df, expected frequencies.
    """
    rows = len(contingency_table)
    cols = len(contingency_table[0])
    total = sum(sum(row) for row in contingency_table)
    row_totals = [sum(row) for row in contingency_table]
    col_totals = [sum(contingency_table[r][c] for r in range(rows)) for c in range(cols)]

    expected = [[row_totals[r] * col_totals[c] / total for c in range(cols)] for r in range(rows)]

    chi2 = 0.0
    for r in range(rows):
        for c in range(cols):
            e = expected[r][c]
            if e > 0:
                chi2 += (contingency_table[r][c] - e) ** 2 / e

    df = (rows - 1) * (cols - 1)
    p_value = 1.0 - cdf_chi2(chi2, df)

    return {
        "chi2_statistic": round(chi2, 6),
        "p_value": round(max(0.0, min(1.0, p_value)), 8),
        "df": df,
        "expected": [[round(e, 4) for e in row] for row in expected],
    }


# ---------------------------------------------------------------------------
# F-test
# ---------------------------------------------------------------------------

def f_test_variance(
    data1: List[float],
    data2: List[float],
) -> Dict[str, float]:
    """
    F-test for equality of two variances.

    F = s₁² / s₂²  (larger variance in numerator)
    """
    v1 = validate_numeric(data1, "data1", min_len=2)
    v2 = validate_numeric(data2, "data2", min_len=2)
    s1_sq = _var(v1, ddof=1)
    s2_sq = _var(v2, ddof=1)

    if s1_sq >= s2_sq:
        f_stat = s1_sq / s2_sq if s2_sq > 0 else float("inf")
        df1 = len(v1) - 1
        df2 = len(v2) - 1
    else:
        f_stat = s2_sq / s1_sq if s1_sq > 0 else float("inf")
        df1 = len(v2) - 1
        df2 = len(v1) - 1

    p_value = 2.0 * (1.0 - _cdf_f(f_stat, df1, df2))
    p_value = min(1.0, p_value)

    return {
        "f_statistic": round(f_stat, 6),
        "p_value": round(max(0.0, p_value), 8),
        "df1": df1,
        "df2": df2,
        "s1_sq": round(s1_sq, 6),
        "s2_sq": round(s2_sq, 6),
    }


# ---------------------------------------------------------------------------
# One-way ANOVA
# ---------------------------------------------------------------------------

def anova_oneway(*groups: List[float]) -> Dict[str, float]:
    """
    One-way ANOVA (Analysis of Variance).

    Tests H₀: all group means are equal.

    Parameters
    ----------
    *groups : variable number of sample lists (one per treatment level)

    Returns
    -------
    dict with F_statistic, p_value, df_between, df_within, SS_between,
    SS_within, MS_between, MS_within, group_means.
    """
    k = len(groups)
    if k < 2:
        raise ValueError("ANOVA requires at least 2 groups")

    validated = [validate_numeric(list(g), f"group_{i}", min_len=1) for i, g in enumerate(groups)]
    ns = [len(g) for g in validated]
    N = sum(ns)
    group_means = [_mean(g) for g in validated]
    grand_mean = sum(sum(g) for g in validated) / N

    # Sum of squares
    ss_between = sum(n * (m - grand_mean) ** 2 for n, m in zip(ns, group_means))
    ss_within = sum(
        sum((x - m) ** 2 for x in g)
        for g, m in zip(validated, group_means)
    )

    df_between = k - 1
    df_within = N - k
    ms_between = ss_between / df_between
    ms_within = ss_within / df_within if df_within > 0 else 0.0

    f_stat = ms_between / ms_within if ms_within > 0 else float("inf")
    p_value = 1.0 - _cdf_f(f_stat, df_between, df_within)

    return {
        "F_statistic": round(f_stat, 6),
        "p_value": round(max(0.0, min(1.0, p_value)), 8),
        "df_between": df_between,
        "df_within": df_within,
        "SS_between": round(ss_between, 6),
        "SS_within": round(ss_within, 6),
        "MS_between": round(ms_between, 6),
        "MS_within": round(ms_within, 6),
        "grand_mean": round(grand_mean, 6),
        "group_means": [round(m, 6) for m in group_means],
        "group_sizes": ns,
    }
