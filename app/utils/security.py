
import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional, List
from pytz import UTC
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from .timezone import now_tz
import logging

load_from_dotenv = True # Assumed loaded in main

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "7"))
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * ACCESS_TOKEN_EXPIRE_DAYS
API_KEY_HEADER = "X-API-Key"

# Account lockout configuration
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
ACCOUNT_LOCK_MINUTES = int(os.getenv("ACCOUNT_LOCK_MINUTES", "30"))

# API Keys for client apps
_raw_keys = os.getenv("API_KEYS", "")
if not _raw_keys:
    _raw_keys = "bp-mobile-app-key,bp-web-app-key"
VALID_API_KEYS = [k.strip() for k in _raw_keys.split(",") if k.strip()]

logger = logging.getLogger(__name__)

# Premium bypass — comma-separated: user IDs, Telegram chat IDs, or phone numbers
# e.g. PREMIUM_BYPASS_USERS=+66645293605,123456789
# Read lazily because dotenv loads AFTER module imports in main.py
_premium_bypass_cache = None


def _get_bypass_ids() -> set:
    global _premium_bypass_cache
    if _premium_bypass_cache is None:
        raw = os.getenv("PREMIUM_BYPASS_USERS", "")
        _premium_bypass_cache = {x.strip() for x in raw.split(",") if x.strip()}
    return _premium_bypass_cache


def check_premium(user) -> bool:
    """Check if user has active premium subscription or is in bypass list.

    Bypass matches against user.id, user.telegram_id, or user.phone_number.
    Useful for testing and promotions.
    """
    bypass_ids = _get_bypass_ids()
    if bypass_ids:
        if str(user.id) in bypass_ids:
            return True
        try:
            tg_id = user.telegram_id
            if tg_id and str(tg_id) in bypass_ids:
                return True
        except Exception:
            pass
        try:
            phone = user.phone_number
            if phone:
                # Match with or without '+' prefix
                if phone in bypass_ids or f"+{phone}" in bypass_ids or phone.lstrip("+") in bypass_ids:
                    return True
        except Exception:
            pass
    if user.subscription_tier == "premium":
        if user.subscription_expires_at and user.subscription_expires_at > now_tz():
            return True
    return False

# ── Startup warnings for default/fallback values ────────────────
if not SECRET_KEY or SECRET_KEY == "your-secret-key-here":
    raise RuntimeError("SECRET_KEY must be set and not use default value")
if not os.getenv("API_KEYS", ""):
    logger.warning(
        "API_KEYS not set in environment. Using default dev keys. "
        "Set API_KEYS env var in production!"
    )

security = HTTPBearer()
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = now_tz() + expires_delta
    else:
        expire = now_tz() + \
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access_token"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    to_encode = data.copy()
    # Refresh token expires in 30 days
    expire = now_tz() + timedelta(days=30)
    to_encode.update({"exp": expire, "type": "refresh_token"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify API key for client applications"""
    if not api_key:
         # Log warning but maybe frontend forgot it? 
         # If auto_error=False, api_key is None.
         # But code below checks 'if api_key not in VALID_API_KEYS'. None is not in list.
         logger.warning("Missing API Key in request")
         pass # Let it fail below

    if api_key not in VALID_API_KEYS:
        logger.warning(f"Invalid API Key: {api_key}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )
    return api_key


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user"""
    try:
        payload = jwt.decode(credentials.credentials,
                             SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "access_token":
            logger.warning("Invalid token type")
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id: int = payload.get("user_id")
        if user_id is None:
            logger.warning("Invalid authentication (no user_id)")
            raise HTTPException(
                status_code=401, detail="Invalid authentication")

    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError as e:
        logger.warning(f"JWT Error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid authentication")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        logger.warning(f"User deactivated: {user_id}")
        raise HTTPException(status_code=401, detail="Account deactivated")

    # Check if account is locked
    if user.account_locked_until:
        # Ensure aware (DB might return naive)
        locked_until = user.account_locked_until
        if locked_until.tzinfo is None:
            locked_until = UTC.localize(locked_until)
            
        if locked_until > now_tz():
            logger.warning(f"Account locked: {user_id}")
            raise HTTPException(
                status_code=423, detail="Account temporarily locked")

    return user

def is_account_locked(user: User) -> bool:
    """Check if user account is locked due to failed login attempts"""
    if user.account_locked_until:
        locked_until = user.account_locked_until
        if locked_until.tzinfo is None:
            locked_until = UTC.localize(locked_until)
        
        if locked_until > now_tz():
            return True
    return False


def lock_account(user: User, db: Session):
    """Lock user account after too many failed attempts"""
    user.account_locked_until = now_tz() + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
    user.failed_login_attempts = 0  # Reset counter
    db.commit()
