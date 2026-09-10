"""
analytics/test_analytics.py
============================
Pytest test suite for Member 4's analytics package.
"""

from __future__ import annotations

import os
import sys
import pytest

_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from analytics.anomaly import detect_anomalies
from analytics.contributions import explain_index_change
from analytics.lead_time import compute_lead_time_curve
from analytics.validation import validate_against_reference

SAMPLE_OBSERVATIONS = [
    {"origin": "DEL", "destination": "BOM", "booking_window": "T+45", "total_fare": 3900.0, "base_fare": 3198.0, "taxes": 624.0, "fees": 78.0, "observed_at": "2026-09-10T10:00:00Z"},
    {"origin": "DEL", "destination": "BOM", "booking_window": "T+30", "total_fare": 4200.0, "base_fare": 3444.0, "taxes": 672.0, "fees": 84.0, "observed_at": "2026-09-10T10:00:00Z"},
    {"origin": "DEL", "destination": "BOM", "booking_window": "T+15", "total_fare": 4900.0, "base_fare": 4018.0, "taxes": 784.0, "fees": 98.0, "observed_at": "2026-09-10T10:00:00Z"},
    {"origin": "DEL", "destination": "BOM", "booking_window": "T+7",  "total_fare": 5700.0, "base_fare": 4674.0, "taxes": 912.0, "fees": 114.0, "observed_at": "2026-09-10T10:00:00Z"},
    {"origin": "DEL", "destination": "BOM", "booking_window": "T+1",  "total_fare": 7300.0, "base_fare": 5986.0, "taxes": 1168.0, "fees": 146.0, "observed_at": "2026-09-10T10:00:00Z"},
]


def test_lead_time_curve():
    """Lead-time curve must order windows from T+45 to T+1."""
    res = compute_lead_time_curve(SAMPLE_OBSERVATIONS, "DEL-BOM")
    assert res["route"] == "DEL-BOM"
    curve = res["curve"]
    assert len(curve) == 5
    assert curve[0]["booking_window"] == "T+45"
    assert curve[-1]["booking_window"] == "T+1"
    assert curve[-1]["avg_total_fare"] > curve[0]["avg_total_fare"]  # Surge price property


def test_detect_anomalies():
    """Anomaly detector must flag an extreme price spike."""
    obs_list = [
        {"origin": "DEL", "destination": "BOM", "booking_window": "T+1", "total_fare": 5000.0, "observed_at": "2026-09-10T10:00:00Z"},
        {"origin": "DEL", "destination": "BOM", "booking_window": "T+1", "total_fare": 5100.0, "observed_at": "2026-09-10T10:00:00Z"},
        {"origin": "DEL", "destination": "BOM", "booking_window": "T+1", "total_fare": 5200.0, "observed_at": "2026-09-10T10:00:00Z"},
        {"origin": "DEL", "destination": "BOM", "booking_window": "T+1", "total_fare": 14500.0, "observed_at": "2026-09-10T10:00:00Z"},  # Spike!
    ]
    anomalies = detect_anomalies(obs_list)
    assert len(anomalies) >= 1
    assert anomalies[0]["observed_fare"] == 14500.0
    assert anomalies[0]["severity"] in ("HIGH", "MEDIUM")


def test_explain_index_change():
    """Index contribution decomposer must compute route contributions."""
    prev = {"national_index": 100.0, "route_indices": {"DEL-BOM": 100.0, "DEL-BLR": 100.0}, "route_weights": {"DEL-BOM": 0.28, "DEL-BLR": 0.22}}
    curr = {"national_index": 104.2, "route_indices": {"DEL-BOM": 110.0, "DEL-BLR": 105.0}, "route_weights": {"DEL-BOM": 0.28, "DEL-BLR": 0.22}}

    explanation = explain_index_change(prev, curr)
    assert explanation["total_index_change"] == 4.2
    assert len(explanation["top_routes"]) >= 2
    assert explanation["top_routes"][0]["route"] == "DEL-BOM"
    assert explanation["top_routes"][0]["contribution"] == 2.8  # 0.28 * +10.0 = +2.8


def test_validate_against_reference():
    """Validation metrics must return accurate MAE, RMSE, and correlation r=1.0 for identical series."""
    s1 = [100.0, 102.0, 105.0, 108.0]
    s2 = [100.0, 102.0, 105.0, 108.0]

    metrics = validate_against_reference(s1, s2)
    assert metrics["mae"] == 0.0
    assert metrics["rmse"] == 0.0
    assert metrics["mape"] == 0.0
    assert metrics["pearson_r"] == 1.0
