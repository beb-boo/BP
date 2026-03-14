"""Subscription pricing configuration"""
from typing import Dict

SUBSCRIPTION_PLANS: Dict[str, dict] = {
    "monthly": {
        "name": "Premium รายเดือน",
        "name_en": "Premium Monthly",
        "price": 9.0,
        "duration_days": 30,
        "features": {
            "th": [
                "บันทึกความดันได้ไม่จำกัด",
                "ดูประวัติย้อนหลังทั้งหมด",
                "Export ข้อมูลไม่จำกัด"
            ],
            "en": [
                "Unlimited BP records",
                "Full history access",
                "Unlimited data export"
            ]
        }
    },
    "yearly": {
        "name": "Premium รายปี",
        "name_en": "Premium Yearly",
        "price": 99.0,
        "duration_days": 365,
        "features": {
            "th": [
                "บันทึกความดันได้ไม่จำกัด",
                "ดูประวัติย้อนหลังทั้งหมด",
                "Export ข้อมูลไม่จำกัด",
                "ประหยัด 9 บาท (เทียบกับรายเดือน)"
            ],
            "en": [
                "Unlimited BP records",
                "Full history access",
                "Unlimited data export",
                "Save 9 THB (vs Monthly)"
            ]
        }
    }
}

# บัญชีรับเงิน (แสดงให้ user)
PAYMENT_ACCOUNT = {
    "bank": "ธนาคารกสิกรไทย",
    "bank_en": "Kasikorn Bank (KBank)",
    "bank_code": "004",
    "account_number": "000-0-00000-0",  # Example - User to config
    "account_name": "Your Name"          
}

AMOUNT_TOLERANCE = 0.50  # ยอมรับความคลาดเคลื่อน 0.50 บาท

def get_plan(plan_type: str) -> dict:
    return SUBSCRIPTION_PLANS.get(plan_type)

def is_valid_amount(expected: float, actual: float) -> bool:
    return abs(expected - actual) <= AMOUNT_TOLERANCE
