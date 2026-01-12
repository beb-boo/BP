
from cryptography.fernet import Fernet
import os
import logging

logger = logging.getLogger(__name__)

# Load or Generate Key
# In production, this should be loaded from secure storage.
# Here we check env, if not found, we warn (or generate one for dev).
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    logger.warning("No ENCRYPTION_KEY found in env. Generating temporary key for this session (Data will be lost on restart if not persisted!).")
    key = Fernet.generate_key()
    ENCRYPTION_KEY = key.decode()
    # In a real app, we might validly stop here to force admin to set the key.
    # For this refactor/demo, we'll proceed but log heavily.

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
        logger.error(f"Decryption failed: {e}")
        return None
