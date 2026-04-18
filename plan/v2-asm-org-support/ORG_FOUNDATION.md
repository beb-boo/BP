# Organization Foundation Plan — BP Monitor

> **Status:** Draft v1.1 — decisions from [[PLAN_REVIEW_RESPONSE]] applied
> **Last updated:** 2026-04-18
> **Owner:** Pornthep
> **Depends on:** `MVP_PILOT_SCOPE.md`, `PLAN_REVIEW_RESPONSE.md`
> **Blocks:** `ADMIN_WEB_SPEC.md`, `ASM_PWA_SPEC.md`, all PDPA implementation

> [!IMPORTANT] **v1.1 CHANGELOG** (2026-04-18)
> - §4.1.4: Removed `paper_scan_file_id` (data minimization; physical paper only)
> - §4.2.1: `users.role` column **NOT dropped** — `primary_role` added as additive column (dual-read)
> - §4.2.2: Added `measured_at` validation rules (block future, warn >7d, block >30d)
> - NEW §4.3: DoctorPatient + CareAssignment coexistence
> - NEW §4.4: License ↔ Organization relationship
> - §5.1: Migration sequence revised to respect FK dependencies
> - §5.2: `LEGACY_ROLE_MAP` for backfill (staff → superadmin, not rpsst_staff)
> - §7: AdminAuditLog → AuditLog via dual-write (no data migration)
> - §6: Multi-org support via JWT claim `active_org_id`

---

## 1. Purpose

เอกสารนี้กำหนด **schema foundation** สำหรับขยาย BP Monitor จากระบบ personal (1:1 doctor-patient) เป็นระบบองค์กร (รพ.สต. → อสม. → ชาวบ้าน) โดย:
- ไม่กระทบผู้ใช้เดิม (backward compatible)
- รองรับ PDPA ตั้งแต่ schema design
- รองรับการขยายในอนาคต (multi-รพ.สต., doctor, research)

---

## 2. Design Principles

1. **Single source of truth** — ใช้ table `users` เดียว ไม่แยก `patients`, `asm_users`, `admin_users` ออกจากกัน แบ่งด้วย role + account_type
2. **Backward compatible migration** — user เดิมทุกคน default เป็น `self_managed` + role = `patient_self` ไม่ต้องเปลี่ยนพฤติกรรม
3. **Soft delete over hard delete** — user และ org ใช้ `is_active` + `deleted_at` ไม่ลบจริง (ยกเว้น right to be forgotten)
4. **Audit everything cross-user** — ทุก action ที่เข้าถึงข้อมูลคนอื่น log หมด
5. **Encryption at rest** — PII เก็บ encrypted (Fernet ของเดิม) + hash สำหรับ index
6. **Time-bounded relationships** — care_assignment, consent มี effective_from + effective_until
7. **Explicit over implicit** — scope ของ consent ต้องชัด (ไม่ใช่ blanket "ยอมให้เข้าถึงข้อมูล")
8. **Data minimization (สำคัญ)** — เก็บเฉพาะข้อมูลที่จำเป็นต่อ purpose เท่านั้น, ทุก artifact ต้องมี retention policy ชัดเจนและ auto-delete. โดยเฉพาะรูปภาพที่อาจมี PII: หลีกเลี่ยงการเก็บถาวรเว้นแต่จำเป็นจริง ๆ

---

## 3. New Enums

```python
# app/models.py

class AccountType(str, enum.Enum):
    """ประเภทบัญชีผู้ใช้"""
    self_managed = "self_managed"      # ชาวบ้านใช้ระบบเอง (default เดิม)
    proxy_managed = "proxy_managed"    # อสม. เก็บข้อมูลให้, ชาวบ้านไม่ล็อกอิน
    hybrid = "hybrid"                  # ล็อกอินเองได้ + อสม. ช่วยบันทึกได้


class UserRole(str, enum.Enum):
    """บทบาทใน application"""
    superadmin = "superadmin"          # เรา (Anthropic-style, ทำ system ops)
    rpsst_admin = "rpsst_admin"        # admin ของ รพ.สต.
    rpsst_staff = "rpsst_staff"        # staff ปกติใน รพ.สต. (Phase 2)
    doctor = "doctor"                  # แพทย์
    asm = "asm"                        # อาสาสมัครสาธารณสุข
    patient_self = "patient_self"      # ชาวบ้านล็อกอินเอง
    patient_proxy = "patient_proxy"    # ชาวบ้าน proxy-managed (ไม่มี login)


class OrganizationType(str, enum.Enum):
    """ประเภทองค์กร"""
    rpsst = "rpsst"                    # โรงพยาบาลส่งเสริมสุขภาพตำบล
    hospital = "hospital"              # โรงพยาบาล
    clinic = "clinic"                  # คลินิก
    district_health = "district_health" # สาธารณสุขอำเภอ (Phase 2)
    provincial_health = "provincial_health" # สาธารณสุขจังหวัด (Phase 3)
    other = "other"


class MeasurementContext(str, enum.Enum):
    """บริบทของการวัด"""
    self_home = "self_home"            # วัดเองที่บ้าน (flow เดิม)
    self_other = "self_other"          # วัดเองสถานที่อื่น
    asm_field_visit = "asm_field_visit"  # อสม. ไปวัดที่บ้านชาวบ้าน
    asm_community = "asm_community"    # อสม. วัดรวมที่ชุมชน
    clinic_visit = "clinic_visit"      # วัดที่คลินิก/รพ.สต.
    other = "other"


class ConsentScope(str, enum.Enum):
    """Scope ของความยินยอม (granular)"""
    asm_collect = "asm_collect"                # ยินยอมให้ อสม. เก็บข้อมูล
    rpsst_view = "rpsst_view"                  # ยินยอมให้ รพ.สต. ดูข้อมูล
    doctor_view = "doctor_view"                # ยินยอมให้แพทย์ดูข้อมูล
    research_anonymized = "research_anonymized" # ยินยอมให้ใช้เพื่อ research (ไม่ระบุตัวตน)
    data_export_to_smart_osm = "data_export_to_smart_osm"  # ส่งออกไปยัง Smart อสม. (Phase 2)


class ConsentMethod(str, enum.Enum):
    """วิธีการให้ความยินยอม"""
    paper = "paper"                    # กระดาษเซ็นมือ (scan/photo แนบใน system)
    digital_signature = "digital_signature"  # e-signature ในแอป
    both = "both"                      # กระดาษ + ดิจิทัล (recommended)


class ConsentStatus(str, enum.Enum):
    """สถานะของความยินยอม"""
    active = "active"
    withdrawn = "withdrawn"
    expired = "expired"                # ถ้ามี expiry
    superseded = "superseded"          # มี consent ใหม่มาแทน


class AuditAction(str, enum.Enum):
    """Action types สำหรับ audit log"""
    # Auth
    login_success = "login_success"
    login_failure = "login_failure"
    logout = "logout"
    password_change = "password_change"
    password_reset = "password_reset"

    # User management
    user_create = "user_create"
    user_update = "user_update"
    user_suspend = "user_suspend"
    user_reactivate = "user_reactivate"
    user_deactivate = "user_deactivate"  # right to be forgotten

    # Org management
    org_create = "org_create"
    org_update = "org_update"
    org_member_add = "org_member_add"
    org_member_remove = "org_member_remove"

    # Care assignment
    care_assignment_create = "care_assignment_create"
    care_assignment_end = "care_assignment_end"
    care_assignment_transfer = "care_assignment_transfer"

    # Patient data (cross-user access = MUST LOG)
    patient_view = "patient_view"
    patient_list_view = "patient_list_view"
    patient_update = "patient_update"

    # BP readings
    bp_reading_create = "bp_reading_create"
    bp_reading_view = "bp_reading_view"          # only if viewer != owner
    bp_reading_update = "bp_reading_update"
    bp_reading_delete = "bp_reading_delete"

    # Consent
    consent_grant = "consent_grant"
    consent_withdraw = "consent_withdraw"
    consent_update = "consent_update"

    # Data operations
    data_export = "data_export"
    data_subject_request = "data_subject_request"  # ขอดู/แก้/ลบข้อมูลตัวเอง
    data_breach_reported = "data_breach_reported"

    # OCR
    ocr_batch_process = "ocr_batch_process"
    ocr_review_queue_action = "ocr_review_queue_action"
```

