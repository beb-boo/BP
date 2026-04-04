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
│   ├── models.py          # SQLAlchemy models (User, BloodPressureRecord, DoctorPatient, Payment, AdminAuditLog)
│   ├── schemas.py         # Pydantic validation schemas
│   ├── database.py        # DB connection & session setup
│   ├── routers/           # API endpoints
│   │   ├── auth.py       # OTP, login, register, JWT
│   │   ├── users.py      # Profile management
│   │   ├── bp_records.py # CRUD for BP measurements, stats
│   │   ├── doctor.py     # Doctor-patient relationships (verified doctor enforced)
│   │   ├── admin.py      # Staff-only membership admin (masked PII, audit log)
│   │   ├── ocr.py        # Image processing via Gemini
│   │   ├── payment.py    # Subscription handling
│   │   └── export.py     # CSV/PDF export
│   ├── services/          # Shared business logic
│   │   └── payment_service.py  # Unified payment verification (Web + Bot)
│   ├── bot/              # Telegram bot (dual-mode: polling + webhook)
│   │   ├── main.py       # Bot entry, build_application(), run_polling()
│   │   ├── webhook.py    # FastAPI webhook handler for serverless
│   │   ├── handlers.py   # Conversation handlers (/bp, /stats, OCR, etc.)
│   │   └── locales.py    # i18n (EN, TH)
│   ├── chart-renderer/    # Server-side Chart.js renderer (Node.js)
│   │   ├── render.js     # Chart.js + @napi-rs/canvas → PNG
│   │   └── package.json  # npm dependencies
│   ├── otp_service.py    # OTP with dual backend (Memory / Redis)
│   └── utils/            # Shared utilities
│       ├── security.py   # JWT, hashing, API key, require_verified_doctor, require_staff
│       ├── encryption.py # Fernet field-level encryption
│       ├── subscription.py # Single source of truth for subscription state
│       ├── rate_limiter.py # Centralized rate limiter (Memory / Redis)
│       ├── chart_generator.py # BP chart generation (calls Node.js subprocess)
│       ├── timezone.py   # Centralized timezone handling
│       └── ocr_helper.py # Gemini integration
│   ├── routers/
│   │   └── telegram_auth.py # Telegram Mini App auth (HMAC verify → JWT)
├── migrations/           # Manual schema migration scripts
│   ├── migrate_schema.py # Main migration (language, admin_audit_logs)
│   └── add_admin_audit_log.py # Standalone AdminAuditLog migration
├── frontend/             # Next.js web dashboard
│   ├── app/              # App directory structure
│   │   ├── auth/        # Login/register pages
│   │   ├── (dashboard)/ # Protected dashboard routes
│   │   ├── telegram/bp/ # Telegram Mini App (auto-login BP recording)
│   │   ├── error.tsx    # Custom error page
│   │   └── not-found.tsx # Custom 404 page
│   ├── proxy.ts          # Auth guard (Next.js 16, replaces middleware.ts)
│   ├── lib/api.ts       # Axios instance (base: localhost:8888/api/v1)
│   ├── lib/telegram.ts  # Telegram WebApp SDK types + helpers
│   └── contexts/        # React contexts (Language)
└── MobileApp/           # React Native (Expo)
```

## Key Patterns

### Authentication Flow

- OTP-based authentication via email/SMS
- JWT tokens (7-day expiry) in `Authorization: Bearer` header
- API key required in `X-API-Key` header
- Account locking after failed login attempts
- **Telegram Mini App**: HMAC-SHA256 verify `initData` → issue JWT (no API key needed for auth endpoint)

### Data Encryption

- Field-level Fernet encryption for PII (email, phone, citizen_id, medical_license, full_name)
- Hashed indexes for unique lookups without decrypting entire DB
- Encryption key from `ENCRYPTION_KEY` environment variable

### BP Record Timestamps

Priority: OCR screen time → EXIF metadata → Current time

### Subscription Tiers

- Free: 30 records limit, basic stats (avg/min/max + BP classification)
- Premium: Unlimited history, advanced stats (SD, CV, PP, MAP, Trend), export features
- `PREMIUM_BYPASS_USERS` env: comma-separated user IDs, Telegram IDs, or phone numbers for testing

### Clinical Statistics (Stats Endpoint)

`GET /api/v1/stats/summary?days=30` returns clinical metrics:

| Metric | Formula | Free | Premium |
|--------|---------|------|---------|
| **Average** | `sum(values) / n` | Yes | Yes |
| **Min / Max** | `min(values)`, `max(values)` | Yes | Yes |
| **BP Classification** | AHA/ACC 2017: Normal (<120/<80), Elevated (120-129/<80), Stage 1 (130-139/80-89), Stage 2 (>=140/>=90), Crisis (>180/>120) | Yes | Yes |
| **SD (Std Dev)** | `sqrt(sum((x - mean)^2) / (n-1))` — requires >= 2 records | No | Yes |
| **Median** | Middle value when sorted | No | Yes |
| **CV (Coeff of Variation)** | `(SD / Mean) * 100` (%) | No | Yes |
| **Pulse Pressure (PP)** | `avg_SBP - avg_DBP` — >60 = arterial stiffness | No | Yes |
| **MAP (Mean Arterial Pressure)** | `(avg_SBP + 2 * avg_DBP) / 3` — >=65 = adequate perfusion | No | Yes |
| **Trend (Linear Regression)** | Slope via least squares: `slope = (n*sum(xi*yi) - sum(xi)*sum(yi)) / (n*sum(xi^2) - sum(xi)^2)` where xi = day index, yi = SBP/DBP | No | Yes |

**Rounding**: API returns 1 decimal (`round(x, 1)`). Display uses half-up rounding: Python `math.floor(x + 0.5)`, JavaScript `Math.round(x)`.

### Telegram Mini App

- **Route**: `/telegram/bp` — WebApp opened from Telegram chat button
- **Auth flow**: `initData` (HMAC-SHA256 signed by BOT_TOKEN) → `POST /api/v1/auth/telegram/mini-app-auth` → JWT
- **UI**: BP form + OCR photo upload + Stats (tier-aware) + 5 recent records
- **Bot commands**: `/bp` opens Mini App button, `/start` shows it in welcome
- **SDK**: `telegram-web-app.js` loaded in `frontend/app/telegram/layout.tsx`
- **No separate auth needed**: JWT from mini-app-auth works with all existing API endpoints

### User Roles & Access Control

Three roles: `patient`, `doctor`, `staff`. Role-specific behavior:

| Role | Dashboard View | Special Guards |
|------|---------------|----------------|
| **patient** | BP records, stats, doctor access management | Standard `get_current_user` |
| **doctor** | Patient list, BP record viewer | `require_verified_doctor` — must have `verification_status == "verified"` |
| **staff** | Admin panel (users, pending doctors, audit log) | `require_staff` + optional `STAFF_ALLOWLIST` env |

- Doctor-only endpoints (request access, view patients, view BP records, cancel request) enforce verified status
- Patient cannot authorize a doctor whose license is not yet verified
- Staff admin panel shows only masked PII — no health data (BP records, citizen_id, DOB, etc.)

### Staff Admin Panel

Staff-only membership admin at `/api/v1/admin/*`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/users` | GET | List users with filters (role, verification_status, is_active), masked PII, pagination |
| `/admin/users/{id}` | GET | User detail (masked) + sanitized verification_logs for doctors |
| `/admin/users/{id}/payments` | GET | Payment history for a user |
| `/admin/users/{id}/verify` | POST | Verify/reject doctor license (requires reason) |
| `/admin/users/{id}/deactivate` | POST | Deactivate user (requires reason, cannot target self/staff) |
| `/admin/users/{id}/activate` | POST | Reactivate user (requires reason, cannot target other staff) |
| `/admin/audit-log` | GET | View admin action audit log, paginated |

All admin endpoints require both `require_staff` and `verify_api_key` dependencies. All state-changing actions write to `AdminAuditLog` atomically with the state change.

**`STAFF_ALLOWLIST`** env (optional): comma-separated user IDs. If set, only listed staff can access admin endpoints.

### Database Migrations

No Alembic — manual migration scripts in `migrations/`:

```bash
# Run all migrations (idempotent, safe to re-run)
python3 -m migrations.run_all
```

Migrations handle both SQLite and PostgreSQL. The `.vscode/tasks.json` "Run DB Migrations" task uses the same unified runner as other task configs.

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
STAFF_SYNC_MODE=dry-run      # Recommended for first env-managed staff rollout
```

For existing Vercel databases, run `python3 -m migrations.run_all` before turning `AUTO_CREATE_TABLES=false`. Do not rely on serverless request handling to perform schema upgrades.
For env-managed staff rollout on Vercel, start with `STAFF_SYNC_MODE=dry-run`, inspect `[staff-sync] Would ...` logs, then switch to `apply` only after the migration for `staff_management_states` is present.

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
TELEGRAM_WEBAPP_URL=    # Mini App URL (HTTPS required, e.g. https://frontend.vercel.app/telegram/bp)
WEB_DASHBOARD_URL=      # Web dashboard URL shown in bot /stats
PREMIUM_BYPASS_USERS=   # Comma-separated: user IDs, Telegram IDs, phone numbers
STAFF_ALLOWLIST=        # Leave unset to skip sync; use NONE to demote env-managed staff; prefer user:/email:/phone:/telegram:
STAFF_SYNC_MODE=apply   # dry-run | apply
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
