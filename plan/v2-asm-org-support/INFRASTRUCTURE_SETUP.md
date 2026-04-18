---
title: "Infrastructure Setup — v2 Prerequisites"
aliases:
  - "Infrastructure Setup"
  - "Tier 0 Setup"
tags:
  - infrastructure
  - v2-asm-org
  - prerequisites
order: 0.8
status: draft
version: 1.0
updated: 2026-04-18
summary: "Production safety prerequisites ก่อนเริ่ม v2 code phase: schema_migrations table, feature flags, staging branch, backup drill, pre-flight verification queries"
---

# Infrastructure Setup — v2 Prerequisites

> **Purpose:** Setup ที่ต้องทำ **ก่อน** เริ่ม v2 code phase เพื่อลด risk บน prod
>
> **Audience:** Pornthep (solo developer)
>
> **Blocks:** All v2 migration work — อย่าเริ่ม coding migration scripts จนกว่า steps ใน doc นี้เสร็จ

---

## 1. Pre-flight verification queries

**Run ทั้งหมดนี้บน Neon prod ก่อน** เพื่อตัดสินใจแผน migration ที่เหลือ

```sql
-- 1. Row counts (สำคัญสำหรับ timezone migration cost estimate)
SELECT 'users' AS tbl, COUNT(*) AS n FROM users
UNION ALL
SELECT 'blood_pressure_records', COUNT(*) FROM blood_pressure_records
UNION ALL
SELECT 'admin_audit_logs', COUNT(*) FROM admin_audit_logs
UNION ALL
SELECT 'licenses', COUNT(*) FROM licenses
UNION ALL
SELECT 'access_requests', COUNT(*) FROM access_requests
UNION ALL
SELECT 'doctor_patients', COUNT(*) FROM doctor_patients
UNION ALL
SELECT 'staff_management_state', COUNT(*) FROM staff_management_state;

-- 2. Role distribution (verify LEGACY_ROLE_MAP covers all values)
SELECT role, COUNT(*) FROM users GROUP BY role ORDER BY COUNT(*) DESC;

-- 3. Verification status (doctor verify workflow)
SELECT verification_status, COUNT(*) FROM users
WHERE role = 'doctor' GROUP BY verification_status;

-- 4. Subscription tier (for future license mapping)
SELECT subscription_tier, COUNT(*) FROM users GROUP BY subscription_tier;

-- 5. Active access requests (surface area for doctor flow)
SELECT status, COUNT(*) FROM access_requests GROUP BY status;

-- 6. Staff source (env vs db)
SELECT management_source, COUNT(*) FROM staff_management_state GROUP BY management_source;
```

**Document results ใน `plan/v2-asm-org-support/PROD_SNAPSHOT_<date>.md`** ก่อน migration day เพื่อ reference.

**Decision triggers ตาม numbers:**

