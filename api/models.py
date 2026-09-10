"""
api/models.py
=============
Pydantic schemas for API response serialization and validation.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class FareResponse(BaseModel):
    id: Optional[int] = None
    source: str
    data_status: str
    origin: str
    destination: str
    carrier: str
    travel_date: str
    observed_at: str
    booking_window: str
    fare_class: str
    base_fare: float
    taxes: float
    fees: float
    total_fare: float
    availability: int


class RouteResponse(BaseModel):
    origin: str
    destination: str
    route: str
    weight: float
    weight_percentage: str


class IndexCurrentResponse(BaseModel):
    national_index: float
    base_date: str
    latest_date: str
    route_indices: Dict[str, float]
    route_weights: Dict[str, float]


class IndexHistoryItem(BaseModel):
    date: str
    route: str
    index_value: float


class IndexHistoryResponse(BaseModel):
    history: List[IndexHistoryItem]
    total_records: int


class LeadTimeItem(BaseModel):
    booking_window: str
    avg_total_fare: float
    avg_base_fare: float
    avg_taxes: float
    observation_count: int


class LeadTimeResponse(BaseModel):
    route: str
    lead_time_curve: List[LeadTimeItem]
