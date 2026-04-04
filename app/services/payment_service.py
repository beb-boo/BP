"""Shared payment verification service — used by both Web API and Telegram Bot.

This module is the **single** place where slip verification, duplicate
detection, amount validation, payment recording and subscription upgrade
happen.  Neither the web router nor the bot service should contain their
own copy of this pipeline.
"""

import json
import uuid
import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import Payment
from app.services.slipok import slipok_service
from app.config.pricing import get_plan, is_valid_amount
from app.utils.timezone import now_tz
from app.utils.encryption import encrypt_value, hash_value
from app.utils.subscription import get_renewal_base_datetime

logger = logging.getLogger(__name__)

# ── Per-user verify-slip rate limiting (shared by Web and Bot) ────
# The web route ALSO has @limiter.limit("3/minute") on the HTTP layer,
# but this in-service check ensures the Bot path gets the same policy.
import time
import threading

_verify_lock = threading.Lock()
_verify_timestamps: dict[int, list[float]] = {}  # user_id → [timestamps]
VERIFY_RATE_LIMIT = 3        # max attempts
VERIFY_RATE_WINDOW = 60.0    # per 60 seconds


def _check_rate_limit(user_id: int, lang: str = "th") -> None:
    """Enforce per-user rate limit for slip verification.

    Raises PaymentError if the user has exceeded VERIFY_RATE_LIMIT
    attempts in the last VERIFY_RATE_WINDOW seconds.
    """
    now = time.monotonic()
    with _verify_lock:
        timestamps = _verify_timestamps.get(user_id, [])
        # Remove entries outside the window
        timestamps = [t for t in timestamps if now - t < VERIFY_RATE_WINDOW]
        if len(timestamps) >= VERIFY_RATE_LIMIT:
            msg = (
                "Too many verification attempts. Please wait a moment."
                if lang == "en"
                else "คุณลองบ่อยเกินไป กรุณารอสักครู่"
            )
            raise PaymentError(msg, 429)
        timestamps.append(now)
        _verify_timestamps[user_id] = timestamps


# Image validation constants — shared by Web and Bot
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
IMAGE_MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"GIF8": "image/gif",
    b"RIFF": "image/webp",  # RIFF....WEBP
}


