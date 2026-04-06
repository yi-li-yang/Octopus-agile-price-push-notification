"""Generate Octopus-style bar chart of half-hourly prices."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from datetime import datetime
from zoneinfo import ZoneInfo

BG_COLOR = "#1a1438"
BAR_DEFAULT = "#e879c5"
BAR_CHEAP = "#ff6bd6"
BAR_NEGATIVE = "#00d68f"
TEXT_COLOR = "#e0d8f0"
GRID_COLOR = "#ffffff22"


def generate_chart(slots, date_str, avg, timezone="Europe/London", output="chart.png"):
    """Render a 48-bar half-hourly price chart and save to output path."""
    tz = ZoneInfo(timezone)

    hours = []
    prices = []
    for s in slots:
        utc_dt = datetime.fromisoformat(s["valid_from"].replace("Z", "+00:00"))
        local_dt = utc_dt.astimezone(tz)
        hours.append(local_dt.hour + local_dt.minute / 60)
        prices.append(s["value_inc_vat"])

    colors = []
    for p in prices:
        if p < 0:
            colors.append(BAR_NEGATIVE)
        elif p < avg:
            colors.append(BAR_CHEAP)
        else:
            colors.append(BAR_DEFAULT)

    fig, ax = plt.subplots(figsize=(12, 5), dpi=150)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    bar_width = 0.45
    ax.bar(hours, prices, width=bar_width, color=colors, align="edge")

    # Daily average line
    ax.axhline(y=avg, color="white", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.text(
        23.5, avg + 0.5, f"avg: {avg:.1f}p",
        color="white", fontsize=9, ha="right", va="bottom",
    )

    # Axes
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 3))
    ax.set_ylabel("p/kWh", color=TEXT_COLOR, fontsize=10)
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)
    ax.yaxis.grid(True, linestyle="--", color=GRID_COLOR)
    ax.set_axisbelow(True)

    # Spines
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("bottom", "left"):
        ax.spines[spine].set_color("white")
        ax.spines[spine].set_linewidth(0.5)

    ax.set_title(
        f"Agile Octopus \u2014 {date_str}",
        color="white", fontsize=14, loc="left", pad=12,
    )

    fig.tight_layout()
    fig.savefig(output, facecolor=BG_COLOR)
    plt.close(fig)
