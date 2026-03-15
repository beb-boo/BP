# BP Project - Improvement Plan
## แผนปรับปรุงสำหรับ Claude Code

> **เอกสารนี้ใช้คู่กับ plan/BP_Assessment.md**
> ให้ Claude Code อ่านทั้ง 2 ไฟล์ก่อนเริ่มทำงาน
> ทำงานทีละ Phase ตามลำดับ ห้ามข้าม Phase

---

## สารบัญ

- [Phase 1: Bug Fixes (Critical)](#phase-1-bug-fixes-critical)
- [Phase 2: Backend - Dual-Mode Storage](#phase-2-backend-dual-mode-storage)
- [Phase 3: Telegram Bot - Dual-Mode (Polling + Webhook)](#phase-3-telegram-bot-dual-mode)
- [Phase 4: Frontend Improvements](#phase-4-frontend-improvements)
- [Phase 5: Deployment Configuration](#phase-5-deployment-configuration)

---

## Phase 1: Bug Fixes (Critical)

> ทำก่อนทุก Phase เพราะมีผลกับการทำงานพื้นฐาน

### 1.1 แก้ `requirements.txt` - ขาด dependencies

**ไฟล์**: `app/requirements.txt`

**ปัญหา**: ขาด packages ที่ code ใช้จริง

**วิธีแก้**: เพิ่ม dependencies ที่ขาด

```
# เพิ่มบรรทัดเหล่านี้
pyotp              # ใช้ใน otp_service.py
pytz               # ใช้ใน timezone.py, security.py, schemas.py
bcrypt             # ใช้ใน security.py (passlib[bcrypt] อาจไม่ install bcrypt ตรง)
```

**ตรวจสอบ**: รัน `pip install -r app/requirements.txt` ต้องไม่ error

---

### 1.2 แก้ `background_tasks.py` - Import ไม่ครบ

**ไฟล์**: `app/utils/background_tasks.py`

**ปัญหา**: ไฟล์มีแค่ function แต่ไม่มี import statements ด้านบน จะ error ตอน doctor registration

**วิธีแก้**: เพิ่ม imports ที่จำเป็นทั้งหมดที่ต้นไฟล์

```python
import logging
from sqlalchemy.orm import Session
from ..models import User
from ..utils.tmc_checker import verify_doctor_with_tmc
from ..utils.timezone import now_th

logger = logging.getLogger(__name__)
```

**ตรวจสอบ**: import จะต้องไม่ circular กับ models.py หรือ database.py

---

### 1.3 แก้ `BotService.get_user_by_phone` - ใช้ property filter กับ encrypted column

**ไฟล์**: `app/bot/services.py`

**ปัญหา**: method `get_user_by_phone` ใช้ `User.phone_number == phone_number` ซึ่ง `phone_number` เป็น Python property (decrypt) ไม่ใช่ SQLAlchemy column ทำให้ query ไม่ทำงาน

**วิธีแก้**: เปลี่ยนเป็นใช้ hash lookup เหมือนที่ทำใน `auth.py`

```python
@staticmethod
def get_user_by_phone(phone_number: str):
    """Find a user by phone number via hash lookup."""
    phone_h = hash_value(phone_number)
    if not phone_h:
        return None
    with SessionLocal() as db:
        return db.query(User).filter(User.phone_number_hash == phone_h).first()
```

**ปัญหาเดียวกันใน**: `verify_user_password` ก็ใช้ `User.phone_number == phone_number` ต้องแก้เหมือนกัน

```python
@staticmethod
def verify_user_password(phone_number: str, password: str) -> User | None:
    """Verify password for a given phone number."""
    phone_h = hash_value(phone_number)
    if not phone_h:
        return None
    with SessionLocal() as db:
        user = db.query(User).filter(User.phone_number_hash == phone_h).first()
        if user and verify_password(password, user.password_hash):
            return user
        return None
```

---

### 1.4 แก้ Frontend Change Password - ไม่ส่ง `confirm_new_password`

**ไฟล์**: `frontend/app/(dashboard)/settings/page.tsx`

**ปัญหา**: Backend `PasswordChange` schema ต้องการ field `confirm_new_password` แต่ frontend ส่งแค่ `current_password` กับ `new_password` ทำให้ได้ 422 Validation Error

**วิธีแก้**: แก้ `handleChangePassword` ให้ส่ง `confirm_new_password` ด้วย

```typescript
const handleChangePassword = async (e: React.FormEvent) => {
    // ... validation ...
    try {
        await api.post("/auth/change-password", {
            current_password: currentPassword,
            new_password: newPassword,
            confirm_new_password: confirmPassword  // <<< เพิ่มบรรทัดนี้
        });
        // ...
    }
};
```

---

### 1.5 แก้ `get_ocr_handler()` ประกาศซ้ำ 2 ครั้ง

**ไฟล์**: `app/bot/handlers.py`

**ปัญหา**: function `get_ocr_handler()` ถูกประกาศ 2 ครั้ง ตัวที่ 2 (ท้ายไฟล์) override ตัวแรก

**วิธีแก้**: ลบ `get_ocr_handler()` ตัวแรก (ที่มีแค่ `filters.PHOTO`) เก็บเฉพาะตัวที่ 2 ที่รองรับ `filters.PHOTO | filters.Document.IMAGE` และมี `per_message=False`

---

### 1.6 แก้ OTP Bypass Comment ใน Registration

**ไฟล์**: `app/routers/auth.py`

**ปัญหา**: OTP verification ถูก comment out ด้วย `# bypass for demo` ทำให้ใครก็ register ได้โดยไม่ต้อง verify

**วิธีแก้**: เปลี่ยนให้ OTP bypass ถูกควบคุมด้วย ENV variable แทน

```python
import os
BYPASS_OTP = os.getenv("BYPASS_OTP", "false").lower() == "true"

# ในฟังก์ชัน register_user:
if not BYPASS_OTP:
    if not otp_service.is_verified(contact_target):
        raise HTTPException(
            status_code=400,
            detail="Please verify your contact information with OTP first"
        )
```

**ผลลัพธ์**: Dev ตั้ง `BYPASS_OTP=true`, Production ไม่ต้องตั้ง (default false)

---

### 1.7 แก้ Locales duplicate key `tz_select`

**ไฟล์**: `app/bot/locales.py`

**ปัญหา**: ทั้ง EN และ TH dict มี key `"tz_select"` ซ้ำ 2 บรรทัด (Python dict จะใช้ตัวหลังเท่านั้น)

**วิธีแก้**: ลบบรรทัดที่ซ้ำออก เก็บไว้แค่บรรทัดเดียว

---

### 1.8 แก้ `doctor.py` cancel_access_request - variable name conflict

**ไฟล์**: `app/routers/doctor.py`

**ปัญหา**: ใน `cancel_access_request` parameter `request_id: int` (URL path) ถูก override ด้วย `request_id = generate_request_id()` (UUID) ทำให้ query ใช้ UUID แทน int ที่ user ส่งมา

**วิธีแก้**: เปลี่ยนชื่อ internal request ID

```python
@router.delete("/doctor/access-requests/{request_id}", ...)
async def cancel_access_request(
    request_id: int,  # URL path parameter
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req_uuid = generate_request_id()  # <<< ใช้ชื่อ req_uuid แทน
    
    # ... ใช้ request_id (int) สำหรับ query
    req = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,  # ตอนนี้เป็น int ถูกต้อง
        ...
    ).first()
```

---

### 1.9 แก้ `bp_records.py` duplicate code - `pulse_values` ถูกประกาศ 2 ครั้ง

**ไฟล์**: `app/routers/bp_records.py`

**ปัญหา**: ใน `get_bp_stats` มีบรรทัด `pulse_values = [r.pulse for r in records]` ซ้ำ 2 บรรทัดติดกัน

**วิธีแก้**: ลบบรรทัดที่ซ้ำออก

---

## Phase 2: Backend - Dual-Mode Storage

> เป้าหมาย: ให้เลือกได้ว่าใช้ SQLite (dev/simple) หรือ PostgreSQL + Redis (production/serverless)
> ควบคุมด้วย Environment Variables

### 2.1 OTP Service - รองรับทั้ง Memory และ Redis

**ไฟล์ที่แก้**: `app/otp_service.py`

**แนวคิด**: สร้าง interface เดียวกัน แต่ backend storage เลือกได้ ถ้ามี REDIS_URL ใช้ Redis ถ้าไม่มีใช้ Memory (เหมือนเดิม)

**เพิ่มใน requirements.txt**: `redis` (เป็น optional dependency)

ดู code ตัวอย่างเต็มใน revision ก่อนหน้า

---

### 2.2 Rate Limiter - Centralize + Redis support

**ไฟล์ใหม่**: `app/utils/rate_limiter.py`

**แนวคิด**: ถ้ามี REDIS_URL ใช้ Redis storage สำหรับ slowapi

**แก้ไฟล์ที่ import limiter**: `app/main.py`, `app/routers/auth.py`, `app/routers/ocr.py`, `app/routers/payment.py` ให้ import จาก `app.utils.rate_limiter` แทน

---

### 2.3 Database - เพิ่ม Pool settings สำหรับ PostgreSQL

**ไฟล์**: `app/database.py`

**เพิ่ม connection pool settings เมื่อใช้ PostgreSQL**

---

### 2.4 แก้ `main.py` - ควบคุม auto-create tables ด้วย ENV

**ไฟล์**: `app/main.py`

```python
AUTO_CREATE_TABLES = os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true"

if AUTO_CREATE_TABLES:
    Base.metadata.create_all(bind=engine)
```

---

## Phase 3: Telegram Bot - Dual-Mode (Polling + Webhook)

> เป้าหมาย: รองรับทั้ง Long Polling (VPS/local) และ Webhook (Vercel/serverless)
> Webhook บน Vercel ได้ โดยใช้ FastAPI endpoint รับ update จาก Telegram

### 3.1 Refactor `bot/main.py` - แยก build_application ออกมา

**ไฟล์**: `app/bot/main.py`

**แนวคิด**: แยก Application building logic ออกจาก polling เพื่อให้ webhook ใช้ร่วมกันได้

สร้างฟังก์ชัน `build_application()` ที่ return Application instance พร้อม handlers ทั้งหมด แล้วแยก `run_polling()` เป็น function ต่างหาก

### 3.2 สร้าง Webhook Handler

**ไฟล์ใหม่**: `app/bot/webhook.py`

**แนวคิด**: สร้าง FastAPI router ที่มี:
- `POST /bot/webhook` - รับ Telegram updates
- `GET /bot/set-webhook?secret=xxx` - Utility ตั้ง webhook URL (เรียกครั้งเดียวตอน setup)
- `GET /bot/remove-webhook` - ลบ webhook (กลับไปใช้ polling)

### 3.3 แก้ `app/main.py` - เพิ่ม webhook router

```python
BOT_MODE = os.getenv("BOT_MODE", "polling")
if BOT_MODE == "webhook":
    from .bot.webhook import router as bot_webhook_router
    app.include_router(bot_webhook_router)
```

### 3.4 วิธีใช้งาน

**Polling** (local/VPS): รัน `python -m app.bot.main` เป็น process แยก
**Webhook** (Vercel): Deploy backend แล้วเรียก `GET /bot/set-webhook?secret=xxx` ครั้งเดียว

---

## Phase 4: Frontend Improvements

### 4.1 DoctorView - Fetch Real Data ✅ เสร็จแล้ว

**สถานะ**: ทำเสร็จแล้ว

`DoctorView` ใน `dashboard/page.tsx` fetch ข้อมูลจริงจาก API แล้ว:
- `GET /doctor/patients` → แสดง patient list + จำนวน
- `GET /doctor/access-requests` → แสดง pending requests + status
- Search Patient + Request Access
- Cancel pending request

### 4.2 Patient: Manage Authorized Doctors ✅ เสร็จแล้ว

**สถานะ**: ทำเสร็จแล้ว

`ManageDoctorsDialog` ใน `dashboard/page.tsx` ทำงานครบ:
- แสดง authorized doctors + ปุ่ม Remove
- แสดง pending access requests + ปุ่ม Approve/Reject
- Authorize doctor by ID

### 4.3 Auth Guard - proxy.ts (Next.js 16) ✅ เสร็จแล้ว + แนะนำเพิ่มเติม

**สถานะ**: `frontend/proxy.ts` มีอยู่แล้วและถูกต้อง

> **สำคัญ**: Next.js 16 เปลี่ยนจาก `middleware.ts` เป็น `proxy.ts`
> - `middleware.ts` ถูก **deprecated** แล้ว
> - `proxy.ts` ใช้สำหรับ **lightweight routing เท่านั้น** (rewrites, redirects, headers)
> - **ห้ามใช้ proxy.ts สำหรับ auth logic ที่ซับซ้อน** (เพราะ CVE-2025-29927 ที่ bypass ได้)
> - Auth verification ควรทำใน **Server Layout Guard** หรือ **API route/server action**

**สิ่งที่มีอยู่แล้ว** (`frontend/proxy.ts`):
```typescript
export function proxy(request: NextRequest) {
    const token = request.cookies.get("token")?.value;
    // redirect ไป login ถ้าไม่มี token (lightweight check)
    // redirect ไป dashboard ถ้ามี token แล้วเข้า auth pages
}
```

**แนะนำเพิ่มเติม (Optional - Defense in Depth)**:

สร้าง Server Layout Guard ที่ `frontend/app/(dashboard)/layout.tsx` เพื่อเป็น auth check ชั้นที่ 2 ฝั่ง server ตาม Next.js 16 best practice:

```typescript
// frontend/app/(dashboard)/layout.tsx
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

export default async function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const cookieStore = await cookies();
    const token = cookieStore.get('token')?.value;

    // Server-side auth check (defense in depth)
    // proxy.ts ทำ redirect แล้ว แต่นี่เป็น safety net
    if (!token) {
        redirect('/auth/login');
    }

    return <>{children}</>;
}
```

**ข้อดี**:
- proxy.ts = ด่านแรก (เร็ว, lightweight, ทำ redirect ก่อน render)
- Server Layout Guard = ด่านที่สอง (server-side, ไม่ถูก bypass เหมือน proxy)
- API interceptor (401 → redirect) = ด่านที่สาม (จัดการ token expired)

**สิ่งที่ต้องปรับใน Dashboard Page**:

เมื่อมี proxy.ts + Server Layout Guard แล้ว client-side `useEffect` cookie check ใน `DashboardPage` สามารถลดลงได้ ไม่ต้อง redirect เอง แค่ดึงข้อมูล user จาก cookie:

```typescript
// เดิม: redirect ใน useEffect (ซ้ำซ้อนกับ proxy.ts)
useEffect(() => {
    const userCookie = Cookies.get("user");
    if (!userCookie) {
        router.push("/auth/login");  // ← ไม่จำเป็นแล้ว proxy จัดการแล้ว
        return;
    }
    // ...
}, []);

// ใหม่: ไม่ต้อง redirect เอง เพราะ proxy.ts + layout ทำแล้ว
useEffect(() => {
    const userCookie = Cookies.get("user");
    if (!userCookie) return; // proxy จะ redirect ก่อนหน้านี้แล้ว
    try {
        const userData = JSON.parse(userCookie);
        setUser(userData);
        if (userData.language) setLanguage(userData.language);
    } catch (e) {
        console.error("Invalid user cookie");
    } finally {
        setLoading(false);
    }
}, []);
```

---

### 4.4 API Key เป็น ENV Variable

**ไฟล์**: `frontend/lib/api.ts`

เปลี่ยน hardcoded `'bp-web-app-key'` เป็น:
```typescript
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'bp-web-app-key';
```

### 4.5 Implement Resend OTP

**ไฟล์**: `frontend/app/auth/verify-otp/page.tsx`

แก้ `handleResend` ให้เรียก `/auth/request-otp` จริง พร้อม cooldown timer

### 4.6 Custom Error & 404 Pages

**ไฟล์ใหม่**: `frontend/app/error.tsx`, `frontend/app/not-found.tsx`

สร้าง custom error pages ที่มี branding BP Monitor

### 4.7 `next.config.ts` ✅ มี standalone แล้ว

**สถานะ**: มี `output: 'standalone'` อยู่แล้ว

**เพิ่มเติม (Optional)**: API proxy rewrites ถ้า backend อยู่คนละ domain

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    output: 'standalone',
    
    // Optional: API Proxy (ถ้า backend อยู่คนละ domain)
    async rewrites() {
        const apiUrl = process.env.API_PROXY_URL;
        if (!apiUrl) return [];
        return [
            {
                source: '/api/v1/:path*',
                destination: `${apiUrl}/api/v1/:path*`
            }
        ];
    }
};

export default nextConfig;
```

---

## Phase 5: Deployment Configuration

### 5.1 อัพเดต `docker-compose.yml`

เพิ่ม Redis service, แยก Bot เป็น service ต่างหาก, เพิ่ม Frontend service

### 5.2 สร้าง `frontend/Dockerfile`

สำหรับ standalone Next.js build

### 5.3 อัพเดต `.env.example`

ให้ครบทุก variable ที่เพิ่มใหม่ พร้อม comments อธิบาย

### 5.4 อัพเดต `CLAUDE.md`

เพิ่มส่วน Deployment Modes และ Environment Variable Quick Reference

---

## ลำดับการทำงานสำหรับ Claude Code

```
1. อ่าน CLAUDE.md เพื่อเข้าใจ project structure
2. อ่าน plan/BP_Improvement_Plan.md (ไฟล์นี้) + plan/BP_Assessment.md + plan/BP_Deployment_Plan.md
3. ทำ Phase 1 (Bug Fixes) ทั้งหมดก่อน → ทดสอบ
4. ทำ Phase 2 (Dual-Mode Storage) → ทดสอบ
5. ทำ Phase 3 (Bot Dual-Mode) → ทดสอบ
6. ทำ Phase 4 (Frontend) → เฉพาะข้อที่ยังไม่เสร็จ (4.3 เพิ่มเติม, 4.4, 4.5, 4.6) → ทดสอบ
7. ทำ Phase 5 (Deployment Config) → ทดสอบ
8. อัพเดต CLAUDE.md ให้สะท้อนสถานะใหม่
```

**หลักการ**: ทำทีละ Phase, commit ทีละ Phase, ทดสอบว่า existing functionality ไม่พังก่อนไปต่อ
