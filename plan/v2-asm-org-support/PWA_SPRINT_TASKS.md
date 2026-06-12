---
title: "PWA Sprint Tasks — Claude Code Execution Plan"
aliases:
  - "PWA Tasks"
tags:
  - pwa
  - tasks
  - claude-code
  - v2-asm-org
order: 4.6
status: done
version: 1.1
updated: 2026-06-11
summary: "Detailed task list สำหรับ Claude Code execute — 4 sprints: PWA foundation, web push, offline-first, service layer unification"
---
# PWA Sprint Tasks — สำหรับ Claude Code

> [!NOTE] **Executed 2026-06-11** — ทั้ง 4 sprints เสร็จบน stacked branches `feature/pwa-sprint-1..4` (commit ต่อ task) Deviations ทั้งหมดสรุปไว้ใน `PWA_SPEC.md` v1.1 header note เหลือ field testing บนมือถือจริง + Vercel deploy (ดู verification checklist ของแต่ละ sprint)

> **Spec:** `PWA_SPEC.md` (อ่านก่อนเริ่มทุก sprint — decisions D1-D5 lock อยู่ที่นั่น)
> **Repo:** `/Users/seal/Documents/GitHub/BP`
> Frontend = `frontend/` (Next.js 16.1.1, App Router, Tailwind 4, axios, js-cookie, sonner)
> Backend = `app/` (FastAPI), migrations = `migrations/` (ad-hoc scripts + `run_all.py`)

---

## Ground Rules (ทุก sprint)

1. **อ่าน code จริงก่อนแก้เสมอ** — ห้าม assume โครงสร้างจากเอกสารนี้ ถ้าไฟล์จริงต่างจากที่เขียนไว้ ให้ยึดไฟล์จริงและบันทึก deviation ไว้ท้าย commit message
2. **Behavior-preserving ก่อน refactor** — งานย้าย code (Sprint 4) แยก commit จากงานเปลี่ยน behavior
3. **Migration ทุกตัวมี `upgrade()` + `rollback()`** ตาม pattern ใน `migrations/` เดิม และลงทะเบียนใน `run_all.py` + `schema_migrations`
4. **UI strings ทุกตัวเข้า `frontend/locales/en.ts` + `th.ts`** เรียกผ่าน `t()` (`contexts/LanguageContext.tsx`) — ห้าม hardcode ห้าม render raw enum
5. **อย่าแตะ** `frontend/app/telegram/` behavior, bot webhook flow, payment flows — นอกจากที่ task ระบุ
6. **ทดสอบหลังทุก task ที่มี ✅ Verify** — ถ้า verify ไม่ผ่าน ห้ามไป task ถัดไป
7. Commit ต่อ task (หรือกลุ่ม task เล็ก) — message format: `pwa(sprint-N): <task>`

---

## Sprint 0 — Pre-flight (ทำครั้งเดียว ~30 นาที)

### T0.1 — Survey actual code
อ่านไฟล์ต่อไปนี้ทั้งหมดก่อนเริ่ม (ใช้ read หลายไฟล์รวดเดียว):
- `frontend/next.config.ts`, `frontend/package.json`, `frontend/app/layout.tsx`
- `frontend/lib/` ทั้ง dir (หา axios client + token mechanics)
- `frontend/contexts/LanguageContext.tsx`, `frontend/locales/th.ts` (ดู key structure)
- `app/main.py`, `app/models.py` (User model), `app/routers/auth.py`, `app/routers/bp_records.py`, `app/routers/ocr.py`
- `app/bot/handlers.py`, `app/bot/services.py` (หา send/notify logic + reminder mechanism)
- `migrations/add_timezone_column.py` (template สำหรับ migration ใหม่)

**Output:** จด (ใน scratch note) — (a) token เก็บที่ไหน/อ่านยังไง, (b) จุดส่ง Telegram notification ทั้งหมด (grep `send_message`), (c) BP record create logic อยู่ไฟล์/ฟังก์ชันไหนบ้าง, (d) duplicate-check logic เดิมมีไหม

