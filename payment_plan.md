# แผนการพัฒนาระบบชำระเงินค่าบริการ (SlipOK Payment System)

## 1. ภาพรวมโครงการ

### 1.1 วัตถุประสงค์
พัฒนาระบบชำระเงินค่า subscription สำหรับ Blood Pressure Monitor Platform โดยใช้ SlipOK API ตรวจสอบสลิปการโอนเงินจากธนาคารไทย

### 1.2 ข้อกำหนด
| รายการ | รายละเอียด |
|--------|-----------|
| ช่องทางชำระเงิน | Web Application + Telegram Bot |
| วิธีการชำระ | โอนเงินผ่านธนาคาร → อัพโหลดสลิป → ตรวจสอบอัตโนมัติ |
| ราคา Monthly | 9 บาท (30 วัน) |
| ราคา Yearly | 99 บาท (365 วัน) |
| การตรวจสอบ | ใช้ SlipOK API พร้อม `log:true` (ป้องกันสลิปซ้ำ + ตรวจบัญชีผู้รับ) |

### 1.3 สิทธิประโยชน์ Premium
| Feature | Free | Premium |
|---------|------|---------|
| จำนวน BP records | จำกัด 30 รายการ | ไม่จำกัด |
| ประวัติการ export | 30 วันล่าสุด | ไม่จำกัด |
| สถิติและกราฟ | 30 วันล่าสุด | ไม่จำกัด |

---

## 2. SlipOK API Reference

### 2.1 Check Slip API
```
POST https://api.slipok.com/api/line/apikey/{BRANCH_ID}
Header: x-authorization: {API_KEY}
```

### 2.2 Request Body Options
| Parameter | Type | Description |
|-----------|------|-------------|
| `files` | File/Base64 | รูปภาพสลิป (JPG, PNG, WEBP) |
| `data` | String | QR Code data จากสลิป |
| `url` | String | URL ของรูปภาพสลิป |
| `log` | Boolean | `true` = เก็บข้อมูล + ตรวจซ้ำ + เช็คบัญชี |
| `amount` | Number | ยอดเงินที่คาดหวัง (optional) |

### 2.3 Response Data (Success)
```json
{
  "success": true,
  "data": {
    "transRef": "010092101507665143",
    "amount": 9.0,
    "sendingBank": "004",
    "receivingBank": "006",
    "transDate": "20260113",
    "transTime": "10:15:07",
    "sender": {
      "displayName": "นาย ตัวอย่าง ก",
      "account": { "value": "xxx-x-x1234-x" }
    },
    "receiver": {
      "displayName": "ร้านค้า",
      "account": { "value": "xxx-x-x5678-x" }
    }
  }
}
```

### 2.4 Error Codes
| Code | ความหมาย | User Message |
|------|----------|--------------|
| 1006 | รูปภาพไม่ถูกต้อง | กรุณาอัพโหลดรูปสลิปที่ชัดเจน |
| 1007 | ไม่พบ QR Code | รูปภาพไม่มี QR Code สำหรับตรวจสอบ |
| 1008 | QR ไม่ใช่สลิปโอนเงิน | QR Code นี้ไม่ใช่สลิปการโอนเงิน |
| 1011 | QR หมดอายุ | สลิปนี้หมดอายุหรือไม่พบรายการ |
| 1012 | สลิปซ้ำ | สลิปนี้เคยใช้ชำระเงินแล้ว |
| 1013 | ยอดไม่ตรง | ยอดเงินในสลิปไม่ตรงกับราคาแพลน |
| 1014 | บัญชีผู้รับไม่ตรง | กรุณาโอนเงินไปยังบัญชีที่ระบุ |

---

## 3. Database Schema

