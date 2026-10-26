"""
test_api.py

Integration tests for the FastAPI REST endpoints using TestClient.
Verifies response schemas, HTTP status codes, parameter validations, and calculations.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient with the lifespan event triggered to load Parquet files."""
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    """Verifies that GET /health returns 200 and status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_config_endpoint(client):
    """Verifies that GET /api/config returns allowed morning cutoffs and January 2026 dates."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "allowed_cutoffs" in data
    assert data["allowed_cutoffs"] == ["06:00", "08:00", "09:00"]
    assert "10:00" not in data["allowed_cutoffs"]
    assert data["default_cutoff"] == "09:00"
    assert data["date_range"]["start"] == "2026-01-01"
    assert data["date_range"]["end"] == "2026-01-31"


def test_forecast_day_endpoint_success(client):
    """
    Verifies that GET /api/forecast returns exactly 48 slots for a valid January day,
    with actuals, selected forecasts, horizons, and publish times populated.
    """
    response = client.get("/api/forecast?day=2026-01-15&cutoff=09:00")
    assert response.status_code == 200
    data = response.json()
    
    assert data["day"] == "2026-01-15"
    assert data["cutoff"] == "09:00"
    assert "before the first slot of the day; slot tooltips show each slot's own lead time" in data["publish_times_summary"]
    assert len(data["slots"]) == 48
    
    # Check first slot
    slot1 = data["slots"][0]
    assert slot1["slot"] == 1
    assert slot1["timeLabel"] == "00:00"
    assert slot1["actual"] is not None
    assert slot1["forecast"] is not None
    assert slot1["publishTime"] is not None
    assert slot1["horizon_hours"] is not None
    assert slot1["error"] == round(slot1["forecast"] - slot1["actual"], 2)


def test_forecast_day_invalid_cutoff(client):
    """Verifies that requesting an unapproved cutoff (e.g. 10:00 after EPEX gate closure) returns 400."""
    response = client.get("/api/forecast?day=2026-01-15&cutoff=10:00")
    assert response.status_code == 400
    assert "Invalid cutoff" in response.json()["detail"]


def test_forecast_day_outside_window(client):
    """Verifies that requesting a date outside January 2026 returns 400."""
    response = client.get("/api/forecast?day=2026-02-15&cutoff=09:00")
    assert response.status_code == 400
    assert "outside the January 2026 analysis window" in response.json()["detail"]


def test_metrics_summary_endpoint(client):
    """Verifies that GET /api/metrics returns all required statistical and risk metrics."""
    response = client.get("/api/metrics?cutoff=09:00")
    assert response.status_code == 200
    data = response.json()
    
    assert data["count"] == 1488
    assert data["cutoff_used"] == "09:00"
    assert data["mae"] > 0
    assert data["rmse"] > 0
    assert data["bias"] > 0
    assert data["p50"] > 0
    assert data["p90"] > 0
    assert data["p95"] > 0
    assert data["buffer_90"] > 0
    assert 0 <= data["over_forecast_pct"] <= 100


def test_metrics_by_hour_endpoint(client):
    """Verifies that GET /api/metrics/by-hour returns 24 hourly buckets (0 to 23)."""
    response = client.get("/api/metrics/by-hour?cutoff=09:00")
    assert response.status_code == 200
    data = response.json()
    
    assert data["cutoff_used"] == "09:00"
    assert len(data["hours"]) == 24
    
    for i, item in enumerate(data["hours"]):
        assert item["hour"] == i
        assert item["count"] > 0
        assert "mae" in item
        assert "bias" in item
        assert "over_forecast_pct" in item


def test_vercel_serverless_entrypoint():
    """Verifies that api.index.app exports the ASGI app and can serve requests in serverless environments."""
    from api.index import app as vercel_app
    test_client = TestClient(vercel_app)
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
