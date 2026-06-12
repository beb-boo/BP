---
title: "PWA Spec — Main App (General Users)"
aliases:
  - "PWA Spec"
  - "Main PWA"
tags:
  - pwa
  - frontend
  - v2-asm-org
order: 4.5
status: implemented
version: 1.1
updated: 2026-06-11
summary: "PWA layer บน Next.js frontend หลัก (general users) — manifest, service worker, web push, offline-first BP entry, service layer unification"
---
# PWA Specification — Main App (General Users / B2C)

> **Status:** Implemented v1.1 (Sprint 1-4 executed 2026-06-11; field testing on real devices pending)
> **Last updated:** 2026-06-11
> **Owner:** Pornthep
> **Depends on:** existing frontend (`frontend/`), existing backend (`app/`)
> **Related:** `CAREGIVER_PWA_SPEC.md` (PWA สำหรับ อสม. — คนละ scope, ดู §1.2), `SCALABILITY_PLAN.md`, `TELEGRAM_MINI_APP_PLAN.md` (ใน `plan/`)
> **Companion:** `PWA_SPRINT_TASKS.md` — detailed task list สำหรับ Claude Code

> [!NOTE] **v1.1 — Implementation deviations (as built)**
> Decisions D1-D5 ทั้งหมดคงเดิม ไม่มีข้อใดถูกละเมิด Deviation จาก v1.0:
> 1. **SW tooling = `@serwist/turbopack`** (ไม่ใช่ `@serwist/next`): `withSerwistInit` ของ @serwist/next inject webpack config ซึ่ง Next 16 (Turbopack default) reject ตอน build — ใช้ Turbopack integration อย่างเป็นทางการของ Serwist แทน SW ถูก serve ที่ **`/serwist/sw.js`** ผ่าน route handler `frontend/app/serwist/[path]/route.ts` (มี `Service-Worker-Allowed: /`) ไม่มี generated file ใน `public/`
> 2. **`NotificationChannel.send(db, user, payload)`** — เพิ่ม db session param จาก snippet §6.6 (channel ต้องใช้ session ของ caller ในการ update subscription state)
> 3. **§6.7 ผล grep จริง:** call site เดิมที่ส่งหา user มีจุดเดียวคือ OCR auto-save (`app/bot/handlers.py`) ซึ่ง**คงไว้ที่ bot** — เป็น conversational feedback ใน chat ไม่ใช่ notification; reminder cron ไม่เคยมีอยู่ → สร้างใหม่เป็น `GET /api/v1/cron/reminders` (CRON_SECRET-protected, ทุก 15 นาที จับ `reminder_times` ตาม timezone ของ user, Vercel Cron หรือ external scheduler)
> 4. **Abnormal alert** (Sprint 4): เกณฑ์ hypertensive crisis (SBP>180 หรือ DBP>120) → fire-and-forget ผ่าน NotificationService ใน `BPRecordService.create_record`
> 5. **Model style ตาม repo เดิม:** `DateTime default=now_tz` (ไม่ใช่ `server_default=func.now()`), `client_record_id` เป็น `VARCHAR(36)` ไม่ใช่ native uuid (SQLite dev compat); `notification_preferences` ใช้ `JSON().with_variant(JSONB, "postgresql")`
> 6. **Background Sync:** queue + sync engine อยู่ฝั่ง client ทั้งหมด (axios auth reuse, testable); SW `sync` event แค่ปลุก window ที่เปิดอยู่ผ่าน message — iOS ครอบด้วย client triggers ตามแผน
> 7. **Settings consolidation (T4.4):** frozen dataclass + lru_cache ใน `app/config/settings.py` (ไม่เพิ่ม dependency pydantic-settings) — ครอบเฉพาะ env ใหม่ของ PWA
> 8. Icons เป็น **placeholder** (blue-600 + หัวใจขาว + "BP") — รอ logo จริงจาก Pornthep

---

## 1. Purpose & Scope

### 1.1 Purpose

เพิ่ม PWA capability ให้ **frontend หลักที่มีอยู่** (Next.js 16, `frontend/`) เพื่อให้ general users (B2C):

