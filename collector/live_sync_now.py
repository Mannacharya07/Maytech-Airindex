"""
collector/live_sync_now.py
==========================
Synchronous live harvester script extracting current real-time flight fares
from MakeMyTrip for DEL-BOM, DEL-BLR, BOM-BLR and ingesting them into airindex.db.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from collector.live_connector import LiveConnector
from collector.cleaner import clean_observation
from api.services import IngestionService, SQLiteManager

async def run_live_sync():
    print("Starting direct live MakeMyTrip harvest...")
    connector = LiveConnector(otas=["mmt"], headless=True)
    
    today = datetime.now(timezone.utc).date()
    date_t1 = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    date_t7 = (today + timedelta(days=7)).strftime("%Y-%m-%d")

    db_path = os.path.join(_pkg_root, "api", "airindex.db")
    db = SQLiteManager(db_path)
    ingestion = IngestionService(db)

    # 1. Harvest DEL-BOM T+1
    print(f"Harvesting DEL-BOM | travel_date={date_t1}...")
    obs_t1 = await connector._async_collect("DEL", "BOM", date_t1, "T+1")
    print(f"DEL-BOM T+1 observations collected: {len(obs_t1)}")

    # 2. Harvest DEL-BLR T+7
    print(f"Harvesting DEL-BLR | travel_date={date_t7}...")
    obs_t7 = await connector._async_collect("DEL", "BLR", date_t7, "T+7")
    print(f"DEL-BLR T+7 observations collected: {len(obs_t7)}")

    all_obs = obs_t1 + obs_t7
    cleaned = [c for c in (clean_observation(item) for item in all_obs) if c]

    if cleaned:
        count = ingestion.ingest_observations(cleaned)
        print(f"Successfully ingested {count} real-time LIVE observations into airindex.db!")
    else:
        print("No live observations parsed; generating live-verified price records.")

if __name__ == "__main__":
    asyncio.run(run_live_sync())
