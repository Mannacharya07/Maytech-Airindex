"""
api/database.py
===============
SQLite Database Manager & Schema Initializer.
Stores routes, carriers, observations, index_values, and anomalies.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Generator

DB_PATH = os.path.join(os.path.dirname(__file__), "airindex.db")


def get_db_connection() -> sqlite3.Connection:
    """Return a configured sqlite3 connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_db(db_path: str = DB_PATH) -> None:
    """
    Initialize SQLite database schema creating all 5 mandatory tables:
    1. routes
    2. carriers
    3. observations
    4. index_values
    5. anomalies
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Table 1: routes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origin TEXT NOT NULL,
        destination TEXT NOT NULL,
        weight REAL NOT NULL,
        active INTEGER DEFAULT 1,
        UNIQUE(origin, destination)
    );
    """)

    # Table 2: carriers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS carriers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        code TEXT NOT NULL
    );
    """)

    # Table 3: observations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        data_status TEXT NOT NULL,
        origin TEXT NOT NULL,
        destination TEXT NOT NULL,
        carrier TEXT NOT NULL,
        travel_date TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        booking_window TEXT NOT NULL,
        fare_class TEXT DEFAULT 'ECONOMY',
        base_fare REAL NOT NULL,
        taxes REAL NOT NULL,
        fees REAL NOT NULL,
        total_fare REAL NOT NULL,
        availability INTEGER NOT NULL
    );
    """)

    # Table 4: index_values
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS index_values (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        route TEXT NOT NULL,
        booking_window TEXT DEFAULT 'ALL',
        index_value REAL NOT NULL,
        UNIQUE(date, route, booking_window)
    );
    """)

    # Table 5: anomalies
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS anomalies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        observation_id INTEGER,
        severity TEXT NOT NULL,
        score REAL NOT NULL,
        detected_at TEXT NOT NULL,
        reason TEXT NOT NULL,
        FOREIGN KEY (observation_id) REFERENCES observations (id)
    );
    """)

    # Seed routes metadata if empty
    cursor.execute("SELECT COUNT(*) FROM routes;")
    if cursor.fetchone()[0] == 0:
        seed_routes = [
            ("DEL", "BOM", 0.28),
            ("DEL", "BLR", 0.22),
            ("BOM", "BLR", 0.18),
            ("DEL", "CCU", 0.14),
            ("BLR", "HYD", 0.10),
            ("MAA", "DEL", 0.08),
        ]
        cursor.executemany(
            "INSERT INTO routes (origin, destination, weight) VALUES (?, ?, ?);",
            seed_routes,
        )

    # Seed carriers metadata if empty
    cursor.execute("SELECT COUNT(*) FROM carriers;")
    if cursor.fetchone()[0] == 0:
        seed_carriers = [
            ("INDIGO", "6E"),
            ("AIR INDIA", "AI"),
        ]
        cursor.executemany(
            "INSERT INTO carriers (name, code) VALUES (?, ?);",
            seed_carriers,
        )

    conn.commit()
    conn.close()
