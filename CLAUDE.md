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
│   ├── otp_service.py    # OTP with dual backend (Memory / Redis)
│   └── utils/            # Shared utilities
│       ├── security.py   # JWT, hashing, API key verification
│       ├── encryption.py # Fernet field-level encryption
│       ├── rate_limiter.py # Centralized rate limiter (Memory / Redis)
│       └── ocr_helper.py # Gemini integration
├── frontend/             # Next.js web dashboard
│   ├── app/              # App directory structure
│   │   ├── auth/        # Login/register pages
│   │   ├── (dashboard)/ # Protected dashboard routes
│   │   ├── error.tsx    # Custom error page
│   │   └── not-found.tsx # Custom 404 page
│   ├── middleware.ts     # Auth guard (redirect unauthenticated)
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
```

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
NEXT_PUBLIC_API_KEY=    # Frontend API key override
ALLOWED_ORIGINS=*       # CORS origins (comma-separated)
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

## Known Limitations

- No automated test suite (critical gap)
- No Alembic migrations - schema changes are manual (use `migrations/` scripts)
- CORS allows all origins (`*`) - restrict in production
- Image audit trail not implemented (images deleted after OCR)
