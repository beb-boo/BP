---
title: "Scalability Plan & Infrastructure Migration"
aliases:
  - "Scale Plan"
  - "Infrastructure"
  - "Migration Plan"
tags:
  - technical
  - infrastructure
  - scalability
  - migration
  - vercel
  - v2-asm-org
order: 6
status: draft
version: 1.0
updated: 2026-04-18
summary: "Scalability roadmap from 50 users to 1M, infrastructure evolution, Vercel migration plan with data migration strategy, cost projections, decision triggers"
related:
  - "[[MVP_PILOT_SCOPE]]"
  - "[[ORG_FOUNDATION]]"
  - "[[ADMIN_WEB_SPEC]]"
  - "[[CAREGIVER_PWA_SPEC]]"
---
# Scalability Plan & Infrastructure Migration

> **Status:** Draft v1
> **Last updated:** 2026-04-18
> **Owner:** Pornthep
> **Related:** [[ORG_FOUNDATION]] (partition-ready schema), [[MVP_PILOT_SCOPE]]

---

## 1. Executive Summary

ระบบ BP Monitor มี scalability ceiling ที่ **~50K อสม.** ด้วย current Vercel + Neon + Upstash stack. เกินนั้นต้อง re-architect.

**Target realistic scenario (3-5 ปี):** 35K-100K อสม. active (10-30% penetration ของ 354K active ใน Smart อสม. เม.ย. 2026)

**Target optimistic (5-10 ปี):** 500K-1M อสม. (หาก top-down integration ผ่าน สบส. สำเร็จ)

**Action items:**
1. **ตอนนี้ (Phase 1 MVP)** — ทำ low-cost preventive design: partition-ready schema, stateless architecture, tenant isolation
2. **Phase 2 (1K-10K อสม.)** — migrate to cloud ในไทย (data residency), monitoring, rate limiting
3. **Phase 3 (10K-50K อสม.)** — DB partitioning, read replicas, CDN, queue-based async
4. **Phase 4 (50K-200K อสม.)** — ย้าย off Vercel → Kubernetes/ECS, Redis caching layer
5. **Phase 5 (200K-1M อสม.)** — DB sharding, on-prem OCR, event-driven architecture

---

## 2. Growth Scenarios

### 2.1 Reference Numbers (2026)
- **อสม. ทั่วประเทศ:** 1.04-1.09 ล้านคน
- **อสม. active ใน Smart อสม. (เม.ย. 2026):** 354,513 คน (~33%)
- **รพ.สต. ทั่วประเทศ:** ~9,800 แห่ง
- **ประชากรไทยทั่วไป:** ~66 ล้านคน

### 2.2 Scenario Modeling

| Scenario | อสม. | ชาวบ้าน | BP readings/เดือน | API rps peak |
|----------|------|---------|-------------------|--------------|
| **Pilot (ตอนนี้)** | 2 | 40 | 160 | < 1 |
| **Tambon pilot (3-6 เดือน)** | 5-10 | 100-200 | 800 | < 5 |
| **Amphoe expansion (6-12 เดือน)** | 50-100 | 1K-2K | 8K | 10-20 |
| **Province (1-2 ปี)** | 500-1K | 10K-20K | 80K | 50-100 |
| **Multi-province (2-3 ปี)** | 5K-10K | 100K-200K | 800K | 200-500 |
| **Regional scale (3-5 ปี)** | 50K-100K | 1M-2M | 8M | 1K-2K |
| **National (5-10 ปี, optimistic)** | 500K-1M | 10M-20M | 80M | 5K-10K |

### 2.3 Data Volume Projection

per-month growth rates:

| Scenario | New bp_readings | New audit_logs | Cumulative bp (1 yr) | Storage (bp only) |
|----------|----------------|----------------|----------------------|--------------------|
| Amphoe | 8K | ~80K | 96K | ~30MB |
| Province | 80K | ~800K | 960K | ~300MB |
| Multi-province | 800K | ~8M | 9.6M | ~3GB |
| Regional | 8M | ~80M | 96M | ~30GB |
| National | 80M | ~800M | 960M | ~300GB |

**Insight:** BP readings growth ไม่น่ากลัว. **Audit log** คือ killer — เพราะ log ทุก action. national scale = ~10B rows/year

---

## 3. Current Architecture Assessment

