# Backup & Migration Runbook

> คู่มือการใช้งาน backup feature ที่หน้า **Admin → System → Backups** (`/admin/system/backups`)
>
> Scope: production database ของ v1 ปัจจุบัน ไว้ใช้ก่อน v2 migration และกรณี emergency rollback
>
> Spec อ้างอิง: [BACKUP_AND_MIGRATION_SPEC.md](../../plan/v2-asm-org-support/BACKUP_AND_MIGRATION_SPEC.md)

---

## 1. ภาพรวมของระบบ

มี backup 2 แบบ ใช้คู่กัน:

| แบบ | เครื่องมือ | เก็บที่ไหน | ใช้ตอนไหน |
|-----|----------|-----------|---------|
| **A) Neon branch snapshot** | หน้า admin web (`/admin/system/backups`) | Neon cloud | rollback เร็ว ~1 นาที (swap `DATABASE_URL`) |
| **B) Local `pg_dump` (SQL)** | terminal บนเครื่อง | local disk (encrypted) | เก็บ offline นานกว่า 30 วัน / ถ้า Neon ล่มทั้ง project |

ใช้คู่กัน — **A ก่อนทุก migration**, **B เพิ่มถ้าต้องการ offline copy**

### Architecture

```
Admin Web  ─►  FastAPI  ─►  Neon Console API  ─►  Branch snapshot
                   │
                   └─►  admin_audit_logs (action='system_backup_*')
```

ทุก action (list/create/delete) ถูก log ลง `admin_audit_logs` ดูได้ที่ `GET /api/v1/admin/system/audit-log`

---

## 2. Prerequisites

### ต้องมีครั้งเดียว

1. **Neon API key + project ID** ตั้งใน Vercel env:
   ```
   NEON_API_KEY=<token จาก console.neon.tech/app/settings/api-keys>
   NEON_PROJECT_ID=<project id จาก Neon Console>
   ```
2. **Superadmin user** — ทำตาม [bootstrap-staff.md](bootstrap-staff.md)
3. **PostgreSQL client tools** (เฉพาะคนที่จะใช้ local `pg_dump`):
   - **Version ต้อง ≥ server** — Neon ปัจจุบันใช้ Postgres 17 ดังนั้น `pg_dump` ต้อง **17 ขึ้นไป**
   - macOS: `brew install libpq@17 && brew link --force libpq@17` (หรือเพิ่ม `/opt/homebrew/opt/libpq@17/bin` ใน PATH)
   - Linux (Ubuntu): ใช้ PGDG repo — `sudo apt install postgresql-client-17`
   - Windows: download จาก postgresql.org (เลือก version 17+)
   - ไม่อยากติดตั้ง: `docker run --rm -v "$PWD:/out" postgres:17 pg_dump ...`
   - ตรวจ version: `pg_dump --version`

### ตรวจก่อนใช้งาน

```bash
# Verify Neon API creds
curl -s -H "Authorization: Bearer $NEON_API_KEY" \
  "https://console.neon.tech/api/v2/projects/$NEON_PROJECT_ID/branches" \
  | head -c 200
```
ต้องเห็น JSON ขึ้นต้นด้วย `{"branches":[...`

---

## 3. การสร้าง Backup (Neon Branch)

### 3.1 ผ่าน Admin Web

1. เข้า `/dashboard` ในฐานะ staff/superadmin
2. กด **"System: Backups"** มุมขวาบน → จะไป `/admin/system/backups`
3. กรอก:
   - **ชื่อ backup** (ตัวพิมพ์เล็ก + ตัวเลข + ขีดกลาง, 3–64 ตัว) — แนะนำ `pre-v2-migration-<YYYY-MM-DD>`
   - **คำอธิบาย** (optional, เก็บใน audit log)
4. กด **"+ สร้าง Backup ตอนนี้"**
5. ยืนยันในกล่อง dialog โดยพิมพ์ `CREATE` → กด **"สร้าง Backup"**
6. รอ ~5–10 วินาที → branch ใหม่จะขึ้นในรายการ สถานะ `ready`

### 3.2 ผ่าน API (automation)

```bash
TOKEN=<JWT ของ superadmin>
curl -X POST https://your-api/api/v1/admin/system/backups \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "pre-v2-migration-2026-04-25", "description": "Before v2 ASM migration"}'
```

Response: `{"status": "success", "data": {"branch": {...}}}`

### 3.3 สิ่งที่ Neon ทำให้

- Branch ถูก "fork" จาก default branch ที่จุดเวลาปัจจุบัน (copy-on-write — ไม่ได้ copy จริงจนกว่าจะแก้)
- **Compute endpoint ไม่ถูกสร้าง** → ไม่กิน compute-hour (free idle)
- Storage คิดตามขนาดข้อมูลที่ diverge จริง (~$0.35/GB-month)

