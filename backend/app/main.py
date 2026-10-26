"""
main.py

FastAPI backend application for the UK Wind Generation Decision Utility.
Serves:
- /health: Service health check
- /api/config: Allowed cutoff options, default cutoff, date range
- /api/forecast: 48 half-hour settlement slots for a chosen delivery day
- /api/metrics: Monthly summary metrics for January 2026
- /api/metrics/by-hour: Diurnal metrics grouped across each hour of the day (0-23)
"""

from contextlib import asynccontextmanager
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import (
    ALLOWED_CUTOFFS,
    DEFAULT_CUTOFF,
    MARKET_TIMEZONE,
    ANALYSIS_START,
    ANALYSIS_END,
)
from .loader import load_actuals, load_forecasts
from .selection import (
    compute_d_minus_one_cutoff,
    select_latest_forecasts_for_day,
    carry_forward_hourly_to_half_hourly,
    select_forecasts_for_window,
)
from .metrics import calculate_summary_metrics, calculate_metrics_by_hour


# ---------------------------------------------------------
# Pydantic Response Models
# ---------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status", json_schema_extra={"example": "ok"})


class ConfigResponse(BaseModel):
    allowed_cutoffs: List[str] = Field(..., description="Supported morning D-1 cutoffs")
    default_cutoff: str = Field(..., description="Default D-1 cutoff time")
    date_range: Dict[str, str] = Field(..., description="Start and end bounds for January 2026")
    market_timezone: str = Field(..., description="GB electricity market timezone")


class ForecastSlot(BaseModel):
    slot: int = Field(..., description="Settlement slot index (1 to 48)")
    startTime: str = Field(..., description="ISO 8601 start timestamp with timezone")
    timeLabel: str = Field(..., description="Formatted UK time label (e.g. 14:00)")
    actual: Optional[float] = Field(None, description="Actual wind outturn generation in MW")
    forecast: Optional[float] = Field(None, description="Selected day-ahead forecast in MW")
    error: Optional[float] = Field(None, description="Forecast error (forecast - actual) in MW")
    publishTime: Optional[str] = Field(None, description="Timestamp when the forecast was published")
    horizon_hours: Optional[float] = Field(None, description="Forecast horizon in hours (startTime - publishTime)")


class ForecastDayResponse(BaseModel):
    day: str = Field(..., description="Target delivery date (YYYY-MM-DD)")
    cutoff: str = Field(..., description="Cutoff time used on D-1")
    cutoff_datetime: str = Field(..., description="Full cutoff timestamp on D-1")
    publish_times_summary: str = Field(..., description="Summary of forecast publications used")
    slots: List[ForecastSlot] = Field(..., description="48 half-hour settlement periods")


class MetricsSummaryResponse(BaseModel):
    cutoff_used: str = Field(..., description="Cutoff time applied on D-1")
    count: int = Field(..., description="Total settlement periods evaluated")
    mae: float = Field(..., description="Mean Absolute Error (MW)")
    rmse: float = Field(..., description="Root Mean Squared Error (MW)")
    bias: float = Field(..., description="Mean Signed Error / Bias (MW)")
    p50: float = Field(..., description="50th percentile (median) absolute error (MW)")
    p90: float = Field(..., description="90th percentile absolute error (MW)")
    p95: float = Field(..., description="95th percentile absolute error (MW)")
    buffer_90: float = Field(..., description="Reserve MW buffer needed for 90% shortfall safety")
    over_forecast_pct: float = Field(..., description="Percentage of slots where forecast > actual (%)")


class HourlyMetricItem(BaseModel):
    hour: int = Field(..., description="Hour of the day (0 to 23)")
    hour_label: str = Field(..., description="Formatted hour label (e.g. 09:00)")
    count: int = Field(..., description="Number of settlement periods")
    mae: float = Field(..., description="Mean Absolute Error (MW)")
    rmse: float = Field(..., description="Root Mean Squared Error (MW)")
    bias: float = Field(..., description="Mean Signed Error / Bias (MW)")
    p50: float = Field(..., description="50th percentile absolute error (MW)")
    p90: float = Field(..., description="90th percentile absolute error (MW)")
    p95: float = Field(..., description="95th percentile absolute error (MW)")
    buffer_90: float = Field(..., description="Reserve MW buffer needed for 90% shortfall safety")
    over_forecast_pct: float = Field(..., description="Percentage of slots where forecast > actual (%)")


class HourlyMetricsResponse(BaseModel):
    cutoff_used: str = Field(..., description="Cutoff time applied on D-1")
    hours: List[HourlyMetricItem] = Field(..., description="Metrics grouped by hour of the day")


