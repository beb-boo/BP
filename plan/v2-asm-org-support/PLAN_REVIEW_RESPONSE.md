---
title: "Plan Review Response — v2 ASM Org Support"
aliases:
  - "Review Response"
  - "Decisions Log"
tags:
  - review
  - decisions
  - v2-asm-org
order: 0.5
status: draft
version: 1.0
updated: 2026-04-18
summary: "Consolidated response to plan reviews (Gemini + internal code verification). Single source of truth for architectural decisions."
---

# v2 ASM — Plan Review Response & Decisions Log

> **Purpose:** บันทึก review + architectural decisions หลัง draft v1 ของ plan set
>
> **Authority:** เวลา plan docs อื่น ขัดแย้งกัน ให้ยึดเอกสารนี้เป็น source of truth
>
> **อ่านก่อน:** [[MVP_PILOT_SCOPE]], [[ORG_FOUNDATION]]

---

## 1. Review Sources

| Source | Date | Scope |
|--------|------|-------|
| Gemini CLI | 2026-04-18 | Critical review of ORG_FOUNDATION + cross-doc consistency |
| Internal code verification | 2026-04-18 | Verified against actual `/Users/seal/Documents/GitHub/BP` codebase before committing decisions |

### 1.1 Verified facts (before making decisions)

Facts ที่ verify แล้วจาก codebase จริง (ไม่ใช่สมมติ):

| Fact | Status | Evidence |
|------|--------|----------|
| Alembic ไม่มี | ✅ confirmed | ไม่มีใน `requirements.txt`, ไม่มี `alembic.ini` |
| Migration pattern ปัจจุบัน | ✅ ad-hoc Python scripts | `migrations/add_*.py` + `run_all.py` |
| `AUTO_CREATE_TABLES=true` ใน prod | ⚠ assumed | `app/main.py` default true; ต้อง verify env จริง |
| Role hardcoding call sites | ✅ 20+ places | `routers/auth.py`, `users.py`, `doctor.py`, `utils/security.py`, `utils/staff_sync.py`, `bot/services.py`, `schemas.py` |
| `DoctorPatient` + `AccessRequest` ใช้งานจริง | ✅ 11 endpoints | `routers/doctor.py` |
| `License` table | ✅ dead code | ไม่มี writer/reader ใน codebase; likely empty in prod |
| `AdminAuditLog` ใช้งานจริง | ✅ มี writers | `routers/admin.py` + `AdminAuditLogResponse` schema |
| SQLite (dev) / PostgreSQL (prod) divergence | ✅ confirmed | `database.py` defaults SQLite; plan ใช้ PG-specific features |
| Staging env | ❌ ไม่มี | ไม่มีใน `BP_Deployment_Plan.md` |

---

## 2. Decisions Summary

| # | Issue | Decision | Affects |
|---|-------|----------|---------|
| **Architectural (Q1–Q3)** |||| 
| Q1 | Migration tooling | **A+** (ad-hoc + `schema_migrations` table + rollback discipline) | [[INFRASTRUCTURE_SETUP]] (new) |
| Q2 | Role refactor | **Additive dual-read** (keep `role`, add `primary_role`, helper `get_effective_role()`) | ORG_FOUNDATION §4.2.1, §5.2 |
| Q3 | DoctorPatient handling | **Keep + parallel** (doctor flow ใช้ DoctorPatient, ASM flow ใช้ CareAssignment) | ORG_FOUNDATION §6, new §4.3 |
| **Gemini items (G1–G7)** |||| 
| G1 | AdminAuditLog + new AuditLog | Dual-write transition (no data migration) | ORG_FOUNDATION §7, MIGRATION_STRATEGY |
| G2 | `paper_scan_file_id` inconsistency | Remove from `consent_records` | ORG_FOUNDATION §4.1.4 |
| G3 | License ↔ Organization FK | Add nullable `organization_id` to licenses; backfill from string | ORG_FOUNDATION new §4.3 |
| G4 | `measured_at` fat-finger | Warn >7d, block future, block >30d back | ORG_FOUNDATION §4.2.2 |
| G5 | Role migration mapping | `staff` → `superadmin` (not `rpsst_staff`); no auto-create org | ORG_FOUNDATION §5.2 |
| G6 | Timezone column type change | Staged (new col + backfill + swap), not big-bang | MIGRATION_STRATEGY |
| G7 | Migration sequence FK order | Revised (see §4.7) | ORG_FOUNDATION §5.1 |
| **Internal additional findings (I1–I3)** |||| 
| I1 | DoctorPatient/AccessRequest not in plan | Keep existing; document interaction with CareAssignment | ORG_FOUNDATION new §4.3 |
| I2 | Payment ↔ Organization | Defer to Phase 2 | Not in MVP |
| I3 | UserSession not tenant-scoped | Add `active_organization_id` JWT claim (stateless, no DB change) | ORG_FOUNDATION §6 |

