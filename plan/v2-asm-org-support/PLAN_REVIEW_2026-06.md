---
title: "Plan Audit Round 2 — v2 ASM Org Support"
aliases:
  - "Audit Round 2"
  - "June 2026 Review"
  - "Plan Audit 2026-06"
tags:
  - review
  - audit
  - v2-asm-org
order: 0.6
status: draft
version: 1.1
updated: 2026-06-21
summary: "Second-round audit. Tier 1 (C1/M1/C3/C2) + Tier 2 (S2/S3) + new C4 + P2 (token_version) resolved across ORG_FOUNDATION + PLAN_REVIEW_RESPONSE (2026-06-20..21). Still open: S1, P1, H1-H3."
---

# v2 ASM — Plan Audit Round 2 (2026-06-20)

> [!INFO] **ความสัมพันธ์กับ [[PLAN_REVIEW_RESPONSE]]**
> เอกสารนั้น = decisions log (review รอบ 1: Gemini + internal, เม.ย. 2026)
> เอกสารนี้ = **findings รอบ 2** (Claude, 20 มิ.ย. 2026)
> **Update 2026-06-21:** Tier 1 (C1/C2/C3/M1) + Tier 2 (S2/S3) + new C4 + P2 ถูก patch แล้วใน [[ORG_FOUNDATION]] (v1.5) และบันทึก decisions 4.11–4.15 ใน [[PLAN_REVIEW_RESPONSE]] (v1.3). ที่ยัง open: S1, P1, H1–H3

---

## 0. Scope & status

**Reviewer:** Claude (chat session) · **Date:** 2026-06-20

**อ่านแล้ว (audit ครอบ):** [[INDEX]], [[PLAN_REVIEW_RESPONSE]], [[MVP_PILOT_SCOPE]], [[MIGRATION_STRATEGY]], [[ORG_FOUNDATION]]

**ยังไม่อ่าน (audit ไม่ครอบ — อาจมีของที่แก้ประเด็น Tier 3 ไว้แล้ว):** [[PDPA_COMPLIANCE]], [[CONSENT_FLOW_SPEC]], [[ADMIN_WEB_SPEC]], [[CAREGIVER_PWA_SPEC]], [[PWA_SPEC]], [[PWA_SPRINT_TASKS]], [[SCALABILITY_PLAN]], [[DATA_RETENTION_POLICY]], [[BREACH_RESPONSE_RUNBOOK]], [[CONSENT_FORMS]], [[ORG_TERMS_OF_SERVICE]], [[INFRASTRUCTURE_SETUP]], [[GENERALIZE_ORG_PLAN]], [[BACKUP_AND_MIGRATION_SPEC]], [[LEGACY_DOCS_MIGRATION]]

**ภาพรวม:** แผนชุดนี้สุก/มีวินัยสูง (additive-first, dual-read, FK ordering, feature flag, decisions ที่ verify codebase จริง) ของที่เจอส่วนใหญ่เป็นจุดเฉพาะ ไม่ใช่ปัญหาเชิงโครงสร้าง

**Status legend:** Open (รอตัดสิน) · Accepted · Rejected · Fixed

---

## 1. Findings tracker