### T0.2 — Serwist compatibility check
```bash
cd frontend && npm info @serwist/next peerDependencies
```
- รองรับ Next 16 → ใช้ Serwist ตามแผน
- ไม่รองรับ → **fallback plan:** custom SW (`public/sw.js` เขียนเอง + register manual) — โครง task เดิมใช้ได้ เปลี่ยนเฉพาะ T1.2/T1.5
- บันทึกผลไว้ใน commit แรกของ Sprint 1

### T0.3 — สร้าง branch
```bash
git checkout -b feature/pwa-sprint-1
```
(branch ใหม่ต่อ sprint, merge ผ่าน PR เข้า main)

---

## Sprint 1 — PWA Foundation (2-3 วัน)

**Goal:** ติดตั้งเป็นแอปได้ + offline shell + ไม่พังของเดิม

### T1.1 — Icons
- Source: ใช้ logo เดิมใน `frontend/public/` (หาไฟล์ logo จริงก่อน)
- สร้าง `frontend/public/icons/`: `icon-192.png`, `icon-512.png`, `maskable-512.png` (maskable = logo มี safe-zone padding ~20%)
- ถ้าไม่มี source logo คุณภาพพอ → แจ้ง Pornthep ขอไฟล์ ก่อน generate placeholder

### T1.2 — ติดตั้ง dependencies
```bash
cd frontend && npm install @serwist/next && npm install -D serwist
```

### T1.3 — `frontend/app/manifest.ts`
ตาม PWA_SPEC §3.2/§3.4: name "BP Monitor — ติดตามความดันโลหิต", short_name "BP Monitor", `start_url: '/'`, `scope: '/'`, `display: 'standalone'`, `lang: 'th'`, theme_color ตาม design system จริง (อ่านจาก `globals.css`/tailwind config ก่อน — อย่าเดาสี), icons 3 ตัวจาก T1.1

✅ Verify: `npm run dev` → GET `/manifest.webmanifest` ได้ JSON ถูกต้อง

### T1.4 — Offline fallback page
- `frontend/app/~offline/page.tsx` — หน้า static: icon + ข้อความ "ไม่มีการเชื่อมต่ออินเทอร์เน็ต" + ปุ่ม retry (`location.reload()`)
- เพิ่ม locale keys: `pwa.offline.title`, `pwa.offline.message`, `pwa.offline.retry` ทั้ง en/th

### T1.5 — Service worker (Serwist)
- `frontend/sw/index.ts`:
  - `defaultCache` ของ Serwist เป็น base
  - Custom runtime caching ตาม PWA_SPEC §4.1 — สำคัญ: `/api/v1/auth/*` NetworkOnly, mutations NetworkOnly, bp-records GET NetworkFirst, navigation fallback `/~offline`
  - **ห้ามใส่ `skipWaiting: true`** (D5)
  - ตรวจว่า `/telegram/*` routes ไม่โดน cache แบบที่ทำให้ Mini App พัง (ใส่ NetworkFirst หรือ NetworkOnly)
- แก้ `frontend/next.config.ts`: wrap config ด้วย `withSerwist({swSrc: 'sw/index.ts', swDest: 'public/sw.js', disable: process.env.NODE_ENV === 'development'})` — **คง rewrites + standalone logic เดิมไว้ครบ** (อ่านไฟล์เดิม แก้แบบ minimal diff)
- เพิ่ม `public/sw.js`, `public/swe-worker*.js` ใน `.gitignore` (generated)

✅ Verify: `npm run build` ผ่าน; `public/sw.js` ถูก generate

### T1.6 — SW registration + update prompt
- `frontend/lib/pwa/registerSW.ts`: register `/sw.js`; expose callback เมื่อพบ `registration.waiting`
- `frontend/components/pwa/PWAUpdatePrompt.tsx`: client component; เมื่อมี waiting SW → sonner toast (persistent): `pwa.update.available` + ปุ่ม `pwa.update.now` / `pwa.update.later`; "now" → `waiting.postMessage({type:'SKIP_WAITING'})` → listen `controllerchange` → `window.location.reload()`
- ใน `sw/index.ts` เพิ่ม message listener: `SKIP_WAITING` → `self.skipWaiting()`
- Mount ใน `frontend/app/layout.tsx` (client boundary) — แก้ layout แบบ minimal

