# 🩸 Blood Pressure Monitor & Telemedicine Platform

A comprehensive platform for tracking blood pressure, managing doctor-patient relationships, and empowering users with their health data.

**Key Components:**
**Backend API**: Fast, Secure (Fernet Encryption), and Scalable (FastAPI).
**Telegram Bot**: AI-powered OCR with "Human-in-the-loop" confirmation for accuracy.
**Web Application**: Modern dashboard with visual analytics and Smart OCR integration.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ (for Web App & Chart Rendering)
- Google Gemini API Key (for OCR)

### 1️⃣ Configuration

Copy `.env.example` to `app/.env` and fill in your values:

```bash
cp .env.example app/.env
# Edit app/.env with your actual keys

# Generate encryption key:
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Key variables (see `.env.example` for full list):

```env
DATABASE_URL=sqlite:///./blood_pressure.db
SECRET_KEY=your_super_secret_jwt_key
ENCRYPTION_KEY=<generated-fernet-key>
API_KEYS=bp-mobile-app-key,bp-web-app-key
GOOGLE_AI_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
APP_TIMEZONE=Asia/Bangkok
```

### 2️⃣ Running the Backend API

The core brain of the system.

```bash
# Install dependencies
pip install -r app/requirements.txt

# Install chart renderer (required for BP chart generation)
cd app/chart-renderer && npm install && cd ../..

# Run Server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8888
```

* **Docs**: [http://localhost:8888/docs](http://localhost:8888/docs)
* **Health Check**: [http://localhost:8888/health](http://localhost:8888/health)

### 3️⃣ Running the Telegram Bot 🤖

Allows users to record BP by sending a photo.

```bash
# Run Bot (in a new terminal)
python3 -m app.bot.main
```

* **Use it**: Open your bot in Telegram.
* **Commands**:
  * `/start` - Welcome & Status.
  * `/login <email> <password>` - Link Telegram to your account.
  * `/stats` - View stats & recent records + BP trend chart image.
  * **[Send Photo]** - Auto-extract BP values -> Confirm/Edit -> Save.

### 4️⃣ Running the Web Application 🌐

Dashboard for patients and doctors.

```bash
cd frontend
# Install dependencies
npm install

# Run Dev Server
npm run dev
```

* **URL**: [http://localhost:3000](http://localhost:3000)

---

## 🛠 Features Breakdown

### 🔐 Security & Privacy

* **Field-Level Encryption**: Sensitive PII (Citizen ID, Medical License) is encrypted *before* valid storage using AES-128 (Fernet). Even database admins cannot read it without the key.
* **Hashed Indexes**: Allows searching for unique IDs (like Citizen ID) without decrypting the entire database.
* **Data Portability**: Users can export their full history via `/api/v1/export/my-data`.

### 🩺 For Patients

* **Smart Recording**:
  * **Scan Photo**: Upload image or file -> AI extracts Sys/Dia/Pulse & Date/Time.
  * **Duplicate Prevention**: Automatically detects and ignores duplicate uploads (Same User + Date/Time + Values).
  * **Intelligent Timestamp**: Auto-detects time from Screen (OCR) -> EXIF -> Fallback.
* **Trends & History**:
  * **Free Level**: View latest 30 records & statistics.
  * **Premium Level**: Unlimited history access.
* **Doctor Access**: Grant or revoke access for doctors to view your data.

### 👨‍⚕️ For Doctors

* **Patient List**: View all authorized patients.
* **Access Request**: Request access to a patient's data by email/ID.
* **Monitoring**: View patient graphs and history (Full History Access).

---

### 💳 Subscription & Payments

We offer a flexible subscription model to ensure sustainability while keeping essential features free.

* **Free Tier**:
  * 30-record history limit.
  * Basic stats.
  * Standard support.
* **Premium Tier** (99 THB/mo or 990 THB/yr):
  * **Unlimited History**: Store and view records from day one.
  * **Data Export**: Full CSV/PDF export.
  * **Priority Support**.

**Payment Flow (Manual Verification)**:
Currently, the system uses a manual slip verification workflow:

1. User selects a plan (Web or Bot).
2. System generates a Bank Account info / QR Code.
3. User transfers money and uploads the bank slip.
4. Admin confirms the slip -> Subscription activated via `/admin` or DB.

---

### 🌍 Localization (Bilingual Support)

The platform is fully bilingual, supporting **English (EN)** and **Thai (TH)**.

**Changing Language:**

* **Web App**: Click the language switcher in the header or go to **Settings > General**.
* **Telegram Bot**: Use the command `/language` to toggle between English and Thai.

**How to Add/Edit Languages:**

1. **Frontend**:
   * Navigate to `frontend/locales/`.
   * Copy `en.ts` to a new file (e.g., `es.ts` for Spanish).
   * Translate the values in the new file.
   * Update `frontend/contexts/LanguageContext.tsx` to include the new language type.
2. **Telegram Bot**:
   * Navigate to `app/bot/locales.py`.
   * Add a new dictionary key (e.g., `'es': {...}`) copying the structure of `'en'`.
   * Translate the strings.
   * Update `app/schemas.py` Language Enum if necessary.

---

## 📡 Deployment Guide (Telegram Bot)

### Localhost Testing

You **do NOT** need a public IP or HTTPS to test locally because we use **Long Polling**.

1. Ensure `TELEGRAM_BOT_TOKEN` is set in `.env`.
2. Run `python3 -m app.bot.main`.
3. The bot immediately starts receiving messages from Telegram servers.

### Server Deployment (Production)

For a real server (e.g., VPS, DigitalOcean, AWS, Vercel):

**Option A: Long Polling (Simpler)**

* **Pros**: Easiest setup, works behind NAT/Firewall.
* **Cons**: Slightly slower than Webhooks for massive scale.
* **How**: Just run the script as a background service (Systemd or Docker).

```env
BOT_MODE=polling
```

**Option B: Webhooks (Recommended for serverless / high traffic)**

* **Pros**: Faster, serverless-friendly (Vercel, Lambda, Cloud Run).
* **Cons**: Requires valid **HTTPS** certificate (SSL).

**Setup:**

1. Generate a hard-to-guess webhook path:
   ```bash
   python3 -c "import secrets; print(f'bot-{secrets.token_hex(16)}')"
   ```

2. Configure environment variables:
   ```env
   BOT_MODE=webhook
   WEBHOOK_URL=https://your-api-domain.com
   WEBHOOK_SECRET=your-strong-random-secret
   WEBHOOK_PATH=bot-a1b2c3d4e5f6...   # Hard-to-guess path from step 1
   ```

3. Deploy and register webhook (call once):
   ```
   GET https://your-api-domain.com/<WEBHOOK_PATH>/set-webhook?secret=<WEBHOOK_SECRET>
   ```

   This tells Telegram to send updates to `https://your-api-domain.com/<WEBHOOK_PATH>/webhook` — a URL that is effectively impossible to guess.

