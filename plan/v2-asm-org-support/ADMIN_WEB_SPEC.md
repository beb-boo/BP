# Admin Web Specification — รพ.สต. / Organization Dashboard

> **Status:** Draft v1.1 — aligned with [[PLAN_REVIEW_RESPONSE]] decisions (2026-04-18)
> **Last updated:** 2026-04-18
> **Owner:** Pornthep
> **Depends on:** `MVP_PILOT_SCOPE.md`, `ORG_FOUNDATION.md`, `PLAN_REVIEW_RESPONSE.md`
> **Related:** `ASM_PWA_SPEC.md`, `CONSENT_FLOW_SPEC.md`

> [!INFO] **v1.1 changes**
> - §2 routes: Added `/admin/select-org` สำหรับ admin ที่อยู่หลาย org (decision 4.10 — JWT `active_org_id` claim)
> - NEW §3.1.5: Organization switcher UI spec
> - §3.16 audit log: Dual-source from `admin_audit_logs` (legacy) + `audit_logs` (new) — decision 4.4
> - §5.1: Added `POST /api/v1/auth/select-org` endpoint
> - §2 routes: Added `/admin/system/backups` (superadmin-only — Neon branch backup tool, see [[BACKUP_AND_MIGRATION_SPEC]])

---

## 1. Purpose

Web application สำหรับ **รพ.สต. admin** (role = `rpsst_admin`) ใช้ผ่าน PC/Laptop browser ที่ รพ.สต.

หน้าที่หลัก:
- จัดการ organization (รพ.สต. เอง)
- จัดการ อสม. ในสังกัด
- จัดการชาวบ้าน (proxy-managed) + care assignments
- ดู BP readings + analytics
- Consent management
- Audit log viewer
- Report & export

**Tech stack**: Next.js 16 (frontend ที่มีอยู่แล้ว) + FastAPI backend + shadcn/ui + TanStack Query

---

## 2. Routes / Pages

| Route | Page | Access |
|-------|------|--------|
| `/admin/login` | Admin login (phone/email + password + optional 2FA) | Public |
| `/admin/select-org` | Organization selector (v1.1 — ถ้า admin อยู่ > 1 org) | rpsst_admin |
| `/admin/onboarding` | First-login ToS acceptance + org setup | rpsst_admin (new) |
| `/admin` | Dashboard home (KPIs + quick links) | rpsst_admin |
| `/admin/organization` | Organization profile + settings | rpsst_admin |
| `/admin/asm` | อสม. list | rpsst_admin |
| `/admin/asm/new` | Create new อสม. + generate pairing code | rpsst_admin |
| `/admin/asm/[id]` | อสม. detail + assignments + activity | rpsst_admin |
| `/admin/patients` | Patient list | rpsst_admin |
| `/admin/patients/new` | Create new proxy patient | rpsst_admin |
| `/admin/patients/[id]` | Patient detail + history + consent | rpsst_admin |
| `/admin/patients/[id]/edit` | Edit patient info | rpsst_admin |
| `/admin/patients/import` | Import CSV (optional) | rpsst_admin |
| `/admin/assignments` | Care assignment management | rpsst_admin |
| `/admin/consent` | Consent records browser | rpsst_admin |
| `/admin/consent/[id]` | Consent detail + withdraw | rpsst_admin |
| `/admin/readings` | BP readings list (all in org) | rpsst_admin |
| `/admin/readings/[id]` | Reading detail + edit + delete | rpsst_admin |
| `/admin/review-queue` | OCR low-confidence review queue | rpsst_admin |
| `/admin/alerts` | Patient alert list (high BP, irregular) | rpsst_admin |
| `/admin/reports` | Report builder + export | rpsst_admin |
| `/admin/audit-log` | Audit log viewer | rpsst_admin |
| `/admin/settings` | Admin profile + password + 2FA + transfer ownership | rpsst_admin |
| `/admin/settings/users` | Manage other admins (if multi-admin) | rpsst_admin |
| `/admin/system/backups` | Neon branch backup tool (see [[BACKUP_AND_MIGRATION_SPEC]]) | **superadmin only** |

---

## 3. Page Specifications

### 3.1 `/admin/login` — Admin Login

**Purpose**: Authenticate admin user

**Layout**:
- Full-page centered form
- Logo + "BP Monitor for Organizations" title
- Form: phone OR email + password + (optional) OTP from authenticator
- Link: "ลืมรหัสผ่าน?" (triggers admin reset flow)

