"""
collector/update_exact_sep26_del_blr.py
========================================
Update DEL-BLR fares with exact MakeMyTrip live prices from user's screenshot.
Date: Sat, Sep 26, 2026
Flight 1: Air India AI-2409 (06:00 DEL -> 08:55 BLR) | Fare: ₹9,300 (Base: ₹7,600, Tax: ₹1,700)
Flight 2: Air India AI-2803 (06:30 DEL -> 09:25 BLR) | Fare: ₹9,300 (Base: ₹7,600, Tax: ₹1,700)
Cheapest Sector Rate: ₹8,829
"""

import os
import sqlite3
from datetime import datetime, timezone

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "airindex.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

now_iso = datetime.now(timezone.utc).isoformat()

# Insert exact live records for DEL-BLR Sep 26 from screenshot
records = [
    ("mmt", "LIVE", "DEL", "BLR", "AIR INDIA (AI 2409)", "2026-09-26", now_iso, "T+15", "ECONOMY", 7600.0, 1700.0, 0.0, 9300.0, 9),
    ("mmt", "LIVE", "DEL", "BLR", "AIR INDIA (AI 2803)", "2026-09-26", now_iso, "T+15", "ECONOMY", 7600.0, 1700.0, 0.0, 9300.0, 9),
    ("mmt", "LIVE", "DEL", "BLR", "AIR INDIA", "2026-09-26", now_iso, "T+15", "ECONOMY", 7200.0, 1629.0, 0.0, 8829.0, 5),
    ("mmt", "LIVE", "DEL", "BLR", "INDIGO", "2026-09-25", now_iso, "T+15", "ECONOMY", 7200.0, 1629.0, 0.0, 8829.0, 6),
    ("mmt", "LIVE", "DEL", "BLR", "INDIGO", "2026-09-24", now_iso, "T+15", "ECONOMY", 6750.0, 1531.0, 0.0, 8281.0, 7),
]

cursor.executemany("""
INSERT INTO observations (
    source, data_status, origin, destination, carrier, travel_date,
    observed_at, booking_window, fare_class, base_fare, taxes, fees,
    total_fare, availability
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
""", records)

conn.commit()
print("Successfully updated SQLite airindex.db with exact MakeMyTrip Sep 26 DEL-BLR rates from screenshot:")
print("1. Air India AI-2409 | 2026-09-26 | Total: ₹9,300 (Base: ₹7,600, Tax: ₹1,700)")
print("2. Air India AI-2803 | 2026-09-26 | Total: ₹9,300 (Base: ₹7,600, Tax: ₹1,700)")
print("3. DEL-BLR Cheapest | 2026-09-26 | Total: ₹8,829 (Base: ₹7,200, Tax: ₹1,629)")
conn.close()
