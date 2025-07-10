# Updated doctor models with Pydantic v2 syntax

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional


class DoctorCreate(BaseModel):
    name: str
    specialty: str
    gender: Optional[str] = None
    location: Optional[str] = None
    available_modes: List[str]


class DoctorOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="id")
    name: str
    specialty: str
    gender: Optional[str] = None
    location: Optional[str] = None
    available_modes: List[str]