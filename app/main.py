"""
Enhanced Blood Pressure API with OTP System
Improved authentication, authorization, and user management
"""

from PIL.ExifTags import TAGS
import PIL.Image
import google.generativeai as genai
import psycopg2
from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile, Body, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from pydantic import BaseModel, EmailStr, Field, model_validator
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Literal, Union, Dict, Any
import bcrypt
import jwt
import os
import io
import json
import tempfile
import uuid
import logging
import random
import string
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import phonenumbers
from phonenumbers import NumberParseException
import hashlib
import secrets
from dotenv import load_dotenv
from pytz import timezone
from otp_service import OTPService

otp_service = OTPService()


# Google Generative AI imports

THAI_TZ = timezone("Asia/Bangkok")


def now_th():
    return datetime.now(THAI_TZ)


# =====================================================
# Configuration
# =====================================================
# สั่งให้โหลดค่าจากไฟล์ .env เข้าสู่ Environment Variables ของโปรแกรม
load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
OTP_EXPIRE_MINUTES = 5
API_KEY_HEADER = "X-API-Key"

# API Keys for client apps
VALID_API_KEYS = os.getenv(
    "API_KEYS", "bp-mobile-app-key,bp-web-app-key").split(",")

# Email Configuration
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@bpmonitor.com")

# SMS Configuration (example for Thai SMS services)
SMS_API_URL = os.getenv("SMS_API_URL", "")
SMS_API_KEY = os.getenv("SMS_API_KEY", "")
SMS_FROM = os.getenv("SMS_FROM", "BPMonitor")

# Google AI Configuration
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY")
if GOOGLE_AI_API_KEY:
    genai.configure(api_key=GOOGLE_AI_API_KEY)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./blood_pressure.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================================================
# Database Models
# =====================================================


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True,
                   nullable=True)  # Made optional
    phone_number = Column(String, unique=True, index=True,
                          nullable=True)  # Made optional
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    citizen_id = Column(String, unique=True, nullable=True)
    medical_license = Column(String, unique=True, nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String, nullable=True)
    blood_type = Column(String, nullable=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    is_phone_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_th())
    updated_at = Column(DateTime, default=now_th(),
                        onupdate=now_th())

    # Relationships
    bp_records = relationship("BloodPressureRecord", back_populates="user")
    doctor_patients = relationship(
        "DoctorPatient", foreign_keys="DoctorPatient.doctor_id", back_populates="doctor")
    patient_doctors = relationship(
        "DoctorPatient", foreign_keys="DoctorPatient.patient_id", back_populates="patient")
    # otp_codes = relationship("OTPCode", back_populates="user")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String, unique=True, nullable=False)
    device_info = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime, default=now_th())
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=now_th())

    user = relationship("User")


class BloodPressureRecord(Base):
    __tablename__ = "blood_pressure_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    systolic = Column(Integer, nullable=False)
    diastolic = Column(Integer, nullable=False)
    pulse = Column(Integer, nullable=False)
    measurement_date = Column(DateTime, nullable=False)
    measurement_time = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    image_path = Column(String, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=now_th())

    user = relationship("User", back_populates="bp_records")


class DoctorPatient(Base):
    __tablename__ = "doctor_patients"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    hospital = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_th())

    doctor = relationship("User", foreign_keys=[
                          doctor_id], back_populates="doctor_patients")
    patient = relationship("User", foreign_keys=[
                           patient_id], back_populates="patient_doctors")


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=now_th())

    doctor = relationship("User", foreign_keys=[doctor_id])
    patient = relationship("User", foreign_keys=[patient_id])

# =====================================================
# Pydantic Models
# =====================================================


def validate_phone_number(phone: str) -> str:
    """Validate phone number format using phonenumbers library"""
    try:
        # Parse phone number (assuming international format or Thai number)
        parsed = phonenumbers.parse(phone, "TH")  # Default to Thailand
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Invalid phone number")
        # Return in international format
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except NumberParseException:
        raise ValueError("Invalid phone number format")


def validate_contact_required(email: Optional[str], phone: Optional[str]):
    if not email and not phone:
        raise ValueError("Either email or phone_number must be provided")


def validate_medical_license(role: str, license: Optional[str]):
    if role == "doctor" and not license:
        raise ValueError("Doctor must provide a medical license")
    if role == "patient" and license:
        raise ValueError("Patient must not provide a medical license")


class StandardResponse(BaseModel):
    status: Literal["success", "error"]
    message: str
    data: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    errors: Optional[List[Dict[str, Any]]] = None
    request_id: Optional[str] = None


class PaginationMeta(BaseModel):
    current_page: int
    per_page: int
    total: int
    total_pages: int


class UserRegister(BaseModel):
    # Either email OR phone_number is required (at least one)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    password: str = Field(..., min_length=8,
                          description="Password must be at least 8 characters")
    full_name: str = Field(..., min_length=2, max_length=100)
    role: Literal["patient", "doctor"]

    # Patient specific fields
    citizen_id: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[Literal["male", "female", "other"]] = None
    blood_type: Optional[Literal["A", "B", "AB", "O", "A+",
                                 "B+", "AB+", "O+", "A-", "B-", "AB-", "O-"]] = None
    height: Optional[float] = Field(None, gt=0, le=300)
    weight: Optional[float] = Field(None, gt=0, le=500)

    # Doctor specific fields
    medical_license: Optional[str] = None

    # validators

    @model_validator(mode="after")
    def validate_all(self) -> 'UserRegister':
        self.phone_number = validate_phone_number(
            self.phone_number) if self.phone_number else None
        validate_contact_required(self.email, self.phone_number)
        validate_medical_license(self.role, self.medical_license)
        return self


class OTPRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    purpose: Literal["registration", "login", "password_reset",
                     "phone_verification", "email_verification"]

    # validators

    @model_validator(mode="after")
    def validate_all(self) -> 'OTPRequest':
        self.phone_number = validate_phone_number(
            self.phone_number) if self.phone_number else None
        validate_contact_required(self.email, self.phone_number)
        return self


