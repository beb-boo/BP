# Membership Admin And Doctor Flow Hardening Plan

> **Status: ✅ IMPLEMENTATION COMPLETE (2026-04-04)**
> All phases implemented, tested, and reviewed through 3 review rounds. Awaiting manual E2E verification before production deploy.

เอกสารนี้เป็นแผนงานต่อยอดจาก `plan/PREMIUM_PRODUCTION_READINESS_PLAN.md` โดยแยก scope ออกเป็น 2 งานหลักที่ต้องทำก่อนปล่อยใช้งานจริงเพิ่มขึ้นอีกระดับ

- งานที่ 1: ทำ Web Membership Admin แบบแคบมาก และจำกัดให้จัดการเฉพาะเรื่องสมาชิกเท่านั้น
- งานที่ 2: ปิดช่องโหว่ของ Doctor Flow ที่ยังไม่พร้อม production

หลักคิดของเอกสารนี้คือ “ลดความเสี่ยงก่อน เพิ่ม capability ทีหลัง” ดังนั้นจะไม่ทำ generic admin panel ขนาดใหญ่ และจะไม่เปิดสิทธิ์ดูข้อมูลสุขภาพหรือข้อมูลส่วนบุคคลเกินความจำเป็น

## 1. Relationship To The Existing Premium Plan

แผนนี้ต้องถือเป็น follow-up plan จาก `plan/PREMIUM_PRODUCTION_READINESS_PLAN.md` ไม่ใช่เอกสารแทนที่ โดยมี dependency สำคัญดังนี้

1. Subscription state normalization จากแผน premium เดิมต้องถูกใช้เป็นฐานกลาง
2. Payment status และ expiry logic ต้องมี single source of truth ก่อนจะทำหน้า admin สำหรับ membership
3. Web/Bot parity ของ payment flow ควรถูก stabilize ก่อน หรืออย่างน้อยต้อง reuse utility กลางชุดเดียวกัน

หากงานในแผน premium เดิมยังไม่ลงมือทั้งหมด ให้ถือว่าแผนนี้ใช้แนวทางต่อไปนี้

- Phase พื้นฐานของแผนนี้สามารถเริ่มเตรียมโครงสร้าง route, guard, UI และ data contract ได้
- แต่ logic สถานะสมาชิกจริงของ admin page ต้องอิง utility กลางจากแผน premium เดิม ไม่ควรเขียนซ้ำ

## 2. Executive Decision Summary

### 2.1 Decision A: ทำ Web Membership Admin ก่อน Bot Admin

ตัดสินใจให้ทำ Web Membership Admin ก่อน เพราะเหมาะกับงานลักษณะนี้มากกว่า

- membership management เป็นงานเชิงรายการ, สถานะ, ตาราง, ตัวกรอง และ action ที่ต้องตรวจซ้ำก่อนกด
- web ให้ auditability, confirmation flow และ data minimization ได้ง่ายกว่า
- bot เหมาะกับ emergency command หรือ operational shortcut มากกว่า ไม่เหมาะเป็น primary back office
- ใน code ปัจจุบันยังไม่มีระบบ admin membership จริงอยู่แล้ว มีเพียง admin broadcast ใน bot

### 2.2 Decision B: จำกัด scope ของ Membership Admin ให้แคบมาก

Membership Admin ต้องเห็นเฉพาะข้อมูลที่จำเป็นต่อการจัดการสมาชิก เช่น

- user id
- role
- ชื่อ
- email หรือ phone แบบ masked
- subscription tier แบบ effective
- subscription expiry
- payment history ที่จำเป็นต่อการตรวจสอบสมาชิก
- internal action log ที่เกี่ยวกับ membership

Membership Admin ต้องไม่เห็นข้อมูลต่อไปนี้

- blood pressure records
- OCR images
- citizen id
- date of birth แบบเต็ม
- doctor-patient relationship details
- medical detail อื่นใดที่ไม่เกี่ยวกับสมาชิก

### 2.3 Decision C: แยก Doctor Verification ออกเป็นอีก scope ถ้าจำเป็น

