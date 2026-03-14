import os
import time
import base64
import hashlib
import logging
import pyotp

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL")


class MemoryOTPBackend:
    """In-memory OTP storage - for dev/local/non-serverless"""

    def __init__(self):
        self.storage = {}
        self.verified = set()
        import threading
        threading.Thread(target=self._cleanup, daemon=True).start()

    def store(self, key, otp_data):
        self.storage[key] = otp_data

    def get(self, key):
        return self.storage.get(key)

    def delete(self, key):
        self.storage.pop(key, None)

    def mark_verified(self, key):
        self.verified.add(key)

    def is_verified(self, key):
        return key in self.verified

    def _cleanup(self):
        while True:
            now = time.time()
            expired = [k for k, v in self.storage.items()
                       if now - v['created_at'] > v['expiration']]
            for k in expired:
                del self.storage[k]
            time.sleep(120)


class RedisOTPBackend:
    """Redis-backed OTP storage - for production/serverless"""

    def __init__(self, redis_url):
        import redis
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.prefix = "otp:"
        self.verified_prefix = "otp_verified:"

    def store(self, key, otp_data):
        import json
        ttl = int(otp_data.get('expiration', 300))
        self.client.setex(f"{self.prefix}{key}", ttl + 60, json.dumps(otp_data))

    def get(self, key):
        import json
        data = self.client.get(f"{self.prefix}{key}")
        return json.loads(data) if data else None

    def delete(self, key):
        self.client.delete(f"{self.prefix}{key}")

    def mark_verified(self, key):
        self.client.setex(f"{self.verified_prefix}{key}", 600, "1")

    def is_verified(self, key):
        return self.client.exists(f"{self.verified_prefix}{key}") > 0


class OTPService:
    """OTP service with auto-selected backend (Memory or Redis)"""

    def __init__(self):
        if REDIS_URL:
            try:
                self.backend = RedisOTPBackend(REDIS_URL)
                logger.info("OTP Service: Using Redis backend")
            except Exception as e:
                logger.warning(f"Redis failed ({e}), falling back to memory")
                self.backend = MemoryOTPBackend()
        else:
            self.backend = MemoryOTPBackend()
            logger.info("OTP Service: Using in-memory backend")

    def generate_otp(self, contact_target, expiration=300):
        contact_target = contact_target.strip().lower()
        hex_key = hashlib.sha256(contact_target.encode()).hexdigest()
        base32_key = base64.b32encode(bytes.fromhex(hex_key)).decode('utf-8')
        totp = pyotp.TOTP(base32_key, digits=4, interval=expiration)
        otp = totp.now()
        self.backend.store(contact_target, {
            'base32_key': base32_key,
            'interval': expiration,
            'created_at': time.time(),
            'expiration': expiration
        })
        return otp

    def confirm_otp(self, contact_target, otp):
        contact_target = contact_target.strip().lower()
        data = self.backend.get(contact_target)
        if not data:
            return False
        if time.time() - data['created_at'] > data['expiration']:
            self.backend.delete(contact_target)
            return False
        totp = pyotp.TOTP(data['base32_key'], digits=4, interval=data['interval'])
        if totp.verify(otp, valid_window=1):
            self.backend.mark_verified(contact_target)
            return True
        return False

    def is_verified(self, contact_target):
        return self.backend.is_verified(contact_target.strip().lower())


# Global Instance
otp_service = OTPService()
