"""
SPC Engine — Statistical Process Control for fleet-wide drilling analytics

Computes control limits (UCL/LCL), capability indices (Cp/Cpk/DPMO),
detects Western Electric rule violations, and generates control-chart datasets.
"""
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field

from core.logging.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class Violation(BaseModel):
    rule: str
    description: str
    indices: List[int] = Field(default_factory=list)
    severity: str = "warning"  # warning | critical


class ControlChartPoint(BaseModel):
    index: int
    value: float
    rig_id: str = ""
    timestamp: Optional[str] = None
    violation: Optional[str] = None


class SPCResult(BaseModel):
    metric_name: str = ""
    n: int = 0
    mean: float = 0.0
    std: float = 0.0
    ucl: float = 0.0
    lcl: float = 0.0
    moving_range_mean: float = 0.0
    cp: Optional[float] = None
    cpk: Optional[float] = None
    dpmo: Optional[float] = None
    violations: List[Violation] = Field(default_factory=list)
    control_chart: List[ControlChartPoint] = Field(default_factory=list)
    in_control: bool = True


# ---------------------------------------------------------------------------
# Core statistics
# ---------------------------------------------------------------------------

def _compute_stats(values: np.ndarray) -> Tuple[float, float]:
    """Mean and standard deviation (ignoring NaN)."""
    clean = values[np.isfinite(values)]
    if len(clean) < 2:
        return (float(clean[0]) if len(clean) == 1 else 0.0, 0.0)
    return float(np.mean(clean)), float(np.std(clean, ddof=1))


def _moving_ranges(values: np.ndarray) -> np.ndarray:
    """Absolute successive differences (MR)."""
    clean = values[np.isfinite(values)]
    if len(clean) < 2:
        return np.array([])
    return np.abs(np.diff(clean))


# ---------------------------------------------------------------------------
# Capability indices
# ---------------------------------------------------------------------------

