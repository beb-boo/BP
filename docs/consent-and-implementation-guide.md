# Consent Flows & Implementation Guide (v2.0)

**BP Monitor — Consent Implementation Guide**

วันที่: [วัน/เดือน/ปี]
เวอร์ชัน: 2.0

---

> **Version 2.0 — Update notes**
> ฉบับนี้ขยายจาก v1 (self-managed + OCR + doctor access) เพิ่มเติม:
> - **Proxy-managed flow** (อสม. เก็บข้อมูลให้ชาวบ้าน)
> - **Granular consent scopes** (asm_collect, rpsst_view, doctor_view, etc.)
> - **Organization ToS acceptance flow** (admin ของ รพ.สต.)
> - **Edge cases** (illiterate, cognitive impairment, non-Thai, deceased, refusal)
> - **Paper + digital signature hybrid** workflow
>
> Version 1.0 เก็บไว้ที่ `consent-and-implementation-guide-v1.md`

**เอกสารอ้างอิง:**
- ฉบับที่แสดงแก่ผู้ใช้: `docs/privacy-policy.md`, `docs/terms-of-service.md`, `docs/org-terms-of-service.md`
- แผนการ implement: `plan/v2-asm-org-support/CONSENT_FLOW_SPEC.md`
- DB schema: `plan/v2-asm-org-support/ORG_FOUNDATION.md`

---

## Part 1: Consent Flows Overview

BP Monitor มี consent flow 4 แบบตามประเภทผู้ใช้:

### Flow 1: Self-managed (ชาวบ้านใช้ระบบเอง) — เหมือน v1
### Flow 2: Proxy-managed (อสม. เก็บข้อมูลให้) — NEW v2
### Flow 3: Organization ToS (admin ของ รพ.สต.) — NEW v2
### Flow 4: OCR Batch consent (เหมือน v1 แต่เพิ่ม batch)

---

## Part 2: Flow 1 — Self-managed

### 2.1 Consent Collection (ลงทะเบียน)

**Trigger:** ผู้ใช้สมัครบัญชีครั้งแรก

**UI elements:**
1. กรอกข้อมูลบัญชี (ชื่อ, อีเมล/เบอร์, รหัสผ่าน)
2. แสดง consent checklist (checkbox แยกกัน — ห้าม pre-check):
   - ☐ ยอมรับ Terms of Service
   - ☐ ยอมรับ Privacy Policy
   - ☐ **ยินยอมให้เก็บข้อมูลสุขภาพ** (ม.26 PDPA — สำคัญ)
3. ยืนยันตัวตนผ่าน OTP (SMS/Email/Telegram)
4. บันทึก consent record พร้อม: version, timestamp, IP, user agent