### 3.1 Payment Model (ใหม่)
```python
# app/models.py

class Payment(Base):
    """บันทึกการชำระเงินค่า subscription"""
    __tablename__ = "payments"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # SlipOK Verification Data
    trans_ref = Column(String(50), nullable=False)           # Transaction reference จาก SlipOK
    trans_ref_hash = Column(String(64), unique=True, index=True)  # Hash สำหรับตรวจซ้ำ

    # Transaction Details
    amount = Column(Float, nullable=False)                   # ยอดเงินจริงในสลิป
    sending_bank = Column(String(10), nullable=True)         # รหัสธนาคารผู้โอน
    sender_name_encrypted = Column(String, nullable=True)    # ชื่อผู้โอน (encrypted)
    receiver_name = Column(String(100), nullable=True)       # ชื่อผู้รับ
    trans_date = Column(String(10), nullable=True)           # วันที่โอน (yyyyMMdd)
    trans_time = Column(String(10), nullable=True)           # เวลาโอน (HH:mm:ss)

    # Subscription Info
    plan_type = Column(String(20), nullable=False)           # "monthly" หรือ "yearly"
    plan_amount = Column(Float, nullable=False)              # ราคาแพลนที่เลือก

    # Status
    status = Column(String(20), default="pending")           # pending, verified, failed
    error_code = Column(String(20), nullable=True)           # SlipOK error code
    error_message = Column(String(255), nullable=True)       # Error message
    verification_response = Column(Text, nullable=True)      # Full JSON response

    # Timestamps
    created_at = Column(DateTime, default=now_th)
    verified_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="payments")
```

### 3.2 User Model (แก้ไข)
```python
# เพิ่ม relationship ใน User model
payments = relationship("Payment", back_populates="user")
```

---

## 4. Backend Implementation

### 4.1 ไฟล์ใหม่: `app/config/pricing.py`
```python
"""Subscription pricing configuration"""
from typing import Dict

SUBSCRIPTION_PLANS: Dict[str, dict] = {
    "monthly": {
        "name": "Premium รายเดือน",
        "name_en": "Premium Monthly",
        "price": 9.0,
        "duration_days": 30,
        "features": [
            "บันทึกความดันได้ไม่จำกัด",
            "ดูประวัติย้อนหลังทั้งหมด",
            "Export ข้อมูลไม่จำกัด"
        ]
    },
    "yearly": {
        "name": "Premium รายปี",
        "name_en": "Premium Yearly",
        "price": 99.0,
        "duration_days": 365,
        "features": [
            "บันทึกความดันได้ไม่จำกัด",
            "ดูประวัติย้อนหลังทั้งหมด",
            "Export ข้อมูลไม่จำกัด",
            "ประหยัด 8 บาท (เทียบกับรายเดือน)"
        ]
    }
}

# บัญชีรับเงิน (แสดงให้ user)
PAYMENT_ACCOUNT = {
    "bank": "ธนาคารกสิกรไทย",
    "bank_code": "004",
    "account_number": "xxx-x-xxxxx-x",  # กำหนดเอง
    "account_name": "ชื่อบัญชี"          # กำหนดเอง
}

AMOUNT_TOLERANCE = 0.50  # ยอมรับความคลาดเคลื่อน 0.50 บาท

def get_plan(plan_type: str) -> dict:
    return SUBSCRIPTION_PLANS.get(plan_type)

def is_valid_amount(expected: float, actual: float) -> bool:
    return abs(expected - actual) <= AMOUNT_TOLERANCE
```

