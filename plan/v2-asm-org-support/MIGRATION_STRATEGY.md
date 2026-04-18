---
title: "Migration Strategy — v2 ASM Org Support"
aliases:
  - "Migration Strategy"
  - "Staged Migration"
tags:
  - migration
  - v2-asm-org
  - strategy
order: 0.9
status: draft
version: 1.0
updated: 2026-04-18
summary: "How to safely apply v2 schema migrations on production: staged column-type changes, FK dependency graph, rollback procedures, zero-downtime principles"
---

# v2 Migration Strategy

> **Purpose:** How to safely migrate production schema from v1 (B2C) to v2 (ASM org support) without data loss or downtime
>
> **Depends on:** [[INFRASTRUCTURE_SETUP]] (must complete first), [[ORG_FOUNDATION]] §5 (migration sequence)
>
> **Principle:** Additive > destructive. Dual-read during transitions. No big-bang column type changes.

---

## 1. Core principles

1. **Additive first** — ทุก column/table ใหม่เพิ่มเข้าไป, ของเก่าคงอยู่
2. **No breaking changes in a single migration** — ถ้าเปลี่ยน type = 5-step procedure (§3)
3. **Dual-read during transitions** — code อ่านทั้ง new + old column, fallback ชัด
4. **Idempotent** — ทุก migration re-run ได้โดยไม่เสียข้อมูล
5. **Rollback tested on staging** ก่อน apply prod ทุกครั้ง
6. **Feature flag gating** — v2 endpoints ปิดจน migration เสร็จ + validate

---

## 2. FK dependency graph

v2 migrations ต้อง respect FK ordering. ภาพรวม:

```
                      schema_migrations (v2_00)
                              │
                      enums (v2_01, PG only)
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
   organizations (v2_02) ◄────────────┐   users (existing, extended v2_04)
          │                           │           │
          ├──► organization_members (v2_03)       │ (backfill v2_05)
          │           │                           │
          │           └───────────────────────────┤
          ▼                                       ▼
   care_assignments (v2_06)  ◄─────────────► consent_records (v2_07)
          │                                       │
          │                                       ▼
          │                               pairing_codes (v2_08)
          │                                       │
          ▼                                       ▼
        files (v2_09) ◄── blood_pressure_records (extended v2_10)
                                                  │
                                         (backfill v2_11)
                                                  │
                                                  ▼
                                          audit_logs (v2_12)
                                                  │
                                                  ▼
                                       licenses (extended v2_13)
```

**Rules:**
- Create referenced table **ก่อน** ต้องมี FK ชี้มา
- Drop เทเบิลที่มี FK ปลายทาง **ก่อน** drop table ต้นทาง
- Rollback order = reverse of migration order

---

## 3. Staged column type migration (5-step)

**Use when:** เปลี่ยน column type (เช่น `DateTime` → `DateTime(timezone=True)`), rename column, or change NOT NULL constraint on existing data

**Never do big-bang** บน prod — PostgreSQL `ALTER COLUMN TYPE` ล็อก table + rewrites (ขึ้นอยู่กับ type)

### Procedure (5 steps, across ≥ 2 deploys)

**Step 1: Add new column (nullable, no default that triggers rewrite)**

Migration `v2_XX_add_<column>_new.py`:
```python
def migrate():
    with db_transaction() as conn:
        conn.execute(text("""
            ALTER TABLE <table>
            ADD COLUMN <column>_new <new_type> NULL
        """))
        # NO DEFAULT with value → avoids full table rewrite
```

Deploy: **Safe** — no reads/writes to new column yet

**Step 2: Backfill ในชุดเล็ก ๆ (chunked update for big tables)**

Migration `v2_XX_backfill_<column>.py`:
```python
def migrate():
    with db_transaction() as conn:
        # Chunked: 1000 rows at a time
        while True:
            result = conn.execute(text("""
                UPDATE <table>
                SET <column>_new = <transformation>(<column>_old)
                WHERE id IN (
                    SELECT id FROM <table>
                    WHERE <column>_new IS NULL
                    LIMIT 1000
                )
                RETURNING id
            """))
            if result.rowcount == 0:
                break
            conn.commit()
```

