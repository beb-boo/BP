"""Subscription pricing configuration"""
import os
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
                "วิเคราะห์ค่า SD, Median, Pulse Pressure, MAP",
                "วิเคราะห์แนวโน้ม (Trend Analysis)",
                "Export ข้อมูลไม่จำกัด"
            ],
            "en": [
                "Unlimited BP records",
                "Full history access",
                "Advanced analytics (SD, Median, Pulse Pressure, MAP)",
                "Trend Analysis",
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
                "วิเคราะห์ค่า SD, Median, Pulse Pressure, MAP",
                "วิเคราะห์แนวโน้ม (Trend Analysis)",
                "Export ข้อมูลไม่จำกัด",
                "ประหยัด 9 บาท (เทียบกับรายเดือน)"
            ],
            "en": [
                "Unlimited BP records",
                "Full history access",
                "Advanced analytics (SD, Median, Pulse Pressure, MAP)",
                "Trend Analysis",
                "Unlimited data export",
                "Save 9 THB (vs Monthly)"
            ]
        }
    }
}

# บัญชีรับเงิน (อ่านจาก ENV — ตั้งค่าใน .env)
PAYMENT_ACCOUNT = {
    "bank": os.getenv("PAYMENT_BANK_NAME", "ธนาคารกสิกรไทย"),
    "bank_en": os.getenv("PAYMENT_BANK_NAME_EN", "Kasikorn Bank (KBank)"),
    "bank_code": os.getenv("PAYMENT_BANK_CODE", "004"),
    "account_number": os.getenv("PAYMENT_ACCOUNT_NUMBER", "000-0-00000-0"),
    "account_name": os.getenv("PAYMENT_ACCOUNT_NAME", "Your Name"),
}

AMOUNT_TOLERANCE = float(os.getenv("PAYMENT_AMOUNT_TOLERANCE", "0.50"))

def get_plan(plan_type: str) -> dict:
    return SUBSCRIPTION_PLANS.get(plan_type)

def is_valid_amount(expected: float, actual: float) -> bool:
    return abs(expected - actual) <= AMOUNT_TOLERANCE
