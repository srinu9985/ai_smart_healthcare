# app/api/healthcare.py

from fastapi import APIRouter, Depends, HTTPException, Request, Query, BackgroundTasks
from app.core.security import get_current_user
from app.db.client import get_db
from app.models.healthcare_models import (
    PatientCreate, PatientResponse, AppointmentRequest,
    CallIntent, HealthcareCallLog, PatientSearchRequest,
    PatientSearchResponse, EditAppointmentRequest
)
from app.services.healthcare_service import HealthcareService
from app.utils.healthcare_helpers import (
    detect_call_intent,
    validate_patient_data,
    generate_patient_id
)
from fastapi.responses import JSONResponse
from app.core.logger import logger
# from app.utils.appointment_bookibg_helpers import generate_doctor_slots
from datetime import datetime, timezone,timedelta
from bson import ObjectId
from typing import List, Optional
import re
import httpx

router = APIRouter(
    prefix="/healthcare",
    tags=["Healthcare"]
)

# Initialize healthcare service
healthcare_service = HealthcareService()



@router.get("/patients/{patient_id}")
async def get_patient_details(
        patient_id: str,
        db=Depends(get_db)
):
    """
    Get detailed patient information
    """
    try:
        patient = db.patients.find_one({"patient_id": patient_id})

        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Remove sensitive fields for response
        patient_data = {
            "patient_id": patient["patient_id"],
            "full_name": patient["full_name"],
            "contact_number": patient["contact_number"],
            "emergency_number": patient.get("emergency_number"),
          #  "preferred_language": patient["preferred_language"],
            "age": patient["age"],
            "gender": patient["gender"],
            "registered_location": patient["registered_location"],
            "registration_date": patient["registration_date"],
            "is_active": patient.get("is_active", True),
            "appointment_count": len(patient.get("appointments", [])),
            "last_visit": patient.get("last_visit_date")
        }

        return {"success": True, "patient": patient_data}

    except Exception as e:
        logger.error(f"Error getting patient details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get patient details: {str(e)}")


@router.post("/appointments/create")
async def create_appointment(
        appointment_data: AppointmentRequest,
        db=Depends(get_db)
):
    """
    Create a new appointment for existing patient
    """
    try:
        print("123333",db)
        # Verify patient exists
        patient = db.patients.find_one({"patient_id": appointment_data.patient_id})
        print("patient",patient)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        appointment_id=f"APT{datetime.now().strftime('%Y%M%S')}"
        # Create appointment document
        appointment_document = {
            "_id": ObjectId(),
            "appointment_id":appointment_id,
            "patient_id": appointment_data.patient_id,
            "patient_name":appointment_data.patient_name,
            "department": appointment_data.department,
            "preferred_date": appointment_data.preferredDate,
            "preferred_time": appointment_data.preferredTime,
            "appointment_type": appointment_data.appointmentType,
            "symptoms": appointment_data.symptoms,
            "doctor_id": appointment_data.doctorId,
            "doctor_name": appointment_data.doctorName,
            "doctor_preference": appointment_data.doctorPreference,
            "status": "scheduled",
            "location": appointment_data.Location,
            "Booked_by": appointment_data.bookingSource,
            "created_at": datetime.now(timezone.utc),
            "uvx_id": appointment_data.uvx_id,
        }
        print(appointment_document)
        result = db.appointments.insert_one(appointment_document)

        doctor_data=db.Doctors_data.find_one({"doctor_id":appointment_data.doctorId})
        print("doctorrrrr",doctor_data)
        doctor_email=doctor_data.get("doctor_email")
        print("doctoremaillll",doctor_email)
        # Update patient's appointment list
        db.patients.update_one(
            {"patient_id": appointment_data.patient_id},
            {"$push": {"appointments": str(result.inserted_id)}}
        )

        logger.info(f"Appointment created for patient {appointment_data.patient_id}")
       
        return {
            "success": True,
            "message": "Appointment scheduled successfully",
            "appointment_id": appointment_document["appointment_id"],
            "database_id": str(result.inserted_id)
        }

    except Exception as e:
        logger.error(f"Error creating appointment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create appointment: {str(e)}")


