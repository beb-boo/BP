
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
                db.commit()
                return True
            if user:
                user.telegram_id = telegram_id
                # Linking via valid token implies verification
                user.is_phone_verified = True 
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
            # SQLite/SQLAlchemy: It's easier to fetch the Last 30 IDs then Average them.
            
            subquery = db.query(BloodPressureRecord.id)\
                .filter(BloodPressureRecord.user_id == user_id)\
                .order_by(BloodPressureRecord.measurement_date.desc())\
                .limit(limit_count)\
                .subquery()
                
            avg = db.query(
                func.avg(BloodPressureRecord.systolic).label('avg_sys'),
                func.avg(BloodPressureRecord.diastolic).label('avg_dia'),
                func.avg(BloodPressureRecord.pulse).label('avg_pulse')
            ).filter(
                BloodPressureRecord.id.in_(subquery)
            ).first()
            
            return {
                "recent": recent,
                "average": avg
            }

