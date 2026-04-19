# MVP Pilot Scope — BP Monitor for อสม. / รพ.สต.

> **Status:** Draft v1 — for review before implementation
> **Last updated:** 2026-04-18
> **Owner:** Pornthep
> **Related docs:** `ORG_FOUNDATION.md`, `ADMIN_WEB_SPEC.md`, `CAREGIVER_PWA_SPEC.md`, `docs/pdpa/PDPA_COMPLIANCE.md`

---

## 1. Purpose

ขยาย BP Monitor จากระบบ personal (ชาวบ้านวัด/บันทึกเอง) เป็นระบบที่รองรับการทำงานของ **อาสาสมัครสาธารณสุขประจำหมู่บ้าน (อสม.)** ร่วมกับ **โรงพยาบาลส่งเสริมสุขภาพตำบล (รพ.สต.)** ในการเก็บข้อมูลความดันโลหิตของประชาชนที่ไม่มีเครื่องวัดเอง

กลยุทธ์ใช้แนวทาง "ป่าล้อมเมือง" — เริ่มจาก pilot เดียวเพื่อ validate workflow จริง แล้วขยายตามลำดับ คู่ขนานกับการ top-down ผ่านกรมสนับสนุนบริการสุขภาพ

---

## 2. Pilot Details

| ข้อมูล | รายละเอียด |
|-------|----------|
| Location | ตำบลเมืองเก่า อำเภอเมือง จังหวัดสุโขทัย |
| รพ.สต. | 1 แห่ง |
| จำนวน อสม. | 2 คน |
| จำนวนครัวเรือนเป้าหมาย | ~20 ครัวเรือน (~30-40 คน) |
| ระยะเวลา pilot | 3-6 เดือน |
| Launch target | TBD (หลังจากเอกสาร planning + coding + UAT) |
| Deployment | Cloud ในประเทศไทย (จะเลือก vendor ภายหลัง) |

### Pilot-specific assumptions
- สัญญาณโทรศัพท์มือถือในพื้นที่ดี (ไม่ต้องทำ offline-first ใน MVP)
- ชาวบ้านส่วนใหญ่ไม่มีเครื่องวัดความดันเอง — อสม. พกเครื่องวัดไปวัดให้ที่บ้าน
- อสม. ใช้สมาร์ทโฟนส่วนตัวของตัวเอง (BYOD)
- อสม. คุ้นเคย LINE แต่**ไม่เคยใช้ Telegram** — ต้อง onboarding flow ที่เรียบง่าย
- รพ.สต. มี PC/Laptop ที่ใช้ browser ได้
- ชาวบ้านที่เป็นกลุ่มเป้าหมาย อายุ 35+ ปี มีความเสี่ยงหรือเป็นโรคความดันโลหิตสูง

---

## 3. Personas

### 3.1 รพ.สต. Admin (1 คน)
- **Device:** PC/Laptop at รพ.สต.
- **Channel:** Web dashboard
- **Login:** phone + password (primary) หรือ email + password (secondary)
- **Needs:**
  - สร้าง/จัดการบัญชี อสม. ในความรับผิดชอบ
  - สร้าง/จัดการบัญชีชาวบ้าน (proxy-managed)
  - ผูก อสม. กับชาวบ้าน (care assignment)
  - อนุมัติ/บันทึก consent ของชาวบ้าน
  - ดู BP readings ทั้งหมดใน รพ.สต. + dashboard แนวโน้ม
  - Export รายงาน (CSV minimum)
  - ดู audit log

### 3.2 อสม. (2 คน)
- **Device:** สมาร์ทโฟน (Android ส่วนใหญ่)
- **Channel:** PWA (Progressive Web App) + Telegram bot (notification + OTP delivery)
- **Login:** phone + Telegram OTP (primary), fallback = ขอ OTP ผ่าน bot ตัวเอง
- **Needs:**
  - เห็นรายชื่อครัวเรือน/บุคคลที่ตัวเองรับผิดชอบ (~10 คน/คน)
  - เลือกคนไข้ → กรอกผลวัด (พิมพ์เอง) หรือ ถ่ายรูป OCR
  - ถ่ายรูป **ใบรายชื่อ + เครื่องวัด** ทีเดียวเพื่อ auto-attribute
  - ดู history ของคนไข้
  - รับ notification "วันนี้ต้องไปวัด X คน" ผ่าน Telegram
  - ส่ง/ดูสถานะการสัญจรลงพื้นที่