def _capability(
    mean: float,
    std: float,
    usl: Optional[float],
    lsl: Optional[float],
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Compute Cp, Cpk, and DPMO.

    usl / lsl = Upper/Lower Specification Limits (user-provided).
    Returns (Cp, Cpk, DPMO) — any may be None if limits not given.
    """
    if std <= 0:
        return (None, None, None)

    cp = cpk = dpmo = None

    if usl is not None and lsl is not None:
        cp = (usl - lsl) / (6 * std)
        cpu = (usl - mean) / (3 * std)
        cpl = (mean - lsl) / (3 * std)
        cpk = min(cpu, cpl)
        # DPMO approximation from Cpk
        try:
            from scipy.stats import norm
            z = 3.0 * cpk if cpk else 0
            defect_rate = 2 * norm.sf(abs(z))  # two-tail
            dpmo = defect_rate * 1_000_000
        except ImportError:
            # Rough approximation without scipy
            if cpk is not None and cpk > 0:
                z = 3.0 * cpk
                dpmo = max(0, (1 - min(z / 6.0, 1.0)) * 1_000_000)

    elif usl is not None:
        cpk = (usl - mean) / (3 * std)
    elif lsl is not None:
        cpk = (mean - lsl) / (3 * std)

    return (
        round(cp, 4) if cp is not None else None,
        round(cpk, 4) if cpk is not None else None,
        round(dpmo, 1) if dpmo is not None else None,
    )


# ---------------------------------------------------------------------------
# Western Electric Rules
# ---------------------------------------------------------------------------

def _detect_violations(
    values: np.ndarray,
    mean: float,
    std: float,
    ucl: float,
    lcl: float,
) -> List[Violation]:
    """
    Apply Western Electric Rules for out-of-control detection.

    Rule 1: Any single point outside ±3σ (control limits)
    Rule 2: 2 of 3 consecutive points beyond ±2σ
    Rule 3: 4 of 5 consecutive points beyond ±1σ
    Rule 4: 8 consecutive points on one side of mean
    """
    violations: List[Violation] = []
    n = len(values)
    if n < 2 or std <= 0:
        return violations

    sigma1 = std
    sigma2 = 2 * std
    # Rule 1 — outside control limits
    r1_indices = [i for i in range(n) if np.isfinite(values[i]) and (values[i] > ucl or values[i] < lcl)]
    if r1_indices:
        violations.append(Violation(
            rule="Rule 1",
            description="Point(s) outside ±3σ control limits",
            indices=r1_indices,
            severity="critical",
        ))

    # Rule 2 — 2 of 3 beyond ±2σ
    r2_indices: List[int] = []
    upper2 = mean + sigma2
    lower2 = mean - sigma2
    for i in range(2, n):
        window = values[i - 2: i + 1]
        above = sum(1 for v in window if np.isfinite(v) and v > upper2)
        below = sum(1 for v in window if np.isfinite(v) and v < lower2)
        if above >= 2 or below >= 2:
            r2_indices.append(i)
    if r2_indices:
        violations.append(Violation(
            rule="Rule 2",
            description="2 of 3 consecutive points beyond ±2σ",
            indices=r2_indices,
            severity="warning",
        ))

    # Rule 3 — 4 of 5 beyond ±1σ
    r3_indices: List[int] = []
    upper1 = mean + sigma1
    lower1 = mean - sigma1
    for i in range(4, n):
        window = values[i - 4: i + 1]
        above = sum(1 for v in window if np.isfinite(v) and v > upper1)
        below = sum(1 for v in window if np.isfinite(v) and v < lower1)
        if above >= 4 or below >= 4:
            r3_indices.append(i)
    if r3_indices:
        violations.append(Violation(
            rule="Rule 3",
            description="4 of 5 consecutive points beyond ±1σ",
            indices=r3_indices,
            severity="warning",
        ))

    # Rule 4 — 8 consecutive on same side
    r4_indices: List[int] = []
    run_above = 0
    run_below = 0
    for i in range(n):
        if not np.isfinite(values[i]):
            run_above = 0
            run_below = 0
            continue
        if values[i] > mean:
            run_above += 1
            run_below = 0
        elif values[i] < mean:
            run_below += 1
            run_above = 0
        else:
            run_above = 0
            run_below = 0
        if run_above >= 8 or run_below >= 8:
            r4_indices.append(i)
    if r4_indices:
        violations.append(Violation(
            rule="Rule 4",
            description="8 consecutive points on one side of mean",
            indices=r4_indices,
            severity="warning",
        ))

    return violations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_spc(
    values: List[float],
    metric_name: str = "",
    rig_ids: Optional[List[str]] = None,
    timestamps: Optional[List[str]] = None,
    usl: Optional[float] = None,
    lsl: Optional[float] = None,
    sigma_multiplier: float = 3.0,
) -> SPCResult:
    """
    Compute SPC analysis for a list of metric values.

    Args:
        values: Numeric measurements (e.g., ROP per rig or per day).
        metric_name: Human-readable metric label.
        rig_ids: Optional parallel list of rig identifiers.
        timestamps: Optional parallel list of timestamps.
        usl: Upper specification limit (for Cp/Cpk).
        lsl: Lower specification limit (for Cp/Cpk).
        sigma_multiplier: Control limit sigma (default 3σ).

    Returns:
        SPCResult with all statistics, violations, control chart data.
    """
    arr = np.array(values, dtype=float)
    clean = arr[np.isfinite(arr)]

    if len(clean) < 2:
        return SPCResult(metric_name=metric_name, n=len(clean))

    mean, std = _compute_stats(arr)
    ucl = mean + sigma_multiplier * std
    lcl = mean - sigma_multiplier * std

    mr = _moving_ranges(arr)
    mr_mean = float(np.mean(mr)) if len(mr) > 0 else 0.0

    cp, cpk, dpmo = _capability(mean, std, usl, lsl)
    violations = _detect_violations(arr, mean, std, ucl, lcl)

    # Build control chart points
    chart: List[ControlChartPoint] = []
    for i, v in enumerate(values):
        viol_label = None
        for viol in violations:
            if i in viol.indices:
                viol_label = viol.rule
                break
        chart.append(ControlChartPoint(
            index=i,
            value=v if np.isfinite(v) else 0.0,
            rig_id=rig_ids[i] if rig_ids and i < len(rig_ids) else "",
            timestamp=timestamps[i] if timestamps and i < len(timestamps) else None,
            violation=viol_label,
        ))

    return SPCResult(
        metric_name=metric_name,
        n=int(len(clean)),
        mean=round(mean, 4),
        std=round(std, 4),
        ucl=round(ucl, 4),
        lcl=round(lcl, 4),
        moving_range_mean=round(mr_mean, 4),
        cp=cp,
        cpk=cpk,
        dpmo=dpmo,
        violations=violations,
        control_chart=chart,
        in_control=len(violations) == 0,
    )


def compute_fleet_spc(
    fleet_data: Dict[str, List[float]],
    metric_name: str = "",
    usl: Optional[float] = None,
    lsl: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compute SPC across an entire fleet (multiple rigs).

    Args:
        fleet_data: {rig_id: [values...]}
        metric_name: Metric label.
        usl / lsl: Specification limits.

    Returns:
        Combined fleet SPC result with per-rig breakdowns.
    """
    all_values: List[float] = []
    all_rig_ids: List[str] = []

    for rig_id, vals in fleet_data.items():
        all_values.extend(vals)
        all_rig_ids.extend([rig_id] * len(vals))

    fleet_result = compute_spc(
        all_values,
        metric_name=metric_name,
        rig_ids=all_rig_ids,
        usl=usl,
        lsl=lsl,
    )

    per_rig: Dict[str, Dict] = {}
    for rig_id, vals in fleet_data.items():
        rig_result = compute_spc(vals, metric_name=f"{metric_name} ({rig_id})", usl=usl, lsl=lsl)
        per_rig[rig_id] = rig_result.model_dump()

    return {
        "fleet": fleet_result.model_dump(),
        "per_rig": per_rig,
        "total_rigs": len(fleet_data),
        "total_observations": len(all_values),
    }
