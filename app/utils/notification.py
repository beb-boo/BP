
import os
import smtplib
import requests
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Email Configuration
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@bpmonitor.com")
OTP_EXPIRE_MINUTES = 5

# SMS Configuration
SMS_API_URL = os.getenv("SMS_API_URL", "")
SMS_API_KEY = os.getenv("SMS_API_KEY", "")
SMS_FROM = os.getenv("SMS_FROM", "BPMonitor")

def send_email_otp(recipient_email: str, otp: str, purpose: str):
    """Send OTP via email"""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        _print_mock_otp("EMAIL", recipient_email, otp, purpose)
        return True

    try:
        subject_map = {
            "registration": "ยืนยันการลงทะเบียน - รหัส OTP",
            "login": "รหัส OTP สำหรับเข้าสู่ระบบ",
            "password_reset": "รีเซ็ตรหัสผ่าน - รหัส OTP",
            "email_verification": "ยืนยันอีเมล - รหัส OTP"
        }

        subject = subject_map.get(purpose, "รหัส OTP")

        message = MIMEMultipart()
        message["From"] = EMAIL_FROM
        message["To"] = recipient_email
        message["Subject"] = subject

        body = f"""
        รหัส OTP ของคุณคือ: {otp}
        
        รหัสนี้จะหมดอายุใน {OTP_EXPIRE_MINUTES} นาที
        
        หากคุณไม่ได้ทำการร้องขอนี้ กรุณาเพิกเฉยต่ออีเมลนี้ :3
        """

        message.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = message.as_string()
        server.sendmail(EMAIL_FROM, recipient_email, text)
        server.quit()

        logger.info(f"OTP email sent to {recipient_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email OTP: {str(e)}")
        return False


def send_sms_otp(phone: str, otp: str, purpose: str):
    """Send OTP via SMS"""
    """Send OTP via SMS"""
    if not SMS_API_URL or not SMS_API_KEY:
        _print_mock_otp("SMS", phone, otp, purpose)
        return True

    try:
        message_map = {
            "registration": f"รหัส OTP สำหรับลงทะเบียน: {otp} (หมดอายุใน {OTP_EXPIRE_MINUTES} นาที)",
            "login": f"รหัส OTP เข้าสู่ระบบ: {otp} (หมดอายุใน {OTP_EXPIRE_MINUTES} นาที)",
            "password_reset": f"รหัส OTP รีเซ็ตรหัสผ่าน: {otp} (หมดอายุใน {OTP_EXPIRE_MINUTES} นาที)",
            "phone_verification": f"รหัส OTP ยืนยันเบอร์โทร: {otp} (หมดอายุใน {OTP_EXPIRE_MINUTES} นาที)"
        }

        message = message_map.get(purpose, f"รหัส OTP: {otp}")

        # Example for Thai SMS service (adjust based on your SMS provider)
        payload = {
            "to": phone,
            "from": SMS_FROM,
            "text": message
        }

        headers = {
            "Authorization": f"Bearer {SMS_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            SMS_API_URL, json=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            logger.info(f"OTP SMS sent to {phone}")
            return True
        else:
            logger.error(
                f"SMS API error: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Failed to send SMS OTP: {str(e)}")
        # Fallback to Mock for Dev/Testing if real send fails
        _print_mock_otp("SMS", phone, otp, purpose)
        return True


# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

def send_telegram_otp(telegram_id: int, otp: str, purpose: str):
    """Send OTP via Telegram Bot"""
    if not TELEGRAM_BOT_TOKEN:
        _print_mock_otp("TELEGRAM", str(telegram_id), otp, purpose)
        return True

    try:
        message_map = {
            "registration": f"🔐 BP Monitor\n\nรหัส OTP สำหรับลงทะเบียน: `{otp}`\n(หมดอายุใน {OTP_EXPIRE_MINUTES} นาที)",
            "login": f"🔐 BP Monitor\n\nรหัส OTP เข้าสู่ระบบ: `{otp}`\n(หมดอายุใน {OTP_EXPIRE_MINUTES} นาที)",
            "password_reset": f"🔐 BP Monitor\n\nรหัส OTP รีเซ็ตรหัสผ่าน: `{otp}`\n(หมดอายุใน {OTP_EXPIRE_MINUTES} นาที)",
            "phone_verification": f"🔐 BP Monitor\n\nรหัส OTP ยืนยันเบอร์โทร: `{otp}`\n(หมดอายุใน {OTP_EXPIRE_MINUTES} นาที)"
        }

        message = message_map.get(purpose, f"🔐 BP Monitor\n\nรหัส OTP: `{otp}`")

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": telegram_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            logger.info(f"OTP Telegram sent to {telegram_id}")
            return True
        else:
            logger.error(
                f"Telegram API error: {response.status_code} - {response.text}")
            # Fallback to mock if API fails (or maybe fallback to SMS? complex logic, keep simple for now)
            _print_mock_otp("TELEGRAM", str(telegram_id), otp, purpose)
            return True

    except Exception as e:
        logger.error(f"Failed to send Telegram OTP: {str(e)}")
        _print_mock_otp("TELEGRAM", str(telegram_id), otp, purpose)
        return True


def _print_mock_otp(channel: str, target: str, otp: str, purpose: str):
    """Helper to print mock OTP to console"""
    logger.warning(f"{channel} credentials issue or send failed. MOCK MODE: OTP for {target} is {otp}")
    print(f"============================================")
    print(f" [MOCK {channel}] To: {target}")
    print(f" [MOCK {channel}] OTP: {otp} ({purpose})")
    print(f"============================================")
