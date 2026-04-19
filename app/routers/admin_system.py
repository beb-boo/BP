"""System-level admin endpoints (superadmin only).

Currently scoped to Neon branch backup management per
`plan/v2-asm-org-support/BACKUP_AND_MIGRATION_SPEC.md`.

During the v1 → v2 transition the guard accepts:
  - legacy `role == "staff"` (env-managed superadmin equivalent), OR
  - new `primary_role == "superadmin"` (v2, once ORG_FOUNDATION lands).

All state-changing actions write to `admin_audit_logs` atomically with the
corresponding Neon call.
"""

import json
import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AdminAuditLog, User
from ..schemas import StandardResponse
from ..services import neon_service
from ..utils.security import get_current_user, is_staff_access_allowed, verify_api_key

router = APIRouter(prefix="/api/v1/admin/system", tags=["admin-system"])
logger = logging.getLogger(__name__)


# Neon's own constraint: lowercase alnum + hyphen, 3-64 chars, starting with alnum.
BRANCH_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    """Guard: legacy `role='staff'` OR new `primary_role='superadmin'`."""
    is_superadmin = False
    if getattr(current_user, "primary_role", None) == "superadmin":
        is_superadmin = True
    elif current_user.role == "staff":
        is_superadmin = True

    if not is_superadmin:
        raise HTTPException(status_code=403, detail="Superadmin access required")

    # Respect STAFF_ALLOWLIST for legacy-staff superadmins.
    if current_user.role == "staff" and not is_staff_access_allowed(current_user):
        raise HTTPException(status_code=403, detail="Superadmin access denied")

    return current_user


def _request_id() -> str:
    return str(uuid.uuid4())


def _audit(db: Session, admin_id: int, action: str, metadata: dict) -> None:
    """Append an audit row. Caller must commit."""
    db.add(
        AdminAuditLog(
            admin_user_id=admin_id,
            action=action,
            target_user_id=None,
            details=json.dumps(metadata, ensure_ascii=False),
        )
    )


def _branch_to_dict(b: dict) -> dict:
    return {
        "id": b.get("id"),
        "name": b.get("name"),
        "is_default": bool(b.get("default", False)),
        "protected": bool(b.get("protected", False)),
        "parent_id": b.get("parent_id"),
        "parent_lsn": b.get("parent_lsn"),
        "current_state": b.get("current_state"),
        "logical_size_bytes": b.get("logical_size"),
        "created_at": b.get("created_at"),
        "updated_at": b.get("updated_at"),
    }


class CreateBackupRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=64)
    description: str = Field(default="", max_length=500)


# ─────────────────────────────────────────────────────────────
# GET /api/v1/admin/system/backups
# ─────────────────────────────────────────────────────────────
@router.get("/backups", response_model=StandardResponse)
async def list_backups(
    current_user: User = Depends(require_superadmin),
    _api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """List all Neon branches = available backups."""
    request_id = _request_id()
    branches = await neon_service.list_branches()

    _audit(
        db,
        current_user.id,
        "system_backup_list",
        {"count": len(branches)},
    )
    db.commit()

    return StandardResponse(
        status="success",
        message="Backups retrieved",
        data={"branches": [_branch_to_dict(b) for b in branches]},
        meta={"total": len(branches)},
        request_id=request_id,
    )


# ─────────────────────────────────────────────────────────────
# POST /api/v1/admin/system/backups
# ─────────────────────────────────────────────────────────────
@router.post("/backups", response_model=StandardResponse)
async def create_backup(
    body: CreateBackupRequest,
    current_user: User = Depends(require_superadmin),
    _api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Create a new Neon branch from the default branch (= snapshot backup)."""
    request_id = _request_id()

    if not BRANCH_NAME_PATTERN.match(body.name):
        raise HTTPException(
            status_code=422,
            detail=(
                "Branch name must be lowercase alphanumeric + hyphen, 3-64 chars, "
                "starting with a letter or digit."
            ),
        )

    result = await neon_service.create_branch(name=body.name)
    branch = result.get("branch", {}) if isinstance(result, dict) else {}

    _audit(
        db,
        current_user.id,
        "system_backup_created",
        {
            "branch_name": body.name,
            "branch_id": branch.get("id"),
            "description": body.description,
        },
    )
    db.commit()

    return StandardResponse(
        status="success",
        message=f"Branch '{body.name}' created successfully",
        data={"branch": _branch_to_dict(branch)},
        request_id=request_id,
    )


# ─────────────────────────────────────────────────────────────
# DELETE /api/v1/admin/system/backups/{branch_id}
# ─────────────────────────────────────────────────────────────
@router.delete("/backups/{branch_id}", response_model=StandardResponse)
async def delete_backup(
    branch_id: str,
    current_user: User = Depends(require_superadmin),
    _api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Delete a Neon branch. Refuses to delete the default (production) branch."""
    request_id = _request_id()

    # Lookup current branches so we can (a) protect the default branch and
    # (b) record the branch name in the audit log.
    branches = await neon_service.list_branches()
    target = next((b for b in branches if b.get("id") == branch_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Branch not found")
    if target.get("default"):
        raise HTTPException(status_code=400, detail="Cannot delete the default (production) branch")
    if target.get("protected"):
        raise HTTPException(status_code=400, detail="Cannot delete a protected branch")

    await neon_service.delete_branch(branch_id)

    _audit(
        db,
        current_user.id,
        "system_backup_deleted",
        {"branch_id": branch_id, "branch_name": target.get("name")},
    )
    db.commit()

    return StandardResponse(
        status="success",
        message="Branch deleted",
        data={"branch_id": branch_id},
        request_id=request_id,
    )


# ─────────────────────────────────────────────────────────────
# GET /api/v1/admin/system/audit-log
# ─────────────────────────────────────────────────────────────
@router.get("/audit-log", response_model=StandardResponse)
async def system_audit_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_superadmin),
    _api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Return audit entries for system_backup_* actions."""
    request_id = _request_id()

    q = db.query(AdminAuditLog).filter(AdminAuditLog.action.like("system_backup_%"))
    total = q.count()
    entries = (
        q.order_by(desc(AdminAuditLog.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    data = [
        {
            "id": e.id,
            "admin_user_id": e.admin_user_id,
            "action": e.action,
            "details": e.details,
            "created_at": str(e.created_at) if e.created_at else None,
        }
        for e in entries
    ]

    return StandardResponse(
        status="success",
        message="System audit log retrieved",
        data={"entries": data},
        meta={
            "current_page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
        },
        request_id=request_id,
    )
