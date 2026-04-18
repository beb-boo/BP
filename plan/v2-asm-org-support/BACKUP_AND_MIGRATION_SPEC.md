---
title: "Backup & Migration Spec — v1 Safety Net"
aliases:
  - "Backup Spec"
  - "Neon Branch Backup"
tags:
  - infrastructure
  - backup
  - neon
  - v2-asm-org
order: 0.7
status: draft
version: 1.0
updated: 2026-04-18
summary: "Admin web feature for creating Neon branch snapshots (instant safety backup) + documented local pg_dump procedure for offline SQL backups. Built BEFORE v2 migration work."
---

# Backup & Migration — v1 Safety Net

> **Purpose:** สร้าง safety mechanism สำหรับ production DB ปัจจุบัน (v1) **ก่อน** เริ่ม v2 migration
>
> **Scope:** Backup ระบบ v1 ปัจจุบันเท่านั้น — ถ้า v2 migration fail สามารถ restore ได้
>
> **Depends on:** Neon project API access
>
> **Blocks:** v2 migration work ทั้งหมด — อย่าเริ่ม v2 จนกว่าจะทำเสร็จ
>
> **Approach:** A+C (Neon branch instant backup + documented local pg_dump)

---

## 1. Decision summary

### 1.1 Why Neon branches (not Python dump / not external worker)

| Factor | Neon branch | Python dump | External worker (GitHub Action) |
|--------|:-----------:|:-----------:|:-----------:|
| Works on Vercel serverless (10-60s timeout) | ✅ API call < 2s | ❌ Timeout risk | ✅ |
| Instant restore | ✅ DATABASE_URL swap | ❌ psql restore | ❌ psql restore |
| Real SQL format compatibility | (via pg_dump step C) | ⚠️ Custom format | ✅ |
| Code complexity | 🟢 Low | 🟡 Medium | 🔴 High |
| Infra setup | 🟢 Neon API key only | 🟢 None | 🔴 GitHub secrets + S3 |
| Cost | Free (compute-hour when used) | Free | Free |
| Time to implement | ~2h | ~1-2 days | ~3-5 days |

**Decision:** **A+C combination**
- Admin web = Neon branch management UI
- Local terminal = `pg_dump` documentation (run when needed, not ใน web)

### 1.2 What this spec does NOT include

- ❌ **Restore/import UI** — ทำแค่ backup ยังไม่มี restore button (ป้องกันการ overwrite prod โดยไม่ตั้งใจ)
- ❌ **Scheduled auto-backup** — Phase 2 feature
- ❌ **S3/external storage upload** — Neon branches + local disk พอสำหรับ MVP
- ❌ **Backup ของ v2 schema** — v2 ยังไม่มี, สร้างภายหลังตอน v2 stable

---

## 2. Architecture

```
┌─────────────────────────────────────────────────┐
│  Admin Web (superadmin only)                     │
│  /admin/system/backups                           │
├─────────────────────────────────────────────────┤
│                                                  │
│  Widget 1: Create Branch Backup                 │
│  [+ สร้าง backup ตอนนี้]  → Neon API (server-side)│
│                                                  │
│  Widget 2: Active Backups (Neon branches)       │
│  ┌──────────────────────────────────────┐      │
│  │ pre-v2-migration-2026-04-18  [Delete]│      │
│  │ pre-release-2026-04-10       [Delete]│      │
│  └──────────────────────────────────────┘      │
│                                                  │
│  Widget 3: Local pg_dump Guide                  │
│  - step-by-step instructions                    │
│  - connection string format                     │
│  - restore procedure                            │
│                                                  │
└─────────────────────────────────────────────────┘
           ↓ (backend API call)
┌─────────────────────────────────────────────────┐
│  Vercel Backend (FastAPI)                        │
│  POST /api/v1/admin/system/backups              │
├─────────────────────────────────────────────────┤
│                                                  │
│  app/routers/admin_system.py                    │
│  app/services/neon_branch_service.py            │
│  ↓ HTTPS (Bearer NEON_API_KEY)                  │
│                                                  │
└─────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────┐
│  Neon Console API                                │
│  console.neon.tech/api/v2/projects/{id}/branches│
│  - POST   create branch                         │
│  - GET    list branches                         │
│  - DELETE delete branch                         │
└─────────────────────────────────────────────────┘
```

