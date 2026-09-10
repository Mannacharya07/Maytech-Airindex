"""
live_demo.py
============
Fetches REAL-TIME live flight prices directly off MakeMyTrip right now,
prints the live observations to the console, and ingests them into the SQLite DB.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from collector.live_connector import LiveConnector
from api.database import get_db_connection, init_sqlite_db
from api.services import compute_and_sync_index_values

print("=" * 72)
print("  AIRINDEX REAL-TIME LIVE HARVEST DEMO (MakeMyTrip)")
print("=" * 72)

lc = LiveConnector(otas=["mmt"], headless=True)

# Query live flights for DEL-BOM for tomorrow (T+1)
tomorrow_str = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")

print(f"\n[LIVE CRAWL] Navigating to MakeMyTrip for DEL-BOM on {tomorrow_str}...")
observations = lc.collect(route="DEL-BOM", travel_date=tomorrow_str, booking_window="T+1")

print(f"\n[RESULTS] Harvested {len(observations)} LIVE observations from MakeMyTrip:\n")

if observations:
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    for obs in observations:
        print(
            f"  ✈️  {obs['carrier']:<10} | {obs['origin']}→{obs['destination']} | {obs['booking_window']} | "
            f"Travel: {obs['travel_date']} | TOTAL FARE: ₹{obs['total_fare']:<7.2f} "
            f"(Base: ₹{obs['base_fare']} + Taxes: ₹{obs['taxes']} + Fees: ₹{obs['fees']})"
        )

        cursor.execute(
            """
            INSERT INTO observations (
                source, data_status, origin, destination, carrier, travel_date,
                observed_at, booking_window, fare_class, base_fare, taxes, fees,
                total_fare, availability
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
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
            ),
        )

    conn.commit()
    conn.close()
    compute_and_sync_index_values()
    print("\n✅ Database & Dashboard synced with fresh live MakeMyTrip data!")
else:
    print("No cards parsed (or Akamai CDN pause). Run harvest_real_data.py to refresh batch.")

print("=" * 72)
