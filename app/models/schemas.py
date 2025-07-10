# app/models/schemas.py
from pydantic import BaseModel,EmailStr, Field
from datetime import datetime
from typing import Optional, Literal, List

class UserRegisterModel(BaseModel):
    email: EmailStr
    password: str
    emp_id: str
    hospital_name: str
    role: Literal["Doctor", "Staff", "Admin"]


class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetOTP(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

class PasswordResetToken(BaseModel):
    token: str
    new_password: str

class CallScheduleRequest(BaseModel):
    candidate_id: str
    job_id: str
    scheduled_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

# UPDATED: Added voice and temperature settings
class ProjectCreate(BaseModel):
    project_name: str
    recruiter_name: Optional[str]
    notes: Optional[str]
    template_id: Optional[str]
    voice_setting: Optional[str] = "Monika-English-Indian"  # Default voice
    temperature_setting: Optional[float] = 0.2  # Default temperature

# UPDATED: Added voice and temperature settings
class ProjectUpdate(BaseModel):
    project_name: Optional[str]
    recruiter_name: Optional[str]
    notes: Optional[str]
    template_id: Optional[str]
    voice_setting: Optional[str]
    temperature_setting: Optional[float]

class ProjectSummary(BaseModel):
    project_id: str
    project_name: str
    status: str
    created_at: datetime

class ProjectListResponse(BaseModel):
    projects: List[ProjectSummary]

class JobSummary(BaseModel):
    job_id: str
    job_title: str

##----------------------------------------
# Template Schema
#----------------------------------------

class TemplateCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    template: str

class TemplateUpdateRequest(BaseModel):
    name: Optional[str]
    description: Optional[str]
    template: Optional[str]

class TemplateSummary(BaseModel):
    template_id: str
    name: str
    description: Optional[str]

class TemplateFull(TemplateSummary):
    template: str

class TemplatePreviewRequest(BaseModel):
    template: str

# UPDATED: Added voice and temperature settings
class ProjectDetailResponse(BaseModel):
    project_id: str
    project_name: str
    recruiter_email: Optional[EmailStr]
    recruiter_name: Optional[str]
    notes: Optional[str]
    status: str
    created_at: datetime
    job: Optional[JobSummary]
    template: Optional[TemplateFull]
    voice_setting: Optional[str] = "Monika-English-Indian"
    temperature_setting: Optional[float] = 0.2

# NEW: Voice settings schema for dedicated endpoint
class ProjectVoiceSettings(BaseModel):
    voice_setting: str = Field(..., description="Voice to use for Ultravox calls")
    temperature_setting: float = Field(..., ge=0.0, le=2.0, description="Temperature setting for Ultravox calls (0.0-2.0)")

class JobDescription(BaseModel):
    job_title: str
    job_description: str
    roles_and_responsibilities: Optional[str] = None
    experience_required: str
    skills_required: str
    qualification_required: Optional[str] = None
    certifications: Optional[str] = None
    job_location: str
    job_shift: Optional[str] = None
    work_mode: Optional[str] = None
    company_name: str
    company_description: Optional[str] = None
    company_website: Optional[str] = None
    interview_process: Optional[str] = None
    why_join_us: Optional[str] = None

class Candidate(BaseModel):
    name: str
    email: str
    phone_number: str
    qualification: Optional[str] = None
    experience: Optional[str] = None
    job_id: str
    project_id: str

class ScriptUpdateRequest(BaseModel):
    script: str
    tag: Optional[str] = None
    comment: Optional[str] = None

class UserProfileResponse(BaseModel):
    full_name: str
    email: EmailStr
    company_name: str
    designation: str
    role: str
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str]
    designation: Optional[str]
    password: Optional[str]
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class TeamMemberResponse(BaseModel):
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

class AdminUserUpdateRequest(BaseModel):
    full_name: Optional[str]
    designation: Optional[str]
    role: Optional[str]
    password: Optional[str]

class DailyCallSummary(BaseModel):
    date: str
    total_calls: int
    received: int
    not_received: int

class CallDurationSummary(BaseModel):
    date: str
    total_duration: int  # in seconds
    average_duration: float

class CallOutcomeDistribution(BaseModel):
    outcome: str
    count: int

#----------------
class Placeholder(BaseModel):
    key: str
    description: str

class PlaceholderResponse(BaseModel):
    id: str
    key: str
    description: str

class TranscriptPayload(BaseModel):
    callId: str
    text: str
    role: str
    medium: str
    final: bool = True
    ordinal: int

class CallbackRequest(BaseModel):
    call_id: str
    callback_time: datetime
    reason: str = "Candidate requested callback"

#srinivas added classes
class CallResponse(BaseModel):
    url: str | None = None
    error: str | None = None
    status_code: int | None = None
    details: str | None = None

#classes added by rohan
class UserInviteRequest(BaseModel):
    email: EmailStr
    role: Literal["Admin", "Recruiter", "Viewer"]
    company_name: str

class UserCompleteRegistration(BaseModel):
    token: str  # From invitation link
    full_name: str
    designation: str
    password: str