
from fastapi import APIRouter, HTTPException, Depends, Request, status, BackgroundTasks
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, UserSession
from ..schemas import (
    StandardResponse, UserRegister, OTPRequest, OTPVerification, 
    UserLogin, PasswordChange, PasswordReset, Token
)
from ..utils.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    verify_api_key, get_current_user, lock_account, is_account_locked,
    now_th, ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..utils.encryption import encrypt_value, hash_value
from ..utils.tmc_checker import verify_doctor_with_tmc
import hashlib

from ..utils.notification import send_email_otp, send_sms_otp, OTP_EXPIRE_MINUTES
import logging
import uuid
import secrets
import os
from datetime import timedelta
from ..otp_service import otp_service
from slowapi import Limiter
from slowapi.util import get_remote_address

# Setup
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

def generate_request_id() -> str:
    return str(uuid.uuid4())

def create_standard_response(status, message, data=None, request_id=None):
    return StandardResponse(
        status=status,
        message=message,
        data=data,
        request_id=request_id or generate_request_id()
    )


@router.post("/request-otp", tags=["OTP"])
@limiter.limit("3/minute")
async def request_otp(
    request: Request,
    otp_request: OTPRequest,
    api_key: str = Depends(verify_api_key)
):
    request_id = generate_request_id()

    contact_method = "email" if otp_request.email else "sms"
    contact_target = (
        otp_request.email or otp_request.phone_number).strip().lower()

    # Generate OTP
    otp_code = otp_service.generate_otp(
        contact_target, expiration=OTP_EXPIRE_MINUTES * 60)

    # Send OTP
    send_success = False
    if contact_method == "email":
        send_success = send_email_otp(
            contact_target, otp_code, otp_request.purpose)
    else:
        send_success = send_sms_otp(
            contact_target, otp_code, otp_request.purpose)

    if not send_success:
        raise HTTPException(status_code=500, detail="Failed to send OTP")

    return create_standard_response(
        status="success",
        message=f"OTP sent to your {contact_method}",
        data={
            "contact_method": contact_method,
            "contact_target": contact_target[:3] + "*" * (len(contact_target) - 6) + contact_target[-3:],
            "expires_in_minutes": OTP_EXPIRE_MINUTES
        },
        request_id=request_id
    )


@router.post("/verify-otp", tags=["OTP"])
@limiter.limit("5/minute")
async def verify_otp(
    request: Request,
    otp_verification: OTPVerification,
    api_key: str = Depends(verify_api_key)
):
    request_id = generate_request_id()
    contact_target = (
        otp_verification.email or otp_verification.phone_number).strip().lower()

    if not otp_service.confirm_otp(contact_target, otp_verification.otp_code):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    return create_standard_response(
        status="success",
        message="OTP verified successfully",
        data={
            "verified": True,
            "purpose": otp_verification.purpose,
            "contact_target": contact_target
        },
        request_id=request_id
    )