- ติดตั้ง BP Monitor บน home screen เป็นแอป (standalone)
- รับ **Web Push notification** (daily reminder, abnormal alert) โดยไม่ต้องพึ่ง Telegram
- **บันทึก BP ขณะ offline** แล้ว sync อัตโนมัติเมื่อกลับมา online
- ลดการพึ่งพา Telegram bot ให้เป็น optional channel (ตาม strategy: Telegram rate limit ~30 msg/s เป็น hard ceiling ที่ scale)

### 1.2 ความสัมพันธ์กับ CAREGIVER_PWA_SPEC

| | **PWA_SPEC (this doc)** | **CAREGIVER_PWA_SPEC** |
|---|---|---|
| Target user | General users (B2C) | อสม. / caregiver (org) |
| Routes | ทุก route เดิมของ frontend (`/`, `/auth`, dashboard) | `/caregiver/*` |
| Manifest scope | `/` (root) | `/caregiver/` |
| Auth | Email/password เดิม (+ LINE later) | Phone + OTP via Telegram |
| Push | **Web Push (สร้างใหม่ใน spec นี้)** | Telegram bot (MVP); reuse Web Push infra ใน Phase 2 |
| Offline | **Offline-first BP entry (Sprint 3)** | Minimal (MVP), full offline Phase 2 |

**Infrastructure ที่ spec นี้สร้างและ caregiver PWA จะ reuse ภายหลัง:**
- `PushSubscription` model + `/api/v1/push/*` endpoints
- `NotificationChannel` adapter pattern + `NotificationService`
- Service worker tooling (Serwist) + offline queue pattern

**Cascade note → CAREGIVER_PWA_SPEC:**
- §2.1 ระบุ "`next-pwa` package or custom Service Worker" → **superseded: ใช้ Serwist** (canonical ทั้ง repo, ดู §3.1)
- §16 Out of Scope "Push notifications via Web Push" → เมื่อ infra จาก spec นี้พร้อม การเปิด web push ให้ caregiver = config เพิ่ม ไม่ใช่งานสร้างใหม่

### 1.3 Out of Scope (เอกสารนี้)

- Caregiver/อสม. flows ทั้งหมด (อยู่ใน CAREGIVER_PWA_SPEC)
- LINE Login implementation (ออกแบบ schema รองรับเท่านั้น — §5.3)
- Native mobile app
- Job queue / async OCR (Gemini OCR ~2-3s ยังรับได้ใน sync path — defer จนกระทบจริง)
- Storage adapter สำหรับภาพ (ระบบไม่เก็บภาพ — ephemeral OCR เท่านั้น)

---

## 2. Locked Decisions

ตัดสินใจแล้ว (2026-06-11) — เปลี่ยนได้เฉพาะผ่านการ update เอกสารนี้ + INDEX:

| # | Decision | Choice |
|---|----------|--------|
| D1 | PWA URL strategy | **ใช้ frontend เดิมทั้งหมด** — ไม่แยก subdomain/path; root manifest scope `/` |
| D2 | Authentication | **Email/password เดิม** + ออกแบบ schema/flow ให้เพิ่ม "Sign in with LINE" ได้แบบ additive (§5.3) |
| D3 | Notification preferences storage | **JSONB column `notification_preferences` บนตาราง `users`** (§6.4) |
| D4 | Push content privacy | **Default: ข้อความทั่วไป** ("ถึงเวลาวัดความดัน") ไม่มีค่าสุขภาพ; user **opt-in** เพื่อเห็นรายละเอียดใน lock screen (§6.5) |
| D5 | Service worker update strategy | **ถาม user ผ่าน `PWAUpdatePrompt`** ก่อน activate version ใหม่ — กัน unsaved input หาย (§4.4) |

---

## 3. Architecture

### 3.1 Tech additions