---

## 3. Frontend spec — Admin Web Page

### 3.1 Route

`/admin/system/backups` — **superadmin only** (not rpsst_admin)

### 3.2 Guard

- Check user role (legacy `role="staff"` OR new `primary_role=superadmin` via `get_effective_role()`)
- Non-superadmin → 403 with message "เฉพาะ superadmin เท่านั้น"

### 3.3 Page layout

```
┌────────────────────────────────────────────┐
│ [←] Backup & Migration                     │
├────────────────────────────────────────────┤
│                                            │
│ ⚠ สำคัญ: หน้านี้จัดการ database snapshots    │
│    ของ production ทุก action ถูก log       │
│                                            │
│ ─── สร้าง Backup ───────────────────────── │
│                                            │
│ ชื่อ backup (optional):                      │
│ [pre-v2-migration-2026-04-18          ]    │
│                                            │
│ คำอธิบาย (เพิ่มใน description field):        │
│ [Before v2 ASM migration            ]      │
│                                            │
│ [+ สร้าง Backup ตอนนี้]                    │
│                                            │
│ ─── Backup ที่มีอยู่ (Neon branches) ──── │
│                                            │
│ ┌─────────────────────────────────────┐  │
│ │ pre-v2-migration-2026-04-18         │  │
│ │ สร้างเมื่อ: 5 นาทีที่แล้ว              │  │
│ │ ขนาด: 42 MB                           │  │
│ │ Status: ● Ready                       │  │
│ │ [ดูรายละเอียด] [ลบ]                   │  │
│ └─────────────────────────────────────┘  │
│                                            │
│ ┌─────────────────────────────────────┐  │
│ │ production (branch หลัก, ห้ามลบ)    │  │
│ │ อัปเดตล่าสุด: เมื่อครู่             │  │
│ │ ขนาด: 42 MB                           │  │
│ │ Status: ● Active                      │  │
│ └─────────────────────────────────────┘  │
│                                            │
│ ─── Local SQL Backup (pg_dump) ────────── │
│                                            │
│ วิธี download backup เป็นไฟล์ .sql:           │
│ [แสดง step-by-step guide ▼]               │
│                                            │
└────────────────────────────────────────────┘
```

### 3.4 Create Backup modal

เมื่อกดปุ่ม "+ สร้าง Backup ตอนนี้":

```
┌─────────────────────────────────┐
│  ยืนยันการสร้าง backup              │
├─────────────────────────────────┤
│                                  │
│ จะสร้าง Neon branch ใหม่จาก      │
│ production branch                │
│                                  │
│ ชื่อ: pre-v2-migration-2026-04-18│
│ ต้นทาง: production              │
│ ขนาด DB ปัจจุบัน: ~42 MB        │
│                                  │
│ ข้อควรรู้:                        │
│ - Branch จะถูก free compute      │
│   (เก็บข้อมูลแต่ไม่กิน compute) │
│ - คิด storage cost เท่า prod    │
│ - เวลา restore: swap DATABASE_URL│
│                                  │
│ พิมพ์ "CREATE" เพื่อยืนยัน:       │
│ [_____________________________]  │
│                                  │
│ [ยกเลิก]   [สร้าง Backup]        │
└─────────────────────────────────┘
```

- Typed confirmation ("CREATE") ป้องกัน accidental click

### 3.5 Delete Backup modal

เมื่อกดปุ่ม "ลบ":

```
┌─────────────────────────────────┐
│  ยืนยันการลบ backup               │
├─────────────────────────────────┤
│                                  │
│ จะลบ Neon branch:                │
│ pre-v2-migration-2026-04-18      │
│                                  │
│ ⚠ ไม่สามารถกู้คืนได้             │
│                                  │
│ พิมพ์ชื่อ branch เพื่อยืนยัน:      │
│ [_____________________________]  │
│                                  │
│ [ยกเลิก]   [ลบ Branch]           │
└─────────────────────────────────┘
```

- Must type exact branch name (case-sensitive) ป้องกัน typo deletion

### 3.6 Local pg_dump guide (expandable section)

