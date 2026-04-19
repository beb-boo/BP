---
title: "Generalize Org Support — Rename & Gap Close Plan"
aliases:
  - "Generalize Plan"
  - "Rename Plan"
tags:
  - refactor
  - v2-asm-org
  - rename
  - generalize
order: 0.6
status: actionable
version: 1.0
updated: 2026-04-19
summary: "Rename rpsst/asm-specific names to generic org names + close gaps for clinic/hospital support + define hybrid self-measure policy. Executable by Claude Code."
---

# Generalize Org Support — Rename & Gap Close

> **Purpose:** ทำให้ v2 plan + code รองรับ **ทุกประเภทองค์กร** (รพ.สต., คลินิก, โรงพยาบาล, corporate wellness) ตั้งแต่ต้น — ไม่ต้อง refactor ทีหลัง
>
> **Executor:** Claude Code
> **Reviewer:** Pornthep (after execution)
> **Scope:** Plan documents (17 files) + future code references
>
> **3 work streams:**
> 1. **RENAME** — rpsst/asm-specific names → generic org names
> 2. **DEFINE** — self-measure data auto-visible policy for hybrid users
> 3. **GAP CLOSE** — hybrid onboarding, clinic/hospital role mapping, consent scope generalization

---

## 1. RENAME — Full Mapping Table

### 1.1 Role enum values

| Old | New | Rationale |
|-----|-----|-----------|
| `rpsst_admin` | `org_admin` | Generic: admin ของ org ใด ๆ (รพ.สต., คลินิก, รพ.) |
| `rpsst_staff` | `org_staff` | Generic: staff ปกติใน org ใด ๆ (Phase 2) |
| `asm` | `caregiver` | Generic: ผู้ดูแลที่ไปวัดให้คนไข้ (อสม., พยาบาล, ผู้ช่วยแพทย์) |
| `patient_self` | `patient_self` | ไม่เปลี่ยน — generic อยู่แล้ว |
| `patient_proxy` | `patient_proxy` | ไม่เปลี่ยน — generic อยู่แล้ว |
| `superadmin` | `superadmin` | ไม่เปลี่ยน |
| `doctor` | `doctor` | ไม่เปลี่ยน |

**หมายเหตุ:** `asm` → `caregiver` เพราะ:
- คลินิก: พยาบาลวัดให้คนไข้ = caregiver function เดียวกับ อสม.
- รพ.: ผู้ช่วยแพทย์วัดให้ = caregiver function เดียวกัน
- Corporate: wellness coordinator วัดให้พนักงาน = caregiver
- `field_worker` พิจารณาแล้วแคบเกินไป (คลินิก staff ไม่ได้ลงภาคสนาม)

### 1.2 API URL namespaces

| Old | New | Used by |
|-----|-----|---------|
| `/api/v1/rpsst/*` | `/api/v1/org/*` | Org-level admin endpoints |
| `/api/v1/asm/*` | `/api/v1/caregiver/*` | Caregiver (อสม./พยาบาล) endpoints |
| `/api/v1/doctor/*` | `/api/v1/doctor/*` | ไม่เปลี่ยน (legacy B2C) |
| `/api/v1/admin/*` | `/api/v1/admin/*` | ไม่เปลี่ยน (existing admin) |

### 1.3 Consent scope enum values

| Old | New | Rationale |
|-----|-----|-----------|
| `asm_collect` | `caregiver_collect` | Generic: ผู้ดูแลคนไหนก็ตามเก็บข้อมูล |
| `rpsst_view` | `org_view` | Generic: admin/staff ของ org ใด ๆ ดูข้อมูล |
| `doctor_view` | `doctor_view` | ไม่เปลี่ยน |
| `research_anonymized` | `research_anonymized` | ไม่เปลี่ยน |
| `data_export_to_smart_osm` | `data_export_to_smart_osm` | ไม่เปลี่ยน (specific integration) |

### 1.4 MeasurementContext enum values

