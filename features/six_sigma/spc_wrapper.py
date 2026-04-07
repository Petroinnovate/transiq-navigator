"""
SPC Wrapper — Thin adapter around app.ddr.spc_engine.

Provides convenience helpers:
  - compute_capability()  → single-metric Cp/Cpk/sigma
  - compute_fleet()       → fleet-wide SPC using existing compute_fleet_spc()
  - spec_limits_for()     → default USL/LSL lookup for Oil & Gas metrics
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from pipelines.inference.ddr.spc_engine import SPCResult, compute_spc, compute_fleet_spc

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default specification limits (USL/LSL) for common O&G metrics
# ---------------------------------------------------------------------------
_DEFAULT_SPEC_LIMITS: Dict[str, Dict[str, Optional[float]]] = {
    # Drilling
    "rop":               {"usl": None,  "lsl": 20.0},   # ft/hr minimum
    "npt":               {"usl": 5.0,   "lsl": None},   # % maximum
    "npt_hours":         {"usl": 8.0,   "lsl": None},   # hours/day
    "mud_weight":        {"usl": 16.0,  "lsl": 9.0},    # ppg
    "wob":               {"usl": 60.0,  "lsl": 5.0},    # klbs
    "torque":            {"usl": 35.0,  "lsl": None},   # kft-lbs
    "cost_per_foot":     {"usl": 500.0, "lsl": None},   # $/ft target
    "hole_depth":        {"usl": None,  "lsl": None},
    # Production
    "production_rate":   {"usl": None,  "lsl": 500.0},  # bbl/d minimum
    "uptime":            {"usl": None,  "lsl": 95.0},   # % minimum
    "availability":      {"usl": None,  "lsl": 90.0},   # %
    # Safety
    "trir":              {"usl": 1.0,   "lsl": None},
    "ltir":              {"usl": 0.5,   "lsl": None},
    "near_miss":         {"usl": 10.0,  "lsl": None},
    # Quality
    "defect_rate":       {"usl": 3.5,   "lsl": None},   # %
    "yield":             {"usl": None,  "lsl": 96.5},   # %
    "oee":               {"usl": None,  "lsl": 85.0},   # %
}


def spec_limits_for(
    metric_name: str,
    usl_override: Optional[float] = None,
    lsl_override: Optional[float] = None,
) -> Tuple[Optional[float], Optional[float]]:
    """Return (USL, LSL) for a metric, with optional overrides."""
    key = metric_name.lower().replace(" ", "_").replace("-", "_")
    defaults = _DEFAULT_SPEC_LIMITS.get(key, {})
    usl = usl_override if usl_override is not None else defaults.get("usl")
    lsl = lsl_override if lsl_override is not None else defaults.get("lsl")
    return usl, lsl


def compute_capability(
    values: List[float],
    metric_name: str = "",
    *,
    usl: Optional[float] = None,
    lsl: Optional[float] = None,
    rig_ids: Optional[List[str]] = None,
    timestamps: Optional[List[str]] = None,
) -> SPCResult:
    """
    Compute SPC + capability for a single metric series.

    Auto-applies default spec limits if not provided.
    """
    auto_usl, auto_lsl = spec_limits_for(metric_name, usl, lsl)

    return compute_spc(
        values=values,
        metric_name=metric_name,
        rig_ids=rig_ids,
        timestamps=timestamps,
        usl=auto_usl,
        lsl=auto_lsl,
    )


def compute_fleet(
    fleet_data: Dict[str, List[float]],
    metric_name: str = "",
    *,
    usl: Optional[float] = None,
    lsl: Optional[float] = None,
) -> Dict[str, Any]:
    """Fleet-wide SPC using existing compute_fleet_spc."""
    auto_usl, auto_lsl = spec_limits_for(metric_name, usl, lsl)

    return compute_fleet_spc(
        fleet_data=fleet_data,
        metric_name=metric_name,
        usl=auto_usl,
        lsl=auto_lsl,
    )
