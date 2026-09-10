"""
api/test_api.py
===============
Pytest test suite for Member 3's FastAPI REST server.
Tests all endpoints using FastAPI TestClient.
"""

from __future__ import annotations

import os
import sys
import pytest
from fastapi.testclient import TestClient

_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from api.database import init_sqlite_db
from api.services import ingest_replay_csv_to_db, compute_and_sync_index_values
from api.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Ensure database schema and seed data are initialized for testing."""
    init_sqlite_db()
    ingest_replay_csv_to_db()
    compute_and_sync_index_values()


def test_root_endpoint():
    """Root endpoint redirects to dashboard or returns 200/307."""
    with TestClient(app) as client:
        res = client.get("/", follow_redirects=True)
        assert res.status_code == 200
        assert "AIRINDEX" in res.text


def test_get_routes_endpoint():
    """GET /api/routes returns tracked DGCA routes with weights summing to 1.0."""
    with TestClient(app) as client:
        res = client.get("/api/routes")
        assert res.status_code == 200
        routes = res.json()
        assert len(routes) == 6
        total_weight = sum(r["weight"] for r in routes)
        assert abs(total_weight - 1.0) < 0.001


def test_get_fares_endpoint():
    """GET /api/fares returns observations with filter support."""
    with TestClient(app) as client:
        res = client.get("/api/fares?route=DEL-BOM&limit=10")
        assert res.status_code == 200
        fares = res.json()
        assert isinstance(fares, list)
        if fares:
            assert fares[0]["origin"] == "DEL"
            assert fares[0]["destination"] == "BOM"


def test_get_index_current_endpoint():
    """GET /api/index/current returns latest national and route indices."""
    with TestClient(app) as client:
        res = client.get("/api/index/current")
        assert res.status_code == 200
        data = res.json()
        assert "national_index" in data
        assert "route_indices" in data
        assert "DEL-BOM" in data["route_indices"]


def test_get_index_history_endpoint():
    """GET /api/index/history returns 30-day time-series history."""
    with TestClient(app) as client:
        res = client.get("/api/index/history?route=NATIONAL")
        assert res.status_code == 200
        data = res.json()
        assert "history" in data
        assert len(data["history"]) > 0


def test_get_lead_time_endpoint():
    """GET /api/lead-time returns booking window fare surge curve."""
    with TestClient(app) as client:
        res = client.get("/api/lead-time?route=DEL-BOM")
        assert res.status_code == 200
        data = res.json()
        assert data["route"] == "DEL-BOM"
        assert "lead_time_curve" in data
        assert len(data["lead_time_curve"]) > 0


def test_404_handling():
    """Non-existent route detail returns clean 404 error."""
    with TestClient(app) as client:
        res = client.get("/api/routes/XYZ-ABC")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"]