---

## 3. Architectural Principles (derived from decisions)

1. **Additive > destructive** — เพิ่มคอลัมน์/ตารางใหม่, ไม่ลบของเก่าใน v2 (รอ stable ก่อน)
2. **Dual-read during transitions** — code อ่านจากทั้ง old + new, fallback ชัด
3. **Feature flag default OFF** — `ENABLE_ORG_MODE=false` ใน prod จนกว่า validate แล้ว
4. **Staging PG parity** — ทุก migration ผ่าน Neon staging branch ก่อน prod
5. **Idempotent migrations** — ทุก script re-run ได้โดยไม่เสียข้อมูล
6. **No big-bang column type changes** — column type migration = 4-5 steps (add → backfill → dual-read → swap → drop)

---

## 4. Detailed Decisions

### 4.1 (Q1) Migration tooling: **A+**

**Problem:** Plan §5.1 เขียน "10 Alembic migrations" แต่ repo ไม่มี Alembic

**Options considered:**
- A. Ad-hoc pattern เดิม (ไม่มี version tracking)
- A+. Ad-hoc + `schema_migrations` table + บังคับ rollback ทุก script
- B. Install Alembic + baseline existing schema

**Decision:** **A+**

**Rationale:**
- Solo developer → ไม่มี multi-branch migration merge problem ที่ Alembic แก้
- Existing pattern ใช้งาน prod ได้แล้ว 5 migrations — ไม่พัง
- v2 เพิ่ม ~10 migrations → total 15 ยังไม่ถึง threshold ที่ Alembic คุ้มค่ากว่า
- Upgrade path ชัด: ถ้า v3 ต้อง > 25 migrations ค่อยย้าย Alembic โดย `alembic stamp` ตาม `schema_migrations` version ล่าสุด

**Action items:**
- [ ] สร้าง `schema_migrations` table ก่อนเริ่ม v2 migration แรก (see INFRASTRUCTURE_SETUP)
- [ ] ปรับ `migrations/run_all.py` อ่าน `schema_migrations` → skip ที่ applied แล้ว
- [ ] ทุก migration ใหม่บังคับมี `migrate()` + `rollback()` (code review rule)

---

### 4.2 (Q2) Role refactor: **Additive dual-read**

**Problem:** 20+ call sites อ่าน `User.role` (String) ด้วย hardcoded strings

**Decision:** **Additive dual-read**

**Design:**
- เพิ่ม `primary_role` (Enum, nullable default null) — **ไม่ลบ** `role` (String)
- เพิ่ม `account_type` (Enum, default `self_managed`) ตาม plan
- Backfill ตอน migrate:
  ```python
  LEGACY_ROLE_MAP = {
      "patient": UserRole.patient_self,
      "doctor": UserRole.doctor,
      "staff": UserRole.superadmin,  # G5: staff = ระบบ admin ไม่ใช่ รพ.สต.
  }
  ```
