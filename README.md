# Blood Pressure Monitor & Telemedicine Platform

A comprehensive platform for tracking blood pressure, managing doctor-patient relationships, and empowering users with their health data.

**Key Components:**
**Backend API**: Fast, Secure (Fernet Encryption), and Scalable (FastAPI).
**Telegram Bot**: AI-powered OCR with "Human-in-the-loop" confirmation for accuracy.
**Web Application**: Modern dashboard with visual analytics and Smart OCR integration.

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ (for Chart Rendering)
- Google Gemini API Key (for OCR)

### 1. Configuration

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
ADMIN_TELEGRAM_IDS=123456789,987654321
APP_TIMEZONE=Asia/Bangkok
```

### 2. Running the Backend API

```bash
pip install -r app/requirements.txt

# Install chart renderer (required for BP chart generation)
cd app/chart-renderer && npm install && cd ../..

# Run Server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8888
```

* **Docs**: http://localhost:8888/docs
* **Health Check**: http://localhost:8888/health

### 3. Running the Telegram Bot

```bash
python3 -m app.bot.main
```

### 4. Running the Web Application

```bash
cd frontend
npm install
npm run dev
```

* **URL**: http://localhost:3000

---

## Deployment

### Vercel (Serverless)

Frontend and Backend are deployed as **separate Vercel projects** from the same repository.

#### How It Works

Vercel runs Python as serverless functions. Because `app/main.py` uses relative imports (`from .database import ...`), it **cannot** be used as a direct entry point. Instead, `api/index.py` acts as a bridge:

```
api/index.py          → Vercel entry point (zero-config path)
  └── from app.main import app   → loads FastAPI as a package (relative imports work)