---

## 4. Local SQL Backup (pg_dump)

**Admin web ไม่ download ไฟล์ `.sql` ให้** (เพราะ Vercel serverless timeout 10–60s และไม่อยาก expose connection string ผ่าน browser) — ถ้าอยากเก็บเป็นไฟล์ต้องรัน `pg_dump` เองบน terminal

### 4.1 หา Connection String

**Option A — จาก Neon Console (manual):**
1. console.neon.tech → Project → Branches → เลือก branch
2. กด **Connect** → copy connection string (เริ่มด้วย `postgresql://`)

**Option B — จาก Neon API (scriptable):**
```bash
BRANCH_ID=br-xxx
curl -s -H "Authorization: Bearer $NEON_API_KEY" \
  "https://console.neon.tech/api/v2/projects/$NEON_PROJECT_ID/connection_uri?branch_id=$BRANCH_ID&database_name=neondb&role_name=neondb_owner" \
  | jq -r .uri
```

> ⚠ ก่อน dump จาก branch ที่ไม่มี compute endpoint, Neon อาจ auto-provision ให้ (จะกิน compute สั้นๆ ช่วง dump)

### 4.2 Dump

```bash
# Custom format (แนะนำ — compressed, restore ด้วย pg_restore เลือก table ได้)
pg_dump "postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require" \
  --no-owner --no-acl \
  -Fc \
  -f backup-$(date +%Y%m%d-%H%M).dump

# Plain SQL (human-readable แต่ไฟล์ใหญ่กว่า)
pg_dump "postgresql://..." \
  --no-owner --no-acl \
  -f backup-$(date +%Y%m%d-%H%M).sql
```

- `--no-owner --no-acl` → ไม่ include GRANT/OWNER statement (portable ไปเครื่องอื่น)
- `-Fc` → custom binary format
- File size: DB ปัจจุบัน (~42 MB) compressed ประมาณ 10–15 MB

### 4.3 เก็บไฟล์ให้ปลอดภัย

⚠ **ไฟล์ backup มี PII ทั้งหมด** (encrypted fields ถูก dump เป็น ciphertext — แต่ถ้าใครได้ไฟล์ + `ENCRYPTION_KEY` จะถอดได้)

**ควร:**
- Encrypt ก่อนเก็บ (เช่น `gpg --symmetric backup.dump`)
- เก็บใน external disk ที่ encrypted (FileVault / LUKS / BitLocker)
- เก็บ `ENCRYPTION_KEY` แยกที่ต่างสถานที่ (offline password manager, safe)

**ห้าม:**
- Commit ไฟล์ backup เข้า git (มี `.gitignore` pattern สำหรับ `*.dump`/`*.sql` แล้วแต่ double-check)
- Upload ไป Google Drive / Dropbox / iCloud โดยไม่ encrypt ก่อน
- เก็บใน `~/Downloads/` นานๆ

**ลบเมื่อไม่จำเป็น:**
```bash
# Linux — overwrite ก่อนลบ
shred -u backup.sql

# macOS — ใช้ rm ธรรมดาได้ (APFS จะ scrub free blocks)
rm backup.sql
```

---

## 5. การนำ Backup กลับมาใช้ (Restore)

เลือก path ตาม scenario:

| Scenario | Path |
|----------|------|
| v2 migration fail, prod DB เสียหาย | **5.1** — swap DATABASE_URL ไป backup branch |
| อยากทดสอบ backup branch ก่อน (dry-run) | **5.2** — create preview deployment ชี้ไป branch |
| ทั้ง project เสียหาย (rare) | **5.3** — restore จาก `.dump` ไป project ใหม่ |
| Restore เฉพาะบาง table | **5.4** — selective restore |

---

### 5.1 Swap DATABASE_URL ไป Backup Branch (fast rollback)

**ใช้ตอน:** prod migration พัง ต้อง rollback ให้เร็วที่สุด (~1–2 นาที downtime)

#### ขั้นตอน

1. **ไปที่ Neon Console → Branches → เลือก backup branch** (เช่น `pre-v2-migration-2026-04-25`)
2. ถ้ายังไม่มี compute endpoint ในนั้น:
   - กด **"Add compute endpoint"** → รอ ~10 วินาที
   - หรือ Neon จะสร้างให้อัตโนมัติเมื่อกด Connect
3. กด **Connect** → copy connection string
4. **Vercel Dashboard → Project (backend) → Settings → Environment Variables**
5. แก้ `DATABASE_URL` ให้ใช้ connection string ของ backup branch (จุดที่เปลี่ยนคือ host `ep-xxx`)
6. **Redeploy** — ไปที่ Deployments → เลือก deployment ล่าสุด → **"Redeploy"** (ไม่ต้อง build ใหม่)
7. ตรวจว่า prod ใช้งานได้:
   ```bash
   curl https://your-api/api/v1/health
   # Login ในเว็บ → ดูว่าข้อมูลอยู่ครบ
   ```
