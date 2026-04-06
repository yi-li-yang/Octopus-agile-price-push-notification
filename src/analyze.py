"""Price analysis: averages, below-average ranges, negative detection."""

from datetime import datetime
from zoneinfo import ZoneInfo


def daily_average(slots):
    """Compute mean value_inc_vat across all slots."""
    if not slots:
        return 0.0
    return sum(s["value_inc_vat"] for s in slots) / len(slots)


def _local_hour(valid_from, tz_name):
    """Extract local hour from a UTC ISO 8601 timestamp string."""
    utc_dt = datetime.fromisoformat(valid_from.replace("Z", "+00:00"))
    return utc_dt.astimezone(ZoneInfo(tz_name)).hour


def below_average_hours(slots, avg=None, timezone="Europe/London"):
    """Group slots into hourly buckets, find below-average hours, collapse ranges.

    Returns list of (start_hour, end_hour, range_avg_price) tuples.
    end_hour is exclusive (e.g. (0, 6, 5.9) means 00:00-06:00).
    """
    if avg is None:
        avg = daily_average(slots)

    # Group into hourly buckets
    hourly = {}
    for s in slots:
        hour = _local_hour(s["valid_from"], timezone)
        hourly.setdefault(hour, []).append(s["value_inc_vat"])

    # Find below-average hours sorted
    below = sorted(
        h for h, vals in hourly.items() if sum(vals) / len(vals) < avg
    )

    if not below:
        return []

    # Collapse contiguous hours into ranges
    ranges = []
    start = prev = below[0]
    for h in below[1:]:
        if h == prev + 1:
            prev = h
        else:
            _append_range(ranges, start, prev, hourly)
            start = prev = h
    _append_range(ranges, start, prev, hourly)

    return ranges


def _append_range(ranges, start, end, hourly):
    """Append a (start_hour, end_hour+1, avg_price) tuple to ranges."""
    prices = []
    for h in range(start, end + 1):
        prices.extend(hourly[h])
    ranges.append((start, end + 1, sum(prices) / len(prices)))


def detect_negative(slots):
    """Return slots with negative value_inc_vat, in original order."""
    return [s for s in slots if s["value_inc_vat"] < 0]
