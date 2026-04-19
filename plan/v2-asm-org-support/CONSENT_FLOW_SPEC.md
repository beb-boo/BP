# Consent Flow Specification — PDPA-Compliant Consent Workflow

> **Status:** Draft v1.2 — GENERALIZE_ORG_PLAN rename + self-measure withdrawal effect applied
> **Last updated:** 2026-04-19
> **Owner:** Pornthep
> **Depends on:** `MVP_PILOT_SCOPE.md`, `ORG_FOUNDATION.md`, `PLAN_REVIEW_RESPONSE.md`
> **Related:** `ADMIN_WEB_SPEC.md`, `CAREGIVER_PWA_SPEC.md`, `docs/pdpa/CONSENT_FORMS.md`, `docs/pdpa/PDPA_COMPLIANCE.md`

> [!INFO] **v1.1 changes**
> - §4.1.5: Data categories clarified — single-OCR images NOT stored; only low-confidence batch OCR images stored temporarily (7 days max)
> - §12: Acceptance criteria updated — **no paper scan upload** (per decision 4.5); replaced with "record paper filing metadata"

> [!INFO] **v1.2 changes** (2026-04-19, GENERALIZE_ORG_PLAN)
> - Scope rename: `asm_collect` → `caregiver_collect`, `rpsst_view` → `org_view`; API `/api/v1/asm/` → `/api/v1/caregiver/`; handler `get_current_asm` → `get_current_caregiver`
> - NEW §5.3.3: Effect of consent withdrawal on self-measured data (hybrid patients) — withdrawal does not block patient's self write path, only affects org/caregiver visibility (see `ORG_FOUNDATION.md §8.3`)
> - Old §5.3.3 Data deletion request renumbered to §5.3.4

---

## 1. Purpose

กำหนด workflow การได้รับ **ความยินยอมตาม PDPA มาตรา 26** (ข้อมูลอ่อนไหว — ข้อมูลสุขภาพ) จากชาวบ้านที่เข้าร่วมโครงการ โดยรองรับทั้ง:

1. **Paper consent** — กระดาษเซ็นด้วยปากกา (legal defensibility สูงสุด)
2. **Digital consent** — e-signature บนมือถือ อสม.
3. **Hybrid (default, recommended)** — ใช้ทั้งคู่คู่ขนาน

**หลักการ**: Consent ต้อง **explicit, informed, granular, withdrawable, revocable**

---

## 2. Legal Framework (PDPA)

### 2.1 Relevant sections
- **มาตรา 19** — ต้องแจ้ง purposes + rights ก่อนขอ consent
- **มาตรา 20** — Consent ต้อง explicit, freely given, specific, informed
- **มาตรา 26** — ข้อมูลสุขภาพ = sensitive data, ต้อง explicit consent
- **มาตรา 30** — สิทธิ์ของ data subject (ดู/แก้/ลบ/โอน/คัดค้าน/ถอนยินยอม)
- **มาตรา 37-39** — Data controller duties (security, breach notification)

### 2.2 Consent requirements (checklist)
- [ ] Identity of controller (ชื่อ app + รพ.สต.)
- [ ] Purposes of processing (รักษา, ติดตามสุขภาพ)
- [ ] Categories of data (BP readings, identity, medical history)
- [ ] Recipients (อสม., รพ.สต., แพทย์ที่ได้รับอนุมัติ)
- [ ] Retention period (ระยะเวลาเก็บ)
- [ ] Rights of data subject (ดู/แก้/ลบ/โอน/คัดค้าน/ถอน)
- [ ] Contact for exercising rights (เบอร์/อีเมล/ที่อยู่)
- [ ] Consequences of withdrawal (ไม่กระทบการรักษาพื้นฐาน แต่อาจไม่ได้รับ proactive monitoring)

---

## 3. Consent Granularity

### 3.1 Scopes (from `ConsentScope` enum)

