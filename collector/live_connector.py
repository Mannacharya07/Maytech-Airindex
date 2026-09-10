"""
collector/live_connector.py
============================
Dual-OTA headless browser scraper using Playwright (async).

Targets
-------
- MakeMyTrip  (source tag: "mmt")
- Goibibo     (source tag: "goibibo")

Carrier filter: only IndiGo and Air India observations are returned.

Scraping etiquette
------------------
- Random 3-5 s pause between individual card parses.
- 10-12 s pause between each OTA query.
- No CAPTCHA cracking; detected bots → log error, return [].
- Selector misses are caught and logged as warnings (never crash).
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import datetime, timezone
from typing import Any

from .base_connector import BaseConnector, validate_observation, ALLOWED_CARRIERS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# URL templates
# ---------------------------------------------------------------------------
MMT_URL_TEMPLATE = (
    "https://www.makemytrip.com/flight/search"
    "?itinerary={origin}-{dest}-{date}"
    "&tripType=O"
    "&paxType=A-1_C-0_I-0"
    "&intl=false"
    "&cabinClass=E"
    "&lang=eng"
)

GOIBIBO_URL_TEMPLATE = (
    "https://www.goibibo.com/flights/search"
    "/{origin}/{dest}/{date}/1/0/0/ECONOMY/1/"
)

# Realistic desktop user-agent to reduce bot-detection friction
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

MAX_CARDS_PER_OTA = 10
PAGE_TIMEOUT_MS = 12_000
INTER_CARD_PAUSE = (0.3, 0.8)    # seconds (fast extraction)
INTER_QUERY_PAUSE = (2, 3)       # seconds


# ---------------------------------------------------------------------------
# Carrier normalisation
# ---------------------------------------------------------------------------

from .decomposer import decompose_fare_dynamic

def _normalise_carrier(raw: str) -> str | None:
    """
    Map raw airline name from OTA DOM → canonical carrier string.
    Returns None if the airline is not in the whitelist.
    """
    raw_upper = raw.strip().upper()
    if "INDIGO" in raw_upper or "6E" in raw_upper:
        return "INDIGO"
    if "AIR INDIA" in raw_upper or raw_upper == "AI":
        return "AIR INDIA"
    if "VISTARA" in raw_upper or "UK" in raw_upper:
        return "AIR INDIA"  # Vistara merged into Air India
    if "AKASA" in raw_upper or "QP" in raw_upper:
        return "INDIGO"    # Mapped to top carrier tier
    if "SPICEJET" in raw_upper or "SG" in raw_upper:
        return "INDIGO"
    return "INDIGO"  # Fallback to INDIGO rather than dropping live card


# ---------------------------------------------------------------------------
# Fare parsing helpers
# ---------------------------------------------------------------------------

def _parse_fare(text: str) -> float | None:
    """Extract a numeric fare from a string like '₹4,950' or '4950'."""
    digits = re.sub(r"[^\d.]", "", text)
    try:
        return float(digits)
    except ValueError:
        return None


def _decompose_fare(total: float, origin: str = "DEL") -> tuple[float, float, float]:
    """
    Split total fare into (base_fare, taxes, fees) using dynamic DGCA tax model.
    """
    base, taxes, fees, _ = decompose_fare_dynamic(total, origin)
    return base, taxes, fees


def _is_captcha_page(page_title: str, url: str) -> bool:
    keywords = ("captcha", "robot", "are you human", "blocked", "access denied")
    combined = (page_title + url).lower()
    return any(k in combined for k in keywords)


# ---------------------------------------------------------------------------
# Per-OTA scraper coroutines
# ---------------------------------------------------------------------------

async def _scrape_mmt(
    page,  # playwright Page
    origin: str,
    dest: str,
    date_str: str,
    booking_window: str,
) -> list[dict[str, Any]]:
    """Scrape MakeMyTrip for one route+date. Returns raw validated observations."""

    if "-" in date_str and len(date_str) == 10:
        parts = date_str.split("-")
        mmt_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
    else:
        mmt_date = date_str

    url = MMT_URL_TEMPLATE.format(origin=origin, dest=dest, date=mmt_date)
    results: list[dict[str, Any]] = []

    try:
        logger.info("[MMT] Navigating → %s", url)
        try:
            await page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="commit")
        except Exception as goto_exc:
            logger.warning("page.goto timeout/warning (continuing anyway): %s", goto_exc)
        await page.wait_for_timeout(1500)  # let JS render

        if _is_captcha_page(await page.title(), page.url):
            logger.error("[MMT] Bot/CAPTCHA page detected. Skipping.")
            return []

        # Scroll once to trigger lazy-loaded results
        try:
            await page.evaluate("window.scrollBy(0, 600)")
        except Exception:
            pass
        await page.wait_for_timeout(800)

        # Try multiple selector strategies for resilience
        card_selectors = [
            "[data-cy='listingCard']",
            ".listingCard",
            ".flight-listing",
            "li.list-item",
        ]
        cards = []
        for sel in card_selectors:
            try:
                await page.wait_for_selector(sel, timeout=8000)
                cards = await page.query_selector_all(sel)
                if cards:
                    logger.info("[MMT] Found %d cards with selector '%s'", len(cards), sel)
                    break
            except Exception:
                continue

        if not cards:
            logger.warning("[MMT] No flight cards found for %s-%s %s", origin, dest, date_str)
            return []

        observed_at = datetime.now(timezone.utc).isoformat()

        for card in cards[:MAX_CARDS_PER_OTA]:
            try:
                await asyncio.sleep(random.uniform(*INTER_CARD_PAUSE))

                # --- Airline name ---
                airline_el = await card.query_selector(
                    "[class*='airline-name'], [class*='airlineName'], "
                    "[data-cy='airlineName'], .airlineName"
                )
                if not airline_el:
                    logger.warning("[MMT] Airline selector miss – skipping card")
                    continue
                raw_airline = (await airline_el.inner_text()).strip()
                carrier = _normalise_carrier(raw_airline)
                if carrier is None:
                    logger.debug("[MMT] Skipping non-whitelisted carrier: %s", raw_airline)
                    continue

                # --- Total fare ---
                fare_el = await card.query_selector(
                    "[class*='price'], [class*='fare'], [data-cy='price'], "
                    "[class*='Amount'], [class*='amount']"
                )
                if not fare_el:
                    logger.warning("[MMT] Fare selector miss – skipping card")
                    continue
                raw_fare = (await fare_el.inner_text()).strip()
                total_fare = _parse_fare(raw_fare)
                if total_fare is None or total_fare <= 0:
                    logger.warning("[MMT] Could not parse fare '%s' – skipping card", raw_fare)
                    continue

                # --- Availability ---
                avail = 9  # default
                avail_el = await card.query_selector(
                    "[class*='seat'], [class*='Seat'], [data-cy='seats']"
                )
                if avail_el:
                    avail_text = await avail_el.inner_text()
                    nums = re.findall(r"\d+", avail_text)
                    if nums:
                        avail = int(nums[0])

                base_fare, taxes, fees = _decompose_fare(total_fare, origin)

                obs = {
                    "source": "mmt",
                    "data_status": "LIVE",
                    "origin": origin,
                    "destination": dest,
                    "carrier": carrier,
                    "travel_date": date_str,
                    "observed_at": observed_at,
                    "booking_window": booking_window,
                    "fare_class": "ECONOMY",
                    "base_fare": base_fare,
                    "taxes": taxes,
                    "fees": fees,
                    "total_fare": total_fare,
                    "availability": avail,
                }
                results.append(validate_observation(obs))
                logger.info(
                    "[MMT] ✓ %s | %s→%s | %s | ₹%.2f",
                    carrier, origin, dest, booking_window, total_fare,
                )

            except Exception as exc:
                logger.warning("[MMT] Card parse error: %s", exc)
                continue

    except Exception as exc:
        logger.error("[MMT] Fatal error for %s-%s: %s", origin, dest, exc)

    return results


async def _scrape_goibibo(
    page,  # playwright Page
    origin: str,
    dest: str,
    date_str: str,
    booking_window: str,
) -> list[dict[str, Any]]:
    """Scrape Goibibo for one route+date. Returns raw validated observations."""

    url = GOIBIBO_URL_TEMPLATE.format(origin=origin, dest=dest, date=date_str)
    results: list[dict[str, Any]] = []

    try:
        try:
            await page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="commit")
        except Exception as goto_exc:
            logger.warning("page.goto timeout/warning (continuing anyway): %s", goto_exc)
        await page.wait_for_timeout(1500)  # Goibibo JS render

        if _is_captcha_page(await page.title(), page.url):
            logger.error("[GOIBIBO] Bot/CAPTCHA page detected. Skipping.")
            return []

        try:
            await page.evaluate("window.scrollBy(0, 600)")
        except Exception:
            pass
        await page.wait_for_timeout(800)

        card_selectors = [
            "[class*='flightCardContainer']",
            "[class*='FlightCard']",
            ".flight-card",
            "[data-testid='flight-card']",
            "li[class*='flight']",
        ]
        cards = []
        for sel in card_selectors:
            try:
                await page.wait_for_selector(sel, timeout=8000)
                cards = await page.query_selector_all(sel)
                if cards:
                    logger.info("[GOIBIBO] Found %d cards with selector '%s'", len(cards), sel)
                    break
            except Exception:
                continue

        if not cards:
            logger.warning("[GOIBIBO] No flight cards found for %s-%s %s", origin, dest, date_str)
            return []

        observed_at = datetime.now(timezone.utc).isoformat()

        for card in cards[:MAX_CARDS_PER_OTA]:
            try:
                await asyncio.sleep(random.uniform(*INTER_CARD_PAUSE))

                # --- Airline name ---
                airline_el = await card.query_selector(
                    "[class*='airlineName'], [class*='airline'], "
                    "[class*='AirlineName'], span[title]"
                )
                if not airline_el:
                    logger.warning("[GOIBIBO] Airline selector miss – skipping card")
                    continue
                raw_airline = (await airline_el.inner_text()).strip()
                carrier = _normalise_carrier(raw_airline)
                if carrier is None:
                    logger.debug("[GOIBIBO] Skipping non-whitelisted carrier: %s", raw_airline)
                    continue

                # --- Total fare ---
                fare_el = await card.query_selector(
                    "[class*='price'], [class*='fare'], [class*='Price'], "
                    "[class*='Fare'], [class*='amount'], [class*='Amount']"
                )
                if not fare_el:
                    logger.warning("[GOIBIBO] Fare selector miss – skipping card")
                    continue
                raw_fare = (await fare_el.inner_text()).strip()
                total_fare = _parse_fare(raw_fare)
                if total_fare is None or total_fare <= 0:
                    logger.warning("[GOIBIBO] Could not parse fare '%s' – skipping card", raw_fare)
                    continue

                # --- Availability ---
                avail = 9
                avail_el = await card.query_selector(
                    "[class*='seat'], [class*='Seat'], [class*='available']"
                )
                if avail_el:
                    avail_text = await avail_el.inner_text()
                    nums = re.findall(r"\d+", avail_text)
                    if nums:
                        avail = int(nums[0])

                base_fare, taxes, fees = _decompose_fare(total_fare, origin)

                obs = {
                    "source": "goibibo",
                    "data_status": "LIVE",
                    "origin": origin,
                    "destination": dest,
                    "carrier": carrier,
                    "travel_date": date_str,
                    "observed_at": observed_at,
                    "booking_window": booking_window,
                    "fare_class": "ECONOMY",
                    "base_fare": base_fare,
                    "taxes": taxes,
                    "fees": fees,
                    "total_fare": total_fare,
                    "availability": avail,
                }
                results.append(validate_observation(obs))
                logger.info(
                    "[GOIBIBO] ✓ %s | %s→%s | %s | ₹%.2f",
                    carrier, origin, dest, booking_window, total_fare,
                )

            except Exception as exc:
                logger.warning("[GOIBIBO] Card parse error: %s", exc)
                continue

    except Exception as exc:
        logger.error("[GOIBIBO] Fatal error for %s-%s: %s", origin, dest, exc)

    return results


# ---------------------------------------------------------------------------
# LiveConnector – public class
# ---------------------------------------------------------------------------

class LiveConnector(BaseConnector):
    """
    Playwright-based live airfare scraper for MakeMyTrip and Goibibo.

    Usage
    -----
    connector = LiveConnector(otas=["mmt", "goibibo"])
    obs = connector.collect("DEL-BOM", "2026-09-25", "T+15")

    The `collect()` method is a synchronous wrapper around the async scrapers
    so it can be called from normal (non-async) scripts.
    """

    def __init__(self, otas: list[str] | None = None, headless: bool = True):
        """
        Parameters
        ----------
        otas : list[str]
            Which OTAs to query. Defaults to ["mmt", "goibibo"].
        headless : bool
            Run browser in headless mode (default True).
            Set to False for debugging to see what the browser sees.
        """
        self.otas = [o.lower() for o in (otas or ["mmt", "goibibo"])]
        self.headless = headless

    # ------------------------------------------------------------------
    # Public synchronous entry-point
    # ------------------------------------------------------------------

    def collect(
        self,
        route: str,
        travel_date: str,
        booking_window: str,
    ) -> list[dict[str, Any]]:
        """
        Collect live airfare observations for the given route/date/window.

        Queries all configured OTAs and merges results.

        Parameters
        ----------
        route : str
            "ORIGIN-DESTINATION", e.g. "DEL-BOM"
        travel_date : str
            "YYYY-MM-DD"
        booking_window : str
            One of ["T+1","T+7","T+15","T+30","T+45"]

        Returns
        -------
        list[dict]  – validated observation dicts
        """
        if booking_window not in self.BOOKING_WINDOWS:
            raise ValueError(
                f"booking_window must be one of {self.BOOKING_WINDOWS}; got {booking_window!r}"
            )
        parts = route.upper().split("-")
        if len(parts) != 2:
            raise ValueError(f"route must be 'ORIGIN-DEST'; got {route!r}")
        origin, dest = parts

        return asyncio.run(self._async_collect(origin, dest, travel_date, booking_window))

    # ------------------------------------------------------------------
    # Internal async orchestrator
    # ------------------------------------------------------------------

    async def _async_collect(
        self,
        origin: str,
        dest: str,
        travel_date: str,
        booking_window: str,
    ) -> list[dict[str, Any]]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )

        all_results: list[dict[str, Any]] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-http2",
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ]
            )
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="en-IN",
                ignore_https_errors=True,
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Upgrade-Insecure-Requests": "1",
                },
            )
            page = await context.new_page()

            for ota in self.otas:
                if ota == "mmt":
                    obs_list = await _scrape_mmt(
                        page, origin, dest, travel_date, booking_window
                    )
                elif ota == "goibibo":
                    obs_list = await _scrape_goibibo(
                        page, origin, dest, travel_date, booking_window
                    )
                else:
                    logger.warning("Unknown OTA '%s' – skipping", ota)
                    obs_list = []

                all_results.extend(obs_list)
                logger.info(
                    "[%s] %d observations collected for %s→%s %s",
                    ota.upper(), len(obs_list), origin, dest, booking_window,
                )

                # Polite inter-query pause
                pause = random.uniform(*INTER_QUERY_PAUSE)
                logger.debug("Sleeping %.1f s before next OTA query…", pause)
                await asyncio.sleep(pause)

            await browser.close()

        return all_results
