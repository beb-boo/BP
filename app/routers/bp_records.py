
from fastapi import APIRouter, HTTPException, Depends, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from ..database import get_db
from ..models import User, BloodPressureRecord
from ..schemas import (
    StandardResponse, BloodPressureRecordCreate,
    BloodPressureRecordResponse, BloodPressureRecordUpdate, PaginationMeta
)
from ..utils.security import verify_api_key, get_current_user, now_th
import logging
import uuid
from typing import Optional, List
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/bp-records", tags=["blood pressure"])
stats_router = APIRouter(prefix="/api/v1/stats", tags=["blood pressure"])
logger = logging.getLogger(__name__)

def generate_request_id() -> str:
    return str(uuid.uuid4())

def create_standard_response(status, message, data=None, request_id=None, meta=None):
    return StandardResponse(
        status=status,
        message=message,
        data=data,
        meta=meta,
        request_id=request_id or generate_request_id()
    )


@router.get("", response_model=StandardResponse)
async def get_bp_records(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Get blood pressure records with pagination and filtering"""
    request_id = generate_request_id()

    # Base query
    query = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id
    )

    # Apply filters
    if start_date:
        query = query.filter(BloodPressureRecord.measurement_date >= start_date)
    if end_date:
        query = query.filter(BloodPressureRecord.measurement_date <= end_date)

    # --- Monetization Logic: Free Tier Limit (Last 30 Days) ---
    is_premium = False
    if current_user.subscription_tier == "premium":
        # Check expiry
        if current_user.subscription_expires_at and current_user.subscription_expires_at > now_th():
            is_premium = True
        else:
            # Expired, fallback to free
            is_premium = False
    
    if not is_premium:
        # Free User: Restrict to latest 30 records
        # limit() applies to the result set. Since we sort by date desc later, 
        # we need to be careful. Ideally we apply the limit on the query that is ORDERED.
        # But SQLAlchemy limit applies to the returned rows.
        # If we just want to HIDE records > 30:
        # We can just check the total count or restricted view.
        # Simple implementation: Let pagination handle naturally, but set a conceptual max.
        # Actually, user wants "Last 30 Records".
        # So we just ensure the user can't paginate past record 30.
        pass
    # ----------------------------------------------------------

    # Get total count for pagination
    total = query.count()

    # Apply pagination
    total_pages = (total + per_page - 1) // per_page
    if page < 1:
        page = 1
    if page > total_pages and total > 0:
        page = total_pages

    records = query.order_by(desc(BloodPressureRecord.measurement_date))\
        .offset((page - 1) * per_page)\
        .limit(per_page)\
        .all()
        
    if not is_premium:
        # Strict Limit: 30 Records Max
        start_idx = (page - 1) * per_page
        if start_idx >= 30:
            records = []
        else:
            # If requesting overlapping range (e.g. 20-40), cut off at 30
            end_idx = start_idx + len(records)
            if end_idx > 30:
                allowed_count = 30 - start_idx
                records = records[:allowed_count]

    # Convert to response model
    data = [BloodPressureRecordResponse.model_validate(
        record).dict() for record in records]

    pagination = PaginationMeta(
        current_page=page,
        per_page=per_page,
        total=total if is_premium else min(total, 30), # Cap reported total
        total_pages=total_pages if is_premium else (min(total, 30) + per_page - 1) // per_page
    )

    return create_standard_response(
        status="success",
        message="Records retrieved successfully",
        data={"records": data},
        meta={"pagination": pagination.dict()},
        request_id=request_id
    )


@router.post("", response_model=StandardResponse)
async def create_bp_record(
    record: BloodPressureRecordCreate,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Create a new blood pressure record manually"""
    request_id = generate_request_id()
    
    # Duplicate Check
    existing = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id,
        BloodPressureRecord.measurement_date == record.measurement_date,
        BloodPressureRecord.measurement_time == record.measurement_time,
        BloodPressureRecord.systolic == record.systolic,
        BloodPressureRecord.diastolic == record.diastolic,
        BloodPressureRecord.pulse == record.pulse
    ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail="Record already exists (Duplicate ignored)")

    new_record = BloodPressureRecord(
        user_id=current_user.id,
        systolic=record.systolic,
        diastolic=record.diastolic,
        pulse=record.pulse,
        measurement_date=record.measurement_date,
        measurement_time=record.measurement_time,
        notes=record.notes,
        created_at=now_th()
    )

    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    logger.info(
        f"BP record created for user: {current_user.id} - Request ID: {request_id}")

    return create_standard_response(
        status="success",
        message="Record created successfully",
        data={"record": BloodPressureRecordResponse.model_validate(
            new_record).dict()},
        request_id=request_id
    )


