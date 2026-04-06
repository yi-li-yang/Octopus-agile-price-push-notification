# GitHub Secrets Checklist

All configuration is via GitHub Actions secrets — no values hardcoded in the repo.

**Where to add them:** Your repo → **Settings → Secrets and variables → Actions → New repository secret**

---

## Required secrets

These five must be set or the workflow will fail.

### `RECIPIENTS`
Comma-separated email addresses. No spaces required, but allowed.
```
yili@gmail.com,partner@gmail.com
```
✅ Single recipient is fine: `yili@gmail.com`
✅ Many recipients fine: `a@x.com, b@y.com, c@z.com, d@w.com`

---

### `SMTP_HOST`
SMTP server hostname for your email provider.

| Provider | Value |
|---|---|
| Gmail | `smtp.gmail.com` |
| Outlook / Hotmail | `smtp-mail.outlook.com` |
| Fastmail | `smtp.fastmail.com` |
| ProtonMail (via Bridge) | `127.0.0.1` |
| iCloud | `smtp.mail.me.com` |

---

### `SMTP_PORT`
Almost always `587` (STARTTLS). Use `465` only if your provider requires SSL/TLS instead.

```
587
```

---

### `SMTP_USER`
The email address you're sending **from**. For Gmail this is your full Gmail address.

```
yili@gmail.com
```

---

### `SMTP_PASSWORD`
**Not your normal password.** Use an app-specific password.

**Gmail:**
1. Enable 2-Step Verification: https://myaccount.google.com/security
2. Go to https://myaccount.google.com/apppasswords
3. App name: `agile-notifier` → Generate
4. Copy the 16-character password (looks like `abcd efgh ijkl mnop`)
5. Paste **without spaces** into the secret: `abcdefghijklmnop`

**Outlook:**
- Go to https://account.microsoft.com/security → Advanced security options → App passwords

**Fastmail:**
- Settings → Privacy & Security → App passwords → New app password

---

## Optional secrets

These have sensible defaults. Only add them if you need to override.

### `SENDER_EMAIL`
**Default:** same as `SMTP_USER`

Set this only if you want the email to appear from a different address than the SMTP login (e.g. `notifier@yourdomain.com` while authenticating as `yili@gmail.com`).

---

### `PRODUCT_CODE`
**Default:** `AGILE-24-10-01`

The Agile product version. Octopus releases new versions occasionally. To check current:
```bash
curl -s https://api.octopus.energy/v1/products/ | grep -o '"code":"AGILE[^"]*"'
```

---

### `TARIFF_CODE`
**Default:** `E-1R-AGILE-24-10-01-C` (London / Region C)

Format: `E-1R-{PRODUCT_CODE}-{REGION_LETTER}`

If you change `PRODUCT_CODE`, you must change the middle of `TARIFF_CODE` to match.

If you move outside London, change the final letter:

| Letter | Region |
|---|---|
| A | Eastern England |
| B | East Midlands |
| **C** | **London** (default) |
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

---

### `TIMEZONE`
**Default:** `Europe/London`

Standard IANA timezone string. Only change if you've moved outside the UK and want "tomorrow" computed in your local time. Note: Octopus prices themselves are always UK-based.

---

## Quick checklist

Copy this and tick off as you add each secret:

```
Required:
[ ] RECIPIENTS
[ ] SMTP_HOST
[ ] SMTP_PORT
[ ] SMTP_USER
[ ] SMTP_PASSWORD

Optional (skip unless needed):
[ ] SENDER_EMAIL
[ ] PRODUCT_CODE
[ ] TARIFF_CODE
[ ] TIMEZONE
```

---

## Verifying setup

After adding secrets:

1. Go to **Actions** tab in your repo
2. Click **Daily Agile Notifier** in the left sidebar
3. Click **Run workflow** (top right) → **Run workflow**
4. Wait ~30 seconds, then click into the run to see logs
5. Check your inbox

If something fails, the Actions log will show **which secret is missing or invalid** without ever printing its value (GitHub auto-redacts secrets).

---

## Security notes

- GitHub auto-encrypts secrets at rest and never exposes them in logs
- Secrets are only injected as environment variables during the workflow run
- The script never writes secrets to disk or to the cache marker
- If you ever leak a Gmail app password, **revoke it immediately** at https://myaccount.google.com/apppasswords and generate a new one — your main Google password is unaffected
- The repo can be **public** safely; secrets are stored separately from code