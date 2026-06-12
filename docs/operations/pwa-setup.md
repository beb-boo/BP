# PWA Setup & Operations Guide

คู่มือตั้งค่า PWA layer ของ frontend หลัก (Web Push, Daily Reminder, Offline-first BP entry)
สเปคเต็ม: `plan/v2-asm-org-support/PWA_SPEC.md` (v1.1) · Task log: `PWA_SPRINT_TASKS.md`

---

## 1. Environment Variables

### Backend (Vercel project: `bp` / local: `app/.env`)

| ตัวแปร | จำเป็น | คำอธิบาย |
|---|---|---|
| `WEB_PUSH_VAPID_PUBLIC` | ✅ (ถ้าจะใช้ web push) | VAPID public key |
| `WEB_PUSH_VAPID_PRIVATE` | ✅ | VAPID private key — **backend เท่านั้น** |
| `WEB_PUSH_VAPID_SUBJECT` | ✅ | `mailto:<admin-email>` |
| `CRON_SECRET` | ✅ (ถ้าจะใช้ reminder) | คุ้มครอง `/api/v1/cron/*` — Vercel Cron ส่ง `Authorization: Bearer <ค่านี้>` ให้อัตโนมัติเมื่อ env นี้ถูกตั้ง |

ถ้า VAPID ไม่ครบ → `WebPushChannel` ปิดตัวเอง (log แจ้ง) ระบบที่เหลือทำงานปกติ
ถ้า `CRON_SECRET` ไม่ตั้ง → endpoint cron ตอบ 503 (ปิดโดยพฤตินัย)

### Frontend (Vercel project: `bp-frontend` / local: `frontend/.env.local`)

| ตัวแปร | จำเป็น | คำอธิบาย |
|---|---|---|
| `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | ✅ | ค่าเดียวกับ `WEB_PUSH_VAPID_PUBLIC` — **ถูก bake ตอน build ต้อง redeploy หลังตั้ง** |

### สร้าง VAPID keys

```bash
npx web-push generate-vapid-keys
```

กติกา:
- **คนละคู่ต่อ environment** (dev / prod แยกกัน)
- **ห้าม rotate โดยไม่มีแผน** — เปลี่ยน key = push subscription เดิมตายทั้งหมด ผู้ใช้ต้องกดเปิดแจ้งเตือนใหม่ทุกคน

### สร้าง CRON_SECRET

```bash
openssl rand -hex 32
```

---

## 2. Database Migrations

มี migration ใหม่ 2 ตัว (idempotent, รันซ้ำได้):

| Migration | สิ่งที่ทำ |
|---|---|
| `add_push_subscriptions` | ตาราง `push_subscriptions` + คอลัมน์ `users.notification_preferences` (JSONB) |
| `add_client_record_id` | คอลัมน์ `blood_pressure_records.client_record_id` + partial unique index (idempotency ของ offline sync) |

รันทั้งชุด (ครอบทั้งสองตัว):

```bash
python3 -m migrations.run_all
```

**บน Neon/prod: รัน migration ก่อนเสมอ** อย่าพึ่ง `AUTO_CREATE_TABLES` กับ DB ที่มีข้อมูลแล้ว
Rollback รายตัว: `python3 -m migrations.add_push_subscriptions --rollback` (เช่นเดียวกับ `add_client_record_id`)

---

## 3. Daily Reminder Cron

- Endpoint: `GET /api/v1/cron/reminders` + header `Authorization: Bearer <CRON_SECRET>`
- ต้องยิง**ทุก 15 นาที** — แต่ละรอบครอบ window 15 นาทีเดียว (เทียบ `reminder_times` ของ user ใน timezone ของ user เอง) ยิงครั้งเดียวต่อ window = ไม่ส่งซ้ำ
- ผู้ใช้ตั้งเวลาได้เองที่ Settings → การแจ้งเตือน (สูงสุด 6 เวลา) — default `07:00, 19:00`, เปิดอยู่โดย default แต่จะส่งได้เฉพาะ user ที่มีช่องทางรับ (push subscription หรือ Telegram ที่ pair แล้ว)

### Vercel Pro ขึ้นไป

`vercel.json` มี cron ตั้งไว้แล้ว (`*/15 * * * *`) — แค่ตั้ง `CRON_SECRET` แล้ว redeploy

### Vercel Hobby (cron ได้แค่วันละครั้ง)

ใช้ external scheduler ฟรี เช่น [cron-job.org](https://cron-job.org):
- URL: `https://<backend-domain>/api/v1/cron/reminders`
- Method: GET, ทุก 15 นาที
- Header: `Authorization: Bearer <CRON_SECRET>`

ทดสอบด้วยมือ:

```bash
curl -H "Authorization: Bearer $CRON_SECRET" https://<backend>/api/v1/cron/reminders
# → {"status":"success","data":{"due":N,"sent":N,"failed":N},...}
```

---

## 4. Service Worker & Cache

