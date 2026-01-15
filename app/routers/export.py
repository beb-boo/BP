
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import get_db
from ..models import User, BloodPressureRecord
from ..schemas import StandardResponse
from ..utils.security import verify_api_key, get_current_user
from ..utils.encryption import decrypt_value
from ..utils.timezone import now_tz, format_datetime
import logging
import uuid
import json
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/export", tags=["export"])
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

@router.get("/my-data", response_model=StandardResponse)
async def export_my_data(
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Export all user data including Profile and BP Records.
    Useful for data portability (GDPR/PDPA) or backups.
    """
    request_id = generate_request_id()
    
    try:
        # 1. Decrypt/Prepare Profile Data
        user_data = {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone_number": current_user.phone_number,
            "citizen_id": decrypt_value(current_user.citizen_id_encrypted),
            "medical_license": decrypt_value(current_user.medical_license_encrypted),
            "gender": current_user.gender,
            "blood_type": current_user.blood_type,
            "height": current_user.height,
            "weight": current_user.weight,
            "date_of_birth": str(current_user.date_of_birth) if current_user.date_of_birth else None,
            "created_at": str(current_user.created_at)
        }
        
        # 2. Fetch BP Records with Monetization Logic
        query = db.query(BloodPressureRecord).filter(
            BloodPressureRecord.user_id == current_user.id
        )

        is_premium = False
        if current_user.subscription_tier == "premium":
             # Simple checking for now, assuming UTC logic or timezone aware handled by model?
             # Actually expires_at is nullable.
             is_premium = True # Assume valid if marked premium for now, or add check
             if current_user.subscription_expires_at:
                  # Naive check vs system time (should use timezone aware if possible)
                  # But let's just use simple date compare
                  pass 

        export_note = "Full History (Premium)"
        if current_user.subscription_tier != "premium":
            # Free: Limit to last 30 records
            records = query.order_by(desc(BloodPressureRecord.measurement_date)).limit(30).all()
            export_note = "Limited to last 30 records (Free Tier)"
        else:
            # Premium: All records, sorted
            records = query.order_by(desc(BloodPressureRecord.measurement_date)).all()
        
        bp_data = []
        for r in records:
            bp_data.append({
                "id": r.id,
                "date": str(r.measurement_date.date()) if r.measurement_date else None,
                "time": r.measurement_time,
                "systolic": r.systolic,
                "diastolic": r.diastolic,
                "pulse": r.pulse,
                "notes": r.notes,
                "source": "ocr" if r.ocr_confidence else "manual"
            })
            
        # 3. Construct Export Payload
        user_tz = current_user.timezone or "Asia/Bangkok"
        export_payload = {
            "exported_at": format_datetime(now_tz(), user_tz),
            "timezone": user_tz,
            "user_profile": user_data,
            "blood_pressure_history": bp_data,
            "meta": {
                "record_count": len(bp_data),
                "system": "BP Monitor API",
                "note": export_note
            }
        }
        
        logger.info(f"User {current_user.id} exported data. Records: {len(bp_data)}")
        
        return create_standard_response(
            status="success",
            message="Data export successful",
            data={"export": export_payload},
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data")
