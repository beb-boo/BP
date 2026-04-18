---
title: "PDPA Compliance Master Reference"
aliases:
  - "PDPA"
  - "Compliance"
  - "PDPA Master"
tags:
  - pdpa
  - compliance
  - legal
  - privacy
  - v2-asm-org
order: 8
status: draft
version: 1.0
updated: 2026-04-18
summary: "Master PDPA compliance reference: legal bases, data subject rights, joint controller model, cross-border transfers, ROPA, breach response, compliance checklist"
related:
  - "[[MVP_PILOT_SCOPE]]"
  - "[[ORG_FOUNDATION]]"
  - "[[CONSENT_FLOW_SPEC]]"
  - "[[DATA_RETENTION_POLICY]]"
  - "[[BREACH_RESPONSE_RUNBOOK]]"
  - "[[CONSENT_FORMS]]"
---
# PDPA Compliance Master Reference

> **Status:** Draft v1 — เอกสารอ้างอิงสูงสุดสำหรับ PDPA compliance ของ BP Monitor
> **Last updated:** 2026-04-18
> **Owner:** Pornthep
> **Disclaimer:** เอกสารนี้เป็น internal reference ไม่ใช่คำปรึกษาทางกฎหมาย ให้ PDPA consultant review ก่อน production

---

## 1. Purpose

เอกสารนี้สรุปกรอบ compliance กับ **พระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 (PDPA)** สำหรับระบบ BP Monitor v2 โดยเฉพาะอย่างยิ่งในส่วนที่เกี่ยวข้องกับ:

- **ข้อมูลอ่อนไหว (Sensitive Personal Data)** ตามมาตรา 26 — ข้อมูลสุขภาพ
- **Joint controller model** — platform + รพ.สต. ร่วมกันเป็น data controller
- **Proxy-managed patients** — ชาวบ้านที่ อสม. เก็บข้อมูลให้
- **Cross-border transfer** — Neon/Vercel/Gemini (US)

---

## 2. PDPA Foundation

### 2.1 Relevant Articles

| มาตรา | หัวข้อ | ความเกี่ยวข้อง |
|-------|--------|--------------|
| ม.6-7 | Data protection principles | ทุก processing activity |
| ม.19 | Consent requirements | Base สำหรับ digital signature + paper |
| ม.20 | Children under 20 | Out of scope MVP |
| ม.22 | Data subject rights notification | User-facing flows |
| ม.24 | Lawful bases (general data) | Account management, billing |
| ม.26 | **Sensitive data (รวมข้อมูลสุขภาพ)** | **Core ของระบบเรา** |
| ม.27 | Further processing | Research scope, exports |
| ม.28 | Cross-border transfer | Neon, Vercel, Gemini (US) |
| ม.30-35 | Data subject rights | View, edit, delete, portability, withdraw |
| ม.37 | Data breach notification | 72-hour rule |
| ม.39-42 | DPO requirement | Assessment needed |

### 2.2 Key Concepts

- **Data Subject (เจ้าของข้อมูลส่วนบุคคล):** ชาวบ้าน, อสม., admin, doctor — ทุก user
- **Data Controller (ผู้ควบคุมข้อมูล):** เรา + รพ.สต. (joint, for org-mode users)
- **Data Processor (ผู้ประมวลผลข้อมูล):** Neon, Vercel, Upstash, Gemini, Telegram, SlipOK
- **Sensitive Data:** ข้อมูลสุขภาพ (BP readings, โรคประจำตัว), ลายเซ็นไบโอเมตริก (ลายนิ้วมือ)
- **Explicit Consent:** ต้องชัดแจ้ง, granular, withdrawable (ม.19)

---

## 3. Data Controller Model

### 3.1 Single Controller (Legacy / Self-Managed Users)

**User type:** ชาวบ้านที่ลงทะเบียนเอง (v1 flow, AccountType = self_managed)

**Controller:** เราเพียงฝ่ายเดียว

**Obligations:**
- ทั้งหมดตามที่ระบุใน privacy policy v1/v2
- Data subject rights ติดต่อเราโดยตรง

### 3.2 Joint Controllers (Org-Mode Users) — NEW in v2

