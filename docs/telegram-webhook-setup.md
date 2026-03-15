# Telegram Bot Webhook Setup Guide

## Overview

Telegram Bot รองรับ 2 โหมด:

| Mode | Use Case | ต้องการ Public URL? |
|------|----------|---------------------|
| `polling` | Local dev, Docker, VPS | ไม่ |
| `webhook` | Vercel, Serverless, Production | ใช่ |

---

## 1. Environment Variables

ตั้งค่าใน `.env` หรือ Vercel Dashboard:

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
| `TELEGRAM_BOT_TOKEN` | Token จาก [@BotFather](https://t.me/BotFather) |
| `BOT_MODE` | ตั้งเป็น `webhook` (default: `polling`) |
| `WEBHOOK_URL` | Base URL ของ API ที่ deploy แล้ว (ไม่มี `/` ต่อท้าย) |
| `WEBHOOK_SECRET` | Secret สำหรับ verify request จาก Telegram |
| `WEBHOOK_PATH` | Path ที่เดายาก เช่น `bot-a1b2c3d4e5f6` (ถ้าไม่ตั้ง จะ random ทุก cold start) |

> **สำคัญ:** สำหรับ Vercel/Serverless ต้องตั้ง `WEBHOOK_PATH` ให้คงที่ เพราะ random path จะเปลี่ยนทุก cold start

---

## 2. Webhook URL Format

```
{WEBHOOK_URL}/{WEBHOOK_PATH}/webhook
```

**ตัวอย่าง:**
```
https://bp-wheat.vercel.app/bot-a1b2c3d4e5f6/webhook
```

---

## 3. Register Webhook กับ Telegram

### วิธีที่ 1: ใช้ Built-in Endpoint (แนะนำ)

หลัง deploy แล้ว เรียก endpoint นี้ครั้งเดียว:

```bash
curl "https://your-backend.vercel.app/{WEBHOOK_PATH}/set-webhook?secret={WEBHOOK_SECRET}"
```

**ตัวอย่าง:**
```bash
curl "https://bp-wheat.vercel.app/bot-a1b2c3d4e5f6/set-webhook?secret=my-secret-123"
```

**Response สำเร็จ:**
```json
{
  "ok": true,
  "webhook_url": "https://bp-wheat.vercel.app/bot-a1b2c3d4e5f6/webhook"
}
```

### วิธีที่ 2: ใช้ Telegram API โดยตรง

```bash
curl "https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}/{WEBHOOK_PATH}/webhook&secret_token={WEBHOOK_SECRET}"
```

---

## 4. ตรวจสอบ Webhook Status

```bash
curl "https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

**Response ที่ดี:**
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

### ใช้ Built-in Endpoint:

```bash
curl "https://your-backend.vercel.app/{WEBHOOK_PATH}/remove-webhook?secret={WEBHOOK_SECRET}"
```

### หรือใช้ Telegram API:

```bash
curl "https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
```

---

## 6. สลับกลับไป Polling Mode (Local Dev)

```env
BOT_MODE=polling
# ไม่ต้องตั้ง WEBHOOK_URL, WEBHOOK_SECRET, WEBHOOK_PATH
```

แล้วรัน bot แยก terminal:
```bash
python3 -m app.bot.main
```

---

## 7. Troubleshooting

| ปัญหา | สาเหตุ | แก้ไข |
|--------|--------|-------|
| Bot ไม่ตอบ | Webhook ยังไม่ได้ register | เรียก `/set-webhook` endpoint |
| 403 Forbidden | `WEBHOOK_SECRET` ไม่ตรง | ตรวจสอบ secret ใน env vars |
| Webhook URL invalid | `WEBHOOK_URL` ผิด หรือไม่มี HTTPS | ต้องเป็น HTTPS เท่านั้น |
| Bot ตอบช้า/timeout | Vercel hobby plan 10s limit | ลดขนาด response หรืออัพเป็น Pro |
| Webhook เปลี่ยนหลัง deploy | ไม่ได้ตั้ง `WEBHOOK_PATH` | ตั้งค่า `WEBHOOK_PATH` ให้คงที่ |

---

## 8. Security Notes

- `WEBHOOK_PATH` ควรเป็น string ที่เดายาก (เช่น UUID หรือ random hex)
- `WEBHOOK_SECRET` ใช้ verify ว่า request มาจาก Telegram จริง ผ่าน header `X-Telegram-Bot-Api-Secret-Token`
- ไม่ควรเปิดเผย `WEBHOOK_PATH` และ `WEBHOOK_SECRET` ใน public repository