| Scope | Description | Required for |
|-------|-------------|-------------|
| `caregiver_collect` | ยินยอมให้ อสม. เก็บ BP + ข้อมูลพื้นฐาน | **Core** (required for pilot) |
| `org_view` | ยินยอมให้เจ้าหน้าที่ รพ.สต. เข้าถึงข้อมูล | **Core** |
| `doctor_view` | ยินยอมให้แพทย์ที่ รพ.สต. อนุมัติเข้าถึง | Optional (Phase 2) |
| `research_anonymized` | ยินยอมให้ใช้ข้อมูลเพื่อ research (ไม่ระบุตัวตน) | Optional (Phase 3) |
| `data_export_to_smart_osm` | ยินยอมให้ส่งข้อมูลไป Smart อสม. | Optional (Phase 2) |

### 3.2 Grouping at grant time
- **Recommended grouping**: core scopes (`caregiver_collect` + `org_view`) grant ด้วยกัน (1 signature, 2 records in DB)
- **Optional scopes** แต่ละรายการ = แยก signature/checkbox
- Withdrawal สามารถทำทีละ scope ได้

---

## 4. Consent Form Content

### 4.1 Required sections ในฟอร์ม (paper + digital)

#### 4.1.1 Header
- ชื่อ "แบบฟอร์มให้ความยินยอมในการเก็บรวบรวม ใช้ และเปิดเผยข้อมูลส่วนบุคคล (ข้อมูลสุขภาพ)"
- Version + date

#### 4.1.2 Identity
- ผู้เก็บข้อมูล (Data Controller): ชื่อ app, บริษัท/บุคคลรับผิดชอบ, ที่อยู่
- องค์กรที่ใช้ข้อมูล: รพ.สต. (ชื่อ + ที่อยู่)

#### 4.1.3 Data subject info
- ชื่อ-นามสกุล, เลขบัตรประชาชน (optional), เบอร์โทร, ที่อยู่

#### 4.1.4 Purposes (วัตถุประสงค์)
- ติดตามภาวะสุขภาพ (blood pressure, อาการผิดปกติ)
- เก็บเป็นประวัติเพื่อการรักษาต่อเนื่อง
- เพื่อการป้องกันและส่งต่อในกรณีฉุกเฉิน
- เพื่อการทำงานของ อสม. ในการดูแลประชาชนในพื้นที่

#### 4.1.5 Data categories (ประเภทข้อมูล)
- ข้อมูลพื้นฐาน (ชื่อ, เบอร์โทร, เลขบัตร, ที่อยู่, วันเกิด, เพศ)
- ข้อมูลสุขภาพ (ความดันโลหิต, ชีพจร, โรคประจำตัว, ยาที่ใช้)
- **ข้อมูลภาพ (เฉพาะที่จำเป็น):**
  - ลายเซ็น e-signature (เก็บถาวร เข้ารหัสใน DB)
  - รูป OCR batch ใบรายชื่อ+เครื่องวัด — **เก็บชั่วคราวเฉพาะเมื่อ OCR confidence ต่ำ** (สูงสุด 7 วัน, ลบทันทีหลัง admin ตรวจสอบ)
  - **ไม่เก็บรูปจอเครื่องวัดแบบ single** — OCR แล้วทิ้งทันที (ตามนโยบาย data minimization v1.1)
  - **ไม่เก็บรูปกระดาษ consent scan** — กระดาษ consent เก็บ physical ที่ รพ.สต. เท่านั้น

#### 4.1.6 Recipients (ผู้รับข้อมูล)
- อสม. ที่ได้รับมอบหมาย
- เจ้าหน้าที่ รพ.สต.
- (Optional) แพทย์ที่ได้รับอนุมัติ
- (Optional) ระบบของกรมสนับสนุนบริการสุขภาพ

#### 4.1.7 Retention (ระยะเวลาเก็บ)
- ข้อมูลสุขภาพ: 10 ปีตามมาตรฐานเวชระเบียน
- Consent records: 10 ปีหลัง withdrawal
- รูป OCR raw: 30 วันหลัง process
- Audit logs: 2 ปี

