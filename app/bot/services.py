
from sqlalchemy.orm import Session
from app.models import User, BloodPressureRecord, UserSession, DoctorPatient, Payment
from app.utils.security import (
    verify_password,
    hash_password,
    SECRET_KEY,
    ALGORITHM,
    check_premium,
    is_account_locked,
    lock_account,
    MAX_LOGIN_ATTEMPTS,
)
from app.utils.encryption import encrypt_value, decrypt_value, hash_value
from app.utils.tmc_checker import verify_doctor_with_tmc_v3
from app.utils.timezone import now_tz, TIMEZONE_CHOICES, is_valid_timezone, format_datetime
from app.utils.subscription import get_subscription_info, normalize_subscription_state
from app.database import SessionLocal
import logging
import jwt
import re

logger = logging.getLogger(__name__)


class PasswordVerificationResult:
    def __init__(self, user: User | None, status: str):
        self.user = user
        self.status = status

class BotService:
    @staticmethod
    def get_db():
        """Helper to get a database session."""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @staticmethod
    def get_user_by_telegram_id(telegram_id: int):
        """Find a user by their linked Telegram ID."""
        t_hash = hash_value(str(telegram_id))
        try:
            with SessionLocal() as db:
                return db.query(User).filter(User.telegram_id_hash == t_hash).first()
        except Exception as e:
            logger.error(f"DB error in get_user_by_telegram_id: {e}")
            return None

    @staticmethod
    def get_user_by_phone(phone_number: str):
        """Find a user by phone number via hash lookup."""
        phone_h = hash_value(phone_number)
        if not phone_h:
            return None
        try:
            with SessionLocal() as db:
                return db.query(User).filter(User.phone_number_hash == phone_h).first()
        except Exception as e:
            logger.error(f"DB error in get_user_by_phone: {e}")
            return None

    @staticmethod
    def verify_user_password(phone_number: str, password: str) -> PasswordVerificationResult:
        """Verify password for a given phone number using the same account rules as web login."""
        phone_h = hash_value(phone_number)
        if not phone_h:
            return PasswordVerificationResult(None, "not_found")
        with SessionLocal() as db:
            user = db.query(User).filter(User.phone_number_hash == phone_h).first()
            if not user:
                return PasswordVerificationResult(None, "not_found")

            if is_account_locked(user):
                return PasswordVerificationResult(None, "locked")

            if not user.is_active:
                return PasswordVerificationResult(None, "inactive")

            if verify_password(password, user.password_hash):
                user.failed_login_attempts = 0
                user.account_locked_until = None
                user.last_login = now_tz()
                db.commit()
                db.refresh(user)
                return PasswordVerificationResult(user, "success")

            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                lock_account(user, db)
                return PasswordVerificationResult(None, "locked")

            db.commit()
            return PasswordVerificationResult(None, "invalid_password")

    @staticmethod
    def link_telegram_account(user_id: int, telegram_id: int):
        """Link a Telegram ID to an existing user."""
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.telegram_id = telegram_id
                # Linking via valid token implies verification
                user.is_phone_verified = True
                db.commit()
                return True
            return False

    @staticmethod
    def update_user_language(user_id: int, language: str):
        """Update user language preference."""
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.language = language
                db.commit()
                return True
            return False

    @staticmethod
    def update_user_timezone(user_id: int, timezone: str):
        """Update user timezone preference."""
        if not is_valid_timezone(timezone):
            return False
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.timezone = timezone
                db.commit()
                return True
            return False

    @staticmethod
    def get_timezone_choices():
        """Get available timezone choices for UI."""
        return TIMEZONE_CHOICES

    @staticmethod
    def process_connection_token(token: str, telegram_id: int):
        """Process a JWT token from Deep Link to connect account."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("purpose") != "telegram_connect":
                return None
                
            user_id = payload.get("user_id")
            if not user_id:
                return None
                
            BotService.link_telegram_account(user_id, telegram_id)
            
            with SessionLocal() as db:
                return db.query(User).filter(User.id == user_id).first()
                
        except (jwt.ExpiredSignatureError, jwt.PyJWTError) as e:
            logger.error(f"Token error: {e}")
            return None

    @staticmethod
    async def register_new_user(user_data: dict, telegram_id: int):
        """
        Register a new user from Telegram data.
        user_data expected keys: phone_number, full_name, role, date_of_birth (datetime), password, gender
        """
        with SessionLocal() as db:
            try:
                # 0. Check duplicate medical license
                if user_data.get('medical_license'):
                    from app.utils.encryption import hash_value
                    lic_hash = hash_value(user_data['medical_license'])
                    existing_lic = db.query(User).filter(User.medical_license_hash == lic_hash).first()
                    if existing_lic:
                        logger.warning(f"Duplicate medical license during bot registration")
                        return None

                # 1. Check if Doctor -> Verify with TMC
                verification_status = "verified" # Default for patient
                verification_logs = None

                if user_data['role'] == 'doctor':
                    import json as _json
                    parts = user_data['full_name'].split()
                    if len(parts) >= 2:
                        first_name = parts[0]
                        last_name = " ".join(parts[1:])
                        result = await verify_doctor_with_tmc_v3(
                            first_name_th=first_name,
                            last_name_th=last_name,
                        )
                        if result.verified:
                            verification_status = "verified"
                        elif result.license_suspended:
                            verification_status = "rejected"
                        else:
                            verification_status = "pending"
                        verification_logs = _json.dumps({
                            "source": "bot",
                            "checked_at": str(now_tz()),
                            "verified": result.verified,
                            "name_th": result.full_name_th,
                            "name_en": result.full_name_en,
                            "license_suspended": result.license_suspended,
                            "message": result.message,
                        }, ensure_ascii=False)
                    else:
                        verification_status = "pending"
                        verification_logs = "Bot Auto-Check: Name format invalid"

                new_user = User(
                    phone_number=user_data['phone_number'],
                    full_name=user_data['full_name'],
                    password_hash=hash_password(user_data['password']),
                    role=user_data['role'],
                    date_of_birth=user_data.get('date_of_birth'),
                    gender=user_data.get('gender'),
                    telegram_id=telegram_id,
                    is_phone_verified=True, # Trust Telegram
                    is_active=True,
                    verification_status=verification_status,
                    verification_logs=verification_logs,
                    language=user_data.get('register_lang', 'th'),
                    timezone=user_data.get('timezone', 'Asia/Bangkok'),
                    medical_license=user_data.get('medical_license'),
                    created_at=now_tz(),
                    updated_at=now_tz()
                )
                
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                return new_user
            except Exception as e:
                logger.error(f"Bot Registration Error: {e}")
                db.rollback()
                return None

    @staticmethod
    def create_bp_record(user_id: int, systolic: int, diastolic: int, pulse: int, notes: str = None, measurement_date=None, measurement_time=None):
        """Create a new blood pressure record."""
        from app.models import BloodPressureRecord # Local import to avoid circular dependency
        from datetime import datetime

        final_date = now_tz()
        final_time = now_tz().strftime("%H:%M")
        
        if measurement_date:
            if isinstance(measurement_date, str):
                try:
                    final_date = datetime.strptime(measurement_date, "%Y-%m-%d")
                except ValueError:
                    pass # Keep default
            else:
                final_date = measurement_date

        if measurement_time:
            final_time = measurement_time

        with SessionLocal() as db:
            from sqlalchemy import func
            # Check for duplicate: Compare only the DATE part of measurement_date
            existing = db.query(BloodPressureRecord).filter(
                BloodPressureRecord.user_id == user_id,
                func.date(BloodPressureRecord.measurement_date) == final_date.date(),
                BloodPressureRecord.measurement_time == final_time,
                BloodPressureRecord.systolic == systolic,
                BloodPressureRecord.diastolic == diastolic,
                BloodPressureRecord.pulse == pulse
            ).first()
            
            if existing:
                return existing, False

            record = BloodPressureRecord(
                user_id=user_id,
                systolic=systolic,
                diastolic=diastolic,
                pulse=pulse,
                measurement_date=final_date,
                measurement_time=final_time,
                notes=notes,
                created_at=now_tz()
            )
            db.add(record)
            db.commit()
            return record, True

    @staticmethod
    def get_user_stats(user_id: int, days: int = 30):
        """Get recent stats for a user with clinical metrics."""
        from app.models import BloodPressureRecord
        from app.routers.bp_records import classify_bp, compute_trend
        from sqlalchemy import func
        from datetime import timedelta
        import statistics as stats_module

        with SessionLocal() as db:
            # Check premium status
            user = db.query(User).filter(User.id == user_id).first()
            is_premium = check_premium(user) if user else False

            # Get records — same logic as API endpoint
            query = db.query(BloodPressureRecord)\
                .filter(BloodPressureRecord.user_id == user_id)\
                .order_by(BloodPressureRecord.measurement_date.desc())

            if is_premium:
                recent = query.limit(days).all()
            else:
                recent = query.limit(30).all()

            if not recent:
                return {
                    "recent": recent,
                    "average": None,
                    "classification": None,
                    "is_premium": is_premium,
                    "advanced": None
                }

            # Calculate averages
            sys_vals = [r.systolic for r in recent]
            dia_vals = [r.diastolic for r in recent]
            pulse_vals = [r.pulse for r in recent]
            n = len(recent)

            avg_sys = round(sum(sys_vals) / n, 1)
            avg_dia = round(sum(dia_vals) / n, 1)
            avg_pulse = round(sum(pulse_vals) / n, 1)

            # Classification (free + premium)
            classification = classify_bp(avg_sys, avg_dia)

            # Advanced stats (premium only)
            advanced = None
            if is_premium:
                has_enough = n >= 2
                sd_sys = round(stats_module.stdev(sys_vals), 1) if has_enough else 0
                sd_dia = round(stats_module.stdev(dia_vals), 1) if has_enough else 0
                pp_avg = round(avg_sys - avg_dia, 1)
                map_avg = round((avg_sys + 2 * avg_dia) / 3, 1)
                trend = compute_trend(recent)
                advanced = {
                    "sd_sys": sd_sys,
                    "sd_dia": sd_dia,
                    "pulse_pressure": pp_avg,
                    "map": map_avg,
                    "trend": trend
                }

            class AvgResult:
                def __init__(self, s, d, p):
                    self.avg_sys = s
                    self.avg_dia = d
                    self.avg_pulse = p

            return {
                "recent": recent,
                "average": AvgResult(avg_sys, avg_dia, avg_pulse),
                "classification": classification,
                "is_premium": is_premium,
                "advanced": advanced
            }


    @staticmethod
    def get_subscription_status(user_id: int):
        """Get user subscription status (normalized via central utility)."""
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None

            # Self-heal: persist downgrade if expired premium
            normalize_subscription_state(user, db=db)

            sub_info = get_subscription_info(user)

            return {
                "tier": sub_info["subscription_tier"],
                "is_active": sub_info["is_premium_active"],
                "expires_at": user.subscription_expires_at.strftime("%Y-%m-%d") if user.subscription_expires_at else "-",
                "days_remaining": sub_info["days_remaining"],
                "language": user.language or "th",
                "timezone": user.timezone or "Asia/Bangkok"
            }

    @staticmethod
    def verify_slip_payment(user_id: int, image_bytes: bytes, plan_type: str):
        """Verify slip and upgrade user (delegates to shared payment service)."""
        from app.services.payment_service import verify_and_upgrade, PaymentError
        from app.config.pricing import SUBSCRIPTION_PLANS

        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            lang = user.language or "th"

            try:
                result = verify_and_upgrade(db, user, image_bytes, plan_type, lang)
                plan = SUBSCRIPTION_PLANS.get(plan_type, {})
                plan_name = plan.get("name_en") if lang == "en" else plan.get("name", plan_type)
                return {
                    "success": True,
                    "amount": result["amount"],
                    "expires_at": result["subscription_expires_at"],
                    "plan_name": plan_name,
                }
            except PaymentError as e:
                return {"success": False, "error": e.message}

    # ================================================================
    # Profile Management
    # ================================================================

    @staticmethod
    def get_user_profile(user_id: int) -> dict | None:
        """Get decrypted user profile data for display."""
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None

            # Self-heal: persist downgrade if expired premium
            normalize_subscription_state(user, db=db)

            gender_map = {"male": "Male", "female": "Female", "other": "Other"}
            role_map = {"patient": "Patient", "doctor": "Doctor"}

            dob = user.date_of_birth
            dob_str = dob.strftime("%d/%m/%Y") if dob else "-"

            sub_info = get_subscription_info(user)

            return {
                "name": user.full_name or "-",
                "phone": user.phone_number or "-",
                "email": user.email or "-",
                "gender": gender_map.get(user.gender, "-"),
                "dob": dob_str,
                "role": role_map.get(user.role, user.role or "-"),
                "timezone": user.timezone or "Asia/Bangkok",
                "subscription": sub_info["subscription_tier"],
                "is_premium_active": sub_info["is_premium_active"],
                "subscription_expires_at": user.subscription_expires_at.strftime("%Y-%m-%d") if user.subscription_expires_at else "-",
                "days_remaining": sub_info["days_remaining"],
                "language": user.language or "th",
            }

    @staticmethod
    def update_user_name(user_id: int, new_name: str) -> bool:
        """Update user full name."""
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.full_name = new_name
                user.updated_at = now_tz()
                db.commit()
                return True
            return False

    @staticmethod
    def update_user_email(user_id: int, new_email: str) -> bool:
        """Update user email."""
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', new_email):
            return False
        with SessionLocal() as db:
            # Check if email already taken
            email_h = hash_value(new_email)
            existing = db.query(User).filter(User.email_hash == email_h, User.id != user_id).first()
            if existing:
                return False
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.email = new_email
                user.updated_at = now_tz()
                db.commit()
                return True
            return False

    # ================================================================
    # Delete BP Records
    # ================================================================

    @staticmethod
    def get_recent_records(user_id: int, limit: int = 10) -> list:
        """Get recent BP records for deletion selection."""
        with SessionLocal() as db:
            records = db.query(BloodPressureRecord).filter(
                BloodPressureRecord.user_id == user_id
            ).order_by(
                BloodPressureRecord.measurement_date.desc(),
                BloodPressureRecord.created_at.desc()
            ).limit(limit).all()

            return [{
                "id": r.id,
                "sys": r.systolic,
                "dia": r.diastolic,
                "pulse": r.pulse,
                "date": r.measurement_date.strftime("%d/%m/%Y") if r.measurement_date else "-",
                "time": r.measurement_time or "",
            } for r in records]

    @staticmethod
    def delete_bp_record(user_id: int, record_id: int) -> dict | None:
        """Delete a BP record. Returns record info or None if not found."""
        with SessionLocal() as db:
            record = db.query(BloodPressureRecord).filter(
                BloodPressureRecord.id == record_id,
                BloodPressureRecord.user_id == user_id
            ).first()
            if not record:
                return None
            info = {
                "sys": record.systolic,
                "dia": record.diastolic,
                "pulse": record.pulse,
                "date": record.measurement_date.strftime("%d/%m/%Y") if record.measurement_date else "-",
                "time": record.measurement_time or "",
            }
            db.delete(record)
            db.commit()
            return info

    @staticmethod
    def update_bp_record(user_id: int, record_id: int, systolic: int, diastolic: int, pulse: int) -> bool:
        """Update an existing BP record's values."""
        with SessionLocal() as db:
            record = db.query(BloodPressureRecord).filter(
                BloodPressureRecord.id == record_id,
                BloodPressureRecord.user_id == user_id
            ).first()
            if not record:
                return False
            record.systolic = systolic
            record.diastolic = diastolic
            record.pulse = pulse
            record.notes = (record.notes or "") + " (Edited)"
            db.commit()
            return True

    # ================================================================
    # Password Management
    # ================================================================

    @staticmethod
    def change_password(user_id: int, current_password: str, new_password: str) -> bool:
        """Change password after verifying current one. Invalidates sessions."""
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            if not verify_password(current_password, user.password_hash):
                return False
            user.password_hash = hash_password(new_password)
            user.updated_at = now_tz()
            # Invalidate all sessions
            db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            ).update({"is_active": False})
            db.commit()
            return True

    @staticmethod
    def reset_password_direct(user_id: int, new_password: str) -> bool:
        """Reset password without current password (after OTP verification). Invalidates sessions."""
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            user.password_hash = hash_password(new_password)
            user.failed_login_attempts = 0
            user.account_locked_until = None
            user.updated_at = now_tz()
            db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            ).update({"is_active": False})
            db.commit()
            return True

    @staticmethod
    def get_user_contact_for_otp(user_id: int) -> dict | None:
        """Get user's email or phone for OTP sending."""
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            return {
                "email": user.email,
                "phone": user.phone_number,
                "user_id": user.id,
            }

    # ================================================================
    # Broadcast
    # ================================================================

    @staticmethod
    def get_all_broadcast_chat_ids():
        """Get all active users' decrypted telegram_ids for broadcast."""
        with SessionLocal() as db:
            users = db.query(User).filter(
                User.telegram_id_hash.isnot(None),
                User.is_active == True
            ).all()

            result = []
            for user in users:
                tid = user.telegram_id
                if tid:
                    result.append({
                        "user_id": user.id,
                        "telegram_id": tid,
                        "language": user.language or "th"
                    })
            return result

    # ================================================================
    # Account Deactivation
    # ================================================================

    @staticmethod
    def deactivate_account(user_id: int) -> bool:
        """Deactivate account: wipe PII, delete records, anonymize user row."""
        with SessionLocal() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return False

                # 1. Delete BP records
                db.query(BloodPressureRecord).filter(
                    BloodPressureRecord.user_id == user_id
                ).delete()

                # 2. Delete sessions
                db.query(UserSession).filter(
                    UserSession.user_id == user_id
                ).delete()

                # 3. Delete doctor-patient relationships
                db.query(DoctorPatient).filter(
                    (DoctorPatient.doctor_id == user_id) |
                    (DoctorPatient.patient_id == user_id)
                ).delete(synchronize_session='fetch')

                # 4. Wipe PII fields
                user.email_encrypted = None
                user.email_hash = None
                user.phone_number_encrypted = None
                user.phone_number_hash = None
                user.full_name_encrypted = None
                user.full_name_hash = None
                user.citizen_id_encrypted = None
                user.citizen_id_hash = None
                user.medical_license_encrypted = None
                user.medical_license_hash = None
                user.date_of_birth_encrypted = None
                user.telegram_id_encrypted = None
                user.telegram_id_hash = None
                user.password_hash = "DEACTIVATED"
                user.gender = None

                # 5. Set inactive
                user.is_active = False
                user.updated_at = now_tz()

                db.commit()
                return True
            except Exception as e:
                logger.error(f"Deactivation error for user {user_id}: {e}")
                db.rollback()
                return False
