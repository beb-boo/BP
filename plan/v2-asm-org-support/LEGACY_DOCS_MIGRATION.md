---
title: "Legacy Docs Migration Plan"
aliases:
  - "Legacy Migration"
  - "Docs Patch Plan"
tags:
  - planning
  - legal
  - pdpa
  - migration
  - v2-asm-org
order: 7
status: draft
version: 1.1
updated: 2026-04-18
summary: "Patch plan for existing docs/ (privacy-policy, terms-of-service, consent-and-implementation-guide) to align with v2 ASM/org model"
related:
  - "[[MVP_PILOT_SCOPE]]"
  - "[[ORG_FOUNDATION]]"
  - "[[CONSENT_FLOW_SPEC]]"
  - "[[PLAN_REVIEW_RESPONSE]]"
---
# Legacy Docs Migration Plan

> **Purpose:** วางแผนการปรับปรุงเอกสาร 3 ไฟล์ใน `docs/` ที่เขียนไว้สำหรับ v1 (personal only) ให้รองรับ v2 (ASM + รพ.สต. + proxy patients)
>
> **v1.1 alignment verified** (2026-04-18): เนื้อหาทุก section ตรงกับ decisions ใน [[PLAN_REVIEW_RESPONSE]] — joint controller model, granular scopes, retention periods (OCR 7 วัน), paper-not-scanned policy

---

## 1. Affected Legacy Docs

| File | Current version | Target version | Scope of change |
|------|----------------|----------------|-----------------|
| `docs/privacy-policy.md` | 1.0 | 2.0 | Major update (+30-40%) |
| `docs/terms-of-service.md` | 1.0 | 2.0 | Major update + **split** into 2 files |
| `docs/consent-and-implementation-guide.md` | 1.0 | 2.0 | Major update (+60%) |

---

## 2. Versioning Strategy

### 2.1 Principle: Backward-compatible + progressive disclosure

- v1 users (self_managed) จะเห็น v2 policies ตอน login ครั้งต่อไป → ต้อง re-accept
- New users (อสม., admin, proxy patient) เห็น v2 ตั้งแต่แรก
- Historical consent records ยังอ้างอิง v1 version (legally valid ณ เวลานั้น)
- In-app: show "Updated" notice with diff summary

### 2.2 Consent version tracking (code level)

ใน [[ORG_FOUNDATION]] — users table มี `terms_accepted_version` + `privacy_policy_accepted_version`

```python
# Check on each authenticated request
if user.terms_accepted_version != CURRENT_TERMS_VERSION:
    # Show re-acceptance modal
    return require_terms_acceptance()
```

### 2.3 Version 2.0 effective date

**Proposed:** Set on launch of Phase 1 pilot. All existing users get 30-day transition notice + in-app banner before cutover.

---

## 3. privacy-policy.md → v2.0

### 3.1 Sections Requiring Major Update

#### Section 2: ผู้ควบคุมข้อมูลส่วนบุคคล
**Change:** Add explanation of **joint controllers** concept for org mode

```markdown
## 2. ผู้ควบคุมข้อมูลส่วนบุคคล

[ชื่อผู้ควบคุมข้อมูล/ชื่อบริษัท] ("เรา") เป็น Data Controller หลักของแพลตฟอร์ม

**สำหรับผู้ใช้ทั่วไป (ชาวบ้านที่ใช้เอง):** เราเป็นผู้ควบคุมข้อมูลฝ่ายเดียว

**สำหรับผู้ใช้ที่มาผ่าน รพ.สต. / องค์กร:** 
เราและองค์กรของท่าน (เช่น รพ.สต.) เป็น **Joint Controllers** (ผู้ควบคุมข้อมูลร่วม)
ตามมาตรา 24 แห่ง PDPA:
- เรารับผิดชอบ: ระบบ, ความปลอดภัยทางเทคนิค, การเข้ารหัส
- องค์กรรับผิดชอบ: ความถูกต้องของข้อมูลที่ป้อน, การเก็บ consent, การใช้งานเพื่อการดูแลสุขภาพ

ท่านสามารถใช้สิทธิตาม PDPA ได้กับทั้งสองฝ่าย
```