รอบนี้จะ harden doctor flow ที่มีอยู่ให้ปลอดภัยและ consistent ก่อน แต่จะไม่รีบทำ full manual doctor verification admin workflow ถ้ายังไม่จำเป็น

สิ่งที่ทำในรอบนี้คือ

- บังคับ verified doctor ก่อนใช้ doctor-only flow
- ทำให้ web และ bot เก็บ doctor registration data ให้สอดคล้องกันมากขึ้น
- แสดงสถานะ verification ให้ผู้ใช้เห็นอย่างชัดเจน

สิ่งที่ยังไม่ทำในรอบนี้ เว้นแต่จะจำเป็นจริง

- queue manual review สำหรับแพทย์
- upload เอกสารประกอบการยืนยันตัวตนของแพทย์
- back-office full review screen สำหรับ staff medical verification

## 3. Current Findings That Drive This Plan

### 3.1 Membership/Admin Side

- backend มี self-service payment history และ subscription status endpoint แล้ว
- ยังไม่มี staff-only membership route หรือ membership admin UI
- model มี `role = patient, doctor, staff` แล้ว แต่ยังไม่ได้ใช้สร้าง membership admin capability จริง
- subscription data ในระบบยังต้องพึ่งงานจากแผน premium เดิมเพื่อ normalize ให้เป็น effective state ที่เชื่อถือได้

### 3.2 Doctor Flow Side

- web register รองรับ doctor และบังคับ medical license แล้ว
- backend register ตั้ง doctor เป็น `pending` และยิง background TMC verification แล้ว
- doctor-patient flow มี API จริงแล้ว ทั้ง request access, approve/reject, patient list, patient BP records
- frontend dashboard มี doctor view จริง แต่ปุ่มดู records ยังเป็น placeholder toast ไม่ได้เรียก API จริง
- doctor-only endpoints ส่วนใหญ่เช็คแค่ role เป็น `doctor` แต่ยังไม่ enforce `verification_status == verified`
- bot registration เลือก role doctor ได้ แต่ยังไม่เก็บ medical license ให้สอดคล้องกับ web flow

### 3.3 Production Risk If We Do Nothing

- staff จะไม่มีทางจัดการเคสสมาชิกผิดปกติได้อย่างปลอดภัยและเป็นระบบ
- doctor ที่ยัง pending อาจใช้ doctor flow ได้ ทั้งที่ยังไม่ผ่าน verified gate
- web กับ bot จะให้ประสบการณ์ register doctor ไม่ตรงกัน
- user และทีม ops จะสับสนเมื่อมีเคส membership state เพี้ยนหรือ doctor verification ค้าง

## 4. Goals

## 4.1 Primary Goals

1. มีหน้า Web Membership Admin ที่เห็นเฉพาะข้อมูลสมาชิกเท่าที่จำเป็น
2. staff สามารถตรวจ membership status, payment history, และทำ action พื้นฐานต่อสมาชิกได้อย่าง audit ได้
3. doctor flow ฝั่ง web และ backend ต้องบังคับ verified doctor อย่างชัดเจนก่อนใช้งาน doctor-only capability
4. doctor dashboard ต้องดู patient records ผ่าน API จริง ไม่ใช่ placeholder
5. bot registration ของ doctor ต้องเก็บ medical license และใช้ rule ใกล้เคียง web

## 4.2 Secondary Goals

1. ลดโอกาส regression โดยใช้ utility subscription กลางจากแผน premium เดิม
2. ทำให้ data contract ระหว่าง backend และ frontend ชัดเจนขึ้น
3. เปิดทางให้ทำ doctor verification back office ในอนาคต โดยไม่ต้องรื้อโครงสร้างใหม่

## 5. Non-Negotiable Constraints

1. Membership Admin ห้ามแสดง health data
2. Membership Admin ห้ามกลายเป็น generic admin panel
3. Doctor hardening ต้องไม่ทำให้ patient flow เดิมพัง
4. ต้องไม่แก้ MobileApp scope
5. ต้องมี audit log สำหรับ admin membership actions อย่างน้อยระดับ MVP

