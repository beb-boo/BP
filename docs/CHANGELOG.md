# Legal Documents Changelog

ประวัติการเปลี่ยนแปลงของเอกสารทางกฎหมายสำหรับ BP Monitor

---

## Version 2.0 — 2026-04-18 (draft)

### Scope
ปรับปรุงเพื่อรองรับ **ระบบ v2: ASM/รพ.สต. Organization Support** — ขยายจากระบบ personal ไปรองรับอาสาสมัครสาธารณสุข (อสม.) และ โรงพยาบาลส่งเสริมสุขภาพตำบล (รพ.สต.)

### Changed Files

#### `privacy-policy.md` v1.0 → v2.0 (major update)
- **เพิ่ม Joint Controller concept** — เรา + รพ.สต. เป็นผู้ควบคุมข้อมูลร่วม (ม.24 PDPA)
- **เพิ่มข้อมูลประเภทใหม่**:
  - ข้อมูลของ อสม. (เบอร์โทร, บทบาท, care assignments)
  - ข้อมูลองค์กร (รพ.สต. profile)
  - Digital signature (e-signature)
  - GPS coordinates
  - OCR ภาพใบรายชื่อ + เครื่องวัด (ชั่วคราว, max 7 วัน)
- **เพิ่ม granular consent scopes** — `asm_collect`, `rpsst_view`, `doctor_view`, `research_anonymized`
- **อัปเดต retention periods** ให้สอดคล้องมาตรฐานเวชระเบียน (10 ปี)
- **เพิ่ม section สิทธิของ proxy-managed patients** (ชาวบ้านที่ไม่ได้ล็อกอินเอง)
- **อัปเดตการเปิดเผยข้อมูล** — เพิ่ม อสม. และ รพ.สต. admin
- **เพิ่ม tenant isolation + audit logging** ในมาตรการความปลอดภัย

#### `terms-of-service.md` v1.0 → v2.0 (major update + split)
- **Split** — แยกเป็น 2 ไฟล์:
  - `terms-of-service.md` — สำหรับ individual users (self_managed, doctor, อสม.)
  - `org-terms-of-service.md` — ใหม่ สำหรับ admin ขององค์กร (รพ.สต.)
- **เพิ่ม section หน้าที่ อสม.** (5.4) — จรรยาบรรณ, การใช้งาน, การเก็บ consent
- **อัปเดตการลงทะเบียน** (5.1) — แยก flow ตามบทบาท (self/อสม./doctor/proxy)
- **เพิ่ม section ผู้ใช้ผ่านองค์กร** (6.3) — joint controller + portability + ย้าย รพ.สต.

#### `consent-and-implementation-guide.md` v1.0 → v2.0 (major update)
- **เพิ่ม Consent Flows overview** — แยก 4 flows: self, proxy, org, OCR batch
- **เพิ่ม Proxy-managed flow** (detailed) — paper + digital hybrid, e-signature, GPS, witness
- **เพิ่ม Granular scopes table** + withdrawal matrix
- **เพิ่ม Edge cases** — illiterate, cognitive impairment, non-Thai, deceased, refusal
- **อัปเดต DB schema reference** → ชี้ไปที่ [[ORG_FOUNDATION]]
- **เพิ่ม Evidence chain documentation** (digital + physical)

### New Files

#### `org-terms-of-service.md` v1.0 (NEW)
- ข้อตกลงสำหรับองค์กรที่ใช้ BP Monitor
- Joint Controller model (ม.24 PDPA)
- Admin responsibilities (consent collection, data accuracy, breach notification)
- Ownership transfer flow
- Subscription / termination
- Indemnification

### Archived

- `privacy-policy-v1.md` (v1.0, self-managed only)
- `terms-of-service-v1.md` (v1.0, individual only)
- `consent-and-implementation-guide-v1.md` (v1.0)

### Migration Notes

- **v1 users** (self_managed) จะเห็น v2 policies ตอน login ครั้งต่อไป → ต้อง re-accept (30-day grace period)
- **Historical consent records** ยังอ้างอิง v1 version (legally valid ณ เวลานั้น)
- **New users** (อสม., admin, proxy patient) เห็น v2 ตั้งแต่แรก
- ใน code: `CURRENT_PRIVACY_POLICY_VERSION = "2.0"`, `CURRENT_TERMS_VERSION = "2.0"`, `CURRENT_ORG_TERMS_VERSION = "1.0"`, `CURRENT_CONSENT_FORM_VERSION = "2.0"`

### Legal Review Status

- [ ] Draft complete (2026-04-18)
- [ ] PDPA consultant review (external)
- [ ] Thai language expert review
- [ ] Stakeholder review (รพ.สต. pilot partner)
- [ ] Published

---

## Version 1.0 — 2026-04-03

### Initial Release

- `privacy-policy.md` v1.0 — สำหรับ self-managed users
- `terms-of-service.md` v1.0 — สำหรับ individual users (patient, doctor)
- `consent-and-implementation-guide.md` v1.0 — template consent สำหรับ OCR + doctor access

---

**Note:** รายละเอียดแผน migration จาก v1 → v2 ดูใน `plan/v2-asm-org-support/LEGACY_DOCS_MIGRATION.md`