@router.post("/register", tags=["register"])
@limiter.limit("3/minute")
async def register_user(
    request: Request,
    user_data: UserRegister,
    background_tasks: BackgroundTasks, 
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Register new user - requires prior OTP verification"""
    request_id = generate_request_id()

    contact_target = (
        user_data.email or user_data.phone_number).strip().lower()

    # Check if OTP has been verified for this contact
    if not otp_service.is_verified(contact_target):
        raise HTTPException(
            status_code=400,
            detail="Please verify your contact information with OTP first"
        )

    # Check for existing users using HASH lookup
    if user_data.email:
        email_h = hash_value(user_data.email)
        if db.query(User).filter(User.email_hash == email_h).first():
            raise HTTPException(
                status_code=400, detail="This email is already registered. Please log in.")

    if user_data.phone_number:
        phone_h = hash_value(user_data.phone_number)
        if db.query(User).filter(User.phone_number_hash == phone_h).first():
            raise HTTPException(
                status_code=400, detail="This phone number is already in use.")

    # Check for existing citizen_id (via hash)
    if user_data.citizen_id:
        c_hash = hash_value(user_data.citizen_id)
        if db.query(User).filter(User.citizen_id_hash == c_hash).first():
            raise HTTPException(status_code=400, detail="This Citizen ID is already registered.")

    if user_data.role == "doctor" and user_data.medical_license:
        m_hash = hash_value(user_data.medical_license)
        if db.query(User).filter(User.medical_license_hash == m_hash).first():
            raise HTTPException(
                status_code=400, detail="This Medical License is already registered.")

    try:
        # Note: We rely on the User model setters to handle encryption/hashing transparently!
        new_user = User(
            email=user_data.email, # Setter handles email_encrypted / email_hash
            phone_number=user_data.phone_number, # Setter handles phone_number_encrypted / phone_number_hash
            password_hash=hash_password(user_data.password),
            full_name=user_data.full_name, # Setter handles full_name_encrypted / full_name_hash
            role=user_data.role,
            verification_status="pending" if user_data.role == "doctor" else "verified", # Auto-verify patients, pending for doctors
            
            # Using properties for transparent encryption
            citizen_id=user_data.citizen_id, 
            medical_license=user_data.medical_license,
            date_of_birth=user_data.date_of_birth, # Setup takes date, converts to iso str -> encrypts
            
            gender=user_data.gender,
            blood_type=user_data.blood_type,
            height=user_data.height,
            weight=user_data.weight,
            
            is_email_verified=bool(user_data.email),
            is_phone_verified=bool(user_data.phone_number),
            
            created_at=now_th(),
            updated_at=now_th()
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        if new_user.role == "doctor":
             from ..utils.background_tasks import verify_doctor_background
             # Accessing properties decrypts them for usage
             full_name_clean = new_user.full_name
             if full_name_clean:
                 fname = full_name_clean.split()[0]
                 lname = full_name_clean.split()[-1] if len(full_name_clean.split()) > 1 else ""
                 background_tasks.add_task(verify_doctor_background, new_user.id, fname, lname, db)

        logger.info(
            f"New user registered: {contact_target} - Role: {new_user.role} - Request ID: {request_id}"
        )

        return create_standard_response(
            status="success",
            message="User registered successfully",
            data={
                "user_id": new_user.id,
                "email": new_user.email,
                "phone_number": new_user.phone_number,
                "role": new_user.role,
                "is_email_verified": new_user.is_email_verified,
                "is_phone_verified": new_user.is_phone_verified
            },
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Registration failed: {str(e)} - Request ID: {request_id}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login", tags=["authentication"])
@limiter.limit("5/minute")
async def login(
    request: Request,
    user_credentials: UserLogin,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """User login with email or phone number"""
    request_id = generate_request_id()

    # Find user by email or phone via HASH
    if user_credentials.email:
        email_h = hash_value(user_credentials.email)
        user = db.query(User).filter(
            User.email_hash == email_h).first()
    else:
        phone_h = hash_value(user_credentials.phone_number)
        user = db.query(User).filter(User.phone_number_hash == phone_h).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check if account is locked
    if is_account_locked(user):
        raise HTTPException(
            status_code=423, detail="Account temporarily locked due to multiple failed attempts")

    # Verify password
    if not verify_password(user_credentials.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            lock_account(user, db)
            logger.warning(
                f"Account locked due to failed attempts (ID: {user.id}) - Request ID: {request_id}")
            raise HTTPException(
                status_code=423, detail="Account locked due to multiple failed attempts")

        db.commit()
        logger.warning(
            f"Failed login attempt (ID: {user.id}) - Attempts: {user.failed_login_attempts} - Request ID: {request_id}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is deactivated")

    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.last_login = now_th()
    user.account_locked_until = None
    db.commit()

    # Create tokens
    # Access properties to get decrypted email/phone for token payload (if needed) or just ID
    token_data = {"user_id": user.id, "email": user.email}

    if user_credentials.remember_me:
        expires_delta = timedelta(days=30)
    else:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data=token_data, expires_delta=expires_delta)
    refresh_token = create_refresh_token(data=token_data)

    # Create session record
    session = UserSession(
        user_id=user.id,
        session_token=secrets.token_urlsafe(32),
        device_info=request.headers.get("user-agent", "")[:500],
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", "")[:500],
        expires_at=now_th() + expires_delta
    )

    db.add(session)
    db.commit()

    logger.info(
        f"Successful login (ID: {user.id}) - Request ID: {request_id}")

    return create_standard_response(
        status="success",
        message="Login successful",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(expires_delta.total_seconds()),
            "user": {
                "id": user.id,
                "email": user.email,
                "phone_number": user.phone_number,
                "role": user.role,
                "full_name": user.full_name,
                "is_email_verified": user.is_email_verified,
                "is_phone_verified": user.is_phone_verified,
                "subscription_tier": user.subscription_tier # New field
            }
        },
        request_id=request_id
    )


@router.post("/logout", tags=["authentication"])
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Logout user and invalidate session"""
    request_id = generate_request_id()

    # Invalidate all active sessions for this user
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True
    ).update({"is_active": False})

    db.commit()

    logger.info(
        f"User logged out: {current_user.id} - Request ID: {request_id}")

    return create_standard_response(
        status="success",
        message="Logged out successfully",
        request_id=request_id
    )