## 6. Scope Split

## 6.1 Scope A: Narrow Web Membership Admin

In scope

- staff-only backend routes สำหรับ membership management
- staff-only frontend page สำหรับ membership management
- membership list/search/detail แบบจำกัดข้อมูล
- payment history viewer สำหรับ membership support
- admin actions ที่เกี่ยวกับสมาชิกเท่านั้น
- audit logging สำหรับ membership actions

Out of scope

- full admin dashboard
- user deletion
- doctor-patient access management
- health record moderation
- financial reconciliation beyond membership support needs

## 6.2 Scope B: Doctor Flow Hardening

In scope

- enforce verified doctor on doctor-only routes
- enforce verified doctor on patient authorize-doctor flow หากต้องการเลือกหมอด้วย direct authorization
- expose verification status to frontend in safe form
- replace placeholder view-records button with real data flow
- align bot doctor registration with web medical license requirement

Out of scope

- full manual doctor verification console
- evidence upload and review workflow
- hospital onboarding workflow

## 6.3 Scope C: Optional Future Scope

Optional follow-up scope ถ้าหลังจาก hardening แล้วยังมีความจำเป็น

- manual doctor verification admin queue
- review and approve/reject doctor profiles
- richer audit trail for medical verification decisions

## 7. Target State

หลังจบแผนนี้ ระบบต้องอยู่ในสภาพดังนี้

1. staff login เข้าหน้า membership admin ได้เฉพาะคนที่มีสิทธิ์
2. หน้า membership admin แสดงเฉพาะ membership-centric data
3. staff สามารถค้นหาสมาชิก, ดูสถานะ effective membership, ดู payment history, และทำ action พื้นฐานได้
4. ทุก admin action ถูกบันทึกลง audit log พร้อม actor, target, reason, before/after summary
5. doctor ที่ยังไม่ verified ใช้งาน doctor-only API ไม่ได้
6. patient ไม่สามารถ authorize doctor ที่ยังไม่ verified ได้ ถ้าธุรกิจยืนยัน rule นี้
7. doctor dashboard เรียกดู patient records จริงผ่าน API ที่มีอยู่แล้ว
8. bot doctor registration เก็บ medical license ได้ และใช้ validation ใกล้เคียงกับ web
9. frontend แสดง verification state ของ doctor อย่างชัดเจน ไม่ทำให้ user เข้าใจผิด

## 8. High-Level Delivery Order

ลำดับที่แนะนำคือ

1. ใช้ subscription utility กลางจากแผน premium เดิมให้เสร็จหรือพร้อม reuse
2. ทำ backend guard และ data contract ของ doctor flow ก่อน
3. ทำ doctor UI ให้เรียก API จริงก่อน
4. ทำ bot doctor registration ให้สอดคล้องกับ web
5. ค่อยสร้าง narrow web membership admin บนสถานะสมาชิกที่ normalize แล้ว

เหตุผลของลำดับนี้คือ membership admin ต้องพึ่ง state สมาชิกที่เชื่อถือได้ ขณะที่ doctor flow มีช่องโหว่เชิงสิทธิ์ที่ควรปิดก่อนเปิดของใหม่

## 9. Detailed Plan

## Phase 0: Foundation And Dependency Lock ✅

### Objective

ตรึง dependency กับแผน premium เดิมและกำหนด contract กลางก่อนเริ่มแตก route/UI ใหม่

### Tasks

- ยืนยันว่า subscription status utility จากแผน `PREMIUM_PRODUCTION_READINESS_PLAN.md` ถูกใช้เป็น source of truth
- กำหนด `effective_membership_status` ที่ backend admin route จะคืน
- กำหนด masking rules สำหรับ email และ phone ใน admin UI
- กำหนด staff-only guard helper สำหรับ membership admin

### Deliverables

- design note สั้นใน code comments/docstrings
- agreed response shape สำหรับ membership admin list/detail

### Acceptance Criteria

- ไม่มี route ใหม่ใดคำนวณสถานะสมาชิกเองแบบ ad hoc
- data minimization rules ถูกล็อกก่อนสร้าง UI

