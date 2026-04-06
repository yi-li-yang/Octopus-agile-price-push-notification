"""Tests for src.analyze — pure functions, no network."""

import json
from pathlib import Path

from src.analyze import daily_average, below_average_hours, detect_negative

FIXTURE = Path(__file__).parent / "fixtures" / "sample_response.json"
# Fixture uses BST dates (UTC+1), so analysis should use Europe/London
TZ = "Europe/London"


def _load_slots():
    data = json.loads(FIXTURE.read_text())
    slots = data["results"]
    slots.sort(key=lambda s: s["valid_from"])
    return slots


# --- daily_average ---

def test_daily_average():
    slots = _load_slots()
    avg = daily_average(slots)
    # Hand-computed: sum=584.8, count=48, avg~12.183
    assert abs(avg - 12.183) < 0.01


def test_daily_average_empty():
    assert daily_average([]) == 0.0


# --- below_average_hours ---

def test_below_average_hours_fixture():
    slots = _load_slots()
    avg = daily_average(slots)
    ranges = below_average_hours(slots, avg, TZ)

    # Expected ranges: 00-06, 11-15, 22-24
    assert len(ranges) == 3

    starts = [r[0] for r in ranges]
    ends = [r[1] for r in ranges]
    assert starts == [0, 11, 22]
    assert ends == [6, 15, 24]

    # Each range avg should be below daily avg
    for _, _, price in ranges:
        assert price < avg


def test_below_average_hours_range_prices():
    slots = _load_slots()
    avg = daily_average(slots)
    ranges = below_average_hours(slots, avg, TZ)

    # 00:00-06:00 range avg = 70.5/12 = 5.875
    assert abs(ranges[0][2] - 5.875) < 0.01
    # 11:00-15:00 range avg = 55.0/8 = 6.875
    assert abs(ranges[1][2] - 6.875) < 0.01
    # 22:00-24:00 range avg = 41.0/4 = 10.25
    assert abs(ranges[2][2] - 10.25) < 0.01


def test_below_average_all_identical():
    """When all prices are identical, no hours are below average."""
    slots = [
        {"value_inc_vat": 10.0, "valid_from": f"2026-04-08T{h:02d}:{m:02d}:00Z"}
        for h in range(24)
        for m in (0, 30)
    ]
    avg = daily_average(slots)
    assert avg == 10.0
    ranges = below_average_hours(slots, avg, "UTC")
    assert ranges == []


# --- detect_negative ---

def test_detect_negative_fixture():
    slots = _load_slots()
    neg = detect_negative(slots)
    assert len(neg) == 2
    assert all(s["value_inc_vat"] < 0 for s in neg)
    # First negative is -2.4 (local 13:00), second is -1.1 (local 13:30)
    assert neg[0]["value_inc_vat"] == -2.4
    assert neg[1]["value_inc_vat"] == -1.1


def test_detect_negative_none():
    slots = [{"value_inc_vat": 5.0, "valid_from": "2026-04-08T00:00:00Z"}]
    assert detect_negative(slots) == []


def test_detect_negative_single():
    """Edge case: 48 slots with exactly one negative."""
    slots = []
    for h in range(24):
        for m in (0, 30):
            val = 15.0
            if h == 3 and m == 0:
                val = -5.0
            slots.append({
                "value_inc_vat": val,
                "valid_from": f"2026-04-08T{h:02d}:{m:02d}:00Z",
            })
    neg = detect_negative(slots)
    assert len(neg) == 1
    assert neg[0]["value_inc_vat"] == -5.0