@router.post("/change-password", tags=["authentication"])
async def change_password(
    request: Request,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Change password for authenticated user"""
    request_id = generate_request_id()

    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=400, detail="Current password is incorrect")

    try:
        # Update password
        current_user.password_hash = hash_password(password_data.new_password)
        current_user.updated_at = now_th()

        # Invalidate all sessions except current one
        db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True
        ).update({"is_active": False})

        db.commit()

        logger.info(
            f"Password changed for user: {current_user.id} - Request ID: {request_id}")

        return create_standard_response(
            status="success",
            message="Password changed successfully",
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Password change failed: {str(e)} - Request ID: {request_id}")
        raise HTTPException(
            status_code=500, detail="Failed to change password")


@router.post("/reset-password", tags=["authentication"])
@limiter.limit("3/minute")
async def reset_password(
    request: Request,
    reset_data: PasswordReset,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Reset password via OTP verification"""
    request_id = generate_request_id()

    # Find user by email or phone via HASH
    if reset_data.email:
        email_h = hash_value(reset_data.email)
        user = db.query(User).filter(User.email_hash == email_h).first()
    else:
        phone_h = hash_value(reset_data.phone_number)
        user = db.query(User).filter(User.phone_number_hash == phone_h).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify OTP (in-memory)
    contact_target = (
        reset_data.email or reset_data.phone_number).strip().lower()
    if not otp_service.confirm_otp(contact_target, reset_data.otp_code):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    try:
        # Update password and unlock account
        user.password_hash = hash_password(reset_data.new_password)
        user.updated_at = now_th()
        user.failed_login_attempts = 0
        user.account_locked_until = None

        # Invalidate all user sessions
        db.query(UserSession).filter(UserSession.user_id == user.id).delete()

        db.commit()

        logger.info(
            f"Password reset successful for user: {user.id} - Request ID: {request_id}"
        )

        return create_standard_response(
            status="success",
            message="Password reset successful",
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Password reset failed: {str(e)} - Request ID: {request_id}")
        raise HTTPException(status_code=500, detail="Password reset failed")

@router.post("/verify-contact", tags=["authentication"])
@limiter.limit("3/minute")
async def verify_contact_method(
    request: Request,
    verification_data: OTPVerification,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Verify email or phone number for existing user"""
    request_id = generate_request_id()

    contact_target = (
        verification_data.email or verification_data.phone_number).strip().lower()

    # In-memory OTP verification
    if not otp_service.confirm_otp(contact_target, verification_data.otp_code):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    try:
        # Update user verification flags and contact info
        # Note: Setters handle encryption/hashing
        if verification_data.purpose == "email_verification":
            current_user.is_email_verified = True
            current_user.email = contact_target 
        elif verification_data.purpose == "phone_verification":
            current_user.is_phone_verified = True
            current_user.phone_number = contact_target

        current_user.updated_at = now_th()
        db.commit()

        logger.info(
            f"Contact verified - User: {current_user.id} - Type: {verification_data.purpose} - Request ID: {request_id}"
        )

        return create_standard_response(
            status="success",
            message="Contact method verified successfully",
            data={
                "verified": True,
                "contact_type": verification_data.purpose,
                "contact_target": contact_target
            },
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Contact verification failed: {str(e)} - Request ID: {request_id}")
        raise HTTPException(
            status_code=500, detail="Failed to verify contact method")


@router.post("/telegram/generate-link", tags=["authentication"])
async def generate_telegram_link(
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """Generate a deep link to connect Telegram account"""
    request_id = generate_request_id()
    
    # Create a short-lived token for verification (10 minutes)
    token_data = {
        "user_id": current_user.id, 
        "purpose": "telegram_connect"
    }
    token = create_access_token(token_data, expires_delta=timedelta(minutes=10))
    
    # Replace with your actual Bot Username
    # In production, this should be in env or config
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "BPMonitor_Bot") 
    
    link = f"https://t.me/{bot_username}?start=verify_{token}"
    
    return create_standard_response(
        status="success",
        message="Link generated",
        data={"link": link},
        request_id=request_id
    )