8. **บันทึก incident** — เขียน note ว่า swap ไปใช้ branch อะไร เมื่อไหร่ เพราะอะไร

#### ข้อควรรู้

- หลัง swap แล้วทุก write ใหม่จะเขียนลง backup branch (กลายเป็น prod ใหม่ไปแล้ว)
- Original default branch ยังอยู่ — ถ้าอยากกลับไปก็ swap URL กลับ (แต่ข้อมูลที่เขียนใน backup branch ช่วงนั้นจะไม่ sync กลับ — ต้อง merge เอง)
- แนะนำ: หลัง stable ซัก 1 สัปดาห์ → **promote backup branch เป็น default** ใน Neon Console เพื่อ simplify ต่อ

#### Rollback checklist

- [ ] Backup branch มีอยู่และสถานะ `ready`
- [ ] มี compute endpoint หรือ provision แล้ว
- [ ] Connection string copy ถูกต้อง (รวม `?sslmode=require`)
- [ ] Vercel env ถูกแก้ที่ **Production scope** (ไม่ใช่ Preview only)
- [ ] Redeploy trigger แล้ว
- [ ] Smoke test: login, list records, create record ได้

---

### 5.2 ทดสอบ Backup Branch ก่อน Swap (safe dry-run)

**ใช้ตอน:** อยาก verify ว่า backup branch ใช้ได้จริง ก่อนทำ 5.1

1. Neon Console → backup branch → Add compute endpoint → Connect → copy URL
2. Vercel → Project → Settings → Environment Variables
3. เพิ่ม `DATABASE_URL` เป็น **Preview scope** (แยกจาก Production) ชี้ไป backup branch
4. Trigger preview deployment (push branch หรือ redeploy)
5. เปิด preview URL → test feature สำคัญๆ
6. ถ้า OK → ค่อยทำ 5.1 กับ Production scope

---

### 5.3 Restore จาก `.dump` ไป Project ใหม่ (disaster recovery)

**ใช้ตอน:** Neon project หายทั้งก้อน / organization ถูกลบ / อยากย้ายไป DB อื่น

#### 5.3.1 สร้าง DB เปล่าใหม่

```bash
# Option 1 — Neon project ใหม่
#   Neon Console → New Project → Postgres 17 → copy connection string

# Option 2 — local PostgreSQL
createdb bp_restore
# Connection string: postgresql://localhost/bp_restore
```

#### 5.3.2 Restore

```bash
# จาก .dump (custom format)
pg_restore \
  --dbname="postgresql://..." \
  --no-owner --no-acl \
  --verbose \
  backup-20260418-1200.dump

# จาก .sql (plain text)
psql "postgresql://..." < backup-20260418-1200.sql
```

Flags สำคัญ:
- `--no-owner --no-acl` ต้องตรงกับตอน dump
- `--verbose` ดู progress และ error ได้
- ไม่ต้องใส่ `--clean` ถ้า restore ไป DB เปล่า

#### 5.3.3 Sanity check

```sql
-- จำนวน user และ BP record
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM blood_pressure_records;

-- Latest record
SELECT id, created_at FROM blood_pressure_records ORDER BY id DESC LIMIT 5;

-- Audit log
SELECT action, COUNT(*) FROM admin_audit_logs GROUP BY action;
```

#### 5.3.4 Swap Vercel DATABASE_URL → point to new DB → redeploy

#### 5.3.5 Re-apply ENCRYPTION_KEY ให้ตรงกับตอน dump

⚠ ถ้า `ENCRYPTION_KEY` บน Vercel ไม่ตรงกับตอนที่สร้าง record เดิม → encrypted field (email, phone, citizen_id, full_name, medical_license) จะถอดไม่ได้ทั้งหมด

---

### 5.4 Selective Restore (เฉพาะบาง Table)

**ใช้ตอน:** migration เสียหายเฉพาะ table เดียว ไม่อยาก rollback ทุกอย่าง

```bash
# List contents ของ .dump
pg_restore --list backup.dump > toc.txt

# เลือก table ที่ต้องการ restore (edit toc.txt ให้เหลือ table ที่ต้องการ)
# หรือใช้ flag -t:
pg_restore \
  --dbname="$DATABASE_URL" \
  --no-owner --no-acl \
  -t blood_pressure_records \
  -t users \
  backup.dump
```

⚠ ระวัง FK constraint — ถ้า restore แค่ `blood_pressure_records` โดย `users` row ที่อ้างอิงไม่มี จะ fail ตอน insert

---

## 6. การลบ Backup (Cleanup)

### 6.1 ผ่าน Admin Web