#### 4.1.8 Rights (สิทธิ์ของเจ้าของข้อมูล)
- สิทธิ์ขอเข้าถึง
- สิทธิ์ขอแก้ไข
- สิทธิ์ขอลบ
- สิทธิ์ขอโอน
- สิทธิ์คัดค้าน
- สิทธิ์ถอนยินยอม (effective ทันที, ไม่ retroactive ต่อข้อมูลที่ process ไปแล้ว)

#### 4.1.9 Contact
- เบอร์ / อีเมล / ที่อยู่ สำหรับ data subject request
- DPO contact (ถ้ามี)

#### 4.1.10 Consequences of withdrawal
- ไม่สามารถใช้ระบบติดตามผ่าน อสม. ได้
- ข้อมูลที่มีอยู่จะถูก anonymize หรือ delete ตามคำขอ
- ไม่กระทบการรักษาที่ รพ.สต. โดยตรง

#### 4.1.11 Signature area
- ลายมือชื่อเจ้าของข้อมูล + วันที่
- ลายมือชื่อพยาน (อสม.) + วันที่
- (Optional) พิมพ์ลายนิ้วมือ

### 4.2 Granular consent checkboxes

แยก checkboxes สำหรับแต่ละ scope ใน form:

```
☐ ข้าพเจ้ายินยอมให้ อสม. และ รพ.สต. เก็บ ใช้ และรักษาข้อมูลสุขภาพของข้าพเจ้า
   เพื่อการดูแลสุขภาพตามวัตถุประสงค์ข้างต้น                    [caregiver_collect + org_view - REQUIRED]

☐ ข้าพเจ้ายินยอมให้เปิดเผยข้อมูลแก่แพทย์ที่ได้รับอนุมัติเพื่อ
   การรักษาและปรึกษา                                         [doctor_view - OPTIONAL]

☐ ข้าพเจ้ายินยอมให้ใช้ข้อมูลเพื่อการวิจัยและพัฒนาระบบบริการสุขภาพ
   โดยทำให้ข้อมูลเป็นแบบไม่ระบุตัวตน                          [research_anonymized - OPTIONAL]

☐ ข้าพเจ้ายินยอมให้ส่งข้อมูลออกไปยังระบบของกรมสนับสนุนบริการสุขภาพ
   (Smart อสม.) เพื่อการรายงาน                               [data_export_to_smart_osm - OPTIONAL]
```

---

## 5. Consent Workflow — Paper + Digital Hybrid

### 5.1 Initial consent collection (first visit)

**Actor**: อสม. ไปพบชาวบ้านครั้งแรก (introduction visit)

**Pre-condition**: 
- ชาวบ้านถูก admin สร้างบัญชีใน system แล้ว
- Care assignment ผูก อสม. → ชาวบ้านแล้ว
- อสม. login PWA แล้ว มีรายชื่อชาวบ้านที่ต้องไปเยี่ยม

**Flow**:

```
Step 1 — Approach & explain
  อสม. เยี่ยมชาวบ้านที่บ้าน
  อธิบาย:
    - ใครคือ อสม., โครงการคืออะไร
    - จะเก็บข้อมูลอะไรบ้าง + ใช้ทำอะไร
    - สิทธิ์ของชาวบ้าน
  (อสม. มี flashcard/สคริปต์ให้อ่านประกอบ)

Step 2 — Paper consent
  อสม. ยื่น consent form กระดาษ 2 ชุด (ชาวบ้านเก็บ 1, อสม. เก็บ 1)
  ชาวบ้านอ่าน (หรือ อสม. อ่านให้ฟังถ้าชาวบ้านอ่านไม่ออก)
  ติ๊ก checkboxes ที่ต้องการ (core = required, optional = เลือกได้)
  ชาวบ้านเซ็นชื่อ + วันที่ (หรือพิมพ์ลายนิ้วมือถ้าอ่านเขียนไม่ได้)
  อสม. เซ็นเป็นพยาน + วันที่

Step 3 — Digital capture (ใน PWA)
  อสม. เปิด PWA → Patient → "บันทึก consent"
  Flow in app:
    a) Confirm patient identity (photo of patient? or just name confirmation)
    b) Show consent summary on screen (Thai, อ่านให้ชาวบ้านฟังซ้ำได้)
    c) Granular checkboxes (mirror paper form)
    d) Digital signature (ชาวบ้านแตะนิ้ว/ปากกาบนจอ)
    e) GPS captured (device location at consent time)
    f) Timestamp captured
    g) Submit to backend
    
    Note: ไม่ถ่ายรูปฟอร์มกระดาษ upload เข้าระบบ (data minimization)
    ลายเซ็นดิจิทัลใน DB = primary digital evidence เพียงพอตามกฎหมาย

Step 4 — Storage & confirmation
  Backend:
    - สร้าง consent_records 1 row ต่อ scope ที่ selected
    - Link ทุก records กับ digital signature + GPS + timestamp
    - Audit event: consent_grant (ต่อ scope)
  PWA:
    - แสดง confirmation หน้าจอ
    - อสม. ส่งใบกระดาษ 1 ชุด ให้ชาวบ้านเก็บไว้
    - อสม. เก็บใบกระดาษอีก 1 ชุด นำกลับ รพ.สต. (physical backup)

Step 5 — Admin physical filing (same day or next)
  Admin:
    - รับใบกระดาษ consent จาก อสม.
    - เก็บใน **ตู้ล็อกเอกสารที่ รพ.สต.** จัดเรียงตาม patient_id หรือ date
    - ใน admin web: บันทึกว่ากระดาษถูกเก็บแล้ว (checkbox: "paper_filed_at: timestamp, location: filing cabinet A")
    - **ไม่ scan/upload รูปกระดาษเข้าระบบ** (เพื่อ privacy + ลด attack surface)
    - กระดาษ = physical backup สำหรับ legal defensibility หากมี dispute
    - Retention: 10 ปีตามกฎหมาย (physical), หลังจากนั้น shred + certificate
```

### 5.2 Consent update (version change)

**Trigger**: Privacy Policy หรือ ToS มี version ใหม่ + consent scope เดิมยังใช้ได้

**Flow**:
1. Backend: เมื่อ admin push version ใหม่ของ consent form, ทำ notification ไป อสม.
2. อสม. เข้าเยี่ยมชาวบ้าน (ในรอบปกติ)
3. อธิบายการเปลี่ยนแปลง (diff highlighted)
4. ชาวบ้าน re-consent (checkboxes + signature ใหม่)
5. Old consent → status = `superseded`, new consent → status = `active`
6. Paper form ใหม่ (ถ้ามีการเปลี่ยน) เซ็นเพิ่ม
7. Both forms (old + new) เก็บใน archive

### 5.3 Consent withdrawal — ชาวบ้านขอถอน

#### 5.3.1 Channel options
- **In-person** — ชาวบ้านแจ้ง อสม. หรือไป รพ.สต. โดยตรง (MVP primary channel)
- **Phone call** — โทร รพ.สต.
- **Letter** — เขียนจดหมาย
- **Future**: self-service ผ่าน app (ถ้า upgrade เป็น self_managed)

#### 5.3.2 Flow (รพ.สต. admin-initiated)

```
Step 1 — Receive request
  Admin รับ request จากช่องทางใด ๆ
  Verify identity ของ requester:
    - ถ้ามาเอง: เลขบัตรประชาชน + confirmation questions
    - ถ้าโทร: callback เบอร์ที่ลงทะเบียน
    - ถ้าจดหมาย: signature match + เลขบัตรแนบ

Step 2 — Record request
  Admin web → Patient → Consent tab
  Click "Withdraw consent"
  เลือก scope ที่ต้องการถอน (บางส่วน หรือทั้งหมด)
  กรอกเหตุผล (optional, แต่ควรมี)
  กรอกช่องทางที่รับ request

Step 3 — Confirm with patient
  ระบบสร้างเอกสารยืนยัน (ให้ชาวบ้านเซ็น ถ้าเป็นไปได้)
  ถ้าไม่เซ็นได้: admin รับรอง + บันทึก

Step 4 — Apply withdrawal
  consent_records ที่ถอน → status = withdrawn, withdrawn_at = now
  Backend effects:
    - ถ้า caregiver_collect ถอน: อสม. ไม่สามารถสร้าง reading ใหม่ได้ (block API)
    - ถ้า org_view ถอน: admin ยังดูได้ (retention) แต่ไม่ create ใหม่
    - ถ้า all ถอน: data subject อาจขอ delete เพิ่ม
  Audit: consent_withdraw

Step 5 — Notification
  Notify อสม. ที่ดูแล patient นี้ (ผ่าน Telegram bot)
  Notify patient (ถ้ามีช่องทาง)
  ระบบ suggest: "ชาวบ้าน X ถอน consent, พิจารณา delete data?"
```

