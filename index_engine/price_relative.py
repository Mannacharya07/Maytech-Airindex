"""
index_engine/price_relative.py
==============================
Computes the price relative ratio between current fare and base period fare.
"""

from __future__ import annotations

from .canonical import FareObservation


def compute_price_relative(
    base_obs: FareObservation,
    current_obs: FareObservation,
) -> float:
    """
    Compute the price relative ratio.

    Formula: Price Relative = Current Total Fare / Base Total Fare
    Example: 5500 / 5000 = 1.10 (+10% movement)
    """
    if base_obs.total_fare <= 0:
        raise ValueError(f"Base period fare must be > 0; got {base_obs.total_fare}")

    return current_obs.total_fare / base_obs.total_fare
