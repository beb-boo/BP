import threading
import time
import base64
import hashlib
import pyotp


class OTPService:
    """One Time Password service supporting email or phone."""

    def __init__(self):
        self.otp_storage = {}
        self.verified_contacts = set()
        threading.Thread(target=self.cleanup_expired_otp, daemon=True).start()

    def generate_otp(self, contact_target, expiration=60):
        """Generate an OTP for a given contact (email or phone)"""
        contact_target = contact_target.strip().lower()
        hex_key = self._get_hex_key_for_contact(contact_target)
        byte_key = bytes.fromhex(hex_key)
        base32_key = base64.b32encode(byte_key).decode('utf-8')

        totp = pyotp.TOTP(base32_key, digits=4, interval=expiration)
        otp = totp.now()

        # เก็บ TOTP object และเวลาที่สร้างใน storage
        self.otp_storage[contact_target] = {
            'totp': totp,
            'created_at': time.time(),
            'expiration': expiration
        }
        return otp

    def confirm_otp(self, contact_target, otp):
        """Verify OTP for email or phone"""
        contact_target = contact_target.strip().lower()
        user_otp_data = self.otp_storage.get(contact_target)
        if not user_otp_data:
            return False

        totp = user_otp_data['totp']
        created_at = user_otp_data['created_at']
        expiration = user_otp_data['expiration']

        # ตรวจสอบว่า OTP หมดอายุหรือไม่
        if time.time() - created_at > expiration:
            del self.otp_storage[contact_target]
            return False

        if totp.verify(otp, valid_window=1):
            self.verified_contacts.add(contact_target)
            return True

        return False

    def is_verified(self, contact_target):
        """Check if contact (email or phone) has successfully verified OTP"""
        return contact_target.strip().lower() in self.verified_contacts

    def get_time_remaining(self, contact_target):
        """Return seconds before OTP expires"""
        contact_target = contact_target.strip().lower()
        user_otp_data = self.otp_storage.get(contact_target)
        if not user_otp_data:
            return None
        totp = user_otp_data['totp']
        current_time = time.time()
        return totp.interval - (current_time % totp.interval)

    def _get_hex_key_for_contact(self, contact_target):
        return hashlib.sha256(contact_target.encode()).hexdigest()

    def cleanup_expired_otp(self):
        while True:
            current_time = time.time()
            for target in list(self.otp_storage.keys()):
                otp_data = self.otp_storage[target]
                if current_time - otp_data['created_at'] > otp_data['expiration']:
                    del self.otp_storage[target]
            time.sleep(120)