Deploy: **Safe** — still no reads from new column

**Step 3: Dual-read in code (with fallback)**

App code changes:
```python
# Helper
def get_measured_at(record) -> datetime:
    # Prefer new column
    if record.measured_at_new is not None:
        return record.measured_at_new
    # Fallback to old column (assume local tz for naive → aware)
    return record.measured_at_old.replace(tzinfo=BANGKOK_TZ)

# Writes: dual-write both columns
record.measured_at_old = value  # legacy
record.measured_at_new = value  # new (same value, with tz)
```

Deploy: **Safe** — all reads/writes go through helper

Observe: monitor logs for 24-72h ว่าไม่มี null issues

**Step 4: Swap (rename columns, make new column NOT NULL)**

Migration `v2_XX_swap_<column>.py`:
```python
def migrate():
    with db_transaction() as conn:
        # Rename old → deprecated, new → canonical
        conn.execute(text("ALTER TABLE <table> RENAME COLUMN <column>_old TO <column>_deprecated"))
        conn.execute(text("ALTER TABLE <table> RENAME COLUMN <column>_new TO <column>"))
        # NOT NULL (safe now — all rows populated)
        conn.execute(text("ALTER TABLE <table> ALTER COLUMN <column> SET NOT NULL"))
```

Code changes: **Remove fallback** — read `<column>` directly (no more helper)

Deploy: **Coordinated** — deploy schema change + code change together

**Step 5: Drop old column** (next release, after stable)

Migration `v2_XX_drop_<column>_deprecated.py`:
```python
def migrate():
    with db_transaction() as conn:
        conn.execute(text("ALTER TABLE <table> DROP COLUMN <column>_deprecated"))
```

Deploy: **Safe** — nothing reads deprecated column

### Priority columns for v2 staged migration

| Column | Priority | Est. rows affected | Reason |
|--------|----------|---------------------|--------|
| `blood_pressure_records.measurement_date` → `measured_at` (tz-aware) | **P1 — defer** | check prod snapshot | Active high-traffic column |
| `users.created_at`, `updated_at`, `last_login` → tz-aware | P2 | low traffic | Less risky |
| `audit_logs.created_at` | **P0 — new table, no migration** | 0 | Start fresh with tz-aware |

**Recommendation for v2 MVP:** Skip timezone migration of existing columns in v2. Keep `measurement_date` (naive) and add NEW column `measured_at` (tz-aware) per ORG_FOUNDATION §4.2.2 — simpler, no 5-step dance.

**Defer** `measurement_date` → `measured_at` swap to **v2.1** after v2 stable.

---

## 4. Per-migration risk & rollback table

| Migration | Risk | Blocking? | Rollback | Notes |
|-----------|------|-----------|----------|-------|
| v2_00 schema_migrations | 🟢 Low | No | `DROP TABLE` | Prerequisite, do first |
| v2_01 create enums | 🟢 Low (PG only) | No | `DROP TYPE IF EXISTS` | No-op on SQLite |
| v2_02 organizations | 🟢 Low | No | `DROP TABLE organizations` | New table |
| v2_03 organization_members | 🟢 Low | No | `DROP TABLE organization_members` | FK to orgs + users |
| v2_04 extend users (ADD cols) | 🟡 Medium | **Yes** | Drop new columns individually | Affects active table |
| v2_05 backfill users | 🟢 Low (data only) | No | `UPDATE ... SET new_cols = NULL` | Idempotent via WHERE IS NULL |
| v2_06 care_assignments | 🟢 Low | No | `DROP TABLE care_assignments` | New |
| v2_07 consent_records | 🟢 Low | No | `DROP TABLE consent_records` | New |
| v2_08 pairing_codes | 🟢 Low | No | `DROP TABLE pairing_codes` | New |
| v2_09 files | 🟡 Medium | No | `DROP TABLE files` + drop CHECK constraint first | Has CHECK constraint |
| v2_10 extend bp_readings (ADD cols) | 🔴 High | **Yes** | Drop new columns individually | **High-traffic table** |
| v2_11 backfill bp_readings | 🟡 Medium (data) | No | `UPDATE ... SET new_cols = NULL` | Chunk if > 100k rows |
| v2_12 audit_logs | 🟢 Low | No | `DROP TABLE audit_logs` | New |
| v2_13 extend licenses | 🟢 Low | No | Drop FK column | Dead code, ~0 rows expected |