- SW serve ที่ **`/serwist/sw.js`** (route handler `frontend/app/serwist/[path]/route.ts` — ไม่ใช่ไฟล์ใน `public/`) ผ่าน `@serwist/turbopack`
- **Dev mode ไม่ register SW** — ทดสอบต้อง `npm run build && npm run start`
- Update policy (D5): SW ใหม่จะไม่ activate เองจนกว่า user กด "อัปเดตเลย" ใน toast
- ห้าม cache: `/api/v1/auth`, `/api/v1/ocr`, `/telegram/*`, และ `/api/v1` อื่นที่ไม่ได้ระบุ (กัน PII) / bp-records GET = NetworkFirst / stats = SWR
- Logout ล้าง IndexedDB + CacheStorage ทั้งหมด (PHI hygiene)

### Emergency Kill Switch

ถ้า SW เสียใน production (cache วน/หน้าขาว) — ดู snippet ใน `plan/v2-asm-org-support/PWA_SPRINT_TASKS.md` §Emergency: แทนที่ `frontend/sw/index.ts` ด้วย SW ที่ unregister ตัวเอง + ล้าง caches แล้ว deploy

---

## 5. Checklist การ Deploy ครั้งแรก

1. [ ] Generate VAPID คู่ prod + `CRON_SECRET`
2. [ ] ตั้ง env backend (`bp`): `WEB_PUSH_VAPID_PUBLIC/PRIVATE/SUBJECT`, `CRON_SECRET`
3. [ ] ตั้ง env frontend (`bp-frontend`): `NEXT_PUBLIC_VAPID_PUBLIC_KEY`
4. [ ] รัน `python3 -m migrations.run_all` กับ production DB
5. [ ] Deploy backend แล้ว frontend (frontend ต้อง build ใหม่เพื่อ bake key)
6. [ ] ตั้ง scheduler สำหรับ reminder (Vercel Cron หรือ external — ดู §3)

## 6. Checklist ทดสอบบนอุปกรณ์จริง

**Android (Chrome):**
- [ ] เปิดเว็บ → login → เห็น banner ติดตั้ง → Add to Home Screen → เปิดแบบ standalone
- [ ] Settings → การแจ้งเตือน → เปิด → กด "ทดสอบการแจ้งเตือน" → push ขึ้นจอล็อก **ข้อความ generic**
- [ ] เปิด "แสดงรายละเอียดในแจ้งเตือน" → ทดสอบอีกครั้ง → เห็นรายละเอียด (D4)
- [ ] Airplane mode → บันทึก BP 2-3 รายการ → เห็น "บันทึกไว้ในเครื่องแล้ว" + banner รอส่ง → ปิด airplane → รายการขึ้น server ไม่ซ้ำ
- [ ] รอ reminder ตามเวลาที่ตั้ง (±15 นาที)
- [ ] Logout → เปิด DevTools (remote) เช็ค IndexedDB/Cache ว่าง

**iOS (Safari):**
- [ ] Banner แนะนำติดตั้ง → ทำตาม (Share → Add to Home Screen)
- [ ] เปิดจาก home screen → **ต้อง login ใหม่ 1 ครั้ง** (cookie แยกจาก Safari — expected)
- [ ] Web Push ต้องเปิดจากแอปที่ติดตั้งแล้วเท่านั้น (iOS 16.4+)
- [ ] Offline: บันทึก → ปิดแอป → เปิดใหม่ตอน online → sync อัตโนมัติตอนเปิด (iOS ไม่มี Background Sync)

**Regression เดิม:**
- [ ] Telegram bot บันทึก/OCR/stats ปกติ
- [ ] Telegram Mini App (`/telegram/bp`) ปกติ (SW ไม่แตะ route นี้)

---

## 7. Troubleshooting

| อาการ | สาเหตุที่พบบ่อย |
|---|---|
| ปุ่มเปิดแจ้งเตือนขึ้น "ยังใช้ไม่ได้" | อยู่ dev mode (ไม่มี SW) หรือ SW ยังไม่ activate — ใช้ production build |
| `POST /push/test` → delivered: false | Subscription ตาย (ระบบ deactivate ให้เองเมื่อเจอ 404/410) — ปิดแล้วเปิดแจ้งเตือนใหม่ |
| Cron ตอบ 503 | `CRON_SECRET` ไม่ได้ตั้งฝั่ง backend |
| Cron ตอบ 401 | Header ไม่ตรง — ต้อง `Bearer <secret>` เป๊ะ |
| Push ไม่มาเลยทั้งที่ subscribe แล้ว | VAPID frontend/backend คนละคู่ (เช็คว่า public key ตรงกัน) หรือ rotate key ไปแล้ว |
| ติดตั้งแอปไม่ขึ้น (Android) | เคยกด dismiss ใน 14 วัน (`localStorage: pwa-install-dismissed-at`) หรือเปิดผ่าน WebView ที่ไม่ใช่ Chrome |
