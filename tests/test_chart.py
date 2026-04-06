"""Smoke test for chart generation."""

import json
from pathlib import Path

from src.analyze import daily_average
from src.chart import generate_chart

FIXTURE = Path(__file__).parent / "fixtures" / "sample_response.json"


def test_chart_generates_png(tmp_path):
    data = json.loads(FIXTURE.read_text())
    slots = sorted(data["results"], key=lambda s: s["valid_from"])
    avg = daily_average(slots)

    output = tmp_path / "chart.png"
    generate_chart(slots, "Wed 8 Apr", avg, "Europe/London", str(output))

    assert output.exists()
    assert output.stat().st_size > 0
    # Verify it starts with PNG magic bytes
    assert output.read_bytes()[:4] == b"\x89PNG"
