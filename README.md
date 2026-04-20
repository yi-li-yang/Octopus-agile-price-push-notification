# Agile Octopus Daily Price Notifier


A small GitHub Actions cron job that fetches tomorrow's [Agile Octopus](https://octopus.energy/agile/) half-hourly electricity prices, generates an Octopus-style bar chart, computes the daily average, and emails it to a configurable list of recipients every evening.

No server. No database. No cost.

---

## What you get

![Email preview](https://raw.githubusercontent.com/yi-li-yang/Octopus-agile-price-push-notification/main/thumb.png)

Every evening (after Octopus publishes the next day's prices), each recipient receives an email like this:

> **Subject:** Agile Octopus — Tue 7 Apr — avg 14.2p
>
> *(chart inline)*
>
> Daily average: 14.2 p/kWh
>
> Below-average windows:
> - 00:00–05:00 → 8.7 p/kWh
> - 13:00–15:00 → 11.4 p/kWh
> - 23:00–24:00 → 12.9 p/kWh

When negative prices appear, the subject and body are flagged prominently and the half-hour windows are listed precisely.

---

## Setup (10 minutes)

### 1. Fork or clone this repo

Push it to your own GitHub account (private is fine).

### 2. Generate a Gmail App Password

If you're sending from Gmail (recommended — free, reliable):

1. Go to https://myaccount.google.com/security
2. Enable **2-Step Verification** if not already on
3. Go to https://myaccount.google.com/apppasswords
4. Create a new app password, name it `agile-notifier`
5. Copy the 16-character password — you'll need it in the next step

If you use another provider (Outlook, Fastmail, ProtonMail Bridge, etc.), find their SMTP credentials instead.

### 3. Add GitHub Secrets

In your repo: **Settings → Secrets and variables → Actions → New repository secret**

Add each secret from [`SECRETS.md`](./SECRETS.md). Required ones first; optional ones only if you need to override defaults.

### 4. Enable GitHub Actions

In your repo: **Actions** tab → click "I understand my workflows, enable them".

### 5. Test it manually

In your repo: **Actions → Daily Agile Notifier → Run workflow** (top right button).

Within ~30 seconds, check your inbox. If the email arrives, you're done — the cron will run automatically every evening from now on.

---

## Configuration

### Adding or removing recipients

Edit the `RECIPIENTS` secret. Comma-separated, no spaces required:

```
yili@example.com,partner@example.com,backup@example.com
```

Save. The next run will use the new list. Recipients are sent as **BCC** so they don't see each other.

### Changing region (if you move)

Octopus has 14 regional codes (one per UK distribution area). Edit the `TARIFF_CODE` secret and replace the final letter:

| Letter | Region |
|---|---|
| A | Eastern England |
| B | East Midlands |
| C | **London** ← default |
| D | Merseyside & Northern Wales |
| E | West Midlands |
| F | North Eastern England |
| G | North Western England |
| H | Southern England |
| J | South Eastern England |
| K | Southern Wales |
| L | South Western England |
| M | Yorkshire |
| N | Southern Scotland |
| P | Northern Scotland |

For example, if you move to Edinburgh: change `E-1R-AGILE-24-10-01-C` → `E-1R-AGILE-24-10-01-N`.

### Changing the Agile product version

Octopus periodically releases new product versions (e.g. when wholesale formula or cap changes). To check the current version:

```bash
curl -s https://api.octopus.energy/v1/products/ | jq '.results[] | select(.code | startswith("AGILE")) | .code'
```

Update both `PRODUCT_CODE` and `TARIFF_CODE` secrets to match.

---

## How it works

1. **Cron triggers** at 16:30, 17:30, and 18:30 UK time daily.
2. The script calls Octopus's public REST API to fetch tomorrow's 48 half-hourly prices.
3. If fewer than 48 slots are returned (prices not yet published), it exits cleanly.
4. Otherwise, it computes the daily average, identifies hour buckets below average, detects negative prices, and renders a chart.
5. The chart and summary are emailed to all recipients via SMTP.
6. A GitHub Actions cache marker prevents duplicate emails on the same day.

If no prices are published by the 18:30 run, a fallback notice is sent so you know to check the Octopus app manually.

---

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in SMTP credentials and RECIPIENTS

python -m src.main
```

Run tests:

```bash
pytest tests/
```

The test suite uses a recorded API response fixture and does not hit the network.

---

## Troubleshooting

**No email arrived after manual run**

1. Check the Actions log: **Actions → Daily Agile Notifier → latest run**
2. Look for `Email sent to N recipients` near the end
3. If you see `Prices not yet published, exiting` — that's normal before 16:00 UK
4. If you see an SMTP error — re-check your `SMTP_PASSWORD` (Gmail app password, not regular password)
5. Check your Gmail spam folder, especially for the first send

**Email arrived but chart is missing**

- Some email clients block remote/CID images by default. The chart is also attached as `chart.png` — you can view it from the attachment.

**Wrong region's prices**

- Verify the final letter of `TARIFF_CODE` matches your distribution region (table above). Postcode and region don't always match intuitively — check at https://www.energynetworks.org/operating-the-networks/whos-my-network-operator.

**Negative prices never appear**

- They're rare (a handful of times per year, usually windy weekends in spring/autumn with low demand). The code path is verified by fixture tests.

**Cron stopped running**

- GitHub Actions disables scheduled workflows on repos with no activity for 60 days. Push any commit (or click "Re-enable workflow" in the Actions tab) to revive it.

---

## Costs

Zero. Stays well within GitHub Actions free tier (2000 minutes/month for private repos, unlimited for public). Each daily run takes ~20 seconds.

---

## License

MIT — do whatever you want with it.