#### Section 3: ข้อมูลที่เราเก็บรวบรวม
**Add:** 
- ข้อมูลของ อสม. (เบอร์โทร, ชื่อ, บทบาท, care assignments)
- ข้อมูลองค์กร (รพ.สต. profile, admin contact)
- Digital signature (e-signature ใน consent flow)
- GPS coordinates (ตอน consent capture, optional ใน readings)
- OCR ภาพ ใบรายชื่อ + เครื่องวัด (ชั่วคราว, max 7 วัน)

**Explicit statement:** 
```markdown
### ข้อมูลที่เราไม่เก็บ (by design)
- รูปจอเครื่องวัดที่ถ่ายเพื่อ OCR — ลบทันทีหลัง process
- รูปกระดาษ consent form — เก็บ physical ที่ รพ.สต. ไม่ scan เข้าระบบ
- เนื้อหาการสนทนาใน Telegram นอกเหนือจากที่ bot ต้อง process
```

#### Section 4: วัตถุประสงค์และฐานทางกฎหมาย
**Add new rows:**

```markdown
| ให้ อสม. เก็บข้อมูลสุขภาพแทนชาวบ้าน | ข้อมูลสุขภาพ, ตำแหน่ง | ความยินยอมชัดแจ้ง (ม.26) — scope "caregiver_collect" |
| ให้ รพ.สต. ดูข้อมูลเพื่อการดูแลต่อเนื่อง | ข้อมูลสุขภาพ | ความยินยอมชัดแจ้ง (ม.26) — scope "org_view" |
| ให้ อสม./admin เก็บ consent ของชาวบ้าน | Digital signature, GPS | สัญญา + ประโยชน์โดยชอบด้วยกฎหมาย |
| บันทึก audit log ของการเข้าถึงข้อมูล | Activity log | หน้าที่ตามกฎหมาย (ม.37) |
```

#### Section 5: การเปิดเผยข้อมูลและผู้ประมวลผลข้อมูล
**Add new rows:**

```markdown
### 5.2 บุคคลอื่นที่อาจเข้าถึงข้อมูล (เพิ่ม)

- **อาสาสมัครสาธารณสุข (อสม.) ที่ได้รับมอบหมาย**: เข้าถึงข้อมูลชาวบ้านที่ตัวเอง 
  ได้รับการผูกผ่าน care assignment เท่านั้น เมื่อชาวบ้านได้ให้ consent scope "caregiver_collect"
  
- **เจ้าหน้าที่ รพ.สต. ที่เป็น admin**: เข้าถึงข้อมูลชาวบ้านทุกคนในความรับผิดชอบของ 
  รพ.สต. นั้น เมื่อได้ให้ consent scope "org_view"

- **ข้อจำกัด**: ทั้งสองกลุ่มเห็นข้อมูลเฉพาะองค์กรของตัวเอง (organization isolation)
  ทุก access ถูก log ใน audit trail
```

#### Section 7: มาตรการรักษาความปลอดภัย
**Add:** RBAC, tenant isolation, audit log + hash of signatures for tamper detection

#### Section 8: ระยะเวลาในการเก็บรักษา
**Update table** (expand):

