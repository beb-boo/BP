"""Payment API Router"""
import logging
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Payment
from ..schemas import StandardResponse
from ..utils.security import verify_api_key, get_current_user
from ..utils.subscription import get_subscription_info
from ..utils.rate_limiter import limiter
from ..services.payment_service import verify_and_upgrade, PaymentError
from ..config.pricing import SUBSCRIPTION_PLANS, PAYMENT_ACCOUNT

router = APIRouter(prefix="/api/v1/payment", tags=["payment"])
logger = logging.getLogger(__name__)


@router.get("/plans")
async def get_subscription_plans(
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """ดูแพลน subscription และสถานะปัจจุบัน / Get subscription plans"""

    lang = current_user.language or "th"

    plans_response = []
    for k, v in SUBSCRIPTION_PLANS.items():
        plan_data = v.copy()
        feat_list = v["features"].get(lang, v["features"]["th"])
        plan_data["features"] = feat_list
        plans_response.append({"plan_type": k, **plan_data})

    # Localize Bank Name
    account_data = PAYMENT_ACCOUNT.copy()
    if lang == "en" and "bank_en" in account_data:
        account_data["bank"] = account_data["bank_en"]

    # Normalized subscription state
    sub_info = get_subscription_info(current_user)

    return StandardResponse(
        status="success",
        message="Subscription plans retrieved",
        data={
            "plans": plans_response,
            "payment_account": account_data,
            "current_tier": sub_info["subscription_tier"],
            "is_active": sub_info["is_premium_active"],
            "expires_at": sub_info["subscription_expires_at"],
            "days_remaining": sub_info["days_remaining"],
            "language": lang
        }
    )


@router.post("/verify-slip")
@limiter.limit("3/minute")
async def verify_payment_slip(
    request: Request,
    plan_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """อัพโหลดและตรวจสอบสลิปการชำระเงิน / Verify Slip"""

    lang = current_user.language or "th"

    # HTTP-layer validation: file type & size
    if not file.content_type or not file.content_type.startswith("image/"):
        msg = "Please upload an image file" if lang == "en" else "กรุณาอัพโหลดไฟล์รูปภาพ"
        raise HTTPException(status_code=400, detail=msg)

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB
        msg = "File too large (>10MB)" if lang == "en" else "ไฟล์ใหญ่เกินไป (สูงสุด 10MB)"
        raise HTTPException(status_code=413, detail=msg)

    # Delegate to shared payment service
    try:
        result = verify_and_upgrade(db, current_user, content, plan_type, lang)
    except PaymentError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    msg_success = (
        "Payment Successful! Upgraded to Premium."
        if lang == "en"
        else "ชำระเงินสำเร็จ! อัพเกรดเป็น Premium แล้ว"
    )

    return StandardResponse(
        status="success",
        message=msg_success,
        data=result
    )


@router.get("/history")
async def get_payment_history(
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """ดูประวัติการชำระเงิน / Payment History"""
    payments = db.query(Payment).filter(
        Payment.user_id == current_user.id
    ).order_by(Payment.created_at.desc()).limit(50).all()

    history = [{
        "id": p.id,
        "plan_type": p.plan_type,
        "amount": p.amount,
        "status": p.status,
        "trans_date": p.trans_date,
        "created_at": str(p.created_at),
        "verified_at": str(p.verified_at) if p.verified_at else None
    } for p in payments]

    return StandardResponse(
        status="success",
        message="Payment history retrieved",
        data={"payments": history}
    )


@router.get("/status")
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """ดูสถานะ subscription ปัจจุบัน / Status"""

    sub_info = get_subscription_info(current_user)

    return StandardResponse(
        status="success",
        message="Subscription status retrieved",
        data={
            "tier": sub_info["subscription_tier"],
            "is_active": sub_info["is_premium_active"],
            "expires_at": sub_info["subscription_expires_at"],
            "days_remaining": sub_info["days_remaining"],
            "features": {
                "max_records": "unlimited" if sub_info["is_premium_active"] else 30,
                "history_days": "unlimited" if sub_info["is_premium_active"] else 30
            }
        }
    )