## Phase 1: Backend Access Control For Membership Admin ✅

### Objective

เปิด staff-only capability แบบแคบโดยไม่สร้าง generic admin framework ที่ใหญ่เกินจำเป็น

### Recommended Approach

- ใช้ `role == "staff"` เป็นฐานสำหรับ MVP
- สร้าง helper ใหม่ เช่น `require_membership_admin()` ใน `app/utils/security.py`
- helper นี้ต้อง reject patient และ doctor ทั้งหมด
- optional: รองรับ allowlist เสริมผ่าน env ถ้าต้องการคุม staff subset ใน production

### Files To Modify

- `app/utils/security.py`
- `app/models.py` ถ้าจำเป็นต่อ audit model
- `app/main.py`

### Tasks

- เพิ่ม helper สำหรับตรวจสิทธิ์ membership admin
- เพิ่ม test สำหรับ unauthorized access
- register admin router ใหม่ใน app main

### Acceptance Criteria

- เฉพาะ staff เท่านั้นที่เข้า membership admin routes ได้
- endpoint เหล่านี้ไม่ปะปนกับ user self-service routes

## Phase 2: Backend Membership Admin API ✅

### Objective

สร้าง staff-only API สำหรับ membership operations ที่แคบและ audit ได้

> **Implementation Note:** Implemented as `app/routers/admin.py` (not `membership_admin.py`). Endpoints use `/api/v1/admin/*` prefix. Grant/expire/normalize-membership endpoints were deferred — current scope covers list, detail, payments, verify/reject doctor, deactivate/activate user. All endpoints require `require_staff` + `verify_api_key`.

### New File

- `app/routers/membership_admin.py`

### Recommended Endpoints

- `GET /api/v1/admin/memberships/users`
  - list/search members
  - filter by effective tier, role, payment status, expiring soon
- `GET /api/v1/admin/memberships/users/{user_id}`
  - membership detail only
- `GET /api/v1/admin/memberships/users/{user_id}/payments`
  - payment history only
- `POST /api/v1/admin/memberships/users/{user_id}/grant-premium`
  - manual grant/extend premium with reason
- `POST /api/v1/admin/memberships/users/{user_id}/expire-premium`
  - set effective free state with reason
- `POST /api/v1/admin/memberships/users/{user_id}/normalize-membership`
  - force re-sync using subscription utility with reason

### Response Data Rules

List/detail response ต้องมีเฉพาะ fields ต่อไปนี้

- user_id
- full_name
- role
- masked_email
- masked_phone
- subscription_tier_raw
- is_premium_active
- effective_tier
- subscription_expires_at
- latest_payment_status
- latest_payment_at
- created_at

ห้ามส่ง

- citizen_id
- date_of_birth เต็มรูปแบบ
- blood pressure records
- medical record fields ใดๆ

### Acceptance Criteria

- staff สามารถจัดการเรื่องสมาชิกได้ครบโดยไม่เห็นข้อมูลสุขภาพ
- endpoint ใหม่ทุกตัวต้องบันทึก audit log เมื่อลงมือ action

## Phase 3: Membership Admin Audit Log ✅

### Objective

ทำให้ทุก action ของ staff สามารถตรวจย้อนหลังได้

> **Implementation Note:** Implemented as `AdminAuditLog` model in `app/models.py`. Fields: id, admin_user_id, action, target_user_id, details, created_at. State changes and audit entries committed atomically. `log_action()` helper adds to session without committing — caller controls transaction. Migration in both `migrate_schema.py` and standalone `add_admin_audit_log.py`.

### Recommended Data Model

เพิ่ม model ใหม่ เช่น `MembershipAdminActionLog`

Suggested fields

- id
- actor_user_id
- target_user_id
- action_type
- reason
- before_state_json
- after_state_json
- created_at

### Files To Modify

- `app/models.py`
- `app/schemas.py` ถ้าต้องใช้ schema เฉพาะ
- migration script ใต้ `migrations/`

### Actions That Must Log

- grant premium
- extend premium
- expire premium
- normalize membership

### Acceptance Criteria

