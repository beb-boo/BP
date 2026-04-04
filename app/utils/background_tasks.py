import json
import logging
from sqlalchemy.orm import Session
from ..models import User
from ..utils.tmc_checker import verify_doctor_with_tmc_v3
from ..utils.timezone import now_tz

logger = logging.getLogger(__name__)


async def verify_doctor_background(
    user_id: int, first_name: str, last_name: str,
    db: Session, medical_license: str = ""
):
    """
    Background task to verify doctor with TMC v3.
    Updates the user's verification_status and logs.
    """
    logger.info(f"Starting background TMC v3 verification for User {user_id}...")
    try:
        from ..database import SessionLocal
        session = SessionLocal()

        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found during background verification.")
            session.close()
            return

        result = await verify_doctor_with_tmc_v3(
            first_name_th=first_name,
            last_name_th=last_name,
        )

        # Store structured JSON log
        log_entry = {
            "checked_at": str(now_tz()),
            "version": "v3",
            "found": result.found,
            "verified": result.verified,
            "name_th": result.full_name_th,
            "name_en": result.full_name_en,
            "license_year": result.license_year_ce,
            "specialties": result.specialties,
            "license_suspended": result.license_suspended,
            "suspension_detail": result.suspension_detail,
            "result_count": result.result_count,
            "message": result.message,
        }
        user.verification_logs = json.dumps(log_entry, ensure_ascii=False)

        if result.verified:
            user.verification_status = "verified"
            logger.info(f"User {user_id} VERIFIED by TMC v3.")
        elif result.license_suspended:
            user.verification_status = "rejected"
            logger.warning(
                f"User {user_id} REJECTED — license suspended: {result.suspension_detail}"
            )
        else:
            # Keep pending for admin manual review
            user.verification_status = "pending"
            logger.warning(f"User {user_id} NOT verified by TMC v3. Status kept as Pending.")

        session.commit()
        session.close()

    except Exception as e:
        logger.error(f"Background verification failed: {e}")
