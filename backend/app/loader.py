"""
loader.py

Loads and prepares cached Parquet datasets for the application.
Ensures timestamps are localized to the market timezone (Europe/London).
"""

from functools import lru_cache
from pathlib import Path
import pandas as pd

from .config import (
    ACTUALS_PATH,
    FORECASTS_PATH,
    MARKET_TIMEZONE,
    ANALYSIS_START,
    ANALYSIS_END,
)


def load_actuals(path: Path = ACTUALS_PATH, filter_window: bool = True) -> pd.DataFrame:
    """
    Loads FUELHH wind generation actuals from Parquet.
    
    WHY:
    Actual generation records are half-hourly outturn numbers.
    Converting to Europe/London aligns settlement periods with UK market rules.
    Filtering to the January 2026 window isolates the exact decision period.
    """
    if not path.exists():
        raise FileNotFoundError(f"Actuals dataset not found at: {path}")

    df = pd.read_parquet(path)
    # Ensure datetime with Europe/London localization
    df["startTime"] = pd.to_datetime(df["startTime"]).dt.tz_convert(MARKET_TIMEZONE)
    df["publishTime"] = pd.to_datetime(df["publishTime"]).dt.tz_convert(MARKET_TIMEZONE)

    if filter_window:
        start_bound = pd.Timestamp(ANALYSIS_START, tz=MARKET_TIMEZONE)
        end_bound = pd.Timestamp(ANALYSIS_END, tz=MARKET_TIMEZONE)
        df = df[(df["startTime"] >= start_bound) & (df["startTime"] <= end_bound)].copy()

    return df.sort_values("startTime").reset_index(drop=True)


def load_forecasts(path: Path = FORECASTS_PATH) -> pd.DataFrame:
    """
    Loads WINDFOR wind generation forecasts from Parquet.
    
    WHY:
    WINDFOR contains multiple forecast runs published throughout December 2025
    and January 2026. We load all available runs so selection.py can evaluate
    different morning cutoffs without missing historical revisions.
    """
    if not path.exists():
        raise FileNotFoundError(f"Forecasts dataset not found at: {path}")

    df = pd.read_parquet(path)
    df["startTime"] = pd.to_datetime(df["startTime"]).dt.tz_convert(MARKET_TIMEZONE)
    df["publishTime"] = pd.to_datetime(df["publishTime"]).dt.tz_convert(MARKET_TIMEZONE)

    return df.sort_values(["publishTime", "startTime"]).reset_index(drop=True)
