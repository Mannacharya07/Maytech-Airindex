"""
collector/test_contract.py
===========================
Pytest suite validating the frozen AIRINDEX observation contract.

Tests are split into two groups:

A) Unit tests – use a hand-crafted valid observation dict.
   These run instantly with zero network I/O and without a populated CSV.

B) CSV integration tests – load collector/data/replay_data.csv.
   Automatically skipped if the CSV is empty (run harvest_real_data.py first).

Run:
    pytest collector/test_contract.py -v
    pytest collector/test_contract.py -v -k "unit"   # unit tests only
    pytest collector/test_contract.py -v -k "csv"    # CSV tests only
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# Import from the package (works when run from maytech/ root)
# ---------------------------------------------------------------------------
import sys

_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from collector.base_connector import (
    BOOKING_WINDOWS,
    ALLOWED_CARRIERS,
    REQUIRED_FIELDS,
    VALID_SOURCES,
    VALID_DATA_STATUSES,
    validate_observation,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "replay_data.csv")

from collector.api_connector import APIConnector

VALID_OBS_TEMPLATE: dict = {
    "source": "mmt",
    "data_status": "LIVE",
    "origin": "DEL",
    "destination": "BOM",
    "carrier": "INDIGO",
    "travel_date": "2026-09-25",
    "observed_at": datetime.now(timezone.utc).isoformat(),
    "booking_window": "T+15",
    "fare_class": "ECONOMY",
    "base_fare": 4100.0,
    "taxes": 800.0,
    "fees": 100.0,
    "total_fare": 5000.0,
    "availability": 5,
}

def test_api_connector_validation():
    connector = APIConnector()
    # Test valid contract initialization
    assert connector is not None



def _make_obs(**overrides) -> dict:
    """Return a copy of the template with any overrides applied."""
    obs = VALID_OBS_TEMPLATE.copy()
    obs.update(overrides)
    return obs


@pytest.fixture(scope="session")
def csv_rows() -> list[dict]:
    """Load all rows from the CSV. Skip fixture if CSV is empty."""
    if not os.path.exists(CSV_PATH):
        pytest.skip("replay_data.csv does not exist – run harvest_real_data.py first")

    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            # Coerce numeric fields
            for f in ("base_fare", "taxes", "fees", "total_fare"):
                try:
                    raw[f] = float(raw[f])
                except (ValueError, KeyError):
                    pass
            try:
                raw["availability"] = int(raw["availability"])
            except (ValueError, KeyError):
                pass
            rows.append(raw)

    if not rows:
        pytest.skip("replay_data.csv is empty – run harvest_real_data.py first")

    return rows


# ===========================================================================
# A) UNIT TESTS  (no CSV needed)
# ===========================================================================

class TestUnitValidateObservation:
    """validate_observation() unit tests with hand-crafted dicts."""

    def test_unit_valid_observation_passes(self):
        """A perfectly formed observation dict should pass without error."""
        obs = validate_observation(_make_obs())
        assert obs is not None

    def test_unit_missing_required_field_raises(self):
        """Dropping any single required field should raise ValueError."""
        for field in REQUIRED_FIELDS:
            bad = _make_obs()
            del bad[field]
            with pytest.raises(ValueError, match=field):
                validate_observation(bad)

    def test_unit_fare_math_exact(self):
        """base_fare + taxes + fees must exactly equal total_fare."""
        # 4100 + 800 + 100 = 5000 ✓
        obs = validate_observation(_make_obs())
        assert obs["total_fare"] == obs["base_fare"] + obs["taxes"] + obs["fees"]

    def test_unit_fare_math_breach_raises(self):
        """total_fare ≠ components should raise ValueError."""
        bad = _make_obs(total_fare=9999.0)  # components still sum to 5000
        with pytest.raises(ValueError, match="Fare math breach"):
            validate_observation(bad)

    def test_unit_invalid_booking_window_raises(self):
        """booking_window not in the 5 legal values should raise."""
        with pytest.raises(ValueError, match="booking_window"):
            validate_observation(_make_obs(booking_window="T+3"))

    def test_unit_invalid_source_raises(self):
        """source outside VALID_SOURCES should raise."""
        with pytest.raises(ValueError, match="source"):
            validate_observation(_make_obs(source="skyscanner"))

    def test_unit_invalid_carrier_raises(self):
        """Carrier not in ALLOWED_CARRIERS should raise."""
        with pytest.raises(ValueError, match="carrier"):
            validate_observation(_make_obs(carrier="SpiceJet"))

    def test_unit_negative_availability_raises(self):
        """availability < 0 should raise."""
        with pytest.raises(ValueError, match="availability"):
            validate_observation(_make_obs(availability=-1))

    def test_unit_invalid_iata_code_raises(self):
        """Non-3-letter IATA code should raise."""
        with pytest.raises(ValueError, match="origin"):
            validate_observation(_make_obs(origin="DELHI"))

    def test_unit_null_field_raises(self):
        """A null (None) required field should raise."""
        with pytest.raises(ValueError, match="carrier"):
            validate_observation(_make_obs(carrier=None))

    def test_unit_air_india_carrier_accepted(self):
        """Air India must be in the whitelist."""
        obs = validate_observation(
            _make_obs(
                carrier="AIR INDIA",
                base_fare=5740.0,
                taxes=1120.0,
                fees=140.0,
                total_fare=7000.0,
            )
        )
        assert obs["carrier"] == "AIR INDIA"

    def test_unit_goibibo_source_accepted(self):
        """source='goibibo' must be valid."""
        obs = validate_observation(_make_obs(source="goibibo", data_status="LIVE"))
        assert obs["source"] == "goibibo"

    def test_unit_replay_source_accepted(self):
        """source='replay' with data_status='REPLAY' must be valid."""
        obs = validate_observation(
            _make_obs(source="replay", data_status="REPLAY")
        )
        assert obs["data_status"] == "REPLAY"


# ===========================================================================
# B) CSV INTEGRATION TESTS  (require a populated replay_data.csv)
# ===========================================================================

class TestCSVContract:
    """Validate every row in replay_data.csv against the frozen contract."""

    def test_csv_required_fields_present(self, csv_rows):
        """Every CSV row must contain all 14 required fields."""
        for i, row in enumerate(csv_rows):
            missing = [f for f in REQUIRED_FIELDS if f not in row or row[f] in (None, "")]
            assert not missing, f"Row {i+1}: missing fields {missing}"

    def test_csv_total_fare_math(self, csv_rows):
        """total_fare must equal base_fare + taxes + fees within ±0.01."""
        for i, row in enumerate(csv_rows):
            computed = round(row["base_fare"] + row["taxes"] + row["fees"], 2)
            assert abs(computed - row["total_fare"]) <= 0.01, (
                f"Row {i+1}: fare math breach – "
                f"base({row['base_fare']}) + taxes({row['taxes']}) + fees({row['fees']}) "
                f"= {computed} ≠ total({row['total_fare']})"
            )

    def test_csv_booking_window_values(self, csv_rows):
        """Every booking_window value must be one of the 5 legal windows."""
        for i, row in enumerate(csv_rows):
            assert row["booking_window"] in BOOKING_WINDOWS, (
                f"Row {i+1}: invalid booking_window '{row['booking_window']}'"
            )

    def test_csv_source_data_status(self, csv_rows):
        """source and data_status must be within their legal value sets."""
        valid_src = VALID_SOURCES | {"replay"}
        for i, row in enumerate(csv_rows):
            assert row["source"] in valid_src, (
                f"Row {i+1}: invalid source '{row['source']}'"
            )
            assert row["data_status"] in VALID_DATA_STATUSES, (
                f"Row {i+1}: invalid data_status '{row['data_status']}'"
            )

    def test_csv_carrier_whitelist(self, csv_rows):
        """All carriers must be INDIGO or AIR INDIA."""
        for i, row in enumerate(csv_rows):
            assert row["carrier"].strip().upper() in ALLOWED_CARRIERS, (
                f"Row {i+1}: non-whitelisted carrier '{row['carrier']}'"
            )

    def test_csv_iata_codes(self, csv_rows):
        """origin and destination must be 3-letter uppercase strings."""
        for i, row in enumerate(csv_rows):
            for code_field in ("origin", "destination"):
                code = str(row[code_field]).strip().upper()
                assert len(code) == 3 and code.isalpha(), (
                    f"Row {i+1}: invalid {code_field} '{row[code_field]}'"
                )

    def test_csv_availability_nonneg(self, csv_rows):
        """availability must be a non-negative integer."""
        for i, row in enumerate(csv_rows):
            assert isinstance(row["availability"], int) and row["availability"] >= 0, (
                f"Row {i+1}: invalid availability '{row['availability']}'"
            )

    def test_csv_observed_at_iso(self, csv_rows):
        """observed_at must parse as a valid ISO-8601 datetime."""
        for i, row in enumerate(csv_rows):
            try:
                datetime.fromisoformat(str(row["observed_at"]).replace("Z", "+00:00"))
            except ValueError:
                pytest.fail(
                    f"Row {i+1}: observed_at is not a valid ISO-8601 timestamp: "
                    f"'{row['observed_at']}'"
                )

    def test_csv_no_nulls(self, csv_rows):
        """No required field in any row may be None or empty string."""
        for i, row in enumerate(csv_rows):
            for field in REQUIRED_FIELDS:
                val = row.get(field)
                assert val not in (None, ""), (
                    f"Row {i+1}: field '{field}' is null or empty"
                )