```markdown
| ประเภทข้อมูล | ระยะเวลา | เหตุผล |
|-------------|---------|--------|
| ข้อมูลบัญชี (self_managed) | ขณะ active + 90 วัน | ไม่เปลี่ยน |
| ข้อมูลบัญชี (proxy_managed — ชาวบ้าน) | ขณะ active + 90 วันหลังถอน consent | PDPA + เวชระเบียน |
| ข้อมูลบัญชี อสม. (active in org) | ขณะยังเป็น org member + 1 ปี | Audit trail |
| ข้อมูลสุขภาพ (ค่าความดัน) | 10 ปี (เวชระเบียน) หรือจน withdraw consent | มาตรฐาน เวชระเบียน |
| ภาพ OCR ใบรายชื่อ | สูงสุด 7 วัน (review queue) | Data minimization |
| Digital signature ของ consent | 10 ปี หลัง withdrawal | Legal defensibility |
| Consent records | 10 ปี หลัง withdrawal | PDPA obligation |
| Audit logs | 2 ปี hot + 5 ปี cold | PDPA + security forensics |
| Care assignments | ขณะ active + 10 ปี | Audit |
```

#### NEW Section: 10.4 สิทธิของเจ้าของข้อมูลในกรณี proxy-managed

```markdown
### 10.4 สิทธิพิเศษของชาวบ้านที่ไม่ได้ล็อกอินเอง (Proxy-managed Patients)

หากท่านเป็นชาวบ้านที่ข้อมูลถูกเก็บโดย อสม. ท่านมีสิทธิเต็มตาม PDPA เหมือนผู้ใช้ทั่วไป:

- **ขอดูข้อมูล**: ติดต่อ รพ.สต. หรือ อสม. ที่ดูแลท่าน
- **ขอแก้ไข**: แจ้ง อสม. เพื่อแก้ไขในระบบ
- **ขอลบ**: ติดต่อ รพ.สต. admin
- **ถอน consent**: ทำได้ตลอดเวลา (verbal, in-person, หรือจดหมาย)
- **โอนข้อมูล**: ขอ export ได้เป็น PDF หรือ CSV

**ช่องทางพิเศษ:** หากท่านไม่สามารถเข้าถึง อสม./รพ.สต. ได้ ติดต่อเราโดยตรงที่ [privacy@yourdomain.com]
```

### 3.2 Implementation

```diff
# Suggested PR scope
docs/
├── privacy-policy.md         # Update in-place to v2.0
├── privacy-policy-v1.md      # Archive v1 for historical reference
└── CHANGELOG.md              # New: track version changes
```

**Timeline:** 1 week for draft → legal review → publish

---

## 4. terms-of-service.md → Split into 2 files

**Major structural change:** Split into:
1. **`docs/terms-of-service.md` (v2.0)** — ToS สำหรับ individual users (ชาวบ้าน, แพทย์, อสม.)
2. **`docs/org-terms-of-service.md` (NEW v1.0)** — ToS สำหรับ admin ที่ผูกกับองค์กร (รพ.สต.)

### 4.1 terms-of-service.md v2 changes

Add role-specific sections:

#### NEW Section: 5.4 หน้าที่ของอาสาสมัครสาธารณสุข (อสม.)

```markdown
### 5.4 หน้าที่ของ อสม.

เมื่อท่านลงทะเบียนและใช้บริการในบทบาทอาสาสมัครสาธารณสุข:

- ใช้งานภายใต้การกำกับของ รพ.สต. ที่ท่านสังกัด
- บันทึกข้อมูลความดันโลหิตของชาวบ้านที่ได้รับมอบหมายเท่านั้น
- ได้รับความยินยอมจากชาวบ้าน (paper + digital) ก่อนเก็บข้อมูล
- ไม่เปิดเผยข้อมูลของชาวบ้านแก่บุคคลภายนอก
- ปฏิบัติตามจรรยาบรรณของอาสาสมัครสาธารณสุข
- ตรวจสอบค่าที่ OCR อ่านได้ทุกครั้งก่อนบันทึก
- แจ้ง รพ.สต. ทันทีหากสงสัยว่ามีการละเมิดความเป็นส่วนตัวหรือเหตุการณ์ผิดปกติ

การละเมิดข้อปฏิบัติดังกล่าว อาจทำให้ถูกระงับบัญชีและ/หรือรายงานต่อ รพ.สต.
```

#### Update Section 5.1 การลงทะเบียน

