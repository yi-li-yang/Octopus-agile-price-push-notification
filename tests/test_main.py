from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.main import expected_slot_count

LONDON = ZoneInfo("Europe/London")


@pytest.mark.parametrize(
    "day, expected",
    [
        ("2026-07-15", 46),  # summer time
        ("2026-11-11", 46),  # winter time
        ("2026-10-25", 48),  # clocks go back
        ("2027-03-28", 44),  # clocks go forward
    ],
)
def test_expected_slot_count(day, expected):
    target = datetime.fromisoformat(f"{day}T18:00").replace(tzinfo=LONDON)
    assert expected_slot_count(target) == expected
