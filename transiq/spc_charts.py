"""
Statistical Process Control charts and run rules.

Covers ASQ Handbook Chapter 21: SPC and Control Charts.

Variable charts:
  X̄-R chart    — subgroup means and ranges
  X̄-S chart    — subgroup means and standard deviations
  I-MR chart   — individual measurements and moving ranges

Attribute charts:
  p chart      — proportion nonconforming
  np chart     — count of nonconforming
  c chart      — count of defects (constant area of opportunity)
  u chart      — defects per unit (varying area of opportunity)

Run rules:
  Western Electric rules (1–4)
  Nelson rules (1–8)
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from transiq.utils import (
    get_A2, get_A3, get_B3_B4, get_D3_D4, get_c4, get_d2,
    validate_numeric,
)
from transiq.statistics import mean as _mean, std_dev as _std


# ---------------------------------------------------------------------------
# Variable control charts
# ---------------------------------------------------------------------------

def xbar_r_limits(subgroups: List[List[float]]) -> Dict[str, float]:
    """
    Compute X̄ and R chart centre lines and control limits.

    Parameters
    ----------
    subgroups : list of lists
        Each inner list is a subgroup of measurements (constant size n).

    Returns
    -------
    dict with keys:
        Xbar_CL, Xbar_UCL, Xbar_LCL   (X-bar chart)
        R_CL, R_UCL, R_LCL             (R chart)
        n, k, sigma_hat
    """
    if not subgroups:
        raise ValueError("subgroups must not be empty")
    n = len(subgroups[0])
    if n < 2 or n > 25:
        raise ValueError(f"subgroup size must be 2–25 (got {n})")
    for i, sg in enumerate(subgroups):
        if len(sg) != n:
            raise ValueError(f"Subgroup {i} has {len(sg)} values, expected {n}")

    k = len(subgroups)
    means = [sum(sg) / n for sg in subgroups]
    ranges = [max(sg) - min(sg) for sg in subgroups]

    x_dbar = sum(means) / k
    r_bar = sum(ranges) / k

    A2 = get_A2(n)
    D3, D4 = get_D3_D4(n)
    d2 = get_d2(n)

    return {
        "Xbar_CL": round(x_dbar, 6),
        "Xbar_UCL": round(x_dbar + A2 * r_bar, 6),
        "Xbar_LCL": round(x_dbar - A2 * r_bar, 6),
        "R_CL": round(r_bar, 6),
        "R_UCL": round(D4 * r_bar, 6),
        "R_LCL": round(D3 * r_bar, 6),
        "n": n,
        "k": k,
        "sigma_hat": round(r_bar / d2, 6),
    }


def xbar_s_limits(subgroups: List[List[float]]) -> Dict[str, float]:
    """
    Compute X̄ and S chart centre lines and control limits.

    Preferred over X̄-R when subgroup size n > 10.
    Uses A3, B3, B4 factors.
    """
    if not subgroups:
        raise ValueError("subgroups must not be empty")
    n = len(subgroups[0])
    if n < 2 or n > 25:
        raise ValueError(f"subgroup size must be 2–25 (got {n})")

    k = len(subgroups)
    means = [sum(sg) / n for sg in subgroups]
    stds = [_std(sg, ddof=1) for sg in subgroups]

    x_dbar = sum(means) / k
    s_bar = sum(stds) / k

    A3 = get_A3(n)
    B3, B4 = get_B3_B4(n)
    c4 = get_c4(n)

    return {
        "Xbar_CL": round(x_dbar, 6),
        "Xbar_UCL": round(x_dbar + A3 * s_bar, 6),
        "Xbar_LCL": round(x_dbar - A3 * s_bar, 6),
        "S_CL": round(s_bar, 6),
        "S_UCL": round(B4 * s_bar, 6),
        "S_LCL": round(B3 * s_bar, 6),
        "n": n,
        "k": k,
        "sigma_hat": round(s_bar / c4, 6),
    }


def imr_limits(data: List[float]) -> Dict[str, float]:
    """
    Individual and Moving-Range (I-MR) chart limits.

    For individual observations (subgroup size = 1).
    MR = |xᵢ - xᵢ₋₁|, σ̂ = MR̄ / d2(2)
    """
    vals = validate_numeric(data, "data", min_len=2)
    n = len(vals)
    x_bar = sum(vals) / n

    # Moving ranges
    mrs = [abs(vals[i] - vals[i - 1]) for i in range(1, n)]
    mr_bar = sum(mrs) / len(mrs)

    d2 = get_d2(2)  # d2 for n=2 (moving range span)
    D3, D4 = get_D3_D4(2)
    sigma_hat = mr_bar / d2

    return {
        "I_CL": round(x_bar, 6),
        "I_UCL": round(x_bar + 3 * sigma_hat, 6),
        "I_LCL": round(x_bar - 3 * sigma_hat, 6),
        "MR_CL": round(mr_bar, 6),
        "MR_UCL": round(D4 * mr_bar, 6),
        "MR_LCL": round(max(0.0, D3 * mr_bar), 6),
        "n": n,
        "sigma_hat": round(sigma_hat, 6),
    }


# ---------------------------------------------------------------------------
# Attribute control charts
# ---------------------------------------------------------------------------

def p_chart_limits(
    defectives: List[int],
    sample_sizes: List[int],
) -> Dict[str, Any]:
    """
    p chart — proportion nonconforming.

    Parameters
    ----------
    defectives : list of int
        Count of nonconforming items per sample.
    sample_sizes : list of int
        Sample size for each period (may vary).

    Returns
    -------
    dict with p_bar (CL), UCL, LCL per sample, and overall values.
    """
    if len(defectives) != len(sample_sizes):
        raise ValueError("defectives and sample_sizes must have same length")
    k = len(defectives)

    total_def = sum(defectives)
    total_n = sum(sample_sizes)
    p_bar = total_def / total_n

    ucl_list = []
    lcl_list = []
    for ni in sample_sizes:
        sigma_p = math.sqrt(p_bar * (1 - p_bar) / ni)
        ucl_list.append(round(min(1.0, p_bar + 3 * sigma_p), 6))
        lcl_list.append(round(max(0.0, p_bar - 3 * sigma_p), 6))

    return {
        "p_bar": round(p_bar, 6),
        "UCL": ucl_list,
        "LCL": lcl_list,
        "k": k,
        "total_defectives": total_def,
        "total_inspected": total_n,
    }


def np_chart_limits(
    defectives: List[int],
    sample_size: int,
) -> Dict[str, float]:
    """
    np chart — number of nonconforming (constant sample size).

    CL = np̄,  UCL = np̄ + 3√(np̄(1-p̄)),  LCL = max(0, np̄ - 3√(np̄(1-p̄)))
    """
    k = len(defectives)
    total_def = sum(defectives)
    p_bar = total_def / (k * sample_size)
    np_bar = p_bar * sample_size
    sigma_np = math.sqrt(np_bar * (1 - p_bar))

    return {
        "np_bar": round(np_bar, 4),
        "UCL": round(np_bar + 3 * sigma_np, 4),
        "LCL": round(max(0.0, np_bar - 3 * sigma_np), 4),
        "p_bar": round(p_bar, 6),
        "k": k,
        "n": sample_size,
    }


def c_chart_limits(defects: List[int]) -> Dict[str, float]:
    """
    c chart — defect counts (constant area of opportunity).

    CL = c̄,  UCL = c̄ + 3√c̄,  LCL = max(0, c̄ - 3√c̄)
    """
    k = len(defects)
    c_bar = sum(defects) / k
    sigma_c = math.sqrt(c_bar)

    return {
        "c_bar": round(c_bar, 4),
        "UCL": round(c_bar + 3 * sigma_c, 4),
        "LCL": round(max(0.0, c_bar - 3 * sigma_c), 4),
        "k": k,
    }


def u_chart_limits(
    defects: List[int],
    sample_sizes: List[int],
) -> Dict[str, Any]:
    """
    u chart — defects per unit (varying area of opportunity).

    CL = ū,  UCL = ū + 3√(ū/nᵢ),  LCL = max(0, ū - 3√(ū/nᵢ))
    """
    if len(defects) != len(sample_sizes):
        raise ValueError("defects and sample_sizes must have same length")
    k = len(defects)
    total_defects = sum(defects)
    total_n = sum(sample_sizes)
    u_bar = total_defects / total_n

    ucl_list = []
    lcl_list = []
    for ni in sample_sizes:
        sigma_u = math.sqrt(u_bar / ni)
        ucl_list.append(round(u_bar + 3 * sigma_u, 6))
        lcl_list.append(round(max(0.0, u_bar - 3 * sigma_u), 6))

    return {
        "u_bar": round(u_bar, 6),
        "UCL": ucl_list,
        "LCL": lcl_list,
        "k": k,
    }


# ---------------------------------------------------------------------------
# Run rules / Western Electric rules
# ---------------------------------------------------------------------------

def western_electric_rules(
    data: List[float],
    cl: float,
    ucl: float,
    lcl: float,
) -> List[Dict[str, Any]]:
    """
    Apply Western Electric / AT&T run rules for out-of-control detection.

    Rule 1: Any single point beyond ±3σ (outside control limits)
    Rule 2: 2 of 3 consecutive points beyond ±2σ
    Rule 3: 4 of 5 consecutive points beyond ±1σ (same side)
    Rule 4: 8 consecutive points on one side of centre line

    Parameters
    ----------
    data : list of float
        Sequential data points (means, ranges, or individuals).
    cl : float
        Centre line.
    ucl, lcl : float
        Upper/lower control limits (3σ).

    Returns
    -------
    List of violation dicts: {rule, description, indices, severity}
    """
    vals = validate_numeric(data, "data")
    n = len(vals)
    sigma = (ucl - cl) / 3.0 if ucl != cl else 1.0

    violations: List[Dict[str, Any]] = []

    # Rule 1 — point outside control limits
    r1_idx = [i for i, v in enumerate(vals) if v > ucl or v < lcl]
    if r1_idx:
        violations.append({
            "rule": "Rule 1",
            "description": "Point(s) outside ±3σ control limits",
            "indices": r1_idx,
            "severity": "critical",
        })

    # Rule 2 — 2 of 3 beyond ±2σ
    upper2 = cl + 2 * sigma
    lower2 = cl - 2 * sigma
    r2_idx: List[int] = []
    for i in range(2, n):
        window = vals[i - 2: i + 1]
        above = sum(1 for v in window if v > upper2)
        below = sum(1 for v in window if v < lower2)
        if above >= 2 or below >= 2:
            r2_idx.append(i)
    if r2_idx:
        violations.append({
            "rule": "Rule 2",
            "description": "2 of 3 consecutive points beyond ±2σ",
            "indices": r2_idx,
            "severity": "warning",
        })

    # Rule 3 — 4 of 5 beyond ±1σ (same side)
    upper1 = cl + sigma
    lower1 = cl - sigma
    r3_idx: List[int] = []
    for i in range(4, n):
        window = vals[i - 4: i + 1]
        above = sum(1 for v in window if v > upper1)
        below = sum(1 for v in window if v < lower1)
        if above >= 4 or below >= 4:
            r3_idx.append(i)
    if r3_idx:
        violations.append({
            "rule": "Rule 3",
            "description": "4 of 5 consecutive points beyond ±1σ (same side)",
            "indices": r3_idx,
            "severity": "warning",
        })

    # Rule 4 — 8 consecutive points on same side of CL
    r4_idx: List[int] = []
    run_above = 0
    run_below = 0
    for i in range(n):
        if vals[i] > cl:
            run_above += 1
            run_below = 0
        elif vals[i] < cl:
            run_below += 1
            run_above = 0
        else:
            run_above = 0
            run_below = 0
        if run_above >= 8 or run_below >= 8:
            r4_idx.append(i)
    if r4_idx:
        violations.append({
            "rule": "Rule 4",
            "description": "8 consecutive points on one side of centre line",
            "indices": r4_idx,
            "severity": "warning",
        })

    return violations


def nelson_rules(
    data: List[float],
    cl: float,
    ucl: float,
    lcl: float,
) -> List[Dict[str, Any]]:
    """
    Full Nelson rules (8 rules) for out-of-control detection.

    Rules 1–4 are same as Western Electric.
    Rule 5: 6 consecutive points trending up or down
    Rule 6: 15 consecutive points within ±1σ (stratification)
    Rule 7: 14 consecutive points alternating up/down
    Rule 8: 8 consecutive points beyond ±1σ (both sides — mixture)
    """
    vals = validate_numeric(data, "data")
    n = len(vals)
    sigma = (ucl - cl) / 3.0 if ucl != cl else 1.0

    # Start with Western Electric rules (1–4)
    violations = western_electric_rules(data, cl, ucl, lcl)

    # Rule 5 — 6 points in a row, all increasing or all decreasing
    r5_idx: List[int] = []
    for i in range(5, n):
        window = vals[i - 5: i + 1]
        all_up = all(window[j + 1] > window[j] for j in range(5))
        all_down = all(window[j + 1] < window[j] for j in range(5))
        if all_up or all_down:
            r5_idx.append(i)
    if r5_idx:
        violations.append({
            "rule": "Rule 5 (Nelson)",
            "description": "6 consecutive points trending monotonically",
            "indices": r5_idx,
            "severity": "warning",
        })

    # Rule 6 — 15 consecutive points within ±1σ (stratification)
    upper1 = cl + sigma
    lower1 = cl - sigma
    r6_idx: List[int] = []
    count_in = 0
    for i in range(n):
        if lower1 <= vals[i] <= upper1:
            count_in += 1
        else:
            count_in = 0
        if count_in >= 15:
            r6_idx.append(i)
    if r6_idx:
        violations.append({
            "rule": "Rule 6 (Nelson)",
            "description": "15 consecutive points within ±1σ (stratification)",
            "indices": r6_idx,
            "severity": "info",
        })

    # Rule 7 — 14 points alternating up and down
    r7_idx: List[int] = []
    alt_count = 1
    for i in range(2, n):
        if (vals[i] - vals[i - 1]) * (vals[i - 1] - vals[i - 2]) < 0:
            alt_count += 1
        else:
            alt_count = 1
        if alt_count >= 14:
            r7_idx.append(i)
    if r7_idx:
        violations.append({
            "rule": "Rule 7 (Nelson)",
            "description": "14 consecutive points alternating up/down",
            "indices": r7_idx,
            "severity": "warning",
        })

    # Rule 8 — 8 consecutive points beyond ±1σ on both sides (mixture)
    r8_idx: List[int] = []
    count_beyond = 0
    for i in range(n):
        if vals[i] > upper1 or vals[i] < lower1:
            count_beyond += 1
        else:
            count_beyond = 0
        if count_beyond >= 8:
            r8_idx.append(i)
    if r8_idx:
        violations.append({
            "rule": "Rule 8 (Nelson)",
            "description": "8 consecutive points beyond ±1σ (mixture pattern)",
            "indices": r8_idx,
            "severity": "warning",
        })

    return violations