```markdown
## วิธี Download SQL dump (manual, บน local terminal)

Admin web สามารถสร้าง Neon branch snapshots ได้ แต่ **ไม่** download
ไฟล์ SQL ตรง ๆ เนื่องจากข้อจำกัดของ Vercel serverless

ถ้าคุณต้องการไฟล์ `.sql` สำรองไว้บน local disk:

### ขั้นตอน

1. **Install PostgreSQL client tools** (ถ้ายังไม่มี):
   - macOS: `brew install libpq` (+ `echo 'export PATH="/opt/homebrew/opt/libpq/bin:$PATH"' >> ~/.zshrc`)
   - Linux: `sudo apt install postgresql-client`
   - Windows: download from postgresql.org

2. **Copy connection string จาก Neon Console:**
   - ไปที่ Neon Console → Project → Branches
   - เลือก branch ที่ต้องการ dump (เช่น `pre-v2-migration-...`)
   - กด Connect → copy connection string

3. **Run pg_dump บน terminal:**

   ```bash
   # Backup production (full, with schema + data)
   pg_dump "postgresql://user:pass@ep-xxx.neon.tech/neondb" \
     --no-owner --no-acl \
     -Fc \
     -f backup-$(date +%Y%m%d-%H%M).dump
   
   # หรือเป็น SQL text (human-readable):
   pg_dump "postgresql://user:pass@ep-xxx.neon.tech/neondb" \
     --no-owner --no-acl \
     -f backup-$(date +%Y%m%d-%H%M).sql
   ```

4. **เก็บไฟล์ใน secure location** — ห้าม commit ไปใน git (contains PII)
   - แนะนำ: external disk encrypted, หรือ password-protected archive
   - ห้าม: Google Drive/Dropbox โดยไม่มี encryption layer

### ขั้นตอน Restore

```bash
# Restore จาก .dump (custom format)
pg_restore --dbname="postgresql://..." --no-owner --no-acl backup.dump

# Restore จาก .sql (text format)
psql "postgresql://..." < backup.sql
```

### ⚠ Security checklist หลัง backup

- [ ] ไฟล์ backup มี PII — encrypt หรือ เก็บ offline เท่านั้น
- [ ] ห้าม upload ไป cloud storage ที่ไม่ได้ encrypt
- [ ] ลบไฟล์เมื่อไม่จำเป็นแล้ว (`shred -u backup.sql` บน Linux)
- [ ] Audit log ใน admin web จะบันทึก **timestamp** ของการสร้าง branch
  แต่**ไม่** log การ pg_dump local (ไม่ visible ใน system)
```

### 3.7 Frontend implementation notes

- ใช้ shadcn/ui เดิม (Dialog, Card, Button, Input)
- Use TanStack Query สำหรับ list branches (auto-refresh every 30s ถ้าเปิดหน้าอยู่)
- Typed confirmations: controlled input + disable button until text matches

---

## 4. Backend spec — API endpoints

### 4.1 Environment variables (new)

เพิ่มใน Vercel prod env:

```bash
NEON_API_KEY=<64-bit-token-from-neon-console>
NEON_PROJECT_ID=<project-id-from-neon>
```

**Note:** API key ต้องเก็บเฉพาะ server-side (ห้าม expose ไป frontend)

### 4.2 New file: `app/services/neon_service.py`

