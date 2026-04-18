# ASM PWA Specification — Progressive Web App for อาสาสมัครสาธารณสุข

> **Status:** Draft v1.1 — aligned with [[PLAN_REVIEW_RESPONSE]] decisions (2026-04-18)
> **Last updated:** 2026-04-18
> **Owner:** Pornthep
> **Depends on:** `MVP_PILOT_SCOPE.md`, `ORG_FOUNDATION.md`, `CONSENT_FLOW_SPEC.md`, `PLAN_REVIEW_RESPONSE.md`
> **Related:** `ADMIN_WEB_SPEC.md`

> [!INFO] **v1.1 alignment status**
> - Image handling (§5.2, §6.5) — ✅ already matches v1.1 policy (no single-OCR storage, temp batch storage 7 days)
> - Consent flow (§7) — ✅ already excludes paper scan upload (§7.3)
> - JWT payload (§3.3) — ✅ includes `organization_id` (= `active_org_id` for ASM = default single org)
> - **Multi-org สำหรับ อสม.:** MVP = 1 อสม. : 1 รพ.สต. (no org selector). Phase 2 ถ้า อสม. เป็น member หลาย รพ.สต. = reuse `/admin/select-org` pattern จาก ADMIN_WEB_SPEC §3.1.5

---

## 1. Purpose

Progressive Web App (PWA) สำหรับ **อาสาสมัครสาธารณสุขประจำหมู่บ้าน (อสม.)** ใช้บนสมาร์ทโฟนภาคสนาม

**Primary use cases:**
- บันทึกผลวัดความดันให้ชาวบ้านในความรับผิดชอบ (หลายคนต่อวัน)
- ใช้ OCR ช่วยลดการพิมพ์ (รูปเครื่องวัด + ใบรายชื่อ)
- เก็บ consent ผ่าน digital signature + GPS
- ดู history ของชาวบ้าน
- รับ notification จาก bot

**Constraints:**
- อสม. ไม่เคยใช้ Telegram มาก่อน → onboarding ต้องเรียบง่าย
- Device = Android สมาร์ทโฟนส่วนตัว (BYOD)
- สัญญาณมือถือพอใช้ได้ในพื้นที่
- อสม. อาจมีอายุ 40-60+ ปี → UX ต้องเป็นมิตร (ปุ่มใหญ่, ข้อความชัด)

---

## 2. PWA Architecture

### 2.1 Tech Stack
- **Framework**: Next.js 16 (same codebase, separate route group)
- **UI**: Tailwind + shadcn/ui
- **State**: TanStack Query (server) + Zustand (local UI)
- **PWA**: `next-pwa` package or custom Service Worker
- **Forms**: react-hook-form + Zod
- **Signature**: `signature_pad` library
- **Camera**: native `<input type="file" accept="image/*" capture="environment">`

### 2.2 Route structure

```
frontend/app/asm/
├── layout.tsx                    # PWA shell, bottom nav
├── login/page.tsx                # Phone + OTP login
├── onboarding/page.tsx           # Telegram pairing guide
├── page.tsx                      # Home/dashboard
├── patients/
│   ├── page.tsx                  # Patient list (mine)
│   └── [id]/
│       ├── page.tsx              # Patient detail
│       ├── reading/new/page.tsx  # Quick entry
│       └── consent/page.tsx      # Capture consent
├── record/
│   ├── single/page.tsx           # Single-photo OCR
│   └── batch/page.tsx            # Batch OCR (ใบรายชื่อ + เครื่องวัด)
├── history/page.tsx              # My recent readings
├── profile/page.tsx              # อสม. profile
└── manifest.json                 # PWA manifest
```

### 2.3 PWA manifest (`/asm/manifest.json`)

```json
{
  "name": "BP Monitor — อสม.",
  "short_name": "BP อสม.",
  "description": "บันทึกความดันโลหิตสำหรับอาสาสมัครสาธารณสุข",
  "start_url": "/asm",
  "display": "standalone",
  "orientation": "portrait",
  "theme_color": "#2563eb",
  "background_color": "#ffffff",
  "lang": "th",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/maskable-icon.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

### 2.4 Service Worker (MVP — minimal)

**MVP scope:**
- Cache static assets (JS, CSS, images, manifest)
- Cache app shell (layout, login page)
- Network-first for API calls (no offline queue in MVP)

**NOT in MVP:**
- Offline data queue (readings queued ขณะ offline, sync เมื่อกลับมา online)
- Background sync
- Push notifications (ใช้ Telegram bot แทน)

**Phase 2+**: add IndexedDB queue + Background Sync API เมื่อจำเป็น

### 2.5 Responsive design

- Target: **Android smartphones** portrait mode (360×640 to 412×915)
- Touch targets: **minimum 48×48px** (WCAG + elderly-friendly)
- Font size: **base 16px**, important labels 18px+
- High contrast (WCAG AA)
- No hover-dependent UI (touch only)

---

## 3. Authentication Flow

### 3.1 One-time Onboarding (Pairing)

**Prerequisite**: Admin สร้างบัญชี อสม. ใน admin web + generate pairing code 6 หลัก (TTL 15 นาที) + แจ้งรหัสให้ อสม.

**Flow**:

```
Step 1 — Install Telegram (ถ้ายังไม่มี)
  อสม. → Play Store → search "Telegram" → install
  → เปิดแอป → เบอร์โทร (เบอร์เดียวกับที่ admin ลงทะเบียน) → OTP → ตั้งชื่อ

Step 2 — Find bot
  อสม. → ค้นหา "@BPMonitorASMBot" (หรือชื่อที่กำหนด)
  OR สแกน QR code ที่ admin ให้ (QR เปิด URL t.me/BPMonitorASMBot)
  → กดปุ่ม "Start" ล่างสุด

Step 3 — Pair
  อสม. พิมพ์: /start 123456   (แทน 123456 ด้วย pairing code)
  Bot ตอบ:
    "ยืนยันตัวตนสำเร็จ ✓
     ชื่อของคุณในระบบ: [name]
     รพ.สต.: [รพ.สต. เมืองเก่า]
     ต่อไปนี้ รหัสผ่านชั่วคราว (OTP) จะส่งมาที่ chat นี้
     
     เริ่มใช้งาน: [ลิงก์เปิด PWA]"