**Behavior**:
- Phone format validation (TH: 10 digits starting with 0)
- Rate limit: 5 failed attempts / 15 min per account (backend enforce)
- On success: redirect to `/admin` (or `/admin/onboarding` if first login)
- On failure: generic error message (don't leak whether user exists)
- If 2FA enabled on account: show TOTP code field on step 2

**API calls**:
- `POST /api/v1/admin/auth/login` — body: `{identifier: "phone_or_email", password}`
- `POST /api/v1/admin/auth/verify-2fa` — body: `{totp_code}` (if 2FA enabled)

**Behavior after successful auth (v1.1):**
- Backend returns `{ access_token, requires_org_selection, org_memberships: [...] }`
- Frontend:
  - ถ้า `requires_org_selection=true` (user มี > 1 org active) → redirect ไป `/admin/select-org`
  - ถ้า `requires_org_selection=false` (1 org auto-selected OR 0 orgs) → redirect ไป `/admin` (dashboard)
- JWT ที่ออกมามี claim `active_org_id` (ถ้า 1 org) หรือ NULL (รอเลือก)

**Audit events**:
- `login_success` or `login_failure`

---

### 3.1.5 `/admin/select-org` — Organization Selector (v1.1 new)

**Purpose:** Admin ที่เป็น member ของหลาย org (multi-tenancy) เลือกว่าตอนนี้ทำงานใน org ไหน

**When shown:** เฉพาะ user ที่มี active membership > 1 org (`organization_members.is_active=true`)

**Layout:**
- Centered card, full-page
- Title: "เลือกองค์กร"
- Subtitle: "คุณเป็นสมาชิกของ X องค์กร เลือกองค์กรที่ต้องการใช้งาน"
- List of org cards:
  - Org name + type icon (รพ.สต./คลินิก/รพ.)
  - Role ใน org นั้น (rpsst_admin / rpsst_staff)
  - จำนวน patients ใน org (stat)
  - Button: "เลือก"

**Behavior:**
- Click เลือก org → `POST /api/v1/auth/select-org {org_id}` → backend issue JWT ใหม่ (มี `active_org_id` claim)
- Redirect ไป `/admin` (dashboard ของ org ที่เลือก)
- Org switcher (top nav) ยังเปลี่ยนภายหลังได้

**API calls:**
- `GET /api/v1/admin/my-orgs` — list user's active org memberships
- `POST /api/v1/auth/select-org` — body: `{org_id}`; response: new JWT with `active_org_id`

**Audit events:**
- `login_success` with metadata `{org_selected: org_id}` เมื่อเลือก org

**Top nav org switcher (shown on all /admin/* pages when multi-org user):**
- Dropdown showing current org name + switch button
- Click switch → return to `/admin/select-org` (re-issue JWT)
- MVP: ถ้า user 1 org เดียว → ไม่แสดง switcher

---

### 3.2 `/admin/onboarding` — First-Login Setup

**Trigger**: admin's `terms_accepted_at` is null

**Flow**:
1. Welcome screen + explanation
2. Accept **Privacy Policy** (checkbox + read link)
3. Accept **Terms of Service for Organizations** (checkbox + read link)
4. Organization profile (if not set):
   - ชื่อ รพ.สต.
   - Code (HCODE ถ้ามี) + code_system
   - Address
   - Province/district/subdistrict (dropdown)
   - Contact info
5. Admin confirms authority: checkbox "ข้าพเจ้ารับรองว่ามีอำนาจผูกพันองค์กรนี้ในการใช้บริการ"
6. Submit → create `terms_accepted_at` + organization record

**Validation**:
- Code (if provided) must be unique within code_system
- Province/district codes valid
- Required: at least organization name + type

**API calls**:
- `POST /api/v1/admin/onboarding/accept-terms`
- `POST /api/v1/admin/organization` (or PATCH if editing)

---

### 3.3 `/admin` — Dashboard Home

**Purpose**: At-a-glance view of organization health + quick actions

**Layout**: Grid of widget cards

**Widgets**:

#### 3.3.1 KPI Row (4 cards)
- **ชาวบ้านทั้งหมด** — count + compared to last month (% change)
- **อสม. active** — count / total
- **BP readings สัปดาห์นี้** — count + sparkline
- **Alerts** — จำนวนคนความดันสูงต้องติดตาม (คลิก → `/admin/alerts`)

#### 3.3.2 Recent Activity
- 10 รายการล่าสุด: อสม. X บันทึก BP ให้ชาวบ้าน Y (timestamp)
- คลิก → patient detail

#### 3.3.3 Review Queue Summary
- "มี N รายการ OCR confidence ต่ำรอ review"
- "มี M รายการ unknown_patient รอจัดสรร"
- Link → `/admin/review-queue`

#### 3.3.4 BP Trend (last 30 days)
- Line chart: average systolic/diastolic ของทั้ง org
- Option: filter by อสม., by patient group

#### 3.3.5 อสม. Activity (last 7 days)
- Bar chart: จำนวน readings ต่อ อสม.
- Help identify under-active อสม.

**API calls**:
- `GET /api/v1/admin/dashboard/kpi`
- `GET /api/v1/admin/dashboard/recent-activity`
- `GET /api/v1/admin/dashboard/review-queue-summary`
- `GET /api/v1/admin/dashboard/bp-trend?days=30`
- `GET /api/v1/admin/dashboard/asm-activity?days=7`

---

### 3.4 `/admin/asm` — อสม. List

**Purpose**: Manage อสม. in organization

**Layout**: Table + actions

**Columns**:
- ชื่อ (decrypted)
- เบอร์โทร (masked: 08x-xxx-x789)
- จำนวนผู้ดูแล (active care_assignments count)
- Last login (relative time)
- Readings this week (count)
- Status (active / suspended / pending_pairing)
- Actions: View / Suspend / Resend Pairing Code

**Filters**:
- Status (all / active / suspended / pending)
- Search by name / phone

**Actions**:
- **Create new อสม.** → `/admin/asm/new`
- **Export CSV** — list of อสม. for offline reference
- **Bulk suspend** (multi-select)

**API calls**:
- `GET /api/v1/admin/asm?status=active&search=&page=1`
- `POST /api/v1/admin/asm/{id}/suspend`
- `POST /api/v1/admin/asm/{id}/resend-pairing`

---

### 3.5 `/admin/asm/new` — Create อสม.

**Purpose**: Onboard new อสม.

**Form fields**:
- ชื่อ-นามสกุล (required)
- เบอร์โทร (required, unique) — ต้องใช้เบอร์ Telegram ที่ อสม. จะใช้
- เลขบัตรประชาชน (optional)
- อายุ / DOB (optional)
- เพศ (optional)
- ที่อยู่ (optional)
- Pre-assign patients (optional, multi-select from unassigned patients)
- Note (optional, admin use)

**Process on submit**:
1. Create user record (role=`asm`, account_type=`self_managed`)
2. Add to `organization_members` (role=`asm`, effective_from=now)
3. Generate 6-digit pairing code → insert `pairing_codes` (TTL 15 min)
4. (If pre-assigned) create `care_assignments`
5. Show success modal with:
   - Pairing code prominently displayed
   - Instructions for อสม. (step-by-step):
     1. เปิด Telegram app (ถ้ายังไม่มี → install ก่อน)
     2. ค้น "@YourBotName" หรือสแกน QR
     3. พิมพ์ `/start 123456` (แทน 123456 ด้วย pairing code)
     4. เสร็จแล้วจะได้ข้อความยืนยัน
   - "Copy pairing code" + "Copy instructions" buttons
   - "Send via SMS" (Phase 2) or "Send via LINE" (Phase 2)

**Validation**:
- เบอร์โทรไทย format
- เบอร์โทรไม่ซ้ำกับ user ที่มีอยู่
- Pairing code sent clearly — admin **ต้อง** ถ่าย screenshot หรือจดเองก่อนปิด modal

**API calls**:
- `POST /api/v1/admin/asm` — create user + org membership
- `POST /api/v1/admin/asm/{id}/pairing-code` — generate new code (auto on create)

**Audit events**:
- `user_create`, `org_member_add`, `care_assignment_create` (if pre-assigned)

---

### 3.6 `/admin/asm/[id]` — อสม. Detail

**Purpose**: View/edit specific อสม. + see their work

**Sections**:

#### 3.6.1 Profile (collapsible)
- Name, phone (masked), email (masked)
- Date joined
- Telegram pairing status (paired at X, or "not paired yet")
- Status (active/suspended)
- Actions: Edit profile / Suspend / Resend pairing / Reset password

#### 3.6.2 Patients under care
- Table of assigned patients: name, sequence, last reading, status
- Actions: Transfer to another อสม. / End assignment

#### 3.6.3 Activity log (last 30 days)
- List of actions: BP readings created, patients viewed, logins
- Timestamps + details

#### 3.6.4 Statistics
- Total readings this month / week
- Average readings per patient
- OCR accuracy (average confidence score of their submissions)
- Average time from measurement to submission

**API calls**:
- `GET /api/v1/admin/asm/{id}`
- `GET /api/v1/admin/asm/{id}/patients`
- `GET /api/v1/admin/asm/{id}/activity?days=30`
- `GET /api/v1/admin/asm/{id}/statistics`

---

### 3.7 `/admin/patients` — Patient List

**Purpose**: Browse all patients in organization

**Layout**: Table with filters sidebar

**Columns**:
- ชื่อ (decrypted, conditional masking based on role)
- อายุ / เพศ
- เบอร์โทร (masked)
- อสม. ดูแล (name + link)
- Sequence in list (for OCR batch)
- Last reading (date + value)
- Reading count (this month)
- Consent status (active/partial/withdrawn)
- Actions: View / Edit / Assign / Deactivate

**Filters**:
- Search by name / phone / citizen ID (masked input, hashed search)
- อสม. (dropdown)
- Age range
- Gender
- Consent status
- Last reading > N days (find overdue patients)
- Severity (high BP last reading)

**Actions**:
- **Create new patient** → `/admin/patients/new`
- **Import CSV** → `/admin/patients/import`
- **Bulk assign** (multi-select + choose อสม.)
- **Export CSV** — respecting encrypted fields (export decrypted ฉะนั้นต้อง audit log)

**Data privacy note**:
- Default masking: citizen ID (`x-xxxx-xxxxx-xx-x`), phone (`08x-xxx-x789`)
- Unmask click → confirm + audit log event `patient_view` with metadata `{field: "citizen_id_unmasked"}`

**API calls**:
- `GET /api/v1/admin/patients?search=&asm=&age_min=&...`
- `POST /api/v1/admin/patients/bulk-assign`
- `POST /api/v1/admin/patients/export` (returns signed download URL)

---

### 3.8 `/admin/patients/new` — Create Proxy Patient

**Purpose**: Register new ชาวบ้าน that doesn't have own account

**Form**:

#### 3.8.1 Identity
- ชื่อ-นามสกุล (required)
- เลขบัตรประชาชน (optional, unique if provided — hashed for search)
- วันเกิด (required)
- เพศ (required)

#### 3.8.2 Contact (optional)
- เบอร์โทร (บางคนมี บางคนไม่มี)
- ที่อยู่ตามทะเบียนบ้าน
- ที่อยู่ปัจจุบัน (ถ้าต่างจากทะเบียนบ้าน)
- Contact person (ญาติ/ผู้ดูแล) + relationship

#### 3.8.3 Medical
- โรคประจำตัว (multi-select: ความดันโลหิตสูง, เบาหวาน, ไขมัน, โรคหัวใจ, etc.)
- Allergies
- Current medications (free text or structured)
- Note

#### 3.8.4 Assignment & Consent
- Assign to อสม. (dropdown, required)
- Sequence in list (auto-increment suggested, editable)
- Consent at creation time (choose):
  - "อสม. จะเก็บ consent ภายหลังตอนลงพื้นที่" (default — pending)
  - "ชาวบ้านได้ให้ความยินยอมแล้ว" → upload consent scan or digital signature data

**Process on submit**:
1. Create user record (role=`patient_proxy`, account_type=`proxy_managed`, `managed_by_organization_id=org`)
2. Encrypt PII + hash for search (citizen_id, phone, name)
3. Create `care_assignment` (caregiver=selected อสม., patient=new user, org=current, sequence=N)
4. (If consent provided) create `consent_records` for relevant scopes
5. Redirect → patient detail page

**API calls**:
- `POST /api/v1/admin/patients` — full payload

**Audit events**:
- `user_create`, `care_assignment_create`, (optionally) `consent_grant`

---

### 3.9 `/admin/patients/[id]` — Patient Detail

**Purpose**: Full view of ชาวบ้าน

**Sections**:

#### 3.9.1 Header
- Name (decrypted) + age + gender
- Status badge: active / deceased / inactive
- Quick actions: Edit / Assign / View consent / Deactivate

#### 3.9.2 Profile (collapsible)
- Full contact info (masked by default, click to unmask with audit)
- Medical info
- Emergency contact

#### 3.9.3 BP History
- Chart (30/90/365 days selectable)
- Recent readings table (10 most recent)
- "View all" → `/admin/readings?patient={id}`

#### 3.9.4 Consent Status
- List of consent records (scope, status, granted_at, method)
- "View full consent" → `/admin/consent/{id}`

#### 3.9.5 Care Assignments
- Current อสม. ผู้ดูแล
- Assignment history

#### 3.9.6 Alerts & Flags
- High BP last N readings
- Overdue reading (> 30 days)
- Any flagged concerns

#### 3.9.7 Audit trail
- Recent actions on this patient (view, edit, reading added)
- Link to full audit log filtered by this patient

**API calls**:
- `GET /api/v1/admin/patients/{id}`
- `GET /api/v1/admin/patients/{id}/readings?days=30`
- `GET /api/v1/admin/patients/{id}/consent`
- `GET /api/v1/admin/patients/{id}/assignments`
- `GET /api/v1/admin/patients/{id}/audit?limit=20`

**Audit events**:
- `patient_view` on every page load (with target_user_id)

---

### 3.10 `/admin/assignments` — Care Assignment Management

**Purpose**: Bulk management of อสม. ↔ patient relationships

**Layout**: Split view

**Left panel**: อสม. list (radio select)
**Right panel**: when อสม. selected, shows assigned patients + unassigned patients

**Operations**:
- Drag-and-drop to assign/unassign (or checkbox-based for mobile-friendly)
- Bulk transfer: select multiple patients → "Transfer to อสม. X"
- Rebalance: suggest distribution (เช่น ทุก อสม. ได้ 10 คน)

**Validation**:
- Warn if อสม. will have > 30 patients (overload)
- Confirm transfer (since it affects data visibility)

**API calls**:
- `GET /api/v1/admin/assignments?asm_id={id}`
- `POST /api/v1/admin/assignments/transfer` — body: `{patient_ids: [...], from_asm: X, to_asm: Y}`
- `POST /api/v1/admin/assignments/end` — body: `{patient_ids: [...], reason}`

---

### 3.11 `/admin/consent` — Consent Records Browser

**Purpose**: Audit + manage all consent records

**Columns**:
- Patient name
- Scope
- Status
- Method (paper/digital/both)
- Granted at
- Granted by (อสม. / admin)
- Paper filed? (yes/no — physical paper tracked, not digitized)
- Expires at
- Actions: View / Record Paper Filing / Withdraw

**Filters**:
- Status (active / withdrawn / expired)
- Scope (asm_collect / rpsst_view / ...)
- Method
- Paper filing status (filed / not filed)
- Date range
- Patient search

**Actions**:
- **Record paper filing** — admin กรอกว่ากระดาษ consent ถูกเก็บในตู้ไหน (no image upload)
- **Export** — audit trail CSV (for PDPA compliance reporting)
- **Withdraw consent** — requires reason, triggers downstream effects (block new readings)

**Important — No paper scan upload**:
- ตามหลัก data minimization, ไม่อัปโหลดรูปกระดาษ consent เข้าระบบ
- กระดาษเก็บ **physical เท่านั้น** ที่ รพ.สต. ในตู้ล็อก
- Digital evidence = signature + GPS + timestamp (เก็บใน DB)
- หน้าจอแค่ track ว่ากระดาษอยู่ที่ไหนในตู้ เพื่อหาเจอตอนต้องใช้

**API calls**:
- `GET /api/v1/admin/consent?status=active&scope=...`
- `POST /api/v1/admin/consent/{id}/record-paper-filing` — body: `{filed_location, notes}`
- `PATCH /api/v1/admin/consent/{id}/withdraw` — body: `{reason}`

**Audit events**:
- `consent_withdraw` on withdraw
- `consent_update` on paper filing record

---

### 3.12 `/admin/readings` — BP Readings List

**Purpose**: Browse all readings in organization

**Columns**:
- Patient name
- Measured at (TH datetime)
- Systolic / Diastolic / Pulse
- Measured by (อสม. name)
- Context (self / asm_field_visit / ...)
- Source (manual / ocr_single / ocr_batch)
- OCR confidence (if OCR)
- Status flags: flagged_high / edited / ocr_reviewed
- Actions: View / Edit / Delete

**Filters**:
- Patient
- อสม.
- Date range
- Value range (systolic >= X, diastolic >= Y)
- Source type
- OCR confidence < threshold
- Needs review queue

**Batch actions**:
- Export CSV
- Flag as reviewed (for OCR queue items)

---

### 3.13 `/admin/review-queue` — OCR Review Queue

**Purpose**: Review + approve OCR readings that need human check

**Two subtabs**:

#### 3.13.1 Low confidence (OCR confidence < threshold, e.g. 0.85)
- List of pending OCR readings
- Per row: thumbnail image + OCR output + claim patient
- Actions: Approve as-is / Edit values / Reassign patient / Reject

#### 3.13.2 Unknown patient (batch OCR couldn't match)
- List of readings where OCR extracted name but couldn't match
- Suggested matches (fuzzy) + manual selection
- Actions: Confirm match / Create new patient / Reject

**Image handling (strict privacy)**:
- รูปที่ display ในหน้านี้มาจาก `files` table (purpose = `ocr_batch_review_temp`)
- รูปเก็บสูงสุด **7 วัน** (`expires_at` enforced)
- เมื่อ admin ดำเนินการ (approve/edit/reject): รูปถูก **ลบทันที** (data_encrypted cleared, deleted_at set)
- หาก admin ไม่ดำเนินการใน 7 วัน: cron job ลบอัตโนมัติ + ส่ง alert ไป admin ว่ามี pending นานเกิน
- Audit log: ทุก view ของรูปใน review queue ถูก log (`bp_reading_view` with metadata `{in_review_queue: true}`)

**Workflow**:
- Each action must include reason/note
- Audit event logged per action
- Notification to submitting อสม. if significant edit
- หลัง action: รูปลบ, `bp_reading.source_image_file_id` → null, `ocr_review_status` → "approved"/"rejected"/"edited"

**API calls**:
- `GET /api/v1/admin/review-queue/low-confidence`
- `GET /api/v1/admin/review-queue/unknown-patient`
- `POST /api/v1/admin/review-queue/{id}/approve` — body: `{edits?, notify_asm?}` (triggers image deletion)
- `POST /api/v1/admin/review-queue/{id}/reject` (triggers image deletion)

---

### 3.14 `/admin/alerts` — Patient Alert List

**Purpose**: Proactive patient monitoring

**Alert types**:
- **High BP sustained** — systolic > 160 or diastolic > 100 ติดกัน N ครั้ง
- **Trending up** — linear regression slope > threshold
- **Overdue reading** — last reading > 30 days
- **Value outlier** — single reading > 180/110 (urgent referral)
- **Missing consent** — patient has readings but no active consent (data compliance)

**Actions per alert**:
- View patient
- Mark as reviewed (with note)
- Escalate (placeholder for Phase 2 doctor workflow)
- Contact อสม. (suggest visit)

**API calls**:
- `GET /api/v1/admin/alerts?type=&status=unreviewed`
- `POST /api/v1/admin/alerts/{id}/review` — body: `{note}`

---

### 3.15 `/admin/reports` — Report Builder + Export

**Purpose**: Generate reports for internal use or (future) regulatory submission

**Report templates (MVP)**:
1. **Monthly BP summary** — per patient, avg/min/max/count
2. **อสม. activity report** — readings count, patients active, last action
3. **Consent audit trail** — all consent grants/withdrawals in period
4. **Data export (raw)** — all readings in date range (CSV)
5. **High-risk patient list** — patients meeting alert criteria

**Report configuration**:
- Date range
- Filters (patient, อสม., severity)
- Format: CSV (MVP), PDF (Phase 2), Excel (Phase 2)
- Privacy level: identified / anonymized (hash patient IDs)

**Generation flow**:
1. Admin configures report
2. Click "Generate"
3. Backend job processes async (large reports)
4. Download link emailed / shown when ready
5. Downloads expire after 24h (signed URL)

**API calls**:
- `POST /api/v1/admin/reports` — body: `{template, config}`
- `GET /api/v1/admin/reports/{id}/status`
- `GET /api/v1/admin/reports/{id}/download` (signed URL)

**Audit events**:
- `data_export` with metadata `{template, row_count, format, privacy_level}`

---

### 3.16 `/admin/audit-log` — Audit Log Viewer

**Purpose**: PDPA compliance audit trail

> **v1.1 DUAL-SOURCE NOTE (decision 4.4):** หน้านี้ query records จาก **2 tables** + merge ในหน้าเดียว:
> - `audit_logs` (new, BigInt PK + JSONB metadata) — รับ write ตั้งแต่ v1.1 MVP launch
> - `admin_audit_logs` (legacy, Integer PK + Text details) — read-only, records ที่เขียนก่อน transition
> - ทั้ง backend union + merge by `created_at desc` ตอน return
> - Filter field `source` ใน response: "new" | "legacy" (ให้ UI distinguish ได้)

**Columns**:
- Timestamp
- Actor (user + role)
- Action
- Target (user/resource)
- Result (success/failure)
- From IP
- Metadata (expandable)

**Filters**:
- Date range (default last 7 days)
- Actor (dropdown of org members)
- Action type (multi-select)
- Target user
- Success/failure

**Search**:
- By request_id
- By target_id
- Free text in metadata (JSONB ~ operator)

**Pagination**: server-side, max 100 rows/page

**Export**:
- CSV (for offline audit)
- Filtered rows only

**API calls**:
- `GET /api/v1/admin/audit?start=&end=&actor=&action=&page=&limit=`
- `POST /api/v1/admin/audit/export`

---

### 3.17 `/admin/settings` — Admin Settings

**Tabs**:

#### 3.17.1 Profile
- Edit name, email, phone (phone change triggers re-verify)
- Profile photo (optional)

#### 3.17.2 Security
- Change password (current + new x2)
- Enable/disable 2FA (TOTP setup)
- Recovery codes (generate + download once)
- Active sessions (list + revoke)

#### 3.17.3 Organization
- Edit org profile (name, address, contact)
- Re-accept latest ToS version (if updated)
- View organization members (other admins — multi-admin in Phase 2)

#### 3.17.4 Transfer Ownership
- **IMPORTANT**: If admin is sole owner, must designate replacement before deactivating
- Flow:
  1. Choose replacement user (must be in same org + role=`rpsst_admin` or promote)
  2. Require password confirmation
  3. New admin receives notification + must accept
  4. On acceptance: original admin can be deactivated
- Superadmin recovery: if admin becomes unavailable (illness, departure), superadmin can reassign

**API calls**:
- `PATCH /api/v1/admin/profile`
- `POST /api/v1/admin/security/change-password`
- `POST /api/v1/admin/security/enable-2fa` → returns TOTP secret + QR
- `POST /api/v1/admin/security/verify-2fa-setup`
- `GET /api/v1/admin/security/sessions`
- `DELETE /api/v1/admin/security/sessions/{id}`
- `POST /api/v1/admin/organization/transfer-ownership` — body: `{new_owner_user_id, password}`
- `POST /api/v1/admin/organization/accept-transfer`

---

## 4. Global UX Requirements

### 4.1 Layout
- Top nav: org name + admin name (dropdown: settings, logout)
- Left sidebar: navigation (expandable groups)
- Main content: page content + breadcrumbs
- Footer: version, support contact, privacy/terms links

### 4.2 Responsiveness
- Desktop-first (admin usually at PC)
- Tablet-compatible (sidebar collapsible)
- Mobile: basic functions only (view, no bulk actions)

### 4.3 Localization
- EN / TH switcher (default TH)
- Date/time: TH Buddhist calendar option + Gregorian
- Number: TH-style comma separator

### 4.4 Notifications / Toasts
- Success: green, auto-dismiss 3s
- Warning: yellow, manual dismiss
- Error: red, manual dismiss + log to Sentry

### 4.5 Confirmations
- Destructive actions (delete, suspend, withdraw consent): modal with typed confirmation (e.g., type patient name to confirm)
- Bulk actions on > 5 records: always confirm
- Show summary of what will be affected

### 4.6 Loading / Skeleton states
- Skeleton loaders for lists/tables
- Spinner for forms submission
- Progress bar for long operations (report generation, CSV import)

### 4.7 Error handling
- Network errors: retry button + toast
- Permission denied (403): clear message + suggest action
- Not found (404): helpful page + breadcrumb back
- Server error (500): friendly message + "report this" link

### 4.8 Accessibility
- WCAG AA minimum
- Keyboard navigation for all actions
- Focus indicators
- Aria labels on icon buttons

---

## 5. API Contract (Summary)

### 5.1 Authentication

```
POST   /api/v1/admin/auth/login
POST   /api/v1/admin/auth/verify-2fa
POST   /api/v1/admin/auth/logout
POST   /api/v1/admin/auth/refresh
POST   /api/v1/admin/auth/forgot-password
POST   /api/v1/admin/auth/reset-password
POST   /api/v1/admin/onboarding/accept-terms
GET    /api/v1/admin/my-orgs                    # v1.1: list user's active org memberships
POST   /api/v1/auth/select-org                   # v1.1: switch active org, re-issue JWT
```

### 5.2 Organization

```
GET    /api/v1/admin/organization
PATCH  /api/v1/admin/organization
POST   /api/v1/admin/organization/transfer-ownership
POST   /api/v1/admin/organization/accept-transfer
```

### 5.3 อสม.

```
GET    /api/v1/admin/asm
POST   /api/v1/admin/asm
GET    /api/v1/admin/asm/{id}
PATCH  /api/v1/admin/asm/{id}
POST   /api/v1/admin/asm/{id}/suspend
POST   /api/v1/admin/asm/{id}/reactivate
POST   /api/v1/admin/asm/{id}/pairing-code
GET    /api/v1/admin/asm/{id}/patients
GET    /api/v1/admin/asm/{id}/activity
GET    /api/v1/admin/asm/{id}/statistics
```

### 5.4 Patients

```
GET    /api/v1/admin/patients
POST   /api/v1/admin/patients
GET    /api/v1/admin/patients/{id}
PATCH  /api/v1/admin/patients/{id}
POST   /api/v1/admin/patients/{id}/deactivate
POST   /api/v1/admin/patients/import
POST   /api/v1/admin/patients/export
POST   /api/v1/admin/patients/bulk-assign
GET    /api/v1/admin/patients/{id}/readings
GET    /api/v1/admin/patients/{id}/consent
GET    /api/v1/admin/patients/{id}/assignments
GET    /api/v1/admin/patients/{id}/audit
```

### 5.5 Care Assignments

```
GET    /api/v1/admin/assignments
POST   /api/v1/admin/assignments
POST   /api/v1/admin/assignments/transfer
POST   /api/v1/admin/assignments/end
```

### 5.6 Consent

```
GET    /api/v1/admin/consent
GET    /api/v1/admin/consent/{id}
POST   /api/v1/admin/consent
PATCH  /api/v1/admin/consent/{id}/withdraw
```

### 5.7 Readings

```
GET    /api/v1/admin/readings
GET    /api/v1/admin/readings/{id}
PATCH  /api/v1/admin/readings/{id}
DELETE /api/v1/admin/readings/{id}
```

### 5.8 Review Queue

```
GET    /api/v1/admin/review-queue/low-confidence
GET    /api/v1/admin/review-queue/unknown-patient
POST   /api/v1/admin/review-queue/{id}/approve
POST   /api/v1/admin/review-queue/{id}/reject
```

### 5.9 Alerts

```
GET    /api/v1/admin/alerts
POST   /api/v1/admin/alerts/{id}/review
```

### 5.10 Reports

```
POST   /api/v1/admin/reports
GET    /api/v1/admin/reports/{id}/status
GET    /api/v1/admin/reports/{id}/download
GET    /api/v1/admin/reports/templates
```

### 5.11 Audit

```
GET    /api/v1/admin/audit
POST   /api/v1/admin/audit/export
```

### 5.12 Dashboard

```
GET    /api/v1/admin/dashboard/kpi
GET    /api/v1/admin/dashboard/recent-activity
GET    /api/v1/admin/dashboard/review-queue-summary
GET    /api/v1/admin/dashboard/bp-trend
GET    /api/v1/admin/dashboard/asm-activity
```

### 5.13 Settings

```
PATCH  /api/v1/admin/profile
POST   /api/v1/admin/security/change-password
POST   /api/v1/admin/security/enable-2fa
POST   /api/v1/admin/security/disable-2fa
POST   /api/v1/admin/security/verify-2fa-setup
GET    /api/v1/admin/security/recovery-codes
GET    /api/v1/admin/security/sessions
DELETE /api/v1/admin/security/sessions/{id}
```

---

## 6. Frontend Implementation Notes

### 6.1 Directory structure (Next.js 16)

```
frontend/app/admin/
├── layout.tsx                    # Admin layout with nav
├── page.tsx                      # Dashboard home
├── login/page.tsx
├── onboarding/page.tsx
├── organization/page.tsx
├── asm/
│   ├── page.tsx                  # List
│   ├── new/page.tsx              # Create
│   └── [id]/page.tsx             # Detail
├── patients/
│   ├── page.tsx
│   ├── new/page.tsx
│   ├── import/page.tsx
│   └── [id]/
│       ├── page.tsx
│       └── edit/page.tsx
├── assignments/page.tsx
├── consent/
│   ├── page.tsx
│   └── [id]/page.tsx
├── readings/
│   ├── page.tsx
│   └── [id]/page.tsx
├── review-queue/page.tsx
├── alerts/page.tsx
├── reports/page.tsx
├── audit-log/page.tsx
└── settings/
    ├── page.tsx
    ├── security/page.tsx
    ├── organization/page.tsx
    └── users/page.tsx

frontend/components/admin/
├── nav/
├── dashboard/
├── patients/
├── asm/
├── consent/
├── readings/
└── shared/
```

### 6.2 State management

- **Server state**: TanStack Query (react-query) — already in stack
- **Form state**: react-hook-form + Zod validation
- **Global UI state**: Zustand or React Context (minimal)
- **Auth state**: Context + cookies (HTTP-only JWT)

### 6.3 Key UI components (shadcn/ui)

- DataTable (with pagination, filtering, sorting)
- Modal / Dialog for confirmations
- Toast notifications
- Form components (Input, Select, Checkbox, RadioGroup)
- Date range picker
- Charts (recharts)
- Command palette (Cmd+K for quick navigation)

### 6.4 Route protection

- Middleware in `frontend/proxy.ts`:
  - Check auth cookie
  - Verify JWT signature (on server)
  - Check role (must be `rpsst_admin` for `/admin/*`)
  - Redirect to login if unauthorized

### 6.5 Permission enforcement on UI

- Hide buttons/sections user doesn't have permission for
- Backend is source of truth — UI hides for UX, backend enforces security
- Example: Only show "Withdraw consent" if user has `WITHDRAW_CONSENT_IN_ORG` permission

---

## 7. Security Considerations

### 7.1 Session management
- JWT TTL: 8 hours
- Refresh token: 30 days (in HTTP-only cookie)
- Force logout on role change
- Max concurrent sessions per admin: 3 (configurable)

### 7.2 CSRF protection
- Use SameSite cookies (strict)
- CSRF token for state-changing operations
- Next.js 16 built-in support

### 7.3 Rate limiting
- Login: 5 attempts / 15 min / IP + per account
- Password reset: 3 / hour / account
- API (general): 100 req / min / user
- Export: 10 reports / hour / admin

### 7.4 Data access
- All cross-user access (viewing patient, reading data) MUST go through RBAC middleware
- Bulk operations (CSV import, mass assign) MUST validate each row's permission
- Export MUST audit log with full metadata

### 7.5 Input validation
- Server-side validation mandatory (Pydantic)
- XSS: sanitize all rendered text
- SQL injection: SQLAlchemy ORM only (no raw SQL from user input)

---

## 8. Acceptance Criteria (for dev done)

### 8.1 Functional
- [ ] Admin can login + complete onboarding (ToS + org setup)
- [ ] Admin can create/edit/suspend อสม. and generate pairing codes
- [ ] Admin can create/edit/deactivate proxy patients with care assignments
- [ ] Admin can view and manage consent records (grant, withdraw, upload scans)
- [ ] Admin can view all BP readings + edit + delete with audit
- [ ] OCR review queue processes items correctly
- [ ] Reports generate + download working
- [ ] Audit log complete + searchable + exportable
- [ ] Dashboard KPIs accurate
- [ ] Settings: password change, 2FA, ownership transfer

### 8.2 Non-functional
- [ ] Load time: initial < 3s, subsequent < 1s (cached)
- [ ] 100% of cross-user data access logged
- [ ] Permission checks on every API endpoint (unit tests)
- [ ] Responsive down to tablet (1024px)
- [ ] Works on Chrome/Safari/Firefox/Edge (latest 2 versions)

### 8.3 Security
- [ ] Pen test basic (OWASP Top 10)
- [ ] CSP headers configured
- [ ] HTTPS only (HSTS)
- [ ] Secrets in environment vars (not committed)

---

## 9. Out of Scope (Phase 2+)

- Multi-admin per org (Phase 2 — need role hierarchy)
- Doctor role + workflows
- Telemedicine video consultation
- Smart อสม. / HDC data sync
- Bulk CSV import with error recovery
- PDF report generation (Excel only MVP)
- Email templates / automated communication
- Mobile app (admin can use responsive web)
- Analytics dashboard (advanced charts, comparative views)

---

**End of ADMIN_WEB_SPEC.md**