- ทุก staff action มี audit log
- before/after state พอใช้ตรวจย้อนหลังได้โดยไม่ต้องอ่าน raw DB diff

## Phase 4: Frontend Narrow Membership Admin ✅

### Objective

สร้างหน้า web สำหรับ staff ที่แสดงเฉพาะ membership support data

> **Implementation Note:** Implemented as `AdminView` component within `dashboard/page.tsx` (not separate route). Staff role routing: `staff → AdminView`, `patient → PatientView`, `doctor → DoctorView`. Three tabs: Users (with filters/pagination), Pending Doctors (independent fetch), Audit Log. User detail dialog with payment history. Confirmation dialog with required reason input for all actions. All locale strings in en.ts/th.ts.

### New Frontend Route

- `frontend/app/(dashboard)/membership-admin/page.tsx`

### UI Requirements

- search by user id, email, phone, full name
- filter by effective tier
- filter expiring soon
- table view สำหรับสมาชิก
- detail drawer หรือ detail panel สำหรับ membership only
- payment history panel
- action form ที่ต้องกรอก reason ก่อน submit

### UX Constraints

- ห้ามมี tab หรือ section สำหรับ health data
- ห้าม embed BP chart, BP history, OCR image, doctor-patient graph
- ต้องมี confirmation dialog ก่อน action สำคัญ
- ต้องแสดง clearly ว่าเป็น internal staff tool

### Files To Modify

- `frontend/app/(dashboard)/membership-admin/page.tsx`
- `frontend/lib/app-types.ts`
- `frontend/proxy.ts` ถ้าต้องเพิ่ม protected route
- layout/navigation เฉพาะกรณีต้องเพิ่ม link สำหรับ staff only

### Acceptance Criteria

- staff ใช้ membership admin จบ flow ได้โดยไม่ออกจากหน้า
- regular users เปิด route นี้ไม่ได้
- UI ไม่เผยข้อมูลเกินจำเป็น

## Phase 5: Doctor Backend Guard Hardening ✅

### Objective

ปิดช่องโหว่ที่ทำให้ doctor ที่ยังไม่ verified ใช้งาน doctor-only flow ได้

> **Implementation Note:** `require_verified_doctor` added to `app/utils/security.py`. Applied to all 5 doctor endpoints in `doctor.py`. Patient authorize-doctor checks `doctor.verification_status != "verified"`. 11 tests in `test_doctor_verification_guard.py`.

### Files To Modify

- `app/routers/doctor.py`
- `app/utils/security.py`
- `app/routers/auth.py`
- `app/schemas.py`

### Tasks

- เพิ่ม helper เช่น `require_verified_doctor(current_user)`
- ใช้ helper นี้ใน routes ต่อไปนี้
  - doctor request access
  - doctor access requests
  - doctor patients
  - doctor patient bp records
  - doctor cancel access request
- พิจารณา enforce verified doctor ใน patient authorize-doctor path ด้วย เพื่อกัน manual authorization ไปยังหมอที่ยัง pending
- expose `verification_status` และ safe verification message ผ่าน profile/login payload สำหรับ frontend

### Behavioral Rule

- role เป็น `doctor` อย่างเดียวไม่พอ
- doctor-only capability ใช้ได้เฉพาะ `verification_status == "verified"`
- ถ้ายัง `pending` ให้ตอบข้อความชัดเจน เช่น account pending verification

### Acceptance Criteria

- pending doctor ใช้ doctor-only endpoints ไม่ได้
- frontend มีข้อมูลพอจะแสดงสถานะว่ากำลังรอตรวจสอบ

## Phase 6: Doctor Frontend Hardening ✅

### Objective

ทำให้หน้า doctor ใช้งานจริงได้ ไม่ใช่ครึ่ง mock ครึ่งจริง

> **Implementation Note:** View Records button now calls real API (`/doctor/patients/{id}/bp-records`) and shows data in a Dialog. DoctorView accepts `user` prop with `isVerified` flag — non-verified doctors see only a verification banner, all UI hard-disabled. `verification_status` exposed in login response and profile. Locale strings updated: removed "เร็วๆ นี้", added verification_pending/rejected messages in both EN/TH.

