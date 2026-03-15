# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Blood Pressure Monitor & Telemedicine Platform - a full-stack healthcare application for tracking blood pressure with doctor-patient relationship management.

**Tech Stack:**

- Backend: Python FastAPI with SQLAlchemy ORM
- Frontend: Next.js 16 (React 19, TypeScript, Tailwind CSS v4)
- Mobile: React Native (Expo)
- Telegram Bot: python-telegram-bot
- Database: SQLite (dev) / PostgreSQL (prod)
- AI/OCR: Google Gemini API
- Chart Rendering: Chart.js via Node.js (@napi-rs/canvas)

## Common Commands

### Backend

```bash
# Install dependencies
pip install -r app/requirements.txt

# Run API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8888

# Run Telegram bot (separate terminal)
python3 -m app.bot.main

# API documentation available at http://localhost:8888/docs

# Install chart renderer (required for BP chart generation)
cd app/chart-renderer && npm install
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # Development server (localhost:3000)
npm run build        # Production build
npm run lint         # ESLint check
```

### Mobile

```bash
cd MobileApp
npm install
npm start            # Expo development server
```

### Docker

```bash
docker-compose up --build  # Runs PostgreSQL + Redis + FastAPI + Bot + Frontend
```

## Architecture

```
BP/
├── app/                    # Backend (FastAPI)
│   ├── main.py            # App entry point, CORS, rate limiting
│   ├── models.py          # SQLAlchemy models (User, BloodPressureRecord, DoctorPatient, Payment)
│   ├── schemas.py         # Pydantic validation schemas
│   ├── database.py        # DB connection & session setup
│   ├── routers/           # API endpoints
│   │   ├── auth.py       # OTP, login, register, JWT
│   │   ├── users.py      # Profile management
│   │   ├── bp_records.py # CRUD for BP measurements, stats
│   │   ├── doctor.py     # Doctor-patient relationships
│   │   ├── ocr.py        # Image processing via Gemini
│   │   ├── payment.py    # Subscription handling
│   │   └── export.py     # CSV/PDF export
│   ├── bot/              # Telegram bot (dual-mode: polling + webhook)
│   │   ├── main.py       # Bot entry, build_application(), run_polling()
│   │   ├── webhook.py    # FastAPI webhook handler for serverless
│   │   ├── handlers.py   # Conversation handlers
│   │   └── locales.py    # i18n (EN, TH)
│   ├── chart-renderer/    # Server-side Chart.js renderer (Node.js)
│   │   ├── render.js     # Chart.js + @napi-rs/canvas → PNG
│   │   └── package.json  # npm dependencies
│   ├── otp_service.py    # OTP with dual backend (Memory / Redis)
│   └── utils/            # Shared utilities
│       ├── security.py   # JWT, hashing, API key verification
│       ├── encryption.py # Fernet field-level encryption
│       ├── rate_limiter.py # Centralized rate limiter (Memory / Redis)
│       ├── chart_generator.py # BP chart generation (calls Node.js subprocess)
│       └── ocr_helper.py # Gemini integration
├── frontend/             # Next.js web dashboard
│   ├── app/              # App directory structure
│   │   ├── auth/        # Login/register pages
│   │   ├── (dashboard)/ # Protected dashboard routes
│   │   ├── error.tsx    # Custom error page
│   │   └── not-found.tsx # Custom 404 page
│   ├── proxy.ts          # Auth guard (Next.js 16, replaces middleware.ts)
│   ├── lib/api.ts       # Axios instance (base: localhost:8888/api/v1)
│   └── contexts/        # React contexts (Language)
└── MobileApp/           # React Native (Expo)
```

## Key Patterns

### Authentication Flow

- OTP-based authentication via email/SMS
- JWT tokens (7-day expiry) in `Authorization: Bearer` header
- API key required in `X-API-Key` header
- Account locking after failed login attempts

### Data Encryption

- Field-level Fernet encryption for PII (email, phone, citizen_id, medical_license, full_name)
- Hashed indexes for unique lookups without decrypting entire DB
- Encryption key from `ENCRYPTION_KEY` environment variable

### BP Record Timestamps

Priority: OCR screen time → EXIF metadata → Current time

### Subscription Tiers

- Free: 30-day history limit
- Premium: Unlimited history, export features

## Deployment Modes

### Local Development (SQLite + Memory)
```bash
# No Redis needed, OTP stored in memory, rate limiting in memory
DATABASE_URL=sqlite:///./blood_pressure.db
BOT_MODE=polling
AUTO_CREATE_TABLES=true
BYPASS_OTP=true  # Optional: skip OTP for dev
```

### Production (PostgreSQL + Redis)
```bash
DATABASE_URL=postgresql://user:pass@host:5432/bp_db
REDIS_URL=redis://redis:6379/0
BOT_MODE=webhook  # or "disabled"
WEBHOOK_URL=https://your-api-domain.com
WEBHOOK_SECRET=your-secret
AUTO_CREATE_TABLES=false  # Use migrations
```

### Docker
```bash
docker-compose up --build  # Runs PostgreSQL + Redis + FastAPI + Bot + Frontend
# Dockerfile includes Node.js installation for chart rendering
```