**User type:** ชาวบ้าน proxy-managed โดย รพ.สต., อสม. ที่เป็นสมาชิก รพ.สต.

**Controllers:**
1. **เรา (Platform Provider)** — รับผิดชอบเทคนิคและระบบ
2. **รพ.สต. (Organization)** — รับผิดชอบข้อมูล content + operational

### 3.3 Responsibility Matrix

| Activity | Platform (เรา) | รพ.สต. (องค์กร) |
|----------|:-------------:|:-------------:|
| System infrastructure, uptime | ✅ Primary | - |
| Encryption at rest + in transit | ✅ Primary | - |
| Access control (RBAC) | ✅ Primary | Configure (add/remove members) |
| Audit logging | ✅ Primary | Use for oversight |
| PDPA technical controls | ✅ Primary | - |
| Obtain consent from data subjects | Provide tools | ✅ Execute (via อสม.) |
| Verify data accuracy | - | ✅ Primary |
| Physical security of paper consent | - | ✅ Primary (locked cabinet) |
| Data subject request response | ✅ Technical execution | ✅ Initial contact + verification |
| Breach detection (platform-side) | ✅ Primary | - |
| Breach detection (content-side) | - | ✅ Primary (e.g., wrong patient data) |
| Breach notification to สคส. | ✅ Primary | Support with evidence |
| Training of users (อสม., admin) | Provide material | ✅ Execute |
| Purpose limitation enforcement | Technical (consent scope) | ✅ Operational |

**Documentation:** Joint controller responsibility recorded in [[ORG_TERMS_OF_SERVICE]] (section 3).

### 3.4 Data Subject Request Handling (Joint Responsibility)

```
Data subject (ชาวบ้าน) asks to see their data
    ↓
Contact either: (a) เรา directly, or (b) รพ.สต.
    ↓
Whoever receives forwards to the other within 5 working days
    ↓
เรา generate technical export (automated)
    ↓
รพ.สต. verify data accuracy + hand to ชาวบ้าน (or mail)
    ↓
Both sides log in audit trail
    ↓
Complete within 30 days (PDPA ม.30 vrdlinyfeldi)
```

---

## 4. Lawful Bases for Processing

### 4.1 Mapping Activities to Legal Bases

| Activity | Data type | Lawful basis | PDPA section |
|----------|-----------|--------------|--------------|
| Create user account | General PII | Contract (ม.24(3)) | ม.24 |
| Send OTP | Phone / Telegram ID | Contract (ม.24(3)) | ม.24 |
| Store blood pressure readings (self_managed) | Sensitive (health) | Explicit consent (ม.19) | ม.26 |
| Store blood pressure readings (proxy_managed) | Sensitive (health) | Explicit consent + healthcare purpose | ม.26 |
| Share BP with doctor | Sensitive (health) | Explicit consent (scope: doctor_view) | ม.26 |
| Share BP with รพ.สต. admin | Sensitive (health) | Explicit consent (scope: rpsst_view) | ม.26 |
| อสม. collect on behalf of patient | Sensitive (health) | Explicit consent (scope: asm_collect) | ม.26 |
| Verify doctor license with TMC | Professional license | Legitimate interest (ม.24(5)) | ม.24 |
| Audit log of access | Metadata | Legal obligation (ม.37 security) | ม.24(6) |
| Fraud detection (failed logins) | Activity data | Legitimate interest (ม.24(5)) | ม.24 |
| Backup and disaster recovery | All | Legal obligation + legitimate interest | ม.24 |
| Processing for research (anonymized) | Anonymized | Explicit consent (scope: research_anonymized) | ม.27 |
| Export to Smart อสม. (future) | All org data | Explicit consent (scope: data_export_to_smart_osm) | ม.27 |
| Communicate updates to users | Email/phone | Contract (ม.24(3)) | ม.24 |
| OCR processing (send image to Gemini) | Image (may contain PII) | Explicit consent ตอน onboarding | ม.26 |

### 4.2 Important: Granular Consent

สำหรับข้อมูลสุขภาพ (ม.26) เราใช้ **granular consent** — แยก scope ให้ user เลือกได้:

