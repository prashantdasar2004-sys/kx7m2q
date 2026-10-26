"""
fetch_data.py

Fetches historical wind generation actuals (FUELHH) and forecasts (WINDFOR)
from the public Elexon BMRS API v1 for the period 2025-12-25 to 2026-02-01.

Saves the cleaned results to local Parquet files:
- backend/data/fuelhh_actuals.parquet
- backend/data/windfor_forecasts.parquet
"""

import json
import logging
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# Configure logging so progress is clearly visible during ingestion
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fetch_data")

# Base URL for public Elexon Insights Solution (BMRS) API
BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

# Target date range: covers December 2025 baseline, entire January 2026, and 2026-02-01
START_DATE_STR = "2025-12-25T00:00:00Z"
# We fetch through 2026-02-02T01:00:00Z to ensure we capture the final settlement period of Feb 01
END_DATE_STR = "2026-02-02T01:00:00Z"

# Directory where parquet files are saved
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def generate_date_chunks(start_iso: str, end_iso: str, chunk_days: int = 5):
    """
    Splits a large date range into smaller chunks of `chunk_days`.
    
    WHY:
    The Elexon API has response size limits and gateway timeouts when
    requesting long time periods in a single call. Splitting into 5-day
    windows keeps each request fast and reliable.
    """
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    current_start = datetime.strptime(start_iso, fmt)
    final_end = datetime.strptime(end_iso, fmt)

    while current_start < final_end:
        current_end = min(current_start + timedelta(days=chunk_days), final_end)
        yield current_start.strftime(fmt), current_end.strftime(fmt)
        current_start = current_end


def fetch_stream_data(endpoint: str, query_params: dict) -> list:
    """
    Sends an HTTP GET request to an Elexon dataset stream endpoint.
    
    WHY:
    Using Python's standard `urllib` avoids unnecessary external dependencies
    for network requests, and adding standard headers ensures the API returns
    clean JSON.
    """
    encoded_params = urllib.parse.urlencode(query_params)
    url = f"{BASE_URL}/{endpoint}?{encoded_params}"
    
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "wind-forecast-utility/1.0"}
    )
    
    # 30-second timeout prevents indefinite hanging if the network slows down
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"API request failed with HTTP {response.status}: {url}")
        raw_bytes = response.read()
        return json.loads(raw_bytes.decode("utf-8"))


def fetch_fuelhh_actuals(start_iso: str, end_iso: str) -> pd.DataFrame:
    """
    Fetches actual outturn half-hourly generation for WIND from FUELHH/stream.
    
    WHY:
    Elexon's FUELHH endpoint provides settlement-period outturn per fuel type.
    We pass `fuelType=WIND` directly in the query parameters so the server
    filters out unnecessary fuel types (gas, nuclear, coal) before sending.
    """
    all_records = []
    logger.info("Fetching FUELHH (WIND actuals)...")
    
    for chunk_start, chunk_end in generate_date_chunks(start_iso, end_iso, chunk_days=5):
        logger.info(f"  FUELHH chunk: {chunk_start} -> {chunk_end}")
        params = {
            "publishDateTimeFrom": chunk_start,
            "publishDateTimeTo": chunk_end,
            "fuelType": "WIND"
        }
        records = fetch_stream_data("datasets/FUELHH/stream", params)
        all_records.extend(records)
        # Polite 0.2s pause between requests to respect public API rate limits
        time.sleep(0.2)
        
    if not all_records:
        raise ValueError("No FUELHH records retrieved from Elexon API.")
        
    df = pd.DataFrame(all_records)
    
    # Filter only requested columns: startTime, publishTime, generation, fuelType
    desired_cols = ["startTime", "publishTime", "generation", "fuelType"]
    df = df[desired_cols].copy()
    
    # Convert timestamps to UTC datetimes
    # WHY: Electricity market settlements must have explicit UTC timezone awareness
    # to avoid ambiguities across daylight saving shifts or local server timezones.
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    
    # Ensure generation is numeric (MW)
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    
    # Sort and remove duplicates by startTime
    # WHY: A half-hour settlement period has a unique actual generation value.
    df = df.drop_duplicates(subset=["startTime"]).sort_values("startTime").reset_index(drop=True)
    return df


def fetch_windfor_forecasts(start_iso: str, end_iso: str) -> pd.DataFrame:
    """
    Fetches wind generation forecasts from WINDFOR/stream.
    
    WHY:
    WINDFOR delivers Elexon WINDFOR day-ahead forecasts.
    Each forecast record includes:
    - `startTime`: the target half-hour period being predicted.
    - `publishTime`: the time when Elexon calculated and published the forecast.
    - `generation`: predicted wind generation in MW.
    """
    all_records = []
    logger.info("Fetching WINDFOR (Wind forecasts)...")
    
    for chunk_start, chunk_end in generate_date_chunks(start_iso, end_iso, chunk_days=5):
        logger.info(f"  WINDFOR chunk: {chunk_start} -> {chunk_end}")
        params = {
            "publishDateTimeFrom": chunk_start,
            "publishDateTimeTo": chunk_end
        }
        records = fetch_stream_data("datasets/WINDFOR/stream", params)
        all_records.extend(records)
        time.sleep(0.2)
        
    if not all_records:
        raise ValueError("No WINDFOR records retrieved from Elexon API.")
        
    df = pd.DataFrame(all_records)
    
    # Filter only requested columns: startTime, publishTime, generation
    desired_cols = ["startTime", "publishTime", "generation"]
    df = df[desired_cols].copy()
    
    # Convert timestamps to UTC datetimes
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    
    # Ensure generation is numeric (MW)
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    
    # Deduplicate exact duplicate updates and sort by publishTime then startTime
    df = df.drop_duplicates().sort_values(["publishTime", "startTime"]).reset_index(drop=True)
    return df


def save_and_summarize(df: pd.DataFrame, output_path: Path, dataset_name: str) -> None:
    """
    Saves a DataFrame to Parquet and prints summary inspection statistics.
    
    WHY:
    Parquet provides column compression, preserves datetime types accurately,
    and enables fast cold-starts for the web application without re-parsing CSVs.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    
    logger.info(f"=== {dataset_name} Summary ===")
    logger.info(f"Saved to: {output_path}")
    logger.info(f"Total row count: {len(df)}")
    logger.info(f"Min startTime: {df['startTime'].min()}")
    logger.info(f"Max startTime: {df['startTime'].max()}")
    print(f"\n--- First 5 rows of {dataset_name} ({output_path.name}) ---")
    print(df.head(5).to_string())
    print("\n" + "=" * 50 + "\n")


def main():
    """
    Main orchestration function to fetch and save both datasets.
    """
    logger.info("Starting Elexon offline data ingestion...")
    
    # 1. Fetch FUELHH Actuals (WIND only)
    fuelhh_df = fetch_fuelhh_actuals(START_DATE_STR, END_DATE_STR)
    fuelhh_path = DATA_DIR / "fuelhh_actuals.parquet"
    save_and_summarize(fuelhh_df, fuelhh_path, "FUELHH Actuals (WIND)")
    
    # 2. Fetch WINDFOR Forecasts
    windfor_df = fetch_windfor_forecasts(START_DATE_STR, END_DATE_STR)
    windfor_path = DATA_DIR / "windfor_forecasts.parquet"
    save_and_summarize(windfor_df, windfor_path, "WINDFOR Forecasts")
    
    logger.info("Data ingestion completed successfully.")


if __name__ == "__main__":
    main()