### 4.2 ไฟล์ใหม่: `app/services/slipok.py`
```python
"""SlipOK API Integration Service"""
import os
import requests
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SLIPOK_API_KEY = os.getenv("SLIPOK_API_KEY")
SLIPOK_BRANCH_ID = os.getenv("SLIPOK_BRANCH_ID", "1")
SLIPOK_BASE_URL = "https://api.slipok.com/api/line/apikey"

@dataclass
class SlipVerificationResult:
    """ผลการตรวจสอบสลิป"""
    success: bool
    trans_ref: Optional[str] = None
    amount: Optional[float] = None
    sending_bank: Optional[str] = None
    sender_name: Optional[str] = None
    receiver_name: Optional[str] = None
    trans_date: Optional[str] = None
    trans_time: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[dict] = None


class SlipOKService:
    """Service สำหรับตรวจสอบสลิปผ่าน SlipOK API"""

    ERROR_MESSAGES = {
        "1006": "รูปภาพไม่ถูกต้อง กรุณาอัพโหลดรูปสลิปที่ชัดเจน",
        "1007": "ไม่พบ QR Code ในรูปภาพ",
        "1008": "QR Code นี้ไม่ใช่สลิปการโอนเงิน",
        "1011": "สลิปนี้หมดอายุหรือไม่พบรายการ",
        "1012": "สลิปนี้เคยใช้ชำระเงินแล้ว",
        "1013": "ยอดเงินในสลิปไม่ตรงกับราคาแพลน",
        "1014": "บัญชีผู้รับไม่ตรง กรุณาโอนไปยังบัญชีที่ระบุ"
    }

    def __init__(self):
        if not SLIPOK_API_KEY:
            raise ValueError("SLIPOK_API_KEY not configured")
        self.api_key = SLIPOK_API_KEY
        self.branch_id = SLIPOK_BRANCH_ID
        self.url = f"{SLIPOK_BASE_URL}/{self.branch_id}"

    def verify_slip_image(
        self,
        image_content: bytes,
        expected_amount: Optional[float] = None
    ) -> SlipVerificationResult:
        """
        ตรวจสอบสลิปจากรูปภาพ

        Args:
            image_content: Binary image data
            expected_amount: ยอดเงินที่คาดหวัง (optional)
        """
        headers = {"x-authorization": self.api_key}
        files = {"files": ("slip.jpg", image_content, "image/jpeg")}
        data = {"log": "true"}

        if expected_amount:
            data["amount"] = str(expected_amount)

        try:
            response = requests.post(
                self.url,
                headers=headers,
                files=files,
                data=data,
                timeout=30
            )
            result = response.json()

            if result.get("success") and result.get("data", {}).get("success"):
                slip_data = result["data"]
                sender = slip_data.get("sender", {})
                receiver = slip_data.get("receiver", {})

                return SlipVerificationResult(
                    success=True,
                    trans_ref=slip_data.get("transRef"),
                    amount=float(slip_data.get("amount", 0)),
                    sending_bank=slip_data.get("sendingBank"),
                    sender_name=sender.get("displayName"),
                    receiver_name=receiver.get("displayName"),
                    trans_date=slip_data.get("transDate"),
                    trans_time=slip_data.get("transTime"),
                    raw_response=result
                )
            else:
                error_code = str(result.get("code", ""))
                return SlipVerificationResult(
                    success=False,
                    error_code=error_code,
                    error_message=self.ERROR_MESSAGES.get(error_code, result.get("message", "ตรวจสอบสลิปไม่สำเร็จ")),
                    raw_response=result
                )

        except requests.Timeout:
            return SlipVerificationResult(
                success=False,
                error_code="TIMEOUT",
                error_message="ระบบตรวจสอบไม่ตอบสนอง กรุณาลองใหม่"
            )
        except Exception as e:
            logger.error(f"SlipOK API error: {e}")
            return SlipVerificationResult(
                success=False,
                error_code="ERROR",
                error_message="เกิดข้อผิดพลาด กรุณาลองใหม่"
            )

    def check_quota(self) -> dict:
        """ตรวจสอบ quota คงเหลือ"""
        headers = {"x-authorization": self.api_key}
        try:
            response = requests.get(
                f"{self.url}/quota",
                headers=headers,
                timeout=10
            )
            return response.json()
        except Exception as e:
            logger.error(f"Check quota error: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
slipok_service = SlipOKService() if SLIPOK_API_KEY else None
```

