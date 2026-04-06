"""Entry point: fetch prices, analyze, chart, email."""

import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import fetch, analyze, chart, email_sender

SENT_MARKER_DIR = Path(".sent_markers")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def _load_dotenv():
    """Load .env file if present (local dev convenience)."""
    env_file = Path(".env")
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key:
            os.environ.setdefault(key, value)


def main():
    _load_dotenv()

    timezone = os.environ.get("TIMEZONE") or "Europe/London"
    tz = ZoneInfo(timezone)
    tomorrow = datetime.now(tz) + timedelta(days=1)
    tomorrow_iso = tomorrow.strftime("%Y-%m-%d")
    date_display = tomorrow.strftime("%a") + f" {tomorrow.day} " + tomorrow.strftime("%b")

    # Check sent marker
    SENT_MARKER_DIR.mkdir(exist_ok=True)
    marker = SENT_MARKER_DIR / f"sent-{tomorrow_iso}"
    if marker.exists():
        log.info("Already sent for %s, skipping", tomorrow_iso)
        return

    # Fetch prices
    log.info("Fetching prices for %s", tomorrow_iso)
    slots = fetch.fetch_prices(timezone=timezone)

    # During BST (UTC+1) the last hour of a London day falls in the next UTC day
    # and isn't published yet, so the API returns 46 slots instead of 48.
    offset_slots = int(tomorrow.utcoffset().total_seconds() // 1800)
    expected_slots = 48 - offset_slots
    log.info("Got %d slots, expecting %d (UTC offset: %s)", len(slots), expected_slots, tomorrow.utcoffset())

    if len(slots) < expected_slots:
        is_last_run = os.environ.get("IS_LAST_RUN", "").lower() == "true"
        if is_last_run:
            fallback_marker = SENT_MARKER_DIR / f"fallback-{tomorrow_iso}"
            if fallback_marker.exists():
                log.info("Fallback already sent for %s, skipping", tomorrow_iso)
            else:
                log.warning("Prices not published by final run, sending fallback")
                email_sender.send_fallback(date_display)
                fallback_marker.write_text("fallback")
        else:
            log.info("Only %d slots, prices not yet published", len(slots))
        return

    # Analyze
    avg = analyze.daily_average(slots)
    ranges = analyze.below_average_hours(slots, avg, timezone)
    negatives = analyze.detect_negative(slots)

    log.info(
        "Daily avg: %.1f p/kWh, %d below-avg ranges, %d negative slots",
        avg, len(ranges), len(negatives),
    )

    # Generate chart
    chart.generate_chart(slots, date_display, avg, timezone)
    log.info("Chart saved to chart.png")

    # Send email
    n = email_sender.send_email(date_display, avg, ranges, negatives)
    marker.write_text("sent")
    log.info("Email sent to %d recipients for %s", n, tomorrow_iso)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Fatal error")
        sys.exit(1)