1. `/admin/system/backups` → หา branch ที่จะลบ
2. กด **ลบ** (ปุ่มจะ disable ถ้าเป็น default/protected branch)
3. พิมพ์ **ชื่อ branch เป๊ะๆ** (case-sensitive) เพื่อยืนยัน
4. กด **ลบ Branch**

### 6.2 Cost Control Rules

- เก็บไว้สูงสุด **3–4 branches** (rolling)
- ลบ branch อายุ > 30 วัน (เว้นแต่เป็น `pre-v2-*` ที่ยังใช้อ้างอิง)
- หลัง v2 stable 7–14 วัน → ลบ `pre-v2-migration-*`

### 6.3 Policy: เก็บ/ลบ เมื่อไหร่

| เหตุการณ์ | Action |
|----------|--------|
| ก่อน v2 migration | Create `pre-v2-migration-<date>` + local `.dump` |
| v2 migration สำเร็จ 7 วัน | เก็บต่อ (ยังอยู่ใน incident window) |
| v2 migration สำเร็จ 30 วัน | ลบ branch, เก็บ `.dump` ไว้ 90 วัน |
| v2 migration fail → swap | เก็บไว้ถาวร จนกว่าจะ fix + re-migrate สำเร็จ |

---

## 7. Security Checklist

ก่อนทุก operation:

- [ ] Login เป็น superadmin (`role=staff` หรือ `primary_role=superadmin`)
- [ ] Vercel env `NEON_API_KEY` **ไม่ expose** ไป frontend (check `NEXT_PUBLIC_*` prefixes)
- [ ] Audit log (`admin_audit_logs` table) backup action = ตัวเรา และ timestamp ตรง

หลังทุก operation (local dump):

- [ ] ไฟล์ `.dump` / `.sql` ถูก encrypt หรือเก็บใน encrypted volume
- [ ] ไม่มี connection string ค้างใน shell history (`history -d <n>` ลบบรรทัดที่มี password)
- [ ] ลบไฟล์เมื่อไม่ใช้ (`shred -u` / `rm`)

---

## 8. Troubleshooting

| ปัญหา | สาเหตุ + แก้ |
|-------|-----------|
| กด "สร้าง Backup" แล้ว 500 `Neon API not configured` | `NEON_API_KEY` หรือ `NEON_PROJECT_ID` ไม่ได้ตั้งใน Vercel env — set แล้ว redeploy |
| 502 `Neon API error: 401` | API key หมดอายุหรือถูก revoke — สร้างใหม่ที่ console.neon.tech/app/settings/api-keys |
| 422 `Branch name must be lowercase...` | ใช้ `^[a-z0-9][a-z0-9-]{2,63}$` เท่านั้น (ห้ามตัวใหญ่, underscore, เริ่มด้วย `-`) |
| 400 `Cannot delete the default branch` | Default branch ลบไม่ได้ ป้องกันโดยเจตนา |
| 400 `Cannot delete a protected branch` | ไปปลด `protected` flag ใน Neon Console ก่อน แล้วค่อยลบ |
| `pg_dump: connection to server failed` | ใน connection string ขาด `?sslmode=require` หรือ compute endpoint ยังไม่ ready |
| `pg_dump: error: server version: 17.x; pg_dump version: 14.x ... aborting because of server version mismatch` | pg_dump เก่ากว่า server — upgrade เป็น 17+: `brew install libpq@17 && brew link --force libpq@17` |
| `pg_restore: permission denied` | ลืม `--no-owner --no-acl` → ไป DB ที่ role ไม่ตรง |
| Restore สำเร็จแต่อ่าน email/phone เป็นขยะ | `ENCRYPTION_KEY` ไม่ตรงกับตอนสร้างข้อมูล — set key เดิม |
| หน้า backup โหลดช้า / timeout | Neon API ช้า — timeout ของ service = 10–30s; ถ้านานกว่านั้นให้ refresh |

---

## 9. Out of Scope (Phase 2+)

- Scheduled auto-backup (cron)
- Upload `.dump` ไป S3 / R2 อัตโนมัติ
- UI button สำหรับ restore (ตั้งใจไม่ทำ — เสี่ยง overwrite prod โดยพลาด)
- Backup ของ v2 schema (รอ v2 stable)
- Multi-region backup

---

## 10. อ้างอิง

- [BACKUP_AND_MIGRATION_SPEC.md](../../plan/v2-asm-org-support/BACKUP_AND_MIGRATION_SPEC.md) — spec เต็ม
- [MIGRATION_STRATEGY.md](../../plan/v2-asm-org-support/MIGRATION_STRATEGY.md) — cutover sequence สำหรับ v2
- [bootstrap-staff.md](bootstrap-staff.md) — วิธีสร้าง superadmin user
- [Neon Docs — Branching](https://neon.tech/docs/introduction/branching)
- [Neon Docs — pg_dump](https://neon.tech/docs/manage/backups)
