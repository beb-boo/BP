
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import get_db
from ..models import User, AdminAuditLog
from ..schemas import (
    StandardResponse, AdminVerifyDoctorInput, AdminActionReasonInput, AdminAuditLogResponse
)
from ..utils.security import require_staff, verify_api_key
from ..utils.subscription import get_subscription_info
from ..utils.timezone import now_tz
import logging
import re
import uuid

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
logger = logging.getLogger(__name__)


def generate_request_id() -> str:
    return str(uuid.uuid4())


def mask_string(value: str | None, show_chars: int = 2) -> str | None:
    """Mask a string, showing only the first `show_chars` characters."""
    if not value:
        return None
    if len(value) <= show_chars:
        return value
    return value[:show_chars] + "***" + (value[-2:] if len(value) > 4 else "")


def mask_email(email: str | None) -> str | None:
    if not email:
        return None
    parts = email.split("@")
    if len(parts) != 2:
        return mask_string(email)
    local = parts[0]
    masked_local = local[:2] + "***" if len(local) > 2 else local
    return f"{masked_local}@{parts[1]}"


def sanitize_verification_logs(logs: str | None) -> str | None:
    """Strip internal details from verification logs for admin display.

    Supports two formats:
    - JSON (v3): structured dict with known safe fields
    - Legacy text: "Auto-Check at <time>: <message> - <details>"
    """
    if not logs:
        return None

    # Try JSON format first (v3 logs)
    try:
        import json
        data = json.loads(logs)
        if isinstance(data, dict):
            # Keep only safe fields for admin display
            safe_keys = {
                "checked_at", "version", "source", "found", "verified",
                "name_th", "name_en", "license_year", "specialties",
                "license_suspended", "suspension_detail", "result_count", "message",
            }
            sanitized = {k: v for k, v in data.items() if k in safe_keys}
            return json.dumps(sanitized, ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, TypeError):
        pass

    # Legacy text format fallback
    lines = logs.split("\n")
    clean = []
    for line in lines:
        if re.match(r"^\s*(Traceback|File |    |Exception|Error|HTTPError|requests\.)", line):
            continue
        line = re.sub(
            r"(Internal Error|TMC Website Error[^-]*|Ambiguous Result)\s*-\s*.+",
            r"\1 - [details redacted]",
            line,
        )
        line = re.sub(
            r"(Bot Auto-Check:.*?)\s*-\s*(Connection failed|Could not determine.*|Search returned.*)",
            r"\1",
            line,
        )
        clean.append(line)
    return "\n".join(clean).strip() or None


def user_to_admin_item(user: User) -> dict:
    """Convert User to masked admin-safe dict. No health data."""
    sub_info = get_subscription_info(user)
    return {
        "id": user.id,
        "role": user.role,
        "verification_status": user.verification_status,
        "is_active": user.is_active,
        "full_name_masked": mask_string(user.full_name, 4) or "(no name)",
        "email_masked": mask_email(user.email),
        "phone_masked": mask_string(user.phone_number, 3),
        "medical_license_masked": mask_string(user.medical_license, 2) if user.role == "doctor" else None,
        "subscription_tier": sub_info["subscription_tier"],
        "subscription_expires_at": sub_info["subscription_expires_at"],
        "created_at": str(user.created_at) if user.created_at else None,
        "last_login": str(user.last_login) if user.last_login else None,
    }


def log_action(db: Session, admin_id: int, action: str, target_id: int | None, details: str | None):
    """Add audit entry to session. Caller must commit."""
    entry = AdminAuditLog(
        admin_user_id=admin_id,
        action=action,
        target_user_id=target_id,
        details=details,
    )
    db.add(entry)


@router.get("/users", response_model=StandardResponse)
async def list_users(
    role: str | None = None,
    verification_status: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_staff),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """List users with filters. Masked PII. No health data."""
    request_id = generate_request_id()

    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if verification_status:
        query = query.filter(User.verification_status == verification_status)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    users = query.order_by(desc(User.created_at)).offset((page - 1) * per_page).limit(per_page).all()

    items = [user_to_admin_item(u) for u in users]

    return StandardResponse(
        status="success",
        message="Users retrieved",
        data={"users": items},
        meta={
            "current_page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
        },
        request_id=request_id,
    )


