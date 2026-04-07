"""
Capability — Process capability analysis driven by SPC wrapper.

Computes per-CTQ and aggregate capability, sigma levels, and DPMO.
Uses transiq library for core statistical calculations.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from features.six_sigma.spc_wrapper import compute_capability as _spc_compute

# Use transiq for deterministic statistical computations
from domain.transiq.process_capability import (
    cp as transiq_cp,
    cpk as transiq_cpk,
    sigma_level as transiq_sigma_level,
    dpmo as transiq_dpmo,
    dpmo_from_sigma as transiq_dpmo_from_sigma,
)
from domain.transiq.statistics import mean as transiq_mean, std_dev as transiq_std_dev

logger = logging.getLogger(__name__)


def sigma_from_cpk(cpk: Optional[float]) -> Optional[float]:
    """Convert Cpk to approximate sigma level: σ ≈ 3 × Cpk (short-term shift of 1.5σ)."""
    if cpk is None:
        return None
    return round(3.0 * cpk, 2)


def sigma_status(sigma: Optional[float]) -> str:
    """Human-readable capability status from sigma level."""
    if sigma is None:
        return "Insufficient Data"
    if sigma >= 6.0:
        return "World Class"
    if sigma >= 5.0:
        return "Excellent"
    if sigma >= 4.0:
        return "Good — Capable"
    if sigma >= 3.0:
        return "Marginal — Needs Improvement"
    if sigma >= 2.0:
        return "Poor — Not Capable"
    return "Critical — Process Failure"


def assess_capability(
    values: List[float],
    metric_name: str = "",
    *,
    usl: Optional[float] = None,
    lsl: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Run full capability assessment for a single metric.

    Returns:
        {
          "metric_name": str,
          "n": int,
          "mean": float,
          "std": float,
          "ucl": float,
          "lcl": float,
          "cp": float | None,
          "cpk": float | None,
          "dpmo": float | None,
          "sigmaLevel": float | None,
          "status": str,
          "inControl": bool,
          "violations": [...],
        }
    """
    spc_result = _spc_compute(values, metric_name, usl=usl, lsl=lsl)

    # Use transiq for deterministic Cp/Cpk when spec limits are available
    t_cp = spc_result.cp
    t_cpk = spc_result.cpk
    t_dpmo = spc_result.dpmo
    if len(values) >= 2:
        s = transiq_std_dev(values, ddof=1)
        m = transiq_mean(values)
        if s > 0 and usl is not None and lsl is not None:
            t_cp = round(transiq_cp(usl, lsl, s), 4)
            t_cpk = round(transiq_cpk(usl, lsl, m, s), 4)
        elif s > 0 and usl is not None:
            t_cpk = round((usl - m) / (3 * s), 4)
        elif s > 0 and lsl is not None:
            t_cpk = round((m - lsl) / (3 * s), 4)

    sigma = sigma_from_cpk(t_cpk)
    if t_cpk is not None and t_cpk > 0:
        t_dpmo = round(transiq_dpmo_from_sigma(3.0 * t_cpk), 2)

    return {
        "metric_name": spc_result.metric_name,
        "n": spc_result.n,
        "mean": spc_result.mean,
        "std": spc_result.std,
        "ucl": spc_result.ucl,
        "lcl": spc_result.lcl,
        "cp": t_cp,
        "cpk": t_cpk,
        "dpmo": t_dpmo,
        "sigmaLevel": sigma,
        "status": sigma_status(sigma),
        "inControl": spc_result.in_control,
        "violations": [v.model_dump() for v in spc_result.violations],
    }


def aggregate_capability(
    capability_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Aggregate individual capability assessments into overall process sigma.

    Uses weighted average of Cpk values (weighted by sample count n).
    """
    if not capability_results:
        return {
            "overallCpk": None,
            "overallSigma": None,
            "overallStatus": "No Data",
            "metricCount": 0,
            "inControlPct": 0.0,
        }

    total_n = 0
    weighted_cpk_sum = 0.0
    valid_count = 0
    in_control_count = 0

    for cap in capability_results:
        n = cap.get("n", 0)
        cpk = cap.get("cpk")
        if cpk is not None and n > 0:
            # Cap Cpk at 3.0 to prevent outliers from inflating aggregate
            capped = max(-3.0, min(3.0, cpk))
            weighted_cpk_sum += capped * n
            total_n += n
            valid_count += 1
        if cap.get("inControl"):
            in_control_count += 1

    overall_cpk = round(weighted_cpk_sum / total_n, 4) if total_n > 0 else None
    overall_sigma = sigma_from_cpk(overall_cpk)

    return {
        "overallCpk": overall_cpk,
        "overallSigma": overall_sigma,
        "overallStatus": sigma_status(overall_sigma),
        "metricCount": len(capability_results),
        "validMetrics": valid_count,
        "inControlCount": in_control_count,
        "inControlPct": round(in_control_count / len(capability_results) * 100, 1) if capability_results else 0.0,
    }
