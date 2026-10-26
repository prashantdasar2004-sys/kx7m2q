"""
test_metrics.py

Unit tests for accuracy metrics, percentiles, and risk buffer calculations.
Validates math against known hand-calculated values.
"""

import numpy as np
import pandas as pd
import pytest

from app.metrics import (
    compute_mae,
    compute_rmse,
    compute_bias,
    compute_over_forecast_pct,
    compute_absolute_error_percentiles,
    compute_safe_mw_buffer_90,
    calculate_summary_metrics,
    calculate_metrics_by_hour,
)


def test_hand_calculated_metrics():
    """
    Validates MAE, RMSE, Bias, percentiles, and over-forecast share against manually pre-calculated values.
    
    Given:
    errors = [-100.0, 200.0, -300.0, 400.0, 0.0]
    
    Hand-calculated:
    - Count = 5
    - MAE = (100 + 200 + 300 + 400 + 0) / 5 = 200.0 MW
    - RMSE = sqrt((10000 + 40000 + 90000 + 160000 + 0) / 5) = sqrt(60000) ≈ 244.95 MW
    - Bias = (-100 + 200 - 300 + 400 + 0) / 5 = 40.0 MW
    - P50 of abs_error [0, 100, 200, 300, 400] = 200.0 MW
    - Shortfalls = max(0, error) = [0, 200, 0, 400, 0] -> sorted [0, 0, 0, 200, 400]
      90th percentile = 320.0 MW
    - Over-forecast % = 2 / 5 = 40.0%
    """
    errors = np.array([-100.0, 200.0, -300.0, 400.0, 0.0])
    
    summary = calculate_summary_metrics(errors)
    
    assert summary["count"] == 5
    assert summary["mae"] == 200.0
    assert summary["rmse"] == 244.95
    assert summary["bias"] == 40.0
    assert summary["p50"] == 200.0
    assert summary["p90"] == 360.0  # linear interpolation of abs_error [0, 100, 200, 300, 400] at 90%
    assert summary["buffer_90"] == 320.0
    assert summary["over_forecast_pct"] == 40.0


def test_positive_and_negative_bias():
    """Verifies that over-forecasting yields positive bias and under-forecasting negative bias."""
    over_forecast_errors = np.array([50.0, 100.0, 150.0])
    assert compute_bias(over_forecast_errors) == 100.0
    assert compute_over_forecast_pct(over_forecast_errors) == 100.0
    
    under_forecast_errors = np.array([-50.0, -100.0, -150.0])
    assert compute_bias(under_forecast_errors) == -100.0
    assert compute_over_forecast_pct(under_forecast_errors) == 0.0


def test_safe_mw_buffer_when_no_shortfall():
    """
    When actual generation always exceeds forecast (actual >= forecast -> error <= 0),
    shortfall is 0, so the 90% safe buffer required should be 0 MW.
    """
    no_shortfall_errors = np.array([-100.0, -50.0, 0.0, -20.0])
    buffer = compute_safe_mw_buffer_90(no_shortfall_errors)
    assert buffer == 0.0
    assert compute_over_forecast_pct(no_shortfall_errors) == 0.0


def test_metrics_grouped_by_hour():
    """
    Verifies that calculate_metrics_by_hour computes metrics across each hour (0-23).
    """
    df = pd.DataFrame([
        # Hour 8: both over-forecast
        {"startTime": pd.Timestamp("2026-01-01 08:00:00", tz="Europe/London"), "error": 100.0},
        {"startTime": pd.Timestamp("2026-01-01 08:30:00", tz="Europe/London"), "error": 200.0},
        # Hour 9: both under-forecast
        {"startTime": pd.Timestamp("2026-01-01 09:00:00", tz="Europe/London"), "error": -50.0},
        {"startTime": pd.Timestamp("2026-01-01 09:30:00", tz="Europe/London"), "error": -150.0},
    ])
    
    hourly = calculate_metrics_by_hour(df)
    
    assert len(hourly) == 24
    
    # Hour 8
    h8 = hourly[8]
    assert h8["count"] == 2
    assert h8["mae"] == 150.0
    assert h8["bias"] == 150.0
    assert h8["over_forecast_pct"] == 100.0
    
    # Hour 9
    h9 = hourly[9]
    assert h9["count"] == 2
    assert h9["mae"] == 100.0
    assert h9["bias"] == -100.0
    assert h9["over_forecast_pct"] == 0.0
    
    # Hour 0 (no data)
    h0 = hourly[0]
    assert h0["count"] == 0
    assert h0["over_forecast_pct"] == 0.0
