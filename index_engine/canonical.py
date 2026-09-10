"""
index_engine/canonical.py
==========================
Typed representation of the FareObservation contract for internal index calculations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class FareObservation:
    """
    Canonical, immutable FareObservation dataclass.
    Strictly aligns with Member 1's input contract schema.
    """
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

    @property
    def route(self) -> str:
        """Returns ORIGIN-DEST e.g. DEL-BOM"""
        return f"{self.origin.upper()}-{self.destination.upper()}"

    @property
    def observed_date(self) -> str:
        """Extract YYYY-MM-DD from observed_at ISO timestamp."""
        return self.observed_at.split("T")[0]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FareObservation:
        """Construct a FareObservation instance from a dictionary."""
        return cls(
            source=str(data["source"]).strip().lower(),
            data_status=str(data["data_status"]).strip().upper(),
            origin=str(data["origin"]).strip().upper(),
            destination=str(data["destination"]).strip().upper(),
            carrier=str(data["carrier"]).strip().upper(),
            travel_date=str(data["travel_date"]).strip(),
            observed_at=str(data["observed_at"]).strip(),
            booking_window=str(data["booking_window"]).strip(),
            fare_class=str(data.get("fare_class", "ECONOMY")).strip().upper(),
            base_fare=float(data["base_fare"]),
            taxes=float(data["taxes"]),
            fees=float(data["fees"]),
            total_fare=float(data["total_fare"]),
            availability=int(data.get("availability", 9)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert back to dictionary format."""
        return {
            "source": self.source,
            "data_status": self.data_status,
            "origin": self.origin,
            "destination": self.destination,
            "carrier": self.carrier,
            "travel_date": self.travel_date,
            "observed_at": self.observed_at,
            "booking_window": self.booking_window,
            "fare_class": self.fare_class,
            "base_fare": self.base_fare,
            "taxes": self.taxes,
            "fees": self.fees,
            "total_fare": self.total_fare,
            "availability": self.availability,
        }
