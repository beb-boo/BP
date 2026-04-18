---
title: "Data Retention Policy"
aliases:
  - "Retention"
  - "Retention Policy"
tags:
  - pdpa
  - compliance
  - policy
  - retention
  - v2-asm-org
order: 9
status: draft
version: 1.0
updated: 2026-04-18
summary: "Retention rules for every data type: BP readings, consent records, audit logs, OCR images, backups. Auto-deletion implementation details."
related:
  - "[[PDPA_COMPLIANCE]]"
  - "[[ORG_FOUNDATION]]"
  - "[[CONSENT_FLOW_SPEC]]"
  - "[[BREACH_RESPONSE_RUNBOOK]]"
---
# Data Retention Policy

> **Status:** Draft v1
> **Last updated:** 2026-04-18
> **Owner:** Pornthep
> **Effective date:** [TBD — set on Phase 1 launch]
> **Review cycle:** Annually

---

## 1. Principles

### 1.1 Guiding Principles

1. **Purpose limitation** — เก็บข้อมูลเท่าที่จำเป็นต่อ purpose ที่แจ้งไว้ (ม.22 PDPA)
2. **Storage limitation** — ไม่เก็บนานกว่าที่ purpose ต้องการ
3. **Legal compliance** — ปฏิบัติตามข้อกำหนดเฉพาะทางการแพทย์ + การเงิน
4. **User agency** — ชาวบ้านขอให้ลบได้ตลอดเวลา (ยกเว้น legal hold)
5. **Automation** — การลบต้องเป็นระบบอัตโนมัติ ไม่พึ่ง manual
6. **Audit trail** — ทุกการลบต้อง logged (แต่ log เองก็มี retention)

### 1.2 Data Minimization First