- Helper `get_effective_role(user) -> UserRole`:
  ```python
  def get_effective_role(user: User) -> UserRole:
      if user.primary_role is not None:
          return user.primary_role
      return LEGACY_ROLE_MAP.get(user.role, UserRole.patient_self)
  ```
- ทุก write ใหม่ของ user เขียนทั้ง 2 columns
- Existing `require_verified_doctor`, `require_staff` **ไม่ต้องแก้** (ยังใช้ `user.role` ได้)
- New permission system (ORG_FOUNDATION §6) ใช้ `get_effective_role()`
- Eventually (v3+) deprecate `role` column

**Why not Full swap:** ไม่ backward compat, เสี่ยงสูงบน prod มี user จริง

**Why not "v2 only uses primary_role":** split-brain problem — user 1 คนมี 2 role source ทำ permission check conflict

**Action items:**
- [ ] ORG_FOUNDATION §4.2.1: เพิ่ม note ว่า `role` **ไม่ลบ**
- [ ] ORG_FOUNDATION §5.2: ใส่ `LEGACY_ROLE_MAP` สมบูรณ์
- [ ] ORG_FOUNDATION §9.1: เพิ่ม "Do not modify existing require_verified_doctor/require_staff"
- [ ] เพิ่ม `app/utils/permissions.py:get_effective_role()` ใน task list

---

### 4.3 (Q3) DoctorPatient vs CareAssignment: **Keep both parallel**

**Problem:** `DoctorPatient` + `AccessRequest` ใช้งาน 11 endpoints + bot cascade

**Decision:** **Keep existing tables ครบ + เพิ่ม `care_assignments` parallel**

**Namespacing (ไม่ให้ชนกัน):**

| Dimension | Doctor flow (เดิม) | ASM flow (ใหม่) |
|-----------|--------------------|------------------|
| Tables | `doctor_patients`, `access_requests` | `care_assignments`, `consent_records` |
| Actor role | `primary_role=doctor` (or legacy `role="doctor"`) | `primary_role=asm` |
| URL namespace | `/api/v1/doctor/*`, `/api/v1/patient/*` | `/api/v1/asm/*`, `/api/v1/rpsst/*` |
| Permission check | `require_verified_doctor` + DoctorPatient.is_active | `has_permission(VIEW_ASSIGNED_PATIENT)` + ConsentRecord scope check |
| Consent mechanism | `AccessRequest` approval chain | `ConsentRecord` (scope=asm_collect) |

**Patient viewable by both:** Valid case — patient ให้สิทธิ์ทั้งหมอและ อสม. แยกกัน
- `BloodPressureRecord` ของ patient 1 คน เห็นได้ 2 paths
- Audit log ต้อง distinguish path (metadata: `via_relationship: "doctor_patient"` vs `"care_assignment"`)

**Withdrawal semantics:**
- ถอนต่อหมอ: `DoctorPatient.is_active = False` (ไม่แตะ care_assignments)
- ถอนต่อ อสม.: `CareAssignment.is_active = False` + `ConsentRecord.status = withdrawn` (ไม่แตะ doctor_patients)

**Action items:**
- [ ] ORG_FOUNDATION เพิ่ม section §4.3 "Coexistence: DoctorPatient + CareAssignment"
- [ ] ORG_FOUNDATION §6 Permissions matrix: เพิ่ม column แยกระหว่าง "doctor (legacy)" และ "doctor (org member)"
- [ ] Audit log §7.1: เพิ่ม field `via_relationship` ใน metadata

---

### 4.4 (G1) AdminAuditLog → AuditLog: **Dual-write transition (no data migration)**

**Problem:** `admin_audit_logs` มี records จริงใน prod (used by admin router)

**Options considered:**
- (ก) Migrate data → AuditLog table ใหม่, drop old
- (ข) Dual-write: new events → AuditLog; old events ยังอ่านจาก admin_audit_logs
- (ค) Keep admin_audit_logs ถาวร, ไม่สร้าง AuditLog

**Decision:** **(ข) Dual-write transition**

