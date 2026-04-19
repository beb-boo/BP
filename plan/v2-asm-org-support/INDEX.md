---
title: "v2 ASM Org Support — Plan Index"
aliases:
  - "Index"
  - "MOC"
  - "Plan Home"
tags:
  - index
  - moc
  - v2-asm-org
order: 0
status: draft
version: 1.3
updated: 2026-04-19
summary: "Map of Content for all v2 ASM/รพ.สต. org support planning documents"
---
# v2 ASM Organization Support — Planning Index

> **Master index สำหรับทั้ง plan set.** เปิดใน Obsidian เพื่อดู graph view แสดงความเชื่อมโยงระหว่างเอกสาร
>
> **Version 2** ของ BP Monitor — ขยายจากระบบ personal ไปรองรับ อาสาสมัครสาธารณสุข (อสม.) และ โรงพยาบาลส่งเสริมสุขภาพตำบล (รพ.สต.)

---

## อ่านอะไรก่อน (Reading Order)

สำหรับคนที่เข้ามาครั้งแรก:

1. **[[MVP_PILOT_SCOPE]]** — อ่านก่อนเสมอ เพื่อเข้าใจ scope + goals + constraints
2. **[[PLAN_REVIEW_RESPONSE]]** — อ่านก่อน plan อื่น เพื่อเข้าใจ architectural decisions + why
3. **[[BACKUP_AND_MIGRATION_SPEC]]** — **สร้างก่อน v2 migration** — Neon branch backup tool ใน admin web
4. **[[SCALABILITY_PLAN]]** — รู้ว่าเราวางอะไรในระยะยาว เพื่อไม่ตัดสินใจผิดใน Phase 1
5. **[[ORG_FOUNDATION]]** — foundation ของทั้งหมด (DB schema, RBAC, self-measure policy, hybrid onboarding, role labels) — v1.2
6. **[[INFRASTRUCTURE_SETUP]]** — Tier 0 prerequisites ก่อนเริ่ม code (schema_migrations, feature flags, staging, backup drill)
7. **[[MIGRATION_STRATEGY]]** — วิธี apply migration บน prod อย่างปลอดภัย
8. **[[CONSENT_FLOW_SPEC]]** — PDPA workflow (สำคัญมาก ต้องอ่านก่อน code)
9. **[[ADMIN_WEB_SPEC]]** — web dashboard สำหรับ รพ.สต. admin
10. **[[CAREGIVER_PWA_SPEC]]** — PWA สำหรับ caregiver (อสม./พยาบาล) ภาคสนาม + batch OCR
11. **[[LEGACY_DOCS_MIGRATION]]** — แผน patch เอกสารเดิม (privacy policy, ToS)

Group C (PDPA/Legal):
12. **[[PDPA_COMPLIANCE]]** — master compliance reference (joint controller, rights, cross-border)
13. **[[DATA_RETENTION_POLICY]]** — retention rules per data type + auto-deletion jobs
14. **[[BREACH_RESPONSE_RUNBOOK]]** — 72h notification playbook, templates, drills
15. **[[CONSENT_FORMS]]** — ready-to-use Thai forms (paper + digital)
16. **[[ORG_TERMS_OF_SERVICE]]** — ToS สำหรับ admin รพ.สต. (new, v1)

---

## Document Map

```
                 [MVP_PILOT_SCOPE]
                        |
        +-------+-------+-------+-------+
        |       |               |       |
   [ORG_FOUNDATION]        [SCALABILITY_PLAN]
        |                       |
   +----+----+                  |
   |         |                  |
[ADMIN_WEB] [CAREGIVER_PWA]    |
   |         |                  |
   +---------+                  |
        |                       |
   [CONSENT_FLOW]                |
        |                       |
   +----+-----+                 |
   |          |                 |
[PDPA_COMP] [CONSENT_FORMS]    |
   |          |                 |
[DATA_RETENTION]  [BREACH_RUNBOOK]
                       
   [LEGACY_DOCS_MIGRATION] → patches existing docs/
```

---

## Status Dashboard