```

#### Required Files (already in repo)

**`api/index.py`** -- Vercel serverless entry point:

```python
from app.main import app
```

This file exists because Vercel's Python runtime recognizes `api/index.py` as a standard entry point. It imports the FastAPI `app` instance from `app/main.py`, which allows all relative imports within the `app/` package to work correctly.

**`vercel.json`** -- Routes all requests to the entry point:

```json
{
  "builds": [
    { "src": "api/index.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "api/index.py" }
  ]
}
```

**`requirements.txt`** (root) -- Mirrors `app/requirements.txt` because Vercel looks for dependencies at the project root.

**`app/__init__.py`** -- Empty file that marks `app/` as a Python package (required for `from app.main import app` to work).

#### Step-by-Step Deployment

**Step 1: Create PostgreSQL Database**

Sign up at [neon.tech](https://neon.tech) and create a database. Copy the connection string.

**Step 2: Create Redis Instance**

Go to [Vercel Marketplace > Upstash](https://vercel.com/marketplace/upstash) or sign up at [upstash.com](https://upstash.com). Copy the Redis URL.

**Step 3: Deploy Backend**

1. Import your GitHub repo in Vercel
2. Set **Root Directory** to `.` (root)
3. Vercel will detect `vercel.json` and use `@vercel/python`
4. Set Environment Variables:

```env
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/bp_db?sslmode=require
REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379
SECRET_KEY=<strong-random-key>
ENCRYPTION_KEY=<fernet-key>
API_KEYS=<your-api-keys>
GOOGLE_AI_API_KEY=<gemini-key>
TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_BOT_USERNAME=<bot-username>
ADMIN_TELEGRAM_IDS=<comma-separated-admin-ids>
BOT_MODE=webhook
WEBHOOK_URL=https://your-backend.vercel.app
WEBHOOK_SECRET=<random-secret>
WEBHOOK_PATH=<hard-to-guess-path>
APP_TIMEZONE=Asia/Bangkok
AUTO_CREATE_TABLES=true
ALLOWED_ORIGINS=https://your-frontend.vercel.app
CHART_RENDERER=quickchart
```

5. Deploy. Verify at `https://your-backend.vercel.app/health`

**Step 4: Deploy Frontend**

1. Create another Vercel project from the **same repo**
2. Set **Root Directory** to `frontend`
3. Framework Preset: Next.js (auto-detected)
4. Set Environment Variables:

```env
NEXT_PUBLIC_API_URL=/api/v1
NEXT_PUBLIC_API_KEY=<same-key-as-backend-API_KEYS>
BACKEND_URL=https://your-backend.vercel.app
```

Note: `NEXT_PUBLIC_API_URL=/api/v1` (not a full URL). Next.js rewrites in `next.config.ts` proxy `/api/v1/*` requests to `BACKEND_URL` server-side, so the backend URL is never exposed to the browser.

**Step 5: Setup Telegram Webhook**

Generate a hard-to-guess path first:
```bash
python3 -c "import secrets; print(f'bot-{secrets.token_hex(16)}')"
```

Set `WEBHOOK_PATH` to the generated value in your backend ENV, then call once:
```
GET https://your-backend.vercel.app/<WEBHOOK_PATH>/set-webhook?secret=<WEBHOOK_SECRET>
```

**Step 6: After First Deploy**

Set `AUTO_CREATE_TABLES=false` to prevent re-creating tables on every cold start.

#### Vercel Limitations

- **Chart rendering**: Node.js subprocess is not available. Set `CHART_RENDERER=quickchart` to use QuickChart.io API instead.
- **Cold start**: First request after idle may take 5-15 seconds.
- **Bot ConversationHandler**: Multi-step flows (registration, OCR confirm) store state in memory. On serverless, state may be lost between requests if the instance is recycled. For production bot usage, consider deploying the bot separately on Railway/Render.
- **Function timeout**: 10s (hobby) / 60s (pro). Long OCR processing may timeout on hobby plan.

---

### Docker (Self-Hosted)

```bash
docker-compose up --build
```

Services: PostgreSQL + Redis + FastAPI (with Node.js) + Telegram Bot + Next.js Frontend

### VPS / Bare Metal

```bash
# Backend
uvicorn app.main:app --host 0.0.0.0 --port 8888

# Bot (separate process)
python3 -m app.bot.main

# Frontend
cd frontend && npm run build && npm start
```

---

## Features

### Security & Privacy

* **Field-Level Encryption**: PII encrypted with AES-128 (Fernet) before storage.
* **Hashed Indexes**: Search by Citizen ID, phone, email without decrypting.
* **Data Portability**: Export via `/api/v1/export/my-data`.

### For Patients

* **Smart Recording**: Scan photo with AI or type values (`120/80/72` or `120 80 72`).
* **Auto-Save**: OCR data is automatically saved after 2 minutes if the user forgets to confirm.
* **Intelligent Timestamp**: OCR screen time > EXIF metadata > Current time.
* **Trends & History**: Free (30 records) / Premium (unlimited).
* **Doctor Access**: Grant or revoke access for doctors.

### For Doctors

* **Patient List**: View authorized patients.
* **Access Request**: Request access by patient ID.
* **Monitoring**: View patient BP history and charts.

### Subscription & Payments

* **Free Tier**: 30-record limit, basic stats.
* **Premium**: Unlimited history, data export. Payment via bank slip verification (SlipOK API).

### Localization

Fully bilingual: English and Thai. Change via web settings or Telegram `/language` command.

---

## Telegram Bot

### Bot Modes

| Mode | Use Case | How |
|------|----------|-----|
| **Polling** | Local dev, VPS | `python3 -m app.bot.main` |
| **Webhook** | Vercel, serverless | Set `BOT_MODE=webhook` + call `/set-webhook` |
| **Disabled** | Frontend-only deploy | Set `BOT_MODE=disabled` |

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Register or connect account |
| `/stats` | View BP statistics + chart |
| `/settings` | Change language, timezone |
| `/upgrade` | Upgrade to Premium |
| `/subscription` | Check subscription status |
| `/help` | Show all commands |
| `/edit` | Edit a recent BP record |
| `/delete` | Delete a BP record |
| `/broadcast` | **[Admin]** Send messages to all users |
| *Send photo* | AI extracts BP values (Auto-saves after 2 mins) |
| *Type text* | Enter BP manually (e.g. `120 80 72` or `120/80/72`) |

### Webhook Security

Two layers protect the webhook endpoint:
* **Layer 1**: `WEBHOOK_PATH` -- random URL path (e.g., `/bot-f77192489b.../webhook`)
* **Layer 2**: `WEBHOOK_SECRET` -- Telegram sends `X-Telegram-Bot-Api-Secret-Token` header for verification

---

## Chart Generation

Server-side BP trend charts with dual renderer:

```
Python (chart_generator.py) → JSON stdin → Node.js (render.js) → PNG stdout
```

| Renderer | When to Use | Quality |
|----------|-------------|---------|
| **Node.js** (`chart-renderer/`) | Docker, VPS | Best |
| **QuickChart.io** | Vercel, serverless | Good |

Set via `CHART_RENDERER` env: `auto` (default) / `nodejs` / `quickchart`

- **API**: `GET /api/v1/stats/chart?days=30&lang=th` -- returns PNG
- **Bot**: `/stats` sends chart image automatically

---

## Project Structure

```
BP/
├── api/
│   └── index.py               # Vercel entry point (imports app.main)
├── app/                        # Backend (FastAPI)
│   ├── main.py                # App entry, CORS, routers, webhook
│   ├── models.py              # SQLAlchemy models
│   ├── schemas.py             # Pydantic validation
│   ├── database.py            # DB connection (SQLite / PostgreSQL)
│   ├── otp_service.py         # OTP dual backend (Memory / Redis)
│   ├── __init__.py            # Package marker
│   ├── routers/               # API endpoints
│   │   ├── auth.py            # OTP, login, register, JWT
│   │   ├── users.py           # Profile management
│   │   ├── bp_records.py      # CRUD + stats + chart
│   │   ├── doctor.py          # Doctor-patient relationships
│   │   ├── ocr.py             # Gemini OCR
│   │   ├── payment.py         # Subscription handling
│   │   └── export.py          # Data export
│   ├── bot/                   # Telegram bot (polling + webhook)
│   │   ├── main.py            # build_application() + run_polling()
│   │   ├── webhook.py         # FastAPI webhook handler
│   │   ├── handlers.py        # Conversation handlers
│   │   ├── payment_handlers.py
│   │   ├── services.py        # Bot business logic
│   │   └── locales.py         # i18n (EN, TH)
│   ├── chart-renderer/        # Node.js chart renderer
│   ├── utils/                 # Shared utilities
│   │   ├── security.py        # JWT, hashing, API key
│   │   ├── encryption.py      # Fernet encryption
│   │   ├── rate_limiter.py    # Centralized (Memory / Redis)
│   │   ├── chart_generator.py # Chart generation wrapper
│   │   ├── ocr_helper.py      # Gemini integration
│   │   └── timezone.py        # Timezone utilities
│   └── config/
│       └── pricing.py         # Subscription plans
├── frontend/                   # Next.js 16 web dashboard
│   ├── app/                   # Pages (auth, dashboard, settings)
│   ├── proxy.ts               # Auth guard (Next.js 16)
│   ├── next.config.ts         # API rewrites + standalone
│   ├── lib/api.ts             # Axios client
│   └── Dockerfile             # Standalone build
├── tests/                      # Test suite (pytest)
├── vercel.json                 # Vercel deployment config
├── requirements.txt            # Root deps (for Vercel)
├── Dockerfile                  # Backend (Python + Node.js)
└── docker-compose.yml          # Full stack deployment
```

---

## Testing

```bash
python3 -m pytest tests/ -v
```

---

## License

Dual-licensed: **AGPL-3.0** (open source) + **Commercial License** (proprietary use).

| Use Case | License | Cost |
|----------|---------|------|
| Personal / educational | AGPL-3.0 | Free |
| Open source (AGPL-compatible) | AGPL-3.0 | Free |
| Internal company use (source private) | Commercial | Contact |
| SaaS / hospital deployment | Commercial | Contact |

Contact for licensing: [GitHub Profile](https://github.com/kaebmoo)

See [LICENSE](LICENSE) and [LICENSE-COMMERCIAL.md](LICENSE-COMMERCIAL.md) for details.