| Layer | Choice | เหตุผล |
|-------|--------|--------|
| SW tooling | **`@serwist/next` + `serwist`** | Successor ของ Workbox, รองรับ App Router/TypeScript; `next-pwa` ไม่ active แล้ว |
| Manifest | `app/manifest.ts` (Next `MetadataRoute.Manifest`) | Native Next.js ไม่ต้องมี static json |
| IndexedDB | **`idb`** (~1.5kb) | TypeScript wrapper มาตรฐาน |
| Web Push (server) | **`pywebpush`** ใน FastAPI | Backend เดิมเป็น Python; VAPID standard |
| Push endpoints | **FastAPI** (`app/routers/push.py`) | `next.config.ts` rewrite `/api/v1/* → backend` อยู่แล้ว — single backend, ไม่สร้าง Next API route |

> [!WARNING] Version check ตอน implement — **RESOLVED v1.1**
> peerDependencies ของ @serwist/next ผ่าน (next>=14) แต่ตัว integration เป็น webpack-only ซึ่งชนกับ Turbopack ของ Next 16 ตอน build จริง → ใช้ **`@serwist/turbopack`** (official, same Serwist family) แทน — ดู deviation note ข้างบน ห้ามใช้ `next-pwa` เช่นเดิม

### 3.2 Frontend file map

```
frontend/
├── app/
│   ├── manifest.ts                    # NEW — Web App Manifest (scope "/")
│   ├── ~offline/page.tsx              # NEW — offline fallback page
│   └── layout.tsx                     # EDIT — register SW + mount prompts
├── sw/
│   └── index.ts                       # NEW — Serwist SW source (swSrc)
├── public/
│   └── icons/                         # NEW — icon-192, icon-512, maskable-512
├── components/pwa/
│   ├── PWAInstallPrompt.tsx           # NEW — Android beforeinstallprompt + iOS instructions
│   ├── PWAUpdatePrompt.tsx            # NEW — D5: ask before SW activate
│   ├── PushNotificationSettings.tsx   # NEW — subscribe toggle + D4 opt-in detail
│   └── OfflineSyncIndicator.tsx       # NEW — pending queue count + manual sync
├── lib/pwa/
│   ├── registerSW.ts                  # NEW
│   ├── pushSubscription.ts            # NEW — subscribe/unsubscribe helpers
│   └── offlineQueue.ts                # NEW — idb queue (Sprint 3)
├── locales/{en,th}.ts                 # EDIT — pwa.* keys (route ผ่าน t() เท่านั้น)
├── next.config.ts                     # EDIT — wrap withSerwist (คง rewrites + standalone เดิม)
└── package.json                       # EDIT — @serwist/next, serwist, idb
```

### 3.3 Backend file map

```
app/
├── routers/
│   └── push.py                        # NEW — subscribe/unsubscribe/test endpoints
├── adapters/                          # NEW package
│   └── notification/
│       ├── __init__.py
│       ├── base.py                    # NotificationChannel ABC + payload/result dataclasses
│       ├── web_push.py                # pywebpush wrapper
│       ├── telegram.py                # wrap existing bot send logic (ย้าย ไม่เขียนใหม่)
│       └── factory.py                 # build_notification_service(settings)
├── services/
│   ├── notification_service.py        # NEW — orchestrator (preference → fan-out → fallback)
│   └── bp_service.py                  # NEW (Sprint 4) — shared business logic bot + API
├── models.py                          # EDIT — PushSubscription + users.notification_preferences
├── schemas.py                         # EDIT — push schemas
└── routers/users.py                   # EDIT — GET/PATCH notification preferences
migrations/
└── add_push_subscriptions.py          # NEW — ตาม pattern ad-hoc + rollback function
```

### 3.4 Manifest scope strategy (D1)

Root manifest `scope: "/"` ครอบทุก route รวม `/caregiver/*` ในอนาคต Chrome/Android อนุญาตหลาย installable manifest บน origin เดียวถ้า `start_url`/`scope` ต่างกัน — caregiver manifest (`scope: "/caregiver/"`) จะ take precedence ภายใน path ตัวเอง ผู้ใช้ติดตั้งได้ทั้งสองแอปแยกกัน **ไม่ต้องแก้อะไรตอนนี้** แค่อย่า hardcode assumption ว่า origin มี manifest เดียว

---

## 4. Service Worker Design

### 4.1 Cache strategies

