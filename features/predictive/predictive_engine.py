"""
Predictive Engine
=================

Forecasts future KPI values using an ensemble of models:
  1. Linear Regression  (always available — baseline)
  2. ARIMA              (structured time series)
  3. Prophet            (seasonal / trend)
  4. XGBoost            (nonlinear / ML)

Model selection: each model is evaluated on a held-out slice using MAPE.
The final result returns individual model forecasts + an ensemble average.

Entry point:
  forecast_kpi(kpi)  → ForecastResult dict (or None when data insufficient)
"""
from __future__ import annotations

import logging
import warnings
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Suppress noisy warnings from forecasting libraries
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="prophet")
warnings.filterwarnings("ignore", category=UserWarning, module="statsmodels")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FORECAST_STEPS = 5          # periods ahead to predict
MIN_HISTORY = 5             # minimum points needed
ENSEMBLE_MIN_HISTORY = 10   # minimum points for full ensemble


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_history(history: List[float]) -> List[float]:
    """Remove NaN/None/inf values and return clean numeric list."""
    cleaned = []
    for v in history:
        try:
            fv = float(v)
            if np.isfinite(fv):
                cleaned.append(fv)
        except (TypeError, ValueError):
            continue
    return cleaned


def _mape(actual: List[float], predicted: List[float]) -> float:
    """Mean Absolute Percentage Error (0–100 scale)."""
    a = np.array(actual, dtype=float)
    p = np.array(predicted[:len(a)], dtype=float)
    mask = a != 0
    if not mask.any():
        return 100.0
    return float(np.mean(np.abs((a[mask] - p[mask]) / a[mask])) * 100)


def _trend_label(history: List[float], forecast: List[float]) -> str:
    if not history or not forecast:
        return "stable"
    return "up" if forecast[-1] > history[-1] else "down"


# ---------------------------------------------------------------------------
# Individual model forecasters
# ---------------------------------------------------------------------------

def _forecast_linear(history: List[float]) -> Optional[List[float]]:
    """Fast, always-available baseline."""
    try:
        from sklearn.linear_model import LinearRegression  # type: ignore
        X = np.arange(len(history)).reshape(-1, 1)
        y = np.array(history)
        model = LinearRegression()
        model.fit(X, y)
        future_X = np.arange(len(history), len(history) + FORECAST_STEPS).reshape(-1, 1)
        return model.predict(future_X).tolist()
    except Exception as exc:
        logger.debug("Linear forecast failed: %s", exc)
        return None


def _forecast_arima(history: List[float]) -> Optional[List[float]]:
    """ARIMA time-series forecasting with auto-order fallback."""
    try:
        from statsmodels.tsa.arima.model import ARIMA  # type: ignore

        arr = np.array(history, dtype=float)
        # Check for constant series (ARIMA fails on zero-variance)
        if np.std(arr) < 1e-10:
            return [float(arr[-1])] * FORECAST_STEPS

        # Try multiple ARIMA orders, fall back on failure
        orders = [(2, 1, 2), (1, 1, 1), (1, 0, 1), (0, 1, 1)]
        for order in orders:
            try:
                model = ARIMA(arr, order=order)
                fit = model.fit()
                forecast = fit.forecast(steps=FORECAST_STEPS)
                result = [float(v) for v in forecast]
                # Sanity check: reject forecasts with NaN or extreme values
                if any(not np.isfinite(v) for v in result):
                    continue
                return result
            except Exception:
                continue

        logger.debug("ARIMA: all order combinations failed")
        return None

    except ImportError:
        logger.warning("statsmodels not installed — ARIMA forecasting disabled")
        return None
    except Exception as exc:
        logger.debug("ARIMA forecast failed: %s", exc)
        return None


def _forecast_prophet(history: List[float]) -> Optional[List[float]]:
    """Prophet seasonal/trend forecasting."""
    try:
        import pandas as pd  # type: ignore
        from prophet import Prophet  # type: ignore

        arr = np.array(history, dtype=float)
        # Prophet needs at least 2 non-NaN rows
        if len(arr) < 2 or np.std(arr) < 1e-10:
            return [float(arr[-1])] * FORECAST_STEPS

        df = pd.DataFrame({
            "ds": pd.date_range(start="2020-01-01", periods=len(arr), freq="D"),
            "y": arr,
        })

        # Suppress Prophet console output
        m = Prophet(
            daily_seasonality=False,
            weekly_seasonality=False,
            yearly_seasonality=False,
        )
        m.fit(df)
        future = m.make_future_dataframe(periods=FORECAST_STEPS)
        forecast = m.predict(future)
        result = forecast["yhat"].tail(FORECAST_STEPS).tolist()

        if any(not np.isfinite(v) for v in result):
            return None
        return [float(v) for v in result]

    except ImportError:
        logger.warning("prophet not installed — Prophet forecasting disabled")
        return None
    except Exception as exc:
        logger.debug("Prophet forecast failed: %s", exc)
        return None