### 3.3 ชาวบ้าน / Proxy-managed Patient (~30-40 คน)
- **Mode ใน MVP:** proxy-managed (ไม่ล็อกอินเอง)
- **Consent:** กระดาษ + digital e-signature (ม.26 explicit consent)
- **Rights:**
  - ขอดูข้อมูลตัวเองได้ผ่าน รพ.สต. admin
  - ขอแก้/ลบได้
  - ถอนความยินยอมได้
- **Upgrade path:** ถ้าได้สมาร์ทโฟน + อยากดูข้อมูลเอง → upgrade เป็น `self_managed` หรือ `hybrid` ได้

### 3.4 Personas ที่ **ไม่ได้** อยู่ใน pilot MVP
- แพทย์ / พยาบาล (เลื่อนไป Phase 2)
- กรมสนับสนุนบริการสุขภาพ / สสอ. / สสจ.
- ชาวบ้านที่มีเครื่องวัดเอง (ใช้ flow เดิม ไม่กระทบ)

---

## 4. In Scope (MVP Features)

### 4.1 Authentication & Onboarding

#### 4.1.1 Pairing Code (อสม. onboarding — one-time)
- รพ.สต. admin สร้างบัญชี อสม. → ระบบ generate 6-digit pairing code, TTL 15 นาที
- Admin ส่ง pairing code ให้ อสม. ผ่านช่องทางใดก็ได้ (LINE, SMS, กระดาษ)
- อสม. เปิด Telegram → ค้น bot → `/start <pairing_code>`
- Bot verify code → ผูก `telegram_id` กับ user record → ตอบว่าสำเร็จ

#### 4.1.2 Login Flow (ทุกครั้งที่เข้า PWA)
- อสม. เปิด PWA → กรอกเบอร์โทร → กด "ขอรหัส OTP"
- Backend gen 6-digit OTP, TTL 5 นาที, rate limit 3 ครั้ง/15 นาที
- ส่ง OTP ผ่าน Telegram bot (bot send message ไปหา `telegram_id` ที่ pair ไว้)
- อสม. กรอก OTP ใน PWA → login สำเร็จ → JWT token (TTL 24 ชม.)
- **Fallback:** ถ้า OTP ส่งไม่ถึง (ลบ bot, ลบ chat) อสม. พิมพ์ `/otp` ใน bot ตัวเอง bot ตอบ OTP ปัจจุบันกลับมา (user-initiated bypass anti-spam)

#### 4.1.3 Admin Login
- Phone + password (primary) or email + password (secondary)
- 2FA optional ใน MVP (แนะนำให้เปิด ใช้ TOTP)
- Password requirements: min 8 chars, 1 upper, 1 lower, 1 digit
- Rate limit: 5 attempts / 15 min per account

#### 4.1.4 Logout & Session
- PWA JWT TTL: 24 ชม. แล้ว re-OTP
- Admin web session TTL: 8 ชม.
- Force logout all sessions endpoint

### 4.2 Admin Web Dashboard (รพ.สต. admin)

#### 4.2.1 ผู้ใช้จัดการ
- สร้าง อสม. (ชื่อ, เบอร์โทร, เลขบัตรประชาชน optional)
- Generate pairing code
- ปิด/เปิด บัญชี อสม. (suspend)
- สร้างบัญชีชาวบ้าน (proxy-managed): ชื่อ, เบอร์โทร optional, เลขบัตรประชาชน, วันเกิด, เพศ, ที่อยู่, โรคประจำตัว
- Edit / deactivate ชาวบ้าน
- Import ชาวบ้านจาก CSV (optional, ดีมีไว้)

