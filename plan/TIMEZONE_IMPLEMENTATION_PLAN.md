# Timezone Implementation Plan

## Overview

แผนการแก้ไขระบบ Timezone จาก hardcoded "Asia/Bangkok" ให้รองรับการปรับเปลี่ยนได้ตามเวลาท้องถิ่นของผู้ใช้

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Database: เก็บเป็น UTC เสมอ                                 │
│  ↓                                                          │
│  Backend API: ส่งออกเป็น ISO 8601 (UTC)                      │
│  ↓                                                          │
│  Frontend/Bot: แปลงเป็น user timezone ตอนแสดงผล              │
└─────────────────────────────────────────────────────────────┘
```

## Task Checklist

### Phase 1: Backend Core Changes ✅ COMPLETED

- [x] 1.1 สร้างไฟล์ `app/utils/timezone.py` - utility functions กลาง
- [x] 1.2 เพิ่ม `APP_TIMEZONE` ใน `.env.example`
- [x] 1.3 แก้ไข `app/models.py` - เพิ่ม timezone field ใน User model
- [x] 1.4 แก้ไข `app/schemas.py` - เพิ่ม timezone ใน schemas
- [x] 1.5 แก้ไข `app/utils/security.py` - ใช้ timezone.py
- [x] 1.6 แก้ไข `app/utils/ocr_helper.py` - ใช้ timezone.py
- [x] 1.7 แก้ไข `app/routers/export.py` - ใช้ timezone-aware datetime
- [x] 1.8 สร้าง database migration script (`migrations/add_timezone_column.py`)

### Phase 2: Backend API Updates ✅ COMPLETED

- [x] 2.1 แก้ไข `app/routers/users.py` - API สำหรับ update timezone + GET /timezones endpoint
- [x] 2.2 แก้ไข `app/routers/auth.py` - set default timezone เมื่อ register, return timezone in login response

### Phase 3: Telegram Bot ✅ COMPLETED

- [x] 3.1 แก้ไข `app/bot/locales.py` - เพิ่ม messages สำหรับ timezone (EN/TH)
- [x] 3.2 แก้ไข `app/bot/handlers.py` - เพิ่ม /settings command และ timezone selection
- [x] 3.3 แก้ไข `app/bot/services.py` - ใช้ now_tz() และเพิ่ม update_user_timezone()
- [x] 3.4 แก้ไข `app/bot/main.py` - register settings handlers

### Phase 4: Frontend ✅ COMPLETED

- [x] 4.1 สร้าง `frontend/lib/date-utils.ts` - utility functions
- [x] 4.2 แก้ไข translations (`locales/en.ts`, `locales/th.ts`) - เพิ่ม timezone labels
- [x] 4.3 แก้ไข `frontend/app/(dashboard)/settings/page.tsx` - timezone selector

### Phase 5: Testing & Documentation ✅ COMPLETED

- [x] 5.1 Run database migration
- [x] 5.2 อัปเดต CLAUDE.md

---

## Files Modified

### Backend (app/)
- `app/utils/timezone.py` - NEW: Centralized timezone utilities
- `app/models.py` - Added `timezone` field to User model
- `app/schemas.py` - Added `timezone` to UserRegister, UserProfileResponse, UserProfileUpdate
- `app/utils/security.py` - Replaced `now_th()` with `now_tz()` from timezone.py
- `app/utils/ocr_helper.py` - Replaced `now_th()` with `now_tz()`
- `app/routers/export.py` - Use timezone-aware datetime
- `app/routers/users.py` - Added `/timezones` endpoint, use `now_tz()`
- `app/routers/auth.py` - Return timezone in login response, set default on register

### Telegram Bot (app/bot/)
- `app/bot/locales.py` - Added timezone-related messages (EN/TH)
- `app/bot/handlers.py` - Added settings_command, settings_callback, timezone_callback
- `app/bot/services.py` - Added update_user_timezone(), replaced `now_th()` with `now_tz()`
- `app/bot/main.py` - Registered /settings command and callbacks

### Frontend (frontend/)
- `frontend/lib/date-utils.ts` - NEW: Date formatting utilities with timezone support
- `frontend/locales/en.ts` - Added timezone translations
- `frontend/locales/th.ts` - Added timezone translations (Thai)
- `frontend/app/(dashboard)/settings/page.tsx` - Added timezone selector dropdown

### Migrations
- `migrations/__init__.py` - NEW
- `migrations/add_timezone_column.py` - NEW: Migration script

### Documentation
- `CLAUDE.md` - Updated with timezone configuration section
- `.env.example` - Added APP_TIMEZONE variable

---

## Environment Variables

เพิ่มใน `.env`:
```
APP_TIMEZONE=Asia/Bangkok
```

## Database Migration

Run migration:
```bash
# Using sqlite3 directly:
sqlite3 blood_pressure.db "ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'Asia/Bangkok';"

# Or using the migration script (requires SQLAlchemy in environment):
python3 -m migrations.add_timezone_column
```

---

## Progress Tracking

Started: 2026-01-15
Last Updated: 2026-01-15
Status: **COMPLETED** ✅

### Summary
- All phases completed successfully
- Database migration applied
- Documentation updated
- Ready for testing in development environment
