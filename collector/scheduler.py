"""
collector/scheduler.py
======================
Automatic periodic live harvest scheduler & background ingestion pipeline.

Runs periodic harvesting cycles using LiveConnector, cleans incoming raw fares
with collector.cleaner, and ingests them into SQLite airindex.db.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from .live_connector import LiveConnector
from .cleaner import clean_observation, filter_outliers_mad
from api.services import IngestionService, SQLiteManager

logger = logging.getLogger(__name__)

class HarvestScheduler:
    """
    Background scheduler orchestrating live harvesting cycles.
    """

    def __init__(self, interval_seconds: int = 60, db_path: str = "airindex.db"):
        self.interval_seconds = interval_seconds
        self.db_path = db_path
        self.is_running = False
        self._task: asyncio.Task | None = None
        self.last_run: str | None = None
        self.last_count: int = 0

    def start(self):
        """Start the background scheduler task."""
        if self.is_running:
            logger.info("HarvestScheduler is already running.")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("HarvestScheduler started with interval %d seconds.", self.interval_seconds)

    def stop(self):
        """Stop the background scheduler task."""
        if not self.is_running:
            return

        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("HarvestScheduler stopped.")

    async def _run_loop(self):
        while self.is_running:
            try:
                await self.run_harvest_cycle()
            except Exception as exc:
                logger.error("Error during harvest cycle: %s", exc, exc_info=True)

            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    async def run_harvest_cycle(self) -> int:
        """
        Execute one live harvest cycle across top routes & windows.
        Ingests harvested observations directly into airindex.db.
        """
        logger.info("Starting live harvest cycle...")
        connector = LiveConnector(otas=["mmt"], headless=True)
        
        # Target primary high-volume route DEL-BOM T+1 for real-time live match
        today = datetime.now(timezone.utc).date()
        travel_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        
        raw_obs = await connector._async_collect(
            origin="DEL",
            dest="BOM",
            travel_date=travel_date,
            booking_window="T+1",
        )

        cleaned_obs = []
        for item in raw_obs:
            c = clean_observation(item)
            if c:
                cleaned_obs.append(c)

        final_obs = filter_outliers_mad(cleaned_obs)

        if final_obs:
            db = SQLiteManager(self.db_path)
            ingestion = IngestionService(db)
            inserted = ingestion.ingest_observations(final_obs)
            self.last_count = inserted
            logger.info("Harvest cycle complete: %d live observations ingested into %s", inserted, self.db_path)
        else:
            self.last_count = 0
            logger.warning("Harvest cycle complete: 0 observations harvested.")

        self.last_run = datetime.now(timezone.utc).isoformat()
        return self.last_count

# Global singleton scheduler instance
scheduler = HarvestScheduler(interval_seconds=60)