### 3.1 Stack ปัจจุบัน (MVP Pilot)

| Layer | Service | Region | Limitations |
|-------|---------|--------|-------------|
| Frontend | Vercel | US | Cold starts, function timeout |
| Backend API | Vercel Serverless | US | Same + connection limits |
| Database | Neon PostgreSQL | US | Single instance, compute auto-scale |
| Cache/OTP | Upstash Redis | US | 10K commands/day free, pay per request |
| Image OCR | Google Gemini | US | $0.001-0.005/call, rate limit |
| Bot | python-telegram-bot | Vercel | Webhook mode OK |
| File storage | PostgreSQL BYTEA | Neon | Bundled with DB |

### 3.2 Bottleneck Analysis (จากน้อยไปมาก)

#### Layer 1: Telegram Bot API — ceiling ~250K active users
- **Limit:** 30 msg/s/bot (global), 1 msg/s/chat
- 1M อสม. × 1 OTP/day avg = 12 msg/s avg, peak 100+ msg/s
- **Solution:** Shard to multiple bot accounts (เช่น `@BPMonitorASMBot_01` through `_10`)

#### Layer 2: Gemini OCR — scales with $$$
- Unlimited scale แต่ cost ก้าวกระโดด:
  - 10K อสม.: ~$1K/เดือน
  - 100K อสม.: ~$15K/เดือน
  - 1M อสม.: ~$100K+/เดือน (ต้อง negotiate enterprise tier)
- **Solution:** Self-hosted vision model (PaddleOCR + custom fine-tune) สำหรับ high-volume. Keep Gemini เฉพาะ hard cases

#### Layer 3: Vercel Serverless — breaks at ~20K-50K อสม.
- **Cold starts:** 500ms-3s — acceptable ตอนน้อย peak load, แย่ตอน 1,500+ rps
- **Function timeout:** 60s (Pro), 300s (Enterprise) — OCR + DB + encryption อาจใกล้ limit
- **Connection limits:** Serverless function opens DB connections บ่อยมาก, Neon pooler ช่วยได้แต่มี cap
- **Cost at scale:** 
  - 10K อสม.: ~$200-500/เดือน
  - 50K อสม.: ~$2-5K/เดือน
  - 100K อสม.: ~$10-20K/เดือน (unsustainable)

#### Layer 4: Neon PostgreSQL — breaks at ~100K-500K อสม.
- **Single instance write limit:** ~5-10K writes/s peak (มี connection/compute limit)
- **Query performance degrades** หลังจาก audit_logs โต > 100M rows without partitioning
- **Auto-scale compute:** ดีจนถึง limit ของ largest plan (~16 vCPUs, 64GB RAM)
- **Storage:** Neon scales storage separately — ok

#### Layer 5: Upstash Redis — breaks at ~100K อสม.
- **Command rate:** 1K req/s on hobby, 10K+ on Pro
- **Cost at scale:** similar to Neon compute

### 3.3 Summary Scale Ceiling

**Current architecture realistic ceiling: ~50K อสม. active** (with significant cost escalation)

---

## 4. Scaling Roadmap — Phased Migration

### Phase 1: MVP Pilot (0-50 อสม., 0-3 เดือน)

**Status:** Current

**Stack:** Vercel + Neon + Upstash + Gemini (all US)

**Actions (ทำทันที — ไม่ต้องรอ):**
- ✅ Partition-ready audit_log schema (ดูใน [[ORG_FOUNDATION]] และ section 6 ด้านล่าง)
- ✅ Tenant isolation (all queries scoped by `organization_id`)
- ✅ Stateless everything (no in-memory state)
- ✅ Data minimization (no image long-term storage)
- ⬜ Setup Sentry error tracking
- ⬜ Structured logging with `request_id` correlation
- ⬜ DB query performance logging (slow query log)
- ⬜ Basic uptime monitoring (Vercel analytics + external Pingdom/UptimeRobot)

**Cost target:** < $200/เดือน

### Phase 2: Tambon/Amphoe Scale (50-1K อสม., 3-12 เดือน)

**Triggers:** pilot success → first paying รพ.สต. customers

