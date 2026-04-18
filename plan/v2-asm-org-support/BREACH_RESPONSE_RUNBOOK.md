---
title: "Data Breach Response Runbook"
aliases:
  - "Breach Runbook"
  - "Incident Response"
  - "Breach Response"
tags:
  - pdpa
  - security
  - incident-response
  - runbook
  - v2-asm-org
order: 10
status: draft
version: 1.0
updated: 2026-04-18
summary: "Step-by-step incident response: detection → containment → 72h notification to สคส. → user communication → remediation. Includes templates."
related:
  - "[[PDPA_COMPLIANCE]]"
  - "[[DATA_RETENTION_POLICY]]"
  - "[[ORG_FOUNDATION]]"
---
# Data Breach Response Runbook

> **Status:** Draft v1
> **Last updated:** 2026-04-18
> **Owner:** Pornthep (interim DPO)
> **Activation:** เมื่อมีเหตุสงสัยว่าข้อมูลรั่ว ให้เปิดเอกสารนี้และทำตามขั้นตอนทันที

---

## 0. TL;DR — Emergency Actions (First 10 Minutes)

ถ้าสงสัยว่าเกิด breach **ณ ตอนนี้**:

1. **หยุดขยาย damage** — disable affected account/service (แต่ preserve evidence)
2. **บันทึกเวลา** — noted breach detection time (สำคัญสำหรับ 72h clock)
3. **เรียก incident team** — Pornthep + (ใครในทีมก็ตามที่พร้อม)
4. **เปิดเอกสารนี้** — ทำตามขั้นตอนถัดไปอย่างเป็นระบบ
5. **ห้ามประกาศต่อสาธารณะ** — ก่อน legal assessment

**Key contacts:**
- DPO / Incident commander: Pornthep — [phone]
- Cloud ops (Vercel/Neon): login + credentials in 1Password
- Legal counsel: [TBD]
- PDPC hotline: 02-141-6993

---

## 1. Overview

### 1.1 What is a "Data Breach"

ตามคำนิยาม PDPA ม.37 — เหตุการณ์ที่ทำให้:
- ข้อมูลส่วนบุคคล **รั่วไหล** (disclosure to unauthorized)
- **ถูกทำลาย** (loss or destruction)
- **ถูกแก้ไขโดยไม่ได้รับอนุญาต** (unauthorized alteration)
- **ถูกเข้าถึงหรือใช้งานโดยไม่ได้รับอนุญาต** (unauthorized access/use)

ไม่ว่าจะเป็นผลจาก:
- การโจมตีจากภายนอก (cyber attack)
- ความผิดพลาดภายใน (misconfiguration, email mistake)
- การกระทำของผู้ใช้ในระบบ (insider threat, หรือ compromised account)
- การสูญหายทางกายภาพ (laptop stolen, paper consent หาย)

### 1.2 72-Hour Rule (ม.37 วรรคสาม)

- เรา (Data Controller) ต้องแจ้ง **สำนักงาน สคส.** ภายใน **72 ชั่วโมง** หลังรู้เรื่อง
- ถ้าเสี่ยงสูงต่อสิทธิและเสรีภาพของบุคคล ต้องแจ้ง **data subjects** โดยไม่ชักช้า
- ถ้าไม่สามารถแจ้งภายใน 72 ชม. ต้องมีเหตุผลที่ชอบธรรมและบันทึกไว้

### 1.3 Clock Starts When?

"การรู้เรื่อง" (becoming aware) = เมื่อเราได้ **reasonable certainty** ว่ามี breach เกิดขึ้น

**ไม่ใช่:**
- ไม่ใช่เมื่อ alert ระบบดัง (อาจเป็น false positive)
- ไม่ใช่เมื่อเริ่ม investigation

**ใช่:**
- เมื่อเราตรวจสอบแล้วมั่นใจว่ามีเหตุการณ์เกิดขึ้นจริง
- เมื่อ vendor notification ระบุชัดว่ากระทบเรา

**Document this precisely** — เพราะเป็นหลักฐานในการ justify timing

---

## 2. Incident Classification

### 2.1 Severity Levels