```python
"""
Neon Console API client for managing branches (backups).
Only for use by superadmin endpoints.
"""
import os
import httpx
import logging
from typing import Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

NEON_API_BASE = "https://console.neon.tech/api/v2"
NEON_API_KEY = os.getenv("NEON_API_KEY")
NEON_PROJECT_ID = os.getenv("NEON_PROJECT_ID")


def _ensure_configured():
    if not NEON_API_KEY or not NEON_PROJECT_ID:
        raise HTTPException(
            500,
            "Neon API not configured. Set NEON_API_KEY and NEON_PROJECT_ID."
        )


async def list_branches() -> list[dict]:
    """List all branches in the project."""
    _ensure_configured()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{NEON_API_BASE}/projects/{NEON_PROJECT_ID}/branches",
            headers={"Authorization": f"Bearer {NEON_API_KEY}"}
        )
    if resp.status_code != 200:
        logger.error(f"Neon list_branches failed: {resp.status_code} {resp.text}")
        raise HTTPException(502, f"Neon API error: {resp.status_code}")
    return resp.json().get("branches", [])


async def get_production_branch_id() -> str:
    """Find the production (default) branch ID."""
    branches = await list_branches()
    for b in branches:
        if b.get("default") is True:
            return b["id"]
    raise HTTPException(500, "No default branch found")


async def create_branch(
    name: str,
    parent_branch_id: Optional[str] = None
) -> dict:
    """Create a new branch from the parent (default=production)."""
    _ensure_configured()
    
    if not parent_branch_id:
        parent_branch_id = await get_production_branch_id()
    
    payload = {
        "branch": {
            "name": name,
            "parent_id": parent_branch_id
        }
        # No endpoint = compute stays stopped, cheaper
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{NEON_API_BASE}/projects/{NEON_PROJECT_ID}/branches",
            headers={
                "Authorization": f"Bearer {NEON_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
    
    if resp.status_code not in (200, 201):
        logger.error(f"Neon create_branch failed: {resp.status_code} {resp.text}")
        raise HTTPException(502, f"Neon API error: {resp.status_code}")
    
    return resp.json()


async def delete_branch(branch_id: str) -> None:
    """Delete a branch by ID. Will fail if branch is default or has children."""
    _ensure_configured()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{NEON_API_BASE}/projects/{NEON_PROJECT_ID}/branches/{branch_id}",
            headers={"Authorization": f"Bearer {NEON_API_KEY}"}
        )
    if resp.status_code not in (200, 202):
        logger.error(f"Neon delete_branch failed: {resp.status_code} {resp.text}")
        raise HTTPException(502, f"Neon API error: {resp.status_code}")
```

### 4.3 New router: `app/routers/admin_system.py`

```python
"""
System-level admin endpoints (superadmin only).
Currently: backup/branch management.
"""
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from ..database import get_db
from ..models import User
from ..utils.security import get_current_user
from ..services import neon_service
# In v1.1+: from ..utils.permissions import get_effective_role, UserRole

router = APIRouter(prefix="/api/v1/admin/system", tags=["admin-system"])


def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    """Guard: only superadmin (legacy role='staff' OR primary_role='superadmin')."""
    # During v1 → v2 transition, check both columns
    is_superadmin = False
    if getattr(current_user, "primary_role", None) == "superadmin":
        is_superadmin = True
    elif current_user.role == "staff":
        # Legacy: env-managed staff (superadmin equivalent per v1.1 decision 4.2)
        is_superadmin = True
    
    if not is_superadmin:
        raise HTTPException(403, "Superadmin access required")
    return current_user


class CreateBackupRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=64)
    description: str = Field(default="", max_length=500)


# Allow only lowercase alphanumeric + hyphen in branch name
BRANCH_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


@router.get("/backups")
async def list_backups(
    current_user: User = Depends(require_superadmin)
):
    """List all branches (= backups) in the Neon project."""
    branches = await neon_service.list_branches()
    
    # Audit log (v1 legacy admin_audit_logs; v1.1+ writes to both)
    # TODO: integrate audit logging
    
    return {
        "branches": [
            {
                "id": b["id"],
                "name": b["name"],
                "is_default": b.get("default", False),
                "created_at": b.get("created_at"),
                "updated_at": b.get("updated_at"),
                "parent_id": b.get("parent_id"),
                "logical_size_bytes": b.get("logical_size"),
                "current_state": b.get("current_state"),
            }
            for b in branches
        ]
    }


@router.post("/backups")
async def create_backup(
    body: CreateBackupRequest,
    current_user: User = Depends(require_superadmin)
):
    """Create a new Neon branch from production (= snapshot backup)."""
    # Validate branch name format (Neon requires lowercase alnum + hyphen)
    if not BRANCH_NAME_PATTERN.match(body.name):
        raise HTTPException(
            422,
            "Branch name must be lowercase alphanumeric + hyphen, 3-64 chars, "
            "starting with letter/digit"
        )
    
    # Create branch
    result = await neon_service.create_branch(name=body.name)
    
    # Audit log
    # TODO: audit_log("system_backup_created", actor=current_user, 
    #                 metadata={"branch_name": body.name, "description": body.description})
    
    return {
        "success": True,
        "branch": result.get("branch", {}),
        "message": f"Branch '{body.name}' created successfully"
    }


@router.delete("/backups/{branch_id}")
async def delete_backup(
    branch_id: str,
    current_user: User = Depends(require_superadmin)
):
    """Delete a Neon branch. Fails if branch is default or has children."""
    # Prevent deletion of production/default branch
    production_id = await neon_service.get_production_branch_id()
    if branch_id == production_id:
        raise HTTPException(400, "Cannot delete default (production) branch")
    
    await neon_service.delete_branch(branch_id)
    
    # Audit log
    # TODO: audit_log("system_backup_deleted", actor=current_user,
    #                 metadata={"branch_id": branch_id})
    
    return {"success": True, "message": "Branch deleted"}
```