### 4.3 ไฟล์ใหม่: `app/routers/payment.py`
```python
"""Payment API Router"""
import logging
import uuid
import json
from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Payment
from ..schemas import StandardResponse
from ..utils.security import verify_api_key, get_current_user, now_th
from ..utils.encryption import encrypt_value, hash_value
from ..services.slipok import slipok_service
from ..config.pricing import SUBSCRIPTION_PLANS, PAYMENT_ACCOUNT, get_plan, is_valid_amount

router = APIRouter(prefix="/api/v1/payment", tags=["payment"])
logger = logging.getLogger(__name__)


@router.get("/plans")
async def get_subscription_plans(
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """ดูแพลน subscription และสถานะปัจจุบัน"""
    plans = [{"plan_type": k, **v} for k, v in SUBSCRIPTION_PLANS.items()]

    return StandardResponse(
        status="success",
        message="Subscription plans retrieved",
        data={
            "plans": plans,
            "payment_account": PAYMENT_ACCOUNT,
            "current_tier": current_user.subscription_tier,
            "expires_at": str(current_user.subscription_expires_at) if current_user.subscription_expires_at else None
        }
    )


@router.post("/verify-slip")
async def verify_payment_slip(
    plan_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """อัพโหลดและตรวจสอบสลิปการชำระเงิน"""

    # Validate plan
    plan = get_plan(plan_type)
    if not plan:
        raise HTTPException(status_code=400, detail="แพลนไม่ถูกต้อง")

    # Check SlipOK service
    if not slipok_service:
        raise HTTPException(status_code=503, detail="ระบบตรวจสอบไม่พร้อมใช้งาน")

    # Validate file
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="กรุณาอัพโหลดไฟล์รูปภาพ")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=413, detail="ไฟล์ใหญ่เกินไป (สูงสุด 10MB)")

    # Verify with SlipOK
    expected_amount = plan["price"]
    result = slipok_service.verify_slip_image(content, expected_amount)

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
        raise HTTPException(status_code=409, detail="สลิปนี้เคยใช้ชำระเงินแล้ว")

    # Verify amount
    if not is_valid_amount(expected_amount, result.amount):
        raise HTTPException(
            status_code=400,
            detail=f"ยอดเงิน ({result.amount} บาท) ไม่ตรงกับราคาแพลน ({expected_amount} บาท)"
        )

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

    return StandardResponse(
        status="success",
        message="ชำระเงินสำเร็จ! อัพเกรดเป็น Premium แล้ว",
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
    """ดูประวัติการชำระเงิน"""
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
    """ดูสถานะ subscription ปัจจุบัน"""
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
```

### 4.4 แก้ไข: `app/main.py`
```python
# เพิ่ม import
from .routers import auth, users, bp_records, ocr, doctor, export, payment

# เพิ่ม router
app.include_router(payment.router)
```

---

## 5. Telegram Bot Implementation

