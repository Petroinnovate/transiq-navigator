"""
Design of Experiments (DOE).

Covers ASQ Handbook Chapter 18: Design of Experiments.

Functions
---------
full_factorial_design    Generate a 2^k or general full factorial design
fractional_factorial     Generate a 2^(k-p) fractional factorial design
anova_factorial          Two-way ANOVA for factorial experiments
main_effects             Compute main effects from factorial results
interaction_effects      Compute two-factor interaction effects
"""
from __future__ import annotations

import itertools
import math
from typing import Any, Dict, List, Optional, Tuple

from transiq.statistics import mean as _mean
from transiq.utils import validate_numeric


def full_factorial_design(
    factors: Dict[str, List[Any]],
) -> List[Dict[str, Any]]:
    """
    Generate a full factorial design matrix.

    Parameters
    ----------
    factors : dict mapping factor names to lists of levels
        e.g. {"Temp": [100, 200], "Pressure": [1, 2, 3]}

    Returns
    -------
    List of dicts, one per experimental run, with all factor combinations.
    """
    if not factors:
        raise ValueError("factors must not be empty")

    names = list(factors.keys())
    levels = [factors[n] for n in names]
    runs: List[Dict[str, Any]] = []

    for combo in itertools.product(*levels):
        run = {"run": len(runs) + 1}
        for name, val in zip(names, combo):
            run[name] = val
        runs.append(run)

    return runs


def coded_factorial_design(
    k: int,
    levels: Tuple[float, float] = (-1.0, 1.0),
) -> List[List[float]]:
    """
    Generate a coded 2^k factorial design.

    Parameters
    ----------
    k : number of factors
    levels : tuple of (low, high) coded levels (default -1, +1)

    Returns
    -------
    List of lists, each inner list is a run with k factor values.
    """
    return [list(combo) for combo in itertools.product(levels, repeat=k)]


def fractional_factorial(
    k: int,
    p: int = 1,
    generators: Optional[List[str]] = None,
) -> List[List[int]]:
    """
    Generate a 2^(k-p) fractional factorial design.

    Parameters
    ----------
    k : total number of factors
    p : number of generators (design is 2^(k-p) runs)
    generators : optional list of generator strings (e.g. ["ABC"] for D=ABC)
                 If not provided, a default Resolution III design is used.

    Returns
    -------
    List of lists — coded design matrix with -1/+1 levels.
    """
    base_k = k - p
    base_design = coded_factorial_design(base_k)

    if generators:
        # Each generator maps a new factor as product of base factors
        for gen_str in generators:
            col_indices = [ord(c.upper()) - ord('A') for c in gen_str if c.upper() in 'ABCDEFGHIJ']
            for run in base_design:
                product = 1
                for idx in col_indices:
                    if idx < len(run):
                        product *= int(run[idx])
                run.append(product)
    else:
        # Default: last p factors are products of first base_k factors
        for run in base_design:
            for _ in range(p):
                product = 1
                for val in run[:base_k]:
                    product *= int(val)
                run.append(product)

    return [[int(v) for v in run] for run in base_design]


def main_effects(
    design: List[Dict[str, Any]],
    response_key: str,
    factor_keys: List[str],
) -> Dict[str, float]:
    """
    Compute main effects for each factor.

    Main effect = mean(response at high level) - mean(response at low level)

    For coded designs (-1/+1), this equals the regression coefficient × 2.
    For general designs, computes difference of level means.
    """
    effects: Dict[str, float] = {}

    for factor in factor_keys:
        levels = sorted(set(run[factor] for run in design))
        if len(levels) == 2:
            low_vals = [run[response_key] for run in design if run[factor] == levels[0]]
            high_vals = [run[response_key] for run in design if run[factor] == levels[1]]
            effects[factor] = _mean(high_vals) - _mean(low_vals)
        else:
            # For multi-level: compute level means
            level_means = {}
            for lvl in levels:
                vals = [run[response_key] for run in design if run[factor] == lvl]
                level_means[lvl] = _mean(vals)
            effects[factor] = max(level_means.values()) - min(level_means.values())

    return {k: round(v, 6) for k, v in effects.items()}


def interaction_effects(
    design: List[Dict[str, Any]],
    response_key: str,
    factor_keys: List[str],
) -> Dict[str, float]:
    """
    Compute two-factor interaction effects for coded 2-level designs.

    Interaction AB = mean(A·B = +1 responses) - mean(A·B = -1 responses)
    """
    interactions: Dict[str, float] = {}

    for i, f1 in enumerate(factor_keys):
        for f2 in factor_keys[i + 1:]:
            plus_vals = [
                run[response_key] for run in design
                if run[f1] * run[f2] > 0
            ]
            minus_vals = [
                run[response_key] for run in design
                if run[f1] * run[f2] < 0
            ]
            if plus_vals and minus_vals:
                interactions[f"{f1}×{f2}"] = round(
                    _mean(plus_vals) - _mean(minus_vals), 6
                )

    return interactions


def anova_factorial(
    design: List[Dict[str, Any]],
    response_key: str,
    factor_keys: List[str],
) -> Dict[str, Any]:
    """
    Two-way (or multi-factor) ANOVA for factorial experiment.

    Computes SS, df, MS, F for each main effect.
    """
    all_responses = [run[response_key] for run in design]
    grand_mean = _mean(all_responses)
    n = len(all_responses)

    ss_total = sum((y - grand_mean) ** 2 for y in all_responses)

    factor_results: List[Dict[str, Any]] = []
    ss_model = 0.0

    for factor in factor_keys:
        levels = sorted(set(run[factor] for run in design))
        level_means = {}
        level_counts = {}
        for lvl in levels:
            vals = [run[response_key] for run in design if run[factor] == lvl]
            level_means[lvl] = _mean(vals)
            level_counts[lvl] = len(vals)

        ss = sum(ct * (m - grand_mean) ** 2 for lvl, (m, ct) in
                 zip(levels, zip(
                     [level_means[l] for l in levels],
                     [level_counts[l] for l in levels]
                 )))
        df = len(levels) - 1
        ms = ss / df if df > 0 else 0.0
        ss_model += ss

        factor_results.append({
            "factor": factor,
            "SS": round(ss, 6),
            "df": df,
            "MS": round(ms, 6),
            "levels": len(levels),
        })

    ss_error = ss_total - ss_model
    df_error = n - sum(fr["df"] for fr in factor_results) - 1
    ms_error = ss_error / df_error if df_error > 0 else 0.0

    for fr in factor_results:
        fr["F"] = round(fr["MS"] / ms_error, 6) if ms_error > 0 else float("inf")

    return {
        "SS_total": round(ss_total, 6),
        "SS_model": round(ss_model, 6),
        "SS_error": round(ss_error, 6),
        "df_error": df_error,
        "MS_error": round(ms_error, 6),
        "factors": factor_results,
        "n": n,
        "grand_mean": round(grand_mean, 6),
    }
