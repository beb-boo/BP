
from fastapi import APIRouter, HTTPException, Depends, Request, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from ..database import get_db
from ..models import User, BloodPressureRecord
from ..schemas import (
    StandardResponse, BloodPressureRecordCreate,
    BloodPressureRecordResponse, BloodPressureRecordUpdate, PaginationMeta
)
from ..utils.security import verify_api_key, get_current_user, check_premium
from ..utils.timezone import now_th
from ..utils.chart_generator import generate_bp_chart
import logging
import uuid
import statistics as stats_module
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
    is_premium = check_premium(current_user)

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
    from sqlalchemy import func
    expected_date = record.measurement_date.date() if record.measurement_date else now_th().date()
    
    existing = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id,
        func.date(BloodPressureRecord.measurement_date) == expected_date,
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

def classify_bp(avg_sys: float, avg_dia: float) -> dict:
    """Classify BP based on AHA/ACC 2017 guidelines using average values."""
    if avg_sys > 180 or avg_dia > 120:
        return {"level": "hypertensive_crisis", "label_en": "Hypertensive Crisis", "label_th": "วิกฤตความดันสูง"}
    elif avg_sys >= 140 or avg_dia >= 90:
        return {"level": "stage_2", "label_en": "Stage 2 Hypertension", "label_th": "ความดันสูงระยะที่ 2"}
    elif (130 <= avg_sys <= 139) or (80 <= avg_dia <= 89):
        return {"level": "stage_1", "label_en": "Stage 1 Hypertension", "label_th": "ความดันสูงระยะที่ 1"}
    elif 120 <= avg_sys <= 129 and avg_dia < 80:
        return {"level": "elevated", "label_en": "Elevated", "label_th": "ความดันสูงเล็กน้อย"}
    else:
        return {"level": "normal", "label_en": "Normal", "label_th": "ปกติ"}


def compute_trend(records) -> dict:
    """Compute linear regression slope for systolic and diastolic over time."""
    if len(records) < 3:
        return {"systolic_slope": 0, "diastolic_slope": 0, "direction": "stable"}

    # Sort chronologically (oldest first)
    sorted_records = sorted(records, key=lambda r: r.measurement_date)
    base_date = sorted_records[0].measurement_date
    x_days = [(r.measurement_date - base_date).total_seconds() / 86400 for r in sorted_records]

    def linear_slope(x_vals, y_vals):
        n = len(x_vals)
        if n < 2:
            return 0.0
        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
        denominator = sum((x - x_mean) ** 2 for x in x_vals)
        return numerator / denominator if denominator != 0 else 0.0

    sys_slope = round(linear_slope(x_days, [r.systolic for r in sorted_records]), 2)
    dia_slope = round(linear_slope(x_days, [r.diastolic for r in sorted_records]), 2)

    # Direction based on systolic slope significance
    if sys_slope > 0.5:
        direction = "increasing"
    elif sys_slope < -0.5:
        direction = "decreasing"
    else:
        direction = "stable"

    return {"systolic_slope": sys_slope, "diastolic_slope": dia_slope, "direction": direction}


