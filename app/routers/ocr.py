import logging
import uuid
import tempfile
import os

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..schemas import StandardResponse, OCRResult
from ..utils.ocr_helper import read_blood_pressure_with_gemini

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


