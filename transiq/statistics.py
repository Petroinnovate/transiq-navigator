"""
Descriptive statistics and probability distributions.

Covers ASQ Handbook Chapters 11–13: Probability, Distributions, Data Summarisation.

Functions
---------
mean, variance, std_dev         Basic descriptive statistics
median, mode, percentile        Location / spread measures
pdf_normal, cdf_normal          Gaussian distribution
pdf_poisson, cdf_poisson        Poisson distribution
pmf_binomial, cdf_binomial      Binomial distribution
pdf_exponential, cdf_exponential Exponential distribution
"""
from __future__ import annotations

import math
from typing import List, Optional

from transiq.utils import validate_numeric


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------

def mean(data: List[float]) -> float:
    """Arithmetic mean: x̄ = Σxᵢ / n."""
    vals = validate_numeric(data, "data")
    return sum(vals) / len(vals)


def variance(data: List[float], ddof: int = 0) -> float:
    """
    Population variance (ddof=0) or sample variance (ddof=1).

    s² = Σ(xᵢ - x̄)² / (n - ddof)
    """
    vals = validate_numeric(data, "data", min_len=1 + ddof)
    mu = mean(vals)
    ss = sum((x - mu) ** 2 for x in vals)
    return ss / (len(vals) - ddof)


def std_dev(data: List[float], ddof: int = 0) -> float:
    """Standard deviation: σ = √variance."""
    return math.sqrt(variance(data, ddof))


def median(data: List[float]) -> float:
    """Median value."""
    vals = sorted(validate_numeric(data, "data"))
    n = len(vals)
    mid = n // 2
    if n % 2 == 0:
        return (vals[mid - 1] + vals[mid]) / 2.0
    return vals[mid]


def mode(data: List[float]) -> List[float]:
    """Mode(s) — values with highest frequency. Returns sorted list."""
    vals = validate_numeric(data, "data")
    freq: dict[float, int] = {}
    for v in vals:
        freq[v] = freq.get(v, 0) + 1
    max_count = max(freq.values())
    return sorted(v for v, c in freq.items() if c == max_count)


def percentile(data: List[float], p: float) -> float:
    """
    p-th percentile (0–100) using linear interpolation.
    """
    if not 0 <= p <= 100:
        raise ValueError(f"percentile must be 0–100 (got {p})")
    vals = sorted(validate_numeric(data, "data"))
    n = len(vals)
    k = (p / 100.0) * (n - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vals[int(k)]
    return vals[f] * (c - k) + vals[c] * (k - f)


def range_(data: List[float]) -> float:
    """Range = max - min."""
    vals = validate_numeric(data, "data")
    return max(vals) - min(vals)


def iqr(data: List[float]) -> float:
    """Interquartile range = Q3 - Q1."""
    return percentile(data, 75) - percentile(data, 25)


def skewness(data: List[float]) -> float:
    """Sample skewness (Fisher's definition)."""
    vals = validate_numeric(data, "data", min_len=3)
    n = len(vals)
    mu = mean(vals)
    s = std_dev(vals, ddof=1)
    m3 = sum((x - mu) ** 3 for x in vals) / n
    return (n * m3) / ((n - 1) * (n - 2) * s ** 3 / n) if s > 0 else 0.0


def kurtosis(data: List[float]) -> float:
    """Sample excess kurtosis."""
    vals = validate_numeric(data, "data", min_len=4)
    n = len(vals)
    mu = mean(vals)
    s = std_dev(vals, ddof=1)
    if s == 0:
        return 0.0
    m4 = sum((x - mu) ** 4 for x in vals) / n
    return (m4 / (s ** 4)) - 3.0


# ---------------------------------------------------------------------------
# Normal distribution (Gaussian)
# ---------------------------------------------------------------------------

def pdf_normal(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    """Normal probability density function."""
    coeff = 1.0 / (sigma * math.sqrt(2.0 * math.pi))
    exponent = -0.5 * ((x - mu) / sigma) ** 2
    return coeff * math.exp(exponent)


def cdf_normal(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    """Normal cumulative distribution function (uses math.erf)."""
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0))))


def z_score(x: float, mu: float, sigma: float) -> float:
    """Standard score: z = (x - μ) / σ."""
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    return (x - mu) / sigma


def inverse_normal(p: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    """
    Inverse normal CDF (quantile function) using rational approximation
    (Abramowitz & Stegun 26.2.23).
    """
    if p <= 0 or p >= 1:
        raise ValueError(f"p must be in (0, 1), got {p}")

    # Rational approximation for standard normal
    if p < 0.5:
        t = math.sqrt(-2.0 * math.log(p))
    else:
        t = math.sqrt(-2.0 * math.log(1.0 - p))

    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    z = t - (c0 + c1 * t + c2 * t ** 2) / (1.0 + d1 * t + d2 * t ** 2 + d3 * t ** 3)

    if p < 0.5:
        z = -z

    return mu + z * sigma


# ---------------------------------------------------------------------------
# Binomial distribution
# ---------------------------------------------------------------------------

def pmf_binomial(k: int, n: int, p: float) -> float:
    """P(X = k) for X ~ Binomial(n, p)."""
    if not 0 <= p <= 1:
        raise ValueError(f"p must be in [0,1], got {p}")
    return math.comb(n, k) * (p ** k) * ((1.0 - p) ** (n - k))


def cdf_binomial(k: int, n: int, p: float) -> float:
    """P(X ≤ k) for X ~ Binomial(n, p)."""
    return sum(pmf_binomial(i, n, p) for i in range(k + 1))


# ---------------------------------------------------------------------------
# Poisson distribution
# ---------------------------------------------------------------------------

def pmf_poisson(k: int, lam: float) -> float:
    """P(X = k) for X ~ Poisson(λ)."""
    if lam < 0:
        raise ValueError(f"lambda must be >= 0, got {lam}")
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def cdf_poisson(k: int, lam: float) -> float:
    """P(X ≤ k) for X ~ Poisson(λ)."""
    return sum(pmf_poisson(i, lam) for i in range(k + 1))


# ---------------------------------------------------------------------------
# Exponential distribution
# ---------------------------------------------------------------------------

def pdf_exponential(x: float, lam: float) -> float:
    """Exponential PDF: f(x) = λe^{-λx} for x >= 0."""
    if x < 0:
        return 0.0
    return lam * math.exp(-lam * x)


def cdf_exponential(x: float, lam: float) -> float:
    """Exponential CDF: F(x) = 1 - e^{-λx} for x >= 0."""
    if x < 0:
        return 0.0
    return 1.0 - math.exp(-lam * x)