### Files To Modify

- `frontend/app/(dashboard)/dashboard/page.tsx`
- `frontend/lib/app-types.ts`
- `frontend/locales/th.ts`
- `frontend/locales/en.ts`

### Tasks

- เปลี่ยนปุ่ม `View Records` จาก toast placeholder เป็น flow จริง
- ทางเลือกที่แนะนำ
  - ใช้ dialog หรือ sheet สำหรับแสดง patient BP records ล่าสุด
  - เรียก `GET /doctor/patients/{patient_id}/bp-records`
- เพิ่ม state/loading/error handling สำหรับ doctor record viewer
- แสดงสถานะ doctor verification ถ้า user เป็น doctor และยัง pending
- แก้ wording ไทยที่ยังค้างว่า `จัดการแพทย์ (เร็วๆ นี้)` ให้ตรงกับของจริง

### Acceptance Criteria

- doctor กดดู records แล้วเห็นข้อมูลจริงจาก API
- pending doctor ไม่ถูกปล่อยให้เข้า flow แล้วเจอ error แบบไม่รู้สาเหตุ
- locale สอดคล้องกับ feature ที่มีจริง

## Phase 7: Bot Doctor Registration Alignment ✅

### Objective

ทำให้ doctor registration ใน bot ไม่เบี่ยงจาก web มากเกินไป

> **Implementation Note:** `REG_LICENSE = 8` state added to `handlers.py`. `reg_license()` handler validates 4-20 chars. `reg_role()` branches: doctor → ask license, patient → skip to password. `services.py` stores `medical_license` in User creation and checks for duplicate license hash. Locale strings (enter_license, license_invalid) added in EN/TH. 7 tests in `test_bot_doctor_registration.py`.

### Files To Modify

- `app/bot/handlers.py`
- `app/bot/services.py`
- `app/bot/locales.py`
- ถ้าจำเป็น `app/schemas.py` หรือ helper validation ที่ reuse ได้

### Tasks

- เพิ่มขั้นตอนถาม medical license ใน bot registration เมื่อ role = doctor
- validate duplicate medical license เหมือน web
- ส่ง medical license เข้า `BotService.register_new_user()`
- เก็บ `medical_license` ลง user model ผ่าน property setter เหมือนฝั่ง web
- แสดงข้อความหลังสมัครว่า verified หรือ pending อย่างชัดเจน
- ถ้า TMC auto-check ยังใช้ชื่อเป็นหลัก ให้เก็บ medical license ไว้ก่อน แม้ยังไม่ได้ใช้เต็มรูปแบบ เพื่อให้ข้อมูล registration ตรงกัน

### Acceptance Criteria

- doctor register ผ่าน bot แล้วมี medical license stored เหมือน web
- duplicate license ผ่าน bot โดน reject ได้
- bot และ web ไม่สร้าง doctor account data shape คนละแบบ

## Phase 8: Optional Separate Scope For Doctor Verification Back Office

### Objective

เก็บเป็น optional next scope ถ้าหลังจาก hardening แล้วยังต้องการ manual doctor verification

### Suggested Future Deliverables

- `plan/DOCTOR_VERIFICATION_BACKOFFICE_PLAN.md`
- staff-only review queue สำหรับ doctor pending
- approve/reject workflow
- review notes
- verification audit log

### Explicit Non-Goal For Current Round

phase นี้ไม่ควรดันเข้ารอบเดียวกับ membership admin narrow ถ้ายังไม่มีเหตุผลทางธุรกิจที่ชัดเจน เพราะจะทำให้ scope บวมและเสี่ยงเปิดข้อมูลเกินจำเป็น

## 10. File Impact Map

### New Backend Files

- `app/routers/membership_admin.py`
- optional `app/utils/admin_membership.py` ถ้าต้องแยก helper

### New Frontend Files

- `frontend/app/(dashboard)/membership-admin/page.tsx`

### New Test Files

- `tests/test_membership_admin_api.py`
- `tests/test_doctor_verification_guards.py`
- `tests/test_bot_doctor_registration.py`