class OTPVerification(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    otp_code: str = Field(..., min_length=4, max_length=4)
    purpose: Literal["registration", "login", "password_reset",
                     "phone_verification", "email_verification"]

    # validators

    @model_validator(mode="after")
    def validate_all(self) -> 'OTPVerification':
        self.phone_number = validate_phone_number(
            self.phone_number) if self.phone_number else None
        validate_contact_required(self.email, self.phone_number)
        return self


class UserLogin(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    password: str
    remember_me: bool = False

    # validators

    @model_validator(mode="after")
    def validate_all(self) -> 'UserLogin':
        self.phone_number = validate_phone_number(
            self.phone_number) if self.phone_number else None
        validate_contact_required(self.email, self.phone_number)
        return self


class UserProfileResponse(BaseModel):
    id: int
    email: Optional[str] = None
    phone_number: Optional[str] = None
    full_name: str
    role: str
    citizen_id: Optional[str] = None
    medical_license: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    is_active: bool
    is_email_verified: bool
    is_phone_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = None
    citizen_id: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[Literal["male", "female", "other"]] = None
    blood_type: Optional[Literal["A", "B", "AB", "O", "A+",
                                 "B+", "AB+", "O+", "A-", "B-", "AB-", "O-"]] = None
    height: Optional[float] = Field(None, gt=0, le=300)
    weight: Optional[float] = Field(None, gt=0, le=500)
    medical_license: Optional[str] = None

    # validators

    @model_validator(mode="after")
    def validate_all(self) -> 'UserProfileUpdate':
        self.phone_number = validate_phone_number(
            self.phone_number) if self.phone_number else None
        return self


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str

    # validators

    @model_validator(mode="after")
    def validate_all(self) -> 'PasswordChange':
        if self.confirm_new_password != self.new_password:
            raise ValueError("New passwords do not match")
        return self


class PasswordReset(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    otp_code: str = Field(..., min_length=4, max_length=4)
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str

    # validators

    @model_validator(mode="after")
    def validate_all(self) -> 'PasswordReset':
        if self.confirm_new_password != self.new_password:
            raise ValueError("Passwords do not match")
        self.phone_number = validate_phone_number(
            self.phone_number) if self.phone_number else None
        return self


class BloodPressureRecordCreate(BaseModel):
    systolic: int = Field(..., ge=50, le=300,
                          description="Systolic pressure (50-300 mmHg)")
    diastolic: int = Field(..., ge=30, le=200,
                           description="Diastolic pressure (30-200 mmHg)")
    pulse: int = Field(..., ge=30, le=200,
                       description="Heart rate (30-200 bpm)")
    measurement_date: datetime
    measurement_time: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)


class BloodPressureRecordResponse(BaseModel):
    id: int
    systolic: int
    diastolic: int
    pulse: int
    measurement_date: datetime
    measurement_time: Optional[str] = None
    notes: Optional[str] = None
    image_path: Optional[str] = None
    ocr_confidence: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BloodPressureRecordUpdate(BaseModel):
    systolic: Optional[int] = Field(None, ge=50, le=300)
    diastolic: Optional[int] = Field(None, ge=30, le=200)
    pulse: Optional[int] = Field(None, ge=30, le=200)
    measurement_date: Optional[datetime] = None
    measurement_time: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None


class OCRResult(BaseModel):
    systolic: Optional[int] = None
    diastolic: Optional[int] = None
    pulse: Optional[int] = None
    time: Optional[str] = None
    confidence: Optional[float] = None
    image_metadata: Optional[dict] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None


class AccessRequestInput(BaseModel):
    patient_id: int


# =====================================================
# FastAPI App Setup
# =====================================================
app = FastAPI(
    title="Blood Pressure Monitoring API with OTP",
    description="Enhanced API with OTP-based authentication and authorization",
    version="2.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json"
)

# Security
security = HTTPBearer()
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# =====================================================
# Database Setup
# =====================================================


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create tables
Base.metadata.create_all(bind=engine)

# =====================================================
# Utility Functions
# =====================================================


def generate_request_id() -> str:
    return str(uuid.uuid4())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = now_th() + expires_delta
    else:
        expire = now_th() + \
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access_token"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    to_encode = data.copy()
    # Refresh token expires in 30 days
    expire = now_th() + timedelta(days=30)
    to_encode.update({"exp": expire, "type": "refresh_token"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def send_email_otp(recipient_email: str, otp: str, purpose: str):
    """Send OTP via email"""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        logger.warning("Email credentials not configured")
        return False

    try:
        subject_map = {
            "registration": "ยืนยันการลงทะเบียน - รหัส OTP",
            "login": "รหัส OTP สำหรับเข้าสู่ระบบ",
            "password_reset": "รีเซ็ตรหัสผ่าน - รหัส OTP",
            "email_verification": "ยืนยันอีเมล - รหัส OTP"
        }

        subject = subject_map.get(purpose, "รหัส OTP")

        message = MIMEMultipart()
        message["From"] = EMAIL_FROM
        message["To"] = recipient_email
        message["Subject"] = subject

        body = f"""
        รหัส OTP ของคุณคือ: {otp}
        
        รหัสนี้จะหมดอายุใน {OTP_EXPIRE_MINUTES} นาที
        
        หากคุณไม่ได้ทำการร้องขอนี้ กรุณาเพิกเฉยต่ออีเมลนี้ :3
        """

        message.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = message.as_string()
        server.sendmail(EMAIL_FROM, recipient_email, text)
        server.quit()

        logger.info(f"OTP email sent to {recipient_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email OTP: {str(e)}")
        return False


def send_sms_otp(phone: str, otp: str, purpose: str):
    """Send OTP via SMS"""
    if not SMS_API_URL or not SMS_API_KEY:
        logger.warning("SMS credentials not configured")
        return False

    try:
        message_map = {
            "registration": f"รหัส OTP สำหรับลงทะเบียน: {otp} (หมดอายุใน {OTP_EXPIRE_MINUTES} นาที)",
            "login": f"รหัส OTP เข้าสู่ระบบ: {otp} (หมดอายุใน {OTP_EXPIRE_MINUTES} นาที)",
            "password_reset": f"รหัส OTP รีเซ็ตรหัสผ่าน: {otp} (หมดอายุใน {OTP_EXPIRE_MINUTES} นาที)",
            "phone_verification": f"รหัส OTP ยืนยันเบอร์โทร: {otp} (หมดอายุใน {OTP_EXPIRE_MINUTES} นาที)"
        }

        message = message_map.get(purpose, f"รหัส OTP: {otp}")

        # Example for Thai SMS service (adjust based on your SMS provider)
        payload = {
            "to": phone,
            "from": SMS_FROM,
            "text": message
        }

        headers = {
            "Authorization": f"Bearer {SMS_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            SMS_API_URL, json=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            logger.info(f"OTP SMS sent to {phone}")
            return True
        else:
            logger.error(
                f"SMS API error: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Failed to send SMS OTP: {str(e)}")
        return False


def create_standard_response(
    status: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
    errors: Optional[List[Dict[str, Any]]] = None,
    request_id: Optional[str] = None
) -> StandardResponse:
    return StandardResponse(
        status=status,
        message=message,
        data=data,
        meta=meta,
        errors=errors,
        request_id=request_id or generate_request_id()
    )


def get_image_metadata(image_path: str) -> Optional[dict]:
    """Extract metadata from image"""
    try:
        img = PIL.Image.open(image_path)
        exif_data = img._getexif()
        if exif_data:
            metadata = {}
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                metadata[tag_name] = value
            return metadata
        return None
    except Exception as e:
        logger.error(f"Error reading image metadata: {e}")
        return None


# =====================================================
# Security Dependencies
# =====================================================


async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify API key for client applications"""
    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )
    return api_key


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user"""
    try:
        payload = jwt.decode(credentials.credentials,
                             SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "access_token":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=401, detail="Invalid authentication")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account deactivated")

    # Check if account is locked
    if user.account_locked_until and user.account_locked_until > now_th():
        raise HTTPException(
            status_code=423, detail="Account temporarily locked")

    return user


def is_account_locked(user: User) -> bool:
    """Check if user account is locked due to failed login attempts"""
    if user.account_locked_until and user.account_locked_until > now_th():
        return True
    return False


def lock_account(user: User, db: Session):
    """Lock user account for 30 minutes after too many failed attempts"""
    user.account_locked_until = now_th() + timedelta(minutes=30)
    user.failed_login_attempts = 0  # Reset counter
    db.commit()


def read_blood_pressure_with_gemini(image_path: str) -> OCRResult:
    """Read blood pressure values from image using Gemini API"""
    if not GOOGLE_AI_API_KEY:
        return OCRResult(error="Google AI API key not configured")

    model = genai.GenerativeModel('gemini-2.0-flash')

    try:
        img = PIL.Image.open(image_path)
    except FileNotFoundError:
        return OCRResult(error="Image not found")
    except Exception as e:
        return OCRResult(error=f"Error opening image: {str(e)}")

    prompt = """
    จากภาพเครื่องวัดความดันนี้:
    1. บอกค่าความดัน Systolic, Diastolic และ Pulse
    2. ให้บอกค่าเวลามาด้วย แต่ถ้าไม่มีค่าเวลาให้คืนเป็นค่าว่าง
    3. บอกค่ามาในรูปแบบ JSON เท่านั้น เช่น {"systolic": 120, "diastolic": 80, "pulse": 70, "time": "10:30"}
    4. ถ้าอ่านค่าไม่ได้ให้ใส่ null สำหรับค่านั้นๆ
    """

    try:
        response = model.generate_content([prompt, img])
        raw_text = response.text.replace("```json\n", "").replace(
            "\n```", "").replace("```json", "").replace("```", "").strip()

        try:
            result_data = json.loads(raw_text)
            metadata = get_image_metadata(image_path)

            return OCRResult(
                systolic=result_data.get("systolic"),
                diastolic=result_data.get("diastolic"),
                pulse=result_data.get("pulse"),
                time=result_data.get("time"),
                confidence=0.95,
                image_metadata=metadata
            )

        except json.JSONDecodeError:
            return OCRResult(
                error="Could not parse response as JSON",
                raw_response=raw_text,
                image_metadata=get_image_metadata(image_path)
            )

    except Exception as e:
        return OCRResult(
            error=f"Error calling Gemini API: {str(e)}",
            image_metadata=get_image_metadata(image_path)
        )


# =====================================================
# Exception Handlers
# =====================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = generate_request_id()
    logger.error(
        f"HTTP Exception: {exc.status_code} - {exc.detail} - Request ID: {request_id}")

    return JSONResponse(
        status_code=exc.status_code,
        content=create_standard_response(
            status="error",
            message=exc.detail,
            request_id=request_id
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    request_id = generate_request_id()
    logger.error(f"Unexpected error: {str(exc)} - Request ID: {request_id}")

    return JSONResponse(
        status_code=500,
        content=create_standard_response(
            status="error",
            message="Internal server error",
            request_id=request_id
        ).dict()
    )

# =====================================================
# API Routes
# =====================================================


@app.get("/")
async def root():
    return create_standard_response(
        status="success",
        message="Blood Pressure API with OTP System is running",
        data={"version": "1.0.0", "status": "healthy"}
    )


@app.get("/health")
async def health_check():
    request_id = generate_request_id()

    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    health_data = {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "google_ai": "configured" if GOOGLE_AI_API_KEY else "not_configured",
        "email_service": "configured" if EMAIL_USER else "not_configured",
        "sms_service": "configured" if SMS_API_URL else "not_configured",
        "timestamp": now_th().isoformat()
    }

    return create_standard_response(
        status="success" if health_data["status"] == "healthy" else "error",
        message="Health check completed",
        data=health_data,
        request_id=request_id
    )

# =====================================================
# OTP Management Routes
# =====================================================


@app.post("/api/v1/auth/request-otp", tags=["OTP"])
@limiter.limit("3/minute")
async def request_otp(
    request: Request,
    otp_request: OTPRequest,
    api_key: str = Depends(verify_api_key)
):
    request_id = generate_request_id()

    contact_method = "email" if otp_request.email else "sms"
    contact_target = (
        otp_request.email or otp_request.phone_number).strip().lower()

    # Generate OTP
    otp_code = otp_service.generate_otp(
        contact_target, expiration=OTP_EXPIRE_MINUTES * 60)

    # Send OTP
    send_success = False
    if contact_method == "email":
        send_success = send_email_otp(
            contact_target, otp_code, otp_request.purpose)
    else:
        send_success = send_sms_otp(
            contact_target, otp_code, otp_request.purpose)

    if not send_success:
        raise HTTPException(status_code=500, detail="Failed to send OTP")

    return create_standard_response(
        status="success",
        message=f"OTP sent to your {contact_method}",
        data={
            "contact_method": contact_method,
            "contact_target": contact_target[:3] + "*" * (len(contact_target) - 6) + contact_target[-3:],
            "expires_in_minutes": OTP_EXPIRE_MINUTES
        },
        request_id=request_id
    )


@app.post("/api/v1/auth/verify-otp", tags=["OTP"])
@limiter.limit("5/minute")
async def verify_otp(
    request: Request,
    otp_verification: OTPVerification,
    api_key: str = Depends(verify_api_key)
):
    request_id = generate_request_id()
    contact_target = (
        otp_verification.email or otp_verification.phone_number).strip().lower()

    if not otp_service.confirm_otp(contact_target, otp_verification.otp_code):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    return create_standard_response(
        status="success",
        message="OTP verified successfully",
        data={
            "verified": True,
            "purpose": otp_verification.purpose,
            "contact_target": contact_target
        },
        request_id=request_id
    )


# =====================================================
# Authentication Routes
# =====================================================


@app.post("/api/v1/auth/register", tags=["register"])
@limiter.limit("3/minute")
async def register_user(
    request: Request,
    user_data: UserRegister,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Register new user - requires prior OTP verification"""
    request_id = generate_request_id()

    contact_target = (
        user_data.email or user_data.phone_number).strip().lower()

    # ✅ Check if OTP has been verified for this contact
    if not otp_service.is_verified(contact_target):
        raise HTTPException(
            status_code=400,
            detail="Please verify your contact information with OTP first"
        )

    # ✅ Check for existing users
    if user_data.email:
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=400, detail="Email already registered")

    if user_data.phone_number:
        if db.query(User).filter(User.phone_number == user_data.phone_number).first():
            raise HTTPException(
                status_code=400, detail="Phone number already registered")

    if user_data.role == "doctor" and user_data.medical_license:
        if db.query(User).filter(User.medical_license == user_data.medical_license).first():
            raise HTTPException(
                status_code=400, detail="Medical license already registered")

    try:
        new_user = User(
            email=user_data.email,
            phone_number=user_data.phone_number,
            password_hash=hash_password(user_data.password),
            full_name=user_data.full_name,
            role=user_data.role,
            citizen_id=user_data.citizen_id,
            medical_license=user_data.medical_license,
            date_of_birth=user_data.date_of_birth,
            gender=user_data.gender,
            blood_type=user_data.blood_type,
            height=user_data.height,
            weight=user_data.weight,
            is_email_verified=bool(user_data.email),
            is_phone_verified=bool(user_data.phone_number),
            created_at=now_th(),
            updated_at=now_th()
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(
            f"New user registered: {contact_target} - Role: {new_user.role} - Request ID: {request_id}"
        )

        return create_standard_response(
            status="success",
            message="User registered successfully",
            data={
                "user_id": new_user.id,
                "email": new_user.email,
                "phone_number": new_user.phone_number,
                "role": new_user.role,
                "is_email_verified": new_user.is_email_verified,
                "is_phone_verified": new_user.is_phone_verified
            },
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Registration failed: {str(e)} - Request ID: {request_id}")
        raise HTTPException(status_code=500, detail="Registration failed")


@app.post("/api/v1/auth/login", tags=["authentication"])
@limiter.limit("5/minute")
async def login(
    request: Request,
    user_credentials: UserLogin,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """User login with email or phone number"""
    request_id = generate_request_id()

    # Find user by email or phone
    if user_credentials.email:
        user = db.query(User).filter(
            User.email == user_credentials.email).first()
    else:
        user = db.query(User).filter(User.phone_number ==
                                     user_credentials.phone_number).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check if account is locked
    if is_account_locked(user):
        raise HTTPException(
            status_code=423, detail="Account temporarily locked due to multiple failed attempts")

    # Verify password
    if not verify_password(user_credentials.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            lock_account(user, db)
            logger.warning(
                f"Account locked due to failed attempts: {user.email or user.phone_number} - Request ID: {request_id}")
            raise HTTPException(
                status_code=423, detail="Account locked due to multiple failed attempts")

        db.commit()
        logger.warning(
            f"Failed login attempt: {user.email or user.phone_number} - Attempts: {user.failed_login_attempts} - Request ID: {request_id}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is deactivated")

    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.last_login = now_th()
    user.account_locked_until = None
    db.commit()

    # Create tokens
    token_data = {"user_id": user.id, "email": user.email}

    if user_credentials.remember_me:
        expires_delta = timedelta(days=30)
    else:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data=token_data, expires_delta=expires_delta)
    refresh_token = create_refresh_token(data=token_data)

    # Create session record
    session = UserSession(
        user_id=user.id,
        session_token=secrets.token_urlsafe(32),
        device_info=request.headers.get("user-agent", "")[:500],
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", "")[:500],
        expires_at=now_th() + expires_delta
    )

    db.add(session)
    db.commit()

    logger.info(
        f"Successful login: {user.email or user.phone_number} - Request ID: {request_id}")

    return create_standard_response(
        status="success",
        message="Login successful",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(expires_delta.total_seconds()),
            "user": {
                "id": user.id,
                "email": user.email,
                "phone_number": user.phone_number,
                "role": user.role,
                "full_name": user.full_name,
                "is_email_verified": user.is_email_verified,
                "is_phone_verified": user.is_phone_verified
            }
        },
        request_id=request_id
    )


@app.post("/api/v1/auth/logout", tags=["authentication"])
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Logout user and invalidate session"""
    request_id = generate_request_id()

    # Invalidate all active sessions for this user
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True
    ).update({"is_active": False})

    db.commit()

    logger.info(
        f"User logged out: {current_user.email or current_user.phone_number} - Request ID: {request_id}")

    return create_standard_response(
        status="success",
        message="Logged out successfully",
        request_id=request_id
    )

# =====================================================
# Password Management Routes
# =====================================================


@app.post("/api/v1/auth/change-password", tags=["authentication"])
async def change_password(
    request: Request,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Change password for authenticated user"""
    request_id = generate_request_id()

    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=400, detail="Current password is incorrect")

    try:
        # Update password
        current_user.password_hash = hash_password(password_data.new_password)
        current_user.updated_at = now_th()

        # Invalidate all sessions except current one
        db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True
        ).update({"is_active": False})

        db.commit()

        logger.info(
            f"Password changed for user: {current_user.email or current_user.phone_number} - Request ID: {request_id}")

        return create_standard_response(
            status="success",
            message="Password changed successfully",
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Password change failed: {str(e)} - Request ID: {request_id}")
        raise HTTPException(
            status_code=500, detail="Failed to change password")


@app.post("/api/v1/auth/reset-password", tags=["authentication"])
@limiter.limit("3/minute")
async def reset_password(
    request: Request,
    reset_data: PasswordReset,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Reset password via OTP verification"""
    request_id = generate_request_id()

    # 🔍 Find user by email or phone
    if reset_data.email:
        user = db.query(User).filter(User.email == reset_data.email).first()
    else:
        user = db.query(User).filter(User.phone_number ==
                                     reset_data.phone_number).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ✅ Verify OTP (in-memory)
    contact_target = (
        reset_data.email or reset_data.phone_number).strip().lower()
    if not otp_service.confirm_otp(contact_target, reset_data.otp_code):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    try:
        # ✅ Update password and unlock account
        user.password_hash = hash_password(reset_data.new_password)
        user.updated_at = now_th()
        user.failed_login_attempts = 0
        user.account_locked_until = None

        # 🔒 Invalidate all user sessions
        db.query(UserSession).filter(UserSession.user_id == user.id).delete()

        db.commit()

        logger.info(
            f"Password reset successful for user: {contact_target} - Request ID: {request_id}"
        )

        return create_standard_response(
            status="success",
            message="Password reset successful",
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Password reset failed: {str(e)} - Request ID: {request_id}")
        raise HTTPException(status_code=500, detail="Password reset failed")


# =====================================================
# User Profile Routes
# =====================================================


@app.get("/api/v1/users/me",  tags=["user"])
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """Get current user profile"""
    request_id = generate_request_id()

    user_profile = UserProfileResponse.model_validate(current_user)

    return create_standard_response(
        status="success",
        message="Profile retrieved successfully",
        data={"profile": user_profile.dict()},
        request_id=request_id
    )


@app.put("/api/v1/users/me", response_model=StandardResponse, tags=["user"])
async def update_user_profile(
    user_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    request_id = generate_request_id()

    # Check if phone number is already taken by another user
    if user_update.phone_number and user_update.phone_number != current_user.phone_number:
        # Require contact verification
        if not current_user.is_phone_verified:
            raise HTTPException(
                status_code=400, detail="Please verify your phone number before updating it")

        existing_user = db.query(User).filter(
            User.phone_number == user_update.phone_number,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=400, detail="Phone number already taken")

    # Check if email is already taken by another user
    if user_update.email and user_update.email != current_user.email:
        if not current_user.is_email_verified:
            raise HTTPException(
                status_code=400, detail="Please verify your email before updating it")

        existing_user = db.query(User).filter(
            User.email == user_update.email,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=400, detail="Email already taken")

    # Check if medical license is already taken (for doctors)
    if (user_update.medical_license and
        current_user.role == "doctor" and
            user_update.medical_license != current_user.medical_license):
        existing_doctor = db.query(User).filter(
            User.medical_license == user_update.medical_license,
            User.id != current_user.id
        ).first()
        if existing_doctor:
            raise HTTPException(
                status_code=400, detail="Medical license already taken")

    try:
        # Update fields
        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(current_user, field, value)

        current_user.updated_at = now_th()
        db.commit()
        db.refresh(current_user)

        logger.info(
            f"Profile updated for user: {current_user.email} - Request ID: {request_id}")

        user_profile = UserProfileResponse.model_validate(current_user)

        return create_standard_response(
            status="success",
            message="Profile updated successfully",
            data={"profile": user_profile.dict()},
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Profile update failed for user {current_user.email}: {str(e)} - Request ID: {request_id}")
        raise HTTPException(status_code=500, detail="Profile update failed")


@app.post("/api/v1/auth/verify-contact", tags=["authentication"])
@limiter.limit("3/minute")
async def verify_contact_method(
    request: Request,
    verification_data: OTPVerification,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Verify email or phone number for existing user"""
    request_id = generate_request_id()

    contact_target = (
        verification_data.email or verification_data.phone_number).strip().lower()

    # ✅ In-memory OTP verification
    if not otp_service.confirm_otp(contact_target, verification_data.otp_code):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    try:
        # ✅ Update user verification flags
        if verification_data.purpose == "email_verification":
            current_user.is_email_verified = True
            current_user.email = contact_target
        elif verification_data.purpose == "phone_verification":
            current_user.is_phone_verified = True
            current_user.phone_number = contact_target

        current_user.updated_at = now_th()
        db.commit()

        logger.info(
            f"Contact verified - User: {current_user.id} - Type: {verification_data.purpose} - Request ID: {request_id}"
        )

        return create_standard_response(
            status="success",
            message="Contact method verified successfully",
            data={
                "verified": True,
                "contact_type": verification_data.purpose,
                "contact_target": contact_target
            },
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Contact verification failed: {str(e)} - Request ID: {request_id}")
        raise HTTPException(
            status_code=500, detail="Failed to verify contact method")


# =====================================================
# Blood Pressure Records Routes
# =====================================================


@app.get("/api/v1/bp-records", response_model=StandardResponse, tags=["blood pressure"])
async def get_bp_records(
    page: int = 1,
    per_page: int = 20,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get blood pressure records with pagination"""
    request_id = generate_request_id()

    if per_page > 100:
        per_page = 100

    skip = (page - 1) * per_page

    query = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id)

    if start_date:
        query = query.filter(
            BloodPressureRecord.measurement_date >= start_date)
    if end_date:
        query = query.filter(BloodPressureRecord.measurement_date <= end_date)

    total = query.count()
    records = query.order_by(BloodPressureRecord.measurement_date.desc()).offset(
        skip).limit(per_page).all()

    total_pages = (total + per_page - 1) // per_page

    records_data = [BloodPressureRecordResponse.model_validate(
        record).dict() for record in records]

    pagination_meta = PaginationMeta(
        current_page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages
    )

    return create_standard_response(
        status="success",
        message="Records retrieved successfully",
        data={"records": records_data},
        meta={"pagination": pagination_meta.dict()},
        request_id=request_id
    )


@app.post("/api/v1/bp-records", response_model=StandardResponse, tags=["blood pressure"])
async def create_bp_record(
    record_data: BloodPressureRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new blood pressure record"""
    request_id = generate_request_id()

    try:
        db_record = BloodPressureRecord(
            user_id=current_user.id,
            systolic=record_data.systolic,
            diastolic=record_data.diastolic,
            pulse=record_data.pulse,
            measurement_date=record_data.measurement_date,
            measurement_time=record_data.measurement_time,
            notes=record_data.notes
        )

        db.add(db_record)
        db.commit()
        db.refresh(db_record)

        logger.info(
            f"BP record created for user {current_user.email} - Record ID: {db_record.id} - Request ID: {request_id}")

        record_response = BloodPressureRecordResponse.model_validate(db_record)

        return create_standard_response(
            status="success",
            message="Blood pressure record created successfully",
            data={"record": record_response.dict()},
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"BP record creation failed for user {current_user.email}: {str(e)} - Request ID: {request_id}")
        raise HTTPException(status_code=500, detail="Failed to create record")


@app.get("/api/v1/bp-records/{record_id}", response_model=StandardResponse, tags=["blood pressure"])
async def get_bp_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific blood pressure record"""
    request_id = generate_request_id()

    record = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.id == record_id,
        BloodPressureRecord.user_id == current_user.id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    record_response = BloodPressureRecordResponse.model_validate(record)

    return create_standard_response(
        status="success",
        message="Record retrieved successfully",
        data={"record": record_response.dict()},
        request_id=request_id
    )


@app.put("/api/v1/bp-records/{record_id}", response_model=StandardResponse, tags=["blood pressure"])
async def update_bp_record(
    record_id: int,
    record_update: BloodPressureRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update blood pressure record"""
    request_id = generate_request_id()

    record = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.id == record_id,
        BloodPressureRecord.user_id == current_user.id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    try:
        update_data = record_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(record, field, value)

        db.commit()
        db.refresh(record)

        logger.info(
            f"BP record updated - Record ID: {record_id} - User: {current_user.email} - Request ID: {request_id}")

        record_response = BloodPressureRecordResponse.model_validate(record)

        return create_standard_response(
            status="success",
            message="Record updated successfully",
            data={"record": record_response.dict()},
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"BP record update failed - Record ID: {record_id}: {str(e)} - Request ID: {request_id}")
        raise HTTPException(status_code=500, detail="Failed to update record")


@app.delete("/api/v1/bp-records/{record_id}", response_model=StandardResponse, tags=["blood pressure"])
async def delete_bp_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete blood pressure record"""
    request_id = generate_request_id()

    record = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.id == record_id,
        BloodPressureRecord.user_id == current_user.id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    try:
        db.delete(record)
        db.commit()

        logger.info(
            f"BP record deleted - Record ID: {record_id} - User: {current_user.email} - Request ID: {request_id}")

        return create_standard_response(
            status="success",
            message="Record deleted successfully",
            data={"deleted_record_id": record_id},
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"BP record deletion failed - Record ID: {record_id}: {str(e)} - Request ID: {request_id}")
        raise HTTPException(status_code=500, detail="Failed to delete record")

# =====================================================
# OCR Routes
# =====================================================


@app.post("/api/v1/ocr/process-image", response_model=StandardResponse, tags=["blood pressure"])
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
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        ocr_result = read_blood_pressure_with_gemini(temp_file_path)
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
            data={
                "ocr_result": {
                    "systolic": ocr_result.systolic,
                    "diastolic": ocr_result.diastolic,
                    "pulse": ocr_result.pulse,
                    "measurement_time": ocr_result.time,
                    "confidence": ocr_result.confidence
                },
                "image_metadata": ocr_result.image_metadata
            },
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        logger.error(
            f"OCR processing error: {str(e)} - Request ID: {request_id}")
        raise HTTPException(status_code=500, detail="Error processing image")


@app.post("/api/v1/bp-records/save-from-ocr", response_model=StandardResponse, tags=["blood pressure"])
async def save_from_ocr(
    data: BloodPressureRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save blood pressure record from OCR result"""
    request_id = generate_request_id()

    try:
        db_record = BloodPressureRecord(
            user_id=current_user.id,
            systolic=data.systolic,
            diastolic=data.diastolic,
            pulse=data.pulse,
            measurement_date=data.measurement_date,
            measurement_time=data.measurement_time,
            notes=data.notes,
        )

        db.add(db_record)
        db.commit()
        db.refresh(db_record)

        logger.info(
            f"OCR-based BP record saved - Record ID: {db_record.id} - User: {current_user.email} - Request ID: {request_id}")

        record_response = BloodPressureRecordResponse.model_validate(db_record)

        return create_standard_response(
            status="success",
            message="OCR-based record saved successfully",
            data={"record": record_response.dict()},
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"OCR-based record save failed for user {current_user.email}: {str(e)} - Request ID: {request_id}")
        raise HTTPException(
            status_code=500, detail="Failed to save OCR-based record")

# =====================================================
# Doctor-Patient Management Routes
# =====================================================


class DoctorAuthorizationInput(BaseModel):
    doctor_id: int


@app.post("/api/v1/patient/authorize-doctor", response_model=StandardResponse, tags=["patient view"])
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
            hospital=None  # or omit this if nullable=True in DB
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
                    "doctor_id": relation.doctor_id,
                    "authorized_at": relation.created_at.isoformat()
                }
            },
            request_id=request_id
        )
    except Exception as e:
        db.rollback()
        logger.error(
            f"Doctor authorization failed: {str(e)} - Request ID: {request_id}")
        raise HTTPException(
            status_code=500, detail="Failed to authorize doctor")


@app.get("/api/v1/patient/authorized-doctors", response_model=StandardResponse, tags=["patient view"])
async def get_authorized_doctors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient views authorized doctors"""
    request_id = generate_request_id()

    if current_user.role != "patient":
        raise HTTPException(
            status_code=403, detail="Only patients can view authorized doctors")

    relations = db.query(DoctorPatient).filter(
        DoctorPatient.patient_id == current_user.id,
        DoctorPatient.is_active == True
    ).all()

    doctors_data = []
    for relation in relations:
        doctor_profile = UserProfileResponse.model_validate(relation.doctor)
        doctors_data.append({
            "relation_id": relation.id,
            "doctor": doctor_profile.dict(),
            "hospital": relation.hospital,
            "authorized_at": relation.created_at
        })

    return create_standard_response(
        status="success",
        message="Authorized doctors retrieved successfully",
        data={"authorized_doctors": doctors_data},
        request_id=request_id
    )


@app.delete("/api/v1/patient/authorized-doctors/{doctor_id}", response_model=StandardResponse, tags=["patient view"])
async def revoke_doctor_access(
    doctor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient revokes doctor access"""
    request_id = generate_request_id()

    if current_user.role != "patient":
        raise HTTPException(
            status_code=403, detail="Only patients can revoke access")

    relation = db.query(DoctorPatient).filter_by(
        doctor_id=doctor_id,
        patient_id=current_user.id,
        is_active=True
    ).first()

    if not relation:
        raise HTTPException(status_code=404, detail="Doctor access not found")

    try:
        relation.is_active = False
        db.commit()

        logger.info(
            f"Doctor access revoked - Doctor ID: {doctor_id} - Patient: {current_user.email} - Request ID: {request_id}")

        return create_standard_response(
            status="success",
            message="Doctor access revoked successfully",
            data={"revoked_doctor_id": doctor_id},
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Access revocation failed - Doctor ID: {doctor_id}: {str(e)} - Request ID: {request_id}")
        raise HTTPException(status_code=500, detail="Failed to revoke access")


@app.get("/api/v1/patient/access-requests", response_model=StandardResponse, tags=["patient view"])
async def view_access_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient views pending access requests"""
    request_id = generate_request_id()

    if current_user.role != "patient":
        raise HTTPException(
            status_code=403, detail="Only patients can view access requests")

    requests = db.query(AccessRequest).filter_by(
        patient_id=current_user.id,
        status="pending"
    ).all()

    requests_data = []
    for req in requests:
        doctor_profile = UserProfileResponse.model_validate(req.doctor)
        requests_data.append({
            "request_id": req.id,
            "doctor": doctor_profile.dict(),
            "requested_at": req.created_at,
            "status": req.status
        })

    return create_standard_response(
        status="success",
        message="Access requests retrieved successfully",
        data={"access_requests": requests_data},
        request_id=request_id
    )


@app.post("/api/v1/patient/access-requests/{request_id}/approve", response_model=StandardResponse, tags=["patient view"])
async def approve_request(
    request_id: int,
    hospital: Optional[str] = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient approves doctor access request"""
    req_id = generate_request_id()

    req = db.query(AccessRequest).filter_by(id=request_id).first()

    if not req or req.patient_id != current_user.id:
        raise HTTPException(status_code=404, detail="Access request not found")

    if req.status != "pending":
        raise HTTPException(
            status_code=400, detail="Request already processed")

    try:
        req.status = "approved"

        # Create doctor-patient relationship
        existing = db.query(DoctorPatient).filter_by(
            doctor_id=req.doctor_id,
            patient_id=req.patient_id
        ).first()

        if not existing:
            db.add(DoctorPatient(
                doctor_id=req.doctor_id,
                patient_id=req.patient_id,
                hospital=hospital or "",
                is_active=True
            ))
        else:
            existing.is_active = True
            existing.hospital = hospital or existing.hospital

        db.commit()

        logger.info(
            f"Access request approved - Request ID: {request_id} - Patient: {current_user.email} - Request ID: {req_id}")

        return create_standard_response(
            status="success",
            message="Access request approved successfully",
            data={"approved_request_id": request_id},
            request_id=req_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Access approval failed - Request ID: {request_id}: {str(e)} - Request ID: {req_id}")
        raise HTTPException(
            status_code=500, detail="Failed to approve access request")


@app.post("/api/v1/patient/access-requests/{request_id}/reject", response_model=StandardResponse, tags=["patient view"])
async def reject_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient rejects doctor access request"""
    req_id = generate_request_id()

    req = db.query(AccessRequest).filter_by(id=request_id).first()

    if not req or req.patient_id != current_user.id:
        raise HTTPException(status_code=404, detail="Access request not found")

    if req.status != "pending":
        raise HTTPException(
            status_code=400, detail="Request already processed")

    try:
        req.status = "rejected"
        db.commit()

        logger.info(
            f"Access request rejected - Request ID: {request_id} - Patient: {current_user.email} - Request ID: {req_id}")

        return create_standard_response(
            status="success",
            message="Access request rejected successfully",
            data={"rejected_request_id": request_id},
            request_id=req_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Access rejection failed - Request ID: {request_id}: {str(e)} - Request ID: {req_id}")
        raise HTTPException(
            status_code=500, detail="Failed to reject access request")


@app.post("/api/v1/doctor/request-access", response_model=StandardResponse, tags=["doctor view"])
async def request_patient_access(
    data: AccessRequestInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Doctor requests access to patient data"""
    request_id = generate_request_id()

    if current_user.role != "doctor":
        raise HTTPException(
            status_code=403, detail="Only doctors can request access")

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

        logger.info(
            f"Access request sent - Doctor: {current_user.email} - Patient: {patient.email} - Request ID: {request_id}")

        return create_standard_response(
            status="success",
            message="Access request sent successfully",
            data={
                "patient_name": patient.full_name,
                "patient_email": patient.email,
                "request_id": request_obj.id
            },
            request_id=request_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Access request failed - Doctor: {current_user.email}: {str(e)} - Request ID: {request_id}")
        raise HTTPException(
            status_code=500, detail="Failed to send access request")


@app.get("/api/v1/doctor/access-requests", response_model=StandardResponse, tags=["doctor view"])
async def doctor_view_access_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Doctor views their access requests (pending, approved, or rejected)"""
    request_id = generate_request_id()

    if current_user.role != "doctor":
        raise HTTPException(
            status_code=403, detail="Only doctors can view access requests")

    requests = db.query(AccessRequest).filter_by(
        doctor_id=current_user.id
    ).order_by(AccessRequest.created_at.desc()).all()

    requests_data = []
    for req in requests:
        patient_profile = UserProfileResponse.model_validate(req.patient)
        requests_data.append({
            "request_id": req.id,
            "patient": patient_profile.dict(),
            "status": req.status,
            "requested_at": req.created_at
        })

    return create_standard_response(
        status="success",
        message="Access requests retrieved successfully",
        data={"access_requests": requests_data},
        request_id=request_id
    )


@app.get("/api/v1/doctor/patients", response_model=StandardResponse, tags=["doctor view"])
async def get_doctor_patients(
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get doctor's patient list with pagination"""
    request_id = generate_request_id()

    if current_user.role != "doctor":
        raise HTTPException(
            status_code=403, detail="Only doctors can access patient lists")

    if per_page > 100:
        per_page = 100

    skip = (page - 1) * per_page

    query = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == current_user.id,
        DoctorPatient.is_active == True
    )

    total = query.count()
    relations = query.offset(skip).limit(per_page).all()

    total_pages = (total + per_page - 1) // per_page

    patients_data = []
    for relation in relations:
        patient_profile = UserProfileResponse.model_validate(relation.patient)
        patients_data.append({
            "relation_id": relation.id,
            "patient": patient_profile.dict(),
            "hospital": relation.hospital,
            "authorized_at": relation.created_at
        })

    pagination_meta = PaginationMeta(
        current_page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages
    )

    return create_standard_response(
        status="success",
        message="Patients retrieved successfully",
        data={"patients": patients_data},
        meta={"pagination": pagination_meta.dict()},
        request_id=request_id
    )


@app.get("/api/v1/doctor/patients/{patient_id}/bp-records", response_model=StandardResponse, tags=["doctor view"])
async def get_patient_bp_records(
    patient_id: int,
    page: int = 1,
    per_page: int = 20,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get patient's blood pressure records (doctor access)"""
    request_id = generate_request_id()

    if current_user.role != "doctor":
        raise HTTPException(
            status_code=403, detail="Only doctors can access patient records")

    # Check if doctor has access to this patient
    relation = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == current_user.id,
        DoctorPatient.patient_id == patient_id,
        DoctorPatient.is_active == True
    ).first()

    if not relation:
        raise HTTPException(
            status_code=403, detail="No access to this patient")

    if per_page > 100:
        per_page = 100

    skip = (page - 1) * per_page

    query = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == patient_id)

    if start_date:
        query = query.filter(
            BloodPressureRecord.measurement_date >= start_date)
    if end_date:
        query = query.filter(BloodPressureRecord.measurement_date <= end_date)

    total = query.count()
    records = query.order_by(BloodPressureRecord.measurement_date.desc()).offset(
        skip).limit(per_page).all()

    total_pages = (total + per_page - 1) // per_page

    records_data = [BloodPressureRecordResponse.model_validate(
        record).model_dump() for record in records]

    pagination_meta = PaginationMeta(
        current_page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages
    )

    return create_standard_response(
        status="success",
        message="Patient records retrieved successfully",
        data={
            "patient_id": patient_id,
            "records": records_data
        },
        meta={"pagination": pagination_meta.dict()},
        request_id=request_id
    )


@app.delete("/api/v1/doctor/access-requests/{request_id}", response_model=StandardResponse, tags=["doctor view"])
async def delete_access_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Doctor deletes a pending access request"""
    req_id = generate_request_id()

    req = db.query(AccessRequest).filter_by(id=request_id).first()

    if not req or req.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Access request not found")

    if req.status != "pending":
        raise HTTPException(
            status_code=400, detail="Only pending requests can be deleted")

    try:
        db.delete(req)
        db.commit()

        logger.info(
            f"Access request deleted - Request ID: {request_id} - Doctor: {current_user.email} - Request ID: {req_id}")

        return create_standard_response(
            status="success",
            message="Access request deleted successfully",
            data={"deleted_request_id": request_id},
            request_id=req_id
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Access request deletion failed - Request ID: {request_id} - {str(e)} - Request ID: {req_id}")
        raise HTTPException(
            status_code=500, detail="Failed to delete access request")


# =====================================================
# Statistics Routes
# =====================================================


@app.get("/api/v1/stats/summary", response_model=StandardResponse, tags=["blood pressure"])
async def get_bp_summary(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get blood pressure summary statistics"""
    request_id = generate_request_id()

    if days > 365:
        days = 365  # Limit to 1 year max

    start_date = now_th() - timedelta(days=days)

    records = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id,
        BloodPressureRecord.measurement_date >= start_date
    ).all()

    if not records:
        return create_standard_response(
            status="success",
            message="No records found for the specified period",
            data={"summary": None, "period_days": days},
            request_id=request_id
        )

    systolic_values = [r.systolic for r in records]
    diastolic_values = [r.diastolic for r in records]
    pulse_values = [r.pulse for r in records]

    summary = {
        "total_records": len(records),
        "period_days": days,
        "systolic": {
            "average": round(sum(systolic_values) / len(systolic_values), 1),
            "min": min(systolic_values),
            "max": max(systolic_values)
        },
        "diastolic": {
            "average": round(sum(diastolic_values) / len(diastolic_values), 1),
            "min": min(diastolic_values),
            "max": max(diastolic_values)
        },
        "pulse": {
            "average": round(sum(pulse_values) / len(pulse_values), 1),
            "min": min(pulse_values),
            "max": max(pulse_values)
        }
    }

    return create_standard_response(
        status="success",
        message="Statistics retrieved successfully",
        data={"summary": summary},
        request_id=request_id
    )

# =====================================================
# Configuration and Info Routes
# =====================================================


@app.get("/api/v1/config/info", response_model=StandardResponse)
async def get_config_info():
    """Get API configuration information"""
    request_id = generate_request_id()

    config_info = {
        "api_name": "Blood Pressure Monitoring API",
        "version": "1.0.0",
        "features": [
            "User Registration & Authentication with Phone Number",
            "Role-based Access Control (Patient/Doctor)",
            "Blood Pressure Record Management",
            "Google Generative AI OCR Integration",
            "Doctor-Patient Access Management",
            "Statistics & Analytics",
            "Rate Limiting & Security",
            "Standardized API Responses"
        ],
        "ai_model": "gemini-2.0-flash",
        "database": "SQLite" if "sqlite" in DATABASE_URL else "PostgreSQL",
        "rate_limits": {
            "registration": "5/minute",
            "login": "10/minute",
            "ocr_processing": "10/minute"
        },
        "supported_formats": {
            "images": ["JPEG", "PNG", "GIF"],
            "max_image_size": "10MB"
        }
    }

    return create_standard_response(
        status="success",
        message="Configuration information retrieved",
        data={"config": config_info},
        request_id=request_id
    )

# =====================================================
# Search and Filter Routes
# =====================================================


@app.get("/api/v1/users/search", response_model=StandardResponse, tags=["user"])
async def search_users(
    q: str,
    role: Optional[Literal["patient", "doctor"]] = None,
    page: int = 1,
    per_page: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search users by full name, ID, or medical license"""
    request_id = generate_request_id()

    if len(q) < 1:
        raise HTTPException(
            status_code=400, detail="Search query must not be empty")

    if per_page > 50:
        per_page = 50

    skip = (page - 1) * per_page

    query = db.query(User).filter(User.is_active == True)

    # Apply role filter if provided
    if role:
        query = query.filter(User.role == role)

    # Perform search in full_name, id, and medical_license
    search_filter = (
        User.full_name.ilike(f"%{q}%") |
        User.medical_license.ilike(f"%{q}%")
    )

    # If query is numeric, include ID
    if q.isdigit():
        search_filter |= (User.id == int(q))

    query = query.filter(search_filter)

    total = query.count()
    users = query.offset(skip).limit(per_page).all()

    total_pages = (total + per_page - 1) // per_page

    # Return only safe fields
    users_data = [
        {
            "id": user.id,
            "full_name": user.full_name,
            "medical_license": user.medical_license
        }
        for user in users
    ]

    pagination_meta = PaginationMeta(
        current_page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages
    )

    return create_standard_response(
        status="success",
        message="Search completed successfully",
        data={
            "users": users_data,
            "search_query": q
        },
        meta={"pagination": pagination_meta.dict()},
        request_id=request_id
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info",
        access_log=True
    )

print("📦 DATABASE_URL = ", os.getenv("DATABASE_URL"))
