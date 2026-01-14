
from sqlalchemy.orm import Session
from app.models import User
from app.utils.security import verify_password, hash_password, now_th, SECRET_KEY, ALGORITHM
from app.utils.encryption import encrypt_value, hash_value
from app.utils.tmc_checker import verify_doctor_with_tmc
from app.database import SessionLocal
import logging
import jwt

logger = logging.getLogger(__name__)

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
        with SessionLocal() as db:
            return db.query(User).filter(User.telegram_id_hash == t_hash).first()

    @staticmethod
    def get_user_by_phone(phone_number: str):
        """Find a user by phone number."""
        with SessionLocal() as db:
            return db.query(User).filter(User.phone_number == phone_number).first()

    @staticmethod
    def verify_user_password(phone_number: str, password: str) -> User | None:
        """Verify password for a given phone number."""
        with SessionLocal() as db:
            user = db.query(User).filter(User.phone_number == phone_number).first()
            if user and verify_password(password, user.password_hash):
                return user
            return None

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
                # 1. Check if Doctor -> Verify with TMC
                verification_status = "verified" # Default for patient
                verification_logs = None
                
                if user_data['role'] == 'doctor':
                    # Split name for checking (Simple split, ideally ask user for First/Last separately)
                    parts = user_data['full_name'].split()
                    if len(parts) >= 2:
                        first_name = parts[0]
                        last_name = " ".join(parts[1:])
                        # This should be awaited if async, but we are inside a blocking DB call?
                        # Wait, handlers are async. This service method should probably be async too 
                        # or we await the TMC check outside DB transaction.
                        result = await verify_doctor_with_tmc(first_name, last_name)
                        if result['verified']:
                            verification_status = "verified"
                        else:
                            verification_status = "pending"
                        verification_logs = f"Bot Auto-Check: {result['message']}"
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
                    created_at=now_th(),
                    updated_at=now_th()
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
        
        final_date = now_th()
        final_time = now_th().strftime("%H:%M")
        
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
            # Check for duplicate
            existing = db.query(BloodPressureRecord).filter(
                BloodPressureRecord.user_id == user_id,
                BloodPressureRecord.measurement_date == final_date,
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
                created_at=now_th()
            )
            db.add(record)
            db.commit()
            return record, True

    @staticmethod
    def get_user_stats(user_id: int, days: int = 30):
        """Get recent stats for a user (Last N days)."""
        from app.models import BloodPressureRecord
        from sqlalchemy import func
        from datetime import timedelta
        
        with SessionLocal() as db:
            # Get last 5 records (Any date)
            recent = db.query(BloodPressureRecord)\
                .filter(BloodPressureRecord.user_id == user_id)\
                .order_by(BloodPressureRecord.measurement_date.desc(), BloodPressureRecord.created_at.desc())\
                .limit(5)\
                .all()
                
            # Get average of last N RECORDS (Count-based, aligning with Web Logic)
            # Use 'days' param as 'limit_count'
            limit_count = 30
            
            # Complex query: We need to average the "Latest 30". 
            # Fix SAWarning: Fetch IDs first (List) then filter. Safer and cleaner for small limits.
            
            recent_ids_result = db.query(BloodPressureRecord.id)\
                .filter(BloodPressureRecord.user_id == user_id)\
                .order_by(BloodPressureRecord.measurement_date.desc())\
                .limit(limit_count)\
                .all()
            
            recent_ids = [r[0] for r in recent_ids_result]
            
            if not recent_ids:
                 return {
                    "recent": recent, # from earlier query
                    "average": None
                 }
                
            avg = db.query(
                func.avg(BloodPressureRecord.systolic).label('avg_sys'),
                func.avg(BloodPressureRecord.diastolic).label('avg_dia'),
                func.avg(BloodPressureRecord.pulse).label('avg_pulse')
            ).filter(
                BloodPressureRecord.id.in_(recent_ids)
            ).first()
            
            return {
                "recent": recent,
                "average": avg
            }


    @staticmethod
    def get_subscription_status(user_id: int):
        """Get user subscription status."""
        from datetime import datetime
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            is_active = False
            days_remaining = 0
            
            if user.subscription_tier == "premium" and user.subscription_expires_at:
                if user.subscription_expires_at > now_th():
                    is_active = True
                    days_remaining = (user.subscription_expires_at - now_th()).days
            
            return {
                "tier": user.subscription_tier,
                "is_active": is_active,
                "expires_at": user.subscription_expires_at.strftime("%Y-%m-%d") if user.subscription_expires_at else "-",
                "days_remaining": days_remaining,
                "language": user.language or "th"
            }

    @staticmethod
    def verify_slip_payment(user_id: int, image_bytes: bytes, plan_type: str):
        """Verify slip and upgrade user."""
        from app.services.slipok import slipok_service
        from app.config.pricing import get_plan, is_valid_amount
        from app.models import Payment
        import uuid
        import json
        from datetime import timedelta

        # 1. Get User Config
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            lang = user.language or "th"
            
            # 2. Validate Plan
            plan = get_plan(plan_type)
            if not plan:
                return {"success": False, "error": "Invalid Plan"}

            # 3. Check Service
            if not slipok_service.api_key:
                return {"success": False, "error": "Payment Service Unavailable"}

            # 4. Verify with SlipOK
            expected_amount = plan["price"]
            result = slipok_service.verify_slip_image(image_bytes, expected_amount, language=lang)
            
            if not result.success:
                 # Log Failure
                payment = Payment(
                    user_id=user_id,
                    trans_ref=f"FAILED-{uuid.uuid4()}",
                    trans_ref_hash=hash_value(f"FAILED-{uuid.uuid4()}-{now_th()}"),
                    amount=0,
                    plan_type=plan_type,
                    plan_amount=expected_amount,
                    status="failed",
                    error_code=result.error_code,
                    error_message=result.error_message,
                    verification_response=json.dumps(result.raw_response) if result.raw_response else None
                )
                db.add(payment)
                db.commit()
                return {"success": False, "error": result.error_message}

            # 5. Check Duplicate
            trans_ref_hash = hash_value(result.trans_ref)
            existing = db.query(Payment).filter(
                Payment.trans_ref_hash == trans_ref_hash,
                Payment.status == "verified"
            ).first()

            if existing:
                msg = "Slip already used" if lang == "en" else "สลิปนี้เคยใช้ชำระเงินแล้ว"
                return {"success": False, "error": msg}

            # 6. Verify Amount
            if not is_valid_amount(expected_amount, result.amount):
                msg = f"Amount mismatch ({result.amount} vs {expected_amount})" if lang == "en" \
                      else f"ยอดเงิน ({result.amount} บาท) ไม่ตรงกับราคาแพลน ({expected_amount} บาท)"
                return {"success": False, "error": msg}

            # 7. Success - Save Payment
            payment = Payment(
                user_id=user_id,
                trans_ref=result.trans_ref,
                trans_ref_hash=trans_ref_hash,
                amount=result.amount,
                sending_bank=result.sending_bank,
                sender_name_encrypted=encrypt_value(result.sender_name) if result.sender_name else None,
                receiver_name=result.receiver_name,
                trans_date=result.trans_date,
                trans_time=result.trans_time,
                plan_type=plan_type,
                plan_amount=expected_amount,
                status="verified",
                verification_response=json.dumps(result.raw_response),
                verified_at=now_th()
            )
            db.add(payment)

            # 8. Upgrade User
            duration_days = plan["duration_days"]
            if (user.subscription_tier == "premium" and
                user.subscription_expires_at and
                user.subscription_expires_at > now_th()):
                new_expiry = user.subscription_expires_at + timedelta(days=duration_days)
            else:
                new_expiry = now_th() + timedelta(days=duration_days)

            user.subscription_tier = "premium"
            user.subscription_expires_at = new_expiry
            user.updated_at = now_th()

            db.commit()
            
            return {
                "success": True,
                "amount": result.amount,
                "expires_at": new_expiry.strftime("%Y-%m-%d"),
                "plan_name": plan['name']
            }