Step 4 — Open PWA + Login (section 3.2)
```

**Pairing Code validation (backend)**:
```python
async def handle_start_command(update, context):
    code = context.args[0] if context.args else None
    if not code or not code.isdigit() or len(code) != 6:
        await update.message.reply_text("รูปแบบ pairing code ไม่ถูกต้อง")
        return
    
    code_hash = sha256(code).hexdigest()
    pairing = await db.query(PairingCode).filter(
        PairingCode.code_hash == code_hash,
        PairingCode.used_at.is_(None),
        PairingCode.expires_at > datetime.utcnow()
    ).first()
    
    if not pairing:
        await update.message.reply_text("Pairing code หมดอายุหรือถูกใช้ไปแล้ว")
        return
    
    user = pairing.user
    telegram_id = update.effective_user.id
    
    # Link telegram_id to user
    user.telegram_id_hash = sha256(str(telegram_id)).hexdigest()
    user.telegram_id_encrypted = fernet.encrypt(str(telegram_id).encode())
    
    # Mark pairing as used
    pairing.used_at = datetime.utcnow()
    pairing.used_by_telegram_id_hash = user.telegram_id_hash
    
    await db.commit()
    await update.message.reply_text(f"""
ยืนยันตัวตนสำเร็จ

ชื่อของคุณ: {user.full_name}
บทบาท: อาสาสมัครสาธารณสุข
รพ.สต.: {user.organization.name}

ต่อไปนี้ รหัสผ่านชั่วคราว (OTP) จะส่งมาที่นี่
เปิด PWA เพื่อเริ่มใช้งาน:
https://bp-frontend.example.com/asm
    """)
```

### 3.2 Login Flow (ทุกครั้งที่ใช้)

```
Step 1 — Open PWA
  อสม. เปิด PWA (home screen icon หรือ browser)
  → /asm → redirect to /asm/login (ถ้ายังไม่ login)

Step 2 — Request OTP
  หน้า login: input เบอร์โทร
  กด "ขอรหัส OTP"