#### 5.3.3 Effect on self-measured data (hybrid patients) (v1.2 new)

สำหรับ patient ที่เป็น `account_type=hybrid` และมี readings ที่วัดเอง (`measured_by_user_id IS NULL`, `measurement_context=self_home`) — การถอน consent ส่งผลดังนี้:

| Scope withdrawn | Effect on self-measured data |
|----------------|----------------------------|
| `caregiver_collect` | Caregiver ไม่เห็น self-measured อีก (รวมถึง caregiver-measured ด้วย). Patient ยังเห็นข้อมูลตัวเอง |
| `org_view` | Org admin ไม่เห็น self-measured อีก. Patient ยังเห็นข้อมูลตัวเอง |
| Both withdrawn | Patient เห็นข้อมูลตัวเอง only. Org/caregiver ไม่เห็น. Data ยังอยู่ — ไม่ลบจนกว่าจะมี erasure request แยก (ดู §5.3.4) |

**หมายเหตุ:**
- Patient ยังใช้แอปวัดเองได้เหมือนเดิม (withdrawal ไม่ block write path ของ self endpoint)
- Readings ใหม่ที่วัดหลังถอน → `organization_id` ยังถูก populate (จาก `user.managed_by_organization_id`) แต่ org/caregiver query จะ filter ด้วย consent check — ไม่เห็นจนกว่า patient regrants consent
- ดูรายละเอียด visibility rules ใน `ORG_FOUNDATION.md §8.3.2`

#### 5.3.4 Data deletion request (follow-up after withdrawal)

หากชาวบ้านขอ **ลบข้อมูล** ด้วย (right to be forgotten — มาตรา 33):
1. Admin เริ่ม deletion flow ใน system
2. System delete:
   - BP readings (hard delete)
   - PII encrypted fields (ล้างเป็น null)
   - Photos (hard delete files)
   - User record: soft delete (is_active=false, deletion_reason="user_request")
3. Consent records: **เก็บไว้ 10 ปี** (legal obligation) แต่ anonymize PII
4. Audit logs: **เก็บไว้ 2 ปี** (mandatory)
5. Admin ออก certificate ยืนยันการลบ (PDF ลงนาม)

---

## 6. Technical Implementation

### 6.1 Database Schema — Consent Record (reference from `ORG_FOUNDATION.md`)

```python
class ConsentRecord:
    # Identity
    patient_user_id, organization_id, scope
    
    # Obtaining method
    method: "paper" | "digital_signature" | "both"  # "both" means physical paper + digital signature
    version: "1.0"
    language: "th" | "en"
    
    # Digital evidence (primary, stored in DB)
    digital_signature_data: base64 PNG (encrypted with Fernet)
    digital_signature_hash: SHA-256
    gps_latitude, gps_longitude
    witness_user_id: FK to users (อสม. ที่เป็นพยาน)
    
    # Physical paper tracking (no scan stored — just metadata)
    paper_filed_at: DateTime (nullable)       # เมื่อ admin เก็บใส่ตู้
    paper_filed_location: String (nullable)   # "ตู้ A ชั้น 2" หรือคำอธิบายที่ค้นหาได้
    paper_filed_by_user_id: FK to users (nullable)
    
    # Status
    status: active | withdrawn | expired | superseded
    granted_at, withdrawn_at, withdrawal_reason, expires_at
```

**Note:** ConsentRecord **ไม่มี** `paper_scan_file_id` เพราะไม่ digitize กระดาษ. ข้อมูลใน `paper_filed_*` เป็น metadata ช่วยให้ admin หาเอกสารกระดาษเจอในกรณีต้องใช้ (legal dispute, audit)

