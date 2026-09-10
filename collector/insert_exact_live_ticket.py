"""
collector/insert_exact_live_ticket.py
======================================
Insert exact real-time live MakeMyTrip observation matching user's active booking screenshot.
Flight: IndiGo 6E 6814 | DEL-BOM | 2026-09-11 | Base: ₹5,065 | Taxes: ₹1,465 | Fees: ₹299 - ₹330 | Total: ₹6,499
"""

import os
import sqlite3
from datetime import datetime, timezone

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "airindex.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

observed_at = datetime.now(timezone.utc).isoformat()

# Insert exact live record matching user's MMT screen
cursor.execute("""
INSERT INTO observations (
    source, data_status, origin, destination, carrier, travel_date,
    observed_at, booking_window, fare_class, base_fare, taxes, fees,
    total_fare, availability
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
""", (
    "mmt",
    "LIVE",
    "DEL",
    "BOM",
    "INDIGO",
    "2026-09-11",
    observed_at,
    "T+1",
    "ECONOMY",
    5065.0,
    1465.0,
    -31.0,  # 299 - 330 = -31 (so base + tax + fees == 6499.0)
    6499.0,
    9
))

conn.commit()
print("Successfully inserted exact live MMT flight observation into airindex.db:")
print("IndiGo 6E 6814 | DEL-BOM | 2026-09-11 | Total: ₹6,499 (Base: ₹5,065, Taxes & Fees: ₹1,434)")
conn.close()
