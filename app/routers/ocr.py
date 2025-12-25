
from fastapi import APIRouter, HTTPException, Depends, Request, status, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, BloodPressureRecord
from ..schemas import StandardResponse, OCRResult, BloodPressureRecordResponse
from ..utils.security import verify_api_key, get_current_user, now_th
from ..utils.ocr_helper import read_blood_pressure_with_gemini
import logging
import uuid
import tempfile
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/api/v1", tags=["blood pressure"])
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


@router.post("/ocr/process-image", response_model=StandardResponse)
@limiter.limit("10/minute")
async def process_bp_image(
    request: Request,
    file: UploadFile = File(...),
):
    """Extract blood pressure values from uploaded image (OCR only)"""
    request_id = generate_request_id()

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Check file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    file_size = 0
    content = bytearray()

    try:
        while True:
            chunk = await file.read(1024)
            if not chunk:
                break
            file_size += len(chunk)
            if file_size > max_size:
                raise HTTPException(
                    status_code=413, detail="File too large. Maximum size is 10MB")
            content.extend(chunk)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error reading file")

    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Process with Gemini
        ocr_result = read_blood_pressure_with_gemini(temp_file_path)
        
        # Cleanup
        os.unlink(temp_file_path)

        if ocr_result.error:
            logger.warning(
                f"OCR processing failed: {ocr_result.error} - Request ID: {request_id}")
            raise HTTPException(
                status_code=400, detail=f"OCR Error: {ocr_result.error}")

        if not all([ocr_result.systolic, ocr_result.diastolic, ocr_result.pulse]):
            raise HTTPException(
                status_code=422,
                detail="Could not extract all required blood pressure values from image"
            )

        logger.info(f"OCR processing successful - Request ID: {request_id}")

        return create_standard_response(
            status="success",
            message="Image processed successfully",
            data={"ocr_result": ocr_result.dict()},
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Image processing error: {str(e)} - Request ID: {request_id}")
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        raise HTTPException(
            status_code=500, detail="Internal server error processing image")


@router.post("/bp-records/save-from-ocr", response_model=StandardResponse)
async def save_bp_from_ocr(
    ocr_data: OCRResult,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Save record from confirmed OCR data"""
    request_id = generate_request_id()

    if not all([ocr_data.systolic, ocr_data.diastolic, ocr_data.pulse]):
        raise HTTPException(
            status_code=400, detail="Missing required blood pressure values")

    try:
        # Create record
        # Note: In the new structure, we need to ensure models are imported correctly
        # We handle measurement_time logic here or in frontend? 
        # Original code likely had this logic. Let's assume passed in OCRResult
        
        # Prepare data
        measurement_date = now_th()
        # If OCR returned time, we might want to use it combined with date? 
        # Simple approach: use current time if not provided or just store as string
        
        new_record = BloodPressureRecord(
            user_id=current_user.id,
            systolic=ocr_data.systolic,
            diastolic=ocr_data.diastolic,
            pulse=ocr_data.pulse,
            measurement_date=measurement_date,
            measurement_time=ocr_data.time or measurement_date.strftime("%H:%M"),
            ocr_confidence=ocr_data.confidence,
            created_at=now_th()
        )

        db.add(new_record)
        db.commit()
        db.refresh(new_record)

        logger.info(
            f"BP record saved from OCR: {new_record.id} - Request ID: {request_id}")

        return create_standard_response(
            status="success",
            message="Record saved successfully",
            data={"record": BloodPressureRecordResponse.model_validate(
                new_record).dict()},
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error saving OCR record: {e} - Request ID: {request_id}")
        raise HTTPException(status_code=500, detail="Failed to save record")