### 5.1 ไฟล์ใหม่: `app/bot/handlers/payment.py`
```python
"""Telegram Payment Handler"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)

from ..services import get_user_by_telegram_id, verify_slip_payment, get_subscription_status
from ...config.pricing import SUBSCRIPTION_PLANS, PAYMENT_ACCOUNT

logger = logging.getLogger(__name__)

# Conversation states
WAITING_SLIP = 1


async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """แสดงแพลน subscription"""
    user = get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        await update.message.reply_text("กรุณา /login ก่อนใช้งาน")
        return ConversationHandler.END

    # สร้างข้อความแสดงแพลน
    text = "💎 *อัพเกรดเป็น Premium*\n\n"
    text += "สิทธิประโยชน์:\n"
    text += "✅ บันทึกความดันได้ไม่จำกัด\n"
    text += "✅ ดูประวัติย้อนหลังทั้งหมด\n"
    text += "✅ Export ข้อมูลไม่จำกัด\n\n"
    text += "📋 *เลือกแพลน:*\n"

    keyboard = []
    for plan_type, plan in SUBSCRIPTION_PLANS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{plan['name']} - {plan['price']:.0f} บาท",
                callback_data=f"pay_{plan_type}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ ยกเลิก", callback_data="pay_cancel")])

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_SLIP


async def plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """เมื่อเลือกแพลน - แสดงข้อมูลการโอนเงิน"""
    query = update.callback_query
    await query.answer()

    if query.data == "pay_cancel":
        await query.edit_message_text("ยกเลิกการอัพเกรด")
        return ConversationHandler.END

    plan_type = query.data.replace("pay_", "")
    plan = SUBSCRIPTION_PLANS.get(plan_type)

    if not plan:
        await query.edit_message_text("แพลนไม่ถูกต้อง")
        return ConversationHandler.END

    context.user_data["selected_plan"] = plan_type

    text = f"📝 *แพลนที่เลือก:* {plan['name']}\n"
    text += f"💰 *ราคา:* {plan['price']:.0f} บาท\n\n"
    text += "🏦 *โอนเงินมาที่:*\n"
    text += f"ธนาคาร: {PAYMENT_ACCOUNT['bank']}\n"
    text += f"เลขบัญชี: {PAYMENT_ACCOUNT['account_number']}\n"
    text += f"ชื่อบัญชี: {PAYMENT_ACCOUNT['account_name']}\n\n"
    text += f"⚠️ *โอนเงินจำนวน {plan['price']:.0f} บาท แล้วส่งรูปสลิปมาที่นี่*\n"
    text += "(พิมพ์ /cancel เพื่อยกเลิก)"

    await query.edit_message_text(text, parse_mode="Markdown")
    return WAITING_SLIP


async def receive_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """รับรูปสลิปและตรวจสอบ"""
    user = get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        await update.message.reply_text("กรุณา /login ก่อน")
        return ConversationHandler.END

    plan_type = context.user_data.get("selected_plan")
    if not plan_type:
        await update.message.reply_text("กรุณาเลือกแพลนก่อน /upgrade")
        return ConversationHandler.END

    # แจ้งว่ากำลังตรวจสอบ
    checking_msg = await update.message.reply_text("🔄 กำลังตรวจสอบสลิป...")

    try:
        # Download photo
        photo = update.message.photo[-1]  # Largest size
        file = await photo.get_file()
        image_bytes = await file.download_as_bytearray()

        # Verify with SlipOK
        result = verify_slip_payment(user.id, bytes(image_bytes), plan_type)

        if result["success"]:
            text = "✅ *ชำระเงินสำเร็จ!*\n\n"
            text += f"แพลน: {SUBSCRIPTION_PLANS[plan_type]['name']}\n"
            text += f"ยอด: {result['amount']:.0f} บาท\n"
            text += f"หมดอายุ: {result['expires_at']}\n\n"
            text += "🎉 คุณเป็น Premium แล้ว!"

            await checking_msg.edit_text(text, parse_mode="Markdown")
        else:
            await checking_msg.edit_text(f"❌ {result['error']}")
            return WAITING_SLIP  # ให้ส่งสลิปใหม่ได้

    except Exception as e:
        logger.error(f"Slip verification error: {e}")
        await checking_msg.edit_text("❌ เกิดข้อผิดพลาด กรุณาลองใหม่")
        return WAITING_SLIP

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ยกเลิกการชำระเงิน"""
    context.user_data.clear()
    await update.message.reply_text("ยกเลิกการชำระเงิน")
    return ConversationHandler.END


async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ดูสถานะ subscription"""
    user = get_user_by_telegram_id(str(update.effective_user.id))
    if not user:
        await update.message.reply_text("กรุณา /login ก่อน")
        return

    status = get_subscription_status(user.id)

    if status["is_active"]:
        text = "💎 *Premium Member*\n\n"
        text += f"หมดอายุ: {status['expires_at']}\n"
        text += f"เหลืออีก: {status['days_remaining']} วัน"
    else:
        text = "📦 *Free Member*\n\n"
        text += "จำกัด 30 รายการ\n"
        text += "พิมพ์ /upgrade เพื่ออัพเกรด"

    await update.message.reply_text(text, parse_mode="Markdown")


def get_payment_handler():
    """สร้าง ConversationHandler สำหรับ payment"""
    return ConversationHandler(
        entry_points=[CommandHandler("upgrade", upgrade_command)],
        states={
            WAITING_SLIP: [
                CallbackQueryHandler(plan_selected, pattern="^pay_"),
                MessageHandler(filters.PHOTO, receive_slip),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
```