@router.post("/appointments/reschedule")
async def reschedule_appointments(req:Request):
    data=await req.json()
    db=get_db()
    appointment_id = data.get("appointment_id")
    preferred_date = data.get("preferred_date")
    preferred_time = data.get("preferred_time")

    appointment = db.appointments.find_one({"appointment_id": appointment_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment is not created for the given appointment id")

    
    if not all([appointment_id, preferred_date, preferred_time]):
        raise HTTPException(status_code=400, detail="appointment_id, preferred_date, and preferred_time are required")

    result = db.appointments.update_one(
        {"appointment_id": appointment_id},
        {
            "$set": {
                "preferred_date": preferred_date,
                "preferred_time": preferred_time,
                "status": "rescheduled"
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    
    return {"message": "Appointment rescheduled successfully"}

@router.post("/appointments/delete")
async def cancel_appointments(req: Request):
    data = await req.json()
    db = get_db()

    appointment_id = data.get("appointment_id")

    appointment = db.appointments.find_one({"appointment_id": appointment_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment is not created for the given appointment id")

    if not appointment_id:
        raise HTTPException(status_code=400, detail="appointment_id is required")

    result =db.appointments.delete_one({"appointment_id": appointment_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {"message": "Appointment cancelled successfully"}


@router.post("/calls/detect-intent")
async def detect_intent(
        request: Request,
        background_tasks: BackgroundTasks
):
    """
    Detect the intent of incoming healthcare calls
    This endpoint will be called by Ultravox at the start of calls
    """
    try:
        data = await request.json()
        call_id = data.get("call_id")
        phone_number = data.get("phone_number")
        initial_message = data.get("message", "")

        if not call_id or not phone_number:
            raise HTTPException(status_code=400, detail="call_id and phone_number required")

        # Detect intent from initial message
        intent_result = detect_call_intent(initial_message)

        # Log the call
        call_log = HealthcareCallLog(
            call_id=call_id,
            phone_number=phone_number,
            call_intent=intent_result["intent"],
            call_status="in_progress"
        )

        # Store in background
        background_tasks.add_task(
            healthcare_service.log_healthcare_call,
            call_log.model_dump()
        )

        return {
            "success": True,
            "intent": intent_result["intent"],
            "confidence": intent_result["confidence"],
            "next_action": intent_result["next_action"],
            "message": intent_result["message"]
        }

    except Exception as e:
        logger.error(f"Error detecting intent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Intent detection failed: {str(e)}")

@router.get("/patients")
async def list_patients(
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        search: Optional[str] = Query(None),
        location: Optional[str] = Query(None),
        db=Depends(get_db)

):
    """
    List patients with pagination and search
    """
    try:
        query = {"is_active": True}

        if search:
            search_pattern = re.compile(re.escape(search), re.IGNORECASE)
            query["$or"] = [
                {"full_name": {"$regex": search_pattern}},
                {"contact_number": {"$regex": search_pattern}},
                {"patient_id": {"$regex": search_pattern}}
            ]

        if location:
            query["registered_location"] = location

        skip = (page - 1) * limit
        total_count = db.patients.count_documents(query)

        patients = list(
            db.patients.find(query)
            .sort("registration_date", -1)
            .skip(skip)
            .limit(limit)
        )

        patient_list = []
        for patient in patients:
            patient_list.append({
                "patient_id": patient["patient_id"],
                "full_name": patient["full_name"],
                "contact_number": patient["contact_number"],
                "age": patient["age"],
                "gender": patient["gender"],
                "registered_location": patient["registered_location"],
                "registration_date": patient["registration_date"]
            })

        return {
            "success": True,
            "patients": patient_list,
            "pagination": {
                "current_page": page,
                "total_pages": (total_count + limit - 1) // limit,
                "total_items": total_count,
                "items_per_page": limit
            }
        }

    except Exception as e:
        logger.error(f"Error listing patients: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list patients: {str(e)}")


@router.get("/analytics/dashboard")
async def healthcare_dashboard(
        date_from: Optional[str] = Query(None),
        date_to: Optional[str] = Query(None),
        db=Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
    """
    Get healthcare analytics dashboard data
    """
    try:
        # Calculate date range
        if date_from and date_to:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            end_date = datetime.strptime(date_to, '%Y-%m-%d')
        else:
            end_date = datetime.now()
            start_date = datetime.now().replace(day=1)  # First day of current month

        # Total patients
        total_patients = db.patients.count_documents({"is_active": True})

        # New patients in date range
        new_patients = db.patients.count_documents({
            "registration_date": {"$gte": start_date, "$lte": end_date}
        })

        # Total appointments
        total_appointments = db.appointments.count_documents({})

        # Appointments in date range
        new_appointments = db.appointments.count_documents({
            "created_at": {"$gte": start_date, "$lte": end_date}
        })

        # Call statistics
        call_stats = db.healthcare_call_logs.aggregate([
            {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {
                "_id": "$call_intent",
                "count": {"$sum": 1}
            }}
        ])

        intent_distribution = {stat["_id"]: stat["count"] for stat in call_stats}

        return {
            "success": True,
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "metrics": {
                "total_patients": total_patients,
                "new_patients": new_patients,
                "total_appointments": total_appointments,
                "new_appointments": new_appointments
            },
            "call_analytics": {
                "intent_distribution": intent_distribution
            }
        }

    except Exception as e:
        logger.error(f"Error generating dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")

#current_user: dict = Depends(get_current_user)
@router.post("/patients/{patient_id}/update")
async def update_patient(
        patient_id: str,
        update_data: dict,
        db=Depends(get_db)
):
    """
    Update patient information
    """
    try:
        # Remove sensitive fields that shouldn't be updated via API
        restricted_fields = ["_id", "patient_id", "registration_date", "created_by"]
        for field in restricted_fields:
            update_data.pop(field, None)

        update_data["updated_at"] = datetime.now(timezone.utc)
        update_data["updated_by"] = "Emma"

        result = db.patients.update_one(
            {"patient_id": patient_id},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Patient not found")

        return {
            "success": True,
            "message": "Patient updated successfully",
            "modified_count": result.modified_count
        }

    except Exception as e:
        logger.error(f"Error updating patient: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update patient: {str(e)}")
    