**Rationale:**
- AdminAuditLog schema ไม่เข้ากับ JSONB `metadata` + BigInt PK (data shape ต่างกันมาก)
- Data migration = risky (มี writer ปัจจุบัน concurrent with migration)
- Dual-write = safer: new writes ไป AuditLog, old records อยู่ไม่แตะ, frontend merge 2 sources ตอน display

**Cutover:**
- Phase 1: สร้าง `audit_logs` table (new schema), เริ่มเขียน dual (ทั้ง `admin_audit_logs` + `audit_logs`)
- Phase 1.5: Admin frontend query both sources, union results, sort by created_at
- Phase 2 (ถัดไป): หยุดเขียน `admin_audit_logs`, ยัง query ได้
- Phase 3 (6+ เดือน): Retention expire (2 yr) → drop `admin_audit_logs` ถ้าว่างแล้ว

**Action items:**
- [ ] ORG_FOUNDATION §7.4: เพิ่ม query section "Legacy admin_audit_logs fallback"
- [ ] MIGRATION_STRATEGY: document cutover phases
- [ ] `AdminAuditLogResponse` schema คงไว้; add `AuditLogResponse` schema ใหม่

---

### 4.5 (G2) Paper consent scan: **Remove inconsistency**

**Problem:** ORG_FOUNDATION §4.1.4 มี `paper_scan_file_id` แต่ §4.1.7 `File.purpose` whitelist มีแค่ `ocr_batch_review_temp` → contradicts

**Decision:** **Remove `paper_scan_file_id`** จาก `consent_records`

**Rationale:**
- Data minimization principle (plan §2.8)
- กระดาษจริงเก็บที่ รพ.สต. ตู้ล็อก (non-digital evidence)
- Digital evidence = signature + GPS + timestamp + audit log (เพียงพอ PDPA)
- ไม่ complexity ของ file encryption + retention jobs สำหรับ consent scan

**Action items:**
- [ ] ORG_FOUNDATION §4.1.4: ลบ `paper_scan_file_id` + `paper_scan` relationship
- [ ] `CONSENT_FLOW_SPEC.md`: verify ไม่มีการอ้าง `paper_scan_file_id`

---

### 4.6 (G3) License ↔ Organization: **Add FK, backfill from string**

**Problem:** `License.organization_name` เป็น String, ไม่ link กับ Organization table

**Decision:** **Add nullable `organization_id` FK, backfill from string**

**Design:**
- เพิ่ม `License.organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)`
- **ไม่ลบ** `organization_name` (dual-column ชั่วคราว)
- Backfill migration: `SELECT COUNT(*) FROM licenses;` ก่อน — ถ้า 0 records (expected) = no-op
- ถ้ามี records: สร้าง Organization row จาก `organization_name` (type="clinic"/"hospital" จาก `License.type`) + link FK
- Permission check (future): `has_permission(user, perm) AND org_has_active_license(org, feature)`
- Phase 2: ลบ `organization_name` column

**Rationale:**
- License table **verified dead code** ใน codebase — no writers/readers → migration ปลอดภัย
- Additive approach ยังใช้ principle เดียวกันทั้ง plan
- FK nullable = optional link (ไม่บังคับทุก license ต้องมี org)

**Action items:**
- [ ] ORG_FOUNDATION เพิ่ม §4.4 "License ↔ Organization relationship"
- [ ] Verify จริง: `SELECT COUNT(*) FROM licenses;` บน prod Neon ก่อน migration

---

### 4.7 (G7) Migration sequence FK order: **Revised**

**Problem:** Original sequence (ORG_FOUNDATION §5.1) ไม่เคารพ FK dependencies — เช่น users เพิ่ม FK ไป organizations ก่อน organizations ถูกสร้าง

**Decision:** **Revised sequence**