- **Core scopes (required to use service):** asm_collect, rpsst_view
- **Optional scopes:** doctor_view, research_anonymized, data_export_to_smart_osm

ผู้ใช้สามารถ:
- ยอมรับเฉพาะ core scopes → ใช้บริการพื้นฐานได้
- ยอมรับ optional scopes → ได้ฟีเจอร์เพิ่มเติม
- Withdraw เฉพาะบาง scope → ฟีเจอร์นั้นถูก disable แต่ service อื่นยังทำงาน

**รายละเอียด scopes ดู [[ORG_FOUNDATION]] section 3 (ConsentScope enum)**

### 4.3 Evidence of Consent

ทุก consent ต้องเก็บหลักฐาน (ม.19 วรรคสอง):
- **What:** scope อะไร
- **When:** timestamp (granted_at)
- **Version:** เวอร์ชันของ consent form
- **Method:** paper / digital / both
- **How:** digital signature + GPS + witness (สำหรับ proxy-managed)
- **Status:** active / withdrawn / expired

ดู schema ใน [[ORG_FOUNDATION]] → `consent_records` table

---

## 5. Data Subject Rights (ม.30-35)

### 5.1 Complete Rights List

| Right | Section | Timeline | Implementation |
|-------|---------|----------|----------------|
| Access own data (ม.30) | Right to access | 30 days | In-app: Profile → Download data |
| Rectify data (ม.32) | Right to correct | 30 days | Self-managed: in-app edit. Proxy: ติดต่อ อสม./รพ.สต. |
| Erase data (ม.33) | Right to be forgotten | 30 days | In-app: Profile → Delete account |
| Restrict processing (ม.34) | Right to restriction | 30 days | Manual process (contact us) |
| Object (ม.32) | Right to object | 30 days | Withdraw consent = object equivalent |
| Data portability (ม.31) | Right to portability | 30 days | In-app: Export as CSV/JSON |
| Withdraw consent (ม.19 วรรคสาม) | Any time | Immediate | In-app or via รพ.สต. |

### 5.2 Implementation Requirements

#### For self-managed users (ม.30-35)
- All rights exercisable **in-app** (self-service)
- Confirmation via OTP
- Processing within 30 days
- No cost to user

#### For proxy-managed users (NEW in v2)
- Rights exercisable via:
  - Contacting รพ.สต. admin (primary channel)
  - Contacting assigned อสม.
  - Direct contact to us: privacy@yourdomain.com
- Identity verification required (national ID + another evidence)
- Processing within 30 days
- รพ.สต. + เรา coordinate response

#### Special: Proxy patient who cannot communicate (incapacitated)
- Legal representative (ผู้อนุบาล) may exercise rights on their behalf
- Requires legal documentation
- Decision recorded in audit log

### 5.3 Proactive Notification (ม.23)

Before/at collection, we must inform data subjects of:
- Identity of controller(s)
- Purpose of processing
- Categories of data collected
- Recipients (who gets the data)
- Retention period
- Rights of the data subject
- Contact for queries

**Implementation:**
- Privacy Policy v2 (comprehensive, on website + in-app)
- Consent form (short summary + link to full policy)
- First-login modal showing key points

### 5.4 Data Erasure Workflow

```
Data subject requests erasure
    ↓
Verify identity (OTP, or national ID for proxy)
    ↓
Determine scope:
    - Account deletion?
    - Specific data type?
    - Specific period?
    ↓
Check retention obligations (medical records, legal holds)
    ↓
Execute:
    - Hard delete: PII from users table (set deleted_at, clear encrypted fields)
    - Anonymize: BP readings (replace user_id with anonymous hash)
    - Preserve: audit logs (2+5 years for security; legal obligation)
    - Preserve: aggregated stats (but remove identifiers)
    ↓
Confirm to data subject within 30 days
    ↓
Log in audit trail: user_deactivate action with metadata
```

### 5.5 Data Portability Format

Export formats supported:
- **CSV** (default, human-readable)
- **JSON** (structured, machine-readable)
- **PDF** (formatted report)

