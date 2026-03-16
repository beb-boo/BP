
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import sys

# Configure specific logger for transactions
txn_logger = logging.getLogger("bot_transactions")
txn_logger.setLevel(logging.INFO)
txn_logger.propagate = False  # Prevent propagation to root logger (avoid double printing if root has console)

# Check if handlers already exist to avoid adding duplicates on reload
if not txn_logger.handlers:
    # 1. Console Handler (stdout)
    c_handler = logging.StreamHandler(sys.stdout)
    c_formatter = logging.Formatter('🔵 [BOT-TXN] %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    c_handler.setFormatter(c_formatter)
    txn_logger.addHandler(c_handler)

    # 2. File Handler (Rotating)
    # Create logs directory if not exists
    log_dir = "logs"
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "bot_transactions.log")

        # Rotate: 10MB limit, keep 5 backups
        f_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
        f_formatter = logging.Formatter('%(asctime)s - %(message)s')
        f_handler.setFormatter(f_formatter)
        txn_logger.addHandler(f_handler)
    except Exception as e:
        print(f"Failed to setup file logging: {e}")


# ---------------------------------------------------------------------------
# Sensitive Data Masking
# ---------------------------------------------------------------------------

def mask_phone(phone: str) -> str:
    """Mask phone number: 66815204587 → 668***4587"""
    digits = re.sub(r'\D', '', phone)
    if len(digits) <= 4:
        return '***'
    return digits[:3] + '***' + digits[-4:]


def mask_name(name: str) -> str:
    """Mask name: 'Somchai Jaidee' → 'So***ai Ja***ee'"""
    parts = name.split()
    masked_parts = []
    for part in parts:
        if len(part) <= 2:
            masked_parts.append(part[0] + '*')
        else:
            masked_parts.append(part[:2] + '***' + part[-2:])
    return ' '.join(masked_parts)


def mask_text(text: str) -> str:
    """Fully mask free text (passwords, unknown input): 'abc123' → '******'"""
    if not text:
        return '***'
    return '*' * min(len(text), 8)


def mask_dob(dob: str) -> str:
    """Mask date of birth: '1990-05-15' → '1990-**-**'"""
    # Try common date patterns
    # DD/MM/YYYY or DD-MM-YYYY
    m = re.match(r'^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$', dob.strip())
    if m:
        return f'**/**/{m.group(3)}'
    # YYYY-MM-DD
    m = re.match(r'^(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})$', dob.strip())
    if m:
        return f'{m.group(1)}-**-**'
    # Fallback
    return '****-**-**'


def mask_contact_content(content: str) -> str:
    """Mask phone number inside 'Contact: 66815204587' format."""
    m = re.match(r'^Contact:\s*(\+?\d+)', content)
    if m:
        return f'Contact: {mask_phone(m.group(1))}'
    return content


# Message types that are known to contain sensitive data
# Mapped to their masking strategy
SENSITIVE_MSG_TYPES = {
    'password',        # User typing password
    'auth_password',   # Auth password input
    'reg_name',        # Registration name
    'reg_dob',         # Date of birth
    'reg_password',    # Registration password
    'contact',         # Phone number
}


class BotLogService:
    @staticmethod
    def log(telegram_id: int, direction: str, message_type: str, content: str,
            user_id: int = None, meta_data: dict = None):
        """
        Log a bot transaction to Console and File.
        direction: 'IN' or 'OUT'

        Sensitive data is automatically masked based on message_type.
        """
        try:
            user_label = f"UID:{user_id}" if user_id else f"TID:{telegram_id}"

            # --- Mask sensitive content ---
            clean_content = str(content).replace('\n', ' ')
            clean_content = BotLogService._mask_content(clean_content, message_type)

            # Truncate for log readability
            if len(clean_content) > 100:
                clean_content = clean_content[:97] + "..."

            log_msg = f"[{direction}] [{user_label}] [{message_type}] {clean_content}"

            txn_logger.info(log_msg)

        except Exception as e:
            # Fallback to print if logger fails
            print(f"Logging Error: {e}")

    @staticmethod
    def _mask_content(content: str, message_type: str) -> str:
        """Apply masking based on message_type."""
        msg_type_lower = message_type.lower()

        # Password — always fully mask
        if 'password' in msg_type_lower:
            return mask_text(content)

        # Contact / Phone
        if msg_type_lower == 'contact':
            return mask_contact_content(content)

        # Name
        if msg_type_lower in ('reg_name', 'name'):
            return mask_name(content)

        # Date of birth
        if msg_type_lower in ('reg_dob', 'dob'):
            return mask_dob(content)

        # For general 'text' type — apply pattern-based masking
        # This catches free-text that could be password/name during auth flows
        if msg_type_lower == 'text':
            return BotLogService._mask_text_patterns(content)

        return content

    @staticmethod
    def _mask_text_patterns(content: str) -> str:
        """
        For generic 'text' messages, detect and mask common sensitive patterns.
        This is the safety net for the log_middleware which doesn't know conversation state.
        """
        # Phone numbers (Thai: 08x, 09x, 06x or with country code 66...)
        content = re.sub(
            r'\b(0[689]\d)(\d{3,4})(\d{4})\b',
            lambda m: m.group(1) + '***' + m.group(3),
            content
        )
        content = re.sub(
            r'\b(66\d)(\d{3,4})(\d{4})\b',
            lambda m: m.group(1) + '***' + m.group(3),
            content
        )

        return content