| ID | Tier | Doc / Section | Issue (สั้น) | Status |
|----|------|---------------|--------------|--------|
| C1 | 1 blocker | ORG_FOUNDATION §4.1.5 | `metadata` เป็นชื่อ attribute ต้องห้ามใน SQLAlchemy → crash ตอน import | Resolved 2026-06-20 |
| C2 | 1 blocker | ORG_FOUNDATION §4.2.2 / §5.1 | `measured_at` NOT NULL + ลำดับ migration ขัดกัน → ALTER fail / divergence | Resolved 2026-06-21 (v2_11b SET NOT NULL; ADD nullable first; write-path dual-write) |
| C3 | 1 blocker | ORG_FOUNDATION §4.2.2 vs §5.2 | ชื่อคอลัมน์เวลาเดิม `recorded_at` vs `measurement_date` ไม่ตรง | Resolved 2026-06-20 (grep confirmed) |
| C4 | 1 blocker | ORG_FOUNDATION §4.2.2 vs PLAN_REVIEW_RESPONSE §4.9 | `measured_at` (tz-aware ใหม่) ซ้ำซ้อนกับแผน tz-migrate `measurement_date` (G6) | Resolved 2026-06-21 (measured_at canonical; measurement_date ถอดจาก G6 list) |
| M1 | 1 blocker | ORG_FOUNDATION §4.1.7 | เทียบ datetime naive (`utcnow()`) กับ tz-aware column → TypeError | Resolved 2026-06-20 |
| S1 | 2 consistency | INDEX / PLAN_REVIEW_RESPONSE / GENERALIZE / PWA_SPEC | "source of truth" แตกเป็น 4 ที่ | Open |
| S2 | 2 consistency | ORG_FOUNDATION §6.1 vs §8.4.3 | gate การให้ caregiver สร้าง patient ขัดกัน | Resolved 2026-06-21 (single gate: active OrganizationMember + consent ณ จุดสร้าง; no pre-approval) |
| S3 | 2 consistency | ORG_FOUNDATION §4.2.2 | `ix_bp_dedupe` ไม่ตรงเจตนา (minute granularity) | Resolved 2026-06-21 (minute-dedupe ใน service layer; index = non-unique helper) |
| P1 | 3 PDPA | ORG_FOUNDATION §8.4.1 | เก็บข้อมูลสุขภาพ (โรคประจำตัว) ก่อน consent — ฐานทางกฎหมาย? | Open (เช็ก PDPA_COMPLIANCE) |
| P2 | 3 PDPA | MVP_PILOT_SCOPE §4.1.2 / §4.1.4 | caregiver auth single-factor โดยพฤตินัย + force-logout บน JWT stateless | Resolved 2026-06-21 (force-logout: เพิ่ม `User.token_version` — decision 4.15 / ORG_FOUNDATION §6.6). คงเหลือ single-factor auth = accept สำหรับ pilot (trusted อสม.) |
| H1 | 4 hygiene | INDEX.md | metadata เก่า (version, sizes, total, สถานะ) | Open |
| H2 | 4 hygiene | plan dir | `.DS_Store` หลุดเข้า repo | Open |
| H3 | 4 process | ทั้งชุด | ปริมาณเอกสาร upfront หนักเทียบกับ pilot scale + สัญญาณ drift | Open (ตัดสินใจเชิง process) |

---

## 2. Tier 1 — แก้ก่อนเขียน code (จะ crash หรือ migration พังจริง)

### C1 — `metadata` เป็นชื่อ attribute ต้องห้ามใน SQLAlchemy declarative
**Where:** `AuditLog.metadata = Column(JSONB)` (§4.1.5)
**Why it bites:** declarative จอง `Base.metadata` ไว้ → throw `InvalidRequestError: Attribute name 'metadata' is reserved` ตั้งแต่ import model `AuditLog` คือ table ที่ทุก action เขียนลง = พังแน่นอนเมื่อรัน หมายเหตุ: `Organization` ใช้ `extra_metadata` (ถูกแล้ว) แต่ `AuditLog` ยังพลาด
**Fix:** เปลี่ยน attribute เป็น `audit_metadata = Column("metadata", JSONB)` (ชื่อคอลัมน์ DB เป็น `metadata` ได้ ห้ามแค่ชื่อ Python attribute) แล้วแก้ caller เช่น `audit_service.log_audit(... metadata=...)` → `audit_metadata=...`
**Patch 2026-06-20:** ORG_FOUNDATION เปลี่ยน model example เป็น `audit_metadata = Column("metadata", JSONB)`, note ระบุ DB column/ORM attribute ชัดเจน, และ dual-write helper ใช้ `AuditLog(audit_metadata=metadata)`.

### C2 — `measured_at` NOT NULL + ลำดับ migration ขัดกัน
**Where:** model `measured_at = Column(..., nullable=False)` (§4.2.2) vs sequence v2_10 ADD → v2_11 backfill (§5.1)
**Why it bites:** เพิ่มคอลัมน์ NOT NULL ที่ไม่มี default ลงตารางที่มีข้อมูล → Postgres reject ทันที; ถ้าเพิ่มแบบ nullable เพื่อให้ backfill ได้ ก็ไม่มี step ไหนใส่ NOT NULL กลับ → DB จริง nullable แต่ model บอก NOT NULL = divergence เงียบ (และ `AUTO_CREATE_TABLES` บน DB ใหม่จะได้ NOT NULL ไม่ตรง prod)
**Fix:** เพิ่ม step ชัด — v2_10 add **nullable** → v2_11 backfill → v2_11b `ALTER COLUMN measured_at SET NOT NULL` (เพิ่มเข้า sequence §5.1)
**Note:** `measurement_context` / `source_type` มี default → ADD ได้ปกติ; ปัญหาเฉพาะ `measured_at` ที่ NOT NULL + ไม่มี default

