# Telegram Bot Webhook Setup Guide

## Overview

The Telegram Bot supports 2 modes:

| Mode | Use Case | Requires Public URL? |
|------|----------|----------------------|
| `polling` | Local dev, Docker, VPS | No |
| `webhook` | Vercel, Serverless, Production | Yes |

---

## 1. Environment Variables

Configure these in `.env` or your Vercel Dashboard:

```env
# Required
TELEGRAM_BOT_TOKEN=<your-bot-token>
BOT_MODE=webhook

# Webhook Config
WEBHOOK_URL=https://your-backend.vercel.app
WEBHOOK_SECRET=<random-secret-string>
WEBHOOK_PATH=bot-<random-hex-string>
```

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Token from [@BotFather](https://t.me/BotFather) |
| `BOT_MODE` | Set to `webhook` (default: `polling`) |
| `WEBHOOK_URL` | Base URL of your deployed API (no trailing `/`) |
| `WEBHOOK_SECRET` | Secret token to verify requests from Telegram |
| `WEBHOOK_PATH` | Hard-to-guess path, e.g., `bot-a1b2c3d4e5f6` (If left empty, a new random path is generated on each cold start) |

> **Important:** For Vercel/Serverless, you must set a fixed `WEBHOOK_PATH` because a random path will change on every cold start.

---

## 2. Webhook URL Format

```
{WEBHOOK_URL}/{WEBHOOK_PATH}/webhook
```

**Example:**
```
https://bp-wheat.vercel.app/bot-a1b2c3d4e5f6/webhook
```

---

## 3. Register Webhook with Telegram

### Method 1: Using Built-in Endpoint (Recommended)

After deploying, call this endpoint once:

```bash
curl "https://your-backend.vercel.app/{WEBHOOK_PATH}/set-webhook?secret={WEBHOOK_SECRET}"
```

**Example:**
```bash
curl "https://bp-wheat.vercel.app/bot-a1b2c3d4e5f6/set-webhook?secret=my-secret-123"
```

**Success Response:**
```json
{
  "ok": true,
  "webhook_url": "https://bp-wheat.vercel.app/bot-a1b2c3d4e5f6/webhook"
}
```

### Method 2: Using Telegram API Directly

```bash
curl "https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}/{WEBHOOK_PATH}/webhook&secret_token={WEBHOOK_SECRET}"
```

---

## 4. Check Webhook Status

```bash
curl "https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

**Good Response:**
```json
{
  "ok": true,
  "result": {
    "url": "https://bp-wheat.vercel.app/bot-a1b2c3d4e5f6/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "last_error_date": null
  }
}
```

---

## 5. Remove Webhook

### Using Built-in Endpoint:

```bash
curl "https://your-backend.vercel.app/{WEBHOOK_PATH}/remove-webhook?secret={WEBHOOK_SECRET}"
```

### Or using Telegram API:

```bash
curl "https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
```

---

## 6. Switch Back to Polling Mode (Local Dev)

```env
BOT_MODE=polling
# No need to set WEBHOOK_URL, WEBHOOK_SECRET, WEBHOOK_PATH
```

Then run the bot in a separate terminal:
```bash
python3 -m app.bot.main
```

---

## 7. Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Bot not responding | Webhook is not registered | Call the `/set-webhook` endpoint |
| 403 Forbidden | `WEBHOOK_SECRET` mismatch | Verify the secret in env vars |
| Invalid Webhook URL | `WEBHOOK_URL` is wrong or missing HTTPS | HTTPS is strictly required |
| Bot replies slowly/timeout | Vercel hobby plan 10s limit | Optimize response time or upgrade to Pro |
| Webhook changes after deploy | `WEBHOOK_PATH` not set | Set a fixed `WEBHOOK_PATH` in env vars |

---

## 8. Security Notes

- `WEBHOOK_PATH` should be a hard-to-guess string (like a UUID or random hex).
- `WEBHOOK_SECRET` is used to verify that the incoming request is genuinely from Telegram via the `X-Telegram-Bot-Api-Secret-Token` header.
- Never expose `WEBHOOK_PATH` or `WEBHOOK_SECRET` in public repositories.
