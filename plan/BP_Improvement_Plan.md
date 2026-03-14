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

**โครงสร้าง**:

```python
# app/otp_service.py

import os
import time
import base64
import hashlib
import logging
import pyotp

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL")  # ถ้ามี = ใช้ Redis, ถ้าไม่มี = ใช้ Memory


class MemoryOTPBackend:
    """In-memory OTP storage - ใช้สำหรับ dev/local/non-serverless"""
    
    def __init__(self):
        self.storage = {}
        self.verified = set()
        import threading
        threading.Thread(target=self._cleanup, daemon=True).start()
    
    def store(self, key, otp_data):
        self.storage[key] = otp_data
    
    def get(self, key):
        return self.storage.get(key)
    
    def delete(self, key):
        self.storage.pop(key, None)
    
    def mark_verified(self, key):
        self.verified.add(key)
    
    def is_verified(self, key):
        return key in self.verified
    
    def _cleanup(self):
        while True:
            now = time.time()
            expired = [k for k, v in self.storage.items() 
                       if now - v['created_at'] > v['expiration']]
            for k in expired:
                del self.storage[k]
            time.sleep(120)


class RedisOTPBackend:
    """Redis-backed OTP storage - ใช้สำหรับ production/serverless"""
    
    def __init__(self, redis_url):
        import redis
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.prefix = "otp:"
        self.verified_prefix = "otp_verified:"
    
    def store(self, key, otp_data):
        import json
        ttl = int(otp_data.get('expiration', 300))
        self.client.setex(f"{self.prefix}{key}", ttl + 60, json.dumps(otp_data))
    
    def get(self, key):
        import json
        data = self.client.get(f"{self.prefix}{key}")
        return json.loads(data) if data else None
    
    def delete(self, key):
        self.client.delete(f"{self.prefix}{key}")
    
    def mark_verified(self, key):
        self.client.setex(f"{self.verified_prefix}{key}", 600, "1")
    
    def is_verified(self, key):
        return self.client.exists(f"{self.verified_prefix}{key}") > 0


class OTPService:
    """OTP service with auto-selected backend (Memory or Redis)"""
    
    def __init__(self):
        if REDIS_URL:
            try:
                self.backend = RedisOTPBackend(REDIS_URL)
                logger.info("OTP Service: Using Redis backend")
            except Exception as e:
                logger.warning(f"Redis failed ({e}), falling back to memory")
                self.backend = MemoryOTPBackend()
        else:
            self.backend = MemoryOTPBackend()
            logger.info("OTP Service: Using in-memory backend")
    
    def generate_otp(self, contact_target, expiration=300):
        contact_target = contact_target.strip().lower()
        hex_key = hashlib.sha256(contact_target.encode()).hexdigest()
        base32_key = base64.b32encode(bytes.fromhex(hex_key)).decode('utf-8')
        totp = pyotp.TOTP(base32_key, digits=4, interval=expiration)
        otp = totp.now()
        self.backend.store(contact_target, {
            'base32_key': base32_key,
            'interval': expiration,
            'created_at': time.time(),
            'expiration': expiration
        })
        return otp
    
    def confirm_otp(self, contact_target, otp):
        contact_target = contact_target.strip().lower()
        data = self.backend.get(contact_target)
        if not data:
            return False
        if time.time() - data['created_at'] > data['expiration']:
            self.backend.delete(contact_target)
            return False
        totp = pyotp.TOTP(data['base32_key'], digits=4, interval=data['interval'])
        if totp.verify(otp, valid_window=1):
            self.backend.mark_verified(contact_target)
            return True
        return False
    
    def is_verified(self, contact_target):
        return self.backend.is_verified(contact_target.strip().lower())


otp_service = OTPService()
```

**เพิ่มใน requirements.txt**: `redis` (เป็น optional dependency)

---

### 2.2 Rate Limiter - Centralize + Redis support

**ไฟล์ใหม่**: `app/utils/rate_limiter.py`

**แนวคิด**: ถ้ามี REDIS_URL ใช้ Redis storage สำหรับ slowapi

```python
# app/utils/rate_limiter.py
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

REDIS_URL = os.getenv("REDIS_URL")

if REDIS_URL:
    limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL)
else:
    limiter = Limiter(key_func=get_remote_address)
```

**แก้ไฟล์ที่ import limiter**: `app/main.py`, `app/routers/auth.py`, `app/routers/ocr.py`, `app/routers/payment.py`