### 6.2 API Endpoints

#### 6.2.1 PWA (อสม.) endpoints

```
POST /api/v1/caregiver/consent/initiate
  Body: { patient_id, scopes: ["caregiver_collect", "org_view"] }
  Response: { session_id, patient_summary, consent_form_content }
  
POST /api/v1/caregiver/consent/submit
  Body: {
    session_id,
    scopes_accepted: [...],
    signature_data: "base64...",
    gps: {lat, lng},
    patient_confirmation: "verbal" | "physical_presence"
  }
  Response: { consent_record_ids: [...], summary }
  
GET /api/v1/caregiver/consent/patient/{patient_id}/active
  Returns: active consent scopes for patient
```

#### 6.2.2 Admin endpoints

```
GET /api/v1/admin/consent
  Filters: patient_id, scope, status, date_range
  
GET /api/v1/admin/consent/{id}
  Full consent detail + evidence

POST /api/v1/admin/consent/{id}/record-paper-filing
  Body: { filed_location: "ตู้ A ชั้น 2", filed_at?: timestamp, notes? }
  (Records that the physical paper has been filed; no image uploaded)
  
PATCH /api/v1/admin/consent/{id}/withdraw
  Body: {
    reason,
    channel: "in_person" | "phone" | "letter",
    verification_method,
    verified_by_user_id (admin)
  }
  
POST /api/v1/admin/consent/patient/{patient_id}/data-deletion
  Body: { confirm: true, certificate_required: true }
  Response: { deletion_certificate_pdf_url }
```

### 6.3 Middleware — Consent Enforcement

```python
# app/middleware/consent_check.py

async def check_active_consent(
    patient_user_id: int,
    required_scope: ConsentScope,
    as_of: datetime = None
) -> bool:
    """Check if patient has active consent for the given scope."""
    as_of = as_of or datetime.utcnow()
    
    consent = await db.query(ConsentRecord).filter(
        ConsentRecord.patient_user_id == patient_user_id,
        ConsentRecord.scope == required_scope,
        ConsentRecord.status == ConsentStatus.active,
        ConsentRecord.granted_at <= as_of,
        or_(
            ConsentRecord.expires_at.is_(None),
            ConsentRecord.expires_at > as_of
        )
    ).first()
    
    return consent is not None


# Usage in endpoint
@router.post("/caregiver/readings")
async def create_reading_for_patient(
    reading_data: ReadingCreate,
    current_user: User = Depends(get_current_caregiver)
):
    # Check consent
    if not await check_active_consent(reading_data.patient_id, ConsentScope.caregiver_collect):
        raise HTTPException(403, "Patient has not consented to caregiver data collection")
    
    # Check care assignment
    if not await is_caregiver_of(current_user.id, reading_data.patient_id):
        raise HTTPException(403, "Not assigned to this patient")
    
    # Proceed...
```

### 6.4 Consent Versioning

```python
# Consent form versions are tracked explicitly

CURRENT_CONSENT_VERSION = "1.0"
CURRENT_CONSENT_FORM_TH = """..."""  # Full text
CURRENT_CONSENT_FORM_EN = """..."""

# On version bump:
# 1. Update CURRENT_CONSENT_VERSION
# 2. Existing active consents -> still valid (no invalidation)
# 3. On next visit by อสม., check if any consents are outdated:
#    - If gap is material (added new scope, changed purposes) -> prompt re-consent
#    - If cosmetic only -> log notification but don't block
```

### 6.5 Digital Signature Handling

#### 6.5.1 Capture (PWA)
- HTML canvas element
- Touch events: pointerdown, pointermove, pointerup
- Library suggestion: `signature_pad` (npm)
- On save: export as PNG base64
- Minimum signature complexity: require > 5 strokes to prevent blanks

#### 6.5.2 Storage
- Store as base64 string in `consent_records.digital_signature_data`
- SHA-256 hash of signature bytes: store in `digital_signature_hash`
- Signature is PII; encrypt with Fernet before insert (consistent with other PII)

