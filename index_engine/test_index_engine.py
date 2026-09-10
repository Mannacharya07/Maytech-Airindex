"""
index_engine/test_index_engine.py
==================================
Pytest test suite for Member 2's Index Engine.

Tests:
1. Base period equals 100.00 exactly.
2. 10% price increase yields 110.00.
3. Jevons geometric mean vs arithmetic mean behavior.
4. Route weights sum to 1.0.
5. Fare identity key generation.
6. Validation filter rejects invalid fares.
7. Reproducibility test (same input -> same index twice).
"""

from __future__ import annotations

import os
import sys
import pytest

_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from index_engine.canonical import FareObservation
from index_engine.jevons import compute_jevons_index
from index_engine.matching import fare_identity, find_matched_pairs
from index_engine.national_index import IndexEngine
from index_engine.price_relative import compute_price_relative
from index_engine.validation import validate_for_index
from index_engine.weights import get_route_weights

SAMPLE_BASE_OBS = {
    "source": "mmt",
    "data_status": "LIVE",
    "origin": "DEL",
    "destination": "BOM",
    "carrier": "INDIGO",
    "travel_date": "2026-09-25",
    "observed_at": "2026-08-11T10:00:00Z",
    "booking_window": "T+15",
    "fare_class": "ECONOMY",
    "base_fare": 4100.0,
    "taxes": 800.0,
    "fees": 100.0,
    "total_fare": 5000.0,
    "availability": 5,
}


def test_base_period_evaluates_to_100():
    """When current period equals base period, index must evaluate to 100.00."""
    obs_base = FareObservation.from_dict(SAMPLE_BASE_OBS)
    obs_curr = FareObservation.from_dict(SAMPLE_BASE_OBS)

    engine = IndexEngine()
    result = engine.calculate_national_index([obs_base], [obs_curr])
    assert result["national_index"] == 100.00


def test_price_increase_yields_expected_index():
    """A 10% uniform price increase must yield index = 110.00."""
    obs_base = FareObservation.from_dict(SAMPLE_BASE_OBS)

    curr_dict = SAMPLE_BASE_OBS.copy()
    curr_dict["total_fare"] = 5500.0  # +10%
    curr_dict["base_fare"] = 4510.0
    curr_dict["taxes"] = 880.0
    curr_dict["fees"] = 110.0
    obs_curr = FareObservation.from_dict(curr_dict)

    relative = compute_price_relative(obs_base, obs_curr)
    assert relative == 1.10

    jevons = compute_jevons_index([relative])
    assert jevons == 110.00


def test_jevons_geometric_mean_property():
    """Geometric mean of [2.0, 0.5] relative changes is sqrt(1.0) = 1.00 -> index = 100.00."""
    relatives = [2.0, 0.5]
    idx = compute_jevons_index(relatives)
    assert idx == 100.00


def test_route_weights_sum_to_one():
    """Route weights must sum to 1.00 exactly."""
    weights = get_route_weights()
    assert abs(sum(weights.values()) - 1.0) < 0.001


def test_fare_identity_string():
    """Fare identity string must format as ORIGIN-DEST|CARRIER|WINDOW|CLASS."""
    obs = FareObservation.from_dict(SAMPLE_BASE_OBS)
    key = fare_identity(obs)
    assert key == "DEL-BOM|INDIGO|T+15|ECONOMY"


def test_validation_rejects_negative_fare():
    """Validation must reject observations with non-positive fare."""
    bad_dict = SAMPLE_BASE_OBS.copy()
    bad_dict["total_fare"] = -100.0
    obs = FareObservation.from_dict(bad_dict)
    is_valid, reason = validate_for_index(obs)
    assert not is_valid
    assert "Total fare must be > 0" in reason


def test_reproducibility():
    """Engine must produce identical results when run twice on same input."""
    obs_base = FareObservation.from_dict(SAMPLE_BASE_OBS)
    obs_curr = FareObservation.from_dict(SAMPLE_BASE_OBS)

    engine = IndexEngine()
    r1 = engine.calculate_national_index([obs_base], [obs_curr])
    r2 = engine.calculate_national_index([obs_base], [obs_curr])

    assert r1["national_index"] == r2["national_index"]