| Finding | Implication |
|---------|-------------|
| `blood_pressure_records` > 100k rows | Timezone migration ต้อง stage แบบละเอียด (chunked update) |
| `admin_audit_logs` > 10k rows | Dual-write transition worthwhile (don't just ignore old table) |
| `licenses` = 0 rows | License backfill = no-op (decision 4.6 verified) |
| `licenses` > 0 rows | ต้องเขียน backfill เป็น sub-migration |
| `users.role` มีค่าที่ไม่อยู่ใน LEGACY_ROLE_MAP | Update map ก่อน migrate |

---

## 2. Vercel environment variables audit

**Check ตอนนี้:**

```bash
# Get current env vars (local terminal)
vercel env ls production
```

**Required values ที่ต้อง verify:**

| Variable | Expected | Why it matters |
|----------|----------|----------------|
| `AUTO_CREATE_TABLES` | `true` (assumed) or `false` | ถ้า `true` = new tables auto-created ตอน startup; ถ้า `false` = migration script ต้องรัน manual |
| `DATABASE_URL` | `postgresql://...neon.tech/...` | Production DB (prod branch) |
| `ENVIRONMENT` | `production` | Prevents dev-only paths |

**Add ใหม่ (v2):**

| Variable | Value | Purpose |
|----------|-------|---------|
| `ENABLE_ORG_MODE` | `false` | Feature flag: v2 endpoints ปิดจน validate แล้ว |
| `ENABLE_DUAL_WRITE_AUDIT` | `true` | Phase 1 ของ AdminAuditLog transition (§7.6) |
| `ENABLE_V2_MIGRATIONS` | `false` | Gate: ห้าม Vercel startup เรียก v2 migration โดย default (manual trigger only) |

**Command:**
```bash
vercel env add ENABLE_ORG_MODE production
# Enter: false
vercel env add ENABLE_DUAL_WRITE_AUDIT production
# Enter: true
vercel env add ENABLE_V2_MIGRATIONS production
# Enter: false
```

**หลัง set: redeploy** เพื่อให้ env vars ใหม่ active
```bash
vercel --prod
```

---

## 3. Feature flag wiring in code

**สร้างไฟล์ใหม่: `app/utils/feature_flags.py`**

```python
"""
Feature flags for v2 migration.
All default to OFF in production to prevent accidental activation.
"""
import os


def _bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name, "").strip().lower()
    if val in ("true", "1", "yes", "on"):
        return True
    if val in ("false", "0", "no", "off"):
        return False
    return default


# Core feature flags
ENABLE_ORG_MODE = _bool("ENABLE_ORG_MODE", default=False)
"""If True, v2 endpoints (/api/v1/asm/*, /api/v1/rpsst/*) are enabled."""

ENABLE_DUAL_WRITE_AUDIT = _bool("ENABLE_DUAL_WRITE_AUDIT", default=True)
"""If True, audit logs are written to BOTH admin_audit_logs (legacy) and audit_logs (new)."""

ENABLE_V2_MIGRATIONS = _bool("ENABLE_V2_MIGRATIONS", default=False)
"""If True, main.py startup can trigger v2 migration scripts. Keep False for manual-only."""


def require_org_mode():
    """Dependency to gate v2 endpoints."""
    from fastapi import HTTPException
    if not ENABLE_ORG_MODE:
        raise HTTPException(503, "Organization mode is currently disabled")
```

**Usage ใน v2 endpoints:**
```python
from app.utils.feature_flags import require_org_mode

@router.get("/asm/patients", dependencies=[Depends(require_org_mode)])
async def list_asm_patients(...):
    ...
```

---

## 4. `schema_migrations` version table

### 4.1 DDL (เป็น migration `v2_00_create_schema_migrations.py`)

```python
# migrations/v2_00_create_schema_migrations.py
"""
Create schema_migrations version tracking table.
This is the FIRST v2 migration — must run before all others.
"""
import os
import logging
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bp_monitor.db")


def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        # Portable DDL (works for both SQLite + PostgreSQL)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(50) PRIMARY KEY,
                description VARCHAR(500),
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                applied_by VARCHAR(100),
                rollback_tested BOOLEAN DEFAULT FALSE
            )
        """))
        logger.info("[v2_00] schema_migrations table ready")


def rollback():
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS schema_migrations"))
        logger.info("[v2_00] schema_migrations table dropped")


if __name__ == "__main__":
    migrate()
```

### 4.2 Helper for other migrations

**เพิ่มใน `migrations/_helpers.py` (ใหม่):**

```python
# migrations/_helpers.py
import os
import logging
import socket
from contextlib import contextmanager
from datetime import datetime
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bp_monitor.db")


@contextmanager
def db_transaction():
    """Yield a transaction-bound connection."""
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        yield conn


def has_migration_run(version: str) -> bool:
    """Check if migration version already applied."""
    try:
        with db_transaction() as conn:
            result = conn.execute(
                text("SELECT 1 FROM schema_migrations WHERE version = :v"),
                {"v": version}
            ).fetchone()
            return result is not None
    except Exception:
        # Table might not exist yet (before v2_00)
        return False


def record_migration(version: str, description: str):
    """Mark migration as applied."""
    with db_transaction() as conn:
        conn.execute(text("""
            INSERT INTO schema_migrations (version, description, applied_by)
            VALUES (:v, :d, :by)
            ON CONFLICT (version) DO NOTHING
        """), {
            "v": version,
            "d": description,
            "by": os.getenv("USER", socket.gethostname())
        })


def unrecord_migration(version: str):
    """Remove migration record (on rollback)."""
    with db_transaction() as conn:
        conn.execute(
            text("DELETE FROM schema_migrations WHERE version = :v"),
            {"v": version}
        )


def migration_guard(version: str, description: str):
    """Decorator: skip if already applied."""
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if has_migration_run(version):
                logger.info(f"[{version}] already applied — skipping")
                return
            logger.info(f"[{version}] starting: {description}")
            fn(*args, **kwargs)
            record_migration(version, description)
            logger.info(f"[{version}] done")
        return wrapper
    return decorator
```

**Note:** `ON CONFLICT (version)` คือ PostgreSQL syntax. สำหรับ SQLite 3.24+ จะใช้ได้เหมือนกัน. ถ้าใช้ SQLite รุ่นเก่า ให้ใช้ `INSERT OR IGNORE` แทน.

### 4.3 Usage ใน migration file

```python
# migrations/v2_02_create_organizations.py
from ._helpers import migration_guard, db_transaction
from sqlalchemy import text

@migration_guard("v2_02", "Create organizations table")
def migrate():
    with db_transaction() as conn:
        conn.execute(text("CREATE TABLE organizations (...)"))

def rollback():
    with db_transaction() as conn:
        conn.execute(text("DROP TABLE IF EXISTS organizations"))
        # manual unrecord
        from ._helpers import unrecord_migration
        unrecord_migration("v2_02")
```

### 4.4 Update `run_all.py` to be migration-aware

**Append to existing `migrations/run_all.py`:**

```python
# Append after existing migrations
V2_MIGRATIONS = [
    ("v2_00", "migrations.v2_00_create_schema_migrations"),
    ("v2_01", "migrations.v2_01_create_enums"),
    # ... (add as created)
]

def run_v2_migrations():
    from migrations._helpers import has_migration_run
    import importlib
    for version, module_path in V2_MIGRATIONS:
        if has_migration_run(version):
            print(f"[{version}] already applied, skip")
            continue
        print(f"[{version}] running...")
        mod = importlib.import_module(module_path)
        mod.migrate()
```

---

## 5. Neon staging branch setup

**Goal:** ทุก migration run บน staging branch ก่อน prod

### 5.1 Create Neon branch

```bash
# Via Neon CLI (install: curl -fsSL https://neon.tech/install.sh | sh)
neon branches create --name staging-v2 --parent production
```

จะได้ staging connection string เช่น:
```
postgres://<user>:<pass>@ep-XXXX-staging-v2.ap-southeast-1.aws.neon.tech/neondb
```

**Alternative via Neon Console:** Dashboard → Project → Branches → "Create branch" → Parent=main → Name=`staging-v2`

### 5.2 Add staging env vars (Vercel preview)

สำหรับ deploy preview testing บน staging DB:

```bash
# Vercel preview env (separate from production)
vercel env add DATABASE_URL preview
# Paste staging connection string
```

### 5.3 Staging migration drill procedure

**ก่อน apply migration บน prod:**
1. เลือก migration file ที่เสร็จ (เช่น `v2_02_create_organizations.py`)
2. Point `DATABASE_URL` ชั่วคราวไปที่ staging branch: `export DATABASE_URL=<staging_url>`
3. Run: `python -m migrations.v2_02_create_organizations`
4. Verify: `psql $DATABASE_URL -c "\d organizations"` — check schema correct
5. Run rollback: `python -c "from migrations.v2_02_create_organizations import rollback; rollback()"`
6. Verify: `psql $DATABASE_URL -c "\d organizations"` — should say "does not exist"
7. Re-run migrate (verify idempotent)
8. **Only then** deploy to prod

### 5.4 Reset staging branch (หลัง drill)

```bash
# Delete + recreate staging branch to match current prod state
neon branches delete staging-v2
neon branches create --name staging-v2 --parent production
```

---

## 6. Backup & PITR drill

### 6.1 Neon PITR enabled?

Neon **default มี 7-day PITR** (point-in-time restore) บน free tier; paid tier = 30 days.

**Verify:**
- Dashboard → Project → Settings → History retention
- ถ้าเป็น 7 days ขึ้นไป = OK สำหรับ pilot

### 6.2 Pre-migration snapshot procedure

**ทำก่อน apply prod migration ทุกครั้ง:**

```bash
# Option A: Create a Neon branch (cheap, instant)
neon branches create --name "pre-v2-$(date +%Y%m%d)" --parent production

# Option B: pg_dump (off-cloud backup)
pg_dump $DATABASE_URL -Fc -f "backup-pre-v2-$(date +%Y%m%d).dump"
# Stored on Pornthep's local disk or /Users/seal/Documents/GitHub/BP/backups/ (add to .gitignore)
```

**Option A (branch) is preferred** — instant, no download, and easy to restore by switching DATABASE_URL back.

### 6.3 Restore drill (ครั้งเดียว ก่อนเริ่ม migration)

**Do this at least once before first real migration to build confidence:**

1. สร้าง `pre-drill` branch: `neon branches create --name pre-drill --parent production`
2. Apply dummy migration: `psql <pre-drill_url> -c "CREATE TABLE _drill_test (id INT);"`
3. "Restore" = switch DATABASE_URL กลับไปที่ production: `export DATABASE_URL=<production_url>`
4. Verify: `psql $DATABASE_URL -c "\d _drill_test"` → "does not exist" (proof that production not affected)
5. Delete drill branch: `neon branches delete pre-drill`

**Writes down result ใน `plan/v2-asm-org-support/BACKUP_DRILL_<date>.md`**

---

## 7. Vercel serverless migration execution

### 7.1 Problem

Vercel serverless = no persistent process. `AUTO_CREATE_TABLES=true` triggers `Base.metadata.create_all()` ตอน cold start — แต่มันแค่สร้าง NEW tables, **ไม่ ALTER existing**.

ดังนั้น v2 migrations **ไม่สามารถรันได้ auto** บน Vercel — ต้องรัน manual บาง channel

### 7.2 Manual migration execution options

**Option A (recommended): Run locally เชื่อมต่อ Neon prod**
```bash
# Local terminal, pointed at Neon prod
export DATABASE_URL="<neon_prod_connection_string>"
python -m migrations.v2_02_create_organizations
# ... one by one, verifying after each
```

Pros: Easy to see output, easy to abort, no serverless timeout
Cons: Need prod connection string on local (secure how you handle it)

**Option B: Vercel CLI one-off execute**
```bash
vercel exec -- python -m migrations.v2_02_create_organizations
```
Note: Vercel free tier has 10-second function timeout — อาจไม่พอสำหรับ big migrations

**Option C: Dedicated migration endpoint (guarded)**
```python
# app/routers/admin.py — ADD to existing admin router
@router.post("/admin/migrations/run/{version}")
async def run_migration(version: str, current_user: User = Depends(require_superadmin)):
    # Extra guard: require feature flag
    if not ENABLE_V2_MIGRATIONS:
        raise HTTPException(403, "V2 migrations disabled")
    # Run specific migration
    import importlib
    mod = importlib.import_module(f"migrations.{version}")
    mod.migrate()
    return {"status": "ok", "version": version}
```
**Only enable when actively migrating, disable immediately after.**

**Recommendation: Option A for MVP.** Simpler, no code changes, full control.

### 7.3 Order of operations for prod migration day

1. Set ENABLE_ORG_MODE=false in Vercel (should already be)
2. Create Neon branch: `neon branches create --name "pre-v2-$(date +%Y%m%d)"`
3. Test migration ทั้งหมดบน staging-v2 branch ก่อน
4. Run migrations ทีละ script บน prod via Option A
5. After EACH script: verify via `psql` check schema matches expected
6. ถ้ามี issue → `python -c "from migrations.vX import rollback; rollback()"`
7. After all migrations done: set `ENABLE_ORG_MODE=true` (ยังไม่เปิดทันที — wait 24h observe)
8. If no issue after 24h: enable in UI + communicate

---

## 8. Checklist (sign off each before code phase)

- [ ] **Pre-flight queries** run, results saved ใน `PROD_SNAPSHOT_<date>.md`
- [ ] **Vercel env vars** `ENABLE_ORG_MODE`, `ENABLE_DUAL_WRITE_AUDIT`, `ENABLE_V2_MIGRATIONS` added to production
- [ ] **`app/utils/feature_flags.py`** file created + imported where needed
- [ ] **`migrations/v2_00_create_schema_migrations.py`** + `_helpers.py` created + tested on local SQLite
- [ ] **Neon staging branch** `staging-v2` exists, DATABASE_URL tested
- [ ] **Backup drill** completed, noted ใน `BACKUP_DRILL_<date>.md`
- [ ] **Migration execution plan** (Option A) agreed
- [ ] **Rollback procedure** tested on `v2_00` script (create → rollback → re-create)

**ห้าม** start code phase สำหรับ v2 migrations อื่น ๆ จนกว่า checklist ทั้งหมด ticked

---

**End of INFRASTRUCTURE_SETUP.md**
