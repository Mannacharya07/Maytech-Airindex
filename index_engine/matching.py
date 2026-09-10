"""
index_engine/matching.py
========================
Fare identity matching logic to ensure only identical flight products
are compared across time periods.
"""

from __future__ import annotations

from typing import Dict, List, Tuple
from .canonical import FareObservation


def fare_identity(obs: FareObservation) -> str:
    """
    Generate a unique, stable fare product identity key.

    Format: ORIGIN-DEST|CARRIER|BOOKING_WINDOW|FARE_CLASS
    Example: DEL-BOM|INDIGO|T+7|ECONOMY
    """
    return (
        f"{obs.origin}-{obs.destination}|"
        f"{obs.carrier}|"
        f"{obs.booking_window}|"
        f"{obs.fare_class}"
    )


def find_matched_pairs(
    base_observations: List[FareObservation],
    current_observations: List[FareObservation],
) -> List[Tuple[FareObservation, FareObservation]]:
    """
    Match observations from base period and current period by fare_identity.
    Returns a list of (base_obs, current_obs) pairs.
    """
    base_map: Dict[str, FareObservation] = {}
    for obs in base_observations:
        key = fare_identity(obs)
        if key not in base_map:
            base_map[key] = obs

    matched_pairs: List[Tuple[FareObservation, FareObservation]] = []
    seen_current: set = set()

    for curr_obs in current_observations:
        key = fare_identity(curr_obs)
        if key in base_map and key not in seen_current:
            matched_pairs.append((base_map[key], curr_obs))
            seen_current.add(key)

    return matched_pairs
