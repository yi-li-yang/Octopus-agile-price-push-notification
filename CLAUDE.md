# Agile Octopus Daily Price Notifier

A small automation that fetches tomorrow's Agile Octopus half-hourly electricity prices, generates an Octopus-style bar chart, computes the daily average, and emails the result to a configurable list of recipients every evening.

Runs on **GitHub Actions** (free tier, no server needed).

---

## 1. Goal

Every day at ~17:00 London time (after Octopus publishes the next day's prices), send an email to a configurable list of recipients containing:

1. **A bar chart** (PNG attachment + inline) of the next day's 48 half-hourly prices, styled to resemble the Octopus mobile app.
2. **The daily average price** (p/kWh).
3. **The list of hours whose hourly average is below the daily average** — these are the "cheap hours" worth scheduling laundry, dishwasher, cooking into.
4. **Special handling for negative prices** (see §6).

The email body should be **minimal** — chart + a few short lines. No long text.

---

## 2. Data source

Octopus public REST API (no auth required).

**Endpoint:**
```
GET https://api.octopus.energy/v1/products/{PRODUCT_CODE}/electricity-tariffs/{TARIFF_CODE}/standard-unit-rates/
```

**Defaults (London / Region C):**
- `PRODUCT_CODE`: `AGILE-24-10-01`
- `TARIFF_CODE`: `E-1R-AGILE-24-10-01-C`

⚠️ Octopus periodically releases new product versions (e.g. `AGILE-25-XX-XX`). Make these two values **environment variables** with the above as defaults so they can be updated without a code change.

**Query params:** use `period_from` and `period_to` to fetch exactly tomorrow's window:
- `period_from = tomorrow 00:00 Europe/London` (converted to UTC ISO 8601)
- `period_to = day-after-tomorrow 00:00 Europe/London` (converted to UTC ISO 8601)

**Response shape:**
```json
{
  "count": 48,
  "results": [
    {
      "value_exc_vat": 12.34,
      "value_inc_vat": 12.957,
      "valid_from": "2026-04-07T00:00:00Z",
      "valid_to":   "2026-04-07T00:30:00Z"
    },
    ...
  ]
}
```

Use `value_inc_vat` for everything (the user pays VAT). Results come back **newest-first** — sort ascending by `valid_from` before plotting.

**If fewer than 48 slots are returned**, the next day's prices haven't been published yet. Retry policy: see §7.

---

## 3. Configuration

All config via **environment variables / GitHub Actions secrets**. No hardcoded values.

| Variable | Required | Description |
|---|---|---|
| `RECIPIENTS` | yes | Comma-separated email addresses, e.g. `a@x.com,b@y.com` |
| `SMTP_HOST` | yes | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | yes | e.g. `587` |
| `SMTP_USER` | yes | sender email / username |
| `SMTP_PASSWORD` | yes | SMTP password or app-password |
| `SENDER_EMAIL` | no | defaults to `SMTP_USER` |
| `PRODUCT_CODE` | no | default `AGILE-24-10-01` |
| `TARIFF_CODE` | no | default `E-1R-AGILE-24-10-01-C` |
| `TIMEZONE` | no | default `Europe/London` |

The recipient list **must** support an arbitrary number of addresses (not hardcoded to 1 or 2). Send as **BCC** so recipients don't see each other.

---

## 4. Chart specification

Generate with `matplotlib`. Style should resemble the Octopus app (dark theme, pink bars). Reference: the user's Flexible Octopus screenshot — same visual language.

**Style requirements:**
- Figure size: `12 x 5` inches, `dpi=150`
- Background: dark navy `#1a1438` (figure + axes)
- Bars: 48 half-hourly bars
  - Default colour: pink/magenta `#e879c5`
  - **Hours below daily average**: same pink but slightly brighter / fully saturated `#ff6bd6`
  - **Negative-price slots**: green `#00d68f` (clearly distinct)
  - **Peak slots above 1.5× average**: a muted variant or just leave default — design decision: keep it simple, only highlight cheap + negative
- Bar width: ~0.9 of slot width, no gaps look (mimic the app)
- X-axis: hours `0, 3, 6, 9, 12, 15, 18, 21, 24`, white text
- Y-axis: `p/kWh`, white text, gridlines as dashed light-grey `#ffffff22`
- **Daily average**: dashed horizontal white line across the chart, with a label `avg: 14.2p` near the right edge
- Title: `Agile Octopus — {date}` in white, top-left, large
- No top/right spines. Bottom/left spines white but thin.
- All text colour: white or `#e0d8f0`

**Output:** save to `chart.png` in working directory.

---

## 5. "Below-average hours" logic

The API gives 48 half-hourly slots. The user wants hours, not half-hours, for readability.

**Algorithm:**
1. Compute `daily_avg = mean(all 48 slots)`.
2. Group the 48 slots into 24 hourly buckets (`00:00–01:00`, `01:00–02:00`, …).
3. For each hour, compute `hour_avg = mean(2 slots)`.
4. Select hours where `hour_avg < daily_avg`.
5. **Collapse contiguous hours into ranges** for readable display:
   - e.g. `[0,1,2,3, 13,14, 23]` → `00:00–04:00, 13:00–15:00, 23:00–24:00`
6. For each range, also show its average price.

**Output format in email body (example):**
```
Daily average: 14.2 p/kWh

Below-average windows:
  00:00–05:00   →   8.7 p/kWh
  13:00–15:00   →  11.4 p/kWh
  23:00–24:00   →  12.9 p/kWh
```

---

## 6. Negative price handling

Negative prices are rare and worth flagging prominently.

**Detection:** any half-hour slot with `value_inc_vat < 0`.

**Treatment:**
1. On the chart: render those bars in **green `#00d68f`** instead of pink. Bars extend downward from the zero line (matplotlib handles this natively if y-axis includes negative).
2. In the email: add a **prominent line at the top** of the body, e.g.:
   ```
   ⚡ NEGATIVE PRICES TOMORROW ⚡
     13:00–13:30   −2.4 p/kWh
     13:30–14:00   −1.1 p/kWh
   ```
   List the exact half-hour slots (not collapsed to hours) so the user knows precisely when to run things.
3. Email **subject line** should also change when negative prices exist:
   - Normal: `Agile Octopus — Tue 7 Apr — avg 14.2p`
   - With negative: `⚡ Agile Octopus — Tue 7 Apr — NEGATIVE PRICES — avg 14.2p`

If there are **no** negative prices, do not include the negative section at all (keep the email clean).

---

## 7. Email composition

Use Python `smtplib` + `email.message.EmailMessage`. No third-party email libraries.

**Subject:** see §6.

**Body (plain text + HTML multipart):**

Plain text version is the source of truth. HTML version embeds the chart inline via `cid:` reference, plus also attaches `chart.png` as a downloadable attachment.

**Plain text body template:**
```
{negative_section_if_any}

Daily average: {avg} p/kWh

Below-average windows:
{ranges}

---
Agile Octopus · Region {region_letter} · Product {product_code}
```

Keep it short. No marketing fluff. No emoji except the negative-price warning.

**HTML body:** same content but with the chart `<img src="cid:chart">` at the top.

**Recipients:** put `SENDER_EMAIL` in `To:` and all `RECIPIENTS` in `Bcc:`.

---

## 8. Retry / failure handling

Octopus typically publishes next-day prices around 16:00 UK time, but it can slip to 17:00 or later. The cron should be robust to this.

**Strategy:**
- Run cron at **16:30, 17:30, and 18:30 UK time**.
- Each run: fetch the API. If fewer than 48 slots for tomorrow are returned, **exit cleanly with a log message** (no email, no error).
- Use a **lockfile committed back to the repo** OR a GitHub Actions cache key based on tomorrow's date to ensure **only one email is sent per day**.
  - Simpler approach: use GitHub Actions cache. Cache key `sent-{YYYY-MM-DD}`. If cache hit, skip. If miss after a successful send, write a marker file to cache.
- If all three runs fail to find 48 slots, **the 18:30 run should send a fallback email** saying "Agile prices for tomorrow not yet published, check Octopus app".

---

## 9. Project structure

```
.
├── CLAUDE.md                       (this file)
├── README.md                       (setup steps for the user)
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── fetch.py                    (Octopus API client)
│   ├── analyze.py                  (averages, below-avg ranges, negative detection)
│   ├── chart.py                    (matplotlib chart generation)
│   ├── email_sender.py             (SMTP composition + send)
│   └── main.py                     (orchestration, entry point)
├── tests/
│   ├── test_analyze.py             (pure-function tests, no network)
│   ├── test_chart.py               (smoke test: produces a PNG)
│   └── fixtures/
│       └── sample_response.json    (recorded API response for offline testing)
└── .github/
    └── workflows/
        └── daily.yml               (cron + manual trigger)
```

**Entry point:** `python -m src.main`

---

## 10. Dependencies

Keep minimal. `requirements.txt`:
```
requests>=2.31
matplotlib>=3.8
```

No pandas, no numpy unless matplotlib pulls it transitively. No email libraries beyond stdlib. No timezone libraries beyond stdlib `zoneinfo`.

---

## 11. GitHub Actions workflow

`.github/workflows/daily.yml`:

- **Triggers:**
  - `schedule`: three crons — `30 15 * * *`, `30 16 * * *`, `30 17 * * *` (UTC; these correspond to 16:30, 17:30, 18:30 UK time during BST; adjust comments to note GMT/BST drift)
  - `workflow_dispatch`: for manual testing
- **Job steps:**
  1. `actions/checkout@v4`
  2. `actions/setup-python@v5` with Python 3.12
  3. `actions/cache@v4` with key `agile-sent-${{ github.run_id }}-tomorrow` (compute tomorrow's date in a previous step and use it)
  4. `pip install -r requirements.txt`
  5. `python -m src.main` with all secrets injected as `env:`
- **Secrets used:** all variables from §3.

The workflow must succeed (exit 0) even when prices aren't yet published — only fail on actual errors (network, SMTP, code bugs).

---

## 12. Testing

Before handing off:

1. `tests/test_analyze.py` must cover:
   - `daily_average` computation
   - `below_average_hours` collapsing into contiguous ranges
   - Negative-price detection
   - Edge case: all prices identical (no below-avg hours)
   - Edge case: single negative slot

2. `tests/test_chart.py`: load fixture, generate chart, assert PNG file exists and is non-empty.

3. **Manual end-to-end smoke test** instructions in `README.md`:
   - Run `python -m src.main` locally with a `.env` file
   - Verify email arrives at all configured recipients
   - Verify chart renders correctly
   - Verify negative-price branch by hand-editing the fixture

---

## 13. README.md (must be created)

Should contain:
1. One-paragraph description.
2. **Setup steps**: fork repo → add GitHub secrets → enable Actions.
3. **Gmail app-password instructions** (since the user will likely use Gmail SMTP).
4. How to **add/remove recipients** (just edit the `RECIPIENTS` secret, comma-separated).
5. How to **change region** (edit `TARIFF_CODE` secret — table of region letters A–P).
6. How to **trigger manually** for testing (`workflow_dispatch` button in Actions tab).
7. Troubleshooting: "no email arrived" checklist.

---

## 14. Out of scope (do not build)

- Web UI / dashboard
- Database / historical price storage
- Telegram / WhatsApp / Slack — email only
- Smart-plug / automation hooks
- Forecasting / ML
- Multiple regions in one run

Keep it small, single-purpose, and reliable.

---

## 15. Definition of done

- [ ] All files in §9 exist
- [ ] `python -m src.main` runs end-to-end against the live Octopus API
- [ ] All tests in `tests/` pass
- [ ] A real email with chart + summary lands in the user's inbox
- [ ] Negative-price code path is verified via fixture (since live negative prices are rare)
- [ ] GitHub Actions workflow runs successfully via `workflow_dispatch`
- [ ] README has working setup instructions