Add phone + Telegram OTP flow explanation:

```markdown
### 5.1 การลงทะเบียน (ปรับปรุง v2)

สำหรับผู้ใช้แต่ละประเภท:

- **ชาวบ้านที่ใช้เอง (self_managed)**: ลงทะเบียนผ่านเว็บ/Telegram + OTP
- **อสม.**: ลงทะเบียนโดย admin ของ รพ.สต. + ผูก Telegram (pairing code)
- **แพทย์**: ลงทะเบียน + ตรวจใบอนุญาตกับแพทยสภา
- **ชาวบ้านแบบ proxy-managed**: สร้างบัญชีโดย admin/อสม. ไม่ล็อกอินเอง
```

#### NEW Section: 6.3 ข้อพิเศษสำหรับผู้ใช้ที่มาผ่านองค์กร

```markdown
### 6.3 ผู้ใช้ที่มาผ่าน รพ.สต.

หากท่านได้รับบัญชีผ่าน รพ.สต.:
- ท่านยังคงเป็นเจ้าของข้อมูลของตัวเองตาม PDPA
- รพ.สต. เป็น joint controller — รับผิดชอบร่วมกันกับเรา
- ท่านสามารถถอน consent หรือย้ายออกจาก รพ.สต. ได้ตลอดเวลา
- หากท่านย้าย รพ.สต. ข้อมูลจะไม่ถ่ายโอนโดยอัตโนมัติ — ต้องขอ data portability
```

### 4.2 NEW: org-terms-of-service.md (Organization ToS)

This is a new file สำหรับ admin ของ รพ.สต. / องค์กร. แสดงตอน admin accept terms ใน onboarding flow.

**ดูรายละเอียดใน section 5 ของเอกสารนี้**

---

## 5. NEW: docs/org-terms-of-service.md

### 5.1 Purpose

ข้อตกลงสำหรับองค์กร (รพ.สต. / คลินิก / บริษัท) ที่ใช้ BP Monitor เพื่อการทำงาน — admin ของ org accept ในนามองค์กร

### 5.2 Structure (proposed)

