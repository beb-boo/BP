
import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from pytz import timezone

load_from_dotenv = True # Assumed loaded in main

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
API_KEY_HEADER = "X-API-Key"

# API Keys for client apps
VALID_API_KEYS = os.getenv(
    "API_KEYS", "bp-mobile-app-key,bp-web-app-key").split(",")

THAI_TZ = timezone("Asia/Bangkok")

def now_th():
    return datetime.now(THAI_TZ)

security = HTTPBearer()
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = now_th() + expires_delta
    else:
        expire = now_th() + \
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access_token"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    to_encode = data.copy()
    # Refresh token expires in 30 days
    expire = now_th() + timedelta(days=30)
    to_encode.update({"exp": expire, "type": "refresh_token"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify API key for client applications"""
    if api_key not in VALID_API_KEYS:
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
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=401, detail="Invalid authentication")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account deactivated")

    # Check if account is locked
    if user.account_locked_until and user.account_locked_until > now_th():
        raise HTTPException(
            status_code=423, detail="Account temporarily locked")

    return user

def is_account_locked(user: User) -> bool:
    """Check if user account is locked due to failed login attempts"""
    if user.account_locked_until and user.account_locked_until > now_th():
        return True
    return False


def lock_account(user: User, db: Session):
    """Lock user account for 30 minutes after too many failed attempts"""
    user.account_locked_until = now_th() + timedelta(minutes=30)
    user.failed_login_attempts = 0  # Reset counter
    db.commit()