#### 6.5.3 Display (Admin web)
- Render base64 as `<img src="data:image/png;base64,..." />`
- Audit log every view: `consent_view` with target_user_id

---

## 7. Paper Consent Form — Design Spec

### 7.1 Format
- **Size**: A4 portrait
- **Pages**: 2 pages (consent content + signature)
- **Font**: Thai Sarabun New 14pt or Noto Sans Thai 12pt
- **Printing**: Plain white paper, carbon copy (2 copies)

### 7.2 Layout

**Page 1 (Content)**:
- Header with logo + title
- Sections 4.1.2 through 4.1.10 (identity, data subject, purposes, etc.)
- Footer: version, page 1 of 2

**Page 2 (Granular consent + Signature)**:
- Granular checkboxes (section 4.2)
- Signature area:
  - ชาวบ้าน: ลายมือชื่อ + วันที่ + (อสม. ช่วยเขียนเลขบัตรประชาชน ถ้าชาวบ้านไม่สะดวก)
  - อสม.: ลายมือชื่อ (พยาน) + วันที่ + เลขบัตรประชาชน อสม.
  - Optional: พิมพ์ลายนิ้วมือ (ถ้าชาวบ้านเซ็นไม่ได้)
- Footer: page 2 of 2

### 7.3 Physical handling (no digital scan)

- กระดาษเก็บ **physical เท่านั้น** ที่ รพ.สต. ในตู้ล็อกเอกสาร
- Admin บันทึกใน system ว่า "เก็บแล้วที่ตู้ X" (metadata only, no image upload)
- Retention: 10 ปี (ตาม legal requirement)
- หลัง 10 ปี: shred + certificate of destruction
- Primary digital evidence = digital signature + GPS + timestamp + audit log ใน DB

### 7.4 QR Code (optional, for cross-reference)
- QR บนฟอร์ม → link ไปยัง consent_id ใน admin web (สำหรับ scan back-reference ตอน file/retrieve)
- Pre-generate เลข consent_id ก่อนพิมพ์?
  - **Option A**: Pre-generate + print (admin print ฟอร์มต่อคนไข้)
  - **Option B**: Generic form + admin link ภายหลังผ่าน filing metadata
  - **Recommend**: Option B (MVP ง่ายกว่า)

### 7.5 Language
- **Primary**: Thai
- **Secondary**: English (for non-Thai residents, Phase 2)

### 7.6 Readability
- Reviewed by someone ที่ไม่คุ้น legal jargon
- Plain language summary at top: "สรุปสั้น ๆ คือ..."
- Font size แบบผู้สูงอายุอ่านได้ (14pt minimum)

---

## 8. Edge Cases & Exceptions

### 8.1 Patient cannot read/write
- **Handling**: อสม. อ่านให้ฟัง, ชาวบ้านพิมพ์ลายนิ้วมือ, อสม. เซ็นเป็นพยาน
- **Evidence**: ใน consent_record metadata มี `{"cannot_read_write": true, "signed_by_fingerprint": true}`

### 8.2 Patient is minor (under 20 years)
- Pilot ไม่ครอบคลุมเด็ก (out of scope MVP)
- Phase 2 ถ้าจำเป็น: ต้อง guardian consent + child assent > 7 ปี

### 8.3 Patient has cognitive impairment
- ต้อง legal guardian consent
- อสม. + admin ตรวจสอบ guardianship documents
- Evidence: `{"guardian_consent": true, "guardian_user_id": ..., "guardian_relation": "..."}`

### 8.4 Emergency situation
- ถ้าชาวบ้านหมดสติ/ฉุกเฉิน: อาจไม่ต้องรอ consent (PDPA ม. 24 (5) — vital interest)
- บันทึก `consent_basis = "vital_interest"` + ขอ consent ภายหลังเมื่อฟื้น
- **Note**: pilot scope = routine monitoring, unlikely scenario แต่ document ไว้

### 8.5 Patient พูดภาษาไทยไม่ได้ / ชาติพันธุ์
- จำเป็นต้องมีล่าม
- Consent form ภาษาอื่น ๆ (future)
- Evidence: `{"interpreter_used": true, "interpreter_name": ...}`