### T1.7 — Install prompt
- `frontend/components/pwa/PWAInstallPrompt.tsx`:
  - Android/Chrome: จับ `beforeinstallprompt` → เก็บ event → แสดงปุ่ม/banner เมื่อ user login แล้ว (ไม่เด้งหน้าแรกทันที) → `prompt()`
  - iOS (UA check + `!window.matchMedia('(display-mode: standalone)').matches`): modal สอน Share → "เพิ่มลงหน้าจอโฮม"
  - Dismiss แล้วจำไว้ (localStorage key ธรรมดา — ไม่ใช่ข้อมูล sensitive) ไม่เด้งซ้ำใน 14 วัน
- Locale keys: `pwa.install.*`

### T1.8 — Sprint 1 verification
```bash
cd frontend && npm run build && npm run start
```
- [ ] Chrome DevTools → Application → Manifest: no errors, installable
- [ ] Lighthouse (mobile): installable pass, no SW errors
- [ ] DevTools offline mode → reload → เห็น app shell หรือ `~offline` page
- [ ] Login/logout ปกติ; `/telegram` routes ปกติ
- [ ] Deploy ไป Vercel preview → ทดสอบ install บนมือถือ Android จริง

---

## Sprint 2 — Web Push (2-3 วัน)

**Goal:** ส่ง notification จาก backend ถึงจอล็อกมือถือ ผ่าน adapter pattern

### T2.1 — VAPID keys
```bash
npx web-push generate-vapid-keys
```
- เพิ่มใน `.env.example` (placeholder) + `.env` จริง + Vercel env:
  `WEB_PUSH_VAPID_PUBLIC`, `WEB_PUSH_VAPID_PRIVATE`, `WEB_PUSH_VAPID_SUBJECT`, และ frontend `NEXT_PUBLIC_VAPID_PUBLIC_KEY`
- dev/prod คนละชุด

### T2.2 — Migration: push_subscriptions + notification_preferences
- `migrations/add_push_subscriptions.py` ตาม template เดิม (`add_timezone_column.py`):
  - `CREATE TABLE push_subscriptions` ตาม PWA_SPEC §6.2 (FK users ON DELETE CASCADE, unique endpoint, index user_id)
  - `ALTER TABLE users ADD COLUMN notification_preferences JSONB NOT NULL DEFAULT '{}'`
  - `rollback()`: drop table + drop column
  - register ใน `run_all.py`
- เพิ่ม `PushSubscription` model + `users.notification_preferences` ใน `app/models.py` (อ่าน model style เดิมก่อน — naming, relationship pattern)

✅ Verify: รัน migration กับ local/Neon dev branch สำเร็จ; rollback แล้ว re-apply สำเร็จ

### T2.3 — Backend: pywebpush + adapter package
```bash
pip install pywebpush && # เพิ่มใน requirements.txt ทั้ง root และ app/ ตามที่ repo ใช้จริง (เช็คว่าไฟล์ไหน canonical)
```
สร้างตาม PWA_SPEC §6.6:
- `app/adapters/__init__.py`, `app/adapters/notification/__init__.py`
- `base.py` — `NotificationPayload` (มี `body_generic`), `DeliveryResult`, `NotificationChannel` ABC
- `web_push.py` — `WebPushChannel`: query active subs ของ user → `pywebpush.webpush()` ต่อ sub → จับ `WebPushException`: status 404/410 → set `is_active=False`; success ≥1 = success; update `last_used_at`
- `telegram.py` — `TelegramChannel`: **wrap ฟังก์ชันส่งที่มีอยู่จริง** (ตามที่ survey ใน T0.1 จุด b) — import มาเรียก ไม่ copy logic
- `factory.py` — `build_notification_service(settings)` อ่าน env ว่า channel ไหน config ครบ

