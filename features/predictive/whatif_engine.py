"""
What-If Scenario Simulation Engine
====================================

Given a set of current KPI values and a set of levers (input adjustments),
computes:
  - Simulated KPI values after the adjustments
  - Delta vs baseline
  - Estimated financial impact
  - AI-friendly narrative

Entry points:
  run_scenario(kpis, inputs)          → ScenarioResult
  compare_scenarios(kpis, scenarios)  → list[ScenarioResult]

KPI_RELATIONSHIPS is the causal dependency map:
  { driver_variable: { affected_kpi_name: influence_coefficient } }

  influence_coefficient > 0 → driver increase pushes KPI up
  influence_coefficient < 0 → driver increase pushes KPI down
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Causal dependency map  (expand per domain / per-project config)
# ---------------------------------------------------------------------------

KPI_RELATIONSHIPS: Dict[str, Dict[str, float]] = {
    # Defect rate reduction → production up, cost down
    "defect_rate_change": {
        "production_rate": -0.6,
        "cost": 0.8,
        "defect_rate": 1.0,
        "quality_score": -0.7,
    },
    # Maintenance frequency increase → downtime down, cost up slightly
    "maintenance_frequency_increase": {
        "downtime": -0.7,
        "cost": 0.3,
        "reliability": -0.5,
    },
    # Production rate adjustment → output up, cost slightly up
    "production_rate_adjustment": {
        "production_rate": 1.0,
        "cost": 0.2,
        "throughput": 0.9,
    },
    # NPT reduction (Non-Productive Time)
    "npt_reduction": {
        "downtime": -1.0,
        "npt_cost": -0.9,
        "production_rate": 0.6,
    },
    # Staff efficiency improvement
    "staff_efficiency_improvement": {
        "throughput": 0.8,
        "cost": -0.4,
        "quality_score": -0.3,
    },
    # ── DDR Drilling-Specific Levers (P3) ──
    "mud_weight_change": {
        "rop": -0.25,           # heavier mud slows ROP
        "wellbore_stability": 0.6,
        "differential_sticking_risk": 0.3,
        "lost_circulation_risk": 0.4,
        "npt_cost": -0.15,      # stability reduces NPT
        "cost": 0.1,            # marginally higher mud cost
    },
    "wob_adjustment": {
        "rop": 0.7,             # more WOB → faster ROP (up to a point)
        "bit_wear_rate": 0.5,
        "torque": 0.4,
        "cost": 0.15,           # bit replacement cost
        "downtime": 0.1,        # potential bit trips
    },
    "rpm_change": {
        "rop": 0.5,             # faster rotation → faster drilling
        "torque": 0.6,
        "vibration_risk": 0.4,
        "bit_wear_rate": 0.35,
        "cost": 0.05,
    },
    "rop_target": {
        "rop": 1.0,             # direct ROP target
        "cost": -0.4,           # faster → less rig time
        "npt_cost": -0.2,
        "footage_per_day": 0.9,
        "production_rate": 0.3,
    },
    "bop_test_interval": {
        "safety_score": 0.5,    # more frequent testing → safer
        "npt_cost": 0.3,        # testing is non-drilling time
        "downtime": 0.2,
        "compliance_score": 0.6,
        "cost": 0.15,
    },
}

# Financial multipliers per KPI type ($/unit-delta)
FINANCIAL_MULTIPLIERS: Dict[str, float] = {
    "production_rate": 1_000.0,
    "throughput": 800.0,
    "downtime": -500.0,
    "npt_cost": -1.0,         # direct dollar offset
    "cost": -1.0,             # direct dollar offset
    "defect_rate": -500.0,
    "quality_score": 300.0,
    "reliability": 400.0,
    # DDR drilling KPIs (P3)
    "rop": 2_000.0,           # faster ROP = less rig time
    "bit_wear_rate": -800.0,
    "torque": -200.0,
    "vibration_risk": -600.0,
    "wellbore_stability": 1_500.0,
    "differential_sticking_risk": -2_000.0,
    "lost_circulation_risk": -3_000.0,
    "footage_per_day": 1_200.0,
    "safety_score": 5_000.0,
    "compliance_score": 2_000.0,
}

# Lever input validation ranges (min, max as %)
LEVER_RANGES: Dict[str, tuple] = {
    "defect_rate_change": (-50, 50),
    "maintenance_frequency_increase": (-30, 100),
    "production_rate_adjustment": (-20, 50),
    "npt_reduction": (-100, 0),
    "staff_efficiency_improvement": (-20, 50),
    # DDR drilling levers (P3)
    "mud_weight_change": (-15, 30),       # ppg % change
    "wob_adjustment": (-30, 50),          # klbs % change
    "rpm_change": (-30, 50),              # RPM % change
    "rop_target": (-20, 100),             # ROP ft/hr % target
    "bop_test_interval": (-50, 100),      # interval % change
}


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------

def _build_kpi_map(kpis: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Convert KPI list to {lower_name: kpi_dict} map."""
    return {
        (k.get("name") or k.get("title") or "").lower(): k
        for k in kpis
    }