@router.get("/{record_id}", response_model=StandardResponse)
async def get_bp_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Get a specific blood pressure record"""
    request_id = generate_request_id()

    record = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.id == record_id,
        BloodPressureRecord.user_id == current_user.id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    return create_standard_response(
        status="success",
        message="Record retrieved successfully",
        data={"record": BloodPressureRecordResponse.model_validate(
            record).dict()},
        request_id=request_id
    )


@router.put("/{record_id}", response_model=StandardResponse)
async def update_bp_record(
    record_id: int,
    record_update: BloodPressureRecordUpdate,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Update a blood pressure record"""
    request_id = generate_request_id()

    record = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.id == record_id,
        BloodPressureRecord.user_id == current_user.id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    update_data = record_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)

    logger.info(
        f"BP record updated: {record_id} for user {current_user.id} - Request ID: {request_id}")

    return create_standard_response(
        status="success",
        message="Record updated successfully",
        data={"record": BloodPressureRecordResponse.model_validate(
            record).dict()},
        request_id=request_id
    )


@router.delete("/{record_id}", response_model=StandardResponse)
async def delete_bp_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Delete a blood pressure record"""
    request_id = generate_request_id()

    record = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.id == record_id,
        BloodPressureRecord.user_id == current_user.id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    db.delete(record)
    db.commit()

    logger.info(
        f"BP record deleted: {record_id} for user {current_user.id} - Request ID: {request_id}")

    return create_standard_response(
        status="success",
        message="Record deleted successfully",
        request_id=request_id
    )

@stats_router.get("/summary", response_model=StandardResponse)
async def get_bp_stats(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Get blood pressure statistics (avg, min, max)"""
    request_id = generate_request_id()

    # If Free Tier, standard is limit to latest 30 records (not days)
    # Logic: Get Latest N records, then stats them.
    
    query = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id
    )
    
    # Use 'days' roughly as 'count' limit for stats if Free
    limit_count = 30 
    
    records = query.order_by(desc(BloodPressureRecord.measurement_date))\
                   .limit(limit_count)\
                   .all()

    # Get total all time count (Always calculate this)
    total_all_time = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id
    ).count()

    if not records:
        return create_standard_response(
            status="success",
            message=f"No records found in last {days} days",
            data={
                "period_days": days, # Fix key consistency
                "stats": {
                    "systolic": {"avg": 0, "min": 0, "max": 0},
                    "diastolic": {"avg": 0, "min": 0, "max": 0},
                    "pulse": {"avg": 0, "min": 0, "max": 0},
                    "total_records_period": 0,
                    "total_records_all_time": total_all_time
                }
            },
            request_id=request_id
        )

    # Calculate stats
    # Calculate stats
    systolic_values = [r.systolic for r in records]
    diastolic_values = [r.diastolic for r in records]
    pulse_values = [r.pulse for r in records]

    pulse_values = [r.pulse for r in records]

    # total_all_time is already calculated above

    stats = {
        "systolic": {
            "avg": sum(systolic_values) / len(records) if records else 0,
            "min": min(systolic_values) if records else 0,
            "max": max(systolic_values) if records else 0
        },
        "diastolic": {
            "avg": sum(diastolic_values) / len(records) if records else 0,
            "min": min(diastolic_values) if records else 0,
            "max": max(diastolic_values) if records else 0
        },
        "pulse": {
            "avg": sum(pulse_values) / len(records) if records else 0,
            "min": min(pulse_values) if records else 0,
            "max": max(pulse_values) if records else 0
        },
        "total_records_period": len(records),
        "total_records_all_time": total_all_time
    }

    return create_standard_response(
        status="success",
        message="Statistics calculated successfully",
        data={
            "period_days": days,
            "stats": stats
        },
        request_id=request_id
    )
