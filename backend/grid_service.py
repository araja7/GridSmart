import csv
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv

from models import PricePoint

load_dotenv()

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "ohio_hub_prices.csv"
CACHE_TTL_SECONDS = 300
ELECZ_BASE_URL = "https://elecz.com"
ELECZ_RETRIES = 3
ELECZ_RETRY_DELAY_SECONDS = 0.5

# Elecz zone code (see https://elecz.com/docs). US-CA-SP15 = California day-ahead.
ELECZ_ZONE = os.getenv("ELECZ_ZONE", "US-CA-SP15")
MIN_FULL_LIVE_HOURS = int(os.getenv("ELECZ_MIN_FULL_HOURS", "20"))
MIN_PARTIAL_HOURS = int(os.getenv("ELECZ_MIN_PARTIAL_HOURS", "4"))
ELECZ_STRICT = os.getenv("ELECZ_STRICT", "").lower() in ("1", "true", "yes")

_cache: dict | None = None
_cache_time: float = 0.0


@dataclass
class PriceBundle:
    prices: list[PricePoint]
    source: str
    cached: bool
    live: bool
    partial: bool
    elecz_attempted: bool
    elecz_zone: str | None = None
    elecz_hours_returned: int | None = None
    elecz_hours_real: int | None = None
    elecz_data_complete: bool | None = None
    fallback_reason: str | None = None
    filled_hours: int | None = None


def _market_timezone(zone: str) -> ZoneInfo:
    if zone.startswith("US-CA"):
        return ZoneInfo("America/Los_Angeles")
    if zone.startswith("US-TX"):
        return ZoneInfo("America/Chicago")
    if zone.startswith("US-NY"):
        return ZoneInfo("America/New_York")
    if zone.startswith("CA-ON"):
        return ZoneInfo("America/Toronto")
    if zone == "GB" or zone.startswith("GB-"):
        return ZoneInfo("Europe/London")
    if zone.startswith("AU-"):
        return ZoneInfo("Australia/Sydney")
    if zone.startswith("NZ-"):
        return ZoneInfo("Pacific/Auckland")
    if zone.startswith("JP-"):
        return ZoneInfo("Asia/Tokyo")
    if zone in ("KR", "KR-JEJU"):
        return ZoneInfo("Asia/Seoul")
    return ZoneInfo("Europe/Berlin")


def _load_csv_prices() -> list[PricePoint]:
    if not CSV_PATH.exists():
        return _synthetic_prices()

    prices: list[PricePoint] = []
    with CSV_PATH.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prices.append(
                PricePoint(
                    hour=int(row["hour"]),
                    price_per_kwh=float(row["price_per_kwh"]),
                    timestamp=row.get("timestamp") or None,
                )
            )
    prices.sort(key=lambda p: p.hour)
    return prices


def _synthetic_prices() -> list[PricePoint]:
    """Typical daily wholesale shape: low overnight, peak afternoon."""
    base = [
        0.045, 0.042, 0.040, 0.039, 0.038, 0.040,
        0.048, 0.055, 0.062, 0.068, 0.072, 0.075,
        0.078, 0.082, 0.088, 0.095, 0.102, 0.110,
        0.105, 0.092, 0.078, 0.065, 0.055, 0.048,
    ]
    today = datetime.now().replace(minute=0, second=0, microsecond=0)
    return [
        PricePoint(
            hour=h,
            price_per_kwh=base[h],
            timestamp=today.replace(hour=h).isoformat(),
        )
        for h in range(24)
    ]


def _parse_elecz_hour(ts: str, zone: str) -> int:
    """Map an Elecz timestamp to local market hour (0–23)."""
    normalized = str(ts).replace(" ", "T")
    if len(normalized) == 16:
        normalized += ":00"
    dt = datetime.fromisoformat(normalized)
    tz = _market_timezone(zone)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz).hour


def _fetch_elecz_json() -> dict | None:
    url = f"{ELECZ_BASE_URL}/signal/cheapest-hours"
    params = {"zone": ELECZ_ZONE, "hours": 24}
    last_error: Exception | None = None

    for attempt in range(1, ELECZ_RETRIES + 1):
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt < ELECZ_RETRIES:
                time.sleep(ELECZ_RETRY_DELAY_SECONDS)

    logger.warning(
        "Elecz fetch failed after %s attempts for zone=%s: %s",
        ELECZ_RETRIES,
        ELECZ_ZONE,
        last_error,
    )
    return None


def _build_prices_from_elecz(data: dict) -> tuple[list[PricePoint], str, int, bool] | None:
    """
    Parse Elecz cheapest-hours payload into 24 hourly PricePoints.
    Returns (prices, zone, real_hour_count, data_complete) or None if unusable.
    """
    if not data.get("available"):
        return None

    zone = data.get("zone", ELECZ_ZONE)
    data_complete = bool(data.get("data_complete"))
    entries = data.get("cheapest_hours") or []

    by_hour: dict[int, tuple[float, str | None]] = {}
    for entry in entries:
        hour_key = entry.get("hour")
        price_val = entry.get("price")
        if hour_key is None or price_val is None:
            continue
        try:
            clock_hour = _parse_elecz_hour(hour_key, zone)
            price_per_kwh = float(price_val) / 100.0
            by_hour[clock_hour] = (price_per_kwh, str(hour_key))
        except (ValueError, TypeError):
            continue

    real_hours = len(by_hour)
    if real_hours < MIN_PARTIAL_HOURS:
        logger.info(
            "Elecz zone=%s returned %s parsed hours (need >= %s); data_complete=%s",
            zone,
            real_hours,
            MIN_PARTIAL_HOURS,
            data_complete,
        )
        return None

    fill_value = sum(p for p, _ in by_hour.values()) / real_hours
    tz = _market_timezone(zone)
    today = datetime.now(tz).replace(minute=0, second=0, microsecond=0)
    prices: list[PricePoint] = []

    for h in range(24):
        if h in by_hour:
            price_per_kwh, ts = by_hour[h]
        else:
            price_per_kwh, ts = fill_value, today.replace(hour=h).isoformat()

        prices.append(
            PricePoint(
                hour=h,
                price_per_kwh=price_per_kwh,
                timestamp=ts,
            )
        )

    return prices, zone, real_hours, data_complete