@router.get("/users/{user_id}", response_model=StandardResponse)
async def get_user_detail(
    user_id: int,
    current_user: User = Depends(require_staff),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Get single user detail (masked). Includes sanitized verification_logs for doctors."""
    request_id = generate_request_id()

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    data = user_to_admin_item(target)
    if target.role == "doctor":
        data["verification_logs"] = sanitize_verification_logs(target.verification_logs)

    return StandardResponse(
        status="success",
        message="User detail retrieved",
        data={"user": data},
        request_id=request_id,
    )


@router.get("/users/{user_id}/payments", response_model=StandardResponse)
async def get_user_payments(
    user_id: int,
    current_user: User = Depends(require_staff),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Get payment history for a user. Staff only."""
    from ..models import Payment
    request_id = generate_request_id()

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    payments = db.query(Payment).filter(
        Payment.user_id == user_id
    ).order_by(desc(Payment.created_at)).limit(50).all()

    data = []
    for p in payments:
        data.append({
            "id": p.id,
            "plan_type": p.plan_type,
            "amount": p.amount,
            "plan_amount": p.plan_amount,
            "status": p.status,
            "created_at": str(p.created_at) if p.created_at else None,
            "verified_at": str(p.verified_at) if p.verified_at else None,
        })

    return StandardResponse(
        status="success",
        message="Payment history retrieved",
        data={"payments": data},
        request_id=request_id,
    )


@router.post("/users/{user_id}/verify", response_model=StandardResponse)
async def verify_doctor(
    user_id: int,
    body: AdminVerifyDoctorInput,
    current_user: User = Depends(require_staff),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Verify or reject a doctor's license. Staff only. Atomic commit."""
    request_id = generate_request_id()

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.role != "doctor":
        raise HTTPException(status_code=400, detail="User is not a doctor")

    old_status = target.verification_status
    new_status = "verified" if body.action == "verify" else "rejected"

    target.verification_status = new_status
    target.verification_logs = (target.verification_logs or "") + \
        f"\n[{now_tz()}] Admin {current_user.id}: {old_status} -> {new_status}. Reason: {body.reason}"
    target.updated_at = now_tz()

    log_action(db, current_user.id, f"{body.action}_doctor", target.id,
               f"Status: {old_status} -> {new_status}. Reason: {body.reason}")
    db.commit()

    return StandardResponse(
        status="success",
        message=f"Doctor {new_status} successfully",
        data={"user_id": target.id, "verification_status": new_status},
        request_id=request_id,
    )


@router.post("/users/{user_id}/deactivate", response_model=StandardResponse)
async def deactivate_user(
    user_id: int,
    body: AdminActionReasonInput,
    current_user: User = Depends(require_staff),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Deactivate a user account. Staff only. Cannot target self or other staff."""
    request_id = generate_request_id()

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    if target.role == "staff":
        raise HTTPException(status_code=400, detail="Cannot deactivate another staff member via API")

    target.is_active = False
    target.updated_at = now_tz()

    log_action(db, current_user.id, "deactivate_user", target.id, f"Deactivated. Reason: {body.reason}")
    db.commit()

    return StandardResponse(
        status="success",
        message="User deactivated",
        data={"user_id": target.id},
        request_id=request_id,
    )


@router.post("/users/{user_id}/activate", response_model=StandardResponse)
async def activate_user(
    user_id: int,
    body: AdminActionReasonInput,
    current_user: User = Depends(require_staff),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Reactivate a deactivated user. Staff only. Cannot target other staff."""
    request_id = generate_request_id()

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.role == "staff" and target.id != current_user.id:
        raise HTTPException(status_code=400, detail="Cannot activate another staff member via API")

    target.is_active = True
    target.updated_at = now_tz()

    log_action(db, current_user.id, "activate_user", target.id, f"Reactivated. Reason: {body.reason}")
    db.commit()

    return StandardResponse(
        status="success",
        message="User activated",
        data={"user_id": target.id},
        request_id=request_id,
    )


@router.get("/audit-log", response_model=StandardResponse)
async def get_audit_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_staff),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """View admin audit log. Staff only."""
    request_id = generate_request_id()

    total = db.query(AdminAuditLog).count()
    entries = db.query(AdminAuditLog).order_by(
        desc(AdminAuditLog.created_at)
    ).offset((page - 1) * per_page).limit(per_page).all()

    data = [AdminAuditLogResponse.model_validate(e).model_dump() for e in entries]

    return StandardResponse(
        status="success",
        message="Audit log retrieved",
        data={"entries": data},
        meta={
            "current_page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
        },
        request_id=request_id,
    )