### T2.4 — Backend: NotificationService
`app/services/notification_service.py` ตาม PWA_SPEC §6.6 + D4 enforcement (§6.5):
- อ่าน `user.notification_preferences` (Pydantic validate, default ตาม §6.4)
- D4: ก่อนส่ง web_push ถ้า `show_details_in_push != true` → ใช้ `payload.body_generic` (ถ้า caller ไม่ให้ generic มา → ใช้ default "ถึงเวลาวัดความดันโลหิต" / ตาม locale ของ user ผ่าน pattern ใน `app/bot/locales.py`)
- First-success ตามลำดับ channels; log ทุก attempt (ใช้ logging pattern เดิมของ repo)

### T2.5 — Backend: push router
`app/routers/push.py` ตาม PWA_SPEC §6.3:
- `POST /api/v1/push/subscribe` (upsert by endpoint — endpoint เดิมของ user อื่น = reassign ไม่ได้, 409), `DELETE /api/v1/push/subscribe`, `POST /api/v1/push/test`
- Auth dependency แบบเดียวกับ router อื่น (ดู `bp_records.py`)
- Rate limit ตาม mechanism เดิมของ repo ถ้ามี (เช็ค T0.1) ถ้าไม่มี → จดเป็น TODO ไม่สร้าง infra ใหม่ใน sprint นี้
- Schemas ใน `app/schemas.py`
- Register router ใน `app/main.py`
- Preferences endpoints: เพิ่ม `GET/PATCH /api/v1/users/me/notification-preferences` ใน `app/routers/users.py` (Pydantic model validate shape §6.4, PATCH = shallow merge)

✅ Verify: `curl` subscribe ด้วย dummy subscription → 200 + row ใน DB; `POST /push/test` → pywebpush ถูกเรียก (จะ fail ที่ endpoint ปลอม — ดู error handling ทำงาน)

### T2.6 — Frontend: subscription flow
- `frontend/lib/pwa/pushSubscription.ts`:
  - `subscribeToPush()`: `Notification.requestPermission()` (ต้องเรียกจาก user gesture เท่านั้น) → `registration.pushManager.subscribe({userVisibleOnly:true, applicationServerKey: urlBase64ToUint8Array(NEXT_PUBLIC_VAPID_PUBLIC_KEY)})` → POST `/api/v1/push/subscribe`
  - `unsubscribeFromPush()`: `subscription.unsubscribe()` + DELETE backend
  - `getSubscriptionState()`
- `frontend/components/pwa/PushNotificationSettings.tsx`: ใส่ในหน้า settings ที่มีอยู่ (หา settings page จริงก่อน):
  - Toggle เปิด/ปิดแจ้งเตือน
  - Sub-toggle (แสดงเมื่อเปิดแล้ว): "แสดงรายละเอียดในแจ้งเตือน" → PATCH `show_details_in_push` (D4) + คำอธิบาย privacy สั้นๆ
  - ปุ่ม "ทดสอบการแจ้งเตือน" → `POST /push/test`
  - State: permission denied → แสดงวิธีเปิดใน browser settings
- Locale keys: `pwa.push.*`

### T2.7 — SW push handlers
ใน `frontend/sw/index.ts`:
```typescript
self.addEventListener('push', (e) => { const d = e.data?.json() ?? {};
  e.waitUntil(self.registration.showNotification(d.title ?? 'BP Monitor',
    { body: d.body, icon: '/icons/icon-192.png', tag: d.tag, data: { url: d.url ?? '/' } })); });
self.addEventListener('notificationclick', (e) => { e.notification.close();
  e.waitUntil(self.clients.openWindow(e.notification.data?.url ?? '/')); });
```

### T2.8 — เชื่อม reminder/alert เดิมเข้า NotificationService
- จาก T0.1(b): แก้ call sites ที่ส่งหา user ตรงๆ → เรียก `NotificationService.notify()` พร้อม payload ที่มีทั้ง detailed body และ `body_generic`
- **เฉพาะ user-facing notifications** — admin/ops messages ไม่ต้องย้าย
- Commit แยกต่อ call site group, regression test bot หลังแก้