| # | Doc | Status | Size | Purpose |
|---|-----|--------|------|---------|
| 0 | [[INDEX]] | ✅ Draft v1.2 | this | MOC — this document |
| 0.5 | [[PLAN_REVIEW_RESPONSE]] | ✅ Draft v1.0 | ~15KB | **Decision log** — source of truth for architectural decisions |
| 0.7 | [[BACKUP_AND_MIGRATION_SPEC]] | ✅ **Draft v1.0** | ~17KB | **Prerequisite: Neon branch backup** — build FIRST before v2 migration |
| 0.75 | [[GENERALIZE_ORG_PLAN]] | ✅ **Draft v1.0** | ~18KB | **Rename rpsst/asm → generic org/caregiver** + hybrid policy + gap close |
| 0.8 | [[INFRASTRUCTURE_SETUP]] | ✅ Draft v1.0 | ~15KB | **Tier 0 prerequisites** — schema_migrations, flags, staging, backup |
| 0.9 | [[MIGRATION_STRATEGY]] | ✅ Draft v1.0 | ~15KB | **How to migrate safely** — staged procedure, FK graph, rollback |
| 1 | [[MVP_PILOT_SCOPE]] | ✅ Draft v1 | 24KB | Scope, personas, metrics, acceptance criteria |
| 2 | [[ORG_FOUNDATION]] | ✅ **Draft v1.2** | ~60KB | DB schema, RBAC, migration, audit log, self-measure policy (§8.3), hybrid onboarding (§8.4), role labels (§6.5) |
| 3 | [[ADMIN_WEB_SPEC]] | ✅ **Draft v1.2** | ~36KB | Admin web dashboard spec — account_type radio, link/unlink actions, source icons |
| 4 | [[CAREGIVER_PWA_SPEC]] | ✅ **Draft v1.2** | ~55KB | Caregiver PWA + batch OCR spec — 🏠/👤 source icons, create-hybrid endpoint |
| 5 | [[CONSENT_FLOW_SPEC]] | ✅ **Draft v1.2** | ~32KB | Consent workflow end-to-end — self-measure withdrawal effect (§5.3.3), templated consent text (§4.3) |
| 6 | [[SCALABILITY_PLAN]] | ✅ Draft v1 | 27KB | Scale to 1M, Vercel migration, costs |
| 7 | [[LEGACY_DOCS_MIGRATION]] | ✅ **Draft v1.1** | 28KB | Patch plan for existing 3 docs in docs/ (aligned w/ decisions) |
| 8 | [[PDPA_COMPLIANCE]] | ✅ Draft v1 | 27KB | Master compliance reference |
| 9 | [[DATA_RETENTION_POLICY]] | ✅ Draft v1 | 19KB | Retention rules per data type |
| 10 | [[BREACH_RESPONSE_RUNBOOK]] | ✅ Draft v1 | 29KB | Incident playbook, 72h notification, templates |
| 11 | [[CONSENT_FORMS]] | ✅ Draft v1.1 | 40KB | Ready-to-use paper + digital Thai forms — org-type templating hooks (§10) |
| 12 | [[ORG_TERMS_OF_SERVICE]] | ✅ Draft v1 | 38KB | ToS for รพ.สต./admin (new, v1) |

**Total: 18 files, ~520 KB**

Legend: ✅ Complete · 🚧 In progress · 📝 Planned · 🔴 Blocked

---

## Key Decisions (Locked v1)

1. **Architecture: PWA + Telegram bot (no LINE in MVP)** — see [[MVP_PILOT_SCOPE]] section 10.1
2. **Legal: No MOU/DPA** — in-app ToS + Privacy + Consent acceptance
3. **Storage: PostgreSQL BYTEA with abstraction** — swap-ready for Phase 2 migration
4. **Org Identity: UUID external_id + optional code/code_system** — supports HCODE + commercial
5. **Data Minimization: No long-term image storage** — only OCR batch review queue (7 days max)
6. **Partition-ready audit_logs from day 1** — don't wait for scale
7. **Consent: Paper + digital signature hybrid** — physical paper at รพ.สต., no scan

---

## Open Decisions (Still TBD)

1. Cloud vendor ในไทย (NT Cloud vs INET vs AWS Bangkok) — see [[SCALABILITY_PLAN]] section 5.1
2. OCR strategy — keep Gemini vs self-host at scale
3. Legal review firm (PDPA consultant)
4. Pilot partner contract terms (informal OK for MVP)
5. Launch date
6. Budget for training, printer, เครื่องวัด

---

## Scaling Context

อสม. ทั่วประเทศ: ~1.05M คน | active ใน Smart อสม. เม.ย. 2026: **354,513 คน** (33%)

- **Pilot → Amphoe (3-6 mo):** 2 → 10 อสม.
- **Province (1-2 yr):** 500-1,000 อสม.
- **Regional (3-5 yr):** 50K-100K อสม.
- **National (5-10 yr, optimistic):** 500K-1M อสม.

Current architecture ceiling: **~50K อสม.** — see [[SCALABILITY_PLAN]] for migration roadmap

---

## Related Existing Plans (in parent `plan/` dir)

- `../TELEGRAM_MINI_APP_PLAN.md` — existing plan, not impacted by v2
- `../MEMBERSHIP_ADMIN_AND_DOCTOR_HARDENING_PLAN.md` — existing, may inform Phase 2
- `../PREMIUM_PRODUCTION_READINESS_PLAN.md` — existing, complementary

---

## Related Existing Docs (in `docs/`)

Legacy docs that need updating per [[LEGACY_DOCS_MIGRATION]]:
- `docs/privacy-policy.md` (v1 exists, needs v2 for org mode)
- `docs/terms-of-service.md` (v1 exists, needs v2 + new Org ToS)
- `docs/consent-and-implementation-guide.md` (v1 exists, needs v2 for proxy flow)

---

## Useful Obsidian Features

- **Graph view:** See relationships between all docs (⌘G in Obsidian)
- **Backlinks panel:** Every doc shows who references it
- **Tag search:** Search `tag:#v2-asm-org` to find all docs in this set
- **Aliases:** Each doc has aliases for natural linking (e.g., `[[Scope]]` = `[[MVP_PILOT_SCOPE]]`)

---

**End of INDEX.md** — Last updated 2026-04-19 (v1.3: GENERALIZE_ORG_PLAN applied — rename rpsst/asm → org/caregiver across all docs, v1.2 bumps on ORG_FOUNDATION/ADMIN_WEB_SPEC/CAREGIVER_PWA_SPEC/CONSENT_FLOW_SPEC, v1.1 on CONSENT_FORMS; v1.2: added BACKUP_AND_MIGRATION_SPEC สำหรับ Neon branch backup tool ใน admin web; v1.1: added PLAN_REVIEW_RESPONSE, INFRASTRUCTURE_SETUP, MIGRATION_STRATEGY)
