"""
metrics.py

Pure calculation functions for evaluating wind forecast accuracy and utility risk:
- Error definition: error = forecast - actual
- Metrics: MAE, RMSE, Bias, P50/P90/P95 of Absolute Error
- Directional metric: Over-forecast percentage (% of slots where forecast > actual)
- Risk metric: 90% Safe MW Buffer against generation shortfalls
- Hourly grouping: Metrics calculated across each hour of the day (0-23)
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd


def compute_mae(errors: np.ndarray) -> float:
    """Computes Mean Absolute Error (MW)."""
    return float(np.mean(np.abs(errors)))


def compute_rmse(errors: np.ndarray) -> float:
    """Computes Root Mean Squared Error (MW)."""
    return float(np.sqrt(np.mean(errors ** 2)))


def compute_bias(errors: np.ndarray) -> float:
    """
    Computes mean forecast bias (MW).
    Positive bias indicates over-forecasting (forecast > actual).
    Negative bias indicates under-forecasting (forecast < actual).
    """
    return float(np.mean(errors))


def compute_over_forecast_pct(errors: np.ndarray) -> float:
    """
    Computes the percentage of slots where forecast exceeded actual generation (error > 0).
    
    WHY:
    A high over-forecast percentage indicates systematic positive bias where the utility
    consistently risks being short of energy in the day-ahead position.
    """
    if len(errors) == 0:
        return 0.0
    return float(np.mean(errors > 0) * 100.0)


def compute_absolute_error_percentiles(errors: np.ndarray) -> Dict[str, float]:
    """Computes the 50th, 90th, and 95th percentiles of absolute errors."""
    abs_errors = np.abs(errors)
    return {
        "p50": float(np.percentile(abs_errors, 50)),
        "p90": float(np.percentile(abs_errors, 90)),
        "p95": float(np.percentile(abs_errors, 95)),
    }


def compute_safe_mw_buffer_90(errors: np.ndarray) -> float:
    """
    Computes the MW buffer needed to be 90% safe against wind generation shortfall.
    
    WHY:
    In power system operations and energy trading, shortfall occurs when actual wind
    generation is less than forecasted (and thus less than what was committed to the grid).
    With error = forecast - actual:
    - Positive error (error > 0) means actual < forecast (a shortfall requiring replacement power).
    - Negative error means actual > forecast (excess wind).
    To be 90% safe against shortfalls, the utility maintains a reserve buffer equal to
    the 90th percentile of positive shortfalls (i.e. max(0, error)), ensuring that
    shortfalls do not exceed the buffer in at least 90% of half-hour periods.
    """
    shortfalls = np.maximum(0.0, errors)
    return float(np.percentile(shortfalls, 90))


def calculate_summary_metrics(errors: np.ndarray) -> Dict[str, Any]:
    """
    Computes all core accuracy, directional, and risk metrics for a given error array.
    """
    if len(errors) == 0:
        return {
            "count": 0,
            "mae": 0.0,
            "rmse": 0.0,
            "bias": 0.0,
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "buffer_90": 0.0,
            "over_forecast_pct": 0.0,
        }

    err_arr = np.asarray(errors, dtype=float)
    pcts = compute_absolute_error_percentiles(err_arr)
    
    return {
        "count": int(len(err_arr)),
        "mae": round(compute_mae(err_arr), 2),
        "rmse": round(compute_rmse(err_arr), 2),
        "bias": round(compute_bias(err_arr), 2),
        "p50": round(pcts["p50"], 2),
        "p90": round(pcts["p90"], 2),
        "p95": round(pcts["p95"], 2),
        "buffer_90": round(compute_safe_mw_buffer_90(err_arr), 2),
        "over_forecast_pct": round(compute_over_forecast_pct(err_arr), 1),
    }


def calculate_metrics_by_hour(df_aligned: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Computes accuracy and risk metrics grouped by hour of the day (0 to 23).
    
    WHY:
    Wind generation forecasting errors often follow diurnal patterns due to
    thermal transitions at sunrise and sunset, or changing atmospheric boundary
    layers. Evaluating hour-by-hour metrics shows operators when uncertainty peaks.
    """
    if "hour" not in df_aligned.columns:
        hours = df_aligned["startTime"].dt.hour
    else:
        hours = df_aligned["hour"]

    hourly_results = []
    for h in range(24):
        mask = hours == h
        subset_errors = df_aligned.loc[mask, "error"].dropna().to_numpy()
        summary = calculate_summary_metrics(subset_errors)
        summary["hour"] = h
        hourly_results.append(summary)

    return hourly_results
