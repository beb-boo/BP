
import os
import hmac
import hashlib
import json
import time
import logging
from urllib.parse import parse_qs, unquote

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from datetime import timedelta

from ..database import get_db
from ..models import User
from ..schemas import TelegramMiniAppAuth
from ..utils.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, is_account_locked
from ..utils.encryption import hash_value
from ..utils.rate_limiter import limiter
from ..utils.timezone import now_tz

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/telegram", tags=["Telegram Auth"])

# initData expiry: 24 hours
INIT_DATA_EXPIRY_SECONDS = 86400


def _verify_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """Verify Telegram WebApp initData using HMAC-SHA256.

    Returns parsed data dict on success, raises HTTPException on failure.
    """
    # Parse URL-encoded key-value pairs
    parsed = parse_qs(init_data, keep_blank_values=True)
    # parse_qs returns lists; flatten to single values
    data = {k: v[0] for k, v in parsed.items()}

    received_hash = data.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing hash in initData")

    # Build data_check_string: sort by key, join with \n
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items())
    )

    # secret_key = HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256
    ).digest()

    # computed_hash = HMAC-SHA256(secret_key, data_check_string)
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    # Constant-time comparison
    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    # Check auth_date expiry
    auth_date = data.get("auth_date")
    if auth_date:
        try:
            auth_ts = int(auth_date)
            if time.time() - auth_ts > INIT_DATA_EXPIRY_SECONDS:
                raise HTTPException(status_code=401, detail="initData expired")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid auth_date")

    # Parse user JSON
    user_str = data.get("user")
    if not user_str:
        raise HTTPException(status_code=401, detail="Missing user in initData")

    try:
        user_data = json.loads(user_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=401, detail="Invalid user JSON in initData")

    return user_data


@router.post("/mini-app-auth")
@limiter.limit("10/minute")
async def telegram_mini_app_auth(
    request: Request,
    body: TelegramMiniAppAuth,
    db: Session = Depends(get_db),
):
    """Authenticate Telegram Mini App user via initData verification.

    No API key required — uses Telegram HMAC signature instead.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        raise HTTPException(status_code=500, detail="Bot not configured")

    # Verify initData HMAC signature
    user_data = _verify_telegram_init_data(body.init_data, bot_token)

    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(status_code=401, detail="Missing telegram user id")

    # Find user by telegram_id_hash
    t_hash = hash_value(str(telegram_id))
    user = db.query(User).filter(User.telegram_id_hash == t_hash).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Telegram account not linked. Please use /start in the bot first."
        )

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account deactivated")

    if is_account_locked(user):
        raise HTTPException(status_code=423, detail="Account temporarily locked")

    # Issue JWT token
    token = create_access_token(
        data={"user_id": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Update last login
    user.last_login = now_tz()
    db.commit()

    return {
        "status": "success",
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id,
                "full_name": user.full_name or "",
                "role": user.role,
                "language": user.language or "th",
                "telegram_id": telegram_id,
            },
        },
    }
