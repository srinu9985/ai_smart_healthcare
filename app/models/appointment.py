# from pydantic import BaseModel
# from typing import Optional
# from datetime import date, time

# class AppointmentCreate(BaseModel):
#     patient_id: str
#     doctor_id: str
#     date: date
#     time: str
#     mode: str
#     symptoms: Optional[str]
#     intent: str  # new_appointment / reschedule / cancel


from pydantic import BaseModel
from datetime import date, time
from typing import Literal

class AppointmentDetails(BaseModel):
    date: date
    time: time
    mode: Literal["audio", "in_person"]
    doctor_id: str
    specialty: str
    location: str

class AppointmentCreate(BaseModel):
    patient_id: str
    intent: Literal["new_appointment", "follow_up"]
    symptoms: str
    urgency: Literal["low", "medium", "high"]
    appointment: AppointmentDetails
    status: Literal["pending", "confirmed", "cancelled"]