# ---------------------------------------------------------
# Application Lifespan (Load Parquet data ONCE at startup)
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Loads Parquet datasets into app.state at startup.
    
    WHY:
    Reading Parquet from disk once during server initialization guarantees sub-millisecond
    in-memory queries for API requests and avoids disk I/O bottlenecks.
    """
    app.state.actuals = load_actuals()
    app.state.forecasts = load_forecasts()
    # Pre-cache window selections per cutoff
    app.state.cached_selections = {}
    yield


app = FastAPI(
    title="UK Wind Generation Forecast vs Actuals Utility",
    description="Decision support API for January 2026 wind forecast evaluation.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
# Public dataset: allows all origins so any deployed frontend (e.g. Vercel) can query the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def ensure_data_loaded():
    """
    Guarantees Parquet datasets are loaded into app.state.
    WHY: In serverless environments (e.g. Vercel Serverless Functions), ASGI lifespan
    events might not run before the first HTTP request. This lazy fallback ensures zero errors.
    """
    if not hasattr(app.state, "actuals") or app.state.actuals is None:
        app.state.actuals = load_actuals()
        app.state.forecasts = load_forecasts()
        app.state.cached_selections = {}


def validate_cutoff(cutoff: str) -> str:
    """Ensures requested cutoff is one of the supported pre-auction morning hours."""
    if cutoff not in ALLOWED_CUTOFFS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cutoff '{cutoff}'. Allowed morning cutoffs are: {ALLOWED_CUTOFFS}"
        )
    return cutoff


def get_or_create_monthly_selection(app_state: Any, cutoff: str) -> pd.DataFrame:
    ensure_data_loaded()
    """
    Retrieves or generates the full January 2026 selected forecast DataFrame for a given cutoff.
    """
    if cutoff not in app_state.cached_selections:
        df_selected, _ = select_forecasts_for_window(
            app_state.forecasts,
            cutoff_time_str=cutoff,
            tz_str=MARKET_TIMEZONE
        )
        app_state.cached_selections[cutoff] = df_selected
    return app_state.cached_selections[cutoff]


# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Health check endpoint to verify service liveness."""
    return HealthResponse(status="ok")


@app.get("/api/config", response_model=ConfigResponse, tags=["Configuration"])
def get_config():
    """Returns application configuration: supported cutoffs and date bounds."""
    return ConfigResponse(
        allowed_cutoffs=ALLOWED_CUTOFFS,
        default_cutoff=DEFAULT_CUTOFF,
        date_range={
            "start": ANALYSIS_START.split()[0],
            "end": ANALYSIS_END.split()[0]
        },
        market_timezone=MARKET_TIMEZONE,
    )