| Old | New | Rationale |
|-----|-----|-----------|
| `asm_field_visit` | `caregiver_field_visit` | Generic |
| `asm_community` | `caregiver_community` | Generic |
| `self_home` | `self_home` | ไม่เปลี่ยน |
| `self_other` | `self_other` | ไม่เปลี่ยน |
| `clinic_visit` | `clinic_visit` | ไม่เปลี่ยน |
| `other` | `other` | ไม่เปลี่ยน |

### 1.5 AuditAction enum values — selective rename

| Old | New |
|-----|-----|
| (no asm/rpsst-specific values) | — |

AuditAction ใช้ generic names อยู่แล้ว (`care_assignment_create`, `patient_view`, etc.) — ไม่ต้อง rename

### 1.6 Permission names

| Old | New |
|-----|-----|
| `CREATE_RPSST` | `CREATE_ORG` |
| `CREATE_ASM_IN_ORG` | `CREATE_CAREGIVER_IN_ORG` |
| `VIEW_ASSIGNED_PATIENT` | `VIEW_ASSIGNED_PATIENT` (ไม่เปลี่ยน) |
| `CREATE_READING_FOR_ASSIGNED` | `CREATE_READING_FOR_ASSIGNED` (ไม่เปลี่ยน) |

### 1.7 Table/column names — ไม่เปลี่ยน

Tables ชื่อ generic อยู่แล้ว: `organizations`, `organization_members`, `care_assignments`, `consent_records`, `audit_logs`

ไม่มี table/column ที่มี `rpsst` หรือ `asm` อยู่ — schema ใช้ได้ทันที

### 1.8 Frontend route paths

| Old | New |
|-----|-----|
| `/admin/asm` | `/admin/caregivers` |
| `/admin/asm/new` | `/admin/caregivers/new` |
| `/admin/asm/[id]` | `/admin/caregivers/[id]` |
| `/asm/*` (PWA routes) | `/caregiver/*` |
| `/asm/login` | `/caregiver/login` |
| `/asm/patients` | `/caregiver/patients` |
| `/asm/record/*` | `/caregiver/record/*` |
| `/asm/history` | `/caregiver/history` |
| `/asm/profile` | `/caregiver/profile` |

### 1.9 UI label strings (i18n)

Plan docs ใช้ "อสม." ในหลายที่ — **ไม่ rename ในภาษาไทย** เพราะ:
- ผู้ใช้ไทยที่เป็น อสม. จริง ๆ ต้องเห็นคำว่า "อสม." ใน UI
- แต่ **i18n key** ต้องเป็น generic: `caregiver.title` (ไม่ใช่ `asm.title`)
- ค่า display ต่าง context:

```typescript
// locales/th.ts
caregiver: {
  title: "ผู้ดูแล",                    // generic
  title_asm: "อาสาสมัครสาธารณสุข (อสม.)", // specific to รพ.สต.
  title_nurse: "พยาบาล",              // specific to clinic
  title_assistant: "ผู้ช่วยแพทย์",      // specific to hospital
}

// locales/en.ts
caregiver: {
  title: "Caregiver",
  title_asm: "Health Volunteer (ASM)",
  title_nurse: "Nurse",
  title_assistant: "Medical Assistant",
}
```

**Display logic:** ดูจาก `organization.type`:
- `rpsst` → show `title_asm`
- `clinic` → show `title_nurse`
- `hospital` → show `title_assistant`
- `other` / default → show `title` (generic)

### 1.10 Metadata / via_relationship values

| Old | New |
|-----|-----|
| `via_relationship: "care_assignment"` | ไม่เปลี่ยน (generic อยู่แล้ว) |
| `via_relationship: "doctor_patient"` | ไม่เปลี่ยน |

---

## 2. RENAME — Files to Update

### 2.1 Plan documents (in `plan/v2-asm-org-support/`)

Claude Code ต้อง search & replace ในไฟล์เหล่านี้:

