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
    """ผลการตรวจสอบสลิป / Verification Result"""
    success: bool
    trans_ref: Optional[str] = None
    amount: Optional[float] = None
    sending_bank: Optional[str] = None
    sender_name: Optional[str] = None
    receiver_name: Optional[str] = None
    trans_date: Optional[str] = None
    trans_time: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None # Localized message
    raw_response: Optional[dict] = None


class SlipOKService:
    """Service สำหรับตรวจสอบสลิปผ่าน SlipOK API"""
    
    # Bilingual Error Messages
    ERROR_MESSAGES = {
        "1000": {"th": "ไม่พบข้อมูล", "en": "Data not found"},
        "1006": {"th": "รูปภาพไม่ถูกต้อง กรุณาอัพโหลดรูปสลิปที่ชัดเจน", "en": "Invalid image. Please upload a clear slip image."},
        "1007": {"th": "ไม่พบ QR Code ในรูปภาพ", "en": "QR Code not found in image."},
        "1008": {"th": "QR Code นี้ไม่ใช่สลิปการโอนเงิน", "en": "QR Code is not a valid bank slip."},
        "1011": {"th": "สลิปนี้หมดอายุหรือไม่พบรายการ", "en": "Slip expired or transaction not found."},
        "1012": {"th": "สลิปนี้เคยใช้ชำระเงินแล้ว", "en": "Slip already used."},
        "1013": {"th": "ยอดเงินในสลิปไม่ตรงกับราคาแพลน", "en": "Amount mismatch."},
        "1014": {"th": "บัญชีผู้รับไม่ตรง กรุณาโอนไปยังบัญชีที่ระบุ", "en": "Incorrect receiving account."}
    }

    def __init__(self):
        if not SLIPOK_API_KEY:
            logger.warning("SLIPOK_API_KEY not configured. Payment verification will fail.")
        self.api_key = SLIPOK_API_KEY
        self.branch_id = SLIPOK_BRANCH_ID
        self.url = f"{SLIPOK_BASE_URL}/{self.branch_id}"

    def get_error_message(self, code: str, language: str = "th") -> str:
        """Get localized error message"""
        msg_dict = self.ERROR_MESSAGES.get(code, {})
        return msg_dict.get(language, msg_dict.get("th", f"Error: {code}"))

    def verify_slip_image(
        self,
        image_content: bytes,
        expected_amount: Optional[float] = None,
        language: str = "th"
    ) -> SlipVerificationResult:
        """
        Verify slip from image content.
        """
        if not self.api_key:
             return SlipVerificationResult(
                success=False,
                error_code="CONFIG",
                error_message="System configuration error (Missing API Key)" if language == "en" else "ระบบขัดข้อง (ไม่พบ API Key)"
            )

        headers = {"x-authorization": self.api_key}
        files = {"files": ("slip.jpg", image_content, "image/jpeg")}
        data = {"log": "true"} # Enable duplicate checking by SlipOK

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

            # Check success (SlipOK returns {success: true, data: {success: true, ...}})
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
                api_msg = result.get("message", "Verification Failed")
                
                # Use our localized dictionary or fallback to API message
                final_msg = self.get_error_message(error_code, language)
                if final_msg.startswith("Error:"): # If not in dict
                     final_msg = f"{final_msg} ({api_msg})"

                return SlipVerificationResult(
                    success=False,
                    error_code=error_code,
                    error_message=final_msg,
                    raw_response=result
                )

        except requests.Timeout:
            return SlipVerificationResult(
                success=False,
                error_code="TIMEOUT",
                error_message="API Timeout. Please try again." if language == "en" else "ระบบตรวจสอบไม่ตอบสนอง กรุณาลองใหม่"
            )
        except Exception as e:
            logger.error(f"SlipOK API error: {e}")
            return SlipVerificationResult(
                success=False,
                error_code="ERROR",
                error_message=f"System Error: {str(e)}"
            )

    def check_quota(self) -> dict:
        """Check remaining quota"""
        if not self.api_key: return {"success": False, "error": "No API Key"}
        
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
slipok_service = SlipOKService()
