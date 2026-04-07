"""
Utility functions, constants, and SPC factor tables.

Provides:
- SPC constants (A2, A3, D3, D4, B3, B4, c4, d2) for subgroup sizes 2–25
- Combinatorial helpers (nCr, nPr)
- Data validation helpers
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# SPC Constants — from standard tables (ASTM E2587, ASQ Handbook Ch 21)
# Keys are subgroup size n
# ---------------------------------------------------------------------------

# A2 factor for X̄-R chart: UCL = X̿ + A2·R̄
A2_TABLE: Dict[int, float] = {
    2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577,
    6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308,
    11: 0.285, 12: 0.266, 13: 0.249, 14: 0.235, 15: 0.223,
    16: 0.212, 17: 0.203, 18: 0.194, 19: 0.187, 20: 0.180,
    21: 0.173, 22: 0.167, 23: 0.162, 24: 0.157, 25: 0.153,
}

# D3 and D4 factors for R chart: UCL = D4·R̄, LCL = D3·R̄
D3_TABLE: Dict[int, float] = {
    2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.076,
    8: 0.136, 9: 0.184, 10: 0.223,
    11: 0.256, 12: 0.283, 13: 0.307, 14: 0.328, 15: 0.347,
    16: 0.363, 17: 0.378, 18: 0.391, 19: 0.403, 20: 0.415,
    21: 0.425, 22: 0.434, 23: 0.443, 24: 0.451, 25: 0.459,
}

D4_TABLE: Dict[int, float] = {
    2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114,
    6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777,
    11: 1.744, 12: 1.717, 13: 1.693, 14: 1.672, 15: 1.653,
    16: 1.637, 17: 1.622, 18: 1.608, 19: 1.597, 20: 1.585,
    21: 1.575, 22: 1.566, 23: 1.557, 24: 1.549, 25: 1.541,
}

# A3 factor for X̄-S chart: UCL = X̿ + A3·S̄
A3_TABLE: Dict[int, float] = {
    2: 2.659, 3: 1.954, 4: 1.628, 5: 1.427,
    6: 1.287, 7: 1.182, 8: 1.099, 9: 1.032, 10: 0.975,
    11: 0.927, 12: 0.886, 13: 0.850, 14: 0.817, 15: 0.789,
    16: 0.763, 17: 0.739, 18: 0.718, 19: 0.698, 20: 0.680,
    21: 0.663, 22: 0.647, 23: 0.633, 24: 0.619, 25: 0.606,
}

# B3 and B4 factors for S chart: UCL = B4·S̄, LCL = B3·S̄
B3_TABLE: Dict[int, float] = {
    2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.030,
    7: 0.118, 8: 0.185, 9: 0.239, 10: 0.284,
    11: 0.321, 12: 0.354, 13: 0.382, 14: 0.406, 15: 0.428,
    16: 0.448, 17: 0.466, 18: 0.482, 19: 0.497, 20: 0.510,
    21: 0.523, 22: 0.534, 23: 0.545, 24: 0.555, 25: 0.565,
}

B4_TABLE: Dict[int, float] = {
    2: 3.267, 3: 2.568, 4: 2.266, 5: 2.089,
    6: 1.970, 7: 1.882, 8: 1.815, 9: 1.761, 10: 1.716,
    11: 1.679, 12: 1.646, 13: 1.618, 14: 1.594, 15: 1.572,
    16: 1.552, 17: 1.534, 18: 1.518, 19: 1.503, 20: 1.490,
    21: 1.477, 22: 1.466, 23: 1.455, 24: 1.445, 25: 1.435,
}

# c4 bias correction factor for S chart
C4_TABLE: Dict[int, float] = {
    2: 0.7979, 3: 0.8862, 4: 0.9213, 5: 0.9400,
    6: 0.9515, 7: 0.9594, 8: 0.9650, 9: 0.9693, 10: 0.9727,
    11: 0.9754, 12: 0.9776, 13: 0.9794, 14: 0.9810, 15: 0.9823,
    16: 0.9835, 17: 0.9845, 18: 0.9854, 19: 0.9862, 20: 0.9869,
    21: 0.9876, 22: 0.9882, 23: 0.9887, 24: 0.9892, 25: 0.9896,
}

# d2 factor (mean of relative range) — used to estimate σ from R̄: σ̂ = R̄/d2
D2_TABLE: Dict[int, float] = {
    2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326,
    6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078,
    11: 3.173, 12: 3.258, 13: 3.336, 14: 3.407, 15: 3.472,
    16: 3.532, 17: 3.588, 18: 3.640, 19: 3.689, 20: 3.735,
    21: 3.778, 22: 3.819, 23: 3.858, 24: 3.895, 25: 3.931,
}


# ---------------------------------------------------------------------------
# Factor look-ups
# ---------------------------------------------------------------------------

def get_A2(n: int) -> float:
    """Return A2 factor for subgroup size n."""
    if n not in A2_TABLE:
        raise ValueError(f"A2 not tabulated for n={n} (must be 2–25)")
    return A2_TABLE[n]


def get_D3_D4(n: int) -> Tuple[float, float]:
    """Return (D3, D4) factors for subgroup size n."""
    if n not in D3_TABLE:
        raise ValueError(f"D3/D4 not tabulated for n={n} (must be 2–25)")
    return D3_TABLE[n], D4_TABLE[n]


def get_A3(n: int) -> float:
    """Return A3 factor for subgroup size n."""
    if n not in A3_TABLE:
        raise ValueError(f"A3 not tabulated for n={n} (must be 2–25)")
    return A3_TABLE[n]


def get_B3_B4(n: int) -> Tuple[float, float]:
    """Return (B3, B4) factors for subgroup size n."""
    if n not in B3_TABLE:
        raise ValueError(f"B3/B4 not tabulated for n={n} (must be 2–25)")
    return B3_TABLE[n], B4_TABLE[n]


def get_c4(n: int) -> float:
    """Return c4 bias correction factor for subgroup size n."""
    if n not in C4_TABLE:
        raise ValueError(f"c4 not tabulated for n={n} (must be 2–25)")
    return C4_TABLE[n]


def get_d2(n: int) -> float:
    """Return d2 factor for subgroup size n."""
    if n not in D2_TABLE:
        raise ValueError(f"d2 not tabulated for n={n} (must be 2–25)")
    return D2_TABLE[n]


# ---------------------------------------------------------------------------
# Combinatorics
# ---------------------------------------------------------------------------

def n_choose_r(n: int, r: int) -> int:
    """Binomial coefficient C(n, r) = n! / (r! * (n-r)!)."""
    if r < 0 or r > n:
        return 0
    return math.comb(n, r)


def n_perm_r(n: int, r: int) -> int:
    """Permutation P(n, r) = n! / (n-r)!."""
    if r < 0 or r > n:
        return 0
    return math.perm(n, r)


# ---------------------------------------------------------------------------
# Data validation
# ---------------------------------------------------------------------------

def validate_numeric(data: Sequence[float], name: str = "data", min_len: int = 1) -> List[float]:
    """Validate that data is a non-empty sequence of finite numbers."""
    if not data:
        raise ValueError(f"{name} must not be empty")
    values = []
    for i, v in enumerate(data):
        if not isinstance(v, (int, float)):
            raise TypeError(f"{name}[{i}] = {v!r} is not numeric")
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"{name}[{i}] = {v} is not finite")
        values.append(float(v))
    if len(values) < min_len:
        raise ValueError(f"{name} must have at least {min_len} values (got {len(values)})")
    return values


def validate_positive(value: float, name: str = "value") -> float:
    """Validate that a value is positive."""
    if value <= 0:
        raise ValueError(f"{name} must be positive (got {value})")
    return float(value)