### Vercel (Serverless)

Frontend and Backend are **separate Vercel projects** from the same repo.

```bash
# Frontend project — Root Directory: frontend
BACKEND_URL=https://your-backend.vercel.app  # Server-side (Next.js rewrites)
NEXT_PUBLIC_API_KEY=<your-api-key>

# Backend project — Root Directory: . (root)
DATABASE_URL=postgresql://...@neon.tech/bp_db?sslmode=require
REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379
SECRET_KEY=<new-strong-random-key>
ENCRYPTION_KEY=<new-fernet-key>
API_KEYS=<your-custom-api-keys>
BOT_MODE=webhook
WEBHOOK_URL=https://your-backend.vercel.app
WEBHOOK_SECRET=<random-secret>
CHART_RENDERER=quickchart   # Node.js subprocess unavailable on Vercel
AUTO_CREATE_TABLES=true      # Set false after first deploy
ALLOWED_ORIGINS=https://your-frontend.vercel.app
```

**Vercel-specific files:**
- `vercel.json` — routes all requests to `app/main.py` via `@vercel/python`
- `requirements.txt` (root) — mirrors `app/requirements.txt` for Vercel Python runtime
- `frontend/next.config.ts` — rewrites `/api/v1/*` to `BACKEND_URL`

## Environment Variables

Required in `.env` (see `.env.example` for full list):

```
DATABASE_URL=sqlite:///./blood_pressure.db
SECRET_KEY=<jwt-secret>
ENCRYPTION_KEY=<fernet-key>
API_KEYS=bp-mobile-app-key,bp-web-app-key
GOOGLE_AI_API_KEY=<gemini-api-key>
TELEGRAM_BOT_TOKEN=<bot-token>
APP_TIMEZONE=Asia/Bangkok  # Default timezone for server (IANA format)
```

Optional:
```
REDIS_URL=              # Redis for OTP/rate limiting (serverless)
BOT_MODE=polling        # polling | webhook | disabled
WEBHOOK_URL=            # Required when BOT_MODE=webhook
WEBHOOK_SECRET=         # Required when BOT_MODE=webhook
AUTO_CREATE_TABLES=true # Set false in prod with migrations
BYPASS_OTP=false        # Set true for dev only
JWT_ALGORITHM=HS256          # JWT signing algorithm
ACCESS_TOKEN_EXPIRE_DAYS=7   # JWT token expiry in days
MAX_LOGIN_ATTEMPTS=5         # Failed logins before account lock
ACCOUNT_LOCK_MINUTES=30      # Account lock duration in minutes
OTP_EXPIRE_MINUTES=5         # OTP code expiry in minutes
GEMINI_MODEL=gemini-2.0-flash # Google AI model for OCR
NEXT_PUBLIC_API_KEY=    # Frontend API key override
ALLOWED_ORIGINS=*       # CORS origins (comma-separated)
CHART_RENDERER=auto     # auto | nodejs | quickchart
BACKEND_URL=            # Frontend rewrites target (server-side, Vercel only)
```

## API Response Format

```json
{
  "status": "success|error",
  "message": "...",
  "data": {...},
  "meta": {...},
  "request_id": "uuid"
}
```

## Scope

**MobileApp - ไม่อยู่ในขอบเขตการพัฒนา:** โฟลเดอร์ `MobileApp/` ยังไม่มีแผนพัฒนาในตอนนี้ ไม่ต้องวิเคราะห์หรือแก้ไข code ใน MobileApp

## Timezone Configuration

Users can set their preferred timezone:
- **Backend:** `app/utils/timezone.py` provides centralized timezone handling
- **User Model:** `timezone` field stores user preference (IANA format, default: Asia/Bangkok)
- **API:** Users can update timezone via `PUT /users/me`
- **Telegram Bot:** `/settings` command allows timezone selection
- **Frontend:** Settings page has timezone selector

## Chart Generation

Server-side BP trend chart rendering with dual renderer support:

- **Node.js renderer:** `app/chart-renderer/render.js` — Chart.js + @napi-rs/canvas → PNG (best quality)
- **QuickChart.io renderer:** `app/utils/chart_generator.py` — HTTP API, works on any platform
- **Python wrapper:** `app/utils/chart_generator.py` — auto-selects renderer via `CHART_RENDERER` env
- **API endpoint:** `GET /api/v1/stats/chart?days=30&lang=en` — returns PNG image
- **Telegram Bot:** `/stats` command sends chart image after text stats
- **`CHART_RENDERER`:** `auto` (default) = Node.js if available, else QuickChart.io | `nodejs` | `quickchart`
- **Node.js requires:** Node.js installed + `npm install` in `app/chart-renderer/`

## Known Limitations

- No Alembic migrations - schema changes are manual (use `migrations/` scripts)
- CORS allows all origins (`*`) - restrict in production
- Image audit trail not implemented (images deleted after OCR)
- Chart generation: Node.js renderer for Docker/VPS, QuickChart.io for Vercel/serverless
- Vercel serverless: 10s timeout (hobby), Node.js subprocess not available
