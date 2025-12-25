
from fastapi import APIRouter, HTTPException, Depends, Request, status
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
from ..utils.notification import send_email_otp, send_sms_otp, OTP_EXPIRE_MINUTES
import logging
import uuid
import secrets
from datetime import timedelta
from ..otp_service import OTPService
from slowapi import Limiter
from slowapi.util import get_remote_address

# Setup
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
logger = logging.getLogger(__name__)

# Note: In a real app, limiter should be initialized in main and passed down, 
# or we use a global instance. For this refactor, we instantiate a dummy one 
# or import if we move it to common. 
# Better strategy: creating a common "limiter" dependency in utils/common.py is best 
# but for now to minimize changes, I will re-declare it or skip it on router level 
# if it requires app state.
# Slowapi limits apply to decorators. If we don't attach it to app, it won't work.
# We will need to attach this router to app with limiter state.
limiter = Limiter(key_func=get_remote_address)

otp_service = OTPService()

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

    # Check for existing users
    if user_data.email:
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=400, detail="Email already registered")

    if user_data.phone_number:
        if db.query(User).filter(User.phone_number == user_data.phone_number).first():
            raise HTTPException(
                status_code=400, detail="Phone number already registered")

    if user_data.role == "doctor" and user_data.medical_license:
        if db.query(User).filter(User.medical_license == user_data.medical_license).first():
            raise HTTPException(
                status_code=400, detail="Medical license already registered")

    try:
        new_user = User(
            email=user_data.email,
            phone_number=user_data.phone_number,
            password_hash=hash_password(user_data.password),
            full_name=user_data.full_name,
            role=user_data.role,
            citizen_id=user_data.citizen_id,
            medical_license=user_data.medical_license,
            date_of_birth=user_data.date_of_birth,
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

    # Find user by email or phone
    if user_credentials.email:
        user = db.query(User).filter(
            User.email == user_credentials.email).first()
    else:
        user = db.query(User).filter(User.phone_number ==
                                     user_credentials.phone_number).first()

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
                f"Account locked due to failed attempts: {user.email or user.phone_number} - Request ID: {request_id}")
            raise HTTPException(
                status_code=423, detail="Account locked due to multiple failed attempts")

        db.commit()
        logger.warning(
            f"Failed login attempt: {user.email or user.phone_number} - Attempts: {user.failed_login_attempts} - Request ID: {request_id}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is deactivated")

    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.last_login = now_th()
    user.account_locked_until = None
    db.commit()

    # Create tokens
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
        f"Successful login: {user.email or user.phone_number} - Request ID: {request_id}")

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
                "is_phone_verified": user.is_phone_verified
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
        f"User logged out: {current_user.email or current_user.phone_number} - Request ID: {request_id}")

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
            f"Password changed for user: {current_user.email or current_user.phone_number} - Request ID: {request_id}")

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

    # Find user by email or phone
    if reset_data.email:
        user = db.query(User).filter(User.email == reset_data.email).first()
    else:
        user = db.query(User).filter(User.phone_number ==
                                     reset_data.phone_number).first()

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
            f"Password reset successful for user: {contact_target} - Request ID: {request_id}"
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