| File | What to rename |
|------|----------------|
| `ORG_FOUNDATION.md` | Enum values, role names, URL namespaces, consent scopes, permission names, migration script comments, backfill LEGACY_ROLE_MAP |
| `PLAN_REVIEW_RESPONSE.md` | Decision references (Q2, Q3, G5), role names, namespacing table |
| `ADMIN_WEB_SPEC.md` | Route paths (`/admin/asm` → `/admin/caregivers`), role references, API endpoints |
| `ASM_PWA_SPEC.md` | **Rename file** → `CAREGIVER_PWA_SPEC.md`; all route paths, role references, API endpoints |
| `CONSENT_FLOW_SPEC.md` | Consent scope names, role references |
| `INFRASTRUCTURE_SETUP.md` | Feature flag references, env var names |
| `MIGRATION_STRATEGY.md` | Migration script names, enum references |
| `BACKUP_AND_MIGRATION_SPEC.md` | Minimal (no rpsst/asm-specific content) |
| `INDEX.md` | File references, reading order |
| `MVP_PILOT_SCOPE.md` | Persona names, role references |
| `SCALABILITY_PLAN.md` | Role references |
| `LEGACY_DOCS_MIGRATION.md` | Role references, consent scope names |
| `PDPA_COMPLIANCE.md` | Role references |
| `DATA_RETENTION_POLICY.md` | Role references |
| `BREACH_RESPONSE_RUNBOOK.md` | Role references |
| `CONSENT_FORMS.md` | Scope names, role references |
| `ORG_TERMS_OF_SERVICE.md` | Role references |

### 2.2 Search patterns (for Claude Code to grep)

```bash
# In plan/v2-asm-org-support/ directory:

# Role enums
grep -rn "rpsst_admin" .
grep -rn "rpsst_staff" .
grep -rn "\"asm\"" .          # careful: match enum value, not Thai word อสม.
grep -rn "'asm'" .
grep -rn "UserRole.asm" .
grep -rn "role=asm" .
grep -rn "role=\"asm\"" .

# URL namespaces
grep -rn "/api/v1/rpsst" .
grep -rn "/api/v1/asm/" .
grep -rn "/asm/" .            # frontend routes

# Consent scopes
grep -rn "asm_collect" .
grep -rn "rpsst_view" .

# Measurement contexts
grep -rn "asm_field_visit" .
grep -rn "asm_community" .

# Permission names
grep -rn "CREATE_RPSST" .
grep -rn "CREATE_ASM_IN_ORG" .

# Frontend directory references
grep -rn "app/asm/" .
grep -rn "admin/asm" .
```

### 2.3 Replace rules

**IMPORTANT:** เวลา rename ต้องระวังไม่แทน **Thai text** ที่ยังต้องเป็น "อสม." และ "รพ.สต.":
- `อสม.` ในข้อความอธิบาย (comments, descriptions, UI labels) → **คงไว้** (Thai term ที่ถูกต้อง)
- `asm` ใน enum/code/URL/file path → **เปลี่ยน** เป็น `caregiver`
- `รพ.สต.` ในข้อความอธิบาย → **คงไว้**
- `rpsst` ใน enum/code/URL → **เปลี่ยน** เป็น `org`