```markdown
# ข้อกำหนดการใช้บริการสำหรับองค์กร (Organization Terms of Service)

เวอร์ชัน: 1.0
วันที่มีผลบังคับใช้: [TBD]

---

## 1. คำนิยาม

- **"องค์กร"** หมายถึง รพ.สต., โรงพยาบาล, คลินิก, หรือหน่วยงานอื่นที่มีสมาชิก (เช่น อสม., พยาบาล) ใช้งานระบบ
- **"Admin ขององค์กร"** หมายถึง ผู้ที่ได้รับมอบหมายให้เป็นผู้ดูแลบัญชีองค์กรในระบบ
- **"สมาชิกขององค์กร"** หมายถึง อสม. หรือเจ้าหน้าที่ที่ถูกเพิ่มเข้าในองค์กรโดย Admin

## 2. การยอมรับในนามองค์กร

โดยการยอมรับข้อตกลงฉบับนี้ Admin ยืนยันว่า:
- ท่านมีอำนาจตามกฎหมายในการผูกพันองค์กรกับข้อตกลงนี้
- ข้อมูลองค์กรที่ท่านให้ถูกต้องและครบถ้วน
- ท่านจะแจ้งเราหากบทบาทของท่านเปลี่ยน (เช่น ลาออก, โอนย้าย)

## 3. บทบาทและความรับผิดชอบ (Joint Controller Model)

ภายใต้ PDPA องค์กรและเราเป็น **ผู้ควบคุมข้อมูลร่วม (Joint Controllers)** ของข้อมูลสมาชิกและผู้ใช้ของท่าน

### 3.1 ความรับผิดชอบของเรา (Platform Provider)
- ระบบ, software, security, availability
- Encryption at rest + in transit
- Audit logging
- Compliance tooling
- Data subject request processing (ด้านเทคนิค)

### 3.2 ความรับผิดชอบขององค์กร
- ความถูกต้องและชอบธรรมของข้อมูลที่ป้อน
- การเก็บ consent จาก data subjects (ชาวบ้าน)
- การใช้ข้อมูลเพื่อการดูแลสุขภาพเท่านั้น (purpose limitation)
- การจัดการสมาชิก (add/remove อสม.)
- การเก็บกระดาษ consent form ในตู้ล็อก
- การตอบข้อซักถามจาก data subjects เบื้องต้น
- การแจ้งเราทันทีหากเกิด data breach ที่ตรวจพบในฝั่งองค์กร

## 4. Ownership Transfer

หาก Admin ลาออกหรือโอนย้าย:
- Admin ปัจจุบันต้องดำเนินการ **Ownership Transfer** ก่อน deactivate ตัวเอง
- หากทำไม่ได้: superadmin ของเราสามารถ reassign ownership ได้เมื่อได้รับคำขอเป็นทางการจากองค์กร
- ข้อมูลขององค์กรยังคงอยู่ระหว่างช่วงเปลี่ยน

## 5. ข้อห้าม

องค์กร **ห้าม**:
- ใช้ข้อมูลสมาชิก/ชาวบ้านเพื่อการตลาดโดยไม่ได้รับความยินยอมแยก
- ขายข้อมูลหรือให้บุคคลภายนอก
- ใช้ระบบเพื่อวัตถุประสงค์ที่ไม่ใช่การดูแลสุขภาพ
- Bypass ระบบ consent หรือ audit log
- ให้สมาชิกของ org อื่นเข้าใช้บัญชีของตัวเอง

## 6. Subscription (ถ้ามีในอนาคต)

[TBD — รายละเอียด pricing model]

## 7. ยกเลิกบริการ

หากองค์กรต้องการยกเลิก:
- แจ้งล่วงหน้า 30 วัน
- ข้อมูลที่มีอยู่จะถูก export ให้องค์กร
- หลังจากนั้น 90 วัน ข้อมูลจะถูก anonymize หรือลบ
- อสม. ในองค์กรจะถูก deactivate (ชาวบ้านที่เคยดูแลได้รับแจ้งทางใดทางหนึ่ง)

## 8. Indemnification

องค์กรชดเชยเราจากการเรียกร้องที่เกิดจาก:
- การใช้งานผิดวัตถุประสงค์โดยสมาชิก
- การให้ข้อมูลเท็จของสมาชิก
- การละเมิด PDPA โดยสมาชิก

## 9. Governing Law

กฎหมายไทย ศาลไทย

## 10. ติดต่อ

[อีเมล, ที่อยู่ขององค์กร เรา]
```

---

## 6. consent-and-implementation-guide.md → v2.0

### 6.1 Current state (v1)

เอกสารเดิมเน้น self-managed flow (ลงทะเบียนเอง + OCR + doctor access)

### 6.2 v2 Additions

**Add major new sections** before existing content:

#### NEW Section 0: Consent Flows Overview