### T2.9 — Sprint 2 verification
- [ ] มือถือ Android (PWA installed): เปิดแจ้งเตือน → กดทดสอบ → notification ขึ้นจอล็อก, body เป็น generic text
- [ ] เปิด `show_details_in_push` → test → เห็น detail
- [ ] Unsubscribe → test ผ่าน API → ไม่ได้รับ + subscription inactive
- [ ] Reminder เดิมทาง Telegram ยังทำงาน (regression)
- [ ] ลบ subscription row ใน DB แล้วส่ง → 410 path → `is_active=False` อัตโนมัติ

---

## Sprint 3 — Offline-First BP Entry (3-4 วัน)

**Goal:** บันทึก BP ตอนไม่มีสัญญาณ → sync อัตโนมัติ ไม่ duplicate

### T3.1 — Backend: idempotency (ทำก่อน frontend — เป็น blocker)
- Migration `migrations/add_client_record_id.py`: `ALTER TABLE <bp_records_table> ADD COLUMN client_record_id UUID NULL` + `CREATE UNIQUE INDEX ... WHERE client_record_id IS NOT NULL` (partial index) + rollback
  - **เช็คชื่อตารางจริงใน `app/models.py` ก่อน**
- แก้ create endpoint (`app/routers/bp_records.py`): รับ optional `client_record_id`; ถ้า unique violation หรือเจอ record เดิม → return record เดิม + 200 (ไม่ error)
- Unit test: ยิงซ้ำ 2 ครั้ง id เดียว → record เดียว, response เท่ากัน

### T3.2 — Frontend: offline queue
```bash
cd frontend && npm install idb
```
- `frontend/lib/pwa/offlineQueue.ts` ตาม PWA_SPEC §7.1: `enqueue`, `dequeueAll`, `markSyncing/markFailed`, `remove`, `count`, `clearAll`
- UUID: `crypto.randomUUID()`

### T3.3 — Submit hook
- หา BP entry form component จริง (T0.1) → extract submit logic เป็น hook `useBPRecordSubmit`:
  - พยายาม POST ปกติ (แนบ `client_record_id` ที่ gen ตอน submit)
  - `!navigator.onLine` หรือ network error (ไม่ใช่ 4xx validation) → `enqueue()` → toast `pwa.sync.savedOffline` → ถ้ามี SyncManager: `registration.sync.register('bp-sync')`
  - 4xx → error ปกติ (ห้าม queue ของที่ validate ไม่ผ่าน)

### T3.4 — Sync engine
- `frontend/lib/pwa/syncEngine.ts`: `syncQueue()` — อ่าน pending → POST ทีละรายการ → สำเร็จ/duplicate → remove; fail → retryCount++ (≥5 → failed)
- Triggers: `window 'online'` listener, app mount (layout effect), ปุ่ม manual ใน indicator
- Background Sync: ใน `sw/index.ts` listen `sync` event tag `bp-sync` → เนื่องจาก queue logic อยู่ฝั่ง client, ใช้วิธี SW post message ปลุก client หรือ implement sync ใน SW โดย import queue module — **เลือกแบบที่ test ได้ง่ายกว่าและจดเหตุผล** (acceptable ถ้า MVP ใช้ trigger ฝั่ง client ล้วน เพราะครอบ iOS อยู่แล้ว — Background Sync เป็น enhancement)

### T3.5 — `OfflineSyncIndicator.tsx`
- Badge/banner เมื่อ `count > 0`: "รอส่ง N รายการ" + ปุ่ม sync now + รายการ failed (retry/ลบ)
- Mount ใน layout (แสดงเฉพาะ authenticated)
- Locale keys: `pwa.sync.*`

### T3.6 — Logout cleanup
- หา logout logic จริง → เพิ่ม: `clearAll()` queue + `caches.keys()→delete` (PWA_SPEC §4.1 warning + §7.4)

### T3.7 — Sprint 3 verification
- [ ] Airplane mode → บันทึก 3 รายการ → ปิด airplane → ทั้ง 3 ขึ้น server, ไม่ duplicate
- [ ] ระหว่าง offline กด sync now → fail gracefully (ไม่ crash, retryCount ไม่พุ่ง)
- [ ] บันทึก offline → ปิดแอป → เปิดใหม่ (online) → sync ตอน mount
- [ ] Logout → IndexedDB + caches ว่าง
- [ ] ค่า validate ไม่ผ่าน (systolic 999) ขณะ offline → error ทันที ไม่เข้า queue