เปลี่ยนจาก:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
```

เป็น:
```python
from ..utils.rate_limiter import limiter  # (หรือ from app.utils.rate_limiter)
```

และใน `app/main.py`:
```python
from .utils.rate_limiter import limiter
# ...
app.state.limiter = limiter
```

---

### 2.3 Database - เพิ่ม Pool settings สำหรับ PostgreSQL

**ไฟล์**: `app/database.py`

**เพิ่ม connection pool settings**:

```python
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True
    )
```

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

สร้างฟังก์ชัน `build_application()` ที่ return Application instance พร้อม handlers ทั้งหมด แล้วแยก `run_polling()` เป็น function ต่างหาก ดู code ตัวอย่างเต็มใน Assessment Report

### 3.2 สร้าง Webhook Handler

**ไฟล์ใหม่**: `app/bot/webhook.py`

**แนวคิด**: สร้าง FastAPI router ที่มี:
- `POST /bot/webhook` - รับ Telegram updates
- `GET /bot/set-webhook?secret=xxx` - Utility ตั้ง webhook URL (เรียกครั้งเดียวตอน setup)
- `GET /bot/remove-webhook` - ลบ webhook (กลับไปใช้ polling)

### 3.3 แก้ `app/main.py` - เพิ่ม webhook router

**เพิ่มใน `app/main.py`**:

```python
BOT_MODE = os.getenv("BOT_MODE", "polling")
if BOT_MODE == "webhook":
    try:
        from .bot.webhook import router as bot_webhook_router
        app.include_router(bot_webhook_router)
        logger.info("Telegram Bot: Webhook mode enabled at /bot/webhook")
    except Exception as e:
        logger.error(f"Failed to load bot webhook: {e}")
```

### 3.4 Environment Variables

```env
# Local dev:
BOT_MODE=polling

# Vercel/Serverless:
BOT_MODE=webhook
WEBHOOK_URL=https://your-api-domain.com
WEBHOOK_SECRET=your-random-secret

# ไม่ต้องการ Bot:
BOT_MODE=disabled
```

### 3.5 วิธีใช้งาน

**Polling** (local/VPS): รัน `python -m app.bot.main` เป็น process แยก
**Webhook** (Vercel): Deploy backend แล้วเรียก `GET /bot/set-webhook?secret=xxx` ครั้งเดียว จากนั้น Telegram จะส่ง updates มาที่ `POST /bot/webhook` อัตโนมัติ

---

## Phase 4: Frontend Improvements

### 4.1 DoctorView - Fetch Real Data

**ไฟล์**: `frontend/app/(dashboard)/dashboard/page.tsx`

**แก้ DoctorView component ให้**:
- Fetch patients จาก `GET /doctor/patients`
- Fetch access requests จาก `GET /doctor/access-requests`
- แสดง patient list จริงพร้อมปุ่ม View Records
- แสดง pending requests พร้อม status
- เพิ่ม Search Patient + Request Access dialog

### 4.2 Patient: Manage Authorized Doctors

**ไฟล์**: `frontend/app/(dashboard)/dashboard/page.tsx`

**แก้ปุ่ม "Manage Doctors" ให้**:
- แสดง authorized doctors (GET `/patient/authorized-doctors`)
- แสดง pending access requests (GET `/patient/access-requests`)
- ปุ่ม Approve/Reject pending requests
- ปุ่ม Remove authorized doctor
- ปุ่ม Authorize Doctor (search → authorize)

### 4.3 Next.js Middleware สำหรับ Auth Guard

**ไฟล์ใหม่**: `frontend/middleware.ts`

สร้าง middleware ที่:
- Redirect ไป `/auth/login` ถ้าเข้า protected routes (`/dashboard`, `/settings`, `/subscription`) โดยไม่มี token cookie
- Redirect ไป `/dashboard` ถ้าเข้า auth routes (`/auth/*`) แต่มี token แล้ว

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

### 4.7 `next.config.ts` - เพิ่ม config

**ไฟล์**: `frontend/next.config.ts`

เพิ่ม `output: 'standalone'` สำหรับ Docker และ optional API proxy rewrites

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
2. อ่าน plan/BP_Improvement_Plan.md (ไฟล์นี้) + plan/BP_Assessment.md
3. ทำ Phase 1 (Bug Fixes) ทั้งหมดก่อน → ทดสอบ
4. ทำ Phase 2 (Dual-Mode Storage) → ทดสอบ
5. ทำ Phase 3 (Bot Dual-Mode) → ทดสอบ
6. ทำ Phase 4 (Frontend) → ทดสอบ
7. ทำ Phase 5 (Deployment Config) → ทดสอบ
8. อัพเดต CLAUDE.md ให้สะท้อนสถานะใหม่
```

**หลักการ**: ทำทีละ Phase, commit ทีละ Phase, ทดสอบว่า existing functionality ไม่พังก่อนไปต่อ
