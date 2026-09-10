"""
index_engine/weights.py
=======================
DGCA Passenger-Traffic Route Weights for representative Indian city-pairs.
Weights reflect estimated annual passenger traffic share and sum to 1.0.
"""

from __future__ import annotations

from typing import Dict

# DGCA Top Passenger Traffic Share Estimates (Sum = 1.00)
DGCA_ROUTE_WEIGHTS: Dict[str, float] = {
    "DEL-BOM": 0.28,  # Delhi - Mumbai (28%)
    "DEL-BLR": 0.22,  # Delhi - Bengaluru (22%)
    "BOM-BLR": 0.18,  # Mumbai - Bengaluru (18%)
    "DEL-CCU": 0.14,  # Delhi - Kolkata (14%)
    "BLR-HYD": 0.10,  # Bengaluru - Hyderabad (10%)
    "MAA-DEL": 0.08,  # Chennai - Delhi (8%)
}


def get_route_weights() -> Dict[str, float]:
    """
    Returns copy of route weights dictionary after validating sum == 1.0.
    """
    total_weight = round(sum(DGCA_ROUTE_WEIGHTS.values()), 4)
    if abs(total_weight - 1.0) > 0.001:
        raise ValueError(f"Route weights must sum to 1.00; got {total_weight}")

    return DGCA_ROUTE_WEIGHTS.copy()