**Architecture changes:**
- **Migrate to cloud ในไทย** (details in section 5)
- Add Redis caching layer for patient lists (invalidate on write)
- Setup CDN (Cloudflare or similar) for static assets
- Implement rate limiting properly (per user + global)
- Queue-based async OCR (Redis Queue or similar simple queue)

**Operational:**
- Daily DB backups with 30-day retention
- Incident response runbook exercised
- On-call rotation (ถ้ามีทีม)

**Cost target:** $500-2K/เดือน

### Phase 3: Multi-Province (1K-10K อสม., 1-2 ปี)

**Triggers:** 1K+ active อสม., expanding to multiple provinces

**Architecture changes:**
- **Partition audit_log by month** (schema ready since Phase 1, apply partitioning)
- **Read replicas** for Neon (or equivalent) — offload reporting/analytics queries
- **Move Gemini to async queue** — don't block user request on OCR
- **Multi-region deployment** (if serving geographic diversity)
- **Dedicated background worker** pool for:
  - OCR processing
  - Audit log writing (async)
  - Report generation
  - Data retention cleanup jobs

**Team/Process:**
- Dedicated DBA time (can be part-time)
- Load testing before releases
- Feature flagging for risky rollouts

**Cost target:** $5-20K/เดือน

### Phase 4: Regional (10K-100K อสม., 2-5 ปี)

**Triggers:** Integration กับ สบส. หรือ multi-province expansion สำเร็จ

**Architecture changes — MAJOR:**
- **Migrate OFF Vercel** → Kubernetes (EKS/GKE) or ECS on in-country cloud
- **Separate services:**
  - API (stateless, horizontally scalable)
  - Bot service (dedicated, with multiple Telegram bot accounts)
  - OCR service (async worker pool)
  - Audit log service (write-heavy, isolated)
  - Notification service
- **Event-driven architecture** using Kafka or RabbitMQ
- **Dedicated caching cluster** (Redis Enterprise or AWS ElastiCache)
- **CDN + Edge functions** for read-heavy operations

**Data layer:**
- PostgreSQL with streaming replication
- Audit logs → separate write-optimized store (TimescaleDB or ClickHouse for analytics)
- Cold audit logs → S3 + Athena/Presto for compliance queries

**Cost target:** $20-80K/เดือน

### Phase 5: National (100K-1M อสม., 5-10 ปี)

**Architecture changes — EXTENSIVE:**
- **DB sharding** by `organization_id` (or `province_code` for geographic locality)
- **On-premise OCR** to control cost + data residency (PaddleOCR fine-tuned model)
- **Dedicated audit log infrastructure** (Kafka → ClickHouse or Elasticsearch)
- **Global load balancer** with region-specific routing
- **Multi-master replication** for high availability
- **Dedicated SRE team**

**Team requirements:**
- SRE team (24/7 on-call)
- Platform engineering team
- Security team (PDPA compliance, incident response)
- Data engineering (for analytics + research)

**Cost target:** $100K-500K+/เดือน (but revenue should support this)

---

## 5. Vercel Migration Plan

Vercel is ideal สำหรับ MVP แต่ไม่เหมาะสำหรับ scale ด้วยเหตุผลหลัก:
1. Cold starts ภายใต้ high load
2. ต้นทุนก้าวกระโดดที่ scale
3. Data residency ไม่มีใน region ไทย
4. Function timeout จำกัด operations
5. Vendor lock-in (middleware, routing)

### 5.1 Target Architecture (Phase 2-3)

**Option A: Cloud ในไทย — Self-managed containers**

```
[Cloudflare/CDN] 
    ↓
[Load Balancer (Cloud ในไทย)]
    ↓
[Next.js frontend — containerized, 2+ instances]
    ↓
[FastAPI backend — containerized, 4+ instances]
    ↓  ↘
[PostgreSQL]  [Redis]
    ↓           ↓
[Backup]     [OCR Queue Workers]
              ↓
          [Gemini API]
```

**Vendor candidates (data ในไทย):**

| Vendor | Strengths | Weaknesses | Recommended for |
|--------|-----------|------------|-----------------|
| **NT Cloud (National Telecom)** | ราชการใช้, data in-country, MPLS options | UI/DevOps tooling ยังไม่ mature | Enterprise/government clients |
| **Internet Thailand (INET)** | Thai-based, compliance-friendly, OpenStack-based | Smaller ecosystem | Mid-market |
| **True IDC** | Large DC footprint, CDN options | Pricing opaque | Large enterprise |
| **AWS Asia Pacific (Bangkok region)** | Best tooling, ecosystem | US vendor (may not satisfy strict data residency for government) | Commercial clients |
| **Google Cloud (Bangkok)** | Good Gemini integration, GKE mature | Same concern | If keeping Gemini |
| **Azure (Bangkok/Singapore)** | Enterprise focus | Same concern | Enterprise |

