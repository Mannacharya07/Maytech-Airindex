"""
index_engine – AIRINDEX Price Index Engine
===========================================
Member 2: Data / Index Engineer  |  Project SIH26056

Public API
----------
from index_engine import (
    FareObservation,
    IndexEngine,
    compute_jevons_index,
    get_route_weights,
)
"""

from .canonical import FareObservation
from .jevons import compute_jevons_index
from .national_index import IndexEngine
from .weights import DGCA_ROUTE_WEIGHTS, get_route_weights

__all__ = [
    "FareObservation",
    "IndexEngine",
    "compute_jevons_index",
    "DGCA_ROUTE_WEIGHTS",
    "get_route_weights",
]
