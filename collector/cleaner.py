"""
collector/cleaner.py
=====================
Data cleaning & statistical outlier rejection pipeline.

Functions:
- filter_valid_observations: rejects negative/zero fares, missing required fields.
- remove_price_outliers: uses Median Absolute Deviation (MAD) robust Z-score
  to eliminate erroneous scraper spikes or anomalous zero/excessive fares.
"""

from __future__ import annotations
import numpy as np
from typing import Any

def clean_observation(obs: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and clean single raw observation."""
    if not isinstance(obs, dict):
        return None
        
    total_fare = obs.get("total_fare")
    if total_fare is None or not isinstance(total_fare, (int, float)) or total_fare <= 0:
        return None

    availability = obs.get("availability", 0)
    if availability < 0:
        obs["availability"] = 0

    return obs

def filter_outliers_mad(observations: list[dict[str, Any]], threshold: float = 3.5) -> list[dict[str, Any]]:
    """Filter list of observation dicts using MAD Z-score threshold."""
    if len(observations) < 4:
        return observations  # sample too small for robust MAD

    fares = np.array([obs["total_fare"] for obs in observations], dtype=float)
    median = float(np.median(fares))
    mad = float(np.median(np.abs(fares - median)))

    if mad == 0:
        return observations

    cleaned = []
    for obs in observations:
        z_score = 0.6745 * abs(obs["total_fare"] - median) / mad
        if z_score <= threshold:
            cleaned.append(obs)

    return cleaned
