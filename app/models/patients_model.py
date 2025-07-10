# app/models/patient_models.py

from pydantic import BaseModel, Field, field_validator
from datetime import datetime, date
from typing import Optional, Literal
from app.utils.date_utils import calculate_age


class PatientCreate(BaseModel):
    """Model for creating new patient records"""
    fullName: str = Field(..., min_length=2, max_length=100)
    contactNumber: str = Field(..., description="Primary contact number")
    dateOfBirth: str = Field(..., description="Date of birth in DD-MM-YYYY format")
    gender: Literal["Male", "Female", "Other"] = Field(..., description="Patient gender")
    locality: str = Field(..., description="Patient's locality")

    @field_validator('contactNumber')
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
        return calculate_age(self.dateOfBirth)


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


class PatientUpdate(BaseModel):
    """Model for updating patient records"""
    fullName: Optional[str] = Field(None, min_length=2, max_length=100)
    contactNumber: Optional[str] = Field(None, description="Primary contact number")
    emergencyNumber: Optional[str] = Field(None, description="Emergency contact number")
    locality: Optional[str] = Field(None, min_length=10, description="Patient's locality")

    @field_validator('contactNumber')
    def validate_contact_number(cls, v):
        if v and len(v.replace('+', '').replace('-', '').replace(' ', '')) < 10:
            raise ValueError('Contact number must be at least 10 digits')
        return v

    @field_validator('emergencyNumber')
    def validate_emergency_number(cls, v):
        if v and len(v.replace('+', '').replace('-', '').replace(' ', '')) < 10:
            raise ValueError('Emergency number must be at least 10 digits')
        return v


class PatientSearchRequest(BaseModel):
    """Model for searching existing patients"""
    contactNumber: Optional[str] = None
    patient_id: Optional[str] = None
    fullName: Optional[str] = None


class PatientSearchResponse(BaseModel):
    """Response model for patient search"""
    found: bool
    patient: Optional[PatientResponse] = None
    message: str