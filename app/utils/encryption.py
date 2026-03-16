
from cryptography.fernet import Fernet
import os
import logging
import hashlib

logger = logging.getLogger(__name__)

# Load or Generate Key
# In production, this should be loaded from secure storage.
# Here we check env, if not found, we warn (or generate one for dev).
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise RuntimeError(
        "ENCRYPTION_KEY is required. Generate with: "
        "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_value(value: str) -> str:
    """Encrypt a string value."""
    if not value:
        return None
    try:
        encrypted_text = cipher_suite.encrypt(value.encode())
        return encrypted_text.decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return None

def decrypt_value(value: str) -> str:
    """Decrypt a string value."""
    if not value:
        return None
    try:
        decrypted_text = cipher_suite.decrypt(value.encode())
        return decrypted_text.decode()
    except Exception as e:
        logger.error(f"Decryption failed of value: {e}") # Don't log the val
        return None

def hash_value(value: str) -> str:
    """Hash a value using SHA-256 for exact match search/indexing."""
    if not value:
        return None
    try:
        # Standardize input: lowercase and strip whitespace
        normalized = value.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()
    except Exception as e:
        logger.error(f"Hashing failed: {e}")
        return None