#### 4.2.2 Care Assignment
- ผูก อสม. x กับ ชาวบ้าน y (many-to-many แต่ default = 1 อสม. ต่อ 1 ชาวบ้าน)
- Bulk assignment (เลือก อสม. 1 คน + เลือกชาวบ้านหลายคน)
- Transfer assignment (ย้ายความรับผิดชอบ)
- End assignment (มี effective date)

#### 4.2.3 Consent Management
- ดู consent records ของชาวบ้านแต่ละคน
- Upload รูปเอกสาร consent กระดาษ (ถ่ายรูปแล้ว upload)
- Mark consent as active/withdrawn
- Consent granular scopes: `caregiver_collect`, `org_view`, `doctor_view` (+ future: `research_anonymized`)
- Admin ยอมรับ ToS for Organizations ตอน onboard + ทุกครั้งที่มี version update

#### 4.2.4 BP Data Review
- รายการ BP readings ทั้งหมดใน รพ.สต. (filter by อสม., by patient, by date, by severity)
- Detail view: chart + history ของชาวบ้านแต่ละคน
- Alert list: คนไข้ที่ค่า > threshold (เช่น systolic > 160 ติดกัน 3 ครั้ง)
- Edit/delete BP reading (มี audit log)
- Review queue: OCR readings ที่ confidence ต่ำ + unknown patient

#### 4.2.5 Report & Export
- Dashboard: จำนวนชาวบ้านทั้งหมด, readings สัปดาห์/เดือน, จำนวนคนความดันสูง
- Export CSV: BP readings ช่วงเวลาที่เลือก (filter patient / อสม.)
- Export consent records (audit trail สำหรับ PDPA)
- (Future) Export ตาม format 43 แฟ้ม

#### 4.2.6 Audit Log Viewer
- ค้นหา: by user, by action type, by date range
- Export CSV

### 4.3 อสม. PWA

#### 4.3.1 Home / Dashboard
- นับจำนวนชาวบ้านในความรับผิดชอบ
- จำนวน readings ที่ส่งในสัปดาห์
- คนที่ยังไม่ได้วัดในเดือนนี้ (reminder list)
- Quick action: "บันทึกผลวัดใหม่"

#### 4.3.2 Patient List
- รายชื่อชาวบ้านในความรับผิดชอบ
- Search (ชื่อ, เบอร์บ้าน)
- Filter (เพศ, ช่วงอายุ, โรคประจำตัว, last reading > N วัน)
- Tap → patient detail

#### 4.3.3 Patient Detail
- ข้อมูลพื้นฐาน (name masked/unmasked ตาม policy, age, gender, โรคประจำตัว)
- BP reading history (list + chart)
- ปุ่ม "บันทึกผลวัดใหม่"

#### 4.3.4 Quick Entry (พิมพ์เอง)
- เลือก patient (หรือมาจาก patient detail)
- พิมพ์ systolic, diastolic, pulse
- เลือก measurement context (ที่บ้าน / ที่ รพ.สต. / อื่น ๆ)
- Timestamp: default = ตอนนี้, edit ได้
- Note (optional)
- Submit → server validate → save

#### 4.3.5 Photo OCR Entry (คนเดียว)
- เลือก patient
- ถ่ายรูปจอเครื่องวัด (เปิดกล้อง capture=environment)
- Preview → retake ได้
- Upload → Gemini OCR → pre-fill systolic/diastolic/pulse + timestamp (ถ้าอ่านจอได้)
- อสม. review + confirm → save

#### 4.3.6 Batch Photo OCR (ใบรายชื่อ + เครื่องวัด)
- ดูรายละเอียดใน `CAREGIVER_PWA_SPEC.md` section "Batch OCR"
- Sub-feature ของ Photo OCR Entry
- ไม่ auto-submit ใน MVP — pre-fill + confirm

#### 4.3.7 Reading History (ของ อสม. ตัวเอง)
- รายการ readings ที่ อสม. บันทึกล่าสุด
- แก้ไข/ลบ ภายใน 24 ชม. (มี audit)