```
01. create schema_migrations table (infrastructure)
02. create enums (no data change)
03. create organizations table
04. create organization_members table
05. extend users (add primary_role, account_type, managed_by_organization_id, external_id, deleted_at)
06. backfill users (role → primary_role via LEGACY_ROLE_MAP)
07. create care_assignments table (FK to users + organizations)
08. create consent_records table
09. create pairing_codes table
10. create files table (with purpose whitelist constraint)
11. extend bp_readings (add measured_at, measurement_context, etc.)
12. backfill bp_readings (measured_at = recorded_at)
13. create audit_logs table (new, BigInt + JSONB)
14. add organization_id FK to licenses
15. backfill licenses (if any records exist)
```

**Reasoning:**
- `users.managed_by_organization_id` FK → org ต้องมีก่อน
- `care_assignments` FK → both users + organizations ต้องมี
- `audit_logs` FK → both users + organizations ต้องมี → หลังทุก table FK ต้นทาง
- License extension = last (dead code, ไม่บล็อก flow อื่น)

**Action items:**
- [ ] ORG_FOUNDATION §5.1: update sequence to match
- [ ] MIGRATION_STRATEGY: document FK dependency graph + rollback order (reverse)

---

### 4.8 (G4) `measured_at` validation

**Decision:** เพิ่ม validation rules ใน service layer

| Condition | Action |
|-----------|--------|
| `measured_at > recorded_at` | **Block** (422 Unprocessable) — cannot measure in future |
| `(recorded_at - measured_at) > 7 days` | **Warn** ใน response, require `notes` field populated |
| `(recorded_at - measured_at) > 30 days` | **Block** — require separate "historical import" endpoint with extra consent |
| OCR batch: ` measured_at` from Gemini screen read | Use if present, confidence > 0.8; else fall back to `recorded_at` |

**Action items:**
- [ ] ORG_FOUNDATION §4.2.2: เพิ่ม validation subsection
- [ ] Add `app/utils/bp_validation.py:validate_measured_at()` ใน task list

---

### 4.9 (G6) Timezone migration: **Staged, 5-step**

**Problem:** Plan uses `DateTime(timezone=True)` but existing columns are `DateTime` (naive). Direct `ALTER COLUMN TYPE` on PostgreSQL locks table + rewrites.

**Decision:** **Staged migration per column**

For each column ที่ต้องเปลี่ยนเป็น timezone-aware:

1. Add `new_column_tz = Column(DateTime(timezone=True))` (nullable)
2. Backfill: `UPDATE t SET new_column_tz = old_column AT TIME ZONE 'Asia/Bangkok'`
3. Code reads `coalesce(new_column_tz, old_column)` (dual-read period)
4. Deploy (monitor for issues)
5. Next release: swap names, drop old

**Columns ที่ต้อง migrate (priority order):**
- `bp_readings.measurement_date` (high traffic — stage carefully)
- `audit_logs.created_at` (new table — tz-aware from start, no migration)
- `users.created_at`, `updated_at`, `last_login` (low traffic)

**Action items:**
- [ ] MIGRATION_STRATEGY: document per-column stage procedure
- [ ] Verify: row count per table before deciding urgency

---

### 4.10 (I3) UserSession active_organization_id: **JWT claim, no DB change**

**Problem:** ถ้า user เป็น member ของหลาย org, API ไม่รู้ว่า "ตอนนี้ active org ไหน"

**Decision:** **JWT claim `active_org_id`, ไม่เก็บใน DB**

**Design:**
- Login response: ถ้า user มี > 1 org membership → return list, frontend แสดง org selector
- Frontend เลือก org → request `/api/v1/auth/select-org { org_id }` → backend verify membership → issue ใหม่ JWT พร้อม `active_org_id` claim
- ทุก request ที่ต้อง org context → read `active_org_id` จาก JWT (no DB hit)
- Switching org = re-issue JWT (logout ง่าย ๆ)

**Why not DB column:**
- Stateless design ดีกว่า (scale ง่าย, ไม่ต้อง sync)
- Session state = UserSession (ของเดิม); org context = JWT claim (new)