**Security Layers:**
* **Layer 1**: `WEBHOOK_PATH` — random URL path (e.g., `/bot-f77192489b.../webhook`)
* **Layer 2**: `WEBHOOK_SECRET` — Telegram sends `X-Telegram-Bot-Api-Secret-Token` header for verification

### Systemd Service Example (Linux)

Create `/etc/systemd/system/bp-bot.service`:

```ini
[Unit]
Description=BP Monitor Telegram Bot
After=network.target

[Service]
User=root
WorkingDirectory=/path/to/BP
ExecStart=/usr/bin/python3 -m app.bot.main
Restart=always
EnvironmentFile=/path/to/BP/app/.env

[Install]
WantedBy=multi-user.target
```

Then: `sudo systemctl enable --now bp-bot`

---

## 📂 Project Structure

```
BP/
├── app/                       # Backend & Bot
│   ├── bot/                   # Telegram Logic
│   ├── routers/               # API Endpoints (Auth, Users, Records, Stats...)
│   ├── chart-renderer/        # Server-side Chart.js renderer (Node.js)
│   │   ├── render.js         # Chart.js + @napi-rs/canvas → PNG
│   │   └── package.json      # npm dependencies
│   ├── utils/                 # Core Utility (OCR, Encryption, Chart)
│   ├── models.py              # DB Schema
│   └── main.py                # App Entry Point
├── frontend/                  # Next.js Web App
│   ├── app/                   # Pages & Layouts
│   ├── components/            # UI Components (Shadcn)
│   └── lib/                   # API Client
├── tests/                     # Test suite (pytest)
├── Dockerfile                 # Python + Node.js
└── docker-compose.yml         # Full stack deployment
```

---

## 📊 Chart Generation

BP trend charts are rendered server-side using **Chart.js** via Node.js subprocess:

```
Python (chart_generator.py) → JSON stdin → Node.js (render.js) → PNG stdout
```

- **API:** `GET /api/v1/stats/chart?days=30&lang=th` — returns PNG image
- **Telegram Bot:** `/stats` command auto-sends chart after text stats
- Supports Thai & English labels
- Reference zones for High BP (Systolic > 140, Diastolic > 90)
- Data labels on every point (SYS/DIA + Pulse values)

**Requirements:** Node.js 18+ and `npm install` in `app/chart-renderer/`

---

## 🐳 Docker Deployment

```bash
docker-compose up --build
```

Services: PostgreSQL + Redis + FastAPI (with Node.js for chart rendering) + Telegram Bot + Next.js Frontend

The Dockerfile installs both Python and Node.js runtimes for chart rendering support.

---

## 🧪 Testing

```bash
python3 -m pytest tests/ -v
```

---

## 📜 License

This project is **dual-licensed**:

### Open Source License (AGPL-3.0)

For open source use, this software is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0).

This means:

- ✅ Free to use, modify, and distribute
- ✅ Must keep source code open
- ⚠️ **Network use is distribution** - If you run a modified version as a network service, you must make the source code available to users of that service

See [LICENSE](LICENSE) for the full AGPL-3.0 text.

### Commercial License

For proprietary or commercial use where you **cannot or do not want to** comply with AGPL-3.0 terms, a Commercial License is available.

**You need a Commercial License if you:**

- Deploy for paying customers without releasing source code
- Integrate into proprietary software
- Offer as a SaaS/managed service without open-sourcing your modifications
- Use within a for-profit healthcare organization

**Commercial License includes:**

- Use without AGPL-3.0 obligations
- Optional support packages
- SLA for response times

📧 **Contact for licensing:** [GitHub Profile](https://github.com/kaebmoo)

See [LICENSE-COMMERCIAL.md](LICENSE-COMMERCIAL.md) for terms.

---

## Quick Reference

| Use Case                                    | License Needed | Cost    |
| ------------------------------------------- | -------------- | ------- |
| Personal/educational use                    | AGPL-3.0       | Free    |
| Open source project (AGPL-compatible)       | AGPL-3.0       | Free    |
| Internal company use (source stays private) | Commercial     | Contact |
| SaaS offering                               | Commercial     | Contact |
| Hospital/clinic deployment                  | Commercial     | Contact |

---
