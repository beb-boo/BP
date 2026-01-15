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

### Phase 1: Backend Core Changes

- [ ] 1.1 สร้างไฟล์ `app/utils/timezone.py` - utility functions กลาง
- [ ] 1.2 เพิ่ม `APP_TIMEZONE` ใน `.env.example`
- [ ] 1.3 แก้ไข `app/models.py` - เพิ่ม timezone field ใน User model
- [ ] 1.4 แก้ไข `app/schemas.py` - เพิ่ม timezone ใน schemas
- [ ] 1.5 แก้ไข `app/utils/security.py` - ใช้ timezone.py
- [ ] 1.6 แก้ไข `app/utils/ocr_helper.py` - ใช้ timezone.py
- [ ] 1.7 แก้ไข `app/routers/export.py` - ใช้ timezone-aware datetime
- [ ] 1.8 สร้าง database migration script

### Phase 2: Backend API Updates

- [ ] 2.1 แก้ไข `app/routers/users.py` - API สำหรับ update timezone
- [ ] 2.2 แก้ไข `app/routers/auth.py` - set default timezone เมื่อ register
- [ ] 2.3 แก้ไข `app/routers/bp_records.py` - return timezone-aware data

### Phase 3: Telegram Bot

- [ ] 3.1 แก้ไข `app/bot/locales.py` - เพิ่ม messages สำหรับ timezone
- [ ] 3.2 แก้ไข `app/bot/handlers.py` - เพิ่ม timezone settings handler
- [ ] 3.3 แก้ไข `app/bot/services.py` - ใช้ user timezone

### Phase 4: Frontend

- [ ] 4.1 สร้าง `frontend/lib/date-utils.ts` - utility functions
- [ ] 4.2 แก้ไข translations - เพิ่ม timezone labels
- [ ] 4.3 แก้ไข `frontend/app/(dashboard)/settings/page.tsx` - timezone selector
- [ ] 4.4 แก้ไข `frontend/components/bp-chart.tsx` - ใช้ date-utils
- [ ] 4.5 แก้ไข `frontend/app/(dashboard)/dashboard/page.tsx` - ใช้ date-utils
- [ ] 4.6 แก้ไข `frontend/app/(dashboard)/subscription/page.tsx` - ใช้ date-utils

### Phase 5: Testing & Documentation

- [ ] 5.1 ทดสอบ Backend API
- [ ] 5.2 ทดสอบ Telegram Bot
- [ ] 5.3 ทดสอบ Frontend
- [ ] 5.4 อัปเดต CLAUDE.md

---

## Implementation Details

### 1.1 app/utils/timezone.py

```python
import os
from datetime import datetime
from typing import Optional
from pytz import timezone, UTC
from pytz.exceptions import UnknownTimeZoneError

# Default timezone from environment variable
DEFAULT_TIMEZONE = os.getenv("APP_TIMEZONE", "UTC")

# Common timezone choices
TIMEZONE_CHOICES = [
    ("UTC", "UTC (Coordinated Universal Time)"),
    ("Asia/Bangkok", "Asia/Bangkok (ICT, UTC+7)"),
    ("Asia/Tokyo", "Asia/Tokyo (JST, UTC+9)"),
    ("Asia/Singapore", "Asia/Singapore (SGT, UTC+8)"),
    ("Asia/Hong_Kong", "Asia/Hong Kong (HKT, UTC+8)"),
    ("Asia/Seoul", "Asia/Seoul (KST, UTC+9)"),
    ("Asia/Shanghai", "Asia/Shanghai (CST, UTC+8)"),
    ("America/New_York", "America/New York (EST/EDT, UTC-5/-4)"),
    ("America/Los_Angeles", "America/Los Angeles (PST/PDT, UTC-8/-7)"),
    ("Europe/London", "Europe/London (GMT/BST, UTC+0/+1)"),
    ("Europe/Paris", "Europe/Paris (CET/CEST, UTC+1/+2)"),
    ("Australia/Sydney", "Australia/Sydney (AEST/AEDT, UTC+10/+11)"),
]

def get_timezone(tz_name: Optional[str] = None):
    """Get timezone object by name, fallback to default"""
    tz_name = tz_name or DEFAULT_TIMEZONE
    try:
        return timezone(tz_name)
    except UnknownTimeZoneError:
        return timezone(DEFAULT_TIMEZONE)

def now_utc() -> datetime:
    """Get current time in UTC"""
    return datetime.now(UTC)

def now_tz(tz_name: Optional[str] = None) -> datetime:
    """Get current time in specified timezone"""
    return datetime.now(get_timezone(tz_name))

def to_user_timezone(dt: datetime, user_tz: Optional[str] = None) -> datetime:
    """Convert datetime to user's timezone"""
    if dt.tzinfo is None:
        dt = UTC.localize(dt)
    return dt.astimezone(get_timezone(user_tz))

def to_utc(dt: datetime, source_tz: Optional[str] = None) -> datetime:
    """Convert datetime to UTC"""
    if dt.tzinfo is None:
        source = get_timezone(source_tz)
        dt = source.localize(dt)
    return dt.astimezone(UTC)

def format_datetime(dt: datetime, user_tz: Optional[str] = None,
                   fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime in user's timezone"""
    local_dt = to_user_timezone(dt, user_tz)
    return local_dt.strftime(fmt)

def is_valid_timezone(tz_name: str) -> bool:
    """Check if timezone name is valid"""
    try:
        timezone(tz_name)
        return True
    except UnknownTimeZoneError:
        return False
```

### 1.3 User Model Changes

เพิ่ม field ใน User model:
```python
timezone = Column(String(50), default="Asia/Bangkok")
```

### 4.1 frontend/lib/date-utils.ts

```typescript
// Timezone choices matching backend
export const TIMEZONE_CHOICES = [
  { value: "UTC", label: { en: "UTC (Coordinated Universal Time)", th: "UTC (เวลาสากลเชิงพิกัด)" } },
  { value: "Asia/Bangkok", label: { en: "Asia/Bangkok (ICT, UTC+7)", th: "เอเชีย/กรุงเทพ (ICT, UTC+7)" } },
  { value: "Asia/Tokyo", label: { en: "Asia/Tokyo (JST, UTC+9)", th: "เอเชีย/โตเกียว (JST, UTC+9)" } },
  // ... more timezones
];

export function formatDate(
  date: string | Date,
  timezone?: string,
  locale: string = "en-GB",
  options?: Intl.DateTimeFormatOptions
): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleDateString(locale, {
    timeZone: timezone,
    ...options,
  });
}

export function formatTime(
  date: string | Date,
  timezone?: string,
  locale: string = "en-GB"
): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleTimeString(locale, {
    timeZone: timezone,
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDateTime(
  date: string | Date,
  timezone?: string,
  locale: string = "en-GB"
): string {
  return `${formatDate(date, timezone, locale)} ${formatTime(date, timezone, locale)}`;
}
```

---

## Environment Variables

เพิ่มใน `.env`:
```
APP_TIMEZONE=Asia/Bangkok
```

## Database Migration

```sql
-- Add timezone column to users table
ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'Asia/Bangkok';
```

---

## Progress Tracking

Started: 2026-01-15
Last Updated: 2026-01-15
Status: In Progress

### Completed Tasks
- (none yet)

### Current Task
- Starting Phase 1

### Blocked/Issues
- (none yet)