Contents include:
- Profile data (decrypted)
- BP readings history (all timestamps, values, context)
- Consent records (granted/withdrawn history)
- Account activity summary

Signed export (optional Phase 2): include SHA-256 hash + timestamp for tamper detection

---

## 6. Cross-Border Data Transfer (ม.28)

### 6.1 Data Processors Outside Thailand

| Service | Location | Data category | Safeguard |
|---------|----------|---------------|-----------|
| Neon PostgreSQL | US | All (encrypted) | DPA available, SOC 2 Type II |
| Vercel | US | Application data in transit | DPA available, SOC 2 |
| Upstash Redis | US | OTP (5 min TTL) | DPA available |
| Google (Gemini API) | US | OCR images (transient) | DPA available, ISO 27001 |
| Telegram | AE/UK | Messages (OTP, alerts) | Privacy policy, less control |
| SlipOK | Thailand | Payment slips | Thai vendor, no cross-border |

### 6.2 Cross-Border Legal Basis

Per ม.28, cross-border transfer requires:
1. **Adequate protection in receiving country** — US has no adequacy decision from TH PDPC. Workaround:
2. **Appropriate safeguards:**
   - Binding Corporate Rules (N/A for us — we're small)
   - Standard Contractual Clauses (equivalent to EU SCCs) via vendor DPA
   - Explicit consent from data subject (we use this — shown in privacy policy + consent form)
   - Necessity for contract performance (ม.28(2))
3. **Documentation** of safeguards in ROPA (Record of Processing Activities)

### 6.3 Mitigation Strategies

**Short-term (Phase 1 MVP):**
- Explicit cross-border consent in privacy policy
- Encryption at rest (data in US DB is encrypted before upload)
- Vendor DPA in place for all US processors
- Data minimization (don't send more than needed)

**Medium-term (Phase 2):**
- Migrate to in-country cloud (see [[SCALABILITY_PLAN]] section 5)
- Keep only Gemini OCR in US (if cost prohibitive to self-host)
- Document all transfers in ROPA

**Long-term (Phase 3+):**
- Self-hosted OCR (in-country)
- Zero cross-border for health data
- Full data sovereignty

---

## 7. Security Requirements (ม.37)

Section 37 requires "appropriate security measures" considering risk level. For sensitive health data:

### 7.1 Technical Measures

| Measure | Implementation | Status |
|---------|---------------|--------|
| Encryption at rest | Fernet (AES-128) for PII | ✅ Current |
| Encryption in transit | HTTPS/TLS 1.2+ | ✅ Current |
| Hash for search | SHA-256 (phone, citizen_id, email) | ✅ Current |
| Password hashing | Bcrypt | ✅ Current |
| RBAC | Role-based with context checks | ⬜ v2 implementation |
| Tenant isolation | organization_id scope on all queries | ⬜ v2 implementation |
| Audit logging | All cross-user access logged | ⬜ v2 implementation |
| Session management | JWT with rotation, refresh tokens | ✅ Current |
| MFA / 2FA | TOTP for admin, OTP for อสม. | ⬜ v2 |
| Rate limiting | Per user + global | ⬜ v2 implementation |
| Intrusion detection | Vercel WAF + Cloudflare (Phase 2) | ⬜ Phase 2 |
| Backup | Daily automated, 30-day retention | ⬜ v2 implementation |
| DR plan | Documented, tested quarterly | ⬜ v2 implementation |

### 7.2 Organizational Measures

- **Data minimization principle:** Enforced at schema + code level
- **Purpose limitation:** Consent scope enforcement in middleware
- **Access control:** Principle of least privilege
- **Training:** Required for admin, อสม. (covers PDPA basics, security awareness)
- **Incident response:** Documented runbook ([[BREACH_RESPONSE_RUNBOOK]])
- **Regular audit:** Internal quarterly, external annually (Phase 2+)

### 7.3 Anonymization & Pseudonymization

- **Identifiers** stored encrypted (Fernet) — can be decrypted with key access
- **Hash fields** used for search (irreversible lookup)
- **For research exports (consent scope):** full anonymization — replace user_id with random UUID, aggregate across multiple users, K-anonymity if needed

---

## 8. Data Breach Response (ม.37 วรรคสาม)

### 8.1 72-Hour Rule

PDPA requires notification to สำนักงาน สคส. within **72 hours** of becoming aware of a breach that is likely to result in risk to rights and freedoms.

For high-risk breaches (involving sensitive data, mass exposure), also **notify affected data subjects without undue delay**.

### 8.2 Response Workflow (Summary)

```
Detection → Containment → Assessment → Notification → Remediation → Review
```

**Detailed runbook in [[BREACH_RESPONSE_RUNBOOK]]**

### 8.3 Categorization

| Breach type | Examples | Notify สคส.? | Notify users? |
|-------------|----------|:------------:|:-------------:|
| Unauthorized access to single user account | Compromised password | ❌ (if contained) | ✅ (affected user only) |
| Mass exfiltration attempt (blocked) | DDoS, scanning | ❌ | ❌ |
| Mass exfiltration (successful) | DB breach, dump leaked | ✅ | ✅ |
| Insider access beyond authorization | อสม. accesses non-assigned | ✅ (if pattern) | ✅ (affected users) |
| Vendor breach (Neon/Vercel) | Provider incident | ✅ | ✅ (if affecting us) |
| Accidental disclosure | Email to wrong recipient | Case-by-case | ✅ (affected) |
| Physical theft (paper consent) | รพ.สต. burgled | Case-by-case | ✅ (affected) |

---

## 9. DPO (Data Protection Officer) Requirement

### 9.1 Assessment (ม.41)

DPO is required if:
1. Core activity = large-scale systematic monitoring, OR
2. Core activity = large-scale processing of sensitive data

**Our case:**
- Phase 1 MVP (< 100 users): DPO **not strictly required**, but recommended
- Phase 2+ (1K+ users with sensitive health data): DPO **required**

### 9.2 DPO Responsibilities

- Inform and advise on PDPA obligations
- Monitor compliance
- Conduct training and awareness
- Cooperate with PDPC (สคส.)
- Serve as contact point for data subjects
- Audit internal processes

### 9.3 Current Plan

- **Phase 1:** Founder (Pornthep) acts as informal DPO + external PDPA consultant for review
- **Phase 2:** Hire part-time DPO or contract with specialized firm
- **Phase 3+:** Full-time DPO role

### 9.4 DPO Contact

Must be publicly available:
- In Privacy Policy (section 15 of privacy-policy.md)
- In Terms of Service
- On website / support page

---

## 10. Records of Processing Activities (ROPA)

### 10.1 Requirement

Although PDPA ม.39 focuses on DPO, best practice is to maintain a ROPA listing all processing activities. Helps with:
- Audits
- Data subject requests (know what data we have)
- Breach assessment

### 10.2 ROPA Template

For each processing activity, record:

| Field | Example |
|-------|---------|
| Activity name | "Store BP readings for proxy-managed patients" |
| Purpose | "Healthcare monitoring by อสม./รพ.สต." |
| Legal basis | "Explicit consent (ม.26), scope=asm_collect" |
| Data categories | "BP values, measured_at, location, patient_id" |
| Data subjects | "Proxy-managed patients (ชาวบ้าน)" |
| Recipients | "อสม., รพ.สต. admin (own org), doctor (if consent)" |
| Cross-border transfer | "Yes — Neon (US), safeguards: encrypted, DPA" |
| Retention | "10 years from last reading or until consent withdrawn" |
| Security measures | "Encrypted (Fernet), RBAC, audit logged" |

Maintain in spreadsheet or dedicated tool (e.g., Airtable, Notion, or internal DB).

---

## 11. Children's Data (ม.20)

### 11.1 MVP Scope

- **Target users:** 35+ (per pilot scope)
- **Out-of-scope for MVP:** users under 20

### 11.2 Phase 2+ Consideration

If extending to pediatrics:
- Parental consent required (ม.20)
- Enhanced safeguards
- Separate consent form for parents
- Age verification process
- Additional retention rules

---

## 12. Special Categories of Data

### 12.1 Health Data (Primary)

- BP readings, โรคประจำตัว, ประวัติการรักษา
- Treated as sensitive (ม.26)
- Explicit consent required
- Enhanced security

### 12.2 Biometric Data

- **Digital signature** (ลายเซ็นนิ้ว/ปากกาบนจอ) — may be classified as biometric
- Treated as sensitive
- Explicit consent at collection
- Encrypted storage (Fernet)
- Never shared externally

### 12.3 Location Data

- GPS coordinates (at consent capture, optional at BP reading)
- Not strictly sensitive under PDPA, but treated with care
- Minimum precision (only for consent verification)
- Not used for tracking movement

### 12.4 National ID

- Optional collection
- Hashed for search (SHA-256)
- Encrypted for display (Fernet)
- Used only for verification in regulated context

### 12.5 Doctor License Number

- Professional data
- Shared with TMC (แพทยสภา) for verification — legitimate interest
- Displayed publicly in doctor profile

---

## 13. Retention Policy Summary

**Full details: [[DATA_RETENTION_POLICY]]**

Key principles:
- **Purpose limitation** — retain only as long as needed for stated purpose
- **Legal obligations** — medical records typically 10 years
- **User-driven deletion** — respect erasure requests within 30 days
- **Audit trail preservation** — 2+5 years (security forensics)
- **Auto-deletion** — implemented as scheduled jobs, logged in audit

---

## 14. Vendor Management

### 14.1 Due Diligence Process

Before using a new data processor:
1. Review their privacy policy
2. Request DPA (Data Processing Agreement)
3. Check certifications (SOC 2, ISO 27001)
4. Review sub-processor list
5. Understand data flows
6. Document in ROPA
7. Get legal review

### 14.2 Current Vendors Status

| Vendor | DPA signed? | Certifications | Review date |
|--------|:-----------:|----------------|-------------|
| Neon | ⬜ TBD | SOC 2 Type II | - |
| Vercel | ⬜ TBD | SOC 2 Type II, ISO 27001 | - |
| Upstash | ⬜ TBD | SOC 2 Type II | - |
| Google (Gemini) | ⬜ TBD | ISO 27001, SOC 2 | - |
| Telegram | ⬜ N/A (public ToS only) | - | - |
| SlipOK | ⬜ TBD | - | - |

**Action item:** Obtain and sign DPAs with all US vendors before processing real user data in Phase 1+.

### 14.3 Vendor Breach Response

If a vendor notifies us of their breach:
- Assess impact on our users within 24 hours
- If our users affected: trigger our own breach response (72-hour clock starts)
- Document timeline and vendor communication

---

## 15. Compliance Checklist — Phase 1 MVP

### 15.1 Before Launching Pilot

**Documentation:**
- [ ] Privacy Policy v2 published ([[LEGACY_DOCS_MIGRATION]])
- [ ] Terms of Service v2 published
- [ ] Organization ToS (new) published ([[ORG_TERMS_OF_SERVICE]])
- [ ] Consent form v2 (paper + digital) designed ([[CONSENT_FORMS]])
- [ ] Data Retention Policy documented and implemented ([[DATA_RETENTION_POLICY]])
- [ ] Breach Response Runbook documented and practiced ([[BREACH_RESPONSE_RUNBOOK]])
- [ ] ROPA created for all processing activities
- [ ] DPO designated (interim: founder)

**Technical:**
- [ ] All PII encrypted at rest (Fernet)
- [ ] HTTPS enforced (HSTS)
- [ ] RBAC implemented with tenant isolation
- [ ] Audit log on all cross-user access
- [ ] Consent scope enforcement in middleware
- [ ] Data subject request endpoints (view, export, delete)
- [ ] Consent withdrawal triggers downstream effects
- [ ] Auto-deletion jobs for expired data
- [ ] Image handling: no long-term OCR image storage

**Organizational:**
- [ ] DPAs signed with Neon, Vercel, Upstash, Google
- [ ] Admin training materials (PDPA basics for รพ.สต.)
- [ ] อสม. training materials (consent collection, data handling)
- [ ] Internal incident response drill completed
- [ ] Legal review by PDPA consultant completed
- [ ] Translation review completed

**User-Facing:**
- [ ] First-login consent modal
- [ ] Privacy Policy link in footer
- [ ] Data export functionality
- [ ] Account deletion self-service
- [ ] Consent withdrawal self-service

### 15.2 Monthly Ongoing

- [ ] Review audit logs for unusual patterns
- [ ] Verify auto-deletion jobs ran successfully
- [ ] Check pending data subject requests (resolve within 30 days)
- [ ] Update ROPA if new processing activities
- [ ] Review new vendor additions

### 15.3 Annually

- [ ] Full compliance review (internal or external)
- [ ] DPA renewals
- [ ] Security assessment / pentest
- [ ] Policy version review and updates
- [ ] DPO assessment (still not required? or now required?)
- [ ] Breach response drill

---

## 16. Training Requirements

### 16.1 For Admins (รพ.สต.)

Topics:
- PDPA basics (sensitive data, explicit consent)
- Organization ToS obligations
- Data subject rights handling
- Physical security (locked cabinet for consent paper)
- Incident reporting
- Access control best practices

Format: 30-min video + quiz + annual refresher

### 16.2 For อสม.

Topics:
- Collecting consent (how to explain to ชาวบ้าน)
- Recording accuracy
- Data security on personal device
- Not sharing credentials
- Recognizing social engineering
- What to do if device lost/stolen

Format: In-person briefing + short video + quick reference card

### 16.3 For Internal Team (เรา)

Topics:
- PDPA full scope
- Incident response
- Data handling standards
- Code review for privacy
- Vendor management

Format: Onboarding + quarterly updates

---

## 17. Complaint Handling

### 17.1 User Complaints

Channels:
- Email: privacy@yourdomain.com
- In-app: Settings → Report issue
- Through รพ.สต. (for proxy-managed users)

Process:
1. Acknowledge within 3 working days
2. Investigate
3. Respond within 30 days
4. If dissatisfied: user has right to file with สำนักงาน สคส.

### 17.2 Escalation to PDPC

สำนักงานคณะกรรมการคุ้มครองข้อมูลส่วนบุคคล (สคส.):
- Website: https://www.pdpc.or.th
- Tel: 02-141-6993
- Email: saraban@pdpc.or.th

We must cooperate fully with PDPC investigations.

---

## 18. Enforcement & Penalties Reference

For awareness only (not exhaustive):

| Violation | Penalty |
|-----------|---------|
| Process sensitive data without consent | Fine up to 5M THB + criminal penalties |
| Fail to notify breach within 72h | Fine up to 3M THB |
| Fail to appoint DPO when required | Fine up to 1M THB |
| Violate data subject rights | Fine up to 3M THB |
| Cross-border transfer without safeguards | Fine up to 5M THB |
| Repeated violations | Double fines + criminal liability |

**Takeaway:** PDPA enforcement is real. Full compliance is cheaper than penalties.

---

## 19. Open Questions / TBD

1. **External PDPA consultant** — hire whom? (Baker McKenzie, DLA Piper, Thai firm?)
2. **DPO** — when exactly to hire full-time?
3. **Insurance** — cyber liability insurance for breach costs?
4. **Specific retention overrides** — does healthcare licensing require any specific period?
5. **Children's data path** — if someone under 20 registers, how do we handle?
6. **Deceased person data** — retention and rights (Phase 2 consideration)
7. **Research data sharing** — detailed process for "research_anonymized" scope (Phase 2)

---

## 20. Document References

- [[MVP_PILOT_SCOPE]] — overall plan
- [[ORG_FOUNDATION]] — technical implementation (schemas, RBAC, audit log)
- [[CONSENT_FLOW_SPEC]] — consent workflow detailed
- [[CONSENT_FORMS]] — ready-to-use consent form text
- [[DATA_RETENTION_POLICY]] — retention rules per data type
- [[BREACH_RESPONSE_RUNBOOK]] — incident response detailed
- [[LEGACY_DOCS_MIGRATION]] — updating privacy-policy.md, terms-of-service.md
- [[ORG_TERMS_OF_SERVICE]] — ToS for รพ.สต./admin

---

**End of PDPA_COMPLIANCE.md**
