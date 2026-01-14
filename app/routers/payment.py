"""Payment API Router"""
import logging
import uuid
import json
from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..database import get_db
from ..models import User, Payment
from ..schemas import StandardResponse
from ..utils.security import verify_api_key, get_current_user, now_th
from ..utils.encryption import encrypt_value, hash_value
from ..services.slipok import slipok_service
from ..config.pricing import SUBSCRIPTION_PLANS, PAYMENT_ACCOUNT, get_plan, is_valid_amount

router = APIRouter(prefix="/api/v1/payment", tags=["payment"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.get("/plans")
async def get_subscription_plans(
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """ดูแพลน subscription และสถานะปัจจุบัน / Get subscription plans"""
    
    # Filter features based on user language
    lang = current_user.language or "th"
    
    plans_response = []
    for k, v in SUBSCRIPTION_PLANS.items():
        plan_data = v.copy()
        # Select localized features
        feat_list = v["features"].get(lang, v["features"]["th"])
        plan_data["features"] = feat_list
        plans_response.append({"plan_type": k, **plan_data})

    # Localize Bank Name
    account_data = PAYMENT_ACCOUNT.copy()
    if lang == "en" and "bank_en" in account_data:
        account_data["bank"] = account_data["bank_en"]

    return StandardResponse(
        status="success",
        message="Subscription plans retrieved",
        data={
            "plans": plans_response,
            "payment_account": account_data,
            "current_tier": current_user.subscription_tier,
            "expires_at": str(current_user.subscription_expires_at) if current_user.subscription_expires_at else None,
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

    # Validate plan
    plan = get_plan(plan_type)
    if not plan:
        msg = "Invalid plan" if lang == "en" else "แพลนไม่ถูกต้อง"
        raise HTTPException(status_code=400, detail=msg)

    # Check SlipOK service
    if not slipok_service.api_key:
         msg = "Payment system unavailable" if lang == "en" else "ระบบตรวจสอบไม่พร้อมใช้งาน"
         raise HTTPException(status_code=503, detail=msg)

    # Validate file
    if not file.content_type or not file.content_type.startswith("image/"):
        msg = "Please upload an image file" if lang == "en" else "กรุณาอัพโหลดไฟล์รูปภาพ"
        raise HTTPException(status_code=400, detail=msg)

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB
        msg = "File too large (>10MB)" if lang == "en" else "ไฟล์ใหญ่เกินไป (สูงสุด 10MB)"
        raise HTTPException(status_code=413, detail=msg)

    # Verify with SlipOK
    expected_amount = plan["price"]
    result = slipok_service.verify_slip_image(content, expected_amount, language=lang)

    if not result.success:
        # Log failed attempt
        payment = Payment(
            user_id=current_user.id,
            trans_ref=f"FAILED-{uuid.uuid4()}",
            trans_ref_hash=hash_value(f"FAILED-{uuid.uuid4()}-{now_th()}"),
            amount=0,
            plan_type=plan_type,
            plan_amount=expected_amount,
            status="failed",
            error_code=result.error_code,
            error_message=result.error_message,
            verification_response=json.dumps(result.raw_response) if result.raw_response else None
        )
        db.add(payment)
        db.commit()

        raise HTTPException(status_code=400, detail=result.error_message)

    # Check duplicate trans_ref in our DB
    trans_ref_hash = hash_value(result.trans_ref)
    existing = db.query(Payment).filter(
        Payment.trans_ref_hash == trans_ref_hash,
        Payment.status == "verified"
    ).first()

    if existing:
        msg = "Slip already used" if lang == "en" else "สลิปนี้เคยใช้ชำระเงินแล้ว"
        raise HTTPException(status_code=409, detail=msg)

    # Verify amount
    if not is_valid_amount(expected_amount, result.amount):
        msg = f"Amount mismatch ({result.amount} vs {expected_amount})" if lang == "en" \
              else f"ยอดเงิน ({result.amount} บาท) ไม่ตรงกับราคาแพลน ({expected_amount} บาท)"
        raise HTTPException(status_code=400, detail=msg)

    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        trans_ref=result.trans_ref,
        trans_ref_hash=trans_ref_hash,
        amount=result.amount,
        sending_bank=result.sending_bank,
        sender_name_encrypted=encrypt_value(result.sender_name) if result.sender_name else None,
        receiver_name=result.receiver_name,
        trans_date=result.trans_date,
        trans_time=result.trans_time,
        plan_type=plan_type,
        plan_amount=expected_amount,
        status="verified",
        verification_response=json.dumps(result.raw_response),
        verified_at=now_th()
    )
    db.add(payment)

    # Upgrade subscription
    duration_days = plan["duration_days"]
    if (current_user.subscription_tier == "premium" and
        current_user.subscription_expires_at and
        current_user.subscription_expires_at > now_th()):
        new_expiry = current_user.subscription_expires_at + timedelta(days=duration_days)
    else:
        new_expiry = now_th() + timedelta(days=duration_days)

    current_user.subscription_tier = "premium"
    current_user.subscription_expires_at = new_expiry
    current_user.updated_at = now_th()

    db.commit()

    logger.info(f"Payment verified: user={current_user.id}, trans_ref={result.trans_ref}, plan={plan_type}")
    
    msg_success = "Payment Successful! Upgraded to Premium." if lang == "en" else "ชำระเงินสำเร็จ! อัพเกรดเป็น Premium แล้ว"

    return StandardResponse(
        status="success",
        message=msg_success,
        data={
            "payment_id": payment.id,
            "plan": plan_type,
            "amount": result.amount,
            "subscription_tier": "premium",
            "subscription_expires_at": str(new_expiry),
            "trans_ref": result.trans_ref
        }
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
    is_active = False
    days_remaining = 0

    if current_user.subscription_tier == "premium" and current_user.subscription_expires_at:
        if current_user.subscription_expires_at > now_th():
            is_active = True
            days_remaining = (current_user.subscription_expires_at - now_th()).days

    return StandardResponse(
        status="success",
        message="Subscription status retrieved",
        data={
            "tier": current_user.subscription_tier,
            "is_active": is_active,
            "expires_at": str(current_user.subscription_expires_at) if current_user.subscription_expires_at else None,
            "days_remaining": days_remaining,
            "features": {
                "max_records": "unlimited" if is_active else 30,
                "history_days": "unlimited" if is_active else 30
            }
        }
    )