Step 3 — Backend generates + sends
  POST /api/v1/asm/auth/request-otp {phone}
  Backend:
    - Validate phone format
    - Look up user by phone_hash
    - Check user has telegram_id_hash (paired)
    - Rate limit check (3 requests / 15 min per account)
    - Generate 6-digit OTP (random)
    - Store hash in Redis: otp:{user_id} = {hash, attempts: 0}, TTL 5 min
    - Send to Telegram via bot:
        bot.send_message(telegram_id, f"รหัส OTP: {otp_code} (หมดอายุใน 5 นาที)")
    - Return success (don't leak whether user exists)

Step 4 — Enter OTP
  PWA shows OTP input (6 digits, numeric keyboard)
  อสม. เปิด Telegram → เห็นรหัสจาก bot → กลับมา PWA → ใส่รหัส
  POST /api/v1/asm/auth/verify-otp {phone, otp}
  Backend:
    - Validate OTP (check hash, check attempts < 3)
    - If OK: issue JWT (TTL 24h) + refresh token (TTL 30d, HTTP-only cookie)
    - If fail: increment attempts; if > 3 invalidate OTP, log security event
    - Return {access_token, user: {...}, assignment_summary: {...}}

Step 5 — Enter PWA home
  PWA store JWT in memory (NOT localStorage — XSS defense)
  refresh token in HTTP-only cookie
  Fetch home dashboard
```

**Fallback — OTP ไม่ถึง (bot blocked/deleted):**

```
User: พิมพ์ /otp ใน Telegram bot
Bot: verify ว่า Telegram chat ผูกกับ user ที่มี active session request
     ส่ง OTP ปัจจุบัน (ถ้ามี valid ใน Redis)
     หรือ แนะนำให้ขอใหม่ใน PWA
```

### 3.3 Session Management

**Access token (JWT):**
- TTL: 24 hours
- Payload: `{user_id, external_id, role, organization_id, iat, exp}`
- Signed HS256 with server secret
- Sent via `Authorization: Bearer {token}` header

**Refresh token:**
- TTL: 30 days
- HTTP-only + Secure + SameSite=Strict cookie
- Used to renew access token without re-OTP
- Stored server-side (hashed) for revocation

**Auto-refresh:**
- When access token expires in < 5 min, client calls `POST /asm/auth/refresh`
- If refresh token valid → new access token
- If expired → redirect to login

**Logout:**
- `POST /asm/auth/logout`
- Invalidate refresh token
- Clear client storage
- Redirect to login

### 3.4 Security considerations

- **No password** (OTP-only) — reduces phishing / credential theft risk
- **Rate limiting**: OTP request 3/15min, verify 5 attempts per OTP
- **Telegram ID encryption**: only hash used for lookup, encrypted for ops
- **JWT in memory only**: no localStorage (XSS mitigation)
- **CSRF**: SameSite cookies + CSRF token for state-changing ops
- **Device binding (future)**: bind JWT to device fingerprint for extra security

---

## 4. Core Screens

### 4.1 `/asm/login` — Login

**Layout**:
```
┌─────────────────────────┐
│   [Logo]                │
│                         │
│   เข้าสู่ระบบ              │
│                         │
│   เบอร์โทรศัพท์             │
│   [08X-XXX-XXXX     ]   │
│                         │
│   [ขอรหัส OTP]            │
│                         │
│   ยังไม่ได้ผูก Telegram?   │
│   ติดต่อแอดมิน              │
└─────────────────────────┘
```

After OTP requested:
```
┌─────────────────────────┐
│   กรุณากรอกรหัส OTP      │
│                         │
│   รหัสถูกส่งไปที่ Telegram │
│                         │
│   [_][_][_][_][_][_]    │
│                         │
│   [ยืนยัน]                │
│                         │
│   ไม่ได้รับรหัส?           │
│   - ตรวจสอบ Telegram     │
│   - พิมพ์ /otp ใน bot     │
│   - [ขอรหัสใหม่]          │
│     (หลัง 60 วินาที)       │
└─────────────────────────┘
```

### 4.2 `/asm/onboarding` — First-time Guide

**Trigger**: `terms_accepted_at` is null OR first successful login

**Steps (3 screens, swipeable):**

Screen 1: Welcome
- "สวัสดี [ชื่อ อสม.]"
- "คุณเป็นสมาชิกของ รพ.สต.เมืองเก่า"
- "แอปนี้ช่วยคุณบันทึกความดันให้ชาวบ้านในความรับผิดชอบ"
- [ถัดไป]

Screen 2: Accept Terms
- Privacy Policy + ToS (scrollable, condensed)
- Checkbox: "ข้าพเจ้าได้อ่านและยอมรับ ข้อตกลง + นโยบายความเป็นส่วนตัว"
- [ยอมรับและดำเนินการต่อ]

Screen 3: Quick Tour (3 tiles)
- "คนในความดูแล" → patient list
- "บันทึกความดัน" → record flow
- "ดูประวัติการบันทึก" → history
- [เริ่มใช้งาน] → home

### 4.3 `/asm` — Home Dashboard

**Layout:**
```
┌─────────────────────────┐
│ [≡] BP อสม.    [🔔][👤] │ ← top bar
├─────────────────────────┤
│                         │
│  สวัสดี, [ชื่อ อสม.]      │
│  รพ.สต. เมืองเก่า         │
│                         │
│ ┌───────────────────┐  │
│ │ คนในความดูแล       │  │
│ │    10 คน          │  │
│ └───────────────────┘  │
│                         │
│ ┌─────────┬─────────┐  │
│ │ บันทึก    │ OCR     │  │
│ │ เดือนนี้   │ รายชื่อ   │  │
│ │  35       │  (batch)│  │
│ └─────────┴─────────┘  │
│                         │
│  วันนี้ต้องไปวัด           │
│  ┌─────────────────┐   │
│  │ 1. สมชาย      >  │   │
│  │ 2. สมหญิง     >  │   │
│  │ 3. สมศรี      >  │   │
│  └─────────────────┘   │
│                         │
│  [+ บันทึกผลวัดใหม่]      │ ← big primary CTA
│                         │
├─────────────────────────┤
│ [🏠][👥][📷][📋][👤]     │ ← bottom nav
└─────────────────────────┘
```

**Bottom nav**: Home / Patients / Record / History / Profile

**KPIs:**
- จำนวนคนในความดูแล (active assignments)
- Readings this month (count)
- "วันนี้ต้องไปวัด" — patients ที่ last reading > N วัน (N configurable)

**CTAs:**
- Primary: "+ บันทึกผลวัดใหม่" → `/asm/record` (chooser: single / batch)
- Secondary: patient tap → `/asm/patients/{id}`

**API**:
- `GET /api/v1/asm/dashboard`
  - Returns: `{patient_count, readings_month, due_patients: [...], recent_activity}`

### 4.4 `/asm/patients` — Patient List

**Layout:**
```
┌─────────────────────────┐
│ [←] คนในความดูแล   [🔍] │
├─────────────────────────┤
│ [เรียง: ลำดับ▼] [กรอง]  │
├─────────────────────────┤
│ 1  สมชาย ใจดี          │
│    อายุ 62 • ชาย         │
│    ครั้งล่าสุด: 3 วันก่อน │
│    ค่า: 135/88 (72)     │
├─────────────────────────┤
│ 2  สมหญิง ใจดี          │
│    อายุ 58 • หญิง        │
│    ยังไม่มีการบันทึก      │
├─────────────────────────┤
│ ...                     │
└─────────────────────────┘
```

**Features**:
- Search (ชื่อ)
- Sort: by sequence, by last reading, by name
- Filter: overdue (> N days), age range, gender, high BP flag
- Tap row → patient detail

**API**:
- `GET /api/v1/asm/patients?search=&sort=&filter=`
- Returns: `[{id, external_id, sequence, name, age, gender, last_reading, flags}]`

**Privacy**: ชื่อ display ตรง ๆ (อสม. มีสิทธิ์เห็น). เบอร์โทรและเลขบัตร mask by default

### 4.5 `/asm/patients/[id]` — Patient Detail

**Layout:**
```
┌─────────────────────────┐
│ [←] สมชาย ใจดี            │
├─────────────────────────┤
│  อายุ 62 • ชาย            │
│  ลำดับที่ 1              │
│  โทร: 08x-xxx-x789 [👁]  │ ← tap to unmask (audit)
│  โรคประจำตัว: ความดันสูง  │
│                         │
│  📊 กราฟความดัน (30 วัน) │
│  [chart]                │
│                         │
│  📝 บันทึกล่าสุด          │
│  17/4/2026 08:30         │
│    135/88 (72) ✓         │
│  10/4/2026 08:15         │
│    140/92 (75)           │
│  [ดูทั้งหมด]              │
│                         │
│  📄 สถานะ Consent         │
│  ✓ อสม. เก็บข้อมูล        │
│  ✓ รพ.สต. ดูข้อมูล        │
│                         │
│ ┌─────────────────────┐ │
│ │ + บันทึกผลวัดใหม่     │ │
│ └─────────────────────┘ │
└─────────────────────────┘
```

**Actions**:
- "+ บันทึกผลวัดใหม่" → chooser: พิมพ์เอง / ถ่ายรูป → `/asm/patients/{id}/reading/new`
- Unmask phone/citizen: confirm modal + audit log
- If no active consent: block record button + message "ต้องเก็บ consent ก่อน" → link to `/asm/patients/{id}/consent`

**API**:
- `GET /api/v1/asm/patients/{id}` — detail + consent + readings summary
- `GET /api/v1/asm/patients/{id}/readings?days=30` — history for chart

### 4.6 `/asm/patients/[id]/reading/new` — Quick Entry

**Flow**:

Screen 1 — Method chooser:
```
บันทึกผลวัดของ สมชาย ใจดี

ท่านต้องการบันทึกด้วยวิธีใด?

[📝 พิมพ์เอง]

[📷 ถ่ายรูปจอเครื่องวัด]
```

Screen 2A — Manual entry:
```
┌─────────────────────────┐
│  ความดันตัวบน (Systolic)  │
│  [      130          ] │
│                         │
│  ความดันตัวล่าง          │
│  [      85           ] │
│                         │
│  ชีพจร (Pulse)            │
│  [      72           ] │
│                         │
│  วัดเมื่อ                  │
│  [17/4/2026 08:30 ▼]   │ ← default now, editable
│                         │
│  สถานที่วัด               │
│  [○ บ้านชาวบ้าน]         │
│  [○ รพ.สต.]              │
│  [○ อื่นๆ]                │
│                         │
│  หมายเหตุ (ถ้ามี)         │
│  [                  ]   │
│                         │
│  [บันทึก]                 │
└─────────────────────────┘
```

Screen 2B — Photo OCR (single):
- See section 5

**Post-submit**:
- Success toast + redirect to patient detail
- If duplicate detected: confirm modal "พบข้อมูลคล้ายกันเมื่อ X นาทีที่แล้ว บันทึกซ้ำ?"

**API**:
- `POST /api/v1/asm/readings` — manual entry
- `POST /api/v1/asm/readings/ocr/single` — with image upload

**Validation**:
- systolic: 60-260
- diastolic: 40-180
- pulse: 30-200
- measured_at: not future, not > 7 days ago (warn if > 24h)

---

## 5. Single-Photo OCR Flow

### 5.1 User flow

```
อสม. patient detail → "+ บันทึก" → "ถ่ายรูป"

→ PWA opens camera (capture=environment)
→ อสม. ถ่ายรูปจอเครื่องวัด
→ Preview: [เก็บรูปนี้] [ถ่ายใหม่]
→ Upload (show progress bar)
→ Backend OCR with Gemini
→ Pre-fill form:
   [systolic: 130   confidence: 0.98]
   [diastolic: 85  confidence: 0.98]
   [pulse: 72      confidence: 0.95]
   [time: 08:30    confidence: 0.92]
→ อสม. review → ถูก → กด "บันทึก"
→ Success
```

### 5.2 Image handling (privacy-first)

**ไม่เก็บรูปใน server ใน flow นี้** (ตาม data minimization):

```
1. Client: capture image (in memory)
2. Client: compress if > 3MB (client-side resize)
3. Client: POST to /api/v1/asm/readings/ocr/single (multipart)
4. Server: receive image (in memory)
5. Server: call Gemini API (pass image base64)
6. Server: parse Gemini JSON response
7. Server: return { pre_fill_values, confidence, warnings } to client
8. Server: discard image (never stored)
9. Client: show pre-fill form
10. อสม. confirm → POST to /api/v1/asm/readings (manual-style with pre_fill metadata)
11. Server: create bp_reading with source_type="ocr_single", ocr_raw_output (JSON)
```

**Server memory handling:**
- Use streaming multipart to avoid large buffer
- Explicit `del image_bytes` after Gemini call
- Memory metrics monitoring (detect leaks)

### 5.3 Gemini prompt (single)

```python
SINGLE_OCR_PROMPT = """
คุณเป็นระบบอ่านค่าจากจอเครื่องวัดความดันโลหิต
วิเคราะห์รูปภาพและดึงข้อมูลต่อไปนี้:

- systolic: ตัวเลขบน (ความดันซิสโตลิก, ปกติ 60-260)
- diastolic: ตัวเลขล่าง (ความดันไดแอสโตลิก, ปกติ 40-180)
- pulse: ตัวเลขชีพจร (ปกติ 30-200)
- measurement_time: เวลาที่แสดงบนจอ (HH:MM) ถ้ามี, null ถ้าไม่มี
- measurement_date: วันที่บนจอ (YYYY-MM-DD) ถ้ามี, null ถ้าไม่มี

ตอบเป็น JSON เท่านั้น (ไม่มี markdown, ไม่มีคำอธิบาย):
{
  "systolic": <number>,
  "diastolic": <number>,
  "pulse": <number | null>,
  "measurement_time": "<HH:MM>" | null,
  "measurement_date": "<YYYY-MM-DD>" | null,
  "confidence": {
    "systolic": <0.0-1.0>,
    "diastolic": <0.0-1.0>,
    "pulse": <0.0-1.0>,
    "time_date": <0.0-1.0>,
    "overall": <0.0-1.0>
  },
  "warnings": ["array of warnings"]
}

หากอ่านค่าไม่ได้: set to null + warning
หากค่าไม่สมเหตุสมผล (นอกช่วงปกติ): confidence < 0.5 + warning
"""
```

### 5.4 Confidence handling

- `overall >= 0.85`: pre-fill + let อสม. confirm (standard)
- `0.7 <= overall < 0.85`: pre-fill + highlight warnings + อสม. review carefully
- `overall < 0.7`: show warning + option to retake photo or enter manually (don't pre-fill)

---

## 6. Batch OCR Flow (ใบรายชื่อ + เครื่องวัด) — ⭐ KEY FEATURE

### 6.1 Concept

อสม. วางใบรายชื่อคนในความดูแล (พิมพ์จาก admin web) **ข้าง ๆ เครื่องวัด** → ติ๊กช่องข้างชื่อคนที่เพิ่งวัด → ถ่ายรูปทีเดียว → Gemini อ่านทั้ง ลำดับที่ติ๊ก + ค่า BP → pre-fill + review → save

**Goal**: ลด friction ของการวัด 10 คนต่อวัน จากการพิมพ์ทุกครั้ง → ถ่ายครั้งเดียวจบ

### 6.2 ใบรายชื่อ Format

**A4 portrait, print on-demand จาก admin web per อสม.**

```
╔═══════════════════════════════════════════════════╗
║       ใบบันทึกการวัดความดันโลหิต                    ║
║       อสม. ชื่อ: ________  วันที่: ________        ║
║       รพ.สต. เมืองเก่า                             ║
╠═══════════════════════════════════════════════════╣
║  ลำดับ │     ชื่อ-นามสกุล     │ ติ๊ก  │ หมายเหตุ    ║
╠════════╪══════════════════════╪═══════╪════════════╣
║   1    │  สมชาย ใจดี          │  ☐   │             ║
║   2    │  สมหญิง ใจดี         │  ☐   │             ║
║   3    │  สมศรี มีสุข          │  ☐   │             ║
║   4    │  สมควร ดีงาม         │  ☐   │             ║
║   5    │  สมใจ ใฝ่ดี          │  ☐   │             ║
║  ...   │  ...                 │  ☐   │             ║
║  10    │  ...                 │  ☐   │             ║
╠════════╪══════════════════════╪═══════╪════════════╣
║  วิธีใช้: วัดเสร็จ → ติ๊ก ☑ ข้างชื่อ →               ║
║  ถ่ายรูปใบรายชื่อพร้อมจอเครื่องวัด                 ║
╚═══════════════════════════════════════════════════╝
```

**Design notes:**
- ลำดับ (Column 1) = **primary identifier** สำหรับ OCR → match กับ `care_assignments.sequence_in_list`
- ชื่อ-นามสกุล (Column 2) = **secondary verification** → fuzzy match ช่วย validate
- ติ๊ก (Column 3) = ช่องให้กากบาท (☒ หรือ ✓) — ใหญ่พอ (≥ 10mm × 10mm)
- หมายเหตุ (Column 4) = optional, ไม่ OCR (for อสม. manual notes)
- พิมพ์ทุกสัปดาห์ (ใหม่) หรือเมื่อ care_assignment เปลี่ยน
- Font ภาษาไทย ขนาดใหญ่ (14-16pt)
- Lamination แนะนำ (กันน้ำ/ฝน)

**Privacy consideration in ใบรายชื่อ:**
- ชื่อเต็มอยู่ในใบ → อสม. ต้องเก็บใบดี (อย่าให้คนอื่นเห็น)
- ไม่มี: เบอร์โทร, เลขบัตรประชาชน, ที่อยู่, โรคประจำตัว (privacy by design)
- เมื่อใบหมดอายุ: tear + shred

**Generate logic (admin web):**
```python
# Admin: /admin/asm/{id}/print-patient-list
# Returns PDF with care assignments ของ อสม. คนนี้, sorted by sequence_in_list
```

### 6.3 Capture flow

```
อสม. home → [OCR รายชื่อ (batch)] หรือ bottom nav "📷"

→ Screen: "ตำแหน่งในการถ่ายรูป"
   - วางใบรายชื่อแนวตั้ง
   - วางเครื่องวัดติดกัน (ด้านขวาของใบ)
   - ติ๊กช่องข้างชื่อคนที่เพิ่งวัด
   - ถ่ายรูปให้เห็นทั้งใบ + จอเครื่องวัด
   - [ตัวอย่างรูป]

→ [📷 ถ่ายรูป]
→ Native camera opens → อสม. ถ่าย
→ Preview
→ [เก็บรูปนี้] / [ถ่ายใหม่]

→ Upload + process (progress bar)
→ Screen: "ยืนยันข้อมูล"
```

### 6.4 Gemini prompt (batch) — Critical engineering

```python
BATCH_OCR_PROMPT = """
คุณเป็นระบบวิเคราะห์ภาพสำหรับอาสาสมัครสาธารณสุขในประเทศไทย
ภาพนี้ประกอบด้วย:
1. ใบรายชื่อคนไข้ (Thai patient list, A4, แนวตั้ง) 
   มีคอลัมน์: ลำดับ | ชื่อ-นามสกุล | ติ๊ก | หมายเหตุ
2. เครื่องวัดความดันโลหิต แสดงค่า systolic / diastolic / pulse

งานของคุณ:
1. หาว่าแถวไหนในใบรายชื่อที่ถูก "ติ๊ก" (กากบาท ✓ หรือ ✗ หรือ ☑)
2. อ่านเลขลำดับและชื่อของแถวนั้น
3. อ่านค่าจากเครื่องวัด
4. ถ้าจอเครื่องวัดแสดงเวลา/วันที่ ให้อ่านด้วย

ตอบเป็น JSON เท่านั้น:
{
  "matched_rows": [
    {
      "row_sequence": <number>,
      "row_name": "<string>",
      "tick_confidence": <0.0-1.0>
    }
  ],
  "bp_reading": {
    "systolic": <number>,
    "diastolic": <number>,
    "pulse": <number | null>,
    "measurement_time": "<HH:MM>" | null,
    "measurement_date": "<YYYY-MM-DD>" | null
  },
  "confidence": {
    "patient_identification": <0.0-1.0>,
    "bp_values": <0.0-1.0>,
    "overall": <0.0-1.0>
  },
  "warnings": ["array of issues"],
  "image_quality": "excellent" | "good" | "fair" | "poor"
}

ข้อสังเกต:
- ถ้ามีหลายแถวถูกติ๊ก: return ทั้งหมดใน matched_rows + warning "multiple_checkmarks"
- ถ้าไม่มีแถวไหนถูกติ๊ก: matched_rows = [] + warning "no_checkmark_found"
- ถ้าค่า BP อ่านไม่ได้: set null + warning
- ถ้าภาพเบลอ/มืด: warning + image_quality = "poor"
- ชื่อภาษาไทย: อ่านเป็นภาษาไทยตามที่ปรากฏ (ไม่ต้องแปล)
"""
```

**Model selection**: `gemini-2.5-flash` or newer (เก่งด้าน multimodal ภาษาไทย)

**Cost estimate**: 1 batch image ~10-20 tokens/ภาพ = ~$0.001-0.005 ต่อครั้ง × 10 คน/วัน × 2 อสม. × 30 วัน = ~$0.60-3/เดือน/pilot (ถูกมาก)

### 6.5 Server-side processing

```python
async def process_batch_ocr(image_bytes: bytes, current_asm: User):
    # 1. Call Gemini
    raw_output = await gemini.generate_content(
        prompt=BATCH_OCR_PROMPT,
        image=image_bytes,
        response_format="json"
    )
    
    # 2. Validate JSON structure
    parsed = validate_batch_ocr_response(raw_output)
    
    # 3. Match patients
    matched = []
    for row in parsed["matched_rows"]:
        # Primary: match by sequence in care_assignments
        assignment = await db.query(CareAssignment).filter(
            CareAssignment.caregiver_user_id == current_asm.id,
            CareAssignment.sequence_in_list == row["row_sequence"],
            CareAssignment.is_active == True
        ).first()
        
        if not assignment:
            matched.append({
                "row": row,
                "patient_id": None,
                "match_status": "unknown_sequence",
                "suggestion": None
            })
            continue
        
        patient = assignment.patient
        
        # Secondary: fuzzy match name (cross-validate)
        name_similarity = rapidfuzz.fuzz.ratio(
            row["row_name"],
            decrypt(patient.full_name_encrypted)
        ) / 100.0
        
        match_status = "matched" if name_similarity > 0.8 else "name_mismatch"
        
        matched.append({
            "row": row,
            "patient_id": patient.id,
            "patient_external_id": patient.external_id,
            "patient_name": decrypt(patient.full_name_encrypted),
            "name_similarity": name_similarity,
            "match_status": match_status
        })
    
    # 4. Check BP values sanity
    bp = parsed["bp_reading"]
    bp_warnings = []
    if bp["systolic"] and not (60 <= bp["systolic"] <= 260):
        bp_warnings.append("systolic_out_of_range")
    if bp["diastolic"] and not (40 <= bp["diastolic"] <= 180):
        bp_warnings.append("diastolic_out_of_range")
    
    # 5. Determine flow
    overall_conf = parsed["confidence"]["overall"]
    multiple_tick = len(matched) > 1
    no_tick = len(matched) == 0
    
    if overall_conf >= 0.85 and not multiple_tick and not no_tick and matched[0]["match_status"] == "matched":
        # Happy path: auto-confirm in UI, high confidence
        flow = "auto_confirm"
        image_stored = False  # DISCARD image
    else:
        # Review needed
        flow = "review_needed"
        # Store image temporarily for review queue (optional — only if admin review enabled)
        if overall_conf < 0.7 or multiple_tick or no_tick:
            # store image with expires_at = now + 7 days
            image_stored = True
            file_id = await store_image_temp(
                image_bytes,
                purpose="ocr_batch_review_temp",
                expires_at=now + timedelta(days=7),
                uploaded_by=current_asm.id
            )
        else:
            image_stored = False  # อสม. review in PWA, no server storage
    
    return {
        "flow": flow,
        "matched_patients": matched,
        "bp_reading": bp,
        "warnings": parsed["warnings"] + bp_warnings,
        "overall_confidence": overall_conf,
        "image_quality": parsed["image_quality"],
        "temp_image_id": file_id if image_stored else None,
        "raw_output": parsed  # เก็บ JSON ใน bp_readings.ocr_raw_output
    }
    
    # Note: image_bytes is NOT stored if flow = auto_confirm or low-stakes review
    # Only stored for review_needed AND low confidence / multi-patient issues
```

### 6.6 Review UI (PWA side)

**Happy path (auto-confirm, high confidence):**
```
┌─────────────────────────┐
│   ตรวจสอบข้อมูล           │
├─────────────────────────┤
│                         │
│ 👤 คนไข้:                 │
│   ลำดับ 1 - สมชาย ใจดี  │
│   ✓ ยืนยันแล้ว (98%)     │
│                         │
│ 💉 ค่าที่วัด:             │
│   Systolic:  130        │
│   Diastolic:  85        │
│   Pulse:     72         │
│   เวลา: 08:30           │
│                         │
│ [ถ่ายใหม่]  [บันทึก →]   │
└─────────────────────────┘
```

**Edge case: name mismatch (ลำดับ 1 แต่ชื่อดูเพี้ยน):**
```
⚠️ ชื่ออาจไม่ตรงกับระบบ

ในใบรายชื่อ: "สมชาย ใจดี"
ในระบบลำดับ 1: "สมชาย ใจดี"
Similarity: 65%

อาจเกิดจาก: ลายมือพร่ามัว หรือ ใบรายชื่อไม่อัปเดต

[ยืนยันว่าเป็นคนนี้]  [เลือกคนอื่น]  [ถ่ายใหม่]
```

**Edge case: no checkmark / multiple checkmarks:**
```
❌ ไม่พบเครื่องหมายติ๊ก (หรือพบหลายอัน)

กรุณา:
1. ติ๊กช่องข้างชื่อคนที่วัด
2. ถ่ายรูปใหม่

หรือ [เลือกคนไข้ด้วยตัวเอง]
```

**Edge case: low BP confidence:**
```
⚠️ ค่าอ่านไม่ชัด

Systolic: 130 (65% confident)
Diastolic: 85 (95% confident)
Pulse: -- (ไม่สามารถอ่านได้)

[แก้ไขเอง]  [ถ่ายใหม่]
```

### 6.7 Save flow

```
อสม. กด "บันทึก"
→ POST /api/v1/asm/readings/ocr/batch/confirm
   Body: { temp_reading_id, confirmed_patient_id, values, edits: {...} }
→ Backend:
   - Verify อสม. owns care_assignment to confirmed_patient_id
   - Check active consent (asm_collect)
   - Create bp_reading
     - source_type = "ocr_batch"
     - ocr_raw_output = {original JSON}
     - ocr_confidence_score = overall
     - source_image_file_id = temp_image_id (if stored)
     - measurement_context = "asm_field_visit"
   - If image was stored: schedule immediate deletion (after commit)
     - For "auto_confirm" flow: delete immediately (image was never really needed)
     - For "review_needed" that was resolved by อสม.: delete immediately
     - Only persist image if enters admin review queue (ocr_review_status = "pending")
   - Audit event: bp_reading_create (metadata: source=ocr_batch)
→ Response: {reading_id, success: true}
→ PWA: success toast → back to home
```

### 6.8 Multi-patient batch (future Phase 2)

ใน MVP: **1 photo = 1 patient** (ติ๊ก 1 ช่อง = วัด 1 คนพึ่งเสร็จ)

Phase 2: multiple checkmarks in one photo (batch multiple patients in one shot) — แต่ logic ซับซ้อน (ทุกคนต้องมีค่า BP แสดงพร้อมกันในจอ = ไม่สมเหตุสมผลในโลกจริง)

**Better approach Phase 2**: take photos in sequence, app batches them (client-side batching)

---

## 7. Consent Capture (Reference: CONSENT_FLOW_SPEC.md)

### 7.1 Entry point

`/asm/patients/{id}/consent` — อสม. opens when first visiting patient

### 7.2 PWA-specific UI

Screen 1: Confirm patient present
- Show patient name + photo if available
- "คุณกำลังอยู่กับ [ชาวบ้าน] ใช่ไหม?"
- [ใช่] [ไม่ใช่ กลับไปเลือกใหม่]

Screen 2: Read consent
- Full consent text (Thai), scrollable
- Speaker icon (future: text-to-speech for illiterate)
- Button disabled until scroll to bottom: "[อ่านจบแล้ว]"

Screen 3: Granular consent checkboxes
- Core scopes (checked by default, cannot uncheck without warning)
- Optional scopes (unchecked by default)

Screen 4: Identity confirmation
- ชาวบ้านยืนยัน:
  - "ข้าพเจ้าเข้าใจเอกสารนี้แล้ว" (checkbox)
  - "ข้าพเจ้าให้ความยินยอมตามที่เลือกไว้ข้างต้น" (checkbox)

Screen 5: Digital signature
- Canvas for finger/stylus signature
- Capture min 5 strokes (enforce)
- Preview + [ล้าง] [ยืนยัน]
- Auto-capture: GPS coords, device timestamp, อสม. user_id (as witness)

Screen 6: Submit
- POST /api/v1/asm/consent/submit
- Server creates consent_records (1 per selected scope)
- Return success + reminder: "กรุณาให้ชาวบ้านเซ็นในกระดาษ + ส่งกระดาษกลับ รพ.สต."

### 7.3 Data NOT collected by PWA during consent

Based on privacy-first principle:
- ❌ Photo of patient face (not needed)
- ❌ Photo of paper form (gets filed at รพ.สต. physically)
- ❌ Voice recording (future opt-in)

### 7.4 Blocked state: no consent → no reading

If `/asm/patients/{id}/reading/new` opened but patient has no active `asm_collect` consent:
- Banner: "ยังไม่ได้รับ consent สำหรับการเก็บข้อมูล"
- CTA: "ไปเก็บ consent ก่อน"
- "บันทึก" button disabled
- Backend double-checks (defense in depth)

---

## 8. History Screen

### 8.1 `/asm/history`

อสม. ดูผลงานที่บันทึกเอง (not patients' full history)

**Layout:**
```
┌─────────────────────────┐
│ [←] ประวัติการบันทึก       │
├─────────────────────────┤
│ [เดือนนี้ ▼]             │
│ รวม 35 รายการ            │
├─────────────────────────┤
│ 17/4/2026 08:30         │
│ สมชาย ใจดี              │
│ 135/88 (72) [แก้][ลบ]   │
├─────────────────────────┤
│ 17/4/2026 08:45         │
│ สมหญิง ใจดี              │
│ 128/82 (70)             │
├─────────────────────────┤
│ ...                     │
└─────────────────────────┘
```

**Edit/Delete window**: 24 hours after creation (beyond that, only admin can)

**API**:
- `GET /api/v1/asm/history?month=2026-04`
- `PATCH /api/v1/asm/readings/{id}` (within 24h)
- `DELETE /api/v1/asm/readings/{id}` (within 24h)

---

## 9. Profile Screen

### 9.1 `/asm/profile`

```
┌─────────────────────────┐
│ [←] ข้อมูลส่วนตัว         │
├─────────────────────────┤
│  [👤]                    │
│  สมศรี อสม.              │
│  รพ.สต. เมืองเก่า         │
├─────────────────────────┤
│  📞 08x-xxx-x789         │
│  💬 Telegram: ✓ paired   │
│  📅 สมัครเมื่อ 1/4/2026    │
├─────────────────────────┤
│ จำนวนคนในความดูแล  10    │
│ บันทึกรวม            128 │
│ Accuracy OCR     96.5%   │
├─────────────────────────┤
│ [ ข้อตกลงการใช้งาน ]      │
│ [ นโยบายความเป็นส่วนตัว ] │
│ [ ติดต่อ รพ.สต. ]         │
│ [ ออกจากระบบ ]            │
└─────────────────────────┘
```

**Actions:**
- View ToS / Privacy Policy (read-only, versions)
- Contact รพ.สต. (phone link)
- Logout → clear session → redirect to login

**No profile edit here** — changes go through admin (ตาม policy อสม. = staff managed by รพ.สต.)

---

## 10. API Contract

### 10.1 Authentication

```
POST /api/v1/asm/auth/request-otp
  Body: { phone }
  Response: { sent: true }  # don't leak user existence

POST /api/v1/asm/auth/verify-otp
  Body: { phone, otp }
  Response: { access_token, user, assignment_summary }

POST /api/v1/asm/auth/refresh
  (uses refresh token cookie)
  Response: { access_token }

POST /api/v1/asm/auth/logout
  Response: { success: true }

POST /api/v1/asm/onboarding/accept-terms
  Body: { terms_version, privacy_policy_version }
  Response: { success: true }
```

### 10.2 Dashboard

```
GET /api/v1/asm/dashboard
  Response: {
    patient_count,
    readings_month,
    due_patients: [...],
    recent_activity: [...]
  }
```

### 10.3 Patients

```
GET /api/v1/asm/patients
  Query: search, sort, filter
  Response: [{id, external_id, sequence, name, age, last_reading, flags, has_consent}]

GET /api/v1/asm/patients/{external_id}
  Response: full patient detail + consent status + recent readings

GET /api/v1/asm/patients/{external_id}/readings?days=30
  Response: [{id, measured_at, systolic, diastolic, pulse, ...}]

POST /api/v1/asm/patients/{external_id}/unmask-phone
  (audit logged)
  Response: { phone: "unmasked" }

POST /api/v1/asm/patients/{external_id}/unmask-citizen-id
  (audit logged)
  Response: { citizen_id: "unmasked" }
```

### 10.4 Readings

```
POST /api/v1/asm/readings
  Body: { patient_external_id, systolic, diastolic, pulse, measured_at, 
          location_name, note, source_type }
  Response: { reading_id, success }

POST /api/v1/asm/readings/ocr/single
  Body: multipart { patient_external_id, image }
  Response: {
    pre_fill: { systolic, diastolic, pulse, measurement_time, measurement_date },
    confidence: { ... },
    warnings: [...],
    raw_output_hash  # for correlation when submitting
  }

POST /api/v1/asm/readings/ocr/batch
  Body: multipart { image }
  Response: {
    flow: "auto_confirm" | "review_needed",
    matched_patients: [...],
    bp_reading: { ... },
    confidence: { ... },
    warnings: [...],
    temp_reading_session_id  # identifier to reference in confirm step
  }

POST /api/v1/asm/readings/ocr/batch/confirm
  Body: {
    temp_reading_session_id,
    confirmed_patient_external_id,
    values_override?: { ... },  # if user edited
    notes?
  }
  Response: { reading_id, success }

PATCH /api/v1/asm/readings/{id}
  (within 24h + own readings only)
  Body: partial fields
  Response: { reading_id, success }

DELETE /api/v1/asm/readings/{id}
  (within 24h + own readings only)
  Response: { success }

GET /api/v1/asm/history?month=YYYY-MM
  Response: [{reading}...]
```

### 10.5 Consent

```
POST /api/v1/asm/consent/initiate
  Body: { patient_external_id, scopes }
  Response: { session_id, consent_form_content, version }

POST /api/v1/asm/consent/submit
  Body: {
    session_id,
    scopes_accepted,
    signature_data,
    gps,
    patient_confirmation
  }
  Response: { consent_record_ids, summary }

GET /api/v1/asm/consent/patient/{external_id}/status
  Response: { scopes: [{scope, status, granted_at}] }
```

### 10.6 Profile

```
GET /api/v1/asm/profile
  Response: { ... }
```

### 10.7 Common response codes

- 200: success
- 400: validation error
- 401: unauthenticated (token invalid/expired)
- 403: unauthorized (no permission, no consent, not assigned)
- 404: not found
- 409: conflict (duplicate)
- 422: semantic error (e.g., BP value out of range)
- 429: rate limited
- 500: server error

---

## 11. Security & Privacy Considerations

### 11.1 Token handling
- Access token: memory only (Zustand or React Context)
- Refresh token: HTTP-only + Secure + SameSite=Strict cookie
- NO tokens in localStorage / sessionStorage (XSS defense)

### 11.2 Image handling (strict)
- Single OCR: image in memory only, discard after Gemini call
- Batch OCR happy path: image discarded after confirm
- Batch OCR review path: stored max 7 days, encrypted, purpose-locked
- Never cache images on client beyond current session

### 11.3 Permissions enforcement
- Every API call goes through RBAC + consent middleware
- Frontend hides buttons, but backend is source of truth
- อสม. can only see their assigned patients' data

### 11.4 GPS handling
- Requested only at: consent capture, optional at reading capture
- User can deny → log reason, continue without GPS
- Never shared cross-user

### 11.5 Camera permissions
- Requested on first camera use
- User can deny → fallback to manual entry
- No background / auto camera access

### 11.6 Clipboard / PII leakage
- Never write PII to clipboard without explicit user action
- Masked phone / citizen ID: unmask = audit log event

### 11.7 Network
- HTTPS only (HSTS)
- Certificate pinning (Phase 2 for extra security)

### 11.8 Session revocation
- Admin can force logout อสม. (token blacklist in Redis)
- Logout on: suspend, role change, pairing code revoked

---

## 12. UX Requirements

### 12.1 Performance
- **First meaningful paint**: < 2s on 3G
- **Interactive**: < 3s on 3G
- **OCR upload + response**: < 8s (p95, depending on image size + Gemini)
- **Skeleton loaders** for all async content

### 12.2 Accessibility
- WCAG AA minimum
- Large touch targets (48×48 min)
- High contrast (4.5:1 text)
- Screen reader support (aria labels, semantic HTML)
- Text resize: 200% without broken layout

### 12.3 Error handling
- Network error: "ไม่สามารถเชื่อมต่อได้ กรุณาลองอีกครั้ง" + retry
- OCR fail: "อ่านรูปไม่สำเร็จ" + fallback to manual
- Permission error: "ไม่มีสิทธิ์" + explain + contact support
- 500 error: generic friendly + report link

### 12.4 Thai-specific
- Default language: TH
- Switcher: EN (for admin/dev testing)
- Buddhist calendar option (display only)
- Thai-formatted phone (08X XXX XXXX)

### 12.5 Notification feedback
- Success: green toast, auto-dismiss 3s
- Warning: yellow, manual dismiss
- Error: red, manual dismiss

### 12.6 Confirmation modals
- Destructive: delete reading → "แน่ใจหรือไม่? ย้อนกลับไม่ได้"
- Edit override: OCR override → "แก้ไขค่าที่ OCR อ่านได้? (คุณกำลังแทนที่ 130 ด้วย 140)"

---

## 13. Offline Handling (MVP: minimal)

### 13.1 What works offline in MVP

- Reading PWA shell (already loaded)
- Form UI (can type values but not submit)
- Cached patient list (last fetched, read-only)

### 13.2 What does NOT work offline (MVP)

- New reading submission (network required)
- OCR upload
- Consent submission
- Login / OTP

### 13.3 Fallback strategy

- Show clear offline banner: "ไม่มีสัญญาณ — กรุณาลองอีกครั้งเมื่อเชื่อมต่อได้"
- Prevent form submission
- Optional Phase 2: store in IndexedDB + sync later (requires Service Worker + Background Sync API)

### 13.4 Weak signal scenarios (MVP)

- Photo taken but upload fails: user can retry manually (photo stored in browser memory during session only)
- OCR call timeout: retry with exponential backoff (3 attempts)
- Session token expires mid-flow: prompt re-login, preserve form state if possible

---

## 14. Testing Requirements

### 14.1 Unit tests
- Every API endpoint's validation + permission check
- Gemini response parsing + edge cases (multiple ticks, no tick, name mismatch)
- Fuzzy name matching accuracy
- Consent enforcement middleware

### 14.2 Integration tests
- End-to-end: onboarding → first reading submission
- End-to-end: consent capture → reading → withdrawal → reading blocked
- End-to-end: batch OCR happy path + each edge case

### 14.3 UX tests
- Tested on **real elderly user** (target demographic for อสม.)
- Tested on low-end Android device (2GB RAM)
- Tested on poor network (3G, 2G)
- Landscape rotation on photo capture

### 14.4 Security tests
- XSS in input fields
- CSRF on state-changing endpoints
- Authorization: อสม. A accessing อสม. B's patient → 403 + audit
- Token theft scenarios (token in localStorage attempt)
- Rate limit verification

### 14.5 Privacy tests
- Image not stored after flow completes (verify DB)
- Image auto-deleted after 7 days in review queue (cron test)
- GPS not sent without user consent
- PII masking by default

---

## 15. Implementation Checklist

### 15.1 Foundation
- [ ] Route structure under `/app/asm/`
- [ ] PWA manifest + Service Worker (basic)
- [ ] Auth state management (Zustand)
- [ ] API client with JWT + refresh flow
- [ ] Error boundary + toast system
- [ ] Thai i18n

### 15.2 Auth
- [ ] Login screen + OTP flow
- [ ] Telegram pairing flow (backend bot handler)
- [ ] Onboarding screens (ToS acceptance)
- [ ] Session management

### 15.3 Core screens
- [ ] Home dashboard
- [ ] Patient list + search + filter
- [ ] Patient detail
- [ ] Quick entry form (manual)

### 15.4 Single OCR
- [ ] Camera capture + preview
- [ ] Upload + Gemini integration
- [ ] Pre-fill form + confirmation
- [ ] Save reading

### 15.5 Batch OCR
- [ ] Batch capture screen
- [ ] Gemini prompt + response parsing
- [ ] Fuzzy name matching
- [ ] Review UI (happy + edge cases)
- [ ] Save with image cleanup logic
- [ ] Admin print ใบรายชื่อ endpoint + PDF template

### 15.6 Consent
- [ ] Consent flow screens
- [ ] Digital signature capture
- [ ] GPS capture
- [ ] Submit + backend consent_records creation

### 15.7 History + Profile
- [ ] History list + filter
- [ ] Edit/delete (within 24h)
- [ ] Profile view
- [ ] Logout

### 15.8 Security
- [ ] RBAC middleware on all endpoints
- [ ] Consent enforcement middleware
- [ ] Rate limiting
- [ ] Audit log integration

### 15.9 Testing
- [ ] Unit tests (> 80% coverage)
- [ ] Integration tests (happy + edge paths)
- [ ] Manual UX test with real user
- [ ] Security penetration test

---

## 16. Out of Scope (Phase 2+)

- Offline queue + background sync (full offline-first)
- Multi-language TH/EN in consent flow (TH only MVP)
- Voice-to-text for consent (illiterate accessibility)
- Photo enhancement on-device (auto-rotate, auto-crop)
- Multiple patients in single batch photo
- Native mobile app (iOS/Android)
- Biometric login (fingerprint, face)
- Push notifications via Web Push (use Telegram bot MVP)
- Advanced analytics (อสม. dashboard)
- Patient self-upgrade (proxy → self_managed) wizard

---

**End of ASM_PWA_SPEC.md**