class PaymentError(Exception):
    """Raised when payment verification fails at any step."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def validate_slip_image(image_bytes: bytes, lang: str = "th") -> None:
    """Validate that image_bytes is a valid image within size limits.

    Raises PaymentError if validation fails.
    This is called by both Web and Bot paths to ensure parity.
    """
    if not image_bytes:
        msg = "No image data" if lang == "en" else "ไม่มีข้อมูลรูปภาพ"
        raise PaymentError(msg, 400)

    if len(image_bytes) > MAX_IMAGE_SIZE:
        msg = (
            "File too large (>10MB)"
            if lang == "en"
            else "ไฟล์ใหญ่เกินไป (สูงสุด 10MB)"
        )
        raise PaymentError(msg, 413)

    # Check magic bytes to verify it's actually an image
    is_image = any(image_bytes[:4].startswith(magic) for magic in IMAGE_MAGIC_BYTES)
    if not is_image:
        msg = (
            "Please upload an image file (JPG/PNG)"
            if lang == "en"
            else "กรุณาอัพโหลดไฟล์รูปภาพ (JPG/PNG)"
        )
        raise PaymentError(msg, 400)


def verify_and_upgrade(
    db: Session,
    user,
    image_bytes: bytes,
    plan_type: str,
    lang: str = "th",
) -> dict:
    """Execute the full payment verification pipeline.

    Steps
    -----
    0. Validate image (size + magic bytes)
    1. Validate plan type
    2. Check SlipOK service availability
    3. Call SlipOK API to verify slip image
    4. Check for duplicate transaction (internal ``trans_ref_hash``)
    5. Validate transferred amount against plan price
    6. Create ``Payment`` record
    7. Upgrade user subscription (stack if active, fresh if expired)

    Returns
    -------
    dict with keys: payment_id, plan, plan_name, amount, subscription_tier,
    subscription_expires_at, trans_ref

    Raises
    ------
    PaymentError  – with ``message`` (localised) and ``status_code``
    """
    now = now_tz()

    # Rate limit: 3 attempts per minute per user (parity with web @limiter)
    _check_rate_limit(user.id, lang)

    # 0. Validate image
    validate_slip_image(image_bytes, lang)

    # 1. Validate plan
    plan = get_plan(plan_type)
    if not plan:
        msg = "Invalid plan" if lang == "en" else "แพลนไม่ถูกต้อง"
        raise PaymentError(msg, 400)

    # 2. Check SlipOK availability
    if not slipok_service.api_key:
        msg = (
            "Payment system unavailable"
            if lang == "en"
            else "ระบบตรวจสอบไม่พร้อมใช้งาน"
        )
        raise PaymentError(msg, 503)

    # 3. Call SlipOK
    expected_amount = plan["price"]
    result = slipok_service.verify_slip_image(
        image_bytes, expected_amount, language=lang
    )

    if not result.success:
        # Log failed attempt
        failed_payment = Payment(
            user_id=user.id,
            trans_ref=f"FAILED-{uuid.uuid4()}",
            trans_ref_hash=hash_value(f"FAILED-{uuid.uuid4()}-{now}"),
            amount=0,
            plan_type=plan_type,
            plan_amount=expected_amount,
            status="failed",
            error_code=result.error_code,
            error_message=result.error_message,
            verification_response=(
                json.dumps(result.raw_response) if result.raw_response else None
            ),
        )
        db.add(failed_payment)
        db.commit()
        # 422 = slip was received and processed by SlipOK but failed business validation
        # (wrong account, expired, amount mismatch, etc.) — distinct from 400 bad input
        raise PaymentError(result.error_message, 422)

    # 4. Duplicate check (internal)
    trans_ref_hash = hash_value(result.trans_ref)
    existing = (
        db.query(Payment)
        .filter(
            Payment.trans_ref_hash == trans_ref_hash,
            Payment.status == "verified",
        )
        .first()
    )
    if existing:
        msg = (
            "Slip already used"
            if lang == "en"
            else "สลิปนี้เคยใช้ชำระเงินแล้ว"
        )
        raise PaymentError(msg, 409)

    # 5. Amount validation
    if not is_valid_amount(expected_amount, result.amount):
        msg = (
            f"Amount mismatch ({result.amount} vs {expected_amount})"
            if lang == "en"
            else f"ยอดเงิน ({result.amount} บาท) ไม่ตรงกับราคาแพลน ({expected_amount} บาท)"
        )
        raise PaymentError(msg, 400)

    # 6. Create payment record
    payment = Payment(
        user_id=user.id,
        trans_ref=result.trans_ref,
        trans_ref_hash=trans_ref_hash,
        amount=result.amount,
        sending_bank=result.sending_bank,
        sender_name_encrypted=(
            encrypt_value(result.sender_name) if result.sender_name else None
        ),
        receiver_name=result.receiver_name,
        trans_date=result.trans_date,
        trans_time=result.trans_time,
        plan_type=plan_type,
        plan_amount=expected_amount,
        status="verified",
        verification_response=json.dumps(result.raw_response),
        verified_at=now,
    )
    db.add(payment)

    # 7. Upgrade subscription
    duration_days = plan["duration_days"]
    base = get_renewal_base_datetime(user, now)
    new_expiry = base + timedelta(days=duration_days)

    user.subscription_tier = "premium"
    user.subscription_expires_at = new_expiry
    user.updated_at = now

    db.commit()

    logger.info(
        "Payment verified: user=%s, trans_ref=%s, plan=%s",
        user.id,
        result.trans_ref,
        plan_type,
    )

    plan_name = plan.get("name_en") if lang == "en" else plan.get("name")

    return {
        "payment_id": payment.id,
        "plan": plan_type,
        "plan_name": plan_name,
        "amount": result.amount,
        "subscription_tier": "premium",
        "subscription_expires_at": str(new_expiry),
        "trans_ref": result.trans_ref,
    }