---

## Sprint 4 — Service Layer + Future-proofing (2-3 วัน)

**Goal:** bot และ web ใช้ business logic เดียวกัน + dev environment portable

### T4.1 — `BPRecordService` (behavior-preserving)
- จาก T0.1(c)(d): สร้าง `app/services/bp_service.py` — ย้าย create/validate/duplicate/abnormal-check logic จาก `routers/bp_records.py` + `bot/handlers.py` เข้า service **แบบ verbatim ที่สุด**
- ลำดับ commit: (1) สร้าง service + router เรียกใช้ → regression, (2) bot handler เรียกใช้ → regression, (3) ค่อย dedupe logic ภายใน service
- Abnormal alert ใน service เรียก `NotificationService` (จาก Sprint 2)

### T4.2 — OCR path เข้า service
- ย้าย Gemini call จาก `routers/ocr.py` (+ bot ถ้ามี) เข้า `bp_service.process_ocr()` — **คง ephemeral behavior เดิมเป๊ะ** (ไม่เก็บภาพ, ลบ temp file ใน finally)

### T4.3 — Docker dev environment
- Repo มี `Dockerfile` + `docker-compose.yml` root อยู่แล้ว → **อ่านก่อน** แล้ว update ให้ครอบ: postgres:16, redis:7, backend (FastAPI), frontend — ตาม PWA_SPEC แนวทาง `docker-compose` ใน spec หลัก
- เป้า: `docker compose up` → stack ทำงาน local ครบ (รวม run migrations)
- ห้ามกระทบ Vercel deploy (compose เป็น dev-only)

### T4.4 — Settings consolidation
- เช็คว่า backend ใช้ Pydantic Settings อยู่แล้วหรือ env กระจาย (T0.1) → ถ้ากระจาย: สร้าง `app/config/settings.py` (Pydantic BaseSettings) รวม env ใหม่ของ PWA (VAPID, channels) — ย้าย env เดิมเข้าเฉพาะที่ low-risk, ที่เหลือจดเป็น follow-up
- `.env.example` update ครบทุก key ใหม่

### T4.5 — Tests
- `tests/test_notification_service.py`: D4 enforcement (generic vs opt-in), channel fallback, 410 deactivation
- `tests/test_bp_service.py`: create + idempotency + abnormal trigger
- `tests/test_push_router.py`: subscribe upsert, auth required
- รัน suite เดิมทั้งหมดผ่าน

### T4.6 — Docs cascade (ปิดงาน)
- Update `PWA_SPEC.md` status → กรณี implementation ต่างจาก spec ให้แก้ spec ตามจริง + bump version
- Update `INDEX.md` status dashboard
- เพิ่มหมายเหตุใน `CAREGIVER_PWA_SPEC.md` header: SW tooling = Serwist (supersede §2.1), Web Push infra พร้อม reuse
- สรุป deviations ทั้งหมดให้ Pornthep review

---

## Emergency: SW Kill Switch

ถ้า service worker เสียหายใน production (cache วน, หน้าขาว):

1. แก้ `frontend/sw/index.ts` ชั่วคราวเป็น:
```javascript
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) await caches.delete(k);
    await self.registration.unregister();
    for (const c of await self.clients.matchAll({type:'window'})) c.navigate(c.url);
  })());
});
```
2. Deploy → SW เดิมจะ update ตัวเอง (browser เช็ค sw.js ทุก navigation, byte-diff → install ใหม่) → unregister ตัวเอง
3. แก้ root cause แล้วค่อย deploy SW จริงกลับ

---

## Decision Reference (จาก PWA_SPEC §2)

D1 ใช้ frontend เดิมทั้งหมด · D2 email/password + LINE-ready schema (design only) · D3 JSONB `notification_preferences` บน users · D4 push generic by default + opt-in detail (บังคับที่ NotificationService) · D5 SW update ถาม user ผ่าน PWAUpdatePrompt

**End of PWA_SPRINT_TASKS.md**