#### 4.3.8 Notification Inbox (via Telegram bot)
- "วันนี้ต้องไปวัด X คน: สมชาย, สมหญิง, ..."
- "ชาวบ้าน X ค่าความดันสูงติด 3 ครั้ง ควรแนะนำพบแพทย์"
- Bot commands: `/today`, `/alerts`, `/otp`

### 4.4 Consent Workflow (paper + digital)
- อสม. ไปเยี่ยมบ้านครั้งแรก → อ่าน consent ให้ชาวบ้านฟัง
- กรอกในแท็บเล็ต/มือถือ → ชาวบ้านแตะนิ้วเซ็น → save e-signature + GPS + timestamp
- เสริมด้วย **กระดาษ consent form ลงนามจริง** ถ่ายรูป upload เข้าระบบ (redundancy สำหรับ legal defensibility)
- ดูรายละเอียดใน `CONSENT_FLOW_SPEC.md`

### 4.5 RBAC (Role-Based Access Control)
- Roles ใน MVP: `superadmin`, `org_admin`, `caregiver`, `patient_self`, `patient_proxy`
- Future roles: `doctor`, `org_staff` (เลื่อน Phase 2)
- Permission matrix: ดู `ORG_FOUNDATION.md` section "Role Matrix"
- Middleware enforce: ทุก API check role + scope

### 4.6 Audit Log
- Event types: login, logout, view_patient (by non-owner), edit_patient, create_reading, edit_reading, delete_reading, consent_grant, consent_withdraw, care_assignment_change, user_create, user_suspend, export_data
- Fields: who (user_id), when (timestamp), what (action), target (resource_id), from_ip, user_agent, metadata (JSON)
- Retention: 2 ปี minimum (PDPA + clinical record requirement)
- ดูรายละเอียด schema ใน `ORG_FOUNDATION.md` section "Audit Log"

### 4.7 PDPA Foundation
- Consent records (granular scopes, versioned)
- Data subject request endpoint: view / export / delete (ขยายจากของเดิม)
- Breach response runbook (manual ใน MVP, automate Phase 2)
- Data retention policy ใน code (not just doc)

---

## 5. Out of Scope (Phase 2+)

| Feature | Phase | เหตุผลที่เลื่อน |
|---------|-------|--------------|
| Offline-first PWA (Service Worker + IndexedDB queue) | 2 | สัญญาณใน pilot ดี, เพิ่ม complexity สูง |
| Bulk entry non-OCR (กรอก 10 คนในฟอร์มเดียว) | 2 | OCR batch แก้ปัญหานี้แล้ว |
| Multi-รพ.สต. hierarchy (อำเภอ, จังหวัด) | 2 | Pilot = 1 รพ.สต. |
| Doctor role + telemedicine workflow | 2 | ของเดิมมี basic, expand ภายหลัง |
| สบส. / HDC / 43 แฟ้ม integration | 3 | ต้องมี MOU + requirement ราชการชัดเจนก่อน |
| Auto-submit OCR (confidence > 95%) | 2 | รอ accuracy data จาก pilot |
| Alert system (SMS/Push/Email) อัตโนมัติ | 2 | Weekly email summary พอใน MVP |
| Mobile native app (iOS/Android) | 3+ | PWA พอ ไม่ต้องขึ้น app store |
| Research/analytics export (anonymized) | 2 | ต้อง consent scope เพิ่ม |
| Multi-tenant isolation ชั้นลึก | 2 | 1 รพ.สต. ใน pilot |
| LINE LIFF as alternative entry | 3 | ทิ้งไว้ดูถ้า Telegram onboarding ไม่ work |
| Predictive model (ML) | 3+ | ต้องมีข้อมูลก่อน |

---

## 6. Success Metrics

### 6.1 Adoption metrics (measure ใน pilot)
- จำนวนชาวบ้านที่ได้ consent = ≥ 16/20 ครัวเรือน (80%)
- จำนวน BP readings ต่อชาวบ้านต่อเดือน = ≥ 4
- จำนวน active อสม. = 2/2 (ใช้ระบบอย่างน้อย 2 ครั้ง/สัปดาห์)