**Rule of thumb:** ถ้า string อยู่ใน code block (```) หรือ enum definition → rename; ถ้าอยู่ในข้อความภาษาไทย → keep

### 2.4 File rename

```bash
# Rename spec file
mv plan/v2-asm-org-support/ASM_PWA_SPEC.md plan/v2-asm-org-support/CAREGIVER_PWA_SPEC.md
```

Update ทุก reference ใน docs อื่นที่อ้าง `ASM_PWA_SPEC` → `CAREGIVER_PWA_SPEC`

---

## 3. DEFINE — Self-Measure Auto-Visible Policy

### 3.1 Policy decision

**DECIDED: Auto-visible (Option A)**

เมื่อ user ที่เป็น `hybrid` หรือ `self_managed` (ที่มี `managed_by_organization_id` set) วัดเองที่บ้าน:
- BP reading **ปรากฏใน org dashboard ทันที** (ถ้ามี active consent scope `org_view`)
- **ไม่ต้อง opt-in per reading** (consent = blanket per scope, ไม่ใช่ per-entry)
- Caregiver ที่ได้รับ assign เห็นข้อมูลนี้ได้ (ถ้ามี active consent `caregiver_collect`)

### 3.2 Data flow diagram

```
Hybrid patient (มี login เอง + อยู่ใน org)
  │
  ├─ วัดเอง (self_home)
  │   └─ POST /api/v1/bp-records (existing v1 endpoint)
  │       └─ BP record created with:
  │           user_id = patient.id
  │           measured_by_user_id = NULL (ตัวเอง)
  │           measurement_context = self_home
  │           organization_id = patient.managed_by_organization_id
  │           ← org_id populated automatically from user profile
  │
  ├─ Caregiver วัดให้ (caregiver_field_visit)
  │   └─ POST /api/v1/caregiver/readings
  │       └─ BP record created with:
  │           user_id = patient.id
  │           measured_by_user_id = caregiver.id
  │           measurement_context = caregiver_field_visit
  │           organization_id = caregiver's active org
  │
  └─ ทั้ง 2 flow → same `blood_pressure_records` table
      → same patient history (merged by patient_id + measured_at)
      → org dashboard sees ALL (ถ้า consent active)
      → UI แยกด้วย icon: 🏠 self-measured vs 👤 caregiver-measured
```

### 3.3 Visibility rules

| Who views | Sees self-measured? | Sees caregiver-measured? | Condition |
|-----------|:-------------------:|:------------------------:|-----------|
| Patient (self) | ✅ Always | ✅ Always | Owner of data |
| Caregiver (assigned) | ✅ | ✅ | Active `caregiver_collect` consent + active `care_assignment` |
| Org admin | ✅ | ✅ | Active `org_view` consent + patient in same org |
| Doctor (B2C legacy) | ✅ | ✅ | Active `DoctorPatient` relationship |
| Other patients | ❌ | ❌ | Never |

### 3.4 Consent withdrawal effect on self-measure

| Scope withdrawn | Effect on self-measured data |
|----------------|----------------------------|
| `caregiver_collect` | Caregiver ไม่เห็นอีก (ทั้ง self + caregiver measured). Patient ยังเห็นเอง |
| `org_view` | Org admin ไม่เห็นอีก. Patient ยังเห็นเอง |
| Both withdrawn | Patient เห็นข้อมูลตัวเอง only. Org/caregiver ไม่เห็น. Data ยังอยู่ (ไม่ลบ) |

### 3.5 Implementation notes

**Existing v1 endpoint `/api/v1/bp-records`:**
- ปัจจุบัน: สร้าง record with `user_id = current_user.id`, ไม่มี `organization_id`
- **v2 change:** ถ้า `current_user.managed_by_organization_id` is not null → auto-set `organization_id` ใน record
- **ไม่ break** existing flow: user ไม่มี org → `organization_id = null` → เหมือนเดิม

**Query for org dashboard:**
```python
# Admin/caregiver ดู readings ของ patient ที่มี consent
readings = db.query(BloodPressureRecord).filter(
    BloodPressureRecord.user_id == patient_id,
    # No filter on measured_by — show ALL sources
).order_by(desc(BloodPressureRecord.measured_at))

# Frontend: distinguish by measured_by_user_id
# null = self-measured (show 🏠 icon)
# not null = caregiver-measured (show 👤 icon + caregiver name)
```

---

## 4. GAP CLOSE — Hybrid User Onboarding

### 4.1 What is a hybrid user?

`AccountType.hybrid` = ชาวบ้าน/คนไข้ที่:
- **มี login เอง** (phone/email + password หรือ Telegram OTP)
- **สังกัด org** (มี `managed_by_organization_id`)
- **มี caregiver assign** (optional — caregiver ก็มาวัดให้ได้)
- **วัดเองได้** (ใช้แอปเดิม เหมือน v1 self_managed)

### 4.2 Onboarding flows (3 paths)

#### Path A: Admin creates → patient self-activates (recommended for clinic/hospital)

```
1. Org admin สร้างบัญชี hybrid patient ในระบบ:
   POST /api/v1/admin/patients
   Body: {
     full_name, phone, dob, gender,
     account_type: "hybrid",
     assign_to_caregiver_id: optional
   }
   Backend creates:
   - User record (account_type=hybrid, managed_by_organization_id=admin's org)
   - Random temporary password (hashed, stored)
   - Care assignment (if caregiver assigned)

2. Admin ให้ข้อมูล login แก่คนไข้:
   - เบอร์โทร + temporary password (พิมพ์ใบ / บอกปากเปล่า / SMS)
   - หรือ pairing code 6 หลัก (เหมือน caregiver flow)

3. คนไข้ login ครั้งแรก:
   - เปิดแอป → ใส่เบอร์ + temp password
   - Force change password (ใช้ flow v1 เดิม)
   - Accept ToS + Privacy Policy
   - Optional: ผูก Telegram (เพื่อรับ OTP ทีหลัง)
   
4. คนไข้ใช้งาน:
   - วัดเอง → ข้อมูลไปรวมใน org (ถ้ามี consent)
   - caregiver มาวัดให้ → ข้อมูลไปรวมเช่นกัน
```

#### Path B: Patient self-registers → admin links to org (recommended for รพ.สต./อสม.)

```
1. ชาวบ้าน register เอง (v1 flow เดิม):
   POST /api/v1/auth/register
   Body: { phone, password, full_name, role: "patient" }
   → User created: account_type=self_managed, managed_by_organization_id=null

2. Admin ค้นหา user แล้ว link เข้า org:
   POST /api/v1/admin/patients/{user_id}/link-to-org
   Body: { organization_id, assign_to_caregiver_id, consent_pending: true }
   Backend:
   - Update user: account_type → hybrid, managed_by_organization_id → org.id
   - Create care_assignment (if caregiver assigned)
   - Mark consent as pending (caregiver ต้องไปเก็บ)

3. Caregiver ไปเยี่ยม → เก็บ consent (กระดาษ + digital)

4. ชาวบ้าน ยังใช้แอปเดิม ได้เหมือนปกติ
   + ข้อมูลเริ่ม visible ต่อ org (หลัง consent active)
```

#### Path C: Caregiver creates hybrid on field visit (convenience)

```
1. Caregiver อยู่ภาคสนาม เจอชาวบ้านที่มีมือถือ+อยากใช้เอง
2. Caregiver PWA → "สร้างคนไข้ใหม่" → เลือก account_type = hybrid
3. Backend creates user + care_assignment + ส่ง activation link ทาง SMS/Telegram
4. ชาวบ้าน activate เอง (set password)
5. Caregiver เก็บ consent ทันที
```

### 4.3 Hybrid-specific API endpoints (NEW — add to spec)

```
POST /api/v1/admin/patients/{user_id}/link-to-org
  Body: { organization_id, assign_to_caregiver_id?, consent_pending? }
  Guard: org_admin of target org
  Effect: user.account_type → hybrid, user.managed_by_organization_id → org.id

POST /api/v1/admin/patients/{user_id}/unlink-from-org
  Body: { reason }
  Guard: org_admin of target org
  Effect: user.account_type → self_managed, user.managed_by_organization_id → null
  Note: care_assignments ended, consent withdrawn (if patient confirms)

POST /api/v1/caregiver/patients/create-hybrid
  Body: { full_name, phone, dob?, gender?, notes? }
  Guard: caregiver in active org
  Effect: create user (hybrid) + care_assignment + activation pending

POST /api/v1/auth/activate
  Body: { activation_token, new_password }
  Effect: set password + mark as activated
  (Reuse existing password reset flow with different purpose)
```

### 4.4 UI changes for hybrid support

**Admin web — Patient creation form (`/admin/patients/new`):**
- Add radio: "ประเภทบัญชี":
  - `proxy_managed` — "ไม่มี login (ผู้ดูแลบันทึกให้)" (default for รพ.สต.)
  - `hybrid` — "มี login + ผู้ดูแลบันทึกให้ได้" (default for clinic)
  - `self_managed_link` — "ผูกบัญชีเดิม" (search existing user → link to org)

**Admin web — Patient detail (`/admin/patients/[id]`):**
- Show account type badge: "proxy" / "hybrid" / "self"
- For hybrid: show "last self-measured" + "last caregiver-measured" separately
- Action: "Unlink from org" (with confirmation + consent withdrawal)

**Caregiver PWA — Patient detail:**
- For hybrid patients: note "คนไข้วัดเองได้" badge
- History: icon distinguish self vs caregiver measured (🏠 vs 👤)

---

## 5. GAP CLOSE — Clinic/Hospital Role Mapping

### 5.1 Role mapping per org type

| Org type | `org_admin` | `org_staff` | `caregiver` | `doctor` | Notes |
|----------|:-----------:|:-----------:|:-----------:|:--------:|-------|
| `rpsst` (รพ.สต.) | ผอ.รพ.สต. | เจ้าหน้าที่ | อสม. | แพทย์ที่ปรึกษา | MVP pilot |
| `clinic` | เจ้าของคลินิก | receptionist | พยาบาล | แพทย์ | Phase 2 |
| `hospital` | admin ฝ่าย | เจ้าหน้าที่ | พยาบาล/ผู้ช่วย | แพทย์ | Phase 2+ |
| `other` (corporate) | HR admin | — | wellness coordinator | — | Phase 3 |

### 5.2 Functional equivalence

**ทุก org type ใช้ permissions เดียวกัน** — ต่างแค่ display label:

| Permission | ทำอะไร | ใช้ได้กับ roles |
|------------|--------|----------------|
| `CREATE_CAREGIVER_IN_ORG` | เพิ่ม caregiver ใหม่ | `org_admin` |
| `CREATE_PROXY_PATIENT_IN_ORG` | สร้างคนไข้ proxy | `org_admin`, `caregiver` |
| `VIEW_ASSIGNED_PATIENT` | ดูข้อมูลคนไข้ที่ assign | `caregiver` |
| `CREATE_READING_FOR_ASSIGNED` | บันทึก BP ให้คนไข้ | `caregiver` |
| `VIEW_PATIENT_IN_ORG` | ดูข้อมูลคนไข้ทั้ง org | `org_admin`, `org_staff` |
| `MANAGE_ASSIGNMENTS` | จัดการ care assignments | `org_admin` |
| `MANAGE_CONSENT` | จัดการ consent records | `org_admin` |
| `VIEW_AUDIT_LOG` | ดู audit log ของ org | `org_admin` |

### 5.3 Display label resolution

```python
# app/utils/org_display.py

ORG_ROLE_LABELS = {
    # org_type → role → {th, en}
    "rpsst": {
        "org_admin": {"th": "ผู้อำนวยการ รพ.สต.", "en": "RPSST Director"},
        "org_staff": {"th": "เจ้าหน้าที่ รพ.สต.", "en": "RPSST Staff"},
        "caregiver": {"th": "อาสาสมัครสาธารณสุข (อสม.)", "en": "Health Volunteer (ASM)"},
        "doctor": {"th": "แพทย์ที่ปรึกษา", "en": "Consulting Doctor"},
    },
    "clinic": {
        "org_admin": {"th": "ผู้ดูแลคลินิก", "en": "Clinic Administrator"},
        "org_staff": {"th": "เจ้าหน้าที่", "en": "Staff"},
        "caregiver": {"th": "พยาบาล", "en": "Nurse"},
        "doctor": {"th": "แพทย์", "en": "Doctor"},
    },
    "hospital": {
        "org_admin": {"th": "ผู้ดูแลระบบ", "en": "System Administrator"},
        "org_staff": {"th": "เจ้าหน้าที่", "en": "Staff"},
        "caregiver": {"th": "พยาบาล/ผู้ช่วยแพทย์", "en": "Nurse/Medical Assistant"},
        "doctor": {"th": "แพทย์", "en": "Doctor"},
    },
    "_default": {
        "org_admin": {"th": "ผู้ดูแลระบบ", "en": "Administrator"},
        "org_staff": {"th": "เจ้าหน้าที่", "en": "Staff"},
        "caregiver": {"th": "ผู้ดูแล", "en": "Caregiver"},
        "doctor": {"th": "แพทย์", "en": "Doctor"},
    },
}


def get_role_label(org_type: str, role: str, lang: str = "th") -> str:
    """Get display label for a role within an org type."""
    labels = ORG_ROLE_LABELS.get(org_type, ORG_ROLE_LABELS["_default"])
    role_labels = labels.get(role, ORG_ROLE_LABELS["_default"].get(role, {}))
    return role_labels.get(lang, role)
```

---

## 6. GAP CLOSE — Consent Form per Org Type

### 6.1 Problem

Consent form ปัจจุบันเขียนเฉพาะ อสม./รพ.สต. context:
- "ข้าพเจ้ายินยอมให้ **อสม.** และ **รพ.สต.** เก็บข้อมูล..."

คลินิก/รพ. ต้องเป็น:
- "ข้าพเจ้ายินยอมให้ **พยาบาล** และ **คลินิก XYZ** เก็บข้อมูล..."

### 6.2 Solution: Templated consent with org-specific terms

```python
# consent form content is parameterized

CONSENT_TEMPLATE = {
    "th": {
        "caregiver_collect": (
            "ข้าพเจ้ายินยอมให้ {caregiver_label} และ {org_name} "
            "เก็บ ใช้ และรักษาข้อมูลสุขภาพของข้าพเจ้า "
            "เพื่อการดูแลสุขภาพตามวัตถุประสงค์ข้างต้น"
        ),
        "org_view": (
            "ข้าพเจ้ายินยอมให้เจ้าหน้าที่ {org_name} "
            "เข้าถึงข้อมูลสุขภาพของข้าพเจ้า"
        ),
    }
}

# Usage:
text = CONSENT_TEMPLATE["th"]["caregiver_collect"].format(
    caregiver_label=get_role_label(org.type, "caregiver", "th"),
    org_name=org.name
)
# Result for รพ.สต.: "...ให้ อาสาสมัครสาธารณสุข (อสม.) และ รพ.สต.เมืองเก่า เก็บ..."
# Result for clinic: "...ให้ พยาบาล และ คลินิก ABC เก็บ..."
```

### 6.3 Paper consent forms

CONSENT_FORMS.md ปัจจุบัน hardcode "อสม." — ต้อง update เป็น template:
- Header: `{org_name}` แทน "รพ.สต. เมืองเก่า"
- Body: `{caregiver_label}` แทน "อสม."
- Admin web: generate PDF from template + org data

---

## 7. GAP CLOSE — LEGACY_ROLE_MAP Update

### 7.1 Updated backfill map

```python
# v1 legacy role → v2 generic role
LEGACY_ROLE_MAP = {
    "patient": "patient_self",
    "doctor":  "doctor",
    "staff":   "superadmin",    # env-managed staff = system admin
}
```

No change needed — legacy roles don't include `rpsst_admin` or `asm` (those are v2-only values)

### 7.2 UserRole enum (final, post-rename)

```python
class UserRole(str, enum.Enum):
    """บทบาทใน application (generic, org-type independent)"""
    superadmin = "superadmin"        # ระบบ admin (เรา)
    org_admin = "org_admin"          # admin ขององค์กร (รพ.สต./คลินิก/รพ.)
    org_staff = "org_staff"          # staff ขององค์กร (Phase 2)
    doctor = "doctor"                # แพทย์
    caregiver = "caregiver"          # ผู้ดูแล (อสม./พยาบาล/ผู้ช่วยแพทย์)
    patient_self = "patient_self"    # คนไข้ login เอง
    patient_proxy = "patient_proxy"  # คนไข้ proxy (ไม่มี login)
```

---

## 8. Execution Checklist for Claude Code

### Phase 1: Rename in plan docs

```
[ ] grep all plan docs for old names (§2.2 patterns)
[ ] Apply rename mapping (§1.1 through §1.8) to each file
[ ] Rename ASM_PWA_SPEC.md → CAREGIVER_PWA_SPEC.md
[ ] Update all cross-file references to renamed file
[ ] Update INDEX.md (reading order, status dashboard, file count)
[ ] Verify no orphan references (grep for old names after rename)
```

### Phase 2: Add self-measure policy

```
[ ] Add §3 content (self-measure auto-visible) to ORG_FOUNDATION.md as new subsection
[ ] Update CAREGIVER_PWA_SPEC.md: patient detail shows 🏠/👤 icons
[ ] Update ADMIN_WEB_SPEC.md: patient detail shows self vs caregiver measured
[ ] Update CONSENT_FLOW_SPEC.md: add withdrawal effect on self-measured data
```

### Phase 3: Add hybrid onboarding

```
[ ] Add §4 content (3 onboarding paths) to CAREGIVER_PWA_SPEC.md or ORG_FOUNDATION.md §8
[ ] Add new API endpoints (§4.3) to ADMIN_WEB_SPEC.md §5 + CAREGIVER_PWA_SPEC.md §10
[ ] Update ADMIN_WEB_SPEC.md: patient creation form → account_type radio (§4.4)
[ ] Update ADMIN_WEB_SPEC.md: patient detail → link/unlink buttons
```

### Phase 4: Add role label resolution

```
[ ] Add §5.3 (org_display.py) to ORG_FOUNDATION.md §6 (RBAC section)
[ ] Add §5.1 role mapping table to ORG_FOUNDATION.md
[ ] Add §6 (consent template) to CONSENT_FLOW_SPEC.md + CONSENT_FORMS.md
```

### Phase 5: Final verification

```
[ ] grep for any remaining "rpsst_admin", "rpsst_staff", "asm" (as enum/code)
[ ] grep for any remaining "/api/v1/rpsst/", "/api/v1/asm/"
[ ] grep for any remaining "/admin/asm", "/asm/"
[ ] Verify INDEX.md file count + reading order correct
[ ] Verify PLAN_REVIEW_RESPONSE.md decisions still make sense with new names
[ ] Add changelog note to every updated file header
```

---

## 9. What NOT to change (preserve list)

- **Thai text "อสม."** ในข้อความอธิบาย → keep (เป็นคำที่ user เข้าใจ)
- **Thai text "รพ.สต."** ในข้อความอธิบาย → keep
- **File names** ของ PDPA/legal docs → keep (ไม่มี rpsst/asm ในชื่อ)
- **`DoctorPatient` table** → keep (legacy B2C, ไม่ใช่ org-related)
- **`AccessRequest` table** → keep (legacy B2C)
- **`doctor` role** → keep (generic อยู่แล้ว)
- **LEGACY_ROLE_MAP values** → keep (`"patient"`, `"doctor"`, `"staff"` = v1 legacy strings ใน DB จริง)
- **Neon branch names** → keep (ไม่เกี่ยว)
- **`data_export_to_smart_osm`** scope → keep (specific integration ชื่อถูกแล้ว)

---

## 10. Prompt สำหรับ Claude Code

```
อ่าน plan/v2-asm-org-support/GENERALIZE_ORG_PLAN.md แล้วทำตาม execution checklist §8

ขั้นตอน:
1. อ่าน spec ทั้งหมดก่อน
2. ทำ Phase 1 (rename) ก่อน — grep ทุก pattern ใน §2.2 ก่อนเริ่มแก้
3. แต่ละ phase: แก้ไฟล์ → verify ด้วย grep → commit
4. Phase 5: final verification ว่าไม่มี orphan references
5. สรุป diff summary ให้ review

Rules:
- §9 "What NOT to change" สำคัญมาก — ห้ามแก้ Thai text "อสม.", "รพ.สต."
- ใช้ edit_file dryRun ก่อนทุกครั้ง
- ถ้าไม่แน่ใจว่าจะ rename ตรงไหน → ถามก่อน
```

---

**End of GENERALIZE_ORG_PLAN.md**