---

## 4. Database Schema

### 4.1 New Tables

#### 4.1.1 `organizations`

```python
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB

class Organization(Base):
    __tablename__ = "organizations"

    # Identity
    id = Column(Integer, primary_key=True)  # internal PK for fast joins
    external_id = Column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid.uuid4,
        index=True,
    )  # สำหรับ API/URLs (ไม่ expose internal id)

    # External code system (flexible: HCODE for รพ.สต., custom for commercial)
    code = Column(String(50), nullable=True, index=True)         # nullable — บางองค์กรไม่มี code
    code_system = Column(String(50), nullable=True)              # "MOPH_HCODE", "CUSTOM", null

    # Basic info
    name = Column(String(200), nullable=False)
    type = Column(SQLEnum(OrganizationType), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)

    # Geographic (useful for รพ.สต. แต่ optional สำหรับ commercial clients)
    address = Column(Text, nullable=True)
    province_code = Column(String(2), nullable=True, index=True)   # "64" = สุโขทัย
    district_code = Column(String(4), nullable=True, index=True)   # "6401" = เมืองสุโขทัย
    subdistrict_code = Column(String(6), nullable=True, index=True) # "640106" = เมืองเก่า

    # Contact
    contact_name = Column(String(200), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(200), nullable=True)

    # Legal — In-app Terms of Service acceptance (no external DPA)
    terms_version = Column(String(20), nullable=True)              # version ที่ยอมรับ
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
    terms_accepted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    terms_accepted_from_ip = Column(String(64), nullable=True)

    # Meta
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Flexible metadata (e.g., business registration info for commercial, HCODE attrs for รพ.สต.)
    extra_metadata = Column(JSONB, nullable=True)

    # Relationships
    parent = relationship("Organization", remote_side=[id], backref="children")
    members = relationship("OrganizationMember", back_populates="organization")
    terms_accepted_by = relationship("User", foreign_keys=[terms_accepted_by_user_id])

    __table_args__ = (
        # code ต้อง unique ภายใน code_system เดียวกัน (partial unique)
        UniqueConstraint("code", "code_system", name="uq_org_code_system"),
        Index("ix_org_province_district_subdistrict", "province_code", "district_code", "subdistrict_code"),
        Index("ix_org_type_active", "type", "is_active"),
    )
```

**Notes:**
- `external_id` UUID: ใช้ใน API/URLs (`/api/v1/orgs/{external_id}`) — ป้องกัน enumeration
- `id` integer: ใช้เป็น foreign key internal (faster joins, smaller index)
- `code` + `code_system`: flexible identity system
  - รพ.สต.: `code="11836", code_system="MOPH_HCODE"`
  - คลินิก: `code=null, code_system=null`
  - บริษัทประกัน: `code="BLA-2026", code_system="CUSTOM"`
- `parent_id` รองรับ hierarchy: รพ.สต. → สสอ. → สสจ. (Phase 2+)
- Legal: ไม่มี DPA field เพราะใช้ in-app ToS acceptance (admin กด accept ในแอป)
- `extra_metadata` JSONB: เก็บข้อมูลเฉพาะองค์กร เช่น `{"moph_data": {...}}` หรือ `{"tax_id": "..."}` สำหรับ commercial

#### 4.1.2 `organization_members`

```python
class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    role = Column(SQLEnum(UserRole), nullable=False, index=True)

    # Lifecycle
    effective_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    effective_until = Column(DateTime(timezone=True), nullable=True)  # null = ยังทำงานอยู่
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Meta
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    added_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # ใครเพิ่ม

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="org_memberships")
    organization = relationship("Organization", back_populates="members")
    added_by = relationship("User", foreign_keys=[added_by_user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", "role", name="uq_user_org_role"),
        Index("ix_org_member_active", "organization_id", "is_active"),
    )
```

**Notes:**
- User 1 คน สามารถเป็น member ของหลาย org ได้ และหลาย role ก็ได้
- เช่น หมอ A เป็น doctor ใน รพ. X และ เป็น rpsst_admin ใน รพ.สต. Y พร้อมกัน
- `effective_until` รองรับ "เคยทำงานที่นี่แต่ลาออกแล้ว" — audit ย้อนหลังได้

#### 4.1.3 `care_assignments`

```python
class CareAssignment(Base):
    __tablename__ = "care_assignments"

    id = Column(Integer, primary_key=True)
    caregiver_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    patient_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)

    # ลำดับของคนไข้ที่ caregiver ดูแล (สำหรับ OCR batch: ใบรายชื่อ = เลข 1-N)
    sequence_in_list = Column(Integer, nullable=True, index=True)

    # Lifecycle
    effective_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    effective_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Reason ตอนจบ assignment (optional but useful)
    end_reason = Column(String(200), nullable=True)  # "transfer", "patient_moved", "caregiver_left"

    # Meta
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    caregiver = relationship("User", foreign_keys=[caregiver_user_id], backref="patients_i_care_for")
    patient = relationship("User", foreign_keys=[patient_user_id], backref="caregivers")
    organization = relationship("Organization")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        # Active assignment ของ caregiver-patient pair ต้องมีได้แค่ 1 รายการ
        Index("ix_care_active_unique", "caregiver_user_id", "patient_user_id",
              postgresql_where=(Column("is_active") == True), unique=True),
        Index("ix_care_caregiver_active", "caregiver_user_id", "is_active"),
        Index("ix_care_patient_active", "patient_user_id", "is_active"),
    )
```

**Notes:**
- Many-to-many: 1 patient อาจถูกดูแลโดย 2 อสม. ต่อกัน (transfer) หรือซ้อน (backup)
- `sequence_in_list` ใช้กับ OCR batch feature — อสม. พิมพ์ใบรายชื่อออกมา ลำดับ 1-10 ในใบ map กับ sequence นี้
- Partial unique index: active assignment ซ้ำกันไม่ได้ แต่ inactive ซ้ำได้

#### 4.1.4 `consent_records`

```python
class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True)
    patient_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    scope = Column(SQLEnum(ConsentScope), nullable=False, index=True)

    # How consent was obtained
    method = Column(SQLEnum(ConsentMethod), nullable=False)
    version = Column(String(20), nullable=False)  # consent form version e.g. "1.0"
    language = Column(String(10), nullable=False, default="th")

    # Evidence
    # NOTE (v1.1): paper_scan_file_id REMOVED per decision 4.5 in PLAN_REVIEW_RESPONSE.
    # Paper consent = physical storage at รพ.สต. only (data minimization).
    # Digital evidence via signature + GPS + timestamp is sufficient per PDPA.
    digital_signature_data = Column(Text, nullable=True)    # base64 PNG ของลายเซ็น
    digital_signature_hash = Column(String(64), nullable=True)  # SHA-256 ของ signature
    gps_latitude = Column(Float, nullable=True)
    gps_longitude = Column(Float, nullable=True)
    witness_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # อสม. ที่เป็นพยาน

    # Status
    status = Column(SQLEnum(ConsentStatus), nullable=False, default=ConsentStatus.active, index=True)
    granted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    withdrawal_reason = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # ถ้ามี

    # Meta
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    patient = relationship("User", foreign_keys=[patient_user_id], backref="consent_records")
    organization = relationship("Organization")
    # paper_scan relationship REMOVED (v1.1) — see note above
    witness = relationship("User", foreign_keys=[witness_user_id])

    __table_args__ = (
        Index("ix_consent_active", "patient_user_id", "scope", "status"),
    )
```

