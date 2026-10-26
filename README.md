# UK Wind Generation Forecast vs Actuals (January 2026)

[![Live App Demo](https://img.shields.io/badge/Demo-Vercel%20Deployment-blue?style=for-the-badge&logo=vercel)](https://kx7m2q.vercel.app)
> **Live Application URL**: [https://kx7m2q.vercel.app](https://kx7m2q.vercel.app)

A decision-support web application for a UK energy utility evaluating Great Britain (GB) day-ahead wind generation forecasts against actual metered outturn for **January 2026**.

The application evaluates systematic forecast bias, quantifies safety reserve buffers required to protect against sudden wind drops, and allows trading analysts to benchmark different pre-auction morning decision cutoffs without lookahead bias.

---

## Purpose

Wind power forms a critical and highly volatile component of the Great Britain electricity system. In power trading and balancing operations, utilities and traders must commit generation schedules or hedge positions in the day-ahead hourly power auctions on the day prior to delivery ($D-1$): the EPEX day-ahead hourly auction closes at 09:20 UK time and the N2EX day-ahead hourly auction closes at 09:50 UK time.

This tool provides:
1. **Historical Outturn Benchmarking**: Direct 30-minute settlement period comparison between metered wind outturn (`FUELHH`) and the day-ahead forecast the buyer would have seen (`WINDFOR`).
2. **Systematic Bias & Risk Quantification**: Calculation of Mean Absolute Error (MAE), Mean Bias, Over-Forecast percentage, P50/P90/P95 error percentiles, and the 90% Safe Reserve MW buffer.
3. **Diurnal Pattern Analysis**: Error breakdown across all 24 hours of the day to identify recurring morning or evening forecast discrepancies.
4. **Interactive Cutoff Auditing**: Ability to test different pre-auction morning cutoffs (06:00, 08:00, 09:00 UK time) while strictly enforcing causal timeline integrity.

---

## Folder & File Descriptions

```text
wind-forecast-utility/
|-- backend/
|   |-- api/
|   |   `-- index.py              # Serverless ASGI entrypoint for Vercel deployment
|   |-- app/
|   |   |-- config.py             # Allowed cutoffs, analysis bounds, and market timezone
|   |   |-- loader.py             # Parquet dataset ingestion and timezone localization
|   |   |-- selection.py          # D-1 cutoff forecast selection & resolution carry-forward
|   |   |-- metrics.py            # MAE, RMSE, bias, quantiles, and 90% safe buffer formulas
|   |   `-- main.py               # FastAPI REST endpoints, CORS rules, and lazy-load guard
|   |-- data/                     # Bundled Parquet datasets (tracked in git for offline runtime)
|   |   |-- fuelhh_actuals.parquet      # Metered 30-min wind generation (41 KB)
|   |   `-- windfor_forecasts.parquet   # Multi-run day-ahead wind forecasts (103 KB)
|   |-- scripts/
|   |   `-- fetch_data.py         # Elexon BMRS API ingestion script (used for offline data prep)
|   |-- tests/                    # Pytest automated test suite
|   |   |-- test_selection.py     # Unit tests for cutoff filtering and audit trail
|   |   |-- test_metrics.py       # Hand-calculated mathematical assertions for all metrics
|   |   `-- test_api.py           # Integration tests for REST endpoints and Vercel entrypoint
|   |-- Dockerfile                # Production container for FastAPI (Python 3.11-slim)
|   |-- requirements.txt          # Python dependencies (fastapi, pandas, pyarrow, numpy, etc.)
|   `-- vercel.json               # Serverless Python function configuration and routing
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |   |-- Header.jsx             # Top branding banner with data source badges
|   |   |   |-- CutoffControls.jsx     # Morning cutoff buttons (06:00, 08:00, 09:00)
|   |   |   |-- MetricsCards.jsx       # 7 core metric cards with tooltips and interpretation note
|   |   |   |-- WindChart.jsx          # 48-slot line chart with fixed 3,000 MW ticks and legend
|   |   |   `-- HourlyErrorChart.jsx   # 24-hour diurnal error & bias bar chart
|   |   |-- services/
|   |   |   `-- api.js                 # API client (reads VITE_API_URL or local Vite proxy)
|   |   |-- App.jsx                    # Root state orchestration (date picker, cutoff, loading)
|   |   |-- index.css                  # Modern dark-mode energy utility design system
|   |   `-- main.jsx                   # React DOM entrypoint
|   |-- Dockerfile                # Multi-stage production container (Node build + Nginx serve)
|   |-- nginx.conf                # Nginx reverse proxy routing /api to backend and serving SPA
|   |-- package.json              # Frontend dependencies (React 18, Recharts, Lucide-React)
|   |-- vite.config.js            # Vite configuration with local dev proxy
|   `-- vercel.json               # SPA client-side rewrite configuration
|-- docker-compose.yml            # Multi-container orchestration (frontend:3000, backend:8000)
|-- .gitignore                    # Git rules (explicitly preserves backend/data/*.parquet)
`-- README.md                     # Documentation and execution guide
```

---

## Analysis Assumptions

1. **Default D-1 Cutoff (09:00 UK Time)**:
   - 09:00 on D-1 is shortly before the EPEX (09:20) and N2EX (09:50) day-ahead gate closures, leaving time to prepare bids.
   - Supported pre-auction cutoffs are **06:00, 08:00, and 09:00 (default) UK time (`Europe/London`)**. The 10:00 cutoff is excluded because it occurs after gate closures and would introduce lookahead bias.
   - All 48 settlement slots of delivery day $D$ share the exact same cutoff. Forecasts published after the cutoff are discarded to guarantee zero lookahead bias.
2. **Resolution Alignment (Hourly Carry-Forward)**:
   - Elexon `WINDFOR` forecasts are issued at 1-hour intervals, whereas GB settlement periods (`FUELHH`) operate on 30-minute intervals (48 slots per day).
   - *Assumption*: We assume the hourly forecast represents the expected generation level across the full hour and carry it forward across the subsequent half-hour (e.g. the 14:00 forecast applies to 14:00-14:30 and 14:30-15:00).
3. **Analysis Window**:
   - Strictly spans **2026-01-01 00:00:00 to 2026-01-31 23:30:00 UK Time (`Europe/London`)**.
   - Covers exactly 31 delivery days $\times$ 48 settlement periods = **1,488 half-hour slots**. Under the 09:00 cutoff, 100% of slots (0 missing) have valid forecasts.

---

## How to Start

### Option A: With Docker (configuration provided; not run on the author's machine)

Make sure Docker Desktop is running, then run:

```bash
docker compose up --build
```

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Backend**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

*Note: The frontend container uses an internal Nginx reverse proxy that routes `/api` directly to the backend container, so no manual URL configuration is required.*

---

### Option B: Without Docker (Local Development)

#### 1. Backend Setup (FastAPI)
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
python -m uvicorn app.main:app --port 8000
```
Backend will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

#### 2. Frontend Setup (React + Vite)
In a new terminal:
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
Frontend will be available at [http://localhost:5173](http://localhost:5173). The Vite development server automatically proxies `/api` requests to `http://127.0.0.1:8000`.

---

## Refreshing the Data

To refresh the local Parquet datasets directly from the public Elexon BMRS API:

```bash
python backend/scripts/fetch_data.py
```

* **Date Range Fetched**: `2025-12-25T00:00:00Z` to `2026-02-01T01:00:00Z` (captures December 2025 lookback required for D-1 cutoff evaluation on January 1, through all settlement periods of January 2026).
* **Saved Outputs**: Updates `backend/data/fuelhh_actuals.parquet` and `backend/data/windfor_forecasts.parquet`.

---

## Automated Tests

The backend test suite includes 16 unit and integration tests verifying the mathematical formulas, timeline cutoff logic, horizon calculations, REST endpoints, and Vercel serverless entrypoint.

Run the test suite from the project root:

```bash
python -m pytest backend/tests -v
```

### Test Coverage Highlights:
- `test_selection.py`: Asserts that forecasts published after the cutoff are discarded, verifies that hourly forecasts are carried forward to `:30` half-hours, and tests the audit trail.
- `test_metrics.py`: Compares calculated MAE, RMSE, bias, quantiles, and safe buffers against hand-calculated expected values.
- `test_api.py`: Tests `/health`, `/api/config`, `/api/forecast`, `/api/metrics`, `/api/metrics/by-hour`, 400 validations for unapproved cutoffs/out-of-window dates, and the `api.index` Vercel entrypoint.

---

## Findings & Limitations

### January 2026 Findings
- **High Over-Forecasting Frequency**: Under the default `09:00` $D-1$ cutoff, day-ahead forecasts over-predicted actual wind generation in **84.9% of settlement slots** (1,263 out of 1,488 slots).
- **Systematic Positive Bias**: The average forecast error was **+1,851.90 MW** (MAE: 2,145.17 MW; RMSE: 2,615.81 MW). Because bias is positive, wind buyers regularly faced supply shortfalls relative to day-ahead expectations.
- **Risk Buffer Requirement**: To cover unexpected wind generation deficits in 90% of settlement periods, a utility would have needed to procure a **4,274.90 MW safe reserve buffer**.
- **Safe Buffer Equivalence**: The "90% safe buffer" (one-sided P90 of max(forecast - actual, 0)) equals the P90 absolute error (4,274.90 MW) here because the largest absolute errors are all over-forecasts.
- **Level Offset vs. Timing Shift**: Mean actual wind was 11,580.74 MW and mean forecast 13,432.64 MW, so the bias is a level offset (about 16% of mean actual), not a timing shift.

### Limitations
1. **Root Cause Undetermined**: The underlying cause of this positive bias **cannot be determined from these two datasets alone** (`FUELHH` actuals and `WINDFOR` forecasts). In the GB system, a shortfall in metered wind outturn relative to day-ahead forecasts can be driven by several distinct mechanisms:
   - **Transmission Curtailment**: Wind farms in Scotland and Northern England are frequently instructed by the national system operator (via the Balancing Mechanism) to reduce output to prevent transmission grid overloads across the B6 boundary.
   - **Unplanned Plant Outages**: Mechanical outages or connection constraints that reduced physical capacity after the weather forecast was created.
   - **Meteorological Model Over-Estimation**: Systematic over-prediction of wind speeds by numerical weather prediction (NWP) models under specific atmospheric pressure patterns.
   Isolating these causes requires Balancing Mechanism unit-level bid-offer acceptance (BOA) data and physical notification (PN) data, which are outside the scope of `FUELHH` and `WINDFOR`.
2. **Single Month Scope**: These results represent **one winter month (January 2026)**. Wind generation patterns, storm frequencies, and transmission constraints vary substantially across seasons; conclusions drawn from this period cannot be extrapolated to full-year utility risk without multi-year analysis.

---

## AI Usage

AI tools (Google Antigravity, Claude) assisted with code and explanations. I defined the approach, reviewed and tested the code, and validated the results.