def _forecast_xgboost(history: List[float]) -> Optional[List[float]]:
    """XGBoost sliding-window regression forecasting."""
    try:
        from xgboost import XGBRegressor  # type: ignore

        arr = np.array(history, dtype=float)
        window = min(3, len(arr) - 1)
        if len(arr) < window + 2:
            return None

        # Build supervised learning features from sliding window
        X, y = [], []
        for i in range(len(arr) - window):
            X.append(arr[i: i + window].tolist())
            y.append(float(arr[i + window]))

        X_np = np.array(X, dtype=float)
        y_np = np.array(y, dtype=float)

        model = XGBRegressor(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.1,
            verbosity=0,
        )
        model.fit(X_np, y_np)

        # Iterative multi-step forecast
        preds: List[float] = []
        last_window = arr[-window:].tolist()
        for _ in range(FORECAST_STEPS):
            pred = float(model.predict(np.array([last_window]))[0])
            if not np.isfinite(pred):
                break
            preds.append(pred)
            last_window = last_window[1:] + [pred]

        return preds if len(preds) == FORECAST_STEPS else None

    except ImportError:
        logger.warning("xgboost not installed — XGBoost forecasting disabled")
        return None
    except Exception as exc:
        logger.debug("XGBoost forecast failed: %s", exc)
        return None


def _ensemble(forecasts: List[Optional[List[float]]]) -> Optional[List[float]]:
    valid = [f for f in forecasts if f and len(f) == FORECAST_STEPS]
    if not valid:
        return None
    return np.mean(valid, axis=0).tolist()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def forecast_kpi(kpi: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Main entry point.

    kpi must contain:
      "history"  : List[float]  — chronological values

    Optional fields used for labelling:
      "name"  / "title"
      "unit"
      "target"

    Returns a ForecastResult dict or None when data is insufficient.
    """
    raw_history: List = kpi.get("history", [])
    history = _clean_history(raw_history)

    if len(history) < MIN_HISTORY:
        return None

    linear_pred  = _forecast_linear(history)
    arima_pred   = _forecast_arima(history) if len(history) >= ENSEMBLE_MIN_HISTORY else None
    prophet_pred = _forecast_prophet(history) if len(history) >= ENSEMBLE_MIN_HISTORY else None
    xgb_pred     = _forecast_xgboost(history) if len(history) >= ENSEMBLE_MIN_HISTORY else None

    ens = _ensemble([linear_pred, arima_pred, prophet_pred, xgb_pred])
    primary = ens or linear_pred  # fall back to linear if ensemble empty

    # Track which models succeeded
    models_used: List[str] = []
    if linear_pred:
        models_used.append("linear")
    if arima_pred:
        models_used.append("arima")
    if prophet_pred:
        models_used.append("prophet")
    if xgb_pred:
        models_used.append("xgboost")
    if ens:
        models_used.append("ensemble")

    # Model scores (MAPE on 80/20 split)
    model_scores: Dict[str, float] = {}
    split = int(len(history) * 0.8)
    if split >= MIN_HISTORY:
        train, test = history[:split], history[split:]
        for name, func in [("linear", _forecast_linear), ("arima", _forecast_arima),
                            ("xgboost", _forecast_xgboost)]:
            try:
                p = func(train)
                if p and len(p) >= len(test):
                    model_scores[name] = round(_mape(test, p[:len(test)]), 2)
            except Exception:
                pass

    trend = _trend_label(history, primary or [])
    slope = float(np.polyfit(range(len(history)), history, 1)[0]) if len(history) >= 2 else 0.0

    return {
        "forecast":      primary,              # list of FORECAST_STEPS floats
        "trend":         trend,                # "up" | "down"
        "slope":         round(slope, 4),
        "models": {
            "linear":    [round(v, 2) for v in linear_pred]  if linear_pred  else None,
            "arima":     [round(v, 2) for v in arima_pred]   if arima_pred   else None,
            "prophet":   [round(v, 2) for v in prophet_pred] if prophet_pred else None,
            "xgboost":   [round(v, 2) for v in xgb_pred]     if xgb_pred     else None,
            "ensemble":  [round(v, 2) for v in ens]          if ens          else None,
        },
        "modelsUsed":    models_used,
        "modelScores":   model_scores,
        "forecastSteps": FORECAST_STEPS,
        "historyLength": len(history),
    }