**Notes:**
- 1 patient สามารถมีหลาย consent records (1 record ต่อ scope ต่อ version)
- เมื่อ update version: old = `superseded`, new = `active`
- Withdrawal ไม่ลบ record (audit trail) แต่เปลี่ยน status

#### 4.1.5 `audit_logs`

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True)  # BigInt สำหรับ scale
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)

    # Who
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # null = system
    actor_role = Column(String(50), nullable=True)        # snapshot ของ role ตอนทำ action
    actor_organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)

    # What / Target
    target_type = Column(String(50), nullable=True, index=True)   # "user", "bp_reading", "consent", etc.
    target_id = Column(String(100), nullable=True, index=True)    # target resource ID (string เพื่อ flexible)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # ถ้า action มี target user

    # Context
    from_ip = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(64), nullable=True, index=True)    # correlation ID
    session_id = Column(String(64), nullable=True, index=True)

    # Result
    success = Column(Boolean, nullable=False, default=True, index=True)
    error_message = Column(Text, nullable=True)

    # Additional data (JSONB สำหรับ flexibility)
    metadata = Column(JSONB, nullable=True)

    # When
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    actor = relationship("User", foreign_keys=[actor_user_id])
    actor_organization = relationship("Organization")
    target_user = relationship("User", foreign_keys=[target_user_id])

    __table_args__ = (
        # Composite indexes สำหรับ query pattern บ่อย
        Index("ix_audit_actor_time", "actor_user_id", "created_at"),
        Index("ix_audit_target_user_time", "target_user_id", "created_at"),
        Index("ix_audit_action_time", "action", "created_at"),
        Index("ix_audit_org_time", "actor_organization_id", "created_at"),
        # Partial index สำหรับ failed actions (security review)
        Index("ix_audit_failures", "created_at", postgresql_where=(Column("success") == False)),
    )
```

**Notes:**
- BigInteger PK เพราะ audit log จะโตเร็ว
- `metadata` JSONB: เก็บ extra context เช่น `{"old_value": "...", "new_value": "..."}`
- **ไม่มี UPDATE / DELETE ให้ audit_logs** — append-only
- Retention: 2 ปี minimum (PDPA)

#### 4.1.6 `pairing_codes`

```python
class PairingCode(Base):
    __tablename__ = "pairing_codes"

    id = Column(Integer, primary_key=True)
    code_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256 ของ 6-digit code
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    purpose = Column(String(50), nullable=False)  # "telegram_pairing", future: "line_pairing"

    # Lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    used_by_telegram_id_hash = Column(String(64), nullable=True)

    # Meta
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        Index("ix_pairing_active", "expires_at", postgresql_where=(Column("used_at").is_(None))),
    )
```

**Notes:**
- เก็บเฉพาะ hash ของ code ไม่เก็บ plain text (ปลอดภัย)
- TTL 15 นาที (expires_at = created_at + 15 min)
- Used once (used_at ถูก set แล้วใช้ไม่ได้)

#### 4.1.7 `files` (MVP: เก็บเฉพาะที่จำเป็นจริง ๆ)

```python
class File(Base):
    __tablename__ = "files"

    # Identity
    id = Column(Integer, primary_key=True)
    external_id = Column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid.uuid4,
        index=True,
    )

    # Basic metadata
    filename = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)

    # Storage abstraction
    storage_backend = Column(String(50), nullable=False, index=True)  # "postgres_bytea" (MVP)
    storage_path = Column(Text, nullable=True)
    storage_region = Column(String(50), nullable=True)

    # Encrypted bytes (MVP: BYTEA in DB; always encrypted with Fernet)
    data_encrypted = Column(LargeBinary, nullable=True)
    encryption_key_id = Column(String(100), nullable=True)

    # Classification — **MVP จำกัดเฉพาะ purpose ที่จำเป็น**
    purpose = Column(String(100), nullable=False, index=True)
    # Allowed values (enforce via Pydantic + DB check constraint):
    #   "ocr_batch_review_temp"  — รูปใบรายชื่อ + เครื่องวัด
    #                              เก็บ ชั่วคราว เฉพาะเมื่อ OCR confidence ต่ำ + เข้า review queue
    #                              expires_at = created_at + 7 days (hard cap)
    #                              deleted immediately หลัง admin ดำเนินการ review
    #
    # NOT stored in MVP:
    #   - BP photo single (OCR แล้ว ทิ้งทันที, เก็บแค่ ocr_raw_output JSON)
    #   - Consent paper scan (physical storage ที่ รพ.สต. เท่านั้น)
    #   - Patient documents (out of MVP scope)
    related_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    related_organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Retention & lifecycle (MANDATORY expires_at)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)  # non-null, ต้องกำหนดเสมอ
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    related_user = relationship("User", foreign_keys=[related_user_id])
    related_organization = relationship("Organization")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])

    __table_args__ = (
        Index("ix_file_expires", "expires_at", postgresql_where=(Column("deleted_at").is_(None))),
        Index("ix_file_purpose_user", "purpose", "related_user_id"),
        # DB check constraint: purpose ต้องอยู่ใน whitelist
        CheckConstraint(
            "purpose IN ('ocr_batch_review_temp')",
            name="ck_files_purpose_whitelist"
        ),
        # expires_at ต้อง > created_at
        CheckConstraint("expires_at > created_at", name="ck_files_expires_after_created"),
    )
```

**Data minimization policy (enforce ในระดับ code + DB):**

| Purpose | Retention | Auto-delete trigger | Rationale |
|---------|-----------|--------------------|-----------|
| `ocr_batch_review_temp` | **Max 7 days** | (ก) Admin review complete (immediate) OR (ข) expires_at (cron ลบ) | รูปมีชื่อหลายคน = high privacy risk. เก็บเฉพาะตอน OCR ไม่แน่ใจ. ลบเร็วที่สุด |

**สิ่งที่ไม่เก็บในระบบ (by design):**

- ❌ **รูปจอเครื่องวัด (single OCR)** — ของเดิมไม่เก็บ, ใหม่ก็ไม่เก็บ. OCR แล้วทิ้งทันที. เก็บแค่ `ocr_raw_output` (JSON text) + `ocr_confidence_score` + ค่า BP ที่ save ลง `bp_readings`
- ❌ **Consent paper scan** — เก็บกระดาษจริงที่ รพ.สต. ในตู้ล็อก. Digital evidence = signature + GPS + timestamp + audit log ใน DB (pain เพียงพอตามกฎหมาย)
- ❌ **Patient documents (generic)** — out of MVP scope

**Auto-deletion cron job:**
```python
# app/jobs/file_cleanup.py - รันทุก 6 ชม.

async def cleanup_expired_files():
    now = datetime.utcnow()
    expired = await db.query(File).filter(
        File.expires_at < now,
        File.deleted_at.is_(None)
    ).all()
    
    for file in expired:
        # Hard delete: ลบ data_encrypted + soft-flag record (keep for audit)
        file.data_encrypted = None
        file.deleted_at = now
        await log_audit(
            action="file_auto_deleted",
            target_type="file",
            target_id=file.id,
            metadata={"purpose": file.purpose, "age_days": (now - file.created_at).days}
        )
    await db.commit()