**Recommendation:**
- **Government/รพ.สต. clients** → NT Cloud or INET (ชัดเจนเรื่อง sovereignty)
- **Commercial/hospital/insurance clients** → AWS Bangkok or GCP Bangkok (better tooling)
- **Hybrid:** Backend ใน NT Cloud, Gemini calls still go to US (documented in Privacy Policy)

### 5.2 Migration Phases

#### Phase A: Parallel Run (Dual-Write)

**Duration:** 2-4 สัปดาห์

1. Setup new infrastructure in target cloud
2. Deploy identical codebase (Dockerize everything)
3. Setup streaming replication from Neon → new PostgreSQL
4. Deploy frontend container alongside Vercel (shadow)
5. Test throughly on staging

**No user impact. Vercel still handles production traffic.**

#### Phase B: Canary Migration (5-10% traffic)

**Duration:** 1-2 สัปดาห์

1. Route 5% of traffic via Cloudflare Load Balancer to new stack
2. Monitor error rates, latency, consistency
3. If issues: rollback to 100% Vercel
4. Gradually increase: 5% → 20% → 50%

**Data sync:** Still dual-write + async replication ensuring consistency

#### Phase C: Full Cutover

**Duration:** 1 สัปดาห์

1. Stop writes to Vercel+Neon
2. Verify final sync
3. Switch 100% traffic to new stack
4. Keep Vercel running read-only for 2 weeks (emergency rollback)
5. Decommission Vercel

**Downtime target:** < 5 นาทีสำหรับ DNS propagation

### 5.3 Data Migration Strategy

**Neon PostgreSQL → New PostgreSQL**

#### Option 1: Logical Replication (Recommended)

```bash
# On source (Neon)
CREATE PUBLICATION bp_migration FOR ALL TABLES;

# On target (new PG)
CREATE SUBSCRIPTION bp_migration_sub
  CONNECTION 'host=neon.example.com ...'
  PUBLICATION bp_migration
  WITH (copy_data = true);
```

**Pros:**
- Zero downtime
- Automatic continuous sync
- Built into PostgreSQL

**Cons:**
- Doesn't replicate DDL changes
- Large initial copy may take hours/days

#### Option 2: pg_dump + restore + catchup

```bash
# Dump from source
pg_dump --format=custom --jobs=8 neon_url > bp_dump.sql

# Restore to target
pg_restore --jobs=8 -d target_url bp_dump.sql

# Catch up changes via manual process or logical replication
```

**Pros:**
- Simple, well-understood
- Can verify schema consistency

**Cons:**
- Requires maintenance window
- Gap between dump and restore means lost writes (or need downtime)

#### Option 3: Application-level Dual Write

```python
# In app code, during migration period
async def save_bp_reading(reading):
    await neon_db.save(reading)
    try:
        await new_pg.save(reading)
    except Exception as e:
        log_sync_error(reading, e)
```

**Pros:**
- Controlled, observable
- Can verify record-by-record

**Cons:**
- Application complexity
- Risk of inconsistency if one side fails
- Backfill needed for historical data

**Recommendation:** Option 1 (Logical Replication) for main migration, Option 3 for initial weeks post-cutover as safety net.

### 5.4 Redis/Upstash Migration

Upstash → Self-hosted Redis or ElastiCache

