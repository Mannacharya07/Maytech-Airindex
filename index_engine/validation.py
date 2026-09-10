"""
index_engine/validation.py
==========================
Data validation rules before fare observations enter index calculation.
"""

from __future__ import annotations

from typing import Tuple
from .canonical import FareObservation

ALLOWED_WINDOWS = {"T+1", "T+7", "T+15", "T+30", "T+45"}
ALLOWED_CLASSES = {"ECONOMY", "BUSINESS", "FIRST"}


def validate_for_index(obs: FareObservation) -> Tuple[bool, str]:
    """
    Validate if a FareObservation is fit for index calculation.
    Returns (True, "") if valid, or (False, "reason") if invalid.
    """
    if obs.total_fare <= 0:
        return False, f"Total fare must be > 0; got {obs.total_fare}"

    if obs.base_fare < 0 or obs.taxes < 0 or obs.fees < 0:
        return False, "Fare components cannot be negative"

    if obs.booking_window not in ALLOWED_WINDOWS:
        return False, f"Invalid booking window: {obs.booking_window}"

    if obs.fare_class not in ALLOWED_CLASSES:
        return False, f"Invalid fare class: {obs.fare_class}"

    if len(obs.origin) != 3 or len(obs.destination) != 3:
        return False, f"Invalid IATA codes: {obs.origin}-{obs.destination}"

    if obs.origin == obs.destination:
        return False, "Origin and destination cannot be identical"

    return True, ""
