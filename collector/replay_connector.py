"""
collector/replay_connector.py
==============================
Reads previously harvested rows from collector/data/replay_data.csv
and streams them as validated observation dicts.

Useful for:
- Deterministic offline testing without hitting live sites.
- Replaying historical data for model training / validation.
- Simulating a feed for downstream consumers.

Usage
-----
from collector import ReplayConnector

rc = ReplayConnector()

# Stream all rows
for obs in rc.stream():
    print(obs)

# Filtered: only DEL-BOM, IndiGo, T+15
for obs in rc.stream(route="DEL-BOM", carrier="INDIGO", booking_window="T+15"):
    print(obs)

# collect() interface (returns a list, compatible with BaseConnector API)
obs_list = rc.collect("DEL-BOM", "2026-09-25", "T+15")
"""

from __future__ import annotations

import csv
import logging
import os
from typing import Any, Generator

from .base_connector import BaseConnector, validate_observation

logger = logging.getLogger(__name__)

# Default path relative to this file's location
_DEFAULT_CSV = os.path.join(
    os.path.dirname(__file__), "data", "replay_data.csv"
)


class ReplayConnector(BaseConnector):
    """
    CSV-backed replay connector.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file written by harvest_real_data.py.
        Defaults to collector/data/replay_data.csv.
    """

    def __init__(self, csv_path: str = _DEFAULT_CSV):
        self.csv_path = csv_path

    # ------------------------------------------------------------------
    # Core streaming interface
    # ------------------------------------------------------------------

    def stream(
        self,
        route: str | None = None,
        carrier: str | None = None,
        booking_window: str | None = None,
        travel_date: str | None = None,
        source: str | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Yield validated observation dicts from the CSV, with optional filters.

        All filter arguments are case-insensitive and support partial matching
        for `carrier` (e.g., "indigo" matches "INDIGO").

        Parameters
        ----------
        route : str | None
            "ORIGIN-DEST" e.g. "DEL-BOM". Filters on origin+destination.
        carrier : str | None
            Carrier name, e.g. "INDIGO" or "AIR INDIA".
        booking_window : str | None
            e.g. "T+15"
        travel_date : str | None
            "YYYY-MM-DD"
        source : str | None
            "mmt", "goibibo", or "replay"
        """
        if not os.path.exists(self.csv_path):
            logger.warning(
                "Replay CSV not found at '%s'. Run harvest_real_data.py first.", self.csv_path
            )
            return

        # Parse optional route filter
        origin_filter = dest_filter = None
        if route:
            parts = route.upper().split("-")
            if len(parts) == 2:
                origin_filter, dest_filter = parts
            else:
                logger.warning("Invalid route filter '%s' – ignored", route)

        carrier_filter = carrier.strip().upper() if carrier else None
        bw_filter = booking_window.strip() if booking_window else None
        td_filter = travel_date.strip() if travel_date else None
        src_filter = source.strip().lower() if source else None

        row_count = 0
        yielded = 0

        with open(self.csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for raw_row in reader:
                row_count += 1

                # Apply filters
                if origin_filter and raw_row.get("origin", "").upper() != origin_filter:
                    continue
                if dest_filter and raw_row.get("destination", "").upper() != dest_filter:
                    continue
                if carrier_filter and raw_row.get("carrier", "").upper() != carrier_filter:
                    continue
                if bw_filter and raw_row.get("booking_window", "").strip() != bw_filter:
                    continue
                if td_filter and raw_row.get("travel_date", "").strip() != td_filter:
                    continue
                if src_filter and raw_row.get("source", "").lower() != src_filter:
                    continue

                # Coerce numeric fields (CSV stores everything as strings)
                for num_field in ("base_fare", "taxes", "fees", "total_fare"):
                    try:
                        raw_row[num_field] = float(raw_row[num_field])
                    except (ValueError, KeyError):
                        pass
                for int_field in ("availability",):
                    try:
                        raw_row[int_field] = int(raw_row[int_field])
                    except (ValueError, KeyError):
                        pass

                try:
                    obs = validate_observation(dict(raw_row))
                    # Mark replayed rows
                    obs["source"] = "replay"
                    obs["data_status"] = "REPLAY"
                    yield obs
                    yielded += 1
                except ValueError as exc:
                    logger.warning("Row %d failed validation – skipped: %s", row_count, exc)

        logger.info(
            "ReplayConnector: %d/%d rows yielded (filters: route=%s carrier=%s bw=%s)",
            yielded, row_count, route, carrier, booking_window,
        )

    # ------------------------------------------------------------------
    # BaseConnector.collect() implementation
    # ------------------------------------------------------------------

    def collect(
        self,
        route: str,
        travel_date: str,
        booking_window: str,
    ) -> list[dict[str, Any]]:
        """
        Return a list of replay observations matching the given filters.

        Compatible with the BaseConnector API so ReplayConnector can be
        used as a drop-in replacement for LiveConnector in tests.
        """
        return list(
            self.stream(
                route=route,
                travel_date=travel_date,
                booking_window=booking_window,
            )
        )
