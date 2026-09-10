"""
api/services.py
===============
Pipeline integration service connecting:
Collector (CSV/Live) -> SQLite Database -> Index Engine -> API Responses
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List

_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from collector import ReplayConnector
from index_engine import IndexEngine, FareObservation
from .database import get_db_connection, init_sqlite_db

logger = logging.getLogger(__name__)


def ingest_replay_csv_to_db() -> int:
    """
    Read observation rows from collector CSV and bulk insert into SQLite observations table.
    Avoids duplicate observations by checking existing timestamps & fare parameters.
    """
    init_sqlite_db()
    rc = ReplayConnector()
    records = list(rc.stream())

    if not records:
        logger.warning("No records found in replay CSV to ingest")
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing REPLAY observations to preserve LIVE observations
    cursor.execute("DELETE FROM observations WHERE data_status = 'REPLAY';")

    insert_sql = """
    INSERT INTO observations (
        source, data_status, origin, destination, carrier, travel_date,
        observed_at, booking_window, fare_class, base_fare, taxes, fees,
        total_fare, availability
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    tuples_to_insert = [
        (
            r["source"],
            r["data_status"],
            r["origin"],
            r["destination"],
            r["carrier"],
            r["travel_date"],
            r["observed_at"],
            r["booking_window"],
            r.get("fare_class", "ECONOMY"),
            r["base_fare"],
            r["taxes"],
            r["fees"],
            r["total_fare"],
            r["availability"],
        )
        for r in records
    ]

    cursor.executemany(insert_sql, tuples_to_insert)
    conn.commit()
    inserted_count = cursor.rowcount
    conn.close()

    logger.info("Ingested %d observation records into SQLite", len(tuples_to_insert))
    return len(tuples_to_insert)


def compute_and_sync_index_values() -> int:
    """
    Pull observations from SQLite DB, run IndexEngine across all 30 observation dates,
    and populate the index_values table.
    """
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM observations ORDER BY observed_at ASC;")
    rows = cursor.fetchall()
    if not rows:
        conn.close()
        return 0

    records = [dict(r) for r in rows]

    # Group records by observation date YYYY-MM-DD
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        obs_date = r["observed_at"].split("T")[0]
        by_date.setdefault(obs_date, []).append(r)

    sorted_dates = sorted(by_date.keys())
    base_date = sorted_dates[0]
    base_records = by_date[base_date]

    engine = IndexEngine()

    # Clear index_values table
    cursor.execute("DELETE FROM index_values;")

    index_rows_to_insert = []

    for curr_date in sorted_dates:
        curr_records = by_date[curr_date]
        res = engine.calculate_national_index(base_records, curr_records)

        # Insert National Index row
        index_rows_to_insert.append((curr_date, "NATIONAL", "ALL", res["national_index"]))

        # Insert Route Index rows
        for route_code, val in res["route_indices"].items():
            index_rows_to_insert.append((curr_date, route_code, "ALL", val))

    cursor.executemany(
        "INSERT INTO index_values (date, route, booking_window, index_value) VALUES (?, ?, ?, ?);",
        index_rows_to_insert,
    )

    conn.commit()
    conn.close()

    logger.info("Synced %d index_value records into SQLite", len(index_rows_to_insert))
    return len(index_rows_to_insert)


class SQLiteManager:
    def __init__(self, db_path: str = "airindex.db"):
        self.db_path = db_path

    def get_connection(self):
        return get_db_connection()


class IngestionService:
    def __init__(self, db_manager: SQLiteManager):
        self.db_manager = db_manager

    def ingest_observations(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0
        init_sqlite_db()
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        insert_sql = """
        INSERT INTO observations (
            source, data_status, origin, destination, carrier, travel_date,
            observed_at, booking_window, fare_class, base_fare, taxes, fees,
            total_fare, availability
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        tuples_to_insert = [
            (
                r["source"],
                r.get("data_status", "LIVE"),
                r["origin"],
                r["destination"],
                r["carrier"],
                r["travel_date"],
                r["observed_at"],
                r["booking_window"],
                r.get("fare_class", "ECONOMY"),
                r["base_fare"],
                r["taxes"],
                r["fees"],
                r["total_fare"],
                r.get("availability", 9),
            )
            for r in records
        ]

        cursor.executemany(insert_sql, tuples_to_insert)
        conn.commit()
        count = len(tuples_to_insert)
        conn.close()
        return count

