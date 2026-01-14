
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship, validates
from datetime import datetime
from pytz import timezone
from .database import Base
from .utils.encryption import encrypt_value, decrypt_value, hash_value

THAI_TZ = timezone("Asia/Bangkok")

def now_th():
    return datetime.now(THAI_TZ)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    
    # Login & Identity (Hashed for lookup, Encrypted for display)
    email_encrypted = Column(String, nullable=True)
    email_hash = Column(String, unique=True, index=True, nullable=True)
    
    phone_number_encrypted = Column(String, nullable=True)
    phone_number_hash = Column(String, unique=True, index=True, nullable=True)
    
    password_hash = Column(String, nullable=False)
    role = Column(String, default="patient")  # patient, doctor, staff
    language = Column(String, default="th")    # th, en
    
    full_name_encrypted = Column(String, nullable=True)
    full_name_hash = Column(String, index=True, nullable=True) # Not unique
    
    telegram_id_encrypted = Column(String, nullable=True)
    telegram_id_hash = Column(String, unique=True, index=True, nullable=True)
    
    # Personal Info (Encrypted)
    citizen_id_encrypted = Column(String, nullable=True)
    citizen_id_hash = Column(String, unique=True, index=True, nullable=True)

    # ... [Rest of code] ...

    @property
    def telegram_id(self):
        val = decrypt_value(self.telegram_id_encrypted)
        if val:
            try:
                return int(val)
            except:
                return None
        return None

    @telegram_id.setter
    def telegram_id(self, value):
        if value is not None:
            self.telegram_id_encrypted = encrypt_value(str(value))
            self.telegram_id_hash = hash_value(str(value))
        else:
            self.telegram_id_encrypted = None
            self.telegram_id_hash = None
    
    date_of_birth_encrypted = Column(String, nullable=True) # DOB Encrypted as String
    
    gender = Column(String, nullable=True)  # male, female, other
    blood_type = Column(String, nullable=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    
    medical_license_encrypted = Column(String, nullable=True)
    medical_license_hash = Column(String, unique=True, index=True, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    verification_status = Column(String, default="pending") # pending, verified, rejected
    verification_logs = Column(Text, nullable=True)
    is_email_verified = Column(Boolean, default=False)
    is_phone_verified = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_th())
    updated_at = Column(DateTime, default=now_th(), onupdate=now_th())

    # Monetization (B2C)
    subscription_tier = Column(String, default="free") # free, premium
    subscription_expires_at = Column(DateTime, nullable=True)

    # Relations
    bp_records = relationship("BloodPressureRecord", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    doctor_patients = relationship(
        "DoctorPatient", foreign_keys="DoctorPatient.doctor_id", back_populates="doctor")
    patient_doctors = relationship(
        "DoctorPatient", foreign_keys="DoctorPatient.patient_id", back_populates="patient")
    # licenses = relationship("License", back_populates="main_user") # If we link license to user

    # --- Transparent Encryption Properties ---
    # These allow code to access `user.email` / `user.full_name` normally.
    # The setter automatically encrypts and hashes.
    # The getter automatically decrypts.

    @property
    def email(self):
        return decrypt_value(self.email_encrypted)

    @email.setter
    def email(self, value):
        self.email_encrypted = encrypt_value(value)
        self.email_hash = hash_value(value)

    @property
    def phone_number(self):
        return decrypt_value(self.phone_number_encrypted)

    @phone_number.setter
    def phone_number(self, value):
        self.phone_number_encrypted = encrypt_value(value)
        self.phone_number_hash = hash_value(value)

    @property
    def full_name(self):
        return decrypt_value(self.full_name_encrypted)
    
    @full_name.setter
    def full_name(self, value):
        self.full_name_encrypted = encrypt_value(value)
        self.full_name_hash = hash_value(value)

    @property
    def citizen_id(self):
        return decrypt_value(self.citizen_id_encrypted)

    @citizen_id.setter
    def citizen_id(self, value):
        self.citizen_id_encrypted = encrypt_value(value)
        self.citizen_id_hash = hash_value(value)
        
    @property
    def medical_license(self):
        return decrypt_value(self.medical_license_encrypted)

    @medical_license.setter
    def medical_license(self, value):
        self.medical_license_encrypted = encrypt_value(value)
        self.medical_license_hash = hash_value(value)

    @property
    def date_of_birth(self):
        val = decrypt_value(self.date_of_birth_encrypted)
        if val:
            try:
                # Store as ISO string, parse back to DateTime if possible? 
                # Or keep as string. Front-end expects string or Date.
                # SQLAlchemy expects DateTime for date_of_birth usually? 
                # Original was DateTime. If we encrypt, it MUST be string.
                # Let's return ISO string. Pydantic can parse it.
                return datetime.fromisoformat(val)
            except:
                return None
        return None

    @date_of_birth.setter
    def date_of_birth(self, value):
        if value:
            # If datetime, convert to iso string
            if isinstance(value, datetime):
                str_val = value.isoformat()
            else:
                str_val = str(value)
            self.date_of_birth_encrypted = encrypt_value(str_val)
        else:
            self.date_of_birth_encrypted = None

class License(Base):
    """B2B License for Organizations"""
    __tablename__ = "licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False) # UUID or License Key
    organization_name = Column(String, nullable=False)
    type = Column(String, default="clinic") # clinic, hospital, enterprise
    max_users = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_th())
    
    # Ideally link to a main user who manages it
    # main_user_id = Column(Integer, ForeignKey("users.id"), nullable=True) 

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
    measurement_date = Column(DateTime, default=now_th())
    measurement_time = Column(String, nullable=True)  # HH:MM
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


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    trans_ref = Column(String, index=True)
    trans_ref_hash = Column(String, unique=True, index=True)
    amount = Column(Float)
    plan_type = Column(String)
    plan_amount = Column(Float)
    sending_bank = Column(String, nullable=True)
    sender_name_encrypted = Column(String, nullable=True)
    receiver_name = Column(String, nullable=True)
    trans_date = Column(String, nullable=True)
    trans_time = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, verified, failed
    error_code = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    verification_response = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=now_th())
    verified_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="payments")