| Pattern | Strategy | หมายเหตุ |
|---------|----------|---------|
| `/_next/static/*`, fonts, icons | CacheFirst (1y) | immutable assets |
| `/api/v1/auth/*` | NetworkOnly | ห้าม cache credential flows |
| `GET /api/v1/bp-records*` | NetworkFirst → cache fallback | ดูประวัติ offline ได้ |
| `POST/PATCH/DELETE /api/v1/*` | NetworkOnly (+ offline queue เฉพาะ BP create, §7) | mutation ห้าม cache |
| `/api/v1/ocr/*` | NetworkOnly | ต้องถึง Gemini |
| Stats/summary GET | StaleWhileRevalidate | แสดงเก่าก่อน refresh เบื้องหลัง |
| Navigation (HTML) | NetworkFirst → `/~offline` fallback | |

> [!WARNING] ห้าม cache response ที่มี PII เกินจำเป็น
> Cache ของ bp-records อยู่ใน CacheStorage บนเครื่องผู้ใช้เอง (acceptable — เป็นข้อมูลของเจ้าของเครื่อง) แต่ต้อง **ล้าง cache + IndexedDB ทั้งหมดตอน logout** (`caches.delete` + clear idb) กันเครื่องที่ใช้ร่วมกัน

### 4.2 Precache

App shell: layout, `/~offline`, dashboard entry, critical CSS/JS (Serwist จัดการผ่าน build manifest)

### 4.3 Push event handling

SW รับ `push` event → `showNotification(title, {body, icon, tag, data.url})` → `notificationclick` → focus/open `data.url`

### 4.4 Update flow (D5)

```
SW ใหม่ install สำเร็จ → state "waiting"
→ client ตรวจพบ (registration.waiting) → แสดง PWAUpdatePrompt (sonner toast, ไม่ auto dismiss)
   "มีเวอร์ชันใหม่ — [อัปเดตเลย] [ภายหลัง]"
→ [อัปเดตเลย] → postMessage({type:"SKIP_WAITING"}) → controllerchange → reload
→ [ภายหลัง] → ไม่ทำอะไร; activate ตอนปิด tab ทั้งหมดเองตาม lifecycle ปกติ
```

ห้าม `skipWaiting()` อัตโนมัติใน SW — ขัด D5

---

## 5. Authentication

### 5.1 ปัจจุบัน (ไม่เปลี่ยนใน PWA งวดนี้)

Email/password เดิมผ่าน `app/routers/auth.py` PWA standalone ใช้ flow เดียวกับ browser ปกติ — ไม่มีงานเพิ่มนอกจากทดสอบว่า login/refresh ทำงานใน standalone mode (cookie ทำงานปกติเพราะ same-origin ผ่าน rewrite)

> [!NOTE] Implementation guard
> ก่อนแตะ auth code ใดๆ ให้อ่าน `app/routers/auth.py` + `frontend/lib/` (axios + js-cookie usage) จริงก่อน — ห้าม assume token mechanics จากเอกสาร

### 5.2 ข้อจำกัด iOS standalone

iOS PWA (standalone) แยก cookie storage จาก Safari → user ต้อง login ใหม่ครั้งแรกหลัง install (ครั้งเดียว) — เป็น expected behavior, ใส่ข้อความอธิบายถ้าจำเป็น

### 5.3 LINE Login readiness (D2 — design only, ไม่ implement งวดนี้)

หลักการ: **identity แยกจาก credential** เพื่อให้ user หนึ่งคน link ได้หลาย provider

```sql
-- migration อนาคต (ยังไม่รันงวดนี้)
CREATE TABLE auth_identities (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider      VARCHAR(20) NOT NULL,        -- 'line' | 'google' | ...
    provider_user_id_hash VARCHAR(64) NOT NULL, -- SHA-256 (ตาม PII pattern เดิม)
    provider_user_id_encrypted TEXT,            -- Fernet (ops/debug)
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ,
    UNIQUE (provider, provider_user_id_hash)
);
```