🟢 Low = can run anytime, rollback simple
🟡 Medium = run in maintenance window, verify carefully
🔴 High = staging drill mandatory, run in maintenance window with extra eyes

### 4.1 v2_10 (bp_readings extend) risk mitigation

- **Run during low-traffic window** (for Thai users: 02:00–05:00 ICT)
- Pre-check: `SELECT pg_relation_size('blood_pressure_records');` — ถ้า > 1GB ให้ทำ table-level lock analysis ก่อน
- ADD COLUMN without default = fast (metadata only change)
- ADD COLUMN with default = slow (PG rewrite). **Avoid default values for NOT NULL columns on large tables**; backfill separately (v2_11)

---

## 5. Cutover sequence (prod migration day)

### 5.1 Pre-cutover (t - 24h)

- [ ] Complete INFRASTRUCTURE_SETUP checklist (§8)
- [ ] Final staging drill: run ALL migrations on `staging-v2` branch end-to-end
- [ ] Verify: end-to-end test suite passes on staging
- [ ] Announce (to self in diary/notes): "Migration window: <date>, <time>"
- [ ] Ensure: `ENABLE_ORG_MODE=false` and `ENABLE_V2_MIGRATIONS=false` in prod Vercel env

### 5.2 Cutover (t = 0)

**Step-by-step (allow ~1 hour):**

1. **Create Neon prod snapshot**
   ```bash
   neon branches create --name "pre-v2-$(date +%Y%m%d-%H%M)" --parent production
   ```

2. **Set DATABASE_URL locally to prod**
   ```bash
   export DATABASE_URL="<neon_prod_url>"
   ```

3. **Run v2_00 (schema_migrations table)**
   ```bash
   python -m migrations.v2_00_create_schema_migrations
   # Verify: psql $DATABASE_URL -c "\d schema_migrations"
   ```

4. **Run v2_01 through v2_13 one at a time**
   ```bash
   python -m migrations.v2_01_create_enums
   # verify schema
   python -m migrations.v2_02_create_organizations
   # verify schema
   # ... etc.
   ```

   **After each:**
   - `psql $DATABASE_URL -c "SELECT version FROM schema_migrations ORDER BY applied_at DESC LIMIT 3;"` — confirm recorded
   - `psql $DATABASE_URL -c "\d <new_table_or_column>"` — confirm schema correct
   - Smoke test: hit production API `GET /health` — confirm app still responding

5. **After all migrations done:**
   ```bash
   unset DATABASE_URL  # clear prod connection
   ```

6. **Do NOT flip `ENABLE_ORG_MODE=true` yet.** Existing B2C flow should still work 100%.

### 5.3 Post-cutover observe (t + 0 to t + 24h)

- [ ] Smoke test existing flows: login, record BP, doctor list patients, admin audit log view
- [ ] Monitor Vercel logs for errors
- [ ] Query schema_migrations: confirm all v2_* versions recorded
- [ ] Monitor DB CPU/connections on Neon (should be normal)

### 5.4 Enable v2 endpoints (t + 24-72h, after no issues)

1. Deploy frontend + backend code ที่มี v2 endpoints (stubs first)
2. Set `ENABLE_ORG_MODE=true` in Vercel
3. Redeploy
4. Test v2 endpoints (via direct API calls or admin UI)
5. Monitor

### 5.5 Rollback procedure (if needed)

**If migration fails midway:**

Option A — Script-level rollback (preferred if you know which script failed):
```bash
# Roll back last successful migration
python -c "from migrations.v2_10_extend_bp_readings import rollback; rollback()"
python -c "from migrations.v2_09_create_files import rollback; rollback()"
# ... reverse order
```

