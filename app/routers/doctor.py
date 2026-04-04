
from fastapi import APIRouter, HTTPException, Depends, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import get_db
from ..models import User, DoctorPatient, AccessRequest, BloodPressureRecord
from ..schemas import (
    StandardResponse, DoctorAuthorizationInput, AccessRequestInput,
    BloodPressureRecordResponse, PaginationMeta, DoctorSearchResult
)
from ..utils.encryption import hash_value
from ..utils.security import verify_api_key, get_current_user, require_verified_doctor
from ..utils.timezone import now_th
import json
import logging
import uuid

router = APIRouter(prefix="/api/v1", tags=["doctor view"]) # We have both doctor and patient view here
# Or we can split into /doctor and /patient prefixes but keeping them in one file for relation logic is fine.
# We will use specific prefixes in decorators.

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

# ==========================
# Patient View (Managing Doctors)
# ==========================

@router.post("/patient/authorize-doctor", response_model=StandardResponse, tags=["patient view"])
async def authorize_doctor(
    data: DoctorAuthorizationInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient directly authorizes a doctor"""
    request_id = generate_request_id()

    if current_user.role != "patient":
        raise HTTPException(
            status_code=403, detail="Only patients can authorize doctors")

    doctor = db.query(User).filter(
        User.id == data.doctor_id,
        User.role == "doctor"
    ).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    if doctor.verification_status != "verified":
        raise HTTPException(
            status_code=400,
            detail="This doctor's license has not been verified yet"
        )

    existing = db.query(DoctorPatient).filter_by(
        doctor_id=doctor.id,
        patient_id=current_user.id,
        is_active=True
    ).first()

    if existing:
        raise HTTPException(
            status_code=400, detail="You already authorized this doctor")

    try:
        relation = DoctorPatient(
            doctor_id=doctor.id,
            patient_id=current_user.id,
            hospital=None 
        )

        db.add(relation)
        db.commit()
        db.refresh(relation)

        return create_standard_response(
            status="success",
            message="Doctor authorized successfully",
            data={
                "relation": {
                    "relation_id": relation.id,
                    "doctor_name": doctor.full_name,
                    "created_at": relation.created_at
                }
            },
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to authorize doctor: {e} - Request ID: {request_id}")
        raise HTTPException(status_code=500, detail="Failed to authorize doctor")


@router.get("/patient/authorized-doctors", response_model=StandardResponse, tags=["patient view"])
async def get_authorized_doctors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    request_id = generate_request_id()
    
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients view")

    relations = db.query(DoctorPatient).filter(
        DoctorPatient.patient_id == current_user.id,
        DoctorPatient.is_active == True
    ).all()

    doctors = []
    for r in relations:
        doctors.append({
            "doctor_id": r.doctor.id,
            "full_name": r.doctor.full_name,
            "hospital": r.hospital,
            "authorized_since": r.created_at
        })

    return create_standard_response(
        status="success",
        message="Authorized doctors retrieved",
        data={"doctors": doctors},
        request_id=request_id
    )


@router.delete("/patient/authorized-doctors/{doctor_id}", response_model=StandardResponse, tags=["patient view"])
async def remove_authorized_doctor(
    doctor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    request_id = generate_request_id()

    relation = db.query(DoctorPatient).filter(
        DoctorPatient.patient_id == current_user.id,
        DoctorPatient.doctor_id == doctor_id,
        DoctorPatient.is_active == True
    ).first()

    if not relation:
        raise HTTPException(status_code=404, detail="Authorization not found")

    try:
        db.delete(relation) # Or set is_active=False
        db.commit()

        return create_standard_response(
            status="success",
            message="Doctor authorization removed",
            request_id=request_id
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to remove authorization")


@router.get("/patient/access-requests", response_model=StandardResponse, tags=["patient view"])
async def get_patient_access_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    request_id = generate_request_id()
    
    requests = db.query(AccessRequest).filter(
        AccessRequest.patient_id == current_user.id,
        AccessRequest.status == "pending"
    ).all()

    data = []
    for req in requests:
        data.append({
            "request_id": req.id,
            "doctor_name": req.doctor.full_name,
            "created_at": req.created_at
        })

    return create_standard_response(
        status="success",
        message="Pending access requests retrieved",
        data={"requests": data},
        request_id=request_id
    )


@router.post("/patient/access-requests/{request_id}/approve", response_model=StandardResponse, tags=["patient view"])
async def approve_access_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req_uuid = generate_request_id()

    request_obj = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.patient_id == current_user.id,
        AccessRequest.status == "pending"
    ).first()

    if not request_obj:
        raise HTTPException(status_code=404, detail="Request not found")

    try:
        request_obj.status = "approved"
        
        # Create relation
        relation = DoctorPatient(
            doctor_id=request_obj.doctor_id,
            patient_id=current_user.id
        )
        db.add(relation)
        db.commit()

        return create_standard_response(
            status="success",
            message="Access request approved",
            request_id=req_uuid
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to approve request")


@router.post("/patient/access-requests/{request_id}/reject", response_model=StandardResponse, tags=["patient view"])
async def reject_access_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req_uuid = generate_request_id()

    request_obj = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.patient_id == current_user.id,
        AccessRequest.status == "pending"
    ).first()

    if not request_obj:
        raise HTTPException(status_code=404, detail="Request not found")

    try:
        request_obj.status = "rejected"
        db.commit()

        return create_standard_response(
            status="success",
            message="Access request rejected",
            request_id=req_uuid
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to reject request")


# ==========================
# Doctor View
# ==========================

@router.post("/doctor/request-access", response_model=StandardResponse, tags=["doctor view"])
async def request_patient_access(
    data: AccessRequestInput,
    current_user: User = Depends(require_verified_doctor),
    db: Session = Depends(get_db)
):
    request_id = generate_request_id()

    patient = db.query(User).filter(
        User.id == data.patient_id, User.role == "patient").first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Check if already have access
    existing_relation = db.query(DoctorPatient).filter_by(
        doctor_id=current_user.id,
        patient_id=patient.id,
        is_active=True
    ).first()

    if existing_relation:
        raise HTTPException(
            status_code=400, detail="Already have access to this patient")

    # Check for pending request
    existing_request = db.query(AccessRequest).filter_by(
        doctor_id=current_user.id,
        patient_id=patient.id,
        status="pending"
    ).first()

    if existing_request:
        raise HTTPException(
            status_code=400, detail="Access request already pending")

    try:
        request_obj = AccessRequest(
            doctor_id=current_user.id,
            patient_id=patient.id
        )
        db.add(request_obj)
        db.commit()

        return create_standard_response(
            status="success",
            message="Access request sent",
            request_id=request_id
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to send request")


@router.get("/doctor/access-requests", response_model=StandardResponse, tags=["doctor view"])
async def get_doctor_access_requests(
    current_user: User = Depends(require_verified_doctor),
    db: Session = Depends(get_db)
):
    request_id = generate_request_id()

    requests = db.query(AccessRequest).filter(
        AccessRequest.doctor_id == current_user.id
    ).order_by(desc(AccessRequest.created_at)).all()
    
    data = []
    for req in requests:
        data.append({
            "request_id": req.id,
            "patient_name": req.patient.full_name,
            "status": req.status,
            "created_at": req.created_at
        })
        
    return create_standard_response(
        status="success",
        message="Requests retrieved",
        data={"requests": data},
        request_id=request_id
    )


@router.get("/doctor/patients", response_model=StandardResponse, tags=["doctor view"])
async def get_my_patients(
    current_user: User = Depends(require_verified_doctor),
    db: Session = Depends(get_db)
):
    request_id = generate_request_id()

    relations = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == current_user.id,
        DoctorPatient.is_active == True
    ).all()
    
    patients = []
    for r in relations:
        patients.append({
            "patient_id": r.patient.id,
            "full_name": r.patient.full_name,
            "gender": r.patient.gender,
            "age": (now_th().year - r.patient.date_of_birth.year) if r.patient.date_of_birth else None
        })
        
    return create_standard_response(
        status="success",
        message="Patients retrieved",
        data={"patients": patients},
        request_id=request_id
    )


@router.get("/doctor/patients/{patient_id}/bp-records", response_model=StandardResponse, tags=["doctor view"])
async def get_patient_bp_records(
    patient_id: int,
    current_user: User = Depends(require_verified_doctor),
    db: Session = Depends(get_db)
):
    request_id = generate_request_id()

    # Check authorization
    relation = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == current_user.id,
        DoctorPatient.patient_id == patient_id,
        DoctorPatient.is_active == True
    ).first()
    
    if not relation:
        raise HTTPException(status_code=403, detail="Not authorized to view this patient")
        
    records = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == patient_id
    ).order_by(desc(BloodPressureRecord.measurement_date)).limit(50).all()
    
    data = [BloodPressureRecordResponse.model_validate(r).dict() for r in records]
    
    return create_standard_response(
        status="success",
        message="Patient records retrieved",
        data={"records": data},
        request_id=request_id
    )


@router.delete("/doctor/access-requests/{request_id}", response_model=StandardResponse, tags=["doctor view"])
async def cancel_access_request(
    request_id: int,
    current_user: User = Depends(require_verified_doctor),
    db: Session = Depends(get_db)
):
    req_uuid = generate_request_id()

    req = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.doctor_id == current_user.id,
        AccessRequest.status == "pending"
    ).first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    db.delete(req) # or update status = cancelled
    db.commit()

    return create_standard_response(
        status="success",
        message="Request cancelled",
        request_id=req_uuid
    )


# ==========================
# Search Doctors (for patients to find and authorize)
# ==========================

def _extract_license_year(user: User) -> int | None:
    """Extract license year from verification_logs if available."""
    if not user.verification_logs:
        return None
    try:
        data = json.loads(user.verification_logs)
        if isinstance(data, dict):
            return data.get("license_year")
    except (json.JSONDecodeError, TypeError):
        pass
    return None


@router.get("/patient/search-doctors", response_model=StandardResponse, tags=["patient view"])
async def search_doctors(
    q: str,
    search_by: str = "name",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search for verified doctors in the system.

    - **search_by=name**: Search by full name (exact match first, then partial)
    - **search_by=license**: Search by medical license number (exact match)
    - **search_by=phone**: Search by phone number (exact match)
    """
    request_id = generate_request_id()
    q = q.strip()

    if not q or len(q) < 2:
        raise HTTPException(status_code=400, detail="Search query too short (min 2 characters)")

    if search_by not in ("name", "license", "phone"):
        raise HTTPException(status_code=400, detail="search_by must be name, license, or phone")

    # Base filter: verified active doctors only
    base_filter = [
        User.role == "doctor",
        User.verification_status == "verified",
        User.is_active == True,
    ]

    doctors = []

    if search_by == "license":
        q_hash = hash_value(q)
        if q_hash:
            doctor = db.query(User).filter(
                *base_filter,
                User.medical_license_hash == q_hash,
            ).first()
            if doctor:
                doctors = [doctor]

    elif search_by == "phone":
        # Normalize phone number before hashing
        try:
            import phonenumbers
            parsed = phonenumbers.parse(q, "TH")
            if phonenumbers.is_valid_number(parsed):
                normalized = phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )
                if normalized.startswith("+"):
                    normalized = normalized[1:]
                q_hash = hash_value(normalized)
            else:
                q_hash = hash_value(q)
        except Exception:
            q_hash = hash_value(q)

        if q_hash:
            doctor = db.query(User).filter(
                *base_filter,
                User.phone_hash == q_hash,
            ).first()
            if doctor:
                doctors = [doctor]

    elif search_by == "name":
        # Try exact match via hash first
        q_hash = hash_value(q)
        if q_hash:
            exact = db.query(User).filter(
                *base_filter,
                User.full_name_hash == q_hash,
            ).all()
            if exact:
                doctors = exact

        # Fallback: decrypt and partial match (for small doctor count)
        if not doctors:
            all_verified = db.query(User).filter(*base_filter).limit(500).all()
            q_lower = q.lower()
            for doc in all_verified:
                name = doc.full_name
                if name and q_lower in name.lower():
                    doctors.append(doc)
                    if len(doctors) >= 10:
                        break

    # Build response
    results = []
    for doc in doctors[:10]:
        results.append(DoctorSearchResult(
            doctor_id=doc.id,
            full_name=doc.full_name or "Unknown",
            license_year=_extract_license_year(doc),
        ).model_dump())

    return create_standard_response(
        status="success",
        message=f"Found {len(results)} doctor(s)",
        data={"doctors": results},
        request_id=request_id,
    )
