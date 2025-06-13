"""
Blood Pressure App - FastAPI Server with Google Generative AI OCR
Comprehensive API for blood pressure monitoring application
"""

from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime, timedelta
from typing import Optional, List
import bcrypt
import jwt
import os
import io
import json
import tempfile

# Google Generative AI imports
import google.generativeai as genai
import PIL.Image
from PIL.ExifTags import TAGS

# =====================================================
# Configuration
# =====================================================
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Google AI Configuration
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY")
genai.configure(api_key=GOOGLE_AI_API_KEY)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./blood_pressure.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =====================================================
# Database Models
# =====================================================


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    citizen_id = Column(String, unique=True, nullable=True)
    medical_license = Column(String, unique=True, nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String, nullable=True)
    blood_type = Column(String, nullable=True)
    height = Column(Float, nullable=True)  # cm
    weight = Column(Float, nullable=True)  # kg
    role = Column(String, default="patient")  # patient, doctor
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    bp_records = relationship("BloodPressureRecord", back_populates="user")
    doctor_patients = relationship(
        "DoctorPatient", foreign_keys="DoctorPatient.doctor_id", back_populates="doctor")
    patient_doctors = relationship(
        "DoctorPatient", foreign_keys="DoctorPatient.patient_id", back_populates="patient")


class BloodPressureRecord(Base):
    __tablename__ = "blood_pressure_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    systolic = Column(Integer, nullable=False)
    diastolic = Column(Integer, nullable=False)
    pulse = Column(Integer, nullable=False)
    measurement_date = Column(DateTime, nullable=False)
    measurement_time = Column(String, nullable=True)  # เพิ่มฟิลด์เวลาจาก OCR
    notes = Column(Text, nullable=True)
    image_path = Column(String, nullable=True)
    ocr_confidence = Column(Float, nullable=True)  # เพิ่มค่า confidence
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="bp_records")


class DoctorPatient(Base):
    __tablename__ = "doctor_patients"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    hospital = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    doctor = relationship("User", foreign_keys=[
                          doctor_id], back_populates="doctor_patients")
    patient = relationship("User", foreign_keys=[
                           patient_id], back_populates="patient_doctors")


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)

    doctor = relationship("User", foreign_keys=[doctor_id])
    patient = relationship("User", foreign_keys=[patient_id])

# =====================================================
# Pydantic Models
# =====================================================


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    citizen_id: Optional[str] = None
    medical_license: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    role: str = "patient"


class UserCreate(UserBase):
    password: str
    confirm_password: str

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('passwords do not match')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    citizen_id: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None


class BloodPressureRecordCreate(BaseModel):
    systolic: int
    diastolic: int
    pulse: int
    measurement_date: datetime
    measurement_time: Optional[str] = None
    notes: Optional[str] = None


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
    systolic: Optional[int] = None
    diastolic: Optional[int] = None
    pulse: Optional[int] = None
    measurement_date: Optional[datetime] = None
    measurement_time: Optional[str] = None
    notes: Optional[str] = None


class DoctorPatientCreate(BaseModel):
    patient_id: int
    hospital: Optional[str] = None


class DoctorPatientResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    hospital: Optional[str] = None
    is_active: bool
    created_at: datetime
    patient: UserResponse

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class OCRResult(BaseModel):
    systolic: Optional[int] = None
    diastolic: Optional[int] = None
    pulse: Optional[int] = None
    time: Optional[str] = None
    confidence: Optional[float] = None
    image_metadata: Optional[dict] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None


class OCRProcessRequest(BaseModel):
    auto_save: bool = False  # ถ้าเป็น True จะบันทึกข้อมูลอัตโนมัติ
    notes: Optional[str] = None


class AccessRequestInput(BaseModel):
    patient_email: str