### 5.2 แก้ไข: `app/bot/services.py`
```python
# เพิ่ม functions
def verify_slip_payment(user_id: int, image_bytes: bytes, plan_type: str) -> dict:
    """ตรวจสอบสลิปและอัพเกรด subscription"""
    # Logic เหมือนใน payment router
    pass

def get_subscription_status(user_id: int) -> dict:
    """ดึงสถานะ subscription"""
    pass
```

### 5.3 แก้ไข: `app/bot/main.py`
```python
# เพิ่ม import
from .handlers.payment import get_payment_handler, subscription_command

# เพิ่ม handlers
application.add_handler(get_payment_handler())
application.add_handler(CommandHandler("subscription", subscription_command))
```

---

## 6. Web Frontend Implementation

### 6.1 ไฟล์ใหม่: `frontend/app/(dashboard)/subscription/page.tsx`
```tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CreditCard, Crown, Upload, Check, Loader2, ArrowLeft } from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface Plan {
    plan_type: string;
    name: string;
    name_en: string;
    price: number;
    duration_days: number;
    features: string[];
}

export default function SubscriptionPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [plans, setPlans] = useState<Plan[]>([]);
    const [paymentAccount, setPaymentAccount] = useState<any>(null);
    const [currentTier, setCurrentTier] = useState("free");
    const [expiresAt, setExpiresAt] = useState<string | null>(null);

    const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
    const [slipFile, setSlipFile] = useState<File | null>(null);
    const [isUploading, setIsUploading] = useState(false);

    useEffect(() => {
        fetchPlans();
    }, []);

    const fetchPlans = async () => {
        try {
            const res = await api.get("/payment/plans");
            const data = res.data.data;
            setPlans(data.plans);
            setPaymentAccount(data.payment_account);
            setCurrentTier(data.current_tier);
            setExpiresAt(data.expires_at);
        } catch (error) {
            toast.error("Failed to load subscription plans");
        } finally {
            setLoading(false);
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setSlipFile(e.target.files[0]);
        }
    };

    const handleSubmit = async () => {
        if (!selectedPlan || !slipFile) {
            toast.error("กรุณาเลือกแพลนและอัพโหลดสลิป");
            return;
        }

        setIsUploading(true);

        const formData = new FormData();
        formData.append("plan_type", selectedPlan);
        formData.append("file", slipFile);

        try {
            const res = await api.post("/payment/verify-slip", formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });

            toast.success(res.data.message);
            setCurrentTier("premium");
            setExpiresAt(res.data.data.subscription_expires_at);
            setSelectedPlan(null);
            setSlipFile(null);

        } catch (error: any) {
            toast.error(error.response?.data?.detail || "ชำระเงินไม่สำเร็จ");
        } finally {
            setIsUploading(false);
        }
    };

    if (loading) {
        return <div className="p-8 flex items-center justify-center">Loading...</div>;
    }

    return (
        <div className="p-6 md:p-8 space-y-8 min-h-screen bg-slate-50 dark:bg-slate-950">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.push('/dashboard')}>
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Subscription</h1>
                    <p className="text-slate-500">อัพเกรดเป็น Premium เพื่อใช้งานเต็มรูปแบบ</p>
                </div>
            </div>

            {/* Current Status */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Crown className="h-5 w-5" />
                        สถานะปัจจุบัน
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center gap-4">
                        <Badge variant={currentTier === "premium" ? "default" : "secondary"}>
                            {currentTier === "premium" ? "Premium" : "Free"}
                        </Badge>
                        {expiresAt && (
                            <span className="text-sm text-slate-500">
                                หมดอายุ: {new Date(expiresAt).toLocaleDateString('th-TH')}
                            </span>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Plans */}
            <div className="grid md:grid-cols-2 gap-6">
                {plans.map((plan) => (
                    <Card
                        key={plan.plan_type}
                        className={`cursor-pointer transition-all ${
                            selectedPlan === plan.plan_type
                                ? "ring-2 ring-primary"
                                : "hover:shadow-lg"
                        }`}
                        onClick={() => setSelectedPlan(plan.plan_type)}
                    >
                        <CardHeader>
                            <CardTitle>{plan.name}</CardTitle>
                            <CardDescription>{plan.name_en}</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold mb-4">
                                ฿{plan.price}
                                <span className="text-sm font-normal text-slate-500">
                                    /{plan.duration_days} วัน
                                </span>
                            </div>
                            <ul className="space-y-2">
                                {plan.features.map((feature, i) => (
                                    <li key={i} className="flex items-center gap-2">
                                        <Check className="h-4 w-4 text-green-500" />
                                        <span className="text-sm">{feature}</span>
                                    </li>
                                ))}
                            </ul>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Payment Form */}
            {selectedPlan && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <CreditCard className="h-5 w-5" />
                            ชำระเงิน
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="p-4 bg-blue-50 rounded-lg">
                            <p className="font-medium">โอนเงินมาที่:</p>
                            <p>ธนาคาร: {paymentAccount?.bank}</p>
                            <p>เลขบัญชี: {paymentAccount?.account_number}</p>
                            <p>ชื่อบัญชี: {paymentAccount?.account_name}</p>
                            <p className="mt-2 text-lg font-bold">
                                ยอด: ฿{plans.find(p => p.plan_type === selectedPlan)?.price}
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2">
                                อัพโหลดสลิปการโอนเงิน
                            </label>
                            <Input
                                type="file"
                                accept="image/*"
                                onChange={handleFileChange}
                            />
                        </div>
                    </CardContent>
                    <CardFooter>
                        <Button
                            onClick={handleSubmit}
                            disabled={!slipFile || isUploading}
                            className="w-full"
                        >
                            {isUploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {isUploading ? "กำลังตรวจสอบ..." : "ตรวจสอบและชำระเงิน"}
                        </Button>
                    </CardFooter>
                </Card>
            )}
        </div>
    );
}
```

### 6.2 แก้ไข: `frontend/app/(dashboard)/settings/page.tsx`
```tsx
// เพิ่ม Tab "Subscription" หรือ Link ไปหน้า subscription
<TabsTrigger value="subscription">Subscription</TabsTrigger>

// หรือเพิ่ม Card link
<Card className="cursor-pointer hover:shadow-lg" onClick={() => router.push('/subscription')}>
    <CardHeader>
        <CardTitle>Subscription</CardTitle>
        <CardDescription>จัดการแพลนและอัพเกรดเป็น Premium</CardDescription>
    </CardHeader>
</Card>
```

---

## 7. Implementation Checklist

### Phase 1: Backend Core
- [ ] สร้าง `app/config/pricing.py`
- [ ] สร้าง `app/services/slipok.py`
- [ ] เพิ่ม Payment model ใน `app/models.py`
- [ ] เพิ่ม schemas ใน `app/schemas.py`
- [ ] สร้าง `app/routers/payment.py`
- [ ] แก้ไข `app/main.py` include router
- [ ] Test API endpoints

### Phase 2: Telegram Bot
- [ ] สร้าง `app/bot/handlers/payment.py`
- [ ] เพิ่ม functions ใน `app/bot/services.py`
- [ ] แก้ไข `app/bot/main.py`
- [ ] Test bot commands

### Phase 3: Web Frontend
- [ ] สร้าง `frontend/app/(dashboard)/subscription/page.tsx`
- [ ] แก้ไข settings page เพิ่ม link
- [ ] Test web payment flow

### Phase 4: Configuration
- [ ] ตั้งค่า `SLIPOK_API_KEY` ใน .env
- [ ] ตั้งค่า `SLIPOK_BRANCH_ID` ใน .env
- [ ] กำหนดข้อมูลบัญชีรับเงินใน pricing.py

---

## 8. Security Checklist
- [ ] Rate limiting (5/min) บน verify-slip endpoint
- [ ] ใช้ `log:true` ป้องกันสลิปซ้ำฝั่ง SlipOK
- [ ] เก็บ trans_ref_hash ป้องกันซ้ำในฐานข้อมูล
- [ ] Encrypt sender name (PII protection)
- [ ] Validate file type และ size
- [ ] Log ทุก payment attempt