### 6.2 Quality metrics
- OCR accuracy (ค่าความดัน) = ≥ 95% (confirm โดย อสม.)
- OCR accuracy (ชื่อ/ลำดับคนไข้) = ≥ 98%
- Data entry error rate = ≤ 2% (edit within 24h rate)
- System uptime = ≥ 99% ใน pilot period

### 6.3 User satisfaction
- อสม. rating ≥ 4/5 ใน end-of-pilot survey
- รพ.สต. admin rating ≥ 4/5
- Qualitative: อสม. รู้สึกว่าเร็ว/ง่ายกว่า Smart อสม. (comparative question)

### 6.4 Compliance metrics
- 100% ของ readings มี consent record ที่ active
- 100% ของ cross-user data access มี audit log
- 0 PDPA incidents

---

## 7. Risk Log

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| อสม. onboard Telegram ไม่สำเร็จ | M | H | Step-by-step guide ภาพประกอบ + admin ช่วย onboard ครั้งแรก + fallback OTP via voice call |
| OCR อ่านชื่อ/เลขผิด → attribute readings ผิดคน | M | H | Pre-fill + confirm step ก่อน save, confidence threshold, log OCR output + original image (encrypted) |
| สัญญาณมือถือในบางบ้านไม่ดี | L | M | ถ่ายรูปเก็บในมือถือ upload ทีหลัง (built-in browser queue, ไม่ต้องทำ Service Worker ใน MVP) |
| ชาวบ้านไม่ยอม consent | L | H | Training อสม. วิธีอธิบาย + consent form เข้าใจง่าย ภาษาไทยชัด |
| PDPA compliance ไม่ครบ | M | H | Legal review ก่อน launch, in-app ToS + Privacy Policy เข้มข้น, consent flow ครบถ้วน |
| Admin ของ รพ.สต. ลาออก = บัญชี org ค้าง | M | M | Ownership transfer flow ใน admin web + superadmin recovery path |
| Data breach / leak | L | VH | Encryption at rest (มีอยู่), RBAC, audit log, breach runbook, incident drill |
| Cloud in-country migration ล่าช้า | M | M | เริ่ม pilot ได้บน Vercel + Neon, migrate ก่อน expand beyond pilot |
| อสม. turnover (ลาออก/ย้าย) | L | M | Admin re-assign care_assignment ได้, audit ของ อสม. คนก่อนเก็บไว้ |
| Smart อสม. ชน position กัน | H | L | Position เป็น "เสริม" ไม่แข่ง, export format compatible |

---

## 8. Dependencies

### 8.1 Technical
- Existing codebase: FastAPI backend, Next.js frontend, Telegram bot (python-telegram-bot), Gemini OCR
- PostgreSQL (Neon ปัจจุบัน → migrate to in-country cloud)
- Redis (Upstash ปัจจุบัน → migrate)
- Telegram Bot API (free)
- Gemini API (paid per token)

### 8.2 Non-technical
- **Pilot partner** — ตำบลเมืองเก่า สุโขทัย (confirmed)
- **Legal review** — ทบทวน Privacy Policy + Terms of Service (ทั้ง individual + organization) + Consent form (ต้องจ้างทนาย/ที่ปรึกษา PDPA)
- **Translation review** — consent form + ToS ภาษาไทย ต้องให้ผู้เชี่ยวชาญตรวจ
- **Training materials** — คู่มือ อสม. + admin (video + PDF)
- **Hardware** — เครื่องวัดความดัน (2 เครื่องสำหรับ อสม.), printer สำหรับใบรายชื่อ

---

## 9. Out-of-pilot Extension (สำหรับวาง roadmap)

### Phase 2 targets (หลัง pilot success)
- 5-10 รพ.สต. ในสุโขทัย
- เริ่มมี doctor role active
- Offline-first PWA
- Export format 43 แฟ้ม

### Phase 3 targets
- ขยายระดับจังหวัด (20-50 รพ.สต.)
- เข้าพบกรมสนับสนุนบริการสุขภาพ เพื่อเสนอ partnership
- Data residency migration เสร็จ
- LINE LIFF alternative (ถ้าจำเป็น)

