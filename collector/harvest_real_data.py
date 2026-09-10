"""
collector/harvest_real_data.py
===============================
Batch CLI script to crawl live airfares from MakeMyTrip and Goibibo
for specified routes, booking windows, and carriers, then persist
all validated observations to a CSV file.

Usage
-----
# Full run (defaults)
python -m collector.harvest_real_data

# Custom run
python -m collector.harvest_real_data \\
    --routes DEL-BOM DEL-BLR \\
    --windows T+1 T+7 T+15 T+30 T+45 \\
    --carriers INDIGO "AIR INDIA" \\
    --ota mmt goibibo \\
    --out collector/data/replay_data.csv \\
    --overwrite

Flags
-----
--routes      Space-separated ORIGIN-DEST pairs  (default: DEL-BOM DEL-BLR)
--windows     Booking windows to query           (default: all 5)
--carriers    Carrier whitelist                  (default: INDIGO "AIR INDIA")
--ota         OTAs to query: mmt goibibo         (default: both)
--out         Output CSV path
--overwrite   Truncate existing CSV before writing
--no-headless Show browser window (useful for debugging selectors)
--log-level   DEBUG | INFO | WARNING | ERROR     (default: INFO)
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Ensure package root is on path when run as __main__
# ---------------------------------------------------------------------------
_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from collector.base_connector import BOOKING_WINDOWS, REQUIRED_FIELDS
from collector.live_connector import LiveConnector

# ---------------------------------------------------------------------------
# Booking window → days offset
# ---------------------------------------------------------------------------
WINDOW_DAYS: dict[str, int] = {
    "T+1": 1,
    "T+7": 7,
    "T+15": 15,
    "T+30": 30,
    "T+45": 45,
}


def compute_travel_date(window: str, base: datetime | None = None) -> str:
    """Return YYYY-MM-DD for today + window offset."""
    base = base or datetime.now(timezone.utc)
    offset = WINDOW_DAYS[window]
    return (base + timedelta(days=offset)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def _ensure_csv(path: str, overwrite: bool) -> bool:
    """
    Create or validate the CSV file. Returns True if header was just written.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if overwrite and os.path.exists(path):
        os.remove(path)
        logging.info("Existing CSV truncated (--overwrite).")

    needs_header = not os.path.exists(path) or os.path.getsize(path) == 0
    if needs_header:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=REQUIRED_FIELDS)
            writer.writeheader()
        logging.info("Created CSV with header: %s", path)
    return needs_header


def _append_rows(path: str, rows: list[dict[str, Any]]) -> None:
    """Append validated observation rows to the CSV."""
    if not rows:
        return
    with open(path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=REQUIRED_FIELDS, extrasaction="ignore")
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Summary table printer
# ---------------------------------------------------------------------------

def _print_summary(stats: dict[tuple, int], elapsed_s: float) -> None:
    """Print a harvested-rows breakdown table."""
    print("\n" + "═" * 72)
    print("  AIRINDEX Harvest Summary")
    print("═" * 72)
    print(f"  {'OTA':<12} {'Route':<10} {'Carrier':<12} {'Window':<8} {'Rows':>6}")
    print("  " + "─" * 58)
    total = 0
    for (ota, route, carrier, window), count in sorted(stats.items()):
        print(f"  {ota:<12} {route:<10} {carrier:<12} {window:<8} {count:>6}")
        total += count
    print("  " + "─" * 58)
    print(f"  {'TOTAL':<43} {total:>6}")
    print(f"  Elapsed: {elapsed_s:.1f}s")
    print("═" * 72 + "\n")


# ---------------------------------------------------------------------------
# Main harvest orchestrator
# ---------------------------------------------------------------------------

def harvest(
    routes: list[str],
    windows: list[str],
    carriers: list[str],
    otas: list[str],
    out_path: str,
    overwrite: bool = False,
    headless: bool = True,
) -> None:
    import time

    _ensure_csv(out_path, overwrite)

    connector = LiveConnector(otas=otas, headless=headless)
    stats: dict[tuple, int] = {}
    start = time.monotonic()

    total_queries = len(routes) * len(windows)
    completed = 0

    for route in routes:
        for window in windows:
            travel_date = compute_travel_date(window)
            logging.info(
                "Harvesting %s | window=%s | travel_date=%s",
                route, window, travel_date,
            )

            try:
                obs_list = connector.collect(route, travel_date, window)
            except Exception as exc:
                logging.error("collect() failed for %s %s: %s", route, window, exc)
                obs_list = []

            # Filter to requested carriers only (connector already filters,
            # but apply again as a safety net)
            carrier_upper = [c.upper() for c in carriers]
            filtered = [o for o in obs_list if o.get("carrier", "").upper() in carrier_upper]

            _append_rows(out_path, filtered)

            # Update stats
            for obs in filtered:
                key = (
                    obs.get("source", "?"),
                    route.upper(),
                    obs.get("carrier", "?"),
                    window,
                )
                stats[key] = stats.get(key, 0) + 1

            completed += 1
            logging.info(
                "Progress: %d/%d queries done. %d rows written so far.",
                completed, total_queries, sum(stats.values()),
            )

    elapsed = time.monotonic() - start
    _print_summary(stats, elapsed)
    logging.info("All observations saved to: %s", out_path)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="AIRINDEX – Live airfare batch harvester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--routes",
        nargs="+",
        default=["DEL-BOM", "DEL-BLR", "BOM-BLR", "DEL-CCU", "BLR-HYD", "MAA-DEL"],
        metavar="ROUTE",
        help="DGCA top passenger-traffic city pairs (default: DEL-BOM DEL-BLR BOM-BLR DEL-CCU BLR-HYD MAA-DEL)",
    )
    p.add_argument(
        "--windows",
        nargs="+",
        default=BOOKING_WINDOWS,
        choices=BOOKING_WINDOWS,
        metavar="WINDOW",
        help="Booking windows to query (default: all 5)",
    )
    p.add_argument(
        "--carriers",
        nargs="+",
        default=["INDIGO", "AIR INDIA"],
        metavar="CARRIER",
        help='Carrier whitelist (default: INDIGO "AIR INDIA")',
    )
    p.add_argument(
        "--ota",
        nargs="+",
        default=["mmt", "goibibo"],
        choices=["mmt", "goibibo"],
        dest="ota",
        metavar="OTA",
        help="OTAs to query (default: mmt goibibo)",
    )
    p.add_argument(
        "--out",
        default=os.path.join(os.path.dirname(__file__), "data", "replay_data.csv"),
        help="Output CSV path",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Truncate existing CSV before writing",
    )
    p.add_argument(
        "--no-headless",
        action="store_true",
        dest="no_headless",
        help="Show browser window (useful for debugging)",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        dest="log_level",
        help="Logging verbosity (default: INFO)",
    )
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    )

    harvest(
        routes=args.routes,
        windows=args.windows,
        carriers=args.carriers,
        otas=args.ota,
        out_path=args.out,
        overwrite=args.overwrite,
        headless=not args.no_headless,
    )
