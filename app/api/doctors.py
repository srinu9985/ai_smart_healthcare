# from fastapi import APIRouter
# from app.models.doctor import DoctorCreate
# from app.crud import doctor_crud
# from dotenv import load_dotenv

# load_dotenv()

# router = APIRouter()

# @router.post("/doctors/")
# def add_doctor(doctor: DoctorCreate):
#     return {"id": doctor_crud.create_doctor(doctor.dict())}

# @router.get("/doctors/")
# def get_doctors(specialty: str):
#     return doctor_crud.get_doctors_by_specialty(specialty)


from fastapi import APIRouter
from typing import List
from app.models.doctor import DoctorCreate, DoctorOut
from app.crud import doctor_crud
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

@router.post("/doctors/")
def add_doctor(doctor: DoctorCreate):
    doctor_id = doctor_crud.create_doctor(doctor.dict())
    return {"id": doctor_id}

@router.get("/doctors/", response_model=List[DoctorOut])
def get_doctors(specialty: str):
    return doctor_crud.get_doctors_by_specialty(specialty)