```markdown
# Consent Flows — v2.0

BP Monitor มี consent flow หลายแบบ ขึ้นกับประเภทผู้ใช้:

## Flow 1: Self-managed (ชาวบ้านที่ใช้เอง) — เหมือน v1

[... existing content ...]

## Flow 2: Proxy-managed (ชาวบ้านที่ อสม. เก็บข้อมูลให้) — NEW

### Overview
- ชาวบ้านไม่ได้ล็อกอินเอง
- อสม. ไปเยี่ยมบ้าน → อธิบาย consent → ชาวบ้านเซ็น
- ใช้ระบบ paper + digital signature hybrid

### Steps

1. **Admin ของ รพ.สต. สร้างบัญชีชาวบ้าน** ในระบบ (proxy_managed)
2. **อสม. ไปเยี่ยมบ้าน** พร้อมกระดาษ consent form (2 ฉบับ)
3. **อ่าน consent ให้ชาวบ้านฟัง** (มีสคริปต์ช่วย)
4. **ชาวบ้านเซ็นกระดาษ** → อสม. เซ็นเป็นพยาน
5. **อสม. เปิด PWA → Digital capture**:
   - Tick granular scopes ที่ชาวบ้านเลือก
   - ชาวบ้านแตะนิ้วเซ็นบนจอ (e-signature)
   - ระบบจับ GPS + timestamp
6. **อสม. นำกระดาษ 1 ฉบับกลับ รพ.สต.** → admin เก็บใน ตู้ล็อก
7. **ชาวบ้านเก็บกระดาษ** อีก 1 ฉบับไว้เอง

### Evidence Chain
- Digital: signature PNG (encrypted) + GPS + timestamp + witness_user_id → ใน `consent_records` table
- Physical: กระดาษที่ รพ.สต. (tracked via `paper_filed_at` metadata, no scan)

### Data Not Stored (by design)
- ❌ รูปใบหน้าชาวบ้าน — ไม่จำเป็น เพราะมีลายเซ็น + witness + GPS
- ❌ รูป scan ของกระดาษ — กระดาษเก็บ physical

### Withdrawal
- ชาวบ้านแจ้ง อสม./รพ.สต. (verbal, phone, letter)
- Admin เข้า system → withdraw consent scope ที่ต้องการ
- Downstream effects: API จะ block writes ทันที

## Flow 3: Organization ToS acceptance (admin ของ รพ.สต.) — NEW

(see [[ORG_TERMS_OF_SERVICE]])

## Flow 4: OCR Batch consent (เทียบกับ v1 OCR) — Updated
...
```

#### NEW Section: Granular Consent Scopes

```markdown
## Granular Scopes (v2)

ระบบรองรับ consent แบบ granular — ชาวบ้านเลือกได้ว่ายินยอมเรื่องใดบ้าง:

| Scope | ชื่อภาษาไทย | บังคับ? |
|-------|-----------|---------|
| `caregiver_collect` | ให้ อสม. เก็บข้อมูล | Core (ต้องมี) |
| `org_view` | ให้ รพ.สต. ดูข้อมูล | Core (ต้องมี) |
| `doctor_view` | ให้แพทย์ที่อนุมัติดูข้อมูล | Optional |
| `research_anonymized` | ให้ใช้เพื่อ research (ไม่ระบุตัวตน) | Optional |
| `data_export_to_smart_osm` | ส่งข้อมูลไป Smart อสม. | Optional |

ใน consent form:
- Core scopes: checkbox pre-checked แต่ uncheckable ได้ (ถ้า uncheck = จะไม่สามารถใช้บริการได้)
- Optional scopes: checkbox empty, ชาวบ้านเลือก

## Consent Withdrawal Matrix

เมื่อ withdraw แต่ละ scope:

| Scope withdrawn | Effect |
|----------------|--------|
| `caregiver_collect` | อสม. บันทึกข้อมูลใหม่ไม่ได้ (block API). ข้อมูลเดิมยังอยู่จน data erasure request |
| `org_view` | รพ.สต. admin ดูข้อมูลใหม่ไม่ได้ (ของเก่ายังดูได้ตาม retention) |
| `doctor_view` | Revoke doctor access (ถ้ามี) |
| `research_anonymized` | Stop future anonymization for this user |
| All core | ต้อง ask if want data deletion too (full erasure) |
```

#### UPDATED Section: Database Schema

Replace with reference to [[ORG_FOUNDATION]] + just note what's specific to consent:

```markdown
## Database Schema

ดูรายละเอียดเต็มใน [[ORG_FOUNDATION]] — `consent_records` table

Key fields:
- `scope` (enum ConsentScope) — granular
- `method` (paper / digital_signature / both)
- `digital_signature_data` (base64 PNG, encrypted)
- `gps_latitude/longitude`
- `witness_user_id` (อสม. ที่เป็นพยาน)
- `paper_filed_at/location` (metadata only, no scan)
- `status` (active/withdrawn/expired/superseded)
- `version` (consent form version)
```