**API:**
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "name": "...",
  "email": "...",
  "phone": "...",
  "password": "...",
  "consents": {
    "terms": {"version": "2.0", "accepted": true},
    "privacy_policy": {"version": "2.0", "accepted": true},
    "health_data_collection": {"version": "2.0", "accepted": true}
  },
  "otp": "123456"
}
```

### 2.2 Consent Collection (OCR)

**Trigger:** ผู้ใช้ใช้ฟีเจอร์ OCR ครั้งแรก

**UI:** Modal แสดง "ยอมให้ส่งภาพไป Google Gemini API" + ให้ทางเลือก "บันทึกด้วยตนเอง"

**API:**
```http
POST /api/v1/readings/ocr
{
  "consents": {"ocr_processing": {"version": "2.0", "accepted": true}},
  "image": "..."
}
```

### 2.3 Consent Collection (Doctor Access)

**Trigger:** แพทย์ส่งคำขอเชื่อมต่อ

**UI:** Notification + modal "อนุมัติ" / "ปฏิเสธ"

**API:**
```http
POST /api/v1/patient-doctor/respond/{request_id}
{"approved": true}
```

### 2.4 Withdrawal (Self-managed)

- Settings → Privacy → Withdraw Consent
- สามารถถอน scope แยกได้ (health_data_collection, ocr, doctor_access)
- ถอนทั้งหมด = ลบบัญชี

---

## Part 3: Flow 2 — Proxy-managed (NEW v2)

### 3.1 Overview

**Context:**
- ชาวบ้านไม่มีสมาร์ทโฟนหรือไม่ต้องการล็อกอินเอง
- อสม. ไปเยี่ยมบ้านครั้งแรก เพื่อเก็บ consent
- ใช้ **paper + digital signature hybrid**

### 3.2 Step-by-step Workflow

**Step 0: Preparation (admin)**
- Admin ของ รพ.สต. พิมพ์ consent form 2 ฉบับ (ฉบับชาวบ้าน + ฉบับ รพ.สต.)
- สร้างบัญชีชาวบ้านในระบบ (proxy_managed account_type)
- ผูก อสม. กับชาวบ้าน (care assignment)

**Step 1: อสม. ไปเยี่ยมบ้าน**
- ถือกระดาษ consent + เครื่องวัด + สมาร์ทโฟน
- อธิบาย purpose ของการเก็บข้อมูล
- ใช้สคริปต์มาตรฐาน (ดู [CONSENT_FORMS.md](../plan/v2-asm-org-support/CONSENT_FORMS.md))

**Step 2: ชาวบ้านอ่าน consent (หรือ อสม. อ่านให้ฟัง)**
- ภาษาไทยชัดเจน ใช้คำที่ผู้สูงอายุเข้าใจ
- ย้ำ 3 ประเด็นสำคัญ: (1) เก็บอะไร (2) ใครดูได้ (3) ถอนได้ทุกเมื่อ

**Step 3: Granular scope selection**
- ชาวบ้านเลือก scopes ที่ยินยอม:
  - ☐ ให้ อสม. เก็บข้อมูลความดัน (Core — ต้องมี)
  - ☐ ให้ รพ.สต. ดูข้อมูล (Core — ต้องมี)
  - ☐ ให้แพทย์ที่อนุมัติดูข้อมูล (Optional)
  - ☐ ให้ใช้ข้อมูลเพื่อ research (ไม่ระบุตัวตน, Optional)

**Step 4: ชาวบ้านเซ็นกระดาษ**
- เซ็นชื่อ/พิมพ์นิ้วลงบนกระดาษ 2 ฉบับ
- อสม. เซ็นเป็นพยาน

**Step 5: Digital capture ใน PWA**
- อสม. เปิด PWA → Patient Profile → Consent → New
- Tick scopes ที่ชาวบ้านเลือก (ต้องตรงกับกระดาษ)
- ให้ชาวบ้านแตะนิ้วเซ็นบนจอโทรศัพท์ (touchscreen signature)
- ระบบจับ: GPS + timestamp + witness_user_id = อสม.
- Submit → บันทึกเข้า `consent_records` table

**Step 6: แจกจ่ายกระดาษ**
- ชาวบ้านเก็บ 1 ฉบับ
- อสม. นำอีก 1 ฉบับกลับ รพ.สต.
- Admin เก็บใน **ตู้ล็อกที่ รพ.สต.** → บันทึก `paper_filed_at` + `paper_filed_location` ในระบบ (metadata only, **ไม่ scan**)

### 3.3 Evidence Chain

**Digital evidence (primary — เก็บในระบบ):**
- `digital_signature_data` (base64 PNG, encrypted ด้วย Fernet)
- `digital_signature_hash` (SHA-256 ของ signature)
- `gps_latitude`, `gps_longitude`
- `granted_at` (timestamp)
- `witness_user_id` (อสม. ที่เป็นพยาน)
- `version` (consent form version)
- `language`, `method` (paper+digital)
- Granular `scope`

**Physical evidence (secondary — เก็บที่ รพ.สต.):**
- กระดาษ consent form ต้นฉบับ (เซ็นมือ)
- เก็บใน **ตู้ล็อก/ลิ้นชักปิด** ที่ รพ.สต.
- Tracked in system: `paper_filed_at`, `paper_filed_location`, `paper_filed_by_user_id`
- **ไม่ scan** เข้าระบบ — data minimization

### 3.4 Data Not Stored (by design)

- ❌ รูปใบหน้าชาวบ้าน — redundant เพราะมี signature + witness + GPS
- ❌ รูป scan ของกระดาษ — กระดาษเก็บ physical ที่ รพ.สต. แล้ว

### 3.5 Withdrawal (Proxy-managed)

**Channels:**
1. **Verbal to อสม.** — ชาวบ้านบอก อสม. ตอนเยี่ยม → อสม. แจ้ง admin
2. **Phone call to รพ.สต.** — ชาวบ้านโทรหา รพ.สต.
3. **Written letter** — ส่งจดหมายถึง รพ.สต.
4. **Direct to platform** — ติดต่อ [privacy@yourdomain.com] (fallback)

**Admin flow:**
1. Login เข้า admin web
2. Patient profile → Consent records → Withdraw
3. เลือก scope ที่ต้องการ withdraw (หรือทั้งหมด)
4. Enter reason (optional)
5. System:
   - Update consent record: status=`withdrawn`, `withdrawn_at`, `withdrawal_reason`
   - Block future API calls ที่อาศัย scope นั้น
   - Log audit trail
   - Optional: notify อสม.

**Effects:**
- อสม. บันทึกข้อมูลใหม่ไม่ได้ (ถ้า asm_collect withdrawn)
- รพ.สต. admin ดูข้อมูลเก่าได้อยู่ (read-only historical) แต่เขียนใหม่ไม่ได้
- ข้อมูลเก่ายังอยู่จน data erasure request (separate from consent withdrawal)

---

## Part 4: Flow 3 — Organization ToS (NEW v2)

### 4.1 Overview

Admin ของ รพ.สต. ต้องยอมรับ [Organization Terms of Service](./org-terms-of-service.md) ก่อนใช้ features ขององค์กร

### 4.2 Trigger Points

- **First-time admin onboarding** — สมัครบัญชีครั้งแรก
- **Version update** — เมื่อ Org ToS version ใหม่
- **Admin role transfer** — คนรับโอนต้อง accept อีกครั้ง

### 4.3 UI Flow

**Modal (blocking, non-dismissable):**
1. Show full Org ToS (iframe หรือ embedded)
2. 3 checkboxes ที่ต้อง check ทั้งหมด:
   - ☐ ท่านได้อ่านและเข้าใจข้อกำหนดฉบับนี้
   - ☐ ท่านมีอำนาจผูกพันองค์กร
   - ☐ ท่านยอมรับข้อกำหนดในนามขององค์กร
3. ปุ่ม "ยอมรับและดำเนินการต่อ" (disabled จนกว่าจะ check ทั้ง 3)

### 4.4 Backend Recording

```python
# app/api/org_onboarding.py
@router.post("/accept-org-terms")
async def accept_org_terms(version: str, ...):
    org.terms_version = version
    org.terms_accepted_at = datetime.utcnow()
    org.terms_accepted_by_user_id = current_user.id
    org.terms_accepted_from_ip = request.client.host
    
    await log_audit(action="org_update", metadata={
        "event": "org_terms_acceptance",
        "terms_version": version
    })