### Long-term
- National scale (พันกว่า รพ.สต.)
- API integration กับ Smart อสม. / HDC
- Analytics / research platform (anonymized, opt-in)

---

## 10. Open Questions (ต้องตัดสินใจก่อน/ระหว่าง dev)

1. **Cloud vendor ในไทย** ที่จะ migrate ไปใช้ = ? (Internet Thailand, NT Cloud, True IDC, ฯลฯ)
2. **Legal consultant / PDPA expert** = ใครช่วย review documents?
3. **ใบรายชื่อ format** = กระดาษ A4 แนวตั้ง? แนวนอน? มีช่อง "ทำเครื่องหมาย" หรือ "ลำดับที่วัดวันนี้"? → กำหนดใน `CAREGIVER_PWA_SPEC.md`
4. **เครื่องวัด model ที่ อสม. ใช้** = ? (จอใหญ่/เล็ก, มีเวลา/ไม่มี → กระทบ OCR accuracy)
5. **Pilot launch date** = ?
6. **Budget** สำหรับ training, printer, เครื่องวัด, legal review = ?

### 10.1 Decisions made (v1)
- **Cloud for pilot:** Neon (US) + Vercel OK — migrate ก่อน scale beyond pilot
- **File storage:** PostgreSQL BYTEA ผ่าน abstraction layer (swap-ready)
- **Organization identity:** UUID (`external_id`) + optional `code` + `code_system`
- **Legal structure:** No MOU/DPA — direct in-app acceptance ของ ToS + Privacy Policy + Consent โดย admin/อสม./ชาวบ้าน

---

## 11. Acceptance Criteria สำหรับ "MVP Ready to Pilot"

ระบบจะถือว่าพร้อม pilot เมื่อผ่านทั้งหมดนี้:

### Code / Feature
- [ ] อสม. สามารถ onboard ได้สำเร็จ (pairing + Telegram OTP)
- [ ] อสม. สามารถ login PWA → ดู patient list → บันทึก BP (พิมพ์ + OCR) ได้
- [ ] Admin สามารถสร้าง อสม. + ชาวบ้าน + care assignment ได้
- [ ] Admin สามารถดู BP readings ทั้งหมดและ export CSV ได้
- [ ] RBAC enforce ใน every API endpoint ที่แตะ cross-user data
- [ ] Audit log ครอบคลุม action ทั้งหมดใน section 4.6
- [ ] OCR batch feature (ใบรายชื่อ + เครื่องวัด) ทำงานได้, confidence score shown
- [ ] Consent workflow ครบทั้งกระดาษ + digital

### Non-functional
- [ ] Response time: login < 3s, patient list < 2s, OCR < 8s (p95)
- [ ] System uptime monitoring setup
- [ ] Error tracking (Sentry หรือเทียบเท่า)
- [ ] Backup: daily DB backup, retention 30 วัน
- [ ] Security: all PII encrypted, HTTPS only, JWT rotation, rate limit active

### Legal / PDPA
- [ ] Privacy Policy (individual + organization) + Terms of Service deployed
- [ ] Consent form (กระดาษ + digital) reviewed by PDPA expert
- [ ] Admin ของ รพ.สต. pilot ยอมรับ ToS for Organizations ในแอป
- [ ] Data retention policy implemented in code (auto-delete jobs running)
- [ ] Breach response runbook documented + admin briefed
- [ ] Ownership transfer flow available (หาก admin ลาออก)

### Training
- [ ] คู่มือ อสม. (PDF + video)
- [ ] คู่มือ admin (PDF + video)
- [ ] Quick reference card (พิมพ์ใส่ในกล่องเครื่องวัด)
- [ ] Hand-holding session session วันที่ 1 ของ pilot

### Pilot Operations
- [ ] Verbal agreement / informal commitment กับ รพ.สต. (ไม่ต้อง MOU)
- [ ] Feedback collection channel set up (Google Form หรือ chat group)
- [ ] Weekly review call cadence agreed
- [ ] Incident reporting channel (ถ้ามีปัญหาด่วน ติดต่อได้ 24/7)

---

**End of MVP_PILOT_SCOPE.md**
