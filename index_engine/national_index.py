"""
index_engine/national_index.py
==============================
Two-stage Airfare Price Index calculation engine:
  Stage 1: Calculate route-level Jevons index using geometric mean of price relatives.
  Stage 2: Aggregate route indices using DGCA traffic weights into National Airfare Index.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from .canonical import FareObservation
from .jevons import compute_jevons_index
from .matching import find_matched_pairs
from .price_relative import compute_price_relative
from .validation import validate_for_index
from .weights import get_route_weights

logger = logging.getLogger(__name__)


class IndexEngine:
    """
    Main Index Engine orchestrator.
    Converts raw observation records into Route and National Index values.
    """

    def __init__(self, route_weights: Dict[str, float] | None = None):
        self.weights = route_weights or get_route_weights()

    def process_observations(self, records: List[Dict[str, Any] | FareObservation]) -> List[FareObservation]:
        """Convert raw dict records or objects into validated FareObservation objects."""
        valid_obs: List[FareObservation] = []
        for rec in records:
            obs = rec if isinstance(rec, FareObservation) else FareObservation.from_dict(rec)
            is_valid, reason = validate_for_index(obs)
            if is_valid:
                valid_obs.append(obs)
            else:
                logger.warning("Rejected observation for index: %s", reason)
        return valid_obs

    def calculate_route_indices(
        self,
        base_observations: List[FareObservation],
        current_observations: List[FareObservation],
    ) -> Dict[str, float]:
        """
        Calculate route-level Jevons index for every route in the basket.
        Returns dict mapping route -> index_value (base = 100.00).
        """
        # Group observations by route
        base_by_route: Dict[str, List[FareObservation]] = {}
        for obs in base_observations:
            base_by_route.setdefault(obs.route, []).append(obs)

        current_by_route: Dict[str, List[FareObservation]] = {}
        for obs in current_observations:
            current_by_route.setdefault(obs.route, []).append(obs)

        route_indices: Dict[str, float] = {}

        for route in self.weights.keys():
            b_list = base_by_route.get(route, [])
            c_list = current_by_route.get(route, [])

            matched_pairs = find_matched_pairs(b_list, c_list)
            if not matched_pairs:
                logger.warning("No matched pairs for route '%s' – defaulting to 100.00", route)
                route_indices[route] = 100.0
                continue

            relatives = [compute_price_relative(base, curr) for base, curr in matched_pairs]
            route_indices[route] = compute_jevons_index(relatives)

        return route_indices

    def calculate_national_index(
        self,
        base_records: List[Dict[str, Any] | FareObservation],
        current_records: List[Dict[str, Any] | FareObservation],
    ) -> Dict[str, Any]:
        """
        Calculate end-to-end National & Route-Level Airfare Price Indices.

        Returns output contract dictionary:
        {
            "national_index": 108.45,
            "route_indices": {"DEL-BOM": 110.20, ...},
            "matched_pairs_count": 48
        }
        """
        base_obs = self.process_observations(base_records)
        current_obs = self.process_observations(current_records)

        route_indices = self.calculate_route_indices(base_obs, current_obs)

        # Weighted arithmetic aggregation across routes
        weighted_sum = sum(route_indices[r] * self.weights[r] for r in self.weights.keys() if r in route_indices)
        national_index = round(weighted_sum, 2)

        return {
            "national_index": national_index,
            "route_indices": route_indices,
            "route_weights": self.weights,
            "base_observations_count": len(base_obs),
            "current_observations_count": len(current_obs),
        }