def _is_full_live(real_hours: int, data_complete: bool) -> bool:
    if real_hours >= MIN_FULL_LIVE_HOURS:
        return True
    return data_complete and real_hours >= MIN_PARTIAL_HOURS


def _fetch_elecz_bundle() -> PriceBundle | None:
    data = _fetch_elecz_json()
    if not data:
        return None

    parsed = _build_prices_from_elecz(data)
    if not parsed:
        return None

    prices, zone, real_hours, data_complete = parsed
    entries = data.get("cheapest_hours") or []
    filled_hours = 24 - real_hours
    full_live = _is_full_live(real_hours, data_complete)

    if full_live:
        source = f"elecz_api:{zone}"
        return PriceBundle(
            prices=prices,
            source=source,
            cached=False,
            live=True,
            partial=False,
            elecz_attempted=True,
            elecz_zone=zone,
            elecz_hours_returned=len(entries),
            elecz_hours_real=real_hours,
            elecz_data_complete=data_complete,
            fallback_reason=None,
            filled_hours=filled_hours,
        )

    source = f"elecz_partial:{zone}"
    return PriceBundle(
        prices=prices,
        source=source,
        cached=False,
        live=False,
        partial=True,
        elecz_attempted=True,
        elecz_zone=zone,
        elecz_hours_returned=len(entries),
        elecz_hours_real=real_hours,
        elecz_data_complete=data_complete,
        fallback_reason="incomplete_hourly_coverage",
        filled_hours=filled_hours,
    )


def _csv_bundle(reason: str) -> PriceBundle:
    return PriceBundle(
        prices=_load_csv_prices(),
        source="csv_fallback",
        cached=False,
        live=False,
        partial=False,
        elecz_attempted=True,
        elecz_zone=ELECZ_ZONE,
        elecz_hours_returned=None,
        elecz_hours_real=None,
        elecz_data_complete=None,
        fallback_reason=reason,
        filled_hours=None,
    )


def _bundle_from_cache() -> PriceBundle:
    meta = _cache["meta"]
    return PriceBundle(
        prices=_cache["prices"],
        source=meta["source"],
        cached=True,
        live=meta["live"],
        partial=meta["partial"],
        elecz_attempted=meta["elecz_attempted"],
        elecz_zone=meta.get("elecz_zone"),
        elecz_hours_returned=meta.get("elecz_hours_returned"),
        elecz_hours_real=meta.get("elecz_hours_real"),
        elecz_data_complete=meta.get("elecz_data_complete"),
        fallback_reason=meta.get("fallback_reason"),
        filled_hours=meta.get("filled_hours"),
    )


def _cache_elecz(bundle: PriceBundle) -> None:
    global _cache, _cache_time
    _cache = {
        "is_elecz": True,
        "prices": bundle.prices,
        "meta": {
            "source": bundle.source,
            "live": bundle.live,
            "partial": bundle.partial,
            "elecz_attempted": bundle.elecz_attempted,
            "elecz_zone": bundle.elecz_zone,
            "elecz_hours_returned": bundle.elecz_hours_returned,
            "elecz_hours_real": bundle.elecz_hours_real,
            "elecz_data_complete": bundle.elecz_data_complete,
            "fallback_reason": bundle.fallback_reason,
            "filled_hours": bundle.filled_hours,
        },
    }
    _cache_time = time.time()


def get_current_prices() -> PriceBundle:
    global _cache, _cache_time

    now = time.time()
    if _cache and _cache.get("is_elecz") and (now - _cache_time) < CACHE_TTL_SECONDS:
        return _bundle_from_cache()

    elecz = _fetch_elecz_bundle()
    if elecz:
        _cache_elecz(elecz)
        return elecz

    if _cache and _cache.get("is_elecz"):
        stale = _bundle_from_cache()
        stale.fallback_reason = "elecz_unavailable_serving_stale"
        logger.warning(
            "Elecz unavailable; serving stale cache (age %.0fs)",
            now - _cache_time,
        )
        return stale

    reason = "elecz_unavailable"
    logger.warning("Elecz unavailable for zone=%s; using CSV fallback", ELECZ_ZONE)
    return _csv_bundle(reason)


def require_live_prices(bundle: PriceBundle) -> None:
    """Raise ValueError when ELECZ_STRICT is set and prices are not from Elecz."""
    if not ELECZ_STRICT:
        return
    if bundle.live or bundle.partial:
        return
    raise ValueError(
        bundle.fallback_reason or "Live grid prices unavailable; refusing CSV fallback"
    )