### C3 — ชื่อคอลัมน์เวลาเดิมไม่ตรงกัน: `recorded_at` vs `measurement_date`
**Where:** §4.2.2 เขียน "recorded_at: มีอยู่แล้ว" + validation rules เทียบ `recorded_at`; แต่ backfill v2_11 ทำ `SET measured_at = measurement_date`
**Why it bites:** ถ้า `recorded_at` ไม่มีจริง `validate_measured_at()` พังเพราะอ้างคอลัมน์ที่ไม่มี
**Action ก่อนแก้:** `grep` ชื่อคอลัมน์จริงใน `/Users/seal/Documents/GitHub/BP` (model `BloodPressureRecord`) แล้วทำเอกสารให้ตรงกันทั้ง validation + backfill — **ห้ามเดา ต้องดูของจริงก่อน**
**Patch 2026-06-20:** grep codebase แล้วพบ current model/schema/service/frontend ใช้ `measurement_date`; `BloodPressureRecord` มี `created_at` สำหรับเวลาบันทึกเข้าระบบ และไม่มี `recorded_at`. ORG_FOUNDATION จึงเปลี่ยน migration rule เป็น `measured_at = measurement_date` และ validation ใช้ `recorded_reference = now/created_at` แทนชื่อคอลัมน์ที่ไม่มีจริง.

### M1 — เทียบ datetime naive กับ tz-aware ในโค้ดตัวอย่าง
**Where:** `cleanup_expired_files` (§4.1.7) — `now = datetime.utcnow()` (naive) แล้ว `(now - file.created_at).days` โดย `created_at` เป็น `DateTime(timezone=True)`
**Why it bites:** `TypeError: can't subtract offset-naive and offset-aware datetimes` ตอนรันจริง
**Fix:** ตั้งกฎเดียวทั้งโปรเจกต์ — ใช้ aware now เสมอ (`datetime.now(timezone.utc)` หรือ `datetime.now(BANGKOK_TZ)`) ทั้ง jobs และ validation (เข้มเรื่อง tz เหมือนที่ทำในโปรเจกต์อื่น)
**Patch 2026-06-20:** ORG_FOUNDATION cleanup snippet เปลี่ยนเป็น `from datetime import datetime, timezone` + `datetime.now(timezone.utc)`.

---

## 3. Tier 2 — ความสอดคล้องเชิง spec (ไม่ crash แต่ implement สับสน/ตัดสินซ้ำ)

### S1 — "source of truth" แตกเป็นหลายที่
**Where:** [[PLAN_REVIEW_RESPONSE]] ประกาศตัวเป็น authority แต่ decisions จริงกระจาย 4 ที่ — PLAN_REVIEW_RESPONSE (Q/G/I), [[GENERALIZE_ORG_PLAN]] (§3 self-measure, §4 hybrid onboarding, §5 role label — ฝังใน ORG_FOUNDATION §8.3/§8.4/§6.5), [[PWA_SPEC]] (D1–D5), และ INDEX "Key Decisions"
**Why it matters:** เวลาขัดกันจริงจะงงว่าดูที่ไหน เพราะ authority doc ไม่บรรจุ decisions ของ GENERALIZE/PWA
**Fix:** ทำ PLAN_REVIEW_RESPONSE เป็น index-of-decisions ที่ลิงก์ไปแต่ละที่ + อัปเดตประโยค authority ให้ครอบ GENERALIZE + PWA

### S2 — สิทธิ์ caregiver สร้าง patient ขัดกันสองจุด
**Where:** §6.1 footnote (สร้างได้แต่ต้อง whitelist **หรือ** admin approve หลัง create — ยังไม่เลือก) vs §8.4.3 Path C (caregiver `create-hybrid` ตรง ๆ ไม่มี gate)
**Why it matters:** เป็น action ที่ไวต่อ PDPA (สร้าง record ที่มี PII คนอื่น)
**Fix:** lock gate เดียวให้ชัด ใช้กับทุก path การสร้าง patient โดย caregiver เหมือนกัน

### S3 — dedupe index ไม่ตรงเจตนา
**Where:** `ix_bp_dedupe` บน `(user_id, measured_at, systolic, diastolic)` คอมเมนต์ว่า "ซ้ำระดับ minute" แต่ index ใช้ timestamp เต็ม
**Why it matters:** 10:00:01 กับ 10:00:45 เป็นคนละ key → ดักซ้ำระดับนาทีไม่ได้จริง (data quality)
**Fix:** logic ปัดนาทีใน app หรือ functional index `date_trunc('minute', measured_at)`

---

## 4. Tier 3 — PDPA / legal (อาจถูกแก้แล้วใน doc ที่ยังไม่อ่าน)

> [!WARNING] ยังไม่อ่าน [[PDPA_COMPLIANCE]] + [[CONSENT_FLOW_SPEC]] — ถ้าครอบประเด็นพวกนี้แล้ว ข้ามได้