ก่อนตั้ง retention policy: ถามตัวเองเสมอว่า **"ต้องเก็บเลยไหม?"** ถ้าไม่ต้อง — ไม่เก็บเลย (ดู [[ORG_FOUNDATION]] design principle #8)

---

## 2. Retention Rules by Data Type

### 2.1 User / Account Data

| Data type | Retention | Trigger for deletion | Rationale |
|-----------|-----------|---------------------|-----------|
| Account profile (self_managed) | Active + 90 days after deactivation | User requests deletion OR inactive 2 years | Contract + grace period |
| Account profile (proxy_managed — ชาวบ้าน) | Active + 90 days after withdrawal | All core consents withdrawn OR admin request | PDPA + medical record |
| Account profile (อสม. — active in org) | Active membership + 1 year | Remove from org + grace | Audit trail |
| Account profile (อสม. — left org) | 1 year after leaving | Auto-anonymize after 1 year | Historical accountability |
| Account profile (admin) | Active + 1 year after role removed | Manual deactivation | Audit trail |
| Password hash | Until password changed | Immediate on change | Security |
| OTP codes (in Redis) | 5 minutes | Auto-expire (Redis TTL) | Purpose-limited |
| Session tokens (JWT) | 24 hours (access), 30 days (refresh) | Auto-expire | Security |
| Failed login attempts | 90 days | Auto-cleanup cron | Security forensics |
| Telegram pairing code | 15 minutes | Auto-expire OR used | Single-use |

### 2.2 Health / Sensitive Data

| Data type | Retention | Trigger for deletion | Rationale |
|-----------|-----------|---------------------|-----------|
| BP readings (self_managed) | Until user deletes OR account deletion | User action | User agency |
| BP readings (proxy_managed) | 10 years from last reading | Consent withdrawal OR 10-year mark | Medical records standard |
| BP readings (for deactivated user) | Anonymized, retained 10 years | On account deletion | Research + public health |
| Measurement location (GPS) | Same as BP reading | - | - |
| OCR raw output (JSON) | Same as BP reading | - | Audit OCR performance |
| OCR confidence scores | Same as BP reading | - | - |
| Physical data (height, weight, blood type) | Same as BP reading | - | - |

### 2.3 Consent Records

| Data type | Retention | Trigger for deletion | Rationale |
|-----------|-----------|---------------------|-----------|
| Consent record (active) | As long as active + 10 years post-withdrawal | Legal requirement | Legal defensibility |
| Digital signature (encrypted) | Same as consent record | - | Evidence |
| Consent withdrawal record | 10 years from withdrawal | - | Audit |
| Consent version superseded | 10 years from supersession | - | Historical audit |
| Paper consent (physical) | 10 years (at รพ.สต.) | Manual shred + certificate | Physical record |

### 2.4 Audit Logs

| Data type | Hot storage | Cold storage | Total retention | Rationale |
|-----------|-------------|--------------|-----------------|-----------|
| Authentication events | 2 years | 5 years | 7 years | Security forensics |
| Data access events | 2 years | 5 years | 7 years | PDPA accountability |
| Data modification events | 2 years | 5 years | 7 years | Audit |
| Consent change events | 10 years (in DB) | - | 10 years | Legal |
| Data subject request events | 10 years (in DB) | - | 10 years | PDPA ม.30-35 |
| Breach response events | Indefinite | - | Indefinite | Security + legal |
| System events (deploys, config) | 90 days | 1 year | 1 year 3 months | Operational |

### 2.5 File Storage (from [[ORG_FOUNDATION]] section 4.1.7)

| Purpose | Retention | Auto-delete | Rationale |
|---------|-----------|-------------|-----------|
| `ocr_batch_review_temp` | Max 7 days | On review complete OR expiry | Data minimization |

**Not stored (by design):**
- BP photo single — discarded immediately after OCR
- Consent paper scans — physical only at รพ.สต.
- Patient documents — out of MVP scope

### 2.6 Payment & Subscription Data

| Data type | Retention | Trigger | Rationale |
|-----------|-----------|---------|-----------|
| Transaction records (amount, reference) | 5 years | Transaction date + 5 yr | Revenue Department (กรมสรรพากร) |
| Payment slip images | 5 years | - | Tax audit |
| Subscription history | As long as customer + 5 years | - | Billing disputes |
| Invoice records | 10 years | - | Accounting law (บัญชี) |

### 2.7 Communication Data

| Data type | Retention | Trigger | Rationale |
|-----------|-----------|---------|-----------|
| Telegram message content (BP data) | Stored in DB as BP readings | Per BP reading rules | - |
| Telegram message metadata (chat_id, timestamps) | 90 days | Rolling window | Operational debugging |
| Email notifications sent | 1 year | Rolling window | Support |
| SMS (OTP) logs | 90 days | Rolling window | Security |
| Support ticket content | 2 years from closure | Closure + 2 yr | User support |
| Webhook logs (inbound/outbound) | 30 days | Rolling | Debugging |

### 2.8 Organization Data

| Data type | Retention | Trigger | Rationale |
|-----------|-----------|---------|-----------|
| Organization profile | Active + 1 year after deactivation | Termination | Contract |
| Organization members (historical) | 5 years from departure | - | Audit |
| Care assignments (inactive) | 10 years from end | - | Medical record traceability |
| Terms acceptance records | 10 years from last acceptance | - | Legal |

### 2.9 Backups & Infrastructure

| Data type | Retention | Trigger | Rationale |
|-----------|-----------|---------|-----------|
| Database daily backup | 30 days | Rolling | DR recovery |
| Database weekly backup | 3 months | Rolling | DR + audit |
| Database monthly backup | 1 year | Rolling | Long-term DR |
| Application logs | 90 days | Rolling | Debugging |
| Infrastructure metrics | 1 year | Rolling | Capacity planning |
| Security event logs | 2 years | Rolling | Forensics |

### 2.10 Aggregated / Anonymized Data

Aggregated statistics that cannot re-identify individuals can be retained **indefinitely** for:
- System performance analysis
- Public health research (with consent scope: `research_anonymized`)
- Product improvement metrics

**Requirement:** k-anonymity ≥ 5 (group size), no direct identifiers, no quasi-identifiers combinations that enable re-identification

---

## 3. Legal Basis for Retention Periods

### 3.1 10 Years (Medical Records)

Sources:
- **กฎกระทรวงสาธารณสุข เรื่อง หลักเกณฑ์ วิธีการ และเงื่อนไขในการดำเนินการเวชระเบียน** — 10 ปี มาตรฐาน
- **พระราชบัญญัติการประกอบวิชาชีพเวชกรรม พ.ศ. 2525** — ผู้ประกอบวิชาชีพต้องเก็บประวัติ
- Practical: most legal claims must be filed within 10 years

### 3.2 5 Years (Tax & Accounting)

Sources:
- **ประมวลรัษฎากร (Revenue Code)** — 5 ปี การเก็บหลักฐานภาษี
- **พระราชบัญญัติการบัญชี พ.ศ. 2543** — 5 ปี การเก็บเอกสารบัญชี

### 3.3 7 Years (Security Forensics)

- Industry best practice for breach forensics
- PDPA doesn't mandate specific period — principle-based
- Balances investigation needs vs data minimization

### 3.4 90 Days (Operational Grace)

- Common grace period for user reactivation
- Short enough to respect data minimization
- Long enough for practical re-onboarding

---

## 4. Implementation

### 4.1 Auto-Deletion Jobs

All retention enforcement implemented as **scheduled background jobs**.

#### Job 1: OCR image cleanup (high frequency)

```python
# app/jobs/file_cleanup.py
# Run: every 6 hours

async def cleanup_expired_files():
    now = datetime.utcnow()
    expired = await db.query(File).filter(
        File.expires_at < now,
        File.deleted_at.is_(None)
    ).all()
    
    for file in expired:
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

#### Job 2: OTP cleanup

Via Redis TTL — automatic, no code needed

#### Job 3: Session cleanup

```python
# Run: daily

async def cleanup_expired_sessions():
    await db.execute(text("""
        DELETE FROM refresh_tokens
        WHERE expires_at < NOW() - INTERVAL '7 days'
    """))
```

#### Job 4: Failed login cleanup

```python
# Run: daily

async def cleanup_failed_logins():
    await db.execute(text("""
        DELETE FROM failed_login_attempts
        WHERE created_at < NOW() - INTERVAL '90 days'
    """))
```

#### Job 5: Audit log archival (hot → cold)

```python
# Run: monthly
# After 2 years in hot, move to S3 cold storage

async def archive_old_audit_logs():
    cutoff = datetime.utcnow() - timedelta(days=365*2)
    
    # For partitioned table (recommended in [[SCALABILITY_PLAN]]):
    # DETACH old partition → export to S3 → DROP
    
    # For non-partitioned:
    await db.execute(text("""
        COPY (SELECT * FROM audit_logs WHERE created_at < :cutoff)
        TO PROGRAM 'aws s3 cp - s3://bp-audit-archive/YYYY-MM.csv.gz --gzip'
        WITH CSV HEADER
    """), {"cutoff": cutoff})
    
    await db.execute(text("""
        DELETE FROM audit_logs WHERE created_at < :cutoff
    """), {"cutoff": cutoff})
```

#### Job 6: Audit log cold storage deletion (after 7 years total)

```python
# Run: quarterly

async def delete_very_old_audit_archives():
    cutoff = datetime.utcnow() - timedelta(days=365*7)
    # S3 Lifecycle rule handles this (configure bucket policy)
```

#### Job 7: Inactive user anonymization

```python
# Run: monthly

async def anonymize_inactive_users():
    cutoff = datetime.utcnow() - timedelta(days=365*2)
    
    inactive = await db.query(User).filter(
        User.last_login_at < cutoff,
        User.is_active == True,
        User.account_type == AccountType.self_managed,
        User.deleted_at.is_(None)
    ).all()
    
    for user in inactive:
        # Send warning email 30 days before
        # ... (separate job)
        
        # Deactivate + anonymize
        user.email_encrypted = None
        user.phone_encrypted = None
        user.full_name_encrypted = None
        user.citizen_id_encrypted = None
        user.telegram_id_encrypted = None
        # Keep: email_hash, phone_hash (for lookup only)
        user.deleted_at = datetime.utcnow()
        user.deletion_reason = "inactive_2_years"
        
        await log_audit(
            action=AuditAction.user_deactivate,
            target_user_id=user.id,
            metadata={"reason": "inactive_2_years", "fields_cleared": ["email", "phone", "full_name", "citizen_id", "telegram_id"]}
        )
    
    await db.commit()
```

#### Job 8: Deactivated user hard anonymization (90 days after deactivation)

```python
# Run: weekly

async def hard_anonymize_deactivated_users():
    cutoff = datetime.utcnow() - timedelta(days=90)
    
    users = await db.query(User).filter(
        User.deleted_at < cutoff,
        User.email_encrypted.isnot(None)  # still has PII
    ).all()
    
    for user in users:
        # Wipe remaining PII (if any missed)
        # Keep audit log reference
        user.email_encrypted = None
        user.phone_encrypted = None
        user.full_name_encrypted = None
        # ... all encrypted fields
        
        # Anonymize BP readings (not delete, just anonymize)
        await db.execute(text("""
            UPDATE bp_readings
            SET user_id = :anon_id
            WHERE user_id = :user_id
        """), {"user_id": user.id, "anon_id": generate_anonymous_id()})
    
    await db.commit()
```

#### Job 9: Consent record retention enforcement

```python
# Run: monthly

async def cleanup_old_consent_records():
    cutoff = datetime.utcnow() - timedelta(days=365*10)
    
    # Withdrawn records older than 10 years
    old_withdrawn = await db.query(ConsentRecord).filter(
        ConsentRecord.status == ConsentStatus.withdrawn,
        ConsentRecord.withdrawn_at < cutoff
    ).all()
    
    for record in old_withdrawn:
        # Remove encrypted signature (keep metadata for audit)
        record.digital_signature_data = None
        # Keep hash, GPS, timestamps (not PII)
    
    await db.commit()
```

#### Job 10: Backup retention (S3 Lifecycle)

Configure S3 bucket lifecycle policy (no code needed):
```yaml
Rules:
  - Id: daily-backups
    Prefix: daily/
    Expiration: { Days: 30 }
  - Id: weekly-backups  
    Prefix: weekly/
    Expiration: { Days: 90 }
  - Id: monthly-backups
    Prefix: monthly/
    Expiration: { Days: 365 }
```

### 4.2 Scheduling

| Job | Frequency | Method (MVP) | Method (Phase 2+) |
|-----|-----------|--------------|-------------------|
| File cleanup | Every 6h | Vercel Cron | K8s CronJob |
| Session cleanup | Daily | Vercel Cron | K8s CronJob |
| Failed login cleanup | Daily | Vercel Cron | K8s CronJob |
| Audit archival | Monthly | Manual (MVP) | Automated pipeline |
| Audit deletion | Quarterly | Manual | S3 Lifecycle |
| Inactive anonymization | Monthly | Manual | Automated |
| Hard anonymization | Weekly | Vercel Cron | K8s CronJob |
| Consent cleanup | Monthly | Manual (MVP) | Automated |
| Backup retention | Continuous | S3 Lifecycle | S3 Lifecycle |

### 4.3 Monitoring

Every retention job must:
- Log execution start/end to audit log
- Report count of records processed
- Alert on failure (Sentry)
- Create dashboard metric for DPO review

Example metrics:
- `retention.files.deleted_count` (daily)
- `retention.users.anonymized_count` (monthly)
- `retention.audit_logs.archived_count` (monthly)
- `retention.job.failures` (real-time alert if > 0)

---

## 5. Special Cases

### 5.1 Legal Hold

If data is subject to legal hold (litigation, regulator investigation, court order):
- **PAUSE auto-deletion** for affected records
- Flag in DB: `legal_hold = true, legal_hold_reason, legal_hold_set_at`
- Document in internal log
- Notify DPO
- Resume deletion after hold lifted

### 5.2 Data Subject Erasure Request

When user requests deletion:
- Override standard retention (if no legal obligation)
- Execute within 30 days
- Document in data_subject_request log
- Confirm to user upon completion

**But:** retain audit trail of the deletion itself for 7 years

### 5.3 Deceased Person Data

**MVP scope:** Not explicitly addressed

**Phase 2 approach:**
- If family notifies: mark user as deceased
- Retain data for 10 years (medical records)
- Allow legal representative to exercise rights
- No new data collection

### 5.4 Organization Dissolution

If รพ.สต. discontinues using our service:
- 30-day notice period
- Export all org data
- Transfer to replacement รพ.สต. (if exists) with new consent
- Otherwise: anonymize per standard rules
- Physical consent papers handled by org per their own procedures

### 5.5 Breach-Related Data

Data related to security incidents:
- **Indefinite retention** for incident reports, investigation notes
- Encrypted, access-restricted
- Legal hold considerations
- Needed for potential future litigation

---

## 6. User Communication

### 6.1 Notification of Retention Policy

Users informed via:
- Privacy Policy section 8
- Consent form (retention summary)
- In-app: Settings → My Data → Retention info

### 6.2 Pre-Deletion Notifications

For inactive user anonymization:
- **30 days before:** Email notification + in-app banner
- **7 days before:** Final warning email
- **Day of:** Anonymization occurs + confirmation email

Content includes:
- What will be deleted
- How to preserve account (login, or export first)
- Contact for questions

### 6.3 Post-Deletion Notification

User receives email confirming:
- What was deleted
- What was retained (and why — legal obligation)
- How to verify (they can check by trying to login — should fail)

---

## 7. DPO Review Cadence

DPO reviews retention policy:
- **Quarterly:** Check auto-deletion jobs ran correctly
- **Annually:** Review entire policy for updates
- **Ad hoc:** When new data types added (update this doc)

---

## 8. Retention Policy Changes

### 8.1 Version Control

This document has version history. Changes require:
- DPO approval
- Legal review (for material changes)
- User notification (if retention shortened significantly)

### 8.2 Notification Requirements

| Change type | Notification | Effective date |
|-------------|--------------|----------------|
| Retention shortened | 30 days in advance | After notice period |
| Retention extended | At next privacy policy update | Immediate for new data |
| New data type added | At next privacy policy update | Immediate |
| Legal basis changes | Immediate notification + re-consent if needed | Upon re-consent |

---

## 9. Quick Reference Card (for Admins/DPO)

| Question | Answer |
|----------|--------|
| How long do we keep BP readings? | 10 years (medical records) |
| How long do we keep consent records? | 10 years from withdrawal |
| How long do we keep audit logs? | 2 years hot + 5 years cold |
| How long do we keep OCR images? | Max 7 days (only if in review queue) |
| How long do we keep payment slips? | 5 years (tax) |
| How long do we keep backups? | 30d daily, 3mo weekly, 1yr monthly |
| Can we delete user data on request? | Yes, within 30 days (unless legal hold) |
| What if user is inactive? | Anonymize after 2 years |
| When do we auto-delete? | Run jobs every 6h (files), daily, weekly, monthly |
| Where is this documented? | This file + Privacy Policy |

---

## 10. Related Documents

- [[PDPA_COMPLIANCE]] — master compliance reference
- [[ORG_FOUNDATION]] — technical implementation
- [[BREACH_RESPONSE_RUNBOOK]] — breach retention rules
- [[CONSENT_FLOW_SPEC]] — consent record retention detail
- `docs/privacy-policy.md` (v2) — user-facing summary

---

**End of DATA_RETENTION_POLICY.md**