| Level | Definition | Example | Response time |
|-------|------------|---------|---------------|
| **P0 (Critical)** | Active breach affecting 100+ users OR sensitive health data mass exposure | DB dump leaked online | Immediate, 24/7 |
| **P1 (High)** | Confirmed breach affecting <100 users OR limited sensitive data exposure | Insider access audit reveals pattern | Within 2 hours |
| **P2 (Medium)** | Potential breach (under investigation) OR limited non-sensitive exposure | Email to wrong recipient with general data | Within 8 hours |
| **P3 (Low)** | Near-miss or attempted breach (contained) OR policy violation without actual data exposure | Blocked SQL injection attempt | Within 1 business day |

### 2.2 Notification Decision Matrix

| Scenario | Notify สคส.? | Notify users? | Notify within |
|----------|:------------:|:-------------:|:--------------|
| Mass exfiltration successful | ✅ | ✅ (all affected) | 72h / ASAP |
| Mass exfiltration attempted (blocked) | ❌ (unless persistent) | ❌ | - |
| Single user account compromised | ❌ (if contained) | ✅ (affected user) | ASAP |
| Multiple accounts compromised (< 100) | Case-by-case | ✅ (affected users) | 72h |
| Insider accessing beyond authorization | ✅ | ✅ (affected users) | 72h |
| Vendor (Neon/Vercel) breach affecting us | ✅ (if confirmed) | ✅ | 72h |
| Paper consent stolen from รพ.สต. | ✅ (if significant) | ✅ (affected) | ASAP |
| Lost laptop with access credentials | ✅ (if sensitive data on it) | ✅ (if applicable) | 72h |
| Accidental email disclosure | Case-by-case | ✅ (affected) | ASAP |
| Staff posts screenshot with PII online | ✅ | ✅ (affected) | ASAP |

### 2.3 Risk Assessment Criteria

When deciding to notify, consider:
- **Volume:** How many data subjects affected?
- **Sensitivity:** Is sensitive (health) data involved?
- **Identifiability:** Can individuals be re-identified?
- **Likelihood of harm:** Could this lead to discrimination, financial loss, identity theft?
- **Containment:** Is the breach ongoing or stopped?
- **Attacker intent:** Random scan vs. targeted attack?
- **Data duration of exposure:** Minutes vs. days vs. months?

**Default stance: When in doubt, notify.** Over-reporting is safer than under-reporting.

---

## 3. Response Phases

### 3.1 Phase 1: Detection & Initial Response (0-1 hour)

**Goal:** Confirm breach, contain further damage, preserve evidence

**Steps:**

1. **Acknowledge detection**
   - Who detected? How? When (exact timestamp)?
   - Log to incident tracker

2. **Declare incident**
   - Open incident channel (Slack, Signal, or Google Meet)
   - Notify DPO/Incident Commander
   - Assign roles:
     - **Incident Commander (IC):** coordinates response
     - **Technical Lead:** investigates + contains
     - **Communications Lead:** drafts notifications
     - **Scribe:** timestamp everything

3. **Preserve evidence** (BEFORE containing)
   - Take DB snapshot
   - Copy relevant logs (audit, application, system)
   - Screenshot anything visible
   - Don't modify affected systems yet