### P1 — จังหวะเก็บข้อมูลอ่อนไหว "ก่อน" consent
**Where:** Path A (§8.4.1) admin สร้าง proxy patient พร้อม `โรคประจำตัว` (sensitive ตาม ม.26) ตั้งแต่ตอนสร้าง ทั้งที่ consent ยังไม่เกิด
**Why it matters:** การ gate "readings ต้องมี consent" มีแล้ว แต่ตัวการสร้าง record ที่มีข้อมูลสุขภาพ **คือ collection event เอง** ที่ต้องมีฐานทางกฎหมาย ณ จุดนั้น
**Question ให้ที่ปรึกษา PDPA:** งาน อสม./รพ.สต. ใช้ฐาน "ภารกิจสาธารณสุข" (ม.24) ได้ไหม หรือยืนยันใช้ consent (ม.26) แล้วต้องเลื่อนกรอกข้อมูลสุขภาพไปหลัง consent — กระทบ flow สร้าง patient โดยตรง (โยง dependency legal review)

### P2 — auth ของ caregiver เป็น single-factor โดยพฤตินัย
**Where:** §4.1.2 login = เบอร์ + OTP ผ่าน Telegram แต่ fallback `/otp` ให้ดึงรหัสปัจจุบันได้ตลอด → ปัจจัยจริงเหลือ "ครองบัญชี Telegram นี้" (ไม่มี password caregiver)
**Why it matters:** สำหรับ pilot ที่ caregiver trusted อาจรับได้ แต่ควรเป็น risk ที่ตัดสินใจรับอย่างรู้ตัว; "force logout all sessions" (§4.1.4) บังคับยากกับ JWT stateless — ต้องมี session check ฝั่ง server (ดูเหมือนมี UserSession อยู่) ถึง logout ได้จริง

---

## 5. Tier 4 — hygiene / process

### H1 — metadata ใน INDEX เก่า
frontmatter v1.5 แต่ dashboard บอก INDEX v1.2; sizes เพี้ยน (ORG_FOUNDATION ลง ~60KB จริง 78KB, PLAN_REVIEW_RESPONSE ~15KB จริง 22KB); "Total 20 files ~547KB" จริง ~627KB; PLAN_REVIEW_RESPONSE row บอก v1.0 ไฟล์จริง v1.1 → index เป็นเครื่องมือ navigate ถ้าตัวเลขเชื่อไม่ได้จะลดความน่าเชื่อทั้งชุด

### H2 — `.DS_Store` หลุดเข้า plan dir
ควร gitignore

### H3 — ข้อสังเกตเชิง process (ให้เจ้าของตัดสิน ไม่ใช่ว่าผิด)
~627KB / 20 docs สำหรับ pilot 2 อสม. ~30 คน 1 รพ.สต. — **build scope แคบและดี** (deferred เยอะ เป็นระเบียบ) แต่ **ปริมาณเอกสาร upfront หนัก** สำหรับ stage ที่ยังต้อง validate และเริ่มมี drift: PWA_SPEC = "Implemented with deviations" (เอกสารเริ่มไม่ตรงโค้ด), INDEX metadata เก่า, decisions กระจาย (S1) ความเสี่ยงจริง = **ต้นทุนรักษา 20 doc ให้ sync กับโค้ดที่กำลังขยับ** ทางเบากว่า: มี core "living" แค่ decisions log + current-state ที่อัปเดตจริง แล้วปล่อย spec ละเอียดเป็น point-in-time (freeze + ลงวันที่) — ถ้าใช้ doc ป้อน Claude Code หรือเอาไปคุย partner/legal ปริมาณนี้อาจคุ้ม เจ้าของรู้บริบทดีที่สุด

---

## 6. Next actions

1. เจ้าของ review findings → ตัดสินแต่ละ ID (Accept/Reject) → อัปเดตคอลัมน์ Status + บันทึก decision ที่ [[PLAN_REVIEW_RESPONSE]]
2. C3 ต้อง `grep` ชื่อคอลัมน์จริงก่อน patch
3. Tier 1 (C1/C2/M1) แก้ได้ทันทีหลัง accept — เป็นของที่ชัวร์ว่าพัง
4. Tier 3 (P1/P2): cross-check กับ [[PDPA_COMPLIANCE]] + [[CONSENT_FLOW_SPEC]] ก่อนสรุป

---

**End of Plan Audit Round 2** — Update 2026-06-21: C1/C2/C3/C4/M1/S2/S3/P2 patched ใน ORG_FOUNDATION (v1.5) + PLAN_REVIEW_RESPONSE (v1.3). คงเหลือ open: S1 (source-of-truth consolidation), P1 (รอ PDPA consult), H1–H3 (hygiene)
