"""Compose and send the daily Agile price email."""

import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo


def _format_time(hour):
    """Format hour integer as HH:00."""
    return f"{hour:02d}:00"


def _format_slot_range(valid_from, timezone):
    """Return (start_str, end_str) like ('13:00', '13:30') in local time."""
    tz = ZoneInfo(timezone)
    utc_dt = datetime.fromisoformat(valid_from.replace("Z", "+00:00"))
    start = utc_dt.astimezone(tz)
    end = (utc_dt + timedelta(minutes=30)).astimezone(tz)
    return start.strftime("%H:%M"), end.strftime("%H:%M")


def compose_email(date_str, avg, ranges, negatives,
                  product_code=None, tariff_code=None, timezone=None):
    """Build an EmailMessage with plain text + HTML + chart attachment."""
    product_code = product_code or os.environ.get("PRODUCT_CODE") or "AGILE-24-10-01"
    tariff_code = tariff_code or os.environ.get("TARIFF_CODE") or "E-1R-AGILE-24-10-01-C"
    timezone = timezone or os.environ.get("TIMEZONE") or "Europe/London"
    region_letter = tariff_code[-1] if tariff_code else "C"

    has_negative = len(negatives) > 0

    # Subject
    if has_negative:
        subject = (
            f"\u26a1 Agile Octopus \u2014 {date_str} "
            f"\u2014 NEGATIVE PRICES \u2014 avg {avg:.1f}p"
        )
    else:
        subject = f"Agile Octopus \u2014 {date_str} \u2014 avg {avg:.1f}p"

    # Negative-price section
    neg_section = ""
    if has_negative:
        neg_lines = ["\u26a1 NEGATIVE PRICES TOMORROW \u26a1"]
        for s in negatives:
            start_str, end_str = _format_slot_range(s["valid_from"], timezone)
            neg_lines.append(
                f"  {start_str}\u2013{end_str}   {s['value_inc_vat']:.1f} p/kWh"
            )
        neg_section = "\n".join(neg_lines) + "\n"

    # Below-average ranges section
    range_lines = []
    for start_h, end_h, range_avg in ranges:
        range_lines.append(
            f"  {_format_time(start_h)}\u2013{_format_time(end_h)}"
            f"   \u2192   {range_avg:.1f} p/kWh"
        )
    ranges_text = "\n".join(range_lines)

    # Plain text body
    plain = ""
    if neg_section:
        plain += neg_section + "\n"
    plain += f"Daily average: {avg:.1f} p/kWh\n\n"
    plain += f"Below-average windows:\n{ranges_text}\n\n"
    plain += f"---\nAgile Octopus \u00b7 Region {region_letter} \u00b7 Product {product_code}"

    # HTML body
    html_ranges = ranges_text.replace("\n", "<br>\n")
    html_neg = ""
    if neg_section:
        html_neg_content = neg_section.replace("\n", "<br>")
        html_neg = (
            f"<p style='color:#00d68f;font-weight:bold;'>"
            f"{html_neg_content}</p>"
        )

    html = (
        "<html><body style=\"background:#1a1438;color:#e0d8f0;"
        "font-family:monospace;padding:20px;\">\n"
        "<img src=\"cid:chart\" style=\"max-width:100%;margin-bottom:20px;\">\n"
        f"{html_neg}\n"
        f"<p>Daily average: <strong>{avg:.1f} p/kWh</strong></p>\n"
        f"<p>Below-average windows:<br>\n{html_ranges}</p>\n"
        "<hr style=\"border-color:#ffffff22;\">\n"
        f"<p style=\"font-size:0.8em;color:#888;\">Agile Octopus \u00b7 "
        f"Region {region_letter} \u00b7 Product {product_code}</p>\n"
        "</body></html>"
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")

    # Attach chart inline (cid) and as downloadable attachment
    chart_path = Path("chart.png")
    if chart_path.exists():
        chart_data = chart_path.read_bytes()
        msg.get_payload()[1].add_related(
            chart_data, maintype="image", subtype="png", cid="chart",
        )
        msg.add_attachment(
            chart_data, maintype="image", subtype="png", filename="chart.png",
        )

    return msg


def _smtp_send(msg):
    """Send an EmailMessage via SMTP using env-var credentials."""
    host = os.environ["SMTP_HOST"]
    port = int(os.environ["SMTP_PORT"])
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]

    if port == 465:
        with smtplib.SMTP_SSL(host, port) as server:
            server.login(user, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)


def send_email(date_str, avg, ranges, negatives):
    """Compose and send the daily email to all recipients."""
    msg = compose_email(date_str, avg, ranges, negatives)

    sender = os.environ.get("SENDER_EMAIL") or os.environ.get("SMTP_USER") or ""
    recipients = [r.strip() for r in os.environ["RECIPIENTS"].split(",") if r.strip()]

    msg["From"] = sender
    msg["To"] = sender
    msg["Bcc"] = ", ".join(recipients)

    _smtp_send(msg)
    return len(recipients)


def send_fallback(date_str):
    """Send a fallback email when prices haven't been published."""
    sender = os.environ.get("SENDER_EMAIL") or os.environ.get("SMTP_USER") or ""
    recipients = [r.strip() for r in os.environ["RECIPIENTS"].split(",") if r.strip()]

    msg = EmailMessage()
    msg["Subject"] = (
        f"Agile Octopus \u2014 {date_str} \u2014 prices not yet published"
    )
    msg["From"] = sender
    msg["To"] = sender
    msg["Bcc"] = ", ".join(recipients)
    msg.set_content(
        f"Agile Octopus prices for {date_str} have not been published yet.\n"
        "Check the Octopus app for updates.\n"
    )

    _smtp_send(msg)
    return len(recipients)
