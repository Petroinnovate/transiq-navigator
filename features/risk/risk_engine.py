"""
Risk & Decision Engine
======================

Takes a KPI dict and its ForecastResult and produces:
  - risk_level       : "low" | "medium" | "high" | "critical"
  - breach_predicted : bool
  - time_to_breach   : int | None  (forecast steps until target breach)
  - financial_risk   : float | None
  - decision         : str  (human-readable recommendation)

Entry points:
  detect_risk(kpi, forecast_data)           → RiskResult dict or None
  generate_decision(kpi, forecast, risk)    → str
"""
from __future__ import annotations

from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Risk detection
# ---------------------------------------------------------------------------

def detect_risk(kpi: Dict[str, Any], forecast_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Evaluate whether the forecast will breach the KPI target.

    kpi fields used:
      target    : float | None
      direction : "increase" | "decrease"   (default "increase")
      value     : float  (current value)

    Returns a RiskResult dict or None.
    """
    if not forecast_data:
        return None

    forecast: list = forecast_data.get("forecast") or []
    if not forecast:
        return None

    target = kpi.get("target")
    direction = (kpi.get("direction") or "increase").lower()
    current_value = kpi.get("value")

    # --- breach detection ---
    breach = False
    time_to_breach: Optional[int] = None

    if target is not None:
        try:
            t = float(target)
            for i, val in enumerate(forecast):
                v = float(val)
                breached = (v < t) if direction == "increase" else (v > t)
                if breached:
                    breach = True
                    time_to_breach = i + 1
                    break
        except (TypeError, ValueError):
            pass

    # --- risk level ---
    trend = forecast_data.get("trend", "stable")
    risk_level = "low"

    if breach:
        risk_level = "critical" if time_to_breach is not None and time_to_breach <= 2 else "high"
    elif target is not None:
        try:
            gap = abs(float(forecast[-1]) - float(target)) / abs(float(target))
            if trend == "down" and gap > 0.15:
                risk_level = "medium"
            elif gap > 0.25:
                risk_level = "medium"
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    elif trend == "down":
        risk_level = "medium"

    # --- financial risk estimate (very rough) ---
    financial_risk: Optional[float] = None
    if current_value is not None and target is not None:
        try:
            gap_amount = float(target) - float(current_value)
            # Each 1% gap ≈ $5 000 lost (placeholder factor — override per use-case)
            financial_risk = round(abs(gap_amount) * 5_000, 0)
        except (TypeError, ValueError):
            pass

    return {
        "riskLevel":     risk_level,
        "breachPredicted": breach,
        "timeToBreach":  time_to_breach,
        "financialRisk": financial_risk,
    }


# ---------------------------------------------------------------------------
# Decision / recommendation
# ---------------------------------------------------------------------------

def generate_decision(
    kpi: Dict[str, Any],
    forecast_data: Optional[Dict[str, Any]],
    risk_data: Optional[Dict[str, Any]],
) -> str:
    """
    Produce a short, executive-tone recommendation string.
    """
    if not forecast_data:
        return "Insufficient history to generate a forecast."

    name = kpi.get("name") or kpi.get("title") or "This KPI"
    trend = forecast_data.get("trend", "stable")
    risk_level = (risk_data or {}).get("riskLevel", "low")
    time_to_breach = (risk_data or {}).get("timeToBreach")
    financial_risk = (risk_data or {}).get("financialRisk")

    if risk_level == "critical":
        period = f"in {time_to_breach} period{'s' if time_to_breach != 1 else ''}" if time_to_breach else "imminently"
        fin = f" (~${financial_risk:,.0f} at risk)" if financial_risk else ""
        return f"CRITICAL: {name} is forecast to breach its target {period}{fin}. Immediate action required."

    if risk_level == "high":
        fin = f" (~${financial_risk:,.0f} at risk)" if financial_risk else ""
        return f"HIGH RISK: {name} is likely to miss target{fin}. Escalate and implement corrective measures now."

    if risk_level == "medium":
        return f"WATCH: {name} is trending {'downward' if trend == 'down' else 'unfavourably'}. Monitor closely and prepare contingency plans."

    if trend == "up":
        return f"{name} is on a positive trajectory. Maintain current controls."

    return f"{name} is expected to remain stable. Continue monitoring."


# ---------------------------------------------------------------------------
# Convenience: enrich a single KPI with all predictive fields
# ---------------------------------------------------------------------------

def enrich_kpi_with_predictions(
    kpi: Dict[str, Any],
    forecast_data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Returns a new dict with 'prediction', 'riskForecast', 'futureDecision' added.
    """
    risk = detect_risk(kpi, forecast_data)
    decision = generate_decision(kpi, forecast_data, risk)

    return {
        **kpi,
        "prediction":    forecast_data,
        "riskForecast":  risk,
        "futureDecision": decision,
    }
