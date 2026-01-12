
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

    # Convert to response model
    data = [BloodPressureRecordResponse.model_validate(
        record).dict() for record in records]

    pagination = PaginationMeta(
        current_page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages
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

    start_date = now_th() - timedelta(days=days)

    records = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id,
        BloodPressureRecord.measurement_date >= start_date
    ).all()

    if not records:
        return create_standard_response(
            status="success",
            message=f"No records found in last {days} days",
            data={
                "count": 0,
                "period_days": days,
                "stats": None
            },
            request_id=request_id
        )

    # Calculate stats
    # Calculate stats
    systolic_values = [r.systolic for r in records]
    diastolic_values = [r.diastolic for r in records]
    pulse_values = [r.pulse for r in records]

    # Get total all time count
    total_all_time = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id
    ).count()

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