#### NEW Section: Edge Cases (from CONSENT_FLOW_SPEC)

Bring over the edge cases section from [[CONSENT_FLOW_SPEC]]:
- Patient cannot read/write → fingerprint + witness
- Cognitive impairment → guardian consent
- Non-Thai speaker → interpreter
- Patient refuses → no data collection
- Deceased patient → retention rules

### 6.3 Content to Keep Unchanged

- Implementation checklist (ยังใช้ได้)
- Placeholder table (update ให้ครอบคลุม org fields)
- Legal disclaimer

### 6.4 Version Note

Add at top:
```markdown
> **Version 2.0** — Updated for ASM/รพ.สต. org support
> Previous version (v1.0, self-managed only) archived at `docs/consent-and-implementation-guide-v1.md`
```

---

## 7. Patching Workflow

### 7.1 Sequence (recommended)

1. **Archive v1 files** — copy to `*-v1.md` for historical reference
2. **Draft v2** — use this doc as checklist
3. **Legal review** — hire PDPA consultant (external)
4. **Translation review** — Thai language precision
5. **Stakeholder review** — รพ.สต. pilot partner
6. **Publish** — push to `docs/`, update deploy
7. **Communicate** — in-app banner + email to active users
8. **Enforce** — require re-acceptance at next login (v1 users)

### 7.2 File Locations After Migration

```
docs/
├── privacy-policy.md                     # v2.0 (current)
├── privacy-policy-v1.md                  # archived
├── terms-of-service.md                   # v2.0 (current, individual)
├── terms-of-service-v1.md                # archived
├── org-terms-of-service.md               # v1.0 (new, for organizations)
├── consent-and-implementation-guide.md   # v2.0 (current)
├── consent-and-implementation-guide-v1.md # archived
└── CHANGELOG.md                          # new: version history
```

### 7.3 Code Changes Required

Update constants:
```python
# app/config/legal.py
CURRENT_PRIVACY_POLICY_VERSION = "2.0"
CURRENT_TERMS_VERSION = "2.0"
CURRENT_ORG_TERMS_VERSION = "1.0"
CURRENT_CONSENT_FORM_VERSION = "2.0"
```

Update middleware to check versions on each authenticated request.

Update admin onboarding flow to show org_terms_of_service on first login.

---

## 8. Legal Review Checklist

Before publishing v2, external PDPA expert must verify:

- [ ] Joint controller language accurate
- [ ] Granular consent satisfies ม.26
- [ ] Retention periods compliant with medical record laws
- [ ] Data subject rights clearly explained for proxy-managed
- [ ] Breach notification language meets 72-hour requirement (ม.37)
- [ ] Cross-border transfer language covers Gemini/Vercel/Neon
- [ ] Children's data (ม.20) handled correctly (MVP out-of-scope)
- [ ] Electronic signature validity per E-Transactions Act 2544

---

## 9. Timeline

| Step | Duration | Owner |
|------|----------|-------|
| Draft v2 docs | 1 week | Product |
| Legal review | 1-2 weeks | External PDPA consultant |
| Stakeholder review | 1 week | รพ.สต. pilot, internal |
| Translation review | 3-5 days | Thai language expert |
| In-app integration | 1 week | Engineering |
| Publish + announce | 1 day | Product |
| Transition period | 30 days | - |
| **Total** | **5-7 weeks** | - |

Start date: before Phase 1 launch

---

## 10. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Legal review reveals major issues | Delay | Start legal review early in parallel |
| v1 users don't re-accept → churn | Users lost | Clear communication + simple flow + grace period |
| Translation ambiguity | Legal issues | Expert review + bilingual verification |
| Conflict with existing AGPL license | License conflict | Review open source obligations |

---

**End of LEGACY_DOCS_MIGRATION.md**