def simulate_kpi_changes(
    kpis: List[Dict[str, Any]],
    inputs: Dict[str, float],
    relationships: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Compute simulated KPI values given lever inputs.

    inputs: { lever_name: percentage_change }
      e.g. {"defect_rate_change": -10, "maintenance_frequency_increase": 15}

    Returns a dict keyed by KPI name (lowercase):
      {
        kpi_name: {
          "base": float,
          "simulated": float,
          "delta": float,
          "unit": str,
        }
      }
    """
    rel = relationships if relationships is not None else KPI_RELATIONSHIPS
    kpi_map = _build_kpi_map(kpis)
    simulated: Dict[str, Dict[str, Any]] = {}

    # Collect all KPI names that could be affected
    affected: set = set()
    for lever, effects in rel.items():
        if lever in inputs:
            affected.update(effects.keys())

    for kpi_name in affected:
        # Find the actual KPI (by any matching key)
        kpi = next(
            (k for k in kpis
             if (k.get("name") or k.get("title") or "").lower() == kpi_name),
            None,
        )
        base_value = float(kpi.get("value", 0)) if kpi else 0.0
        unit = (kpi or {}).get("unit", "")

        total_pct_change = 0.0
        for lever, pct_input in inputs.items():
            if lever in rel:
                coeff = rel[lever].get(kpi_name, 0.0)
                total_pct_change += coeff * float(pct_input) / 100.0

        simulated_value = base_value * (1.0 + total_pct_change)

        simulated[kpi_name] = {
            "base":      round(base_value, 4),
            "simulated": round(simulated_value, 4),
            "delta":     round(simulated_value - base_value, 4),
            "unit":      unit,
        }

    return simulated


def calculate_financial_impact(simulated_kpis: Dict[str, Dict[str, Any]]) -> float:
    """Estimate total financial impact (positive = gain, negative = loss)."""
    total = 0.0
    for kpi_name, data in simulated_kpis.items():
        delta = data.get("delta", 0.0)
        multiplier = FINANCIAL_MULTIPLIERS.get(kpi_name, 0.0)
        total += delta * multiplier
    return round(total, 2)


def _narrative(inputs: Dict[str, float], simulated: Dict[str, Dict[str, Any]], impact: float) -> str:
    """Generate a short executive-tone narrative for the scenario."""
    drivers = [k.replace("_", " ") for k, v in inputs.items() if v != 0]
    drivers_str = ", ".join(drivers) if drivers else "selected levers"

    gainers = [f"{k} ({'+'  if d['delta'] >= 0 else ''}{d['delta']:.2f}{d['unit']})"
               for k, d in simulated.items() if d['delta'] > 0]
    losers  = [f"{k} ({'+'  if d['delta'] >= 0 else ''}{d['delta']:.2f}{d['unit']})"
               for k, d in simulated.items() if d['delta'] < 0]

    parts = [f"Adjusting {drivers_str}:"]
    if gainers:
        parts.append("Improvements — " + ", ".join(gainers[:3]) + ("…" if len(gainers) > 3 else ""))
    if losers:
        parts.append("Trade-offs — " + ", ".join(losers[:3]) + ("…" if len(losers) > 3 else ""))
    if impact > 0:
        parts.append(f"Net financial benefit: +${impact:,.0f}")
    elif impact < 0:
        parts.append(f"Net financial cost: ${impact:,.0f}")
    else:
        parts.append("Minimal net financial impact estimated.")

    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_scenario(
    kpis: List[Dict[str, Any]],
    inputs: Dict[str, float],
    scenario_name: str = "Custom Scenario",
    relationships: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """
    Main entry point — run a single scenario.

    Returns:
      {
        "name":             str,
        "inputs":           dict,
        "simulatedKpis":    dict,
        "financialImpact":  float,
        "narrative":        str,
        "warnings":         list,
      }
    """
    # Validate lever ranges
    warnings: List[str] = []
    for lever, value in inputs.items():
        if lever in LEVER_RANGES:
            lo, hi = LEVER_RANGES[lever]
            if value < lo or value > hi:
                warnings.append(
                    f"Lever '{lever}' value {value}% is outside recommended range [{lo}, {hi}]"
                )

    simulated = simulate_kpi_changes(kpis, inputs, relationships)
    impact = calculate_financial_impact(simulated)
    narrative = _narrative(inputs, simulated, impact)

    return {
        "name":            scenario_name,
        "inputs":          inputs,
        "simulatedKpis":   simulated,
        "financialImpact": impact,
        "narrative":       narrative,
        "warnings":        warnings,
    }


def compare_scenarios(
    kpis: List[Dict[str, Any]],
    scenarios: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Run multiple scenarios and return results list (sorted by financialImpact desc).

    scenarios: list of { "name": str, "inputs": dict }
    """
    results = []
    for s in scenarios:
        result = run_scenario(kpis, s.get("inputs", {}), s.get("name", "Scenario"))
        results.append(result)
    results.sort(key=lambda r: r["financialImpact"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Preset scenarios library
# ---------------------------------------------------------------------------

PRESET_SCENARIOS = [
    {
        "name": "Reduce Defect Rate 10%",
        "inputs": {"defect_rate_change": -10},
    },
    {
        "name": "Increase Maintenance +20%",
        "inputs": {"maintenance_frequency_increase": 20},
    },
    {
        "name": "Boost Production Rate 5%",
        "inputs": {"production_rate_adjustment": 5},
    },
    {
        "name": "NPT Reduction 15%",
        "inputs": {"npt_reduction": 15},
    },
    {
        "name": "Combined: Defect -10% + Maintenance +15%",
        "inputs": {"defect_rate_change": -10, "maintenance_frequency_increase": 15},
    },
]