### 4.4 Wire into main.py

```python
# app/main.py additions
from .routers import admin_system  # NEW

app.include_router(admin_system.router)
```

### 4.5 Rate limiting

- `POST /backups`: max 5/hour per superadmin (anti-abuse, Neon has its own limits too)
- `DELETE /backups/{id}`: max 5/hour per superadmin
- `GET /backups`: max 30/min (for UI polling)

Implementation: use existing rate limit middleware if present, or add simple Redis-based counter.

---

## 5. Security considerations

### 5.1 API key handling

- `NEON_API_KEY` เก็บใน Vercel env vars only (ห้าม commit)
- ห้าม expose ไป frontend (all Neon API calls ผ่าน backend)
- Rotate key ทุก 6 เดือน (หรือเมื่อสงสัยว่า compromise)

### 5.2 Authorization

- **Only superadmin** can access `/api/v1/admin/system/*` endpoints
- Use dual-check: `role="staff"` (legacy) OR `primary_role="superadmin"` (v2)
- All endpoints log `actor_user_id` + action

### 5.3 Branch name validation

- Restrict pattern: `^[a-z0-9][a-z0-9-]{2,63}$` (Neon's own restriction)
- Prevent injection via special characters
- Prevent names starting with `-` (CLI gotcha)

### 5.4 Audit logging

Every action MUST be logged:

| Action | Metadata |
|--------|----------|
| `system_backup_list` | - |
| `system_backup_created` | `{branch_name, description}` |
| `system_backup_deleted` | `{branch_id, branch_name}` |

Store in `admin_audit_logs` (v1) — will migrate to `audit_logs` dual-write ใน v2

### 5.5 What this feature does NOT do (by design)

- ❌ **Expose connection strings** of backup branches in UI — prevents credential leak
- ❌ **Auto-download backup file** — prevents large file exfiltration
- ❌ **Allow non-superadmin access** — scope by least privilege
- ❌ **Restore/import** — separate tool later (too risky for MVP)

---

## 6. Testing checklist

### 6.1 Unit tests

- [ ] `neon_service.list_branches()` parses response correctly
- [ ] `neon_service.create_branch()` with/without parent_id
- [ ] `neon_service.delete_branch()` handles error codes
- [ ] `require_superadmin` rejects regular admin/doctor/patient
- [ ] Branch name validation rejects invalid characters
- [ ] Delete protection on default branch

### 6.2 Integration tests (manual, on staging)

- [ ] Neon API credentials valid → list branches returns production
- [ ] Create branch → appears in Neon Console
- [ ] Delete branch → removed from Neon Console
- [ ] Non-superadmin → 403
- [ ] Invalid branch name → 422

### 6.3 Production drill (before v2 migration)

- [ ] Create real backup branch: `pre-v2-baseline-<date>`
- [ ] Verify it exists in Neon Console
- [ ] Simulate restore: change DATABASE_URL to branch → app still works
- [ ] Change back to production
- [ ] Run local `pg_dump` of production → get .dump file → verify with `pg_restore --list`
- [ ] Store .dump file encrypted on external disk
- [ ] Delete test branch

---

## 7. Implementation checklist

### 7.1 Backend

- [ ] Add `NEON_API_KEY` + `NEON_PROJECT_ID` to Vercel env
- [ ] Create `app/services/neon_service.py`
- [ ] Create `app/routers/admin_system.py`
- [ ] Wire `admin_system.router` into `app/main.py`
- [ ] Add rate limiting (if not using global middleware)
- [ ] Add httpx to requirements.txt (if not present)
- [ ] Unit tests for neon_service

### 7.2 Frontend

- [ ] Create `frontend/app/admin/system/backups/page.tsx`
- [ ] Component: `BackupList` (uses TanStack Query for listing)
- [ ] Component: `CreateBackupDialog` (with typed "CREATE" confirm)
- [ ] Component: `DeleteBackupDialog` (with typed branch name confirm)
- [ ] Component: `LocalPgDumpGuide` (expandable markdown section)
- [ ] Update `/admin/layout.tsx` navigation to include "System" group (superadmin only)
- [ ] i18n: Thai strings for all labels

### 7.3 Documentation

- [ ] Add section ใน CLAUDE.md: "Backup operations"
- [ ] Add `docs/operations/backup-runbook.md` — how to create backup + restore
- [ ] Update `docs/operations/` with emergency restore procedure

### 7.4 Pre-deployment verification

- [ ] Test on local (with NEON_PROJECT_ID pointing to Neon dev/test project)
- [ ] Deploy to preview Vercel → test on staging Neon branch
- [ ] Deploy to production
- [ ] Create first real backup + verify

---

## 8. Operational runbook (summary)

### 8.1 Before v2 migration

1. **Superadmin login** → go to `/admin/system/backups`
2. Click "+ สร้าง Backup ตอนนี้"
3. Name: `pre-v2-migration-<YYYY-MM-DD>` (e.g. `pre-v2-migration-2026-04-25`)
4. Description: `Before v2 ASM migration`
5. Type "CREATE" to confirm
6. Wait ~5-10 seconds for Neon to provision branch
7. Verify branch appears in list
8. **Optional but recommended:** run local `pg_dump` to get .sql file (offline copy)

### 8.2 If v2 migration fails

**Option A: Rollback via Neon branch (fast, ~1 min)**

1. In Vercel dashboard → Settings → Environment Variables
2. Edit `DATABASE_URL` → change `ep-prod-xxx` to `ep-backup-xxx` (from backup branch)
3. Redeploy (trigger new deployment)
4. Production now runs off backup branch
5. Investigate migration failure offline
6. Fix → try migration again on new branch

**Option B: Restore via pg_dump (if branches lost)**

1. Create new Neon project or use existing
2. `pg_restore --dbname="..." backup.dump` on local terminal
3. Update Vercel DATABASE_URL to new DB
4. Redeploy

### 8.3 Cleanup after successful v2

1. Wait 7-14 days (monitoring period) before deleting backup
2. Confirm prod stable → delete backup branches via UI
3. Keep 1-2 recent backups as rolling safety

---

## 9. Cost implications (Neon)

### 9.1 Neon pricing (Launch plan — usage-based)

- **Storage**: $0.35/GB-month (size of branch snapshot)
- **Compute**: $0.16/compute-hour (only when branch is queried; stays $0 if idle)
- **Data transfer**: small amounts free

### 9.2 Estimate for typical BP Monitor

- DB size v1 prod: ~42 MB (estimated)
- Backup branch (idle): ~$0.015/month (42 MB × $0.35/GB)
- With 3-4 rolling backups: ~$0.06/month = **negligible**

### 9.3 Cost control rules

- UI shows branch size + age
- Prune branches older than 30 days (manual, via UI)
- Delete after successful v2 migration (keep only 1-2 recent)

---

## 10. Out of scope (Phase 2+)

- Scheduled auto-backup (cron)
- Upload backup SQL file to S3/R2/external
- Restore/import from backup via UI (too risky)
- Multi-region backup
- Backup of sensitive-field-only (not all data)
- Backup verification (auto-restore test on fresh branch)
- Backup encryption at rest (Neon already encrypts)

---

## 11. Relationship to v2 migration

This backup feature is **prerequisite** for v2 migration:

```
v2 Migration Day:
  1. Superadmin creates backup: `pre-v2-migration-2026-04-25`
  2. Verify backup accessible via Neon Console
  3. OPTIONAL: local pg_dump → offline copy
  4. Run v2 migrations (per MIGRATION_STRATEGY.md)
  5. If fail → rollback via DATABASE_URL swap
  6. If success → wait 7 days → delete backup branch
```

See [[MIGRATION_STRATEGY]] §5 for full cutover sequence.

---

**End of BACKUP_AND_MIGRATION_SPEC.md**