Flow อนาคต: LINE OAuth → ได้ `line_user_id` → lookup `auth_identities` → มี = login, ไม่มี = (a) user logged-in อยู่ → link, (b) ไม่ → สร้าง user ใหม่หรือชวน link ด้วย email

**สิ่งที่ต้องไม่ทำตอนนี้เพื่อไม่ปิดทาง:**
- JWT issuance ต้อง provider-agnostic (อย่า encode "password" assumption ใน token/claims)
- อย่า unique-constrain email แบบที่ห้าม user ไม่มี password (LINE-only user อาจไม่มี password ในอนาคต — ตรวจ nullable ตอน implement จริง)
- หมายเหตุ: Telegram pairing เดิม (`telegram_id_hash` บน users) คือ identity provider โดยพฤตินัย — ตอนทำ LINE จริง พิจารณา migrate เข้า `auth_identities` ด้วย (จดไว้ ไม่ทำตอนนี้)

---

## 6. Web Push Notification

### 6.1 VAPID

```bash
npx web-push generate-vapid-keys
```

| Env | ที่ |
|-----|-----|
| `WEB_PUSH_VAPID_PUBLIC` | backend + `NEXT_PUBLIC_VAPID_PUBLIC_KEY` (frontend) |
| `WEB_PUSH_VAPID_PRIVATE` | backend เท่านั้น |
| `WEB_PUSH_VAPID_SUBJECT` | `mailto:...` backend |

Key คู่เดียวต่อ environment (dev/prod แยกชุด) เปลี่ยน key = subscription เดิมตายทั้งหมด — ห้าม rotate โดยไม่มีแผน

### 6.2 Data model

```python
class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(String(500), nullable=False, unique=True)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    user_agent = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, nullable=False)
```

1 user : N subscriptions (หลาย device) Endpoint URL ไม่ใช่ PII ตรง แต่ปฏิบัติเหมือน sensitive (อย่า log เต็ม)

### 6.3 API contract

```
POST   /api/v1/push/subscribe      Body: {endpoint, keys:{p256dh, auth}}   → {id}
        (upsert by endpoint; re-subscribe = reactivate)
DELETE /api/v1/push/subscribe      Body: {endpoint}                        → {success}
POST   /api/v1/push/test           (authed; ส่ง test notification หา device ของตัวเอง) → {delivered}
GET    /api/v1/users/me/notification-preferences                           → JSONB
PATCH  /api/v1/users/me/notification-preferences  Body: partial JSONB      → updated JSONB
```

ทุก endpoint: authenticated, rate-limited (subscribe 10/h/user)

### 6.4 Notification preferences (D3 — JSONB บน users)

```python
notification_preferences = Column(JSONB, nullable=False, server_default='{}')
```

```jsonc
// shape v1 — validate ด้วย Pydantic ฝั่ง API เสมอ
{
  "channels": ["web_push", "telegram"],   // ลำดับ = priority
  "show_details_in_push": false,           // D4 opt-in
  "reminder_enabled": true,
  "reminder_times": ["07:00", "19:00"]     // local time ของ user (มี timezone column แล้ว)
}
```

Default เมื่อ `{}`: `channels` อนุมานจากที่ user มี (telegram paired → telegram; มี push sub → web_push), `show_details_in_push=false`, `reminder_enabled=true`

### 6.5 Push content privacy (D4)

| Mode | Title | Body | เงื่อนไข |
|------|-------|------|---------|
| Generic (default) | "BP Monitor" | "ถึงเวลาวัดความดันโลหิต" / "มีข้อมูลใหม่ในระบบ" | เสมอ เว้นแต่ opt-in |
| Detailed (opt-in) | "BP Monitor" | อาจมีค่า/ชื่อ context | `show_details_in_push == true` เท่านั้น |

บังคับที่ **`NotificationService` ชั้นเดียว** (ไม่ใช่ที่ caller แต่ละจุด): payload เข้ามาแบบ detailed เสมอ → service ตรวจ preference → ถ้าไม่ opt-in แทนที่ body ด้วย generic text **ต่อ channel** — ใช้กับ web_push (lock screen) เป็นหลัก; telegram ถือว่า user ยอมรับ channel นั้นแล้ว แสดง detail ได้ตามพฤติกรรมเดิม ทุก locale string ผ่านระบบ i18n ฝั่ง backend ตาม pattern bot เดิม (ดู `app/bot/locales.py`)

