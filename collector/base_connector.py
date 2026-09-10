"""
collector/base_connector.py
============================
Abstract Base Class for all connectors + the central observation validator.

Every single observation produced by any connector MUST pass
`BaseConnector.validate_observation()` before leaving the module.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------

BOOKING_WINDOWS: list[str] = ["T+1", "T+7", "T+15", "T+30", "T+45"]

VALID_SOURCES: set[str] = {"mmt", "goibibo", "replay"}
VALID_DATA_STATUSES: set[str] = {"LIVE", "REPLAY"}
VALID_FARE_CLASSES: set[str] = {"ECONOMY", "BUSINESS", "FIRST"}

# Whitelisted carriers for this project
ALLOWED_CARRIERS: set[str] = {"INDIGO", "AIR INDIA"}

REQUIRED_FIELDS: list[str] = [
    "source",
    "data_status",
    "origin",
    "destination",
    "carrier",
    "travel_date",
    "observed_at",
    "booking_window",
    "fare_class",
    "base_fare",
    "taxes",
    "fees",
    "total_fare",
    "availability",
]


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------

def validate_observation(obs: dict[str, Any]) -> dict[str, Any]:
    """
    Validate a single observation dict against the frozen contract.

    Returns the *same* dict (possibly with minor type coercions) if valid.
    Raises ValueError with a descriptive message on any contract breach.

    Rules enforced
    --------------
    1. All REQUIRED_FIELDS are present and non-null / non-empty.
    2. source         ∈ VALID_SOURCES
    3. data_status    ∈ VALID_DATA_STATUSES
    4. booking_window ∈ BOOKING_WINDOWS
    5. carrier        ∈ ALLOWED_CARRIERS
    6. origin / destination are 3-letter uppercase IATA codes.
    7. fare_class     ∈ VALID_FARE_CLASSES
    8. base_fare, taxes, fees, total_fare are non-negative floats.
    9. total_fare == round(base_fare + taxes + fees, 2)  (±0.01 tolerance)
    10. availability  is a non-negative integer.
    11. observed_at   is a parseable ISO-8601 timestamp.
    12. travel_date   is a parseable YYYY-MM-DD date string.
    """

    # --- 1. Required fields present & non-null ---
    for field in REQUIRED_FIELDS:
        if field not in obs:
            raise ValueError(f"Missing required field: '{field}'")
        value = obs[field]
        if value is None or value == "":
            raise ValueError(f"Field '{field}' must not be null or empty; got {value!r}")

    # --- 2. source ---
    if obs["source"] not in VALID_SOURCES:
        raise ValueError(
            f"source must be one of {VALID_SOURCES}; got {obs['source']!r}"
        )

    # --- 3. data_status ---
    if obs["data_status"] not in VALID_DATA_STATUSES:
        raise ValueError(
            f"data_status must be one of {VALID_DATA_STATUSES}; got {obs['data_status']!r}"
        )

    # --- 4. booking_window ---
    if obs["booking_window"] not in BOOKING_WINDOWS:
        raise ValueError(
            f"booking_window must be one of {BOOKING_WINDOWS}; got {obs['booking_window']!r}"
        )

    # --- 5. carrier whitelist ---
    carrier_upper = str(obs["carrier"]).strip().upper()
    if carrier_upper not in ALLOWED_CARRIERS:
        raise ValueError(
            f"carrier must be one of {ALLOWED_CARRIERS}; got {obs['carrier']!r}"
        )
    obs["carrier"] = carrier_upper  # normalise in-place

    # --- 6. IATA codes ---
    for code_field in ("origin", "destination"):
        code = str(obs[code_field]).strip().upper()
        if len(code) != 3 or not code.isalpha():
            raise ValueError(
                f"'{code_field}' must be a 3-letter IATA code; got {obs[code_field]!r}"
            )
        obs[code_field] = code  # normalise

    # --- 7. fare_class ---
    if str(obs["fare_class"]).strip().upper() not in VALID_FARE_CLASSES:
        raise ValueError(
            f"fare_class must be one of {VALID_FARE_CLASSES}; got {obs['fare_class']!r}"
        )
    obs["fare_class"] = str(obs["fare_class"]).strip().upper()

    # --- 8. Fare fields are non-negative numbers ---
    for fare_field in ("base_fare", "taxes", "fees", "total_fare"):
        try:
            obs[fare_field] = float(obs[fare_field])
        except (TypeError, ValueError):
            raise ValueError(
                f"'{fare_field}' must be a numeric value; got {obs[fare_field]!r}"
            )
        if obs[fare_field] < 0:
            raise ValueError(f"'{fare_field}' must be >= 0; got {obs[fare_field]}")

    # --- 9. Fare math: total_fare == base_fare + taxes + fees (±0.01) ---
    computed = round(obs["base_fare"] + obs["taxes"] + obs["fees"], 2)
    if abs(computed - obs["total_fare"]) > 0.01:
        raise ValueError(
            f"Fare math breach: base_fare({obs['base_fare']}) + taxes({obs['taxes']}) "
            f"+ fees({obs['fees']}) = {computed} ≠ total_fare({obs['total_fare']})"
        )

    # --- 10. availability ---
    try:
        obs["availability"] = int(obs["availability"])
    except (TypeError, ValueError):
        raise ValueError(
            f"'availability' must be an integer; got {obs['availability']!r}"
        )
    if obs["availability"] < 0:
        raise ValueError(f"'availability' must be >= 0; got {obs['availability']}")

    # --- 11. observed_at is valid ISO timestamp ---
    try:
        datetime.fromisoformat(str(obs["observed_at"]).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(
            f"'observed_at' must be a valid ISO-8601 timestamp; got {obs['observed_at']!r}"
        )

    # --- 12. travel_date is valid YYYY-MM-DD ---
    try:
        datetime.strptime(str(obs["travel_date"]), "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"'travel_date' must be YYYY-MM-DD; got {obs['travel_date']!r}"
        )

    return obs


# ---------------------------------------------------------------------------
# Abstract Base Class
# ---------------------------------------------------------------------------

class BaseConnector(ABC):
    """
    Abstract base for LiveConnector and ReplayConnector.

    Subclasses must implement `collect()` and may call
    `self.validate(obs)` to enforce the frozen contract.
    """

    # Expose constants as class attributes so subclasses don't need to import them
    BOOKING_WINDOWS = BOOKING_WINDOWS
    ALLOWED_CARRIERS = ALLOWED_CARRIERS

    def validate(self, obs: dict[str, Any]) -> dict[str, Any]:
        """Instance-level shim to the module-level validator."""
        return validate_observation(obs)

    @abstractmethod
    def collect(
        self,
        route: str,
        travel_date: str,
        booking_window: str,
    ) -> list[dict[str, Any]]:
        """
        Collect airfare observations for a given route / date / booking window.

        Parameters
        ----------
        route : str
            "ORIGIN-DESTINATION" e.g. "DEL-BOM"
        travel_date : str
            ISO date "YYYY-MM-DD"
        booking_window : str
            One of BOOKING_WINDOWS, e.g. "T+15"

        Returns
        -------
        list[dict]
            Zero or more validated observation dicts.
        """
        ...