@stats_router.get("/summary", response_model=StandardResponse)
async def get_bp_stats(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Get blood pressure statistics with clinical metrics.

    Free tier: avg, min, max, classification.
    Premium tier: + SD, median, CV, pulse pressure, MAP, trend analysis.
    """
    request_id = generate_request_id()

    # --- Premium check ---
    is_premium = check_premium(current_user)

    # --- Query records ---
    # Both tiers: get latest N records (count-based, not date-based)
    # Free: max 30 records, Premium: up to `days` records (no hard cap)
    query = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id
    ).order_by(desc(BloodPressureRecord.measurement_date))

    if is_premium:
        records = query.limit(days).all()
    else:
        records = query.limit(30).all()

    # Total all-time count
    total_all_time = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id
    ).count()

    if not records:
        return create_standard_response(
            status="success",
            message="No records found",
            data={
                "period_days": days,
                "is_premium": is_premium,
                "stats": {
                    "systolic": {"avg": 0, "min": 0, "max": 0},
                    "diastolic": {"avg": 0, "min": 0, "max": 0},
                    "pulse": {"avg": 0, "min": 0, "max": 0},
                    "classification": classify_bp(0, 0),
                    "total_records_period": 0,
                    "total_records_all_time": total_all_time
                }
            },
            request_id=request_id
        )

    # --- Extract values ---
    systolic_values = [r.systolic for r in records]
    diastolic_values = [r.diastolic for r in records]
    pulse_values = [r.pulse for r in records]
    n = len(records)

    # --- Basic stats (Free + Premium) ---
    avg_sys = round(sum(systolic_values) / n, 1)
    avg_dia = round(sum(diastolic_values) / n, 1)
    avg_pulse = round(sum(pulse_values) / n, 1)

    bp_stats = {
        "systolic": {
            "avg": avg_sys,
            "min": min(systolic_values),
            "max": max(systolic_values)
        },
        "diastolic": {
            "avg": avg_dia,
            "min": min(diastolic_values),
            "max": max(diastolic_values)
        },
        "pulse": {
            "avg": avg_pulse,
            "min": min(pulse_values),
            "max": max(pulse_values)
        },
        "classification": classify_bp(avg_sys, avg_dia),
        "total_records_period": n,
        "total_records_all_time": total_all_time
    }

    # --- Advanced stats (Premium only) ---
    if is_premium:
        has_enough = n >= 2

        # SD, Median, CV for each metric
        for key, values in [("systolic", systolic_values), ("diastolic", diastolic_values), ("pulse", pulse_values)]:
            sd = round(stats_module.stdev(values), 1) if has_enough else 0
            median = round(stats_module.median(values), 1)
            avg_val = bp_stats[key]["avg"]
            cv = round((sd / avg_val) * 100, 1) if avg_val > 0 and has_enough else 0
            bp_stats[key]["sd"] = sd
            bp_stats[key]["median"] = median
            bp_stats[key]["cv"] = cv

        # Pulse Pressure (SBP - DBP)
        pp_values = [s - d for s, d in zip(systolic_values, diastolic_values)]
        bp_stats["pulse_pressure"] = {
            "avg": round(sum(pp_values) / n, 1),
            "min": min(pp_values),
            "max": max(pp_values)
        }

        # MAP = (SBP + 2*DBP) / 3
        map_values = [(s + 2 * d) / 3 for s, d in zip(systolic_values, diastolic_values)]
        bp_stats["map"] = {
            "avg": round(sum(map_values) / n, 1),
            "min": round(min(map_values), 1),
            "max": round(max(map_values), 1)
        }

        # Trend Analysis
        bp_stats["trend"] = compute_trend(records)

    return create_standard_response(
        status="success",
        message="Statistics calculated successfully",
        data={
            "period_days": days,
            "is_premium": is_premium,
            "stats": bp_stats
        },
        request_id=request_id
    )


@stats_router.get("/chart")
async def get_bp_chart(
    days: int = Query(default=30, ge=1, le=365, description="Number of recent records to include"),
    lang: str = Query(default="en", pattern="^(en|th)$", description="Language: en or th"),
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Generate a BP trend chart as a PNG image.

    Returns a PNG image showing Systolic, Diastolic, and Pulse trends
    with reference zones for High BP areas. Data labels show SYS/DIA
    values on the chart and Pulse values below.
    """
    # Fetch recent records (most recent N records)
    records = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id
    ).order_by(
        desc(BloodPressureRecord.measurement_date)
    ).limit(days).all()

    # Generate chart (handles empty records internally)
    try:
        chart_buffer = generate_bp_chart(records, lang=lang)
    except RuntimeError as e:
        logger.error(f"Chart generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chart generation unavailable: {e}"
        )

    return StreamingResponse(
        chart_buffer,
        media_type="image/png",
        headers={
            "Content-Disposition": "inline; filename=bp-chart.png",
            "Cache-Control": "no-cache"
        }
    )