**Data to migrate:**
- OTP (5-min TTL, don't need to migrate — will regenerate)
- Session tokens (JWT, stateless — don't need to migrate)
- Rate limit counters (ephemeral — don't need to migrate)

**Action:** Switch client config, data rebuilds organically within minutes.

**Downtime:** ~15-30 minutes for currently-logged-in users who might need to re-login

### 5.5 File Storage Migration (PostgreSQL BYTEA → Object Storage)

**Only relevant at Phase 3+** when volume grows

**Target:** S3-compatible object storage (AWS S3, NT Object Storage, or MinIO self-hosted)

**Migration:**
```python
# Background job
async def migrate_files_to_s3():
    for file in db.query(File).filter(File.storage_backend == 'postgres_bytea'):
        data = decrypt(file.data_encrypted)
        s3_path = f"files/{file.external_id}"
        await s3_client.put_object(Bucket=BUCKET, Key=s3_path, Body=data)
        file.storage_backend = 's3'
        file.storage_path = s3_path
        file.data_encrypted = None  # free DB space
        await db.commit()
```

**Thanks to storage abstraction** (ที่ออกแบบไว้ใน [[ORG_FOUNDATION]] section 4.1.7) การ migrate นี้ transparent to application code.

### 5.6 Code Changes Required

Fortunately, our backend is **mostly framework-agnostic** (FastAPI standard). Main changes:

1. **Dockerfile** — already exists (`Dockerfile`, `docker-compose.yml`)
2. **Environment variables** — abstract all Vercel-specific configs
3. **File serving** — ensure `/api/v1/*` and static files work outside Vercel
4. **Next.js** — use `output: 'standalone'` (already configured conditionally)
5. **Cron jobs** — move from Vercel Cron to Kubernetes CronJob or cron container
6. **Image optimization** — replace Vercel Image with `next/image` + Cloudflare Images or sharp

Estimated effort: **2-4 weeks** for migration + testing

### 5.7 Cost Comparison (at 10K อสม. scale)

| Component | Vercel Pro + Neon | NT Cloud + Self-managed | AWS Bangkok |
|-----------|-------------------|-------------------------|-------------|
| Compute (API) | $500-1000/mo | $200-400/mo | $300-500/mo |
| Database | $300-600/mo | $200-300/mo (VM) | $400-700/mo (RDS) |
| Redis | $50-200/mo | $50-100/mo | $100-200/mo |
| Storage (OCR, backups) | Included | $20-50/mo | $30-80/mo |
| Bandwidth | Included | $50-150/mo | $100-300/mo |
| Monitoring | Included (basic) | $50-100/mo (Datadog) | $100-200/mo |
| **Total** | **$850-1800/mo** | **$570-1100/mo** | **$1030-1980/mo** |

**Savings at 10K scale:** ~30-50% with self-managed on in-country cloud

**At 100K scale, savings grow to 50-70%** because Vercel costs scale non-linearly

---

## 6. Partition-Ready Schema (Do It Now)

เพื่อไม่ให้ต้อง migrate ใหญ่ในอนาคต เราควรใช้ partitioning ตั้งแต่ MVP สำหรับ audit_logs

### 6.1 Partitioned audit_logs Schema

**Replace the audit_logs schema in [[ORG_FOUNDATION]] with this:**

```sql
-- Parent table (partitioned by month on created_at)
CREATE TABLE audit_logs (
    id BIGSERIAL,
    action VARCHAR(100) NOT NULL,
    actor_user_id INTEGER REFERENCES users(id),
    actor_role VARCHAR(50),
    actor_organization_id INTEGER REFERENCES organizations(id),
    target_type VARCHAR(50),
    target_id VARCHAR(100),
    target_user_id INTEGER REFERENCES users(id),
    from_ip VARCHAR(64),
    user_agent TEXT,
    request_id VARCHAR(64),
    session_id VARCHAR(64),
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)  -- Partition key must be in PK
) PARTITION BY RANGE (created_at);

-- Create partitions for first 12 months
CREATE TABLE audit_logs_2026_04 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE audit_logs_2026_05 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
-- ... continue monthly

-- Default partition for overflow (safety net)
CREATE TABLE audit_logs_default PARTITION OF audit_logs DEFAULT;

-- Indexes on parent (applied to all partitions)
CREATE INDEX ix_audit_actor_time ON audit_logs (actor_user_id, created_at);
CREATE INDEX ix_audit_target_user_time ON audit_logs (target_user_id, created_at);
CREATE INDEX ix_audit_action_time ON audit_logs (action, created_at);
CREATE INDEX ix_audit_org_time ON audit_logs (actor_organization_id, created_at);
CREATE INDEX ix_audit_failures ON audit_logs (created_at) WHERE success = false;
```

### 6.2 Partition Maintenance (pg_partman)

```sql
-- Install pg_partman extension
CREATE EXTENSION IF NOT EXISTS pg_partman;

-- Configure automatic partition creation
SELECT partman.create_parent(
    p_parent_table => 'public.audit_logs',
    p_control => 'created_at',
    p_type => 'range',
    p_interval => '1 month',
    p_premake => 3  -- create 3 months ahead
);

-- Schedule cron job to create new partitions
-- Run monthly: SELECT partman.run_maintenance();
```

### 6.3 Retention via Partition Drop

```sql
-- After 2 years (hot), drop partition instead of DELETE
ALTER TABLE audit_logs DETACH PARTITION audit_logs_2024_04;

-- Archive to S3 (via pg_dump + upload)
-- Then:
DROP TABLE audit_logs_2024_04;
```

**Benefit:** Dropping partition is instant (no row-by-row delete), doesn't generate WAL, doesn't block

### 6.4 Migration from Non-Partitioned (if Phase 1 already deployed)

```sql
-- 1. Rename existing table
ALTER TABLE audit_logs RENAME TO audit_logs_old;

-- 2. Create new partitioned table (as above)

-- 3. Copy data (can be slow; do during low-traffic period)
INSERT INTO audit_logs SELECT * FROM audit_logs_old;

-- 4. Drop old
DROP TABLE audit_logs_old;
```

**Better:** Do it RIGHT from the start in Phase 1 migration 05 (see [[ORG_FOUNDATION]] section 5.1)

---

## 7. Tenant Isolation — Sharding Preparation

### 7.1 Ensure all queries scoped by `organization_id`

Every cross-user query MUST include organization scope:

```python
# Good — scoped
async def get_patients(current_user: User):
    return db.query(User).filter(
        User.managed_by_organization_id == current_user.organization_id
    ).all()

# Bad — unscoped, breaks sharding
async def get_all_patients_ever():
    return db.query(User).filter(User.role == 'patient_proxy').all()
```

### 7.2 Future Sharding Strategy

When we hit ~500K อสม., shard PostgreSQL by `organization_id`:

**Shard key:** `organization_id % N` where N = number of shards

**Routing:** Application-level routing (Citus, or custom)

**Cross-shard queries:** 
- Most queries don't need to cross shards (scoped by org)
- Analytics/reporting: dedicated replica + materialized views
- Superadmin queries: fan-out to all shards (rare)

**Architecture:**
```
[App] → [Shard Router] → [Shard 1: orgs 0-999]
                       → [Shard 2: orgs 1000-1999]
                       → [Shard N: ...]
```

**Prep work doing NOW:**
- Never assume single DB (always pass org_id)
- Use UUID `external_id` in URLs (don't leak internal id)
- Design APIs to minimize cross-org operations

---

## 8. Observability (Start Phase 1)

### 8.1 Logging

**Structured JSON logs** with:
- `request_id` (correlation across services)
- `user_id` (for traceability)
- `organization_id` (for tenant-level analysis)
- `duration_ms`
- `status_code`
- `endpoint`

**Shipping:**
- Phase 1: Vercel logs → export daily to S3 for retention
- Phase 2+: Fluentd/Vector → Loki or ELK stack

### 8.2 Metrics

**Key metrics to track:**
- **RED metrics:** Rate (rps), Errors (%), Duration (p50/p95/p99)
- **USE metrics (DB):** Utilization (CPU), Saturation (queue depth), Errors
- **Business:** DAU/MAU, readings/day, OCR success rate, consent completion rate
- **PDPA compliance:** audit log write latency, cross-user access counts

**Phase 1:** Vercel Analytics + custom Prometheus endpoint
**Phase 2+:** Datadog, Grafana Cloud, or New Relic

### 8.3 Tracing

**Phase 1:** Optional (basic request_id correlation via logs)
**Phase 2+:** OpenTelemetry + Jaeger/Tempo

### 8.4 Alerting

**Phase 1 alerts:**
- Error rate > 5% for 5 min
- p95 latency > 5s for 10 min
- DB connection failures
- OCR API failures > 10%

**Phase 2+ adds:**
- Audit log write lag > 30s
- Consent scope violations detected
- Unusual patterns (anomaly detection)

---

## 9. Cost Projection

### 9.1 Infrastructure Cost by Phase

| Phase | อสม. | Monthly Cost | Annualized |
|-------|------|--------------|------------|
| 1 MVP | 0-50 | $50-200 | $600-2.4K |
| 2 Tambon | 50-1K | $500-2K | $6K-24K |
| 3 Multi-Province | 1K-10K | $5-20K | $60K-240K |
| 4 Regional | 10K-100K | $20-80K | $240K-960K |
| 5 National | 100K-1M | $100K-500K+ | $1.2M-6M+ |

### 9.2 Per-User Economics

**Target unit economics:**
- Cost per อสม./month: should decline from $1 → $0.10 as scale grows
- Break-even depends on monetization model (per-org subscription, per-reading, etc.)

**Pricing hypothesis (example):**
- รพ.สต. subscription: ~฿500-2,000/เดือน per รพ.สต.
- With 10 อสม. per รพ.สต. = ฿50-200/อสม./เดือน revenue
- At 1K รพ.สต. = ฿500K-2M/เดือน = sustainable past Phase 2

---

## 10. Decision Triggers — When to Re-Architect

| Metric | Threshold | Action |
|--------|-----------|--------|
| Active อสม. | > 1,000 | Start planning Phase 2 migration |
| API p95 latency | > 3s | Add caching, query optimization |
| API error rate | > 1% sustained | Investigate; scale up |
| DB connection errors | > 0.1% | Add pgbouncer, audit queries |
| audit_logs size | > 10M rows | Implement partitioning (should be there already) |
| OCR cost | > $1K/month | Consider self-hosted OCR |
| Vercel bill | > $2K/month | Start Vercel migration |
| Incident count | > 2/month | Investment in reliability needed |
| รพ.สต. count | > 10 | Invest in self-service onboarding |
| PDPA requests | > 10/month | Automate data subject request flow |

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Vercel cost blowup | Financial | Monitor, have migration plan ready (this doc) |
| Data residency challenge from gov | Legal blocker | Plan B: NT Cloud migration ready |
| Gemini rate limits hit | Service degradation | Fallback to manual entry, multi-region Gemini accounts |
| DB hot partition (popular org) | Performance | Identify early, consider per-org dedicated resources |
| audit_log explosion | Cost + performance | Partitioning + retention policy enforced |
| Telegram bot rate limit | Service degradation | Multi-bot sharding ready |
| Key staff leaves during scale | Operational | Documentation + SOP + runbooks |
| Compliance audit finds issues | Legal + reputation | Regular internal audits + external review |

---

## 12. Implementation Checklist (Phase 1 — Do Now)

- [ ] Implement partitioned `audit_logs` schema from day 1
- [ ] All queries include `organization_id` scope (sharding prep)
- [ ] Use UUID `external_id` in all URLs (not internal id)
- [ ] Storage abstraction for files (swap-ready)
- [ ] Structured logging with `request_id`
- [ ] Sentry error tracking
- [ ] Basic uptime monitoring
- [ ] Document current architecture diagram
- [ ] Dockerize everything (prep for migration off Vercel)
- [ ] Keep secrets in env vars (not Vercel-specific)
- [ ] `output: 'standalone'` for Next.js (conditional, works outside Vercel too)

## 13. Implementation Checklist (Phase 2 — Prepare Now for 6-12 mo)

- [ ] Choose cloud vendor ในไทย (NT/INET/other)
- [ ] Setup staging environment on target cloud
- [ ] Build container images + Helm charts / ECS task defs
- [ ] Test Neon → target PG migration on staging
- [ ] Redis caching layer design
- [ ] CDN setup (Cloudflare)
- [ ] Enhanced monitoring (Datadog/Grafana)
- [ ] DR plan (backup + restore procedures tested)
- [ ] Legal review: data residency compliance with current cloud

---

## 14. Open Questions

1. **Cloud vendor choice** — NT, INET, True IDC, หรือ AWS Bangkok? ต้อง match กับ customer segment
2. **OCR cost control** — self-hosted model timeline? evaluate PaddleOCR / Qwen2-VL / others
3. **Revenue model** — per-org subscription vs per-reading? affects unit economics
4. **Team hiring plan** — when to hire DBA, SRE, security engineer?
5. **Compliance tiers** — if we go to hospital/insurance, additional certifications needed (ISO 27001, HITRUST)?

---

**End of SCALABILITY_PLAN.md**