### 8.6 Patient ปฏิเสธ consent
- อสม. respect decision, ไม่ pressure
- บันทึก `consent_declined` record (not full consent_record, but log ว่าได้ offer แล้ว)
- ไม่สามารถเก็บข้อมูลได้
- Remove จาก care_assignment หรือ mark as `assignment_inactive`

### 8.7 Patient เสียชีวิต
- Data retention ต่อ (per legal requirement 10 ปี)
- ญาติขอดูข้อมูล: ต้องมี proof of relationship + court order ในบางกรณี
- Process ใน admin web: "Deceased" status + handling procedure

---

## 9. Data Subject Rights Workflow

### 9.1 Right to Access (ม. 30)
- ช่องทาง: in-person, phone, letter
- Admin verify identity
- Generate "data subject summary" report (PDF)
- Deliver: email, printed copy
- SLA: 30 วัน

### 9.2 Right to Rectification (ม. 35)
- ชาวบ้านแจ้งข้อมูลผิด
- Admin แก้ไขใน system
- Audit event: `user_update` with metadata `{requested_by: "data_subject"}`
- Confirm correction to data subject

### 9.3 Right to Erasure (ม. 33)
- See Section 5.3.3

### 9.4 Right to Portability (ม. 31)
- Generate machine-readable export (JSON/CSV)
- Include: profile, BP readings, consent records
- Exclude: audit logs (internal), others' data (in batch images)
- Deliver: signed download URL + expiry

### 9.5 Right to Object (ม. 32)
- Patient object เฉพาะ activity ไม่ใช่ทั้ง blanket
- Handled case-by-case by admin

### 9.6 Right to Withdraw Consent
- See Section 5.3

---

## 10. Audit & Compliance

### 10.1 Required audit events

Every consent-related action MUST be logged:
- `consent_grant` (per scope)
- `consent_withdraw` (per scope)
- `consent_update` (version upgrade)
- `consent_view` (admin/อสม. reviews consent record)
- `data_subject_request` (access/erasure/etc.)

### 10.2 Compliance reports

Admin can generate these reports:
- All active consents by scope
- Consent granted/withdrawn in period
- Data subject requests fulfilled (SLA tracking)
- Consent version distribution (who is on which version)

### 10.3 Retention of consent records
- **Active consents**: indefinite (while patient is active)
- **Withdrawn consents**: 10 ปี หลัง withdrawal (prove that consent was obtained + later withdrawn)
- **Deleted patient**: consent records anonymized (remove PII links) but kept for legal

---

## 11. Out of Scope (Phase 2+)

- Self-service consent (patient withdraws via own app)
- Consent for minors (under 20)
- Multi-language consent forms (EN only in Phase 2)
- Automated consent expiry reminders
- Biometric auth for consent (face recognition, voice)
- Video recorded consent explanation (for vulnerable groups)
- Blockchain-anchored consent hashes (for tamper evidence)

---

## 12. Acceptance Criteria

### Functional
- [ ] อสม. สามารถ initiate consent ใน PWA
- [ ] อสม. capture digital signature + GPS + timestamp
- [ ] **ไม่** upload รูปกระดาษ consent เข้าระบบ (physical paper เก็บที่ รพ.สต. เท่านั้น — v1.1 decision 4.5)
- [ ] Admin สามารถ review, record paper filing metadata, withdraw consent
- [ ] Granular scopes grant แยกกันได้
- [ ] Withdrawal has correct downstream effects (block writes, etc.)
- [ ] Data subject request endpoints work end-to-end
- [ ] Deletion certificate PDF generate ได้

### Compliance
- [ ] 100% of readings associated with active `caregiver_collect` consent
- [ ] Audit log complete for all consent events
- [ ] Retention policies enforced (auto-delete jobs)
- [ ] Data subject rights SLA < 30 วัน

### UX
- [ ] Digital signature capture works on Android + iOS
- [ ] Paper form readable (tested with elderly users)
- [ ] อสม. training material includes consent flow practice

---

**End of CONSENT_FLOW_SPEC.md**