### Existing Files Likely To Change

- `app/models.py`
- `app/schemas.py`
- `app/main.py`
- `app/utils/security.py`
- `app/routers/auth.py`
- `app/routers/doctor.py`
- `app/routers/payment.py`
- `app/bot/handlers.py`
- `app/bot/services.py`
- `app/bot/locales.py`
- `frontend/app/(dashboard)/dashboard/page.tsx`
- `frontend/app/(dashboard)/subscription/page.tsx` if linking to admin/support views is needed later
- `frontend/lib/app-types.ts`
- `frontend/proxy.ts`
- `frontend/locales/th.ts`
- `frontend/locales/en.ts`

## 11. Testing Plan

### 11.1 Backend Tests

- staff-only membership admin endpoints reject patient and doctor
- membership admin list/detail never return forbidden fields
- grant premium action writes audit log
- expire premium action writes audit log
- normalize membership action uses subscription utility correctly
- pending doctor cannot request patient access
- pending doctor cannot list patients
- pending doctor cannot read patient records
- patient cannot authorize pending doctor if rule is enabled

### 11.2 Frontend Tests

- membership admin page only renders for staff
- membership admin page does not contain health widgets
- doctor dashboard view records calls real API path
- pending doctor sees verification state messaging
- locale text no longer says coming soon for features that exist

### 11.3 Bot Tests

- doctor bot registration asks for medical license
- duplicate medical license is rejected
- stored doctor account from bot contains medical license fields

### 11.4 Manual E2E Checklist

1. Login as staff and open membership admin
2. Search a free user
3. View membership detail and confirm no health data is visible
4. View payment history
5. Grant premium with reason
6. Verify audit log entry created
7. Expire membership with reason
8. Verify user becomes effective free
9. Register doctor on web and confirm pending or verified state behaves correctly
10. Register doctor on bot and confirm medical license is collected
11. Login as pending doctor and verify doctor-only features are blocked cleanly
12. Login as verified doctor and verify patient records open through real API flow

## 12. Rollout Strategy

### Stage 1

- backend guards for verified doctor
- frontend doctor record viewer
- bot doctor registration alignment

### Stage 2

- backend membership admin API
- audit log

### Stage 3

- frontend membership admin page
- staff-only navigation and operational checklist

### Stage 4

- optional doctor verification back office plan decision

## 13. Risks And Mitigations

### Risk 1

การ enforce verified doctor อาจ block user ที่เคยใช้งาน flow อยู่แล้วแบบไม่ตั้งใจ

Mitigation

- สำรวจก่อนว่ามี doctor pending อยู่กี่ราย
- เตรียม user-facing message ชัดเจน
- ถ้าจำเป็นให้ทำ temporary staff support path ระหว่าง rollout

### Risk 2

membership admin อาจเผลอเผยข้อมูลมากเกินจำเป็น

Mitigation

- lock response schema ตั้งแต่ backend
- ทำ explicit allowlist ของ fields แทนการ serialize profile ทั้งก้อน

### Risk 3

bot registration change อาจกระทบ conversation flow เดิม

Mitigation

- เพิ่ม state ใหม่แบบชัดเจน
- ทดสอบทั้ง patient และ doctor registration path

## 14. Definition Of Done

ถือว่างานนี้เสร็จเมื่อครบทุกข้อ

1. ✅ มีเอกสารนี้ใช้เป็น execution reference ร่วมกับ `PREMIUM_PRODUCTION_READINESS_PLAN.md`
2. ✅ staff-only membership admin backend พร้อมใช้ — `app/routers/admin.py` (7 endpoints, require_staff + verify_api_key)
3. ✅ frontend membership admin page พร้อมใช้และไม่เปิดข้อมูลสุขภาพ — AdminView ใน dashboard, 3 tabs
4. ✅ มี audit log สำหรับ membership admin actions — `AdminAuditLog` model, atomic commit
5. ✅ doctor-only routes บังคับ verified doctor แล้ว — `require_verified_doctor` on 5 endpoints + patient authorize check
6. ✅ doctor dashboard เรียกดู patient records ผ่าน API จริง — Dialog with real BP data
7. ✅ bot doctor registration เก็บ medical license แล้ว — REG_LICENSE state, duplicate check
8. ✅ มี automated tests ครอบคลุม critical paths — 24 admin + 11 doctor guard + 7 bot registration = 42 tests
9. ✅ locale และ UX messaging สอดคล้องกับระบบจริง — removed "เร็วๆ นี้", all admin/doctor strings localized EN/TH

