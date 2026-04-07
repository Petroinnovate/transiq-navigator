"""
KPI Intelligence Engine — AI-driven scoring, ranking, widget assignment,
predictive forecasting, risk detection, and what-if simulation.

Exposes:
  process_kpis(kpis)                → enriched pool with priorityScore / visibility
  map_kpis_to_widgets(kpis)         → widget assignment dict for frontend
  forecast_kpi(kpi)                 → ForecastResult dict (or None)
  detect_risk(kpi, forecast)        → RiskResult dict (or None)
  generate_decision(kpi, f, r)      → recommendation string
  enrich_kpi_with_predictions(k, f) → kpi dict with prediction fields
  run_scenario(kpis, inputs)        → ScenarioResult dict
  compare_scenarios(kpis, scenarios)→ list[ScenarioResult]
  PRESET_SCENARIOS                  → list of named what-if presets
"""
from .kpi_engine import process_kpis, compute_priority_score, assign_visibility
from .widget_mapper import map_kpis_to_widgets
from .predictive_engine import forecast_kpi
from .risk_engine import detect_risk, generate_decision, enrich_kpi_with_predictions
from .whatif_engine import run_scenario, compare_scenarios, PRESET_SCENARIOS

__all__ = [
    "process_kpis",
    "compute_priority_score",
    "assign_visibility",
    "map_kpis_to_widgets",
    "forecast_kpi",
    "detect_risk",
    "generate_decision",
    "enrich_kpi_with_predictions",
    "run_scenario",
    "compare_scenarios",
    "PRESET_SCENARIOS",
]