```

**Volume estimate สำหรับ pilot (ลดลงมาก):**
- Steady state: ~5-10 รูปใน review queue ณ ช่วงใดก็ตาม × 3MB = **~30MB max** (transient)
- ประมาณ ~10% ของ OCR batch เข้า review queue = ~50 รูป/เดือน × 3MB × 7 วัน = **~35MB avg**
- ไม่มี long-term file storage เลย

### 4.2 Modified Tables

#### 4.2.1 `users` — เพิ่ม fields

> **v1.1 IMPORTANT:** existing column `role` (String) **ไม่ลบ** ใน v2 — เพิ่ม `primary_role` เป็น additive column (nullable) และใช้ helper `get_effective_role()` เพื่อ dual-read.

```python
# เพิ่มใน User model ที่มีอยู่แล้ว

# External identity (for API)
external_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)

# Role / account type — ADDITIVE (v1.1): role (String) ยังคงไว้, dual-read
# primary_role nullable เพื่อให้ backfill script เติมค่า; code fallback ไป role ถ้ายังว่าง
account_type = Column(SQLEnum(AccountType), nullable=True, default=AccountType.self_managed, index=True)
primary_role = Column(SQLEnum(UserRole), nullable=True, default=None, index=True)

# สำหรับ proxy-managed (ชาวบ้านที่ไม่ login)
managed_by_organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)

# In-app legal acceptance
terms_version = Column(String(20), nullable=True)              # ToS version
terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
privacy_policy_version = Column(String(20), nullable=True)
privacy_policy_accepted_at = Column(DateTime(timezone=True), nullable=True)

# สำหรับ soft delete / deactivation
deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
deletion_reason = Column(String(100), nullable=True)  # "user_request", "dpa_expiry", "admin_suspend"
```

**Migration rule (v1.1 — Additive dual-read):**

- Existing users: `account_type = self_managed`, `primary_role` backfilled from `role` via `LEGACY_ROLE_MAP` (ดู §5.2)
- **`role` column ไม่ลบ** (deprecated แต่ไม่ drop) — code เดิม (`require_verified_doctor`, `require_staff`, bot services) ยังอ่าน `user.role` ได้เหมือนเดิม
- **New code** ใช้ helper:
  ```python
  # app/utils/permissions.py
  LEGACY_ROLE_MAP = {
      "patient": UserRole.patient_self,
      "doctor":  UserRole.doctor,
      "staff":   UserRole.superadmin,  # env-managed staff = ระบบ admin (not รพ.สต.)
  }

  def get_effective_role(user: User) -> UserRole:
      """Dual-read: prefer primary_role (new), fallback to role (legacy)."""
      if user.primary_role is not None:
          return user.primary_role
      return LEGACY_ROLE_MAP.get(user.role, UserRole.patient_self)
  ```
- **Dual-write discipline:** ทุก code path ที่ `set` role ใหม่ ต้องเขียนทั้ง `user.role` และ `user.primary_role` พร้อมกัน (ใช้ helper `set_user_role(user, primary_role)`)
- Deprecation timeline: `role` column drops ใน v3 (หลัง all call sites migrate ไปใช้ `get_effective_role()` เท่านั้น)
- Existing users: ต้อง re-accept ToS + Privacy Policy version ใหม่ ตอน login ครั้งต่อไป (show modal)
- ไม่กระทบ login / flow เดิม

#### 4.2.2 `bp_readings` — เพิ่ม fields

```python
# เพิ่มใน BloodPressureRecord model

# Who measured
measured_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # null = ตัวคนไข้เอง
measurement_context = Column(SQLEnum(MeasurementContext), nullable=False, default=MeasurementContext.self_home)

# When (แยก measured vs recorded)
# recorded_at: มีอยู่แล้ว (timestamp ที่บันทึกเข้าระบบ)
# measured_at: เพิ่มใหม่ (เวลาที่วัดจริง — อาจมาจาก OCR screen, EXIF, หรือ user input)
measured_at = Column(DateTime(timezone=True), nullable=False, index=True)
measured_at_source = Column(String(50), nullable=True)  # "ocr_screen", "exif", "manual", "current_time"

# Location (optional)
location_name = Column(String(200), nullable=True)  # "บ้านชาวบ้าน", "รพ.สต."
gps_latitude = Column(Float, nullable=True)
gps_longitude = Column(Float, nullable=True)

# Data entry source
source_type = Column(String(50), nullable=False, default="manual", index=True)
# values: "manual" (พิมพ์), "ocr_single" (รูปเครื่องวัด), "ocr_batch" (ใบรายชื่อ + เครื่องวัด)

# OCR metadata — keep only textual evidence, NOT the image
ocr_confidence_score = Column(Float, nullable=True)
ocr_raw_output = Column(JSONB, nullable=True)
# ocr_raw_output ตัวอย่าง:
# {
#   "gemini_response": {"systolic": 130, "diastolic": 85, ...},
#   "gemini_version": "gemini-2.0-flash",
#   "prompt_version": "bp_single_v1",
#   "processed_at": "2026-04-18T10:30:00Z"
# }
# Note: ไม่เก็บ base64 image ใน JSON

# Review queue (only for OCR with low confidence)
ocr_reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
ocr_reviewed_at = Column(DateTime(timezone=True), nullable=True)
ocr_review_status = Column(String(20), nullable=True, index=True)
# values: null (not needing review), "pending", "approved", "rejected", "edited"

# Temporary image link (ONLY for review queue; null after review completes)
source_image_file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
# IMPORTANT: หลังจาก admin review ในระบบแล้ว:
#   - source_image_file_id -> set to null
#   - File -> data_encrypted cleared, deleted_at set
# รูปไม่ถูกเก็บถาวรแม้แต่ในกรณี review queue

# Organization context
organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)

