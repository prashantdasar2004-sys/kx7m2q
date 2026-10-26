"""
config.py

Centralized configuration for the Wind Generation Forecast utility.
Defines supported morning D-1 cutoffs, analysis date bounds, and data file paths.
"""

from pathlib import Path

# Base paths
APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
DATA_DIR = BACKEND_DIR / "data"

# Parquet data file paths
ACTUALS_PATH = DATA_DIR / "fuelhh_actuals.parquet"
FORECASTS_PATH = DATA_DIR / "windfor_forecasts.parquet"

# Regional market timezone: Great Britain electricity market operates on Europe/London time
MARKET_TIMEZONE = "Europe/London"

# Supported morning D-1 cutoff times (UK local time)
# WHY: In GB electricity trading, the EPEX day-ahead hourly auction closes at 09:20 UK time
# and the N2EX day-ahead hourly auction closes at 09:50 UK time. 09:00 on D-1 is shortly before
# the EPEX (09:20) and N2EX (09:50) day-ahead gate closures, leaving time to prepare bids.
# 10:00 is excluded because it occurs after gate closures and would introduce lookahead bias.
ALLOWED_CUTOFFS = ["06:00", "08:00", "09:00"]
DEFAULT_CUTOFF = "09:00"

# Target analysis window: January 2026
ANALYSIS_START = "2026-01-02 00:00:00"
ANALYSIS_END = "2026-02-01 23:30:00"
