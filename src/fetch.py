"""Octopus Agile API client."""

import os

import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def fetch_prices(product_code=None, tariff_code=None, timezone=None):
    """Fetch tomorrow's half-hourly Agile prices from the Octopus API.

    Returns a list of slot dicts sorted ascending by valid_from.
    """
    product_code = product_code or os.environ.get("PRODUCT_CODE") or "AGILE-24-10-01"
    tariff_code = tariff_code or os.environ.get("TARIFF_CODE") or "E-1R-AGILE-24-10-01-C"
    timezone = timezone or os.environ.get("TIMEZONE") or "Europe/London"

    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    day_after = tomorrow + timedelta(days=1)

    utc = ZoneInfo("UTC")
    url = (
        f"https://api.octopus.energy/v1/products/{product_code}"
        f"/electricity-tariffs/{tariff_code}/standard-unit-rates/"
    )
    params = {
        "period_from": tomorrow.astimezone(utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "period_to": day_after.astimezone(utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    slots = data.get("results", [])
    slots.sort(key=lambda s: s["valid_from"])
    return slots