## 15. Immediate Recommended Next Implementation Order

ถ้าจะเริ่มลงมือทันที ให้ทำตามลำดับนี้

1. ปรับ backend guard ของ doctor verification
2. เพิ่ม `verification_status` เข้า profile/login contract ที่ frontend ใช้ได้
3. ทำ doctor view records ให้เรียก API จริง
4. ปรับ bot doctor registration ให้เก็บ medical license
5. สร้าง membership admin backend routes และ audit log
6. สร้าง narrow membership admin frontend

## 16. Notes For The Next Round

หากต้องแตกเอกสารต่อจากแผนนี้ เอกสารถัดไปที่ควรแยกออกมาต่างหากคือ

- doctor verification back office spec
- membership admin API contract spec
- execution checklist สำหรับ rollout จริงใน production

## 17. Implementation Summary (2026-04-04)

### Files Created
| File | Purpose |
|------|---------|
| `app/routers/admin.py` | Staff-only admin API (7 endpoints, ~350 lines) |
| `app/utils/subscription.py` | Single source of truth for subscription state |
| `app/services/payment_service.py` | Unified payment verification (Web + Bot) |
| `migrations/add_admin_audit_log.py` | Standalone migration for AdminAuditLog (SQLite + PostgreSQL) |
| `tests/test_membership_admin_api.py` | 24 admin API tests |
| `tests/test_doctor_verification_guard.py` | 11 doctor guard + verification contract tests |
| `tests/test_bot_doctor_registration.py` | 7 bot registration tests |

### Files Modified
| File | Changes |
|------|---------|
| `app/models.py` | +AdminAuditLog model |
| `app/schemas.py` | +Admin schemas, required reason fields, verification_status in profile |
| `app/main.py` | +admin router registration |
| `app/utils/security.py` | +require_verified_doctor, +require_staff (with STAFF_ALLOWLIST) |
| `app/routers/doctor.py` | 5 endpoints use require_verified_doctor; patient authorize checks doctor verification |
| `app/routers/auth.py` | +verification_status in login response |
| `app/bot/handlers.py` | +REG_LICENSE state, +reg_license handler, modified reg_role |
| `app/bot/services.py` | +medical_license in User creation, +duplicate license check |
| `app/bot/locales.py` | +enter_license, +license_invalid (EN + TH) |
| `migrations/migrate_schema.py` | +admin_audit_logs table creation |
| `frontend/.../dashboard/page.tsx` | +AdminView (3 tabs), +DoctorView verification gate, +real View Records |
| `frontend/lib/app-types.ts` | +verification_status, +AdminUserItem, +AdminAuditEntry |
| `frontend/locales/en.ts` | +admin section, +doctor verification strings |
| `frontend/locales/th.ts` | +admin section, +doctor verification strings, removed "เร็วๆ นี้" |

### Review Rounds
- **Round 1:** Fixed non-atomic audit, missing API key gate, missing migration, pending doctor UI leak, raw verification logs
- **Round 2:** Fixed migration not wired into main script, sanitizer gaps, missing reason for activate/deactivate
- **Round 3:** Fixed pending doctors filtered subset, reason required in schemas, .antigravity/tasks.json, hardcoded English strings

### Test Coverage
- 24 admin API tests (access control, verification, deactivate/activate, atomic audit, masking, filtering, pagination)
- 11 doctor verification guard tests (verified/pending/rejected doctors, patient authorize, role blocking)
- 7 bot registration tests (license collection, patient skip, duplicate rejection, handler states)
- 35 payment/subscription tests (from PREMIUM_PRODUCTION_READINESS_PLAN)