### 6.6 Adapter pattern

```python
# app/adapters/notification/base.py
@dataclass
class NotificationPayload:
    title: str
    body: str
    body_generic: str | None = None   # D4: ใช้แทน body เมื่อไม่ opt-in
    url: str | None = None
    tag: str | None = None
    data: dict | None = None

@dataclass
class DeliveryResult:
    success: bool
    channel: str
    error: str | None = None
    should_disable_target: bool = False   # 404/410 Gone → deactivate subscription

class NotificationChannel(ABC):
    channel_name: str
    @abstractmethod
    async def send(self, user, payload: NotificationPayload) -> DeliveryResult: ...
```

- `WebPushChannel`: loop active subscriptions ของ user; 404/410 → `is_active=False`; success ≥1 device = success
- `TelegramChannel`: **wrapper บางๆ รอบ send logic ที่มีอยู่** ใน `app/bot/` — ย้าย/เรียกใช้ ไม่เขียนซ้ำ
- `NotificationService.notify(user, payload)`: อ่าน preference → ลอง channel ตามลำดับ → ตัวแรกที่สำเร็จคือจบ (v1: first-success; broadcast-all เป็น option อนาคต) → log ทุก attempt

### 6.7 จุดที่ต้องเปลี่ยนมาเรียก NotificationService

ทุกจุดที่ปัจจุบันส่งหา user ผ่าน Telegram ตรงๆ (reminder cron, abnormal alert, ฯลฯ) → เปลี่ยนเป็นเรียก `NotificationService` **Implementation guard: grep หา call sites จริงก่อน** (`bot.send_message`, reminder jobs) — อย่า assume ว่ามีกี่จุด

---

## 7. Offline-First BP Entry (Sprint 3)

### 7.1 Queue design (idb)

```typescript
interface QueuedBPRecord {
  id: string;              // client UUID = idempotency key
  payload: BPRecordCreatePayload;
  createdAt: number;
  retryCount: number;
  status: 'pending' | 'syncing' | 'failed';
  lastError?: string;
}
// DB: "bp-monitor-offline", store: "bp-queue", keyPath: "id"
```

### 7.2 Submit flow

```
user กด save
→ online + POST สำเร็จ → ปกติ
→ offline หรือ network error → enqueue → toast "บันทึกไว้ในเครื่อง จะส่งเมื่อมีสัญญาณ"
  → register Background Sync ("bp-sync") ถ้า browser รองรับ
→ sync triggers: (1) Background Sync event, (2) window "online" event,
  (3) app open/foreground, (4) ปุ่ม manual sync — (2)-(4) คือ fallback สำหรับ iOS
→ ต่อ item: POST พร้อม client id → สำเร็จ/409 duplicate → ลบจาก queue
  → fail → retryCount++; ≥5 → status "failed" (ให้ user retry/ลบเอง)
```

### 7.3 Idempotency (backend — บังคับ)

Client ส่ง `client_record_id` (UUID) ใน payload Backend:

- เพิ่ม column `client_record_id UUID NULL` + **unique index** บนตาราง BP records (additive migration)
- ซ้ำ → return record เดิม (200) ไม่สร้างใหม่

ขาดข้อนี้ retry จะสร้าง record ซ้ำ — เป็น blocker ของ Sprint 3 ไม่ใช่ nice-to-have

### 7.4 ข้อมูลใน IndexedDB = PHI บนเครื่อง

- เก็บเฉพาะ payload ที่จำเป็น ไม่เก็บ token
- ล้างทั้ง DB ตอน logout
- แจ้งใน UI ว่ามีข้อมูลรอส่งกี่รายการ (`OfflineSyncIndicator`)

### 7.5 iOS

ไม่มี Background Sync → ใช้ trigger (2)-(4) อย่างเดียว; Safari ลบ IndexedDB หลังไม่ใช้ ~7 วัน → indicator ต้องชัดว่ามีของค้าง

