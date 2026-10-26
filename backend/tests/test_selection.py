"""
test_selection.py

Unit tests for forecast selection and hourly-to-half-hourly alignment.
Verifies strict D-1 cutoff enforcement (no lookahead bias) and carry-forward logic.
"""

import pandas as pd
import pytest

from app.selection import (
    compute_d_minus_one_cutoff,
    select_latest_forecasts_for_day,
    carry_forward_hourly_to_half_hourly,
    select_forecasts_for_window,
    get_slot_audit_trail,
)


def test_d_minus_one_cutoff_computation():
    """Verifies that cutoff is calculated exactly for D-1 at specified morning hour."""
    delivery_date = pd.Timestamp("2026-01-15").date()
    cutoff = compute_d_minus_one_cutoff(delivery_date, cutoff_time_str="09:00", tz_str="Europe/London")
    
    expected = pd.Timestamp("2026-01-14 09:00:00", tz="Europe/London")
    assert cutoff == expected


def test_ignore_forecast_published_after_cutoff():
    """
    CRITICAL LOOKAHEAD TEST:
    Ensures that any forecast published after the morning D-1 cutoff is ignored,
    and only the latest run published AT OR BEFORE the cutoff is chosen.
    """
    delivery_date = pd.Timestamp("2026-01-10").date()
    # D-1 cutoff: 2026-01-09 09:00:00 Europe/London
    
    sample_data = [
        # Run 1: Early morning run (valid, but superseded)
        {
            "startTime": pd.Timestamp("2026-01-10 12:00:00", tz="Europe/London"),
            "publishTime": pd.Timestamp("2026-01-09 06:00:00", tz="Europe/London"),
            "generation": 1000,
        },
        # Run 2: Latest run before 09:00 cutoff (THIS MUST BE CHOSEN)
        {
            "startTime": pd.Timestamp("2026-01-10 12:00:00", tz="Europe/London"),
            "publishTime": pd.Timestamp("2026-01-09 08:30:00", tz="Europe/London"),
            "generation": 1200,
        },
        # Run 3: Published at 09:30, after cutoff (MUST BE IGNORED)
        {
            "startTime": pd.Timestamp("2026-01-10 12:00:00", tz="Europe/London"),
            "publishTime": pd.Timestamp("2026-01-09 09:30:00", tz="Europe/London"),
            "generation": 1500,
        },
        # Run 4: Published at 17:00, evening after cutoff (MUST BE IGNORED)
        {
            "startTime": pd.Timestamp("2026-01-10 12:00:00", tz="Europe/London"),
            "publishTime": pd.Timestamp("2026-01-09 17:00:00", tz="Europe/London"),
            "generation": 1800,
        },
    ]
    df_fc = pd.DataFrame(sample_data)
    
    selected = select_latest_forecasts_for_day(df_fc, delivery_date, cutoff_time_str="09:00")
    
    assert len(selected) == 1
    chosen = selected.iloc[0]
    assert chosen["generation"] == 1200
    assert chosen["publishTime"] == pd.Timestamp("2026-01-09 08:30:00", tz="Europe/London")


def test_carry_forward_hourly_to_half_hourly():
    """
    Verifies that an hourly forecast is forward-filled over the subsequent 30-minute slot,
    preserving the forecast value and calculating the proper forecast horizon in hours.
    """
    df_hourly = pd.DataFrame([{
        "startTime": pd.Timestamp("2026-01-10 14:00:00", tz="Europe/London"),
        "publishTime": pd.Timestamp("2026-01-09 08:00:00", tz="Europe/London"),
        "generation": 2500,
    }])
    
    df_half = carry_forward_hourly_to_half_hourly(df_hourly)
    
    assert len(df_half) == 2
    
    # Slot 1: 14:00 (horizon: 30 hours from Jan 9 08:00 to Jan 10 14:00)
    slot1 = df_half.iloc[0]
    assert slot1["startTime"] == pd.Timestamp("2026-01-10 14:00:00", tz="Europe/London")
    assert slot1["forecast"] == 2500
    assert slot1["horizon_hours"] == 30.0
    
    # Slot 2: 14:30 (horizon: 30.5 hours, forecast carried forward)
    slot2 = df_half.iloc[1]
    assert slot2["startTime"] == pd.Timestamp("2026-01-10 14:30:00", tz="Europe/London")
    assert slot2["forecast"] == 2500
    assert slot2["horizon_hours"] == 30.5


def test_audit_trail_identifies_next_excluded_publish_time():
    """
    Verifies that get_slot_audit_trail correctly identifies both the chosen run
    and the subsequent run that was excluded by the cutoff.
    """
    sample_data = [
        {
            "startTime": pd.Timestamp("2026-01-10 10:00:00", tz="Europe/London"),
            "publishTime": pd.Timestamp("2026-01-09 07:00:00", tz="Europe/London"),
            "generation": 800,
        },
        {
            "startTime": pd.Timestamp("2026-01-10 10:00:00", tz="Europe/London"),
            "publishTime": pd.Timestamp("2026-01-09 11:00:00", tz="Europe/London"),
            "generation": 950,
        },
    ]
    df_fc = pd.DataFrame(sample_data)
    target_slot = pd.Timestamp("2026-01-10 10:30:00", tz="Europe/London")
    
    audit = get_slot_audit_trail(df_fc, target_slot, cutoff_time_str="09:00")
    
    assert audit["chosen_publish_time"] == pd.Timestamp("2026-01-09 07:00:00", tz="Europe/London")
    assert audit["chosen_generation"] == 800
    assert audit["next_excluded_publish_time"] == pd.Timestamp("2026-01-09 11:00:00", tz="Europe/London")
    assert audit["next_excluded_generation"] == 950