**Action items:**
- [ ] ORG_FOUNDATION §6: add subsection "Multi-org JWT claims"
- [ ] `ADMIN_WEB_SPEC`, `ASM_PWA_SPEC`: add org selector UI spec

---

## 5. Cascaded updates required

เอกสารเหล่านี้ต้อง update ให้สอดคล้องกับ decisions ด้านบน:

| Doc | Changes needed | Priority |
|-----|----------------|----------|
| `ORG_FOUNDATION.md` | ทุกหัวข้อด้านบนที่อ้าง | **P0** (in-progress) |
| `INDEX.md` | เพิ่ม PLAN_REVIEW_RESPONSE + MIGRATION_STRATEGY + INFRASTRUCTURE_SETUP ในรายการ | P0 |
| `MIGRATION_STRATEGY.md` (new) | Staged migration procedures, FK order, rollback | **P0** (new doc) |
| `INFRASTRUCTURE_SETUP.md` (new) | `schema_migrations` table, feature flags, staging env, backup drill | **P0** (new doc) |
| `ADMIN_WEB_SPEC.md` | Remove references to `paper_scan_file_id`; add org selector UI; add dual-source audit view | P1 |
| `ASM_PWA_SPEC.md` | Add org selector UI; verify consent flow matches decision 4.5 | P1 |
| `CONSENT_FLOW_SPEC.md` | Verify no `paper_scan_file_id` references; clarify paper = physical only | P1 |
| `docs/privacy-policy.md` | Mention org data controller split (joint controller) | P2 |
| `docs/consent-and-implementation-guide.md` | Align with new consent scope enums | P2 |

---

## 6. Remaining unknowns to verify before code phase

ข้อที่ยังต้อง query prod DB จริงหรือ examine code เพิ่ม:

| Unknown | How to verify | Blocks |
|---------|---------------|--------|
| Row counts: users, bp_readings, admin_audit_logs, licenses | `SELECT COUNT(*) FROM <table>` บน Neon prod | Timezone migration cost, license backfill decision |
| `AUTO_CREATE_TABLES` ค่าจริงใน Vercel prod | Check Vercel env vars dashboard | Migration deployment procedure |
| Hardcoded role strings ใน frontend | `grep -r "role ===" frontend/app frontend/components` | Frontend adaptation scope |
| Hardcoded role strings ใน routers/ocr.py, payment.py, telegram_auth.py | Read each file | Ripple scope completion |
| `access_requests` table row count | Prod query | DoctorPatient migration decision (ถ้าจำเป็น Phase 2) |

**Next action:** `INFRASTRUCTURE_SETUP.md` จะมี queries เหล่านี้เป็น checklist ที่ Pornthep รันก่อน Phase 1 code

---

## 7. Open decisions (deferred to later)

| # | Topic | Why deferred |
|---|-------|--------------|
| O1 | Audit log partitioning (by month) | Pilot scale (~2 รพ.สต.) ไม่ถึง threshold; revisit at 10M+ rows |
| O2 | File encryption key rotation schedule | Phase 2 — MVP ใช้ single key ก่อน |
| O3 | Subdistrict reference table import | Pilot hardcode Sukhothai เท่านั้นก่อน |
| O4 | Payment ↔ Organization | Phase 2 — MVP ยังเป็น B2C only |
| O5 | Smart อสม. data export scope | Phase 2 — ต้องคุยกับทีม Smart อสม. ก่อน |

---

## 8. Approval trail

| Role | Name | Decision-approved date |
|------|------|----------------------|
| Project owner | Pornthep | 2026-04-18 (Q1, Q2, Q3 via chat) |
| Reviewer | Gemini CLI | 2026-04-18 (initial review) |
| Synthesis | Claude (via chat session) | 2026-04-18 |

---

**End of PLAN_REVIEW_RESPONSE.md**

เอกสารนี้เป็น **commit of decisions**. ถ้าจะเปลี่ยน decision ใน future ต้องแก้ที่นี่ก่อนแก้ plan อื่น เพื่อรักษา consistency