---

## 8. Service Layer Unification (Sprint 4)

แก้ปัญหา logic ซ้ำระหว่าง `app/routers/bp_records.py`, `app/routers/ocr.py`, และ `app/bot/handlers.py`:

```python
# app/services/bp_service.py
class BPRecordService:
    async def create_record(self, user, data, *, source: str, client_record_id: UUID | None = None) -> BPRecord:
        # validate ranges → duplicate/idempotency check → save
        # → abnormal check → NotificationService alert → stats invalidation
    async def process_ocr(self, user, image_bytes: bytes) -> OCRResult:
        # Gemini (ephemeral — ไม่เก็บภาพ ตามเดิม)
```

Router และ bot handler เหลือหน้าที่: parse input → เรียก service → format output **ย้ายแบบ verbatim ก่อน (behavior-preserving) แล้วค่อย refactor** — ห้ามเปลี่ยน behavior กับ refactor ใน commit เดียว

ผล: PWA, Telegram, และ caregiver PWA ในอนาคต ใช้ code path เดียว

---

## 9. UX Requirements

- Install prompt: Android = `beforeinstallprompt` (custom UI, แสดงหลัง user มี engagement ไม่ใช่ทันทีที่เข้า); iOS = instruction modal (Share → Add to Home Screen) ตรวจจาก UA + `display-mode`
- ทุก string ใหม่เข้า `locales/en.ts` + `locales/th.ts` route ผ่าน `t()` — **ห้าม render enum/raw backend value ใน UI** (key learning เดิม)
- Toast ใช้ sonner ที่มีอยู่
- Lighthouse PWA: installable + no console errors; Performance ≥ 80 mobile
- Permission prompt ของ Notification ต้องมาจาก user gesture (กดปุ่มใน settings) — ห้ามขอ on load

---

## 10. Testing & Acceptance

### Per-sprint acceptance

| Sprint | Acceptance |
|--------|-----------|
| 1 | ติดตั้งบน Android Chrome ได้; เปิด offline แล้วเห็น app shell/`~offline` ไม่ใช่ dinosaur; Lighthouse installable pass; ของเดิม (auth, dashboard, telegram mini app) ไม่พัง |
| 2 | กดเปิดแจ้งเตือนใน settings → ได้รับ test push บนมือถือจอล็อก; ปิด → ไม่ได้รับ; 410 endpoint ถูก deactivate; generic text by default, detail เมื่อ opt-in |
| 3 | เปิด airplane mode → บันทึก BP → ปิด airplane → record ขึ้น server ภายใน 1 นาที (Android) หรือเมื่อเปิดแอป (iOS); retry ไม่สร้าง duplicate; logout ล้าง queue |
| 4 | บันทึกผ่าน bot และผ่าน web ให้ผลเหมือนเดิมทุกประการ (regression); abnormal alert ออกทาง channel ตาม preference; tests ผ่าน |

### Regression ที่ต้องเช็คทุก sprint

- Telegram bot ทำงานปกติ (webhook, บันทึก, OCR)
- Telegram Mini App (`frontend/app/telegram/`) ไม่ได้รับผลกระทบจาก SW caching (เพิ่ม route นี้ใน NetworkOnly/NetworkFirst ให้เหมาะ — ตรวจตอน implement)
- Vercel deploy สำเร็จ (SW build ใน CI)

---

## 11. Rollout

1. Deploy หลัง Sprint 1 ทันที (PWA install เป็น additive ไม่กระทบใคร)
2. Push (Sprint 2) เปิดเป็น opt-in ใน settings — ไม่มี migration ของพฤติกรรมเดิม
3. Offline (Sprint 3) เปิดเงียบๆ — พฤติกรรม online ปกติไม่เปลี่ยน
4. Sprint 4 เป็น internal refactor — ต้องมี regression test ก่อน merge

Rollback: ถ้า SW มีปัญหาร้ายแรง → deploy SW เปล่าที่ `self.registration.unregister()` + ล้าง caches (เตรียม snippet ไว้ใน task list)

---

**End of PWA_SPEC.md**
