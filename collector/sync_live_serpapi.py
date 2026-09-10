"""
collector/sync_live_serpapi.py
==============================
Live Sync script that queries SerpAPI Google Flights with the provided API key,
fetches real-time flight rates for DGCA routes, inserts them into airindex.db,
and recomputes the index.
"""

from __future__ import annotations

import os
import sys
import sqlite3
from datetime import datetime, timedelta, timezone

_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from collector.api_connector import APIConnector
from api.database import init_sqlite_db, get_db_connection
from index_engine import IndexEngine

ROUTES_TO_FETCH = [
    ("DEL-BOM", "T+1", 1),
    ("DEL-BLR", "T+15", 15),
    ("DEL-BLR", "T+1", 1),
    ("BOM-BLR", "T+7", 7),
    ("DEL-CCU", "T+7", 7),
    ("BLR-HYD", "T+15", 15),
    ("MAA-DEL", "T+30", 30),
]

def run_live_serpapi_sync(api_key: str):
    print("Starting SerpAPI Live Sync...")
    init_sqlite_db()
    connector = APIConnector(serpapi_key=api_key)
    
    conn = get_db_connection()
    cursor = conn.cursor()

    now_base = datetime.now(timezone.utc)
    all_observations = []

    for route, window, days_offset in ROUTES_TO_FETCH:
        travel_date = (now_base + timedelta(days=days_offset)).strftime("%Y-%m-%d")
        print(f"Fetching live flight search data for {route} on {travel_date} ({window})...")
        try:
            obs_list = connector.collect(route, travel_date, window)
            print(f" -> Retreived {len(obs_list)} live observations for {route}")
            all_observations.extend(obs_list)
        except Exception as exc:
            print(f" Error fetching {route}: {exc}")

    if not all_observations:
        print("No observations fetched!")
        return

    # Delete previous live observations to avoid duplication
    cursor.execute("DELETE FROM observations WHERE data_status = 'LIVE';")

    insert_sql = """
    INSERT INTO observations (
        source, data_status, origin, destination, carrier, travel_date,
        observed_at, booking_window, fare_class, base_fare, taxes, fees,
        total_fare, availability
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    records_to_insert = [
        (
            obs["source"],
            obs["data_status"],
            obs["origin"],
            obs["destination"],
            obs["carrier"],
            obs["travel_date"],
            obs["observed_at"],
            obs["booking_window"],
            obs["fare_class"],
            obs["base_fare"],
            obs["taxes"],
            obs["fees"],
            obs["total_fare"],
            obs["availability"],
        )
        for obs in all_observations
    ]

    cursor.executemany(insert_sql, records_to_insert)
    conn.commit()
    print(f"Inserted {len(records_to_insert)} LIVE SerpAPI observations into airindex.db.")

    # Re-calculate index values
    try:
        from api.services import compute_and_sync_index_values
        compute_and_sync_index_values()
        print("Successfully re-computed index values in SQLite DB.")
    except Exception as exc:
        print(f"Index recalculation note: {exc}")

if __name__ == "__main__":
    key = os.environ.get("SERPAPI_KEY", "1fb2bd035520daca1aebf66aee88f9d9c021bb3285d879376262cf46bfeedce2")
    run_live_serpapi_sync(key)
