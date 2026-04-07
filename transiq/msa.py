"""
Measurement System Analysis (MSA) — Gauge R&R.

Covers ASQ Handbook Chapter 14: Measurement System Analysis.

Implements the ANOVA method for Gauge R&R studies:
  - Repeatability (equipment variation)
  - Reproducibility (appraiser variation)
  - Part-to-part variation
  - %GRR, %Contribution, number of distinct categories (ndc)
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

from transiq.statistics import mean as _mean, variance as _var
from transiq.utils import validate_numeric


def gage_rr_anova(
    measurements: List[List[List[float]]],
    tolerance: float = 0.0,
) -> Dict[str, Any]:
    """
    Gauge R&R study using ANOVA method (crossed design).

    Parameters
    ----------
    measurements : 3D list [part][operator][replicate]
        measurements[i][j][k] = k-th measurement of part i by operator j.
        All parts must have the same number of operators and replicates.
    tolerance : float, optional
        Specification tolerance (USL - LSL). If > 0, %Tolerance is computed.

    Returns
    -------
    dict with ANOVA table, variance components, %Contribution, %Study Variation,
    ndc (number of distinct categories).
    """
    n_parts = len(measurements)
    n_operators = len(measurements[0])
    n_replicates = len(measurements[0][0])
    N = n_parts * n_operators * n_replicates

    # Flatten all values
    all_vals: List[float] = []
    for part in measurements:
        for op in part:
            for rep in op:
                all_vals.append(float(rep))

    grand_mean = _mean(all_vals)

    # Part means
    part_means = []
    for i in range(n_parts):
        vals = [measurements[i][j][k]
                for j in range(n_operators) for k in range(n_replicates)]
        part_means.append(_mean(vals))

    # Operator means
    op_means = []
    for j in range(n_operators):
        vals = [measurements[i][j][k]
                for i in range(n_parts) for k in range(n_replicates)]
        op_means.append(_mean(vals))

    # Cell means (part × operator)
    cell_means = [[0.0] * n_operators for _ in range(n_parts)]
    for i in range(n_parts):
        for j in range(n_operators):
            cell_means[i][j] = _mean(measurements[i][j])

    # --- ANOVA Sums of Squares ---
    # SS_Part
    ss_part = n_operators * n_replicates * sum(
        (pm - grand_mean) ** 2 for pm in part_means
    )
    # SS_Operator
    ss_operator = n_parts * n_replicates * sum(
        (om - grand_mean) ** 2 for om in op_means
    )
    # SS_Interaction (Part × Operator)
    ss_interaction = n_replicates * sum(
        (cell_means[i][j] - part_means[i] - op_means[j] + grand_mean) ** 2
        for i in range(n_parts) for j in range(n_operators)
    )
    # SS_Repeatability (within cells)
    ss_repeat = sum(
        (measurements[i][j][k] - cell_means[i][j]) ** 2
        for i in range(n_parts) for j in range(n_operators) for k in range(n_replicates)
    )
    ss_total = sum((v - grand_mean) ** 2 for v in all_vals)

    # Degrees of freedom
    df_part = n_parts - 1
    df_operator = n_operators - 1
    df_interaction = df_part * df_operator
    df_repeat = n_parts * n_operators * (n_replicates - 1)
    df_total = N - 1

    # Mean squares
    ms_part = ss_part / df_part if df_part > 0 else 0.0
    ms_operator = ss_operator / df_operator if df_operator > 0 else 0.0
    ms_interaction = ss_interaction / df_interaction if df_interaction > 0 else 0.0
    ms_repeat = ss_repeat / df_repeat if df_repeat > 0 else 0.0

    # F-statistics
    f_part = ms_part / ms_interaction if ms_interaction > 0 else float("inf")
    f_operator = ms_operator / ms_interaction if ms_interaction > 0 else float("inf")
    f_interaction = ms_interaction / ms_repeat if ms_repeat > 0 else float("inf")

    # --- Variance Components ---
    var_repeat = ms_repeat
    var_interaction = max(0.0, (ms_interaction - ms_repeat) / n_replicates)
    var_operator = max(0.0, (ms_operator - ms_interaction) / (n_parts * n_replicates))
    var_part = max(0.0, (ms_part - ms_interaction) / (n_operators * n_replicates))

    var_reproducibility = var_operator + var_interaction
    var_grr = var_repeat + var_reproducibility
    var_total = var_grr + var_part

    # --- %Contribution (of total variance) ---
    pct_repeat = (var_repeat / var_total * 100) if var_total > 0 else 0.0
    pct_reprod = (var_reproducibility / var_total * 100) if var_total > 0 else 0.0
    pct_grr = (var_grr / var_total * 100) if var_total > 0 else 0.0
    pct_part = (var_part / var_total * 100) if var_total > 0 else 0.0

    # --- %Study Variation (6σ basis) ---
    sd_repeat = math.sqrt(var_repeat)
    sd_reprod = math.sqrt(var_reproducibility)
    sd_grr = math.sqrt(var_grr)
    sd_part = math.sqrt(var_part)
    sd_total = math.sqrt(var_total)

    sv_repeat = (6 * sd_repeat / (6 * sd_total) * 100) if sd_total > 0 else 0.0
    sv_reprod = (6 * sd_reprod / (6 * sd_total) * 100) if sd_total > 0 else 0.0
    sv_grr = (6 * sd_grr / (6 * sd_total) * 100) if sd_total > 0 else 0.0
    sv_part = (6 * sd_part / (6 * sd_total) * 100) if sd_total > 0 else 0.0

    # --- %Tolerance ---
    pt_grr = (6 * sd_grr / tolerance * 100) if tolerance > 0 else None

    # --- Number of Distinct Categories (ndc) ---
    ndc = int(math.floor(1.41 * sd_part / sd_grr)) if sd_grr > 0 else 0

    # Rating
    if pct_grr < 10:
        rating = "Acceptable"
    elif pct_grr < 30:
        rating = "Marginal"
    else:
        rating = "Unacceptable"

    return {
        "anova": {
            "Part": {"SS": round(ss_part, 6), "df": df_part, "MS": round(ms_part, 6), "F": round(f_part, 4)},
            "Operator": {"SS": round(ss_operator, 6), "df": df_operator, "MS": round(ms_operator, 6), "F": round(f_operator, 4)},
            "Part×Operator": {"SS": round(ss_interaction, 6), "df": df_interaction, "MS": round(ms_interaction, 6), "F": round(f_interaction, 4)},
            "Repeatability": {"SS": round(ss_repeat, 6), "df": df_repeat, "MS": round(ms_repeat, 6)},
            "Total": {"SS": round(ss_total, 6), "df": df_total},
        },
        "variance_components": {
            "Repeatability": round(var_repeat, 8),
            "Reproducibility": round(var_reproducibility, 8),
            "Operator": round(var_operator, 8),
            "Part×Operator": round(var_interaction, 8),
            "GRR": round(var_grr, 8),
            "Part-to-Part": round(var_part, 8),
            "Total": round(var_total, 8),
        },
        "pct_contribution": {
            "Repeatability": round(pct_repeat, 2),
            "Reproducibility": round(pct_reprod, 2),
            "GRR": round(pct_grr, 2),
            "Part-to-Part": round(pct_part, 2),
        },
        "pct_study_variation": {
            "Repeatability": round(sv_repeat, 2),
            "Reproducibility": round(sv_reprod, 2),
            "GRR": round(sv_grr, 2),
            "Part-to-Part": round(sv_part, 2),
        },
        "pct_tolerance_grr": round(pt_grr, 2) if pt_grr is not None else None,
        "ndc": ndc,
        "rating": rating,
        "design": {
            "parts": n_parts,
            "operators": n_operators,
            "replicates": n_replicates,
            "total_measurements": N,
        },
    }


def precision_to_tolerance(grr_sd: float, tolerance: float) -> float:
    """
    %P/T ratio = (6 × σ_GRR) / tolerance × 100.
    """
    if tolerance <= 0:
        raise ValueError("tolerance must be positive")
    return (6.0 * grr_sd) / tolerance * 100.0
