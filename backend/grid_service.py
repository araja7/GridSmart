import csv
import os
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

from models import PricePoint

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "ohio_hub_prices.csv"
CACHE_TTL_SECONDS = 300
ELECZ_BASE_URL = "https://elecz.com"

_cache: dict | None = None
_cache_time: float = 0.0

# Elecz zone code (see https://elecz.com/docs). US-CA-SP15 = California day-ahead.
ELECZ_ZONE = os.getenv("ELECZ_ZONE", "US-CA-SP15")


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


def _parse_elecz_hour(ts: str) -> int:
    normalized = str(ts).replace(" ", "T")
    if len(normalized) == 16:
        normalized += ":00"
    return datetime.fromisoformat(normalized).hour


def _fetch_elecz_prices() -> tuple[list[PricePoint], str] | None:
    """Fetch next-24h hourly prices from Elecz (no API key). See https://elecz.com/docs"""
    url = f"{ELECZ_BASE_URL}/signal/cheapest-hours"
    params = {"zone": ELECZ_ZONE, "hours": 24}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None

    if not data.get("available"):
        return None

    entries = data.get("cheapest_hours") or []
    if len(entries) < 8:
        return None

    by_hour: dict[int, tuple[float, str | None]] = {}
    for entry in entries:
        hour_key = entry.get("hour")
        price_val = entry.get("price")
        if hour_key is None or price_val is None:
            continue
        try:
            clock_hour = _parse_elecz_hour(hour_key)
            # Elecz returns cents/kWh; scheduler uses currency per kWh
            price_per_kwh = float(price_val) / 100.0
            by_hour[clock_hour] = (price_per_kwh, str(hour_key))
        except (ValueError, TypeError):
            continue

    if len(by_hour) < 8:
        return None

    fill_value = sum(p for p, _ in by_hour.values()) / len(by_hour)
    today = datetime.now().replace(minute=0, second=0, microsecond=0)
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

    zone = data.get("zone", ELECZ_ZONE)
    return prices, zone


def get_current_prices() -> tuple[list[PricePoint], str, bool]:
    global _cache, _cache_time

    now = time.time()
    if _cache and (now - _cache_time) < CACHE_TTL_SECONDS:
        return _cache["prices"], _cache["source"], True

    elecz = _fetch_elecz_prices()
    if elecz:
        prices, zone = elecz
        source = f"elecz_api:{zone}"
    else:
        source = "csv_fallback"
        prices = _load_csv_prices()

    _cache = {"prices": prices, "source": source}
    _cache_time = now
    return prices, source, False