# =====================================================
# FastAPI App Setup
# =====================================================
app = FastAPI(
    title="Blood Pressure Monitoring API",
    description="API for blood pressure monitoring application with Google AI OCR",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

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


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(data: dict):
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Get current authenticated user"""
    try:
        payload = jwt.decode(credentials.credentials,
                             SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=401, detail="Invalid authentication")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_image_metadata(image_path: str) -> Optional[dict]:
    """ดึงข้อมูล metadata จากภาพ"""
    try:
        img = PIL.Image.open(image_path)
        exif_data = img._getexif()
        if exif_data:
            metadata = {}
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                metadata[tag_name] = value
            return metadata
        else:
            return None
    except Exception as e:
        print(f"Error reading metadata: {e}")
        return None


def read_blood_pressure_with_gemini(image_path: str) -> OCRResult:
    """อ่านค่าความดันและอัตราการเต้นของหัวใจจากภาพถ่ายหน้าจอเครื่องวัดความดันโดยใช้ Gemini API"""
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
        # ตัดเครื่องหมาย ```json\n และ \n``` ออก
        raw_text = response.text.replace("```json\n", "").replace(
            "\n```", "").replace("```json", "").replace("```", "").strip()

        try:
            result_data = json.loads(raw_text)

            # ดึง metadata จากภาพ
            metadata = get_image_metadata(image_path)

            # สร้าง OCRResult
            ocr_result = OCRResult(
                systolic=result_data.get("systolic"),
                diastolic=result_data.get("diastolic"),
                pulse=result_data.get("pulse"),
                time=result_data.get("time"),
                confidence=0.95,  # ค่าเริ่มต้น เนื่องจาก Gemini ไม่ return confidence
                image_metadata=metadata
            )

            return ocr_result

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
# API Routes
# =====================================================


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Blood Pressure API with Google AI OCR is running", "status": "healthy"}

# Authentication Routes


@app.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register new user"""

    # Email uniqueness
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if user.citizen_id and db.query(User).filter(User.citizen_id == user.citizen_id).first():
        raise HTTPException(
            status_code=400, detail="Citizen ID already registered")

    # --- Role-specific validation ---
    if user.role == "doctor":
        if not user.medical_license:
            raise HTTPException(
                status_code=400, detail="Doctors must provide a medical license number")
        if db.query(User).filter(User.medical_license == user.medical_license).first():
            raise HTTPException(
                status_code=400, detail="Medical license already registered")
    elif user.role == "patient":
        if user.medical_license:
            raise HTTPException(
                status_code=400, detail="Patients must not provide a medical license")
    else:
        raise HTTPException(status_code=400, detail="Invalid role")

    # Create new user
    db_user = User(
        email=user.email,
        password_hash=hash_password(user.password),
        full_name=user.full_name,
        citizen_id=user.citizen_id,
        medical_license=user.medical_license if user.role == "doctor" else None,
        date_of_birth=user.date_of_birth,
        gender=user.gender,
        blood_type=user.blood_type,
        height=user.height,
        weight=user.weight,
        role=user.role
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@app.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """User login"""
    user = db.query(User).filter(User.email == user_credentials.email).first()

    if not user or not verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=401, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is deactivated")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# User Profile Routes


@app.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@app.put("/users/me", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    update_data = user_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    return current_user

# Blood Pressure Records Routes -> @app.post("/bp-records", response_model=BloodPressureRecordResponse)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    return db_record

    if start_date:
        query = query.filter(
            BloodPressureRecord.measurement_date >= start_date)
    if end_date:
        query = query.filter(BloodPressureRecord.measurement_date <= end_date)

    records = query.order_by(BloodPressureRecord.measurement_date.desc()).offset(
        skip).limit(limit).all()
    return records

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    return record

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    update_data = record_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)

    return record

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    db.delete(record)
    db.commit()

    return {"message": "Record deleted successfully"}

# =====================================================
# OCR Routes - Updated with Google Generative AI
# =====================================================


@app.post("/ocr/process-image")
async def process_bp_image(
    file: UploadFile = File(...),
):
    """Extract blood pressure values from an uploaded image (OCR only)"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        ocr_result = read_blood_pressure_with_gemini(temp_file_path)
        os.unlink(temp_file_path)

        if ocr_result.error:
            raise HTTPException(
                status_code=400, detail=f"OCR Error: {ocr_result.error}")

        if not all([ocr_result.systolic, ocr_result.diastolic, ocr_result.pulse]):
            raise HTTPException(
                status_code=400, detail="Could not extract all required blood pressure values")

        return {
            "systolic": ocr_result.systolic,
            "diastolic": ocr_result.diastolic,
            "pulse": ocr_result.pulse,
            "measurement_time": ocr_result.time,
            "image_metadata": ocr_result.image_metadata,
            "confidence": ocr_result.confidence
        }

    except Exception as e:
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        raise HTTPException(
            status_code=500, detail=f"Error processing image: {str(e)}")

'''
@app.post("/ocr/process-and-save", response_model=BloodPressureRecordResponse)
async def process_and_save_bp_record(
    file: UploadFile = File(...),
    auto_save: bool = True,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process blood pressure image with OCR and optionally save to database"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # ประมวลผลด้วย OCR
        ocr_result = read_blood_pressure_with_gemini(temp_file_path)

        # ลบไฟล์ชั่วคราว
        os.unlink(temp_file_path)

        # ตรวจสอบว่า OCR สำเร็จหรือไม่
        if ocr_result.error:
            raise HTTPException(
                status_code=400, detail=f"OCR Error: {ocr_result.error}")

        if not all([ocr_result.systolic, ocr_result.diastolic, ocr_result.pulse]):
            raise HTTPException(
                status_code=400, detail="Could not extract all required blood pressure values")

        # บันทึกข้อมูลลงฐานข้อมูลถ้า auto_save = True
        if auto_save:
            # ใช้เวลาปัจจุบันถ้าไม่มีเวลาจาก OCR
            measurement_date = datetime.utcnow()

            # ถ้ามี metadata ของวันที่จากภาพ ให้ใช้แทน
            if ocr_result.image_metadata:
                if "DateTimeOriginal" in ocr_result.image_metadata:
                    try:
                        measurement_date = datetime.strptime(
                            ocr_result.image_metadata["DateTimeOriginal"],
                            "%Y:%m:%d %H:%M:%S"
                        )
                    except:
                        pass
                elif "DateTime" in ocr_result.image_metadata:
                    try:
                        measurement_date = datetime.strptime(
                            ocr_result.image_metadata["DateTime"],
                            "%Y:%m:%d %H:%M:%S"
                        )
                    except:
                        pass

            db_record = BloodPressureRecord(
                user_id=current_user.id,
                systolic=ocr_result.systolic,
                diastolic=ocr_result.diastolic,
                pulse=ocr_result.pulse,
                measurement_date=measurement_date,
                measurement_time=ocr_result.time,
                notes=notes,
                ocr_confidence=ocr_result.confidence
            )

            db.add(db_record)
            db.commit()
            db.refresh(db_record)

            return db_record
        else:
            # ถ้าไม่ save ให้ return ข้อมูลที่อ่านได้เท่านั้น
            raise HTTPException(status_code=200, detail={
                "message": "OCR completed successfully but not saved",
                "ocr_result": ocr_result.dict()
            })

    except HTTPException:
        raise
    except Exception as e:
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass

        raise HTTPException(
            status_code=500, detail=f"Error processing image: {str(e)}")
'''


@app.get("/bp-records", response_model=List[BloodPressureRecordResponse])
async def get_bp_records(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get blood pressure records with optional date filtering"""
    query = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id)

    if start_date:
        query = query.filter(
            BloodPressureRecord.measurement_date >= start_date)
    if end_date:
        query = query.filter(BloodPressureRecord.measurement_date <= end_date)

    records = query.order_by(BloodPressureRecord.measurement_date.desc()).offset(
        skip).limit(limit).all()
    return records


@app.post("/bp-records/save-from-ocr", response_model=BloodPressureRecordResponse)
async def save_from_ocr(
    data: BloodPressureRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save blood pressure record from OCR result (edited or not)"""
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
    return db_record


@app.delete("/bp-records/{record_id}")
async def delete_bp_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete blood pressure record"""
    record = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.id == record_id,
        BloodPressureRecord.user_id == current_user.id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    db.delete(record)
    db.commit()

    return {"message": "Record deleted successfully"}
# Patient: View List of Authorized Doctors


@app.get("/patient/authorized-doctors", response_model=List[DoctorPatientResponse])
async def get_authorized_doctors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient views which doctors currently have access"""
    if current_user.role != "patient":
        raise HTTPException(
            status_code=403, detail="Only patients can view authorized doctors")

    relations = db.query(DoctorPatient).filter(
        DoctorPatient.patient_id == current_user.id,
        DoctorPatient.is_active == True
    ).all()

    return relations

# Patient: Revoke (Delete) Doctor Access


@app.delete("/patient/authorized-doctors/{doctor_id}")
async def revoke_doctor_access(
    doctor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient revokes a doctor's access"""
    if current_user.role != "patient":
        raise HTTPException(
            status_code=403, detail="Only patients can revoke access")

    relation = db.query(DoctorPatient).filter_by(
        doctor_id=doctor_id,
        patient_id=current_user.id,
        is_active=True
    ).first()

    if not relation:
        raise HTTPException(status_code=404, detail="Doctor not authorized")

    # Option 1: Mark inactive (soft delete)
    relation.is_active = False

    # Option 2: Hard delete (fully remove from DB)
    # db.delete(relation)

    db.commit()
    return {"message": "Access revoked"}


@app.post("/doctor/request-access")
async def request_patient_access(
    payload: AccessRequestInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    patient_email = payload.patient_email
    """Doctor requests access to patient data"""
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=403, detail="Only doctors can request access")

    # Find patient by email
    patient = db.query(User).filter(
        User.email == patient_email,
        User.role == "patient"
    ).first()

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
        raise HTTPException(status_code=400, detail="Request already sent")

    # Create new request
    request = AccessRequest(
        doctor_id=current_user.id,
        patient_id=patient.id
    )

    try:
        db.add(request)
        db.commit()
        return {"message": "Access request sent", "patient_name": patient.full_name}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to send request")


@app.get("/patient/access-requests")
async def view_access_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "patient":
        raise HTTPException(
            status_code=403, detail="Only patients can view access requests")

    requests = db.query(AccessRequest).filter_by(
        patient_id=current_user.id,
        status="pending"
    ).all()

    return requests


@app.post("/patient/access-requests/{request_id}/approve")
async def approve_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req = db.query(AccessRequest).filter_by(id=request_id).first()

    if not req or req.patient_id != current_user.id:
        raise HTTPException(status_code=404, detail="Request not found")

    req.status = "approved"

    # Automatically link doctor-patient relationship
    existing = db.query(DoctorPatient).filter_by(
        doctor_id=req.doctor_id,
        patient_id=req.patient_id
    ).first()

    if not existing:
        db.add(DoctorPatient(
            doctor_id=req.doctor_id,
            patient_id=req.patient_id,
            hospital="",
            is_active=True
        ))

    db.commit()
    return {"message": "Access approved"}


@app.post("/patient/authorize-doctor", response_model=DoctorPatientResponse)
async def authorize_doctor(
    doctor_id: int,  # Direct parameter instead of reusing schema
    hospital: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient adds doctor to allow access"""
    if current_user.role != "patient":
        raise HTTPException(
            status_code=403, detail="Only patients can authorize doctors")

    # Fix: Use doctor_id directly
    doctor = db.query(User).filter(
        User.id == doctor_id,
        User.role == "doctor"
    ).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Check if already linked
    existing = db.query(DoctorPatient).filter_by(
        doctor_id=doctor.id,
        patient_id=current_user.id,
        is_active=True
    ).first()

    if existing:
        raise HTTPException(
            status_code=400, detail="You already authorized this doctor")

    # Create new doctor-patient relation
    relation = DoctorPatient(
        doctor_id=doctor.id,
        patient_id=current_user.id,
        hospital=hospital
    )

    db.add(relation)
    db.commit()
    db.refresh(relation)
    return relation


@app.post("/patient/access-requests/{request_id}/reject")
async def reject_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Patient rejects a doctor's access request"""
    req = db.query(AccessRequest).filter_by(id=request_id).first()

    if not req or req.patient_id != current_user.id:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.status != "pending":
        raise HTTPException(
            status_code=400, detail="Request already processed")

    req.status = "rejected"
    db.commit()
    return {"message": "Access request rejected"}


@app.get("/doctor/patients", response_model=List[DoctorPatientResponse])
async def get_doctor_patients(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get doctor's patient list"""
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=403, detail="Only doctors can access patient lists")

    relations = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == current_user.id,
        DoctorPatient.is_active == True
    ).all()

    return relations


@app.get("/doctor/patients/{patient_id}/bp-records", response_model=List[BloodPressureRecordResponse])
async def get_patient_bp_records(
    patient_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get patient's blood pressure records (doctor only)"""
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

    records = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == patient_id
    ).order_by(BloodPressureRecord.measurement_date.desc()).offset(skip).limit(limit).all()

    return records

# Statistics Routes


@app.get("/stats/summary")
async def get_bp_summary(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get blood pressure summary statistics"""
    start_date = datetime.utcnow() - timedelta(days=days)

    records = db.query(BloodPressureRecord).filter(
        BloodPressureRecord.user_id == current_user.id,
        BloodPressureRecord.measurement_date >= start_date
    ).all()

    if not records:
        return {"message": "No records found for the specified period"}

    systolic_values = [r.systolic for r in records]
    diastolic_values = [r.diastolic for r in records]
    pulse_values = [r.pulse for r in records]

    return {
        "total_records": len(records),
        "period_days": days,
        "systolic": {
            "average": sum(systolic_values) / len(systolic_values),
            "min": min(systolic_values),
            "max": max(systolic_values)
        },
        "diastolic": {
            "average": sum(diastolic_values) / len(diastolic_values),
            "min": min(diastolic_values),
            "max": max(diastolic_values)
        },
        "pulse": {
            "average": sum(pulse_values) / len(pulse_values),
            "min": min(pulse_values),
            "max": max(pulse_values)
        }
    }

# Additional utility routes


@app.get("/health/check")
async def health_check():
    """Detailed health check endpoint"""
    try:
        # Test database connection
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Test Google AI API (optional - commented out to avoid unnecessary API calls)
    # ai_status = "not_tested"

    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "google_ai": "configured" if GOOGLE_AI_API_KEY != "AIxxxxxxxxxxxx" else "not_configured",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/config/info")
async def get_config_info():
    """Get API configuration information"""
    return {
        "api_name": "Blood Pressure Monitoring API",
        "version": "1.0.0",
        "features": [
            "User Registration & Authentication",
            "Blood Pressure Record Management",
            "Google Generative AI OCR",
            "Doctor-Patient Management",
            "Statistics & Analytics"
        ],
        "ai_model": "gemini-2.0-flash",
        "database": "SQLite" if "sqlite" in DATABASE_URL else "PostgreSQL"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