__table_args__ = (
    # Composite index สำหรับ query pattern "รายการ BP ของ patient X เรียงเวลา"
    Index("ix_bp_patient_measured", "user_id", "measured_at"),
    # Dedupe: หาซ้ำจาก patient + measured_at (minute) + systolic + diastolic
    Index("ix_bp_dedupe", "user_id", "measured_at", "systolic", "diastolic"),
    # Review queue query
    Index("ix_bp_review_pending", "ocr_review_status",
          postgresql_where=(Column("ocr_review_status") == "pending")),
)
```

**Migration rule:**
- Existing records: `measured_at = recorded_at`, `measurement_context = self_home`, `measured_at_source = "manual"`, `measured_by_user_id = user_id`, `source_type = "manual"`

**Validation rules for `measured_at` (v1.1 — new):**

Service layer `app/utils/bp_validation.py:validate_measured_at()` enforce:

| Condition | Action | Rationale |
|-----------|--------|-----------|
| `measured_at > recorded_at` (future) | **Block** (422 Unprocessable Entity) | ไม่สามารถวัดในอนาคต |
| `(recorded_at - measured_at) > 7 days` | **Warn** + require `notes` field populated | Fat-finger protection; 7 วันย้อนหลัง = reasonable บันทึกช้า |
| `(recorded_at - measured_at) > 30 days` | **Block** — ต้องใช้ endpoint "historical import" แยก + extra consent | Bulk backfill คนละ flow กับ routine entry |
| OCR batch: screen reads date/time | Use if OCR confidence > 0.8; else fallback `recorded_at` | OCR uncertain ไม่ควรเชื่อถือ date/time |

**Image handling policy (strict):**

| Scenario | Image storage |
|----------|---------------|
| OCR single, confidence > threshold | **Not stored** — process in-memory + save values only |
| OCR single, confidence ≤ threshold | **Not stored** — อสม. review ใน PWA ทันทีก่อน submit (user-side review, no backend storage) |
| OCR batch, confidence > threshold, no name collision | **Not stored** — auto-process + save values |
| OCR batch, confidence ≤ threshold OR name collision | **Stored temporarily** (`ocr_batch_review_temp`), max 7 days, deleted after admin review |
| User-submitted photo for BP single (existing flow) | **Not stored** (ตาม practice เดิมของระบบ) |

### 4.3 Coexistence: `DoctorPatient` / `AccessRequest` ↔ `CareAssignment` (v1.1 new)

> **Decision 4.3 (PLAN_REVIEW_RESPONSE):** Keep existing B2C tables; care_assignments = parallel for ASM flow only.

**Rationale:**
- `DoctorPatient` + `AccessRequest` ใช้งานใน **11 endpoints** ของ `routers/doctor.py` + bot cascade delete
- Migrate ไป `care_assignments` ทั้งหมด = surface area ใหญ่ + risk สูง
- Coexistence ไม่มี data collision ถ้า namespace ชัดเจน

**Namespacing (ไม่ให้ชนกัน):**

| Dimension | Doctor flow (legacy, B2C) | ASM flow (new, Org-based) |
|-----------|---------------------------|---------------------------|
| Tables | `doctor_patients`, `access_requests` | `care_assignments`, `consent_records` |
| Actor role | `primary_role=doctor` OR legacy `role="doctor"` | `primary_role=asm` |
| URL namespace | `/api/v1/doctor/*`, `/api/v1/patient/*` | `/api/v1/asm/*`, `/api/v1/rpsst/*` |
| Permission guard | `require_verified_doctor` + `DoctorPatient.is_active` | `has_permission(VIEW_ASSIGNED_PATIENT)` + `ConsentRecord.scope=asm_collect, status=active` |
| Consent mechanism | `AccessRequest` approval chain | `ConsentRecord` (granular scope) |
| Audit metadata | `via_relationship: "doctor_patient"` | `via_relationship: "care_assignment"` |

**Case: patient คนเดียวมีทั้ง doctor + asm**
- `BloodPressureRecord` ของ patient 1 คน เห็นได้ 2 paths (แพทย์ + อสม.) — ถูกต้องเพราะให้ยินยอมทั้งคู่
- Audit log ต้อง distinguish path ใน `metadata.via_relationship`
- ถอน consent ของฝ่ายใด ไม่กระทบอีกฝ่าย

**Consent withdrawal semantics:**
- ถอน consent ต่อหมอ: `DoctorPatient.is_active = False` (ไม่แตะ `care_assignments`)
- ถอน consent ต่อ อสม.: `CareAssignment.is_active = False` + `ConsentRecord.status = withdrawn` (ไม่แตะ `doctor_patients`)

**Future unification (Phase 2+, not v2):**
- ถ้าประสบการณ์ pilot ผ่านไปดี, ค่อย migrate `doctor_patients` → `care_assignments` (ด้วย `CareRole={doctor, asm}` enum เพิ่ม)
- นอก v2 scope

### 4.4 Relationship: `License` ↔ `Organization` (v1.1 new)

> **Decision 4.6 (PLAN_REVIEW_RESPONSE):** Add nullable FK, backfill from string; keep `organization_name` for 1 release cycle.

**Existing `License` table (verified dead code, no writers/readers in current codebase):**
```python
class License(Base):
    __tablename__ = "licenses"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    organization_name = Column(String)   # แค่ string, ยังไม่ link ข้าม table
    type = Column(String, default="clinic")
    max_users = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_tz)
```

**Extension (v1.1):**
```python
# เพิ่มใน License model
organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
# ไม่ลบ organization_name ใน v1.1 (dual-column ชั่วคราว)

# Relationship
organization = relationship("Organization", backref="licenses")
```

**Backfill migration:**
1. Query prod: `SELECT COUNT(*) FROM licenses;` ก่อน (คาดว่า = 0, เพราะ dead code verified)
2. ถ้า > 0:
   - สร้าง `Organization` row จาก `organization_name` (type ดูจาก `License.type`: "clinic"→clinic, "hospital"→hospital, "enterprise"→other)
   - Set `License.organization_id = new_org.id`
3. เวลา grace period (~1 release): permission check ค่อย read จาก `organization_id` ได้เต็ม
4. v3: drop `organization_name` column

**Future permission check (Phase 2):**
```python
# Entitlement check: org มี license active สำหรับ feature ไหม
if not has_active_license(user.active_org_id, feature="premium_asm"):
    raise HTTPException(402, "License required")
```

---

## 5. Migration Plan (v1.1 — ad-hoc scripts, no Alembic)

### 5.1 Migration sequence (revised v1.1 — FK-correct order)

> **Decision Q1 (PLAN_REVIEW_RESPONSE):** Use ad-hoc Python migration pattern (แบบเดียวกับ `migrations/add_*.py`) + `schema_migrations` version table. See [[INFRASTRUCTURE_SETUP]] for tooling.

Each file = `migrations/v2_XX_<description>.py` with both `migrate()` and `rollback()` functions, idempotent via `schema_migrations` table.

```
migrations/
├── v2_00_create_schema_migrations.py       # infra: version tracking table
├── v2_01_create_enums.py                    # AccountType, UserRole, etc. (PG) / no-op (SQLite)
├── v2_02_create_organizations.py            # table + indexes
├── v2_03_create_organization_members.py
├── v2_04_extend_users.py                    # ADD external_id, account_type, primary_role,
│                                           # managed_by_organization_id, terms_*, deleted_at
│                                           # (does NOT drop existing role column)
├── v2_05_backfill_users.py                  # LEGACY_ROLE_MAP → primary_role
├── v2_06_create_care_assignments.py
├── v2_07_create_consent_records.py
├── v2_08_create_pairing_codes.py
├── v2_09_create_files.py                    # with purpose whitelist CHECK constraint
├── v2_10_extend_bp_readings.py              # ADD measured_at, measurement_context, etc.
├── v2_11_backfill_bp_readings.py            # measured_at = recorded_at
├── v2_12_create_audit_logs.py               # new table (BigInt PK, JSONB metadata)
│                                           # (does NOT drop admin_audit_logs)
└── v2_13_extend_licenses.py                 # ADD organization_id FK (nullable)
                                            # + backfill from organization_name if any records
```

**FK dependency order rationale:**
- `organizations` ต้องมีก่อน `users.managed_by_organization_id` FK ถูกเพิ่ม
- `care_assignments` + `audit_logs` FK → users + organizations → อยู่หลังสุด
- License extension = last (dead code, ไม่บล็อค flow อื่น)

**Rollback order = reverse of migrate order**, except backfill scripts (skip rollback for data-only scripts).

### 5.2 Backfill scripts (v1.1 revised)

**File: `migrations/v2_05_backfill_users.py`**

```python
# LEGACY_ROLE_MAP (v1.1 decision 4.2)
LEGACY_ROLE_MAP = {
    "patient": "patient_self",
    "doctor":  "doctor",
    "staff":   "superadmin",  # env-managed staff = ระบบ admin (NOT rpsst_staff)
}

def migrate():
    # Backfill primary_role from legacy role
    for legacy, new_role in LEGACY_ROLE_MAP.items():
        conn.execute(text(f"""
            UPDATE users
            SET primary_role = :new_role,
                account_type = 'self_managed'
            WHERE role = :legacy AND primary_role IS NULL
        """), {"legacy": legacy, "new_role": new_role})

    # Catch-all: any remaining null primary_role → patient_self
    conn.execute(text("""
        UPDATE users
        SET primary_role = 'patient_self',
            account_type = 'self_managed'
        WHERE primary_role IS NULL
    """))

def rollback():
    # Clear new columns (role column ยังมีอยู่ = safe)
    conn.execute(text("UPDATE users SET primary_role = NULL, account_type = NULL"))
```

**File: `migrations/v2_11_backfill_bp_readings.py`**

```python
def migrate():
    # Note: current table name = blood_pressure_records (not bp_readings)
    conn.execute(text("""
        UPDATE blood_pressure_records
        SET measured_at = measurement_date,
            measured_at_source = 'manual',
            measurement_context = 'self_home',
            measured_by_user_id = user_id,
            source_type = 'manual'
        WHERE measured_at IS NULL
    """))

def rollback():
    conn.execute(text("""
        UPDATE blood_pressure_records
        SET measured_at = NULL,
            measured_at_source = NULL,
            measured_by_user_id = NULL
    """))
    # ไม่ rollback measurement_context, source_type (NOT NULL columns w/ defaults)
```

### 5.3 Rollback strategy (v1.1 expanded)

- ทุก migration ต้องมี `migrate()` + `rollback()` (code review rule) — enforce ใน [[INFRASTRUCTURE_SETUP]]
- Test rollback บน Neon staging branch ก่อน production (see [[MIGRATION_STRATEGY]])
- Backup Neon DB ก่อนรัน migration production: ใช้ PITR + snapshot
- Per-script rollback order = **reverse of migrate order**
- Data-only backfill scripts: rollback = "clear additive columns"; ไม่ restore เดิม (ไม่ได้เก็บ)
- **Zero-downtime principle:** ทุก ALTER column type = multi-step (add new → backfill → dual-read → swap → drop old) — ดู [[MIGRATION_STRATEGY]]

---

## 6. RBAC — Role Matrix

### 6.1 Permissions matrix

| Action | superadmin | rpsst_admin | doctor | asm | patient_self | patient_proxy |
|--------|:----------:|:-----------:|:------:|:---:|:------------:|:-------------:|
| **User mgmt** ||||||| 
| Create รพ.สต. | Y | - | - | - | - | - |
| Create อสม. | Y | Y (in own org) | - | - | - | - |
| Create patient (proxy) | Y | Y (in own org) | - | Y (in own org)* | - | - |
| View own profile | Y | Y | Y | Y | Y | (N/A — no login) |
| Edit own profile | Y | Y | Y | Y | Y | (N/A) |
| View other users | Y | Y (in own org) | Y (assigned patients) | Y (assigned patients) | - | - |
| **Care assignment** ||||||| 
| Create/edit assignment | Y | Y (in own org) | - | - | - | - |
| **Consent** ||||||| 
| Grant consent | - | Y (record for patient) | - | Y (record for patient) | Y (self) | - |
| Withdraw consent | Y | Y | - | Y (assigned) | Y (self) | (via รพ.สต.) |
| View consent records | Y | Y (in own org) | Y (assigned) | Y (assigned) | Y (self) | - |
| **BP data** ||||||| 
| Create reading (self) | - | - | - | - | Y | - |
| Create reading for patient | Y | Y (in own org) | - | Y (assigned) | - | - |
| View reading (self) | Y | Y | Y | Y | Y | - |
| View reading (other) | Y | Y (in own org, w/ consent) | Y (assigned, w/ consent) | Y (assigned, w/ consent) | - | - |
| Edit reading | Y | Y (in own org) | - | Y (own entries, within 24h) | Y (self) | - |
| Delete reading | Y | Y (in own org) | - | Y (own entries, within 24h) | Y (self) | - |
| **Reports** ||||||| 
| Export CSV (own data) | Y | Y (own org) | - | Y (assigned) | Y (self) | - |
| View audit log | Y | Y (own org) | - | - | - | - |
| **System** ||||||| 
| Breach response | Y | - | - | - | - | - |
| Data retention job | Y | - | - | - | - | - |

\* `asm` สามารถสร้าง proxy patient ได้ใน org ของตัวเอง (เพื่อ workflow สะดวก) ต้องอยู่ใน pre-approved whitelist ของ รพ.สต. admin หรือให้ admin approve หลัง create

### 6.2 Implementation approach

```python
# app/utils/permissions.py

class Permission:
    # Verb_resource format
    CREATE_RPSST = "create_rpsst"
    CREATE_ASM_IN_ORG = "create_asm_in_org"
    CREATE_PROXY_PATIENT_IN_ORG = "create_proxy_patient_in_org"
    VIEW_OWN_PROFILE = "view_own_profile"
    VIEW_PATIENT_IN_ORG = "view_patient_in_org"
    VIEW_ASSIGNED_PATIENT = "view_assigned_patient"
    CREATE_READING_FOR_ASSIGNED = "create_reading_for_assigned"
    # ...

ROLE_PERMISSIONS = {
    UserRole.superadmin: {
        Permission.CREATE_RPSST,
        Permission.CREATE_ASM_IN_ORG,
        # ... all permissions
    },
    UserRole.rpsst_admin: {
        Permission.CREATE_ASM_IN_ORG,
        Permission.CREATE_PROXY_PATIENT_IN_ORG,
        Permission.VIEW_PATIENT_IN_ORG,
        # ...
    },
    UserRole.asm: {
        Permission.VIEW_ASSIGNED_PATIENT,
        Permission.CREATE_READING_FOR_ASSIGNED,
        # ...
    },
    # ...
}


def has_permission(user: User, permission: str, context: dict = None) -> bool:
    """ตรวจว่า user มี permission นี้ใน context ที่ระบุไหม"""
    # Get user's effective roles (across all org memberships)
    user_roles = get_effective_roles(user)

    # Check if any role grants the permission
    for role in user_roles:
        if permission in ROLE_PERMISSIONS.get(role, set()):
            # Context-specific checks (e.g., "in own org", "assigned patient")
            if _check_context(user, permission, context):
                return True

    return False


def _check_context(user: User, permission: str, context: dict) -> bool:
    """Context-specific permission checks"""
    if permission == Permission.VIEW_ASSIGNED_PATIENT:
        target_patient_id = context.get("target_user_id")
        return is_caregiver_of(user.id, target_patient_id)

    if permission == Permission.VIEW_PATIENT_IN_ORG:
        target_patient_id = context.get("target_user_id")
        return are_in_same_org(user.id, target_patient_id)

    # ... more context checks
    return True
```

### 6.3 Middleware

```python
# app/middleware/rbac.py

from fastapi import HTTPException, Request
from functools import wraps

def require_permission(permission: str, context_fn=None):
    """Decorator บังคับ permission check + audit log"""
    def decorator(endpoint):
        @wraps(endpoint)
        async def wrapper(request: Request, *args, **kwargs):
            user = request.state.user  # populated by auth middleware
            context = context_fn(request, *args, **kwargs) if context_fn else {}

            if not has_permission(user, permission, context):
                # Log denied access
                await log_audit(
                    action=AuditAction.login_failure,  # or appropriate
                    actor=user,
                    target=context.get("target_user_id"),
                    success=False,
                    error_message=f"Permission denied: {permission}"
                )
                raise HTTPException(403, "Forbidden")

            # Log successful access (for cross-user operations)
            if permission.startswith(("view_", "create_reading_for", "edit_patient")):
                await log_audit(
                    action=_permission_to_action(permission),
                    actor=user,
                    target=context.get("target_user_id"),
                    success=True
                )

            return await endpoint(request, *args, **kwargs)
        return wrapper
    return decorator


# Usage
@router.get("/patients/{patient_id}")
@require_permission(
    Permission.VIEW_ASSIGNED_PATIENT,
    context_fn=lambda req, patient_id: {"target_user_id": patient_id}
)
async def get_patient(patient_id: int, request: Request):
    ...
```

### 6.4 Multi-org JWT claims (v1.1 new)

> **Decision 4.10 (PLAN_REVIEW_RESPONSE):** User ที่มี > 1 org membership ใช้ JWT claim `active_org_id` — ไม่เก็บใน DB (stateless)

**Login flow with multi-org:**

```
1. User login → verify password
2. Query: SELECT * FROM organization_members WHERE user_id = X AND is_active
   ├─ 0 orgs → normal JWT (no active_org_id claim) — legacy user
   ├─ 1 org  → auto-select → JWT includes active_org_id=org_id
   └─ > 1 orgs → return `requires_org_selection=true` + org list → frontend shows selector

3. Frontend calls POST /api/v1/auth/select-org {org_id}
4. Backend: verify user ∈ org (org_members.is_active=True)
5. Issue new JWT with claim: {"user_id": X, "active_org_id": Y, ...}
```

**JWT payload shape:**

```python
{
    "user_id": 123,
    "email": "user@example.com",
    "type": "access_token",
    "exp": ...,
    "active_org_id": 45,           # v1.1 new, optional
    "active_role": "rpsst_admin",  # v1.1 new, snapshot of role in that org
}
```

**Read in middleware:**
```python
# app/utils/security.py (extended)
def get_active_org_context(credentials) -> tuple[int | None, str | None]:
    payload = jwt.decode(...)
    return payload.get("active_org_id"), payload.get("active_role")
```

**Org switching = re-issue JWT** (user clicks org switcher → POST /auth/select-org → new token)

**Why JWT claim, not DB column:**
- Stateless (scale-friendly, ไม่ต้อง sync)
- UserSession (ของเดิม) = session token validity only; org context = JWT claim (separate concern)
- Logout ยังใช้งาน invalidate session เดิม

**Implementation order:**
- Phase 1a (MVP): สร้าง `POST /api/v1/auth/select-org` endpoint + JWT claim
- Phase 1b: Frontend org selector UI (ADMIN_WEB_SPEC, ASM_PWA_SPEC)
- Legacy users (ไม่มี org membership): JWT ไม่มี `active_org_id` → v2 endpoints ที่ต้องการ org context → 403

---

## 7. Audit Log — Detailed Spec

### 7.1 Events to log (MUST)

| Action | Trigger | metadata fields |
|--------|---------|-----------------|
| `login_success` | Auth success | `{method: "phone_otp" / "password", org_context: ...}` |
| `login_failure` | Auth failure | `{method, reason, attempt_count}` |
| `password_change` | User changes password | `{via: "self" / "admin_reset"}` |
| `user_create` | New user created | `{account_type, primary_role, created_by_role}` |
| `user_suspend` | User suspended | `{reason}` |
| `user_deactivate` | Right to be forgotten | `{fields_cleared: [...]}` |
| `care_assignment_create` | New assignment | `{caregiver_id, patient_id, org_id}` |
| `care_assignment_end` | End assignment | `{end_reason}` |
| `patient_view` | Non-owner views patient | `{via_endpoint, filters}` |
| `patient_list_view` | Non-owner lists patients | `{filter, count, org_id}` |
| `bp_reading_create` | Record created | `{measurement_context, measured_by, source: "manual"/"ocr_single"/"ocr_batch"}` |
| `bp_reading_view` | Non-owner views | `{reading_id}` |
| `bp_reading_update` | Record updated | `{old_value, new_value, fields_changed}` |
| `bp_reading_delete` | Record deleted | `{old_value}` |
| `consent_grant` | Consent granted | `{scope, method, version}` |
| `consent_withdraw` | Consent withdrawn | `{scope, reason}` |
| `data_export` | Data exported | `{format, filter, row_count, target_type}` |
| `data_subject_request` | Request from data subject | `{type: "view"/"export"/"delete", fulfilled_at}` |
| `ocr_batch_process` | OCR batch run | `{image_id, patients_detected, confidence_avg}` |

### 7.2 Events to NOT log (reduce noise)

- User's own BP reading views (not cross-user) — too noisy
- Health checks / system probes
- Static file access

### 7.3 Log writing strategy

- **Async write** — ไม่ block main request (ใช้ background task หรือ queue)
- **At-least-once delivery** — ถ้า log fail ต้อง retry ไม่ลืม
- **Tamper-evident** (optional, advanced) — chain hash ของแต่ละ log entry เพื่อ detect modification

### 7.4 Log reading / query patterns

```sql
-- คนดูข้อมูลคนไข้ X ในเดือนที่แล้วทั้งหมด
SELECT * FROM audit_logs
WHERE target_user_id = X AND created_at >= NOW() - INTERVAL '30 days'
ORDER BY created_at DESC;

-- อสม. Y ทำอะไรบ้างวันนี้
SELECT * FROM audit_logs
WHERE actor_user_id = Y AND created_at >= CURRENT_DATE
ORDER BY created_at DESC;

-- Failed logins ในชั่วโมงที่แล้ว (security monitoring)
SELECT * FROM audit_logs
WHERE action = 'login_failure' AND created_at >= NOW() - INTERVAL '1 hour';
```

### 7.5 Retention

- Hot storage (in DB): 2 ปี
- Cold storage (S3 / archive): 5 ปี
- After 5 ปี: ลบ (PDPA purpose limitation)

### 7.6 AdminAuditLog → AuditLog transition (v1.1 new)

> **Decision 4.4 (PLAN_REVIEW_RESPONSE):** Dual-write transition, no data migration of existing records

**Problem context:**
- Existing `admin_audit_logs` table มี writers จริงใน `routers/admin.py` + schema `AdminAuditLogResponse`
- Plan v2 ต้องการ `audit_logs` (BigInt PK + JSONB metadata) — schema ไม่เข้ากับของเดิม
- Data migration risky เพราะ writer concurrent

**Transition phases:**

| Phase | Duration | Writers | Readers (admin UI) |
|-------|----------|---------|-----|
| **1 (v1.1 MVP)** | Launch | Write BOTH to `admin_audit_logs` + `audit_logs` | Query both, merge by `created_at` |
| **1.5** | +1 month | Same | Same (validate new schema works) |
| **2** | +3 months | Write only `audit_logs` (stop writing admin_audit_logs) | Query both (admin_audit_logs read-only) |
| **3** | +2 years (retention expiry) | `audit_logs` only | `audit_logs` only; drop `admin_audit_logs` table |

**Dual-write helper:**
```python
# app/services/audit_service.py
async def log_audit(action, actor_user_id, target_user_id, metadata, ...):
    # Phase 1: write BOTH
    audit_row = AuditLog(
        action=action,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        metadata=metadata,  # JSONB
        ...
    )
    db.add(audit_row)

    # Legacy mirror (Phase 1 only)
    if ENABLE_DUAL_WRITE_AUDIT:  # feature flag
        legacy_row = AdminAuditLog(
            admin_user_id=actor_user_id,
            action=action,
            target_user_id=target_user_id,
            details=json.dumps(metadata),  # Text
        )
        db.add(legacy_row)

    await db.commit()
```

**Admin UI dual-read (Phase 1 & 2):**
```python
# routers/admin.py
async def get_audit_history(actor_id: int, ...):
    # New source
    new_logs = db.query(AuditLog).filter(AuditLog.actor_user_id == actor_id).all()
    # Legacy source (read-only)
    legacy_logs = db.query(AdminAuditLog).filter(AdminAuditLog.admin_user_id == actor_id).all()
    # Merge by created_at desc
    return merge_logs(new_logs, legacy_logs, sort_key="created_at", desc=True)
```

---

## 8. Data Flow Examples

### 8.1 อสม. บันทึก BP ให้ชาวบ้าน

```
อสม.เปิด PWA 
  → GET /asm/patients (with JWT, role=asm)
  → middleware: check role=asm, get caregiver_id from JWT
  → query: JOIN care_assignments WHERE caregiver_user_id=X AND is_active=True
  → log: patient_list_view
  → return list of patients

อสม.เลือก patient Y, บันทึก BP
  → POST /asm/readings {patient_id=Y, systolic=130, ...}
  → middleware: check permission CREATE_READING_FOR_ASSIGNED with context {target_user_id=Y}
  → verify Y is assigned to อสม.
  → check active consent scope=asm_collect for Y
  → create BloodPressureRecord with measured_by_user_id=อสม., measurement_context=asm_field_visit
  → log: bp_reading_create
  → return 201
```

### 8.2 Consent withdrawal

```
ชาวบ้าน Z ต้องการถอน consent (ผ่านการติดต่อ รพ.สต.)
  → admin เปิด web → dashboard → patient Z → consent records
  → PATCH /admin/consent/{consent_id} {status="withdrawn", reason="..."}
  → middleware: check role=rpsst_admin, org ownership
  → update consent: status=withdrawn, withdrawn_at=now
  → log: consent_withdraw
  → trigger: stop allowing BP writes for Z (scope=asm_collect)
  → optional: notify อสม. assigned to Z
```

---

## 9. Coding Tasks (เป็น actionable list)

### 9.1 Models (models.py)
- [ ] Add enums: AccountType, UserRole, OrganizationType, MeasurementContext, ConsentScope, ConsentMethod, ConsentStatus, AuditAction
- [ ] Add `Organization` model
- [ ] Add `OrganizationMember` model
- [ ] Add `CareAssignment` model
- [ ] Add `AuditLog` model (BigInt PK, JSONB metadata)
- [ ] Add `PairingCode` model
- [ ] Add `File` model
- [ ] Extend `ConsentRecord` (or create new if not exists)
- [ ] Extend `User` with `account_type`, `primary_role`, `managed_by_organization_id`, `deleted_at`, `deletion_reason`
- [ ] Extend `BloodPressureRecord` with new fields (section 4.2.2)

### 9.2 Migrations
- [ ] Create `schema_migrations` version table (see INFRASTRUCTURE_SETUP)
- [ ] ~13 migration scripts per §5.1 sequence (v2_00 through v2_13)
- [ ] Each script: both `migrate()` + `rollback()`
- [ ] Test upgrade + rollback cycle on Neon staging branch
- [ ] Run backfill on staging with prod data snapshot
- [ ] Verify zero data loss + existing endpoints still pass tests
- [ ] Update `migrations/run_all.py` to chain v2_* scripts after existing add_* scripts

### 9.3 Permissions / Middleware
- [ ] `app/utils/permissions.py` — Permission enum + ROLE_PERMISSIONS dict
- [ ] `has_permission(user, permission, context)` function
- [ ] Context checkers (is_caregiver_of, are_in_same_org, etc.)
- [ ] `app/middleware/rbac.py` — `require_permission` decorator
- [ ] `app/middleware/audit.py` — `log_audit()` helper with async write
- [ ] Unit tests for every permission/context combo

### 9.4 Repositories / Services
- [ ] `OrganizationService` — CRUD, members, hierarchy
- [ ] `CareAssignmentService` — assign, transfer, end
- [ ] `ConsentService` — grant, withdraw, check active
- [ ] `AuditLogService` — write (async), query

### 9.5 Seed data (for dev + pilot)
- [ ] Seed: Organization (ตำบลเมืองเก่า รพ.สต.)
- [ ] Seed: 1 rpsst_admin user
- [ ] Seed: 2 อสม. users
- [ ] Seed: 20-40 proxy patients (fake data for dev)

---

## 10. Testing Requirements

### 10.1 Unit tests
- Every permission+context combination
- Consent scope enforcement
- Care assignment lifecycle (create, transfer, end)
- Audit log writing (every AuditAction)

### 10.2 Integration tests
- End-to-end: อสม. onboard → login → view patients → create reading
- End-to-end: admin create รพ.สต. → add อสม. → assign patient → view data
- PDPA flows: grant consent → create reading → withdraw consent → verify subsequent reads denied

### 10.3 Security tests
- Try accessing other org's data (should 403 + audit log)
- Try accessing assigned patient's data after assignment ended (should 403)
- Try creating reading without active consent (should 403)

### 10.4 Migration tests
- Run upgrade + downgrade cycle 3 times on test DB
- Verify existing user data intact after migration

---

## 11. Backward Compatibility Guarantees

- ✅ Existing self_managed users ยังใช้ bot + web เหมือนเดิม
- ✅ Existing doctor-patient relationship (`DoctorPatient`, `AccessRequest`) ยังทำงาน — ดู §4.3
- ✅ `users.role` column (String) ยังมีอยู่ — `require_verified_doctor`, `require_staff`, bot services ยัง read ได้ (v1.1 decision 4.2)
- ✅ API endpoints เดิมยัง compatible (เพิ่ม optional fields, ไม่ break)
- ✅ Bot commands เดิมใช้ได้
- ✅ Telegram Mini App plan (`TELEGRAM_MINI_APP_PLAN.md`) ไม่กระทบ — ยังใช้ได้
- ✅ Existing BP records ยังดูได้ + stats/trend ใช้ได้ (backfill เติม `measured_at = measurement_date`)
- ✅ `AdminAuditLog` records เดิมยังอ่านได้ จาก admin UI (dual-read) — ดู §7.6
- ✅ Feature flag `ENABLE_ORG_MODE=false` default: v2 endpoints ปิด ระบบทำงานเสมือนเดิม 100%

---

## 12. Open Questions

### 12.1 Resolved (v1)
- ✅ **Organization code format** — ใช้ UUID `external_id` + optional `code` + `code_system` (รองรับทั้ง HCODE + commercial)
- ✅ **File storage backend** — PostgreSQL BYTEA ผ่าน abstraction layer ใน MVP
- ✅ **Legal structure** — In-app ToS/Privacy Policy/Consent acceptance (no external DPA)

### 12.2 Still open
1. **Subdistrict code reference table** — import จาก opendata ของกรมการปกครองไหม? หรือ hardcode แค่ที่ pilot ก่อน?
2. **Audit log partitioning** — เมื่อ log โตถึง X rows (เช่น 100M) จะ partition by month หรือไม่? ควรเตรียม schema ตั้งแต่ตอนนี้ไหม?
3. **Sequence_in_list auto-assign** — เมื่อสร้าง care_assignment ควร auto-increment sequence หรือให้ admin กำหนดเอง?
4. **Org member enforcement** — อสม. ต้องเป็น `OrganizationMember` ของ รพ.สต. เดียวกับ patient ไหม? (ตอบเบื้องต้น: ควร enforce)
5. **File encryption key rotation** — ใช้ key เดียวกับ PII Fernet key หรือแยก? (เพื่อให้ rotate ได้อิสระ)

---

**End of ORG_FOUNDATION.md**
