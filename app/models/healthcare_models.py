# app/models/healthcare_models.py

from pydantic import BaseModel, EmailStr, Field, validator, field_validator
from datetime import datetime, date
from typing import Optional, Literal, List
from bson import ObjectId

class PatientCreate(BaseModel):
    """Model for creating new patient records"""
    fullName: str = Field(..., min_length=2, max_length=100)
    contactNumber: str = Field(..., description="Primary contact number")
    emergencyNumber: Optional[str] = Field(None, description="Emergency contact number")
    dateOfBirth: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    gender: Literal["Male", "Female", "Other"] = Field(..., description="Patient gender")
    locality: str = Field(..., min_length=10, description="Patient's locality")

    @field_validator('contactNumber', 'emergencyNumber')
    def validate_phone_numbers(cls, v):
        if v and len(v.replace('+', '').replace('-', '').replace(' ', '')) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return v

    @field_validator('dateOfBirth')
    def validate_dob(cls, v):
        try:
            birth_date = datetime.strptime(v, '%d-%m-%Y').date()
            if birth_date > date.today():
                raise ValueError('Date of birth cannot be in the future')
            return v
        except ValueError as e:
            if 'does not match format' in str(e):
                raise ValueError('Date of birth must be in DD-MM-YYYY format')
            raise e

    @property
    def age(self) -> int:
        """Calculate age from date of birth"""
        birth_date = datetime.strptime(self.dateOfBirth, '%d-%m-%Y').date()
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age


class PatientResponse(BaseModel):
    """Response model for patient data"""
    patient_id: str
    fullName: str
    contactNumber: str
    age: int
    gender: str
    registeredLocation: str
    registrationDate: datetime
    isActive: bool = True


class AppointmentRequest(BaseModel):
    """Model for appointment booking using Pydantic V2"""
    patient_id: str
    patient_name: str
    department: str
    uvx_id: str
    preferredDate: str = Field(..., description="Preferred date in YYYY-MM-DD format")
    preferredTime: str = Field(..., description="Preferred time in HH:MM format")
    appointmentType: Literal["Consultation", "Follow-up", "Emergency", "Checkup"]
    symptoms: Optional[str] = Field(None, description="Patient symptoms or reason for visit")
    doctorPreference: Optional[str] = Field(None, description="Preferred doctor name")
    doctorId: str = Field(..., description="ID of the preferred doctor")
    doctorName: str = Field(..., description="Name of the preferred doctor")
    Location: str = Field(..., description="Hospital location for the appointment")
    bookingSource: Literal["online", "app", "website", "phone", "walk-in"] = Field(...,
                                                                                 description="Source of the appointment booking")

    @field_validator('preferredDate')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError as e:
            raise ValueError("Incorrect date format, should be YYYY-MM-DD") from e

    @field_validator('preferredTime')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, '%H:%M')
            return v
        except ValueError as e:
            raise ValueError("Incorrect time format, should be HH:MM") from e

class EditAppointmentRequest(BaseModel):
    """Model for appointment editing"""
    appointment_id: str
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    department: Optional[str] = None
    preferred_Date: str = Field(..., description="Preferred date in YYYY-MM-DD format")
    preferred_Time: Optional[str] = None
    status: Optional[Literal["scheduled"]] = None


class CallIntent(BaseModel):
    """Model for call intent detection"""
    intent: Literal[
        "appointment_booking",
        "appointment_query",
        "general_inquiry",
        "emergency",
        "prescription_refill",
        "test_results",
        "other"
    ]
    confidence: float = Field(..., ge=0.0, le=1.0)
    context: Optional[str] = Field(None, description="Additional context about the intent")


class HealthcareCallLog(BaseModel):
    """Model for healthcare call logging"""
    call_id: str
    patient_id: Optional[str] = None
    phone_number: str
    call_intent: Optional[str] = None
    call_status: str
    call_duration: Optional[int] = None
    patient_created: bool = False
    appointment_created: bool = False
    call_summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PatientSearchRequest(BaseModel):
    """Model for searching existing patients"""
    contactNumber: Optional[str] = None


class PatientSearchResponse(BaseModel):
    """Response model for patient search"""
    found: bool
    patient: Optional[PatientResponse] = None
    message: str