```

### 4.5 Middleware Enforcement

```python
# app/middleware/terms.py
if user.role == "rpsst_admin":
    if org.terms_version != CURRENT_ORG_TERMS_VERSION:
        # Allow read, block writes
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            raise HTTPException(403, "Org ToS acceptance required")
```

---

## Part 5: Flow 4 — OCR Batch Consent

### 5.1 Overview

OCR batch = ถ่ายรูป **ใบรายชื่อ + เครื่องวัด** ในรูปเดียว → Gemini อ่านเลขความดัน + ลำดับคนไข้

**Consent impact:**
- ต้องมี `asm_collect` scope ของชาวบ้านทุกคนที่ปรากฏในใบรายชื่อ
- ระบบตรวจ pre-submission: ถ้า scope expired หรือ withdrawn → block
- ภาพถูกเก็บ **ชั่วคราวสูงสุด 7 วัน** เฉพาะเมื่อ confidence ต่ำ

### 5.2 Implementation

ดูรายละเอียดใน `plan/v2-asm-org-support/ASM_PWA_SPEC.md` section "Batch OCR"

---

## Part 6: Granular Consent Scopes

### 6.1 Scope Catalog

| Scope | ชื่อไทย | บังคับ? | ผลเมื่อ active |
|-------|---------|--------|----------------|
| `asm_collect` | ให้ อสม. เก็บข้อมูลความดัน | **Core** | อสม. ที่ถูก assign สามารถ POST bp_readings ของ patient นี้ |
| `rpsst_view` | ให้ รพ.สต. ดูข้อมูล | **Core** | admin ของ รพ.สต. ดู patient data ได้ |
| `doctor_view` | ให้แพทย์ที่อนุมัติดูข้อมูล | Optional | ต้องผ่าน patient-doctor request approval แยก |
| `research_anonymized` | research ที่ anonymize | Optional | ส่งข้อมูลเข้า research dataset (ไม่มี PII) |
| `data_export_to_smart_osm` | ส่งข้อมูลไป Smart อสม. | Optional | ระบบ export รายเดือนไป Smart อสม. API (Phase 2+) |

### 6.2 Core vs Optional

- **Core scopes** (asm_collect, rpsst_view) — ถ้า uncheck: ระบบไม่สามารถให้บริการได้ → ต้องปฏิเสธการเก็บข้อมูล
- **Optional scopes** — ชาวบ้านเลือกได้, checkbox empty by default

### 6.3 Withdrawal Matrix

| Scope withdrawn | Effect |
|----------------|--------|
| `asm_collect` | อสม. บันทึกข้อมูลใหม่ไม่ได้. ข้อมูลเดิมยังอยู่ (jusqu'à data erasure request) |
| `rpsst_view` | รพ.สต. admin ดูข้อมูลใหม่ไม่ได้ (historical data ยังอยู่ตาม retention) |
| `doctor_view` | Revoke doctor access. แพทย์เห็นข้อความ "ผู้ป่วยถอน consent" |
| `research_anonymized` | Stop future anonymization. ข้อมูลที่ส่งไปแล้ว ไม่สามารถดึงกลับ (anonymized แล้ว) |
| All core | ถาม user: ต้องการ **Data Erasure** ด้วยไหม? (full deletion) |

### 6.4 Implementation Notes

- แต่ละ scope มี effective_from + effective_until (ถ้ามี)
- เก็บ history ของ consent changes (ไม่ overwrite record)
- Middleware check `is_consent_active(patient_id, scope)` ก่อนทุก sensitive operation

---

## Part 7: Edge Cases & Special Scenarios

### 7.1 ชาวบ้านที่อ่านหนังสือไม่ออก / เขียนไม่ได้

**Process:**
- อสม. อ่าน consent ให้ฟังแบบละเอียด
- ใช้ **ลายนิ้วมือ** แทนลายเซ็น (บนกระดาษ + digital)
- **Witness เพิ่ม 1 คน** นอกจาก อสม. (ญาติ หรือคนในชุมชนที่ไม่เกี่ยวข้อง)
- บันทึกใน metadata: `method: "fingerprint"`, `witness_count: 2`

### 7.2 Cognitive Impairment (สมองเสื่อม, เป็นผู้ป่วยติดเตียง)

**Process:**
- **ไม่สามารถให้ consent ได้ด้วยตนเอง**
- ต้องให้ **ผู้ดูแลตามกฎหมาย** (guardian) เป็นผู้ให้ consent แทน
- ต้องมีเอกสาร:
  - สำเนาบัตรประชาชนของ guardian
  - เอกสารรับรองความสัมพันธ์ (ทะเบียนบ้าน, ใบรับรองแพทย์, คำสั่งศาล)
- บันทึกใน metadata: `consent_by: "guardian"`, `guardian_user_id`, `guardian_relationship`

### 7.3 ชาวบ้านที่ไม่พูดภาษาไทย (ชนเผ่า, แรงงานต่างชาติ)

**Process:**
- ใช้ล่าม (ญาติ หรือเจ้าหน้าที่) — ต้องระบุในเอกสาร
- หากเป็นไปได้: ใช้ consent form ภาษานั้น (ผลิตเพิ่มสำหรับชาวบ้านเฉพาะกลุ่ม)
- บันทึกใน metadata: `language: "mien"`, `interpreter_user_id`, `interpreter_name`

### 7.4 ชาวบ้านปฏิเสธ consent

**Process:**
- **ห้ามเก็บข้อมูล** — no work-around
- บันทึก "attempt_no_consent" log (เพื่อไม่ให้ อสม. พยายามอีกในอนาคตอันใกล้ เว้นแต่ชาวบ้านขอเอง)
- อสม. ไม่ reprisal, ไม่กดดัน
- ชาวบ้านยังใช้บริการ รพ.สต. แบบปกติได้ (แค่ไม่ใช้ BP Monitor)

### 7.5 ชาวบ้านเสียชีวิต

**Process:**
- Admin มี notification
- Status: `deceased`
- **ข้อมูลเก็บต่อ 10 ปี** (เวชระเบียน) แล้ว anonymize/ลบ
- หากญาติขอ data portability: ให้ได้ (ต้องมีเอกสารรับรองความสัมพันธ์ + ใบมรณบัตร)

### 7.6 Admin ของ รพ.สต. ลาออกกะทันหัน

**Process:**
- ดูรายละเอียดใน [Organization Terms of Service](./org-terms-of-service.md) section 5.2
- หากไม่มี admin เหลือ: superadmin ของเราช่วย reassign
- ต้องมีเอกสารจากองค์กร + หลักฐานอำนาจของผู้ขอใหม่
- Process: 3-7 วันทำการ

### 7.7 ชาวบ้านย้าย รพ.สต.

**Process:**
- ชาวบ้านต้องขอ data portability
- Export จาก รพ.สต. เดิม (CSV/JSON)
- รพ.สต. ใหม่ import (admin manually) + สร้าง consent ใหม่
- ไม่มีการโอนย้ายโดยอัตโนมัติ — protect ชาวบ้านจาก unintended data flow

---

## Part 8: Implementation Checklist

### 8.1 Database (ดู `plan/v2-asm-org-support/ORG_FOUNDATION.md`)

ต้องมี tables:
- [ ] `consent_records` (ตาม schema ใน ORG_FOUNDATION section 4.1.4)
- [ ] `audit_logs` (สำหรับ log consent actions)
- [ ] `users.terms_version`, `users.privacy_policy_version` (tracking)
- [ ] `organizations.terms_version` (org ToS tracking)

### 8.2 Backend

- [ ] API: `/api/v1/consent/grant`
- [ ] API: `/api/v1/consent/withdraw`
- [ ] API: `/api/v1/consent/list` (ของ user ตัวเอง)
- [ ] API: `/api/v1/admin/consent/list` (ของ patient ใน org)
- [ ] API: `/api/v1/admin/consent/record-paper` (อสม.: บันทึก digital consent)
- [ ] Middleware: `check_consent_active(patient_id, scope)`
- [ ] Service: `ConsentService` (grant, withdraw, check active, history)
- [ ] Cron: auto-expire consents ที่มี expires_at

### 8.3 Frontend (PWA — อสม.)

- [ ] Consent capture screen
- [ ] Signature pad (react-signature-canvas หรือเทียบเท่า)
- [ ] GPS capture (navigator.geolocation)
- [ ] Granular scope checkboxes
- [ ] Summary review → submit

### 8.4 Frontend (Admin Web)

- [ ] Consent records list per patient
- [ ] Withdraw modal (scope selection + reason)
- [ ] Paper filing tracker
- [ ] Org ToS acceptance modal (onboarding + version update)

### 8.5 Legal / Operational

- [ ] Print consent forms (ดู `plan/v2-asm-org-support/CONSENT_FORMS.md`)
- [ ] ตู้ล็อก ที่ รพ.สต. สำหรับเก็บกระดาษ
- [ ] อสม. training session on consent process
- [ ] Script สำหรับ อสม. อธิบายชาวบ้าน (ภาษาไทย + ถิ่น)
- [ ] PDPA consultant review

---

## Part 9: Placeholders to Fill (All Files)

ค้นหาและแทนที่ในทุกไฟล์ `docs/*.md`:

| Placeholder | คำอธิบาย | ตัวอย่าง |
|-------------|---------|---------|
| `[ชื่อผู้ควบคุมข้อมูล/ชื่อบริษัท]` | ชื่อจริงหรือชื่อนิติบุคคล | นาย พรเทพ xxx / บริษัท xxx จำกัด |
| `[ที่อยู่]` | ที่อยู่สำหรับติดต่อ | 123 ถ.xxx เขตxxx กรุงเทพฯ 10xxx |
| `[privacy@yourdomain.com]` | อีเมลด้านข้อมูลส่วนบุคคล | privacy@bpmonitor.app |
| `[support@yourdomain.com]` | อีเมลสนับสนุน | support@bpmonitor.app |
| `[security@yourdomain.com]` | อีเมลแจ้ง breach | security@bpmonitor.app |
| `[dpo@yourdomain.com]` | อีเมล DPO | dpo@bpmonitor.app |
| `[https://yourdomain.com]` | เว็บไซต์หลัก | https://bpmonitor.app |
| `[วัน/เดือน/ปี]` | วันที่มีผลบังคับใช้ | 1 กรกฎาคม 2569 |

---

## Part 10: Legal Disclaimer

### 10.1 เอกสารนี้ไม่ใช่คำปรึกษาทางกฎหมาย

เอกสารเหล่านี้เป็น **แนวทาง (Template)** ที่เขียนขึ้นตาม data flow จริงของระบบ BP Monitor แต่ **ไม่ใช่คำปรึกษาทางกฎหมาย** ควรให้ **ทนายความหรือที่ปรึกษาที่มีความเชี่ยวชาญด้าน PDPA** ตรวจสอบก่อนเผยแพร่จริง

### 10.2 ข้อควรระวัง PDPA

- ข้อมูลสุขภาพอยู่ภายใต้ **มาตรา 26 PDPA** ซึ่งมีบทลงโทษรุนแรง (ทั้งทางแพ่งและทางอาญา) หากไม่ปฏิบัติตาม
- การเก็บ consent ต้อง **โดยชัดแจ้ง (Explicit)** ไม่ใช่ implied
- Pre-checked checkboxes = **ไม่ถือเป็น consent ที่ถูกต้อง**
- Bundled consent (รวม checkbox หลายเรื่องใน 1 คลิก) = **ไม่ถือเป็น consent ที่ถูกต้อง**

### 10.3 Medical Device Considerations

- หากมีแผนขึ้นทะเบียนเป็น **อุปกรณ์ทางการแพทย์** (อย./FDA) ในอนาคต:
  - ต้องปรับข้อกำหนดเพิ่มเติมอย่างมาก
  - ต้อง clinical validation
  - ต้อง QMS (Quality Management System)
  - ต้อง post-market surveillance

---

## Part 11: Version History

| Version | Date | Major Changes |
|---------|------|--------------|
| 2.0 | 2026-04-XX | เพิ่ม proxy-managed flow, granular scopes, org ToS, edge cases |
| 1.0 | 2026-04-03 | Initial release (self-managed + OCR + doctor access) |

Archived: `consent-and-implementation-guide-v1.md`

---

**End of Consent Flows & Implementation Guide v2.0**