@app.get("/api/forecast", response_model=ForecastDayResponse, tags=["Forecasts"])
def get_day_forecast(
    day: str = Query(..., description="Target delivery date in YYYY-MM-DD format (e.g. 2026-01-15)"),
    cutoff: str = Query(DEFAULT_CUTOFF, description="Morning D-1 cutoff time (06:00, 08:00, 09:00)")
):
    """
    Returns the 48 half-hour settlement slots for a target delivery day:
    - Metered wind actual generation (FUELHH)
    - Selected day-ahead wind forecast (WINDFOR) with publishTime and horizon
    - Calculated forecast error (forecast - actual)
    """
    validate_cutoff(cutoff)
    
    try:
        delivery_date = datetime.strptime(day, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")
        
    start_bound = pd.Timestamp(ANALYSIS_START).date()
    end_bound = pd.Timestamp(ANALYSIS_END).date()
    if not (start_bound <= delivery_date <= end_bound):
        raise HTTPException(
            status_code=400,
            detail=f"Requested day {day} is outside the analysis window ({start_bound} to {end_bound})."
        )

    # 1. Select forecasts for this delivery day
    ensure_data_loaded()
    df_fc = app.state.forecasts
    df_hourly = select_latest_forecasts_for_day(df_fc, delivery_date, cutoff_time_str=cutoff)
    df_selected = carry_forward_hourly_to_half_hourly(df_hourly)

    # 2. Extract actuals for this delivery day
    df_act = app.state.actuals
    day_actuals = df_act[df_act["startTime"].dt.date == delivery_date].copy()
    
    # 3. Create canonical 48-slot timeline for the delivery day
    day_start = pd.Timestamp(f"{day} 00:00:00", tz=MARKET_TIMEZONE)
    day_end = pd.Timestamp(f"{day} 23:30:00", tz=MARKET_TIMEZONE)
    grid = pd.date_range(start=day_start, end=day_end, freq="30min", tz=MARKET_TIMEZONE)
    timeline = pd.DataFrame({"startTime": grid})
    
    # Merge actuals and forecasts onto timeline
    merged = pd.merge(timeline, day_actuals[["startTime", "generation"]], on="startTime", how="left")
    merged = pd.merge(merged, df_selected, on="startTime", how="left")

    # Build slot records
    slots: List[ForecastSlot] = []
    unique_publish_times = set()
    cutoff_ts = compute_d_minus_one_cutoff(delivery_date, cutoff, MARKET_TIMEZONE)

    for idx, (_, row) in enumerate(merged.iterrows(), start=1):
        actual_val = float(row["generation"]) if pd.notna(row["generation"]) else None
        fc_val = float(row["forecast"]) if pd.notna(row["forecast"]) else None
        err_val = round(fc_val - actual_val, 2) if (fc_val is not None and actual_val is not None) else None
        
        pub_str = None
        if pd.notna(row.get("publishTime")):
            pub_dt = row["publishTime"]
            pub_str = pub_dt.strftime("%Y-%m-%d %H:%M %Z")
            unique_publish_times.add(pub_dt.strftime("%H:%M"))

        horizon_val = float(row["horizon_hours"]) if pd.notna(row.get("horizon_hours")) else None

        slots.append(
            ForecastSlot(
                slot=idx,
                startTime=row["startTime"].isoformat(),
                timeLabel=row["startTime"].strftime("%H:%M"),
                actual=actual_val,
                forecast=fc_val,
                error=err_val,
                publishTime=pub_str,
                horizon_hours=horizon_val,
            )
        )

    # Format publish time badge with date, e.g. "Forecast published 14 Jan 07:30 (16.5 h before the first slot of the day; slot tooltips show each slot's own lead time)"
    valid_pub_slots = [s for s in slots if s.publishTime and s.horizon_hours is not None]
    if valid_pub_slots:
        first_slot = valid_pub_slots[0]
        pub_dt = pd.to_datetime(first_slot.publishTime).tz_convert(MARKET_TIMEZONE)
        pub_date_str = pub_dt.strftime("%d %b %H:%M")
        pub_summary = (
            f"Forecast published {pub_date_str} "
            f"({first_slot.horizon_hours:g} h before the first slot of the day; slot tooltips show each slot's own lead time)"
        )
    else:
        d_minus_one_str = cutoff_ts.strftime("%d %b")
        pub_summary = f"Cutoff on D-1 ({d_minus_one_str} {cutoff} UK)" 

    return ForecastDayResponse(
        day=day,
        cutoff=cutoff,
        cutoff_datetime=cutoff_ts.isoformat(),
        publish_times_summary=pub_summary,
        slots=slots,
    )


@app.get("/api/metrics", response_model=MetricsSummaryResponse, tags=["Metrics"])
def get_metrics_summary(
    cutoff: str = Query(DEFAULT_CUTOFF, description="Morning D-1 cutoff time (06:00, 08:00, 09:00)")
):
    """
    Returns overall accuracy, directional, and risk metrics across all of January 2026.
    """
    validate_cutoff(cutoff)
    df_selected = get_or_create_monthly_selection(app.state, cutoff)
    df_act = app.state.actuals

    merged = pd.merge(df_act, df_selected, on="startTime", how="inner")
    errors = (merged["forecast"] - merged["generation"]).dropna().to_numpy()
    
    summary = calculate_summary_metrics(errors)
    summary["cutoff_used"] = cutoff
    return MetricsSummaryResponse(**summary)


@app.get("/api/metrics/by-hour", response_model=HourlyMetricsResponse, tags=["Metrics"])
def get_metrics_by_hour(
    cutoff: str = Query(DEFAULT_CUTOFF, description="Morning D-1 cutoff time (06:00, 08:00, 09:00)")
):
    """
    Returns January 2026 metrics grouped by hour of the day (0 to 23).
    """
    validate_cutoff(cutoff)
    df_selected = get_or_create_monthly_selection(app.state, cutoff)
    df_act = app.state.actuals

    merged = pd.merge(df_act, df_selected, on="startTime", how="inner")
    merged["error"] = merged["forecast"] - merged["generation"]
    
    hourly_list = calculate_metrics_by_hour(merged)
    formatted_items = []
    for item in hourly_list:
        h = item["hour"]
        item["hour_label"] = f"{h:02d}:00"
        formatted_items.append(HourlyMetricItem(**item))

    return HourlyMetricsResponse(cutoff_used=cutoff, hours=formatted_items)
