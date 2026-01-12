
from fastapi import APIRouter, HTTPException, Depends, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import get_db
from ..models import User
from ..schemas import StandardResponse, UserProfileResponse, UserProfileUpdate
from ..utils.security import verify_api_key, get_current_user, now_th, verify_password
from ..utils.encryption import decrypt_value, encrypt_value, hash_value
from ..otp_service import otp_service
import hashlib
import logging
import uuid
from typing import Optional

router = APIRouter(prefix="/api/v1/users", tags=["user"])
logger = logging.getLogger(__name__)

def generate_request_id() -> str:
    return str(uuid.uuid4())

def create_standard_response(status, message, data=None, request_id=None):
    return StandardResponse(
        status=status,
        message=message,
        data=data,
        request_id=request_id or generate_request_id()
    )


@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """Get current user profile"""
    request_id = generate_request_id()

    # Note: Pydantic model_validate will access properties (like .email, .full_name)
    # which automatically triggers the @property getter that DECRYPTS the value.
    user_profile = UserProfileResponse.model_validate(current_user)
    
    user_data = user_profile.dict()
    # Explicitly handle decrypted fields if manual override needed, 
    # but the Model properties should handle it.
    
    return create_standard_response(
        status="success",
        message="Profile retrieved successfully",
        data={"profile": user_data},
        request_id=request_id
    )


@router.put("/me", response_model=StandardResponse)
async def update_user_profile(
    user_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    request_id = generate_request_id()
    
    # 1. Check for sensitive changes (Email/Phone) -> Require Password
    sensitive_changed = False
    if user_update.email is not None and user_update.email != current_user.email:
        sensitive_changed = True
    if user_update.phone_number is not None and user_update.phone_number != current_user.phone_number:
        sensitive_changed = True
        
    if sensitive_changed:
        if not user_update.current_password or not verify_password(user_update.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=403, 
                detail="Security Check Failed: Incorrect current password."
            )

    # 2. Strong Security: Check if Email-based 2FA is possible and required (Phone Change)
    if user_update.phone_number and user_update.phone_number != current_user.phone_number:
         # If user has an email, enforce OTP for phone change
         if current_user.email:
             if not user_update.otp_code:
                 raise HTTPException(
                     status_code=403,
                     detail="2FA Required: Please enter the OTP sent to your email to change phone number."
                 )
             
             # Verify OTP
             is_valid_otp = otp_service.confirm_otp(
                 contact_target=current_user.email,
                 otp=user_update.otp_code
             )
             if not is_valid_otp:
                 raise HTTPException(status_code=403, detail="Invalid or expired OTP.")

    # Check if phone number is already taken by another user
    if user_update.phone_number and user_update.phone_number != current_user.phone_number:
        # Check uniqueness via HASH
        phone_h = hash_value(user_update.phone_number)
        existing_user = db.query(User).filter(
            User.phone_number_hash == phone_h,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=400, detail="Phone number already taken")
        
        # Phone changed: Reset verification and unlink Telegram
        current_user.is_phone_verified = False
        current_user.telegram_id = None

    # Check if email is already taken by another user
    if user_update.email and user_update.email != current_user.email:
        email_h = hash_value(user_update.email)
        existing_user = db.query(User).filter(
            User.email_hash == email_h,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=400, detail="Email already taken")
        
        # Reset email verification status
        current_user.is_email_verified = False

    # Check if medical license is already taken (for doctors)
    if (user_update.medical_license and
        current_user.role == "doctor" and
            user_update.medical_license != current_user.medical_license):
        
        med_h = hash_value(user_update.medical_license)
        existing_doctor = db.query(User).filter(
            User.medical_license_hash == med_h,
            User.id != current_user.id
        ).first()
        if existing_doctor:
            raise HTTPException(
                status_code=400, detail="Medical license already taken")

    # Check for citizen_id via hash if updating
    if user_update.citizen_id:
        c_hash = hash_value(user_update.citizen_id)
        if c_hash:
            existing = db.query(User).filter(User.citizen_id_hash == c_hash, User.id != current_user.id).first()
            if existing:
                 raise HTTPException(status_code=400, detail="Citizen ID already registered")

    try:
        # Update fields
        update_data = user_update.dict(exclude_unset=True)
        # Remove partial fields
        update_data.pop('current_password', None)
        update_data.pop('otp_code', None)
        
        for field, value in update_data.items():
            # Use setattr on the Model property
            # This triggers the @property setter which Encrypts and Hashes automatically
            # Example: current_user.full_name = "..." -> encrypts full_name_encrypted, hashes full_name_hash
            setattr(current_user, field, value)

        current_user.updated_at = now_th()
        db.commit()
        db.refresh(current_user)

        logger.info(
            f"Profile updated for user: {current_user.id} - Request ID: {request_id}")

        user_profile = UserProfileResponse.model_validate(current_user)
        user_data = user_profile.dict()
        
        # Ensure sensitive fields are returned decrypted (Properties handle this)
        return create_standard_response(
            status="success",
            message="Profile updated successfully",
            data={"profile": user_data},
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Profile update failed for user {current_user.id}: {str(e)} - Request ID: {request_id}")
        raise HTTPException(status_code=500, detail="Profile update failed")

@router.get("/search", response_model=StandardResponse)
async def search_users(
    query: str,
    role: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    # Search users mainly for doctor to find patient or vice versa
    request_id = generate_request_id()
    
    # Exact Match Search via Hash
    # Supports: Full Name, Phone, Email
    query_hash = hash_value(query)
    
    if not query_hash:
        # Empty query
        return create_standard_response(status="success", message="Empty query", data={"users": []})

    users_query = db.query(User).filter(
        or_(
            User.full_name_hash == query_hash,
            User.phone_number_hash == query_hash,
            User.email_hash == query_hash
        )
    )
    
    if role:
        users_query = users_query.filter(User.role == role)
        
    users = users_query.limit(20).all()
    
    results = []
    for u in users:
        # Access properties to decrypt
        results.append({
            "id": u.id,
            "full_name": u.full_name,
            "role": u.role,
            "phone_number": u.phone_number
        })
        
    return create_standard_response(
        status="success",
        message="Search completed",
        data={"users": results},
        request_id=request_id
    )