4. **Initial containment**
   - If compromised account: disable (don't delete — preserve for forensics)
   - If compromised API key: rotate
   - If compromised service: isolate (limit access, don't shut down yet)
   - If ongoing attack: block at WAF/firewall level

5. **Initial assessment**
   - What data is at risk?
   - How many users?
   - Is breach still active?
   - P0/P1/P2/P3?

6. **Create initial incident report**
   - Use template in section 7.1
   - Start the 72h clock officially

### 3.2 Phase 2: Investigation (1-12 hours)

**Goal:** Understand full scope, identify root cause, finalize containment

**Steps:**

1. **Detailed forensics**
   - Timeline reconstruction (when started, when escalated)
   - Entry point (how did attacker get in?)
   - Lateral movement (what else was accessed?)
   - Data exfiltrated (what left our system?)
   - Persistence mechanisms (did they leave backdoors?)

2. **Review audit logs**
   ```sql
   -- Suspicious access patterns
   SELECT actor_user_id, action, target_user_id, created_at, from_ip
   FROM audit_logs
   WHERE created_at BETWEEN :breach_start AND :breach_end
     AND (success = false OR target_user_id != actor_user_id)
   ORDER BY created_at;
   ```

3. **Check data exfiltration**
   - Database query logs
   - Bulk export events in audit log
   - API rate logs (unusual spikes)
   - Vendor logs (Vercel, Neon console)

4. **Identify affected data subjects**
   - Generate list of affected user IDs
   - Categorize by data type exposed
   - Estimate harm potential

5. **Full containment**
   - Patch vulnerability
   - Force logout all users (if needed)
   - Rotate all secrets/keys
   - Update WAF rules
   - Re-enable services with additional monitoring

6. **Update incident report**
   - Root cause (preliminary)
   - Confirmed scope
   - Containment status

### 3.3 Phase 3: Notification (12-72 hours)

**Goal:** Comply with PDPA notification requirements

**Steps:**

1. **Legal review** (mandatory before external comms)
   - PDPA consultant reviews
   - Wording approved
   - Timing confirmed

2. **Notify PDPC (สคส.)** within 72h of detection
   - Use template in section 7.2
   - Send via: email, online form (https://www.pdpc.or.th), or mail
   - Keep proof of submission
   - Follow up if no acknowledgment within 48h

3. **Notify affected data subjects** (if required)
   - Individual notification preferred (email, SMS, in-app)
   - For org-mode users: notify รพ.สต. admin, they notify ชาวบ้าน
   - Use template in section 7.3
   - If can't reach individually: public notice (website, app banner)

4. **Notify joint controllers** (รพ.สต.)
   - Part of joint controller agreement
   - Within 24h of confirming breach
   - Use template in section 7.4

5. **Notify vendors** (if their system involved)
   - Neon / Vercel / Google / etc.
   - Request their breach report

6. **Notify legal counsel**
   - For significant incidents
   - For potential litigation preparation

7. **Prepare media response** (if likely to become public)
   - Don't proactively announce to media
   - Have holding statement ready
   - Route media inquiries to designated spokesperson

### 3.4 Phase 4: Remediation (3-30 days)

**Goal:** Fix root cause, strengthen defenses

**Steps:**

1. **Permanent fix**
   - Patch vulnerability
   - Deploy fix to all environments
   - Verify fix in staging before prod
   - Code review for similar patterns

2. **Enhance detection**
   - Add alerts for similar patterns
   - Update anomaly detection rules
   - Add logging where missing

3. **User support**
   - Dedicated channel for affected users' questions
   - Offer:
     - Password reset assistance
     - Free credit monitoring (if financial data exposed) [Phase 2+]
     - Account recovery
     - Data export (if they want to leave)

4. **Internal review**
   - Why did this happen?
   - What processes failed?
   - What controls were missing?

5. **Update runbooks/docs**
   - Add learnings to this document
   - Update playbooks

### 3.5 Phase 5: Post-Incident Review (30-60 days)

**Goal:** Learn from incident, prevent recurrence

**Steps:**

1. **Post-mortem meeting**
   - Blameless culture — focus on systems, not people
   - Attendees: IC, Tech Lead, Comms, DPO, legal
   - Review timeline, decisions, outcomes

2. **Write post-mortem document**
   - Template in section 7.5
   - Publish internally (and externally if appropriate)

3. **Action items**
   - Each item assigned to owner with deadline
   - Track to completion

4. **Final PDPC report** (if required)
   - Some breaches need follow-up report
   - Usually within 30-60 days

5. **Data subject follow-up**
   - "We resolved the issue" communication
   - Summary of remediation

6. **Board/stakeholder briefing**
   - For significant incidents
   - Recommendations for investment

---

## 4. Roles and Responsibilities

### 4.1 Incident Commander (IC)

- Overall coordination
- Decision authority
- External communication approval
- Usually: DPO or senior technical lead

### 4.2 Technical Lead

- Forensics and investigation
- Containment decisions
- Remediation execution
- Usually: CTO or lead engineer

### 4.3 Communications Lead

- Draft all notifications
- Coordinate with legal
- Manage user support channel
- Usually: Product or customer support lead

### 4.4 DPO (Data Protection Officer)

- PDPA compliance assurance
- Notification to PDPC
- Coordination with legal counsel
- Record-keeping

### 4.5 Scribe

- Document everything as it happens
- Timestamps for every decision
- Evidence chain of custody
- Often: any available team member

### 4.6 Small Team Note

For MVP/early stage: one person may wear multiple hats. That's OK. But ensure:
- At least 2 people aware of incident (for continuity)
- All roles tracked even if same person
- External help (legal, PDPA consultant) on call

---

## 5. Common Scenarios & Playbooks

### 5.1 Scenario: Compromised User Account

**Signs:**
- User reports unauthorized access
- Unusual login location/device
- Rapid bulk actions (mass export, rapid API calls)

**Immediate actions:**
1. Force logout all sessions for user
2. Suspend account (can't login)
3. Investigate audit log for:
   - First unauthorized access time
   - Actions taken by attacker
   - Data accessed/modified/exported
4. Contact user via verified channel (not account email/phone — could be compromised)
5. Reset credentials (user creates new ones)
6. Enable 2FA for account
7. Log incident, determine if notification required

**Notification:** Usually not PDPC (limited scope), but notify affected user.

### 5.2 Scenario: Suspected Mass Data Exfiltration

**Signs:**
- Spike in API rate/DB queries
- Bulk export events in audit log
- Unusual traffic patterns
- Leaked data discovered online

**Immediate actions:**
1. **ENGAGE INCIDENT TEAM IMMEDIATELY (P0)**
2. Block source IPs at WAF
3. Rotate all API keys, database credentials
4. Force logout all users
5. Preserve all logs (snapshot DB, copy to separate system)
6. Scope determination:
   - How much data?
   - What types?
   - Still ongoing?
7. Engage external forensics (if available)
8. Prepare PDPC notification (72h clock)
9. Draft user notification
10. Legal counsel engagement

**Notification:** PDPC + all affected users, within 72h.

### 5.3 Scenario: Vendor (Neon/Vercel) Breach

**Signs:**
- Vendor notification received
- Public disclosure by vendor

**Immediate actions:**
1. Review vendor's advisory — does it affect us?
2. Check our data exposure:
   - What data on their platform?
   - What's the attack scope?
3. Follow vendor's remediation guidance
4. Rotate credentials we shared with vendor (DB creds if compromised)
5. Independent verification of our systems
6. Determine if our users affected
7. If yes: start our own PDPC 72h clock

**Notification:** May be required even though breach was at vendor. We're responsible for our users.

### 5.4 Scenario: Accidental Data Disclosure

**Examples:**
- Staff emails CSV with user data to wrong recipient
- Admin shares screen with PII visible on call recording
- URL with data in query string shared publicly

**Immediate actions:**
1. Contact recipient — request deletion
2. Document what was disclosed (who, what, when)
3. Assess if recipient can/will delete (get written confirmation)
4. Notify affected users
5. If recipient is cooperative and data never used: lower severity
6. Review training/processes to prevent recurrence

**Notification:** Usually notify affected users. PDPC: depends on scope.

### 5.5 Scenario: Lost/Stolen Physical Device

**Examples:**
- อสม.'s phone with PWA logged in
- Laptop with backup files
- Paper consent from รพ.สต.

**Immediate actions:**
1. Force logout user from all sessions (remote kill)
2. Change passwords
3. Determine what was on device:
   - Access credentials?
   - Local copies of data?
4. If paper consent: notify affected ชาวบ้าน
5. Police report (if stolen)

**Notification:** Depends on scope. Paper consent theft of many users = notify PDPC.

### 5.6 Scenario: Insider Threat (rogue อสม. or admin)

**Signs:**
- Audit log shows access to non-assigned patients
- Data exports without business reason
- After-hours unusual activity

**Immediate actions:**
1. **Suspend insider's account (don't alert them yet)**
2. Preserve evidence (logs, access records)
3. Full audit of their access history
4. Determine intent (investigation, HR process)
5. If malicious: treat as criminal matter, involve police
6. Legal review
7. Notify affected data subjects

**Notification:** Usually notify PDPC + affected users.

---

## 6. Evidence Preservation

### 6.1 What to Preserve

- Application logs (all levels)
- Audit logs (critical)
- Database snapshots (pre-containment state)
- System logs (server, firewall)
- Network logs (if available)
- Email/chat communications about incident
- Screenshots
- Third-party vendor responses
- User reports/reports received

### 6.2 Chain of Custody

- Label each piece of evidence with:
  - Date/time obtained
  - Collected by (person)
  - Description
  - Hash (SHA-256 for files)
- Store in access-restricted location
- Document every person who touches evidence
- Don't modify original files

### 6.3 Retention of Incident Records

- **Indefinite retention** for security incident documentation
- Legal hold applies
- May be subpoenaed in future

---

## 7. Notification Templates

### 7.1 Internal Incident Report Template

```markdown
# Incident Report #INC-YYYY-NNNN

**Date detected:** YYYY-MM-DD HH:MM TZ
**Reported by:** [Name]
**Incident Commander:** [Name]
**Severity:** P0 / P1 / P2 / P3

## Summary
[1-2 sentence description]

## Timeline
- HH:MM — Detection
- HH:MM — IC notified
- HH:MM — Incident team assembled
- HH:MM — Initial containment
- HH:MM — Root cause identified
- HH:MM — Full containment
- [continue...]

## Scope
- Affected users: [count / list]
- Data types exposed: [list]
- Data volume: [estimate]
- Geographic scope: [Thailand / global]
- Duration of exposure: [minutes / hours / days]

## Root Cause
[Technical description]

## Response Actions
- [Action 1 — who, when]
- [Action 2]
- [...]

## PDPC Notification Required?
- [ ] Yes — filed on YYYY-MM-DD (within 72h)
- [ ] No — rationale: [...]

## User Notification Required?
- [ ] Yes — method: email / in-app / SMS / public notice
- [ ] No — rationale: [...]

## Containment Status
- [ ] Fully contained
- [ ] Partially contained
- [ ] Ongoing

## Current Risk
- [ ] No ongoing risk
- [ ] Low ongoing risk
- [ ] Medium ongoing risk
- [ ] High ongoing risk

## Next Steps
[What's planned]

## Evidence Location
[File paths, URLs]
```

### 7.2 PDPC Notification Template

```
เรียน  สำนักงานคณะกรรมการคุ้มครองข้อมูลส่วนบุคคล (สคส.)
เรื่อง: การแจ้งเหตุการละเมิดข้อมูลส่วนบุคคล ตามมาตรา 37 แห่ง พ.ร.บ.คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562

ข้าพเจ้า [ชื่อ-สกุล] ในฐานะ [ตำแหน่ง/DPO] ของ [ชื่อผู้ควบคุมข้อมูล/บริษัท] 
(เลขนิติบุคคล/เลขบัตรประชาชน: ...........)
ที่อยู่: ........
อีเมล: ........

ขอแจ้งเหตุการละเมิดข้อมูลส่วนบุคคล ดังนี้:

1. ลักษณะของเหตุการละเมิด
   [อธิบายเหตุการณ์]

2. ประเภทและปริมาณข้อมูลที่ถูกละเมิด
   - ประเภทข้อมูล: [general PII / sensitive health / etc.]
   - จำนวนเจ้าของข้อมูล (โดยประมาณ): [...]

3. ประเภทและจำนวนเจ้าของข้อมูลที่ได้รับผลกระทบ
   [...]

4. วันเวลาที่เกิด
   - เริ่มเกิด: YYYY-MM-DD HH:MM
   - ตรวจพบ: YYYY-MM-DD HH:MM
   - ระยะเวลาที่ข้อมูลอยู่ในภาวะเสี่ยง: [...]

5. มาตรการที่ได้ดำเนินการแล้ว
   [containment actions]

6. มาตรการที่จะดำเนินการต่อ
   [remediation plan]

7. การแจ้งเจ้าของข้อมูล
   [ ] ได้แจ้งแล้ว เมื่อ YYYY-MM-DD ผ่าน [email / in-app / SMS / public notice]
   [ ] จะแจ้งภายใน [date]
   [ ] ไม่จำเป็นต้องแจ้ง เหตุผล: [...]

8. ผลการประเมินความเสี่ยงต่อเจ้าของข้อมูล
   [assessment]

9. ผู้ติดต่อประสานงาน
   ชื่อ: [...]
   ตำแหน่ง: DPO
   โทร: [...]
   อีเมล: [...]

ลายมือชื่อ: ........................
ตำแหน่ง: ........................
วันที่: ........................
```

### 7.3 User Notification Template (Thai)

```
เรื่อง: แจ้งเหตุการละเมิดข้อมูลส่วนบุคคลของท่าน

เรียน [ชื่อผู้ใช้],

บริษัท [ชื่อ] ("เรา") ขอแจ้งให้ท่านทราบว่า เมื่อวันที่ [date] เราได้ตรวจพบ
เหตุการณ์ที่อาจกระทบต่อข้อมูลส่วนบุคคลของท่าน ดังรายละเอียดต่อไปนี้

สิ่งที่เกิดขึ้น:
[brief, clear description — no technical jargon]

ข้อมูลของท่านที่อาจได้รับผลกระทบ:
- [list]

สิ่งที่เราได้ดำเนินการแล้ว:
- [action 1]
- [action 2]
- ได้แจ้งเหตุต่อสำนักงาน สคส. ตามกฎหมาย
- ...

สิ่งที่ท่านควรทำ:
- เปลี่ยนรหัสผ่านของท่าน [link]
- เปิดใช้ 2-factor authentication
- ติดตามกิจกรรมในบัญชี หากพบสิ่งผิดปกติโปรดแจ้งเราทันที

หากมีคำถาม:
- อีเมล: privacy@yourdomain.com
- โทร: [...]
- ในแอป: Settings → Contact Support

เราขออภัยอย่างสูงในความไม่สะดวกและผลกระทบที่เกิดขึ้น เราให้ความสำคัญกับ
ความปลอดภัยของข้อมูลท่านเป็นที่สุด และจะเพิ่มมาตรการป้องกัน ไม่ให้เกิดเหตุ
เช่นนี้อีกในอนาคต

ขอแสดงความนับถือ,
[ชื่อ DPO/CEO]
[ตำแหน่ง]
[Company]
```

### 7.4 Joint Controller (รพ.สต.) Notification Template

```
เรียน  ผู้บริหาร รพ.สต. [ชื่อ]

เรื่อง: แจ้งเหตุการละเมิดข้อมูลส่วนบุคคล (สำคัญ — โปรดดำเนินการด่วน)

ตามที่ รพ.สต. ของท่าน ได้ใช้บริการแพลตฟอร์ม BP Monitor ในฐานะผู้ควบคุมข้อมูลร่วม
เราขอแจ้งว่าเกิดเหตุการละเมิดข้อมูลส่วนบุคคล ดังนี้:

[incident description]

ข้อมูลที่อาจกระทบ:
- ชาวบ้านในความรับผิดชอบของ รพ.สต. ท่าน: [count]
- ประเภทข้อมูล: [list]

สิ่งที่ขอให้ท่านดำเนินการ:
1. ตรวจสอบภายในทีมของท่านว่ามีความผิดปกติเพิ่มเติมหรือไม่
2. เตรียมพร้อมสื่อสารกับชาวบ้านที่ได้รับผลกระทบ (เราจะส่ง template)
3. ยืนยันกับเราหลังดำเนินการเรียบร้อย

สิ่งที่เราได้ดำเนินการแล้ว:
[list]

เรากำลังดำเนินการแจ้งสำนักงาน สคส. ตามขั้นตอนกฎหมาย

ติดต่อเรา: [contact]

ขอขอบคุณในความร่วมมือ
```

### 7.5 Post-Mortem Template

```markdown
# Post-Mortem: Incident #INC-YYYY-NNNN

**Date:** YYYY-MM-DD
**Authors:** [Name, Name]
**Status:** Final / Draft

## TL;DR
[Brief summary for executives]

## Impact
- Duration: [X hours]
- Users affected: [count]
- Data affected: [type and volume]
- Financial impact: [if applicable]
- Reputational impact: [assessment]

## Timeline
[Detailed timeline with timestamps]

## Root Cause Analysis
### What happened
### Why it happened (5 Whys technique)
### How it was detected
### What prevented earlier detection

## Response Assessment
### What went well
### What went poorly
### What was lucky

## Action Items
| Action | Owner | Due | Status |
|--------|-------|-----|--------|
| [item 1] | [name] | [date] | Open/Done |
| [item 2] | | | |

## Lessons Learned
[What we know now that we didn't before]

## Updates to Runbook
[What's being added to this document]
```

---

## 8. Training & Drills

### 8.1 Incident Response Drill Cadence

- **Tabletop exercise:** Quarterly (walk through scenario, no system changes)
- **Full drill:** Bi-annually (simulate incident in staging)
- **Table-top + drill** for all new team members during onboarding

### 8.2 Drill Scenarios

Rotate through:
1. Compromised user account
2. Database breach (mass exfiltration)
3. Vendor breach notification
4. Insider threat
5. Physical theft (device/paper)
6. Ransomware / service disruption

---

## 9. Metrics & SLAs

### 9.1 Internal SLAs

| Metric | Target |
|--------|--------|
| Time to detect (TTD) | < 1 hour for P0/P1 |
| Time to acknowledge (TTA) | < 15 minutes for P0, 1 hour for P1 |
| Time to contain (TTC) | < 4 hours for P0, 24 hours for P1 |
| Time to PDPC notification | Within 72 hours (PDPA requirement) |
| Time to user notification | Within 72 hours for high risk |
| Time to post-mortem | Within 30 days |

### 9.2 Tracking

Incidents tracked in dedicated tool (even Google Sheet works for MVP):
- Incident ID
- Severity
- Detection time
- Resolution time
- Users affected
- Notification status
- Status (open/closed)

---

## 10. External Resources

### 10.1 Authorities

- **PDPC (สคส.)**
  - Website: https://www.pdpc.or.th
  - Hotline: 02-141-6993
  - Email: saraban@pdpc.or.th
  - Address: ศูนย์ราชการเฉลิมพระเกียรติ 80 พรรษา อาคาร B ชั้น 7, ถ.แจ้งวัฒนะ

- **Royal Thai Police (cybercrime division)**
  - Hotline: 1599
  - For criminal matters

- **CERT Thailand (ThaiCERT)**
  - https://www.thaicert.or.th
  - For technical assistance

### 10.2 Legal Counsel

[To be filled — PDPA specialist firm]

### 10.3 Forensics Specialists

[To be filled — cyber incident response firm]

### 10.4 Cyber Liability Insurance

[Consider Phase 2+ — insurance coverage for breach costs]

---

## 11. Contact Information

### 11.1 Internal

| Role | Name | Phone | Email |
|------|------|-------|-------|
| DPO / IC | Pornthep | [...] | [...] |
| [Backup IC] | - | - | - |
| [Tech Lead] | - | - | - |
| [Legal] | - | - | - |

**Update this section regularly.** Ensure contacts have 24/7 availability for P0/P1.

### 11.2 Escalation Path

For P0:
1. DPO (immediate)
2. Founder/CEO (immediate)
3. Legal counsel (within 1 hour)
4. PDPC (within 72 hours)

For P1:
1. DPO (within 1 hour)
2. Tech lead (within 1 hour)
3. Legal counsel (within 24 hours, if external notification needed)

---

## 12. Quick Reference Card

**When breach detected:**
- [ ] Stop extending damage (contain)
- [ ] Preserve evidence (snapshot before changing)
- [ ] Notify DPO/IC
- [ ] Open incident channel
- [ ] Start incident report (template 7.1)

**Within 24 hours:**
- [ ] Full scope assessment
- [ ] Root cause identification
- [ ] Draft PDPC notification
- [ ] Draft user notification
- [ ] Legal review

**Within 72 hours:**
- [ ] PDPC notification submitted
- [ ] User notifications sent
- [ ] Containment fully verified
- [ ] Remediation plan defined

**Within 30 days:**
- [ ] Root cause remediated
- [ ] Post-mortem document published
- [ ] Action items tracked

---

## 13. Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-18 | Pornthep | Initial draft |

**Review cadence:** Annually, or after any major incident

---

**End of BREACH_RESPONSE_RUNBOOK.md**