Option B — Point-in-time restore (nuclear option if rollback scripts fail):
- Via Neon: Switch branch from `production` to `pre-v2-<timestamp>` in Vercel env
- Data written after snapshot is LOST — only use if migration corrupted data

**After rollback:**
- Document what failed in `plan/v2-asm-org-support/ROLLBACK_<date>.md`
- Fix script on staging
- Retry next day (not same day — brain needs rest)

---

## 6. SQLite (dev) vs PostgreSQL (prod) divergence

### 6.1 Syntax that differs

| Feature | PostgreSQL | SQLite | How to handle |
|---------|------------|--------|---------------|
| `JSONB` | native type | use `TEXT` | Check dialect in migration |
| `UUID` | native type | use `TEXT` (store as string) | Same |
| `BigInteger PK` | `BIGINT` | `INTEGER` (auto 64-bit) | Same |
| Partial index `WHERE` clause | `postgresql_where=...` | not supported before 3.8 | Skip index on SQLite |
| Enum type | `CREATE TYPE` | use `TEXT` + CHECK | Migration dialect branch |
| `ON CONFLICT DO NOTHING` | supported | supported 3.24+ | Check SQLite version |

### 6.2 Pattern for dialect-aware migrations

```python
# migrations/_helpers.py (add)
def is_postgres() -> bool:
    return DATABASE_URL.startswith("postgresql")


# In migration file:
def migrate():
    with db_transaction() as conn:
        if is_postgres():
            conn.execute(text("""
                CREATE TABLE organizations (
                    id SERIAL PRIMARY KEY,
                    external_id UUID NOT NULL DEFAULT gen_random_uuid(),
                    extra_metadata JSONB
                )
            """))
        else:  # SQLite
            conn.execute(text("""
                CREATE TABLE organizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    external_id TEXT NOT NULL,
                    extra_metadata TEXT
                )
            """))
```

### 6.3 Test procedure

- Dev: SQLite local — test migration scripts run without error
- Staging: Neon branch (PostgreSQL) — test real dialect, real data shape
- **Never skip staging** even if SQLite works locally

---

## 7. Observability during migration

### 7.1 Logging template in every migration

```python
import logging
logger = logging.getLogger(__name__)

@migration_guard("v2_02", "Create organizations table")
def migrate():
    import time
    start = time.monotonic()
    logger.info(f"[v2_02] START: creating organizations table")
    with db_transaction() as conn:
        # ... migration ...
        pass
    logger.info(f"[v2_02] DONE in {time.monotonic() - start:.1f}s")
```

### 7.2 Neon query insights (during migration)

Dashboard → Query Insights → active queries. ถ้าเห็น:
- `ALTER TABLE` running > 30s บน large table → investigate lock contention
- `UPDATE` not completing → chunked version needed

### 7.3 Post-migration verification queries

```sql
-- Confirm all v2 migrations applied
SELECT version, applied_at FROM schema_migrations WHERE version LIKE 'v2_%' ORDER BY version;

-- Confirm new columns in users
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
  AND column_name IN ('external_id', 'account_type', 'primary_role', 'managed_by_organization_id', 'deleted_at');

-- Confirm new tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('organizations', 'organization_members', 'care_assignments',
                     'consent_records', 'pairing_codes', 'files', 'audit_logs');

-- Confirm backfill complete
SELECT COUNT(*) AS null_primary_role FROM users WHERE primary_role IS NULL;
-- Expected: 0

SELECT COUNT(*) AS null_measured_at FROM blood_pressure_records WHERE measured_at IS NULL;
-- Expected: 0 (after v2_11 backfill)
```

---

## 8. Open questions (to resolve as plan matures)

| # | Question | Blocks |
|---|----------|--------|
| M1 | Chunked backfill size for bp_readings (1000? 5000?) | v2_11 design — depends on row count |
| M2 | Maintenance window timing (low traffic hours) | Cutover day |
| M3 | Vercel function timeout — migration >10s bn Vercel? | Option B/C choice for Vercel execution |
| M4 | Neon paid vs free tier PITR window | Backup drill strategy |

---

**End of MIGRATION_STRATEGY.md**
