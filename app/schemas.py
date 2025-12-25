
from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional, List, Literal, Dict, Any, Union
from datetime import datetime
import phonenumbers
from phonenumbers import NumberParseException

# Helper functions for validation
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
    
class DoctorAuthorizationInput(BaseModel):
    doctor_id: int
