# app/api/appointments.py

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi import status as http_status
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, List
from datetime import datetime, timezone, date
from bson import ObjectId
import re
from app.db.client import get_db
from app.core.logger import logger
from app.models.healthcare_models import EditAppointmentRequest

router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"]
)


# Pydantic models for request/response
class AppointmentUpdateRequest(BaseModel):
    department: Optional[str] = Field(None, max_length=100, description="Department name")
    preferred_date: Optional[str] = Field(None, description="Preferred date in YYYY-MM-DD format")
    preferred_time: Optional[str] = Field(None, description="Preferred time (e.g., '10:00 AM')")
    appointment_type: Optional[Literal["Consultation", "Follow-up", "Emergency", "Routine Checkup"]] = None
    symptoms: Optional[str] = Field(None, max_length=500, description="Patient symptoms")
    doctor_id: Optional[str] = Field(None, description="Doctor ID")
    doctor_name: Optional[str] = Field(None, max_length=100, description="Doctor name")
    doctor_preference: Optional[str] = Field(None, description="Doctor preference")
    status: Optional[Literal["scheduled", "confirmed", "cancelled", "completed", "rescheduled"]] = None
    location: Optional[str] = Field(None, max_length=100, description="Appointment location")
    patient_name: Optional[str] = Field(None, max_length=100, description="Patient name")

    @field_validator('preferred_date')
    @classmethod
    def validate_date_format(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Date must be in YYYY-MM-DD format')
        return v

    @field_validator('preferred_time')
    @classmethod
    def validate_time_format(cls, v):
        if v is not None:
            time_pattern = r'^(0?[1-9]|1[0-2]):[0-5][0-9]\s?(AM|PM)$'
            if not re.match(time_pattern, v, re.IGNORECASE):
                raise ValueError('Time must be in format HH:MM AM/PM')
        return v


class AppointmentListResponse(BaseModel):
    appointment_id: str
    patient_id: str
    patient_name: str
    department: str
    preferred_date: str
    preferred_time: str
    appointment_type: str
    doctor_id: str
    doctor_name: str
    status: str
    location: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class PaginationMetadata(BaseModel):
    current_page: int
    total_pages: int
    total_items: int
    items_per_page: int
    has_next: bool
    has_previous: bool


class AppointmentListResponseData(BaseModel):
    appointments: List[AppointmentListResponse]
    pagination: PaginationMetadata
    filters_applied: dict


class AppointmentResponse(BaseModel):
    appointment_id: str
    patient_id: str
    patient_name: str
    department: str
    preferred_date: str
    preferred_time: str
    appointment_type: str
    symptoms: Optional[str]
    doctor_id: str
    doctor_name: str
    doctor_preference: Optional[str]
    status: str
    location: str
    booked_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


@router.get("/", response_model=AppointmentListResponseData)
def list_appointments(

        page: int = Query(1, ge=1, description="Page number starting from 1"),
        limit: int = Query(20, ge=1, le=100, description="Number of items per page (max 100)"),

        # Date filters
        from_date: Optional[date] = Query(None, description="Filter appointments from this date (YYYY-MM-DD)"),
        to_date: Optional[date] = Query(None, description="Filter appointments to this date (YYYY-MM-DD)"),
        appointment_date: Optional[date] = Query(None, description="Filter by specific appointment date"),

        # Status and type filters
        appointment_status: Optional[List[str]] = Query(None, description="Filter by status (can specify multiple)"),
        appointment_type: Optional[List[str]] = Query(None, description="Filter by appointment type"),
        department: Optional[List[str]] = Query(None, description="Filter by department"),

        # Search filters
        search: Optional[str] = Query(None, description="Search in patient name, appointment ID, or doctor name"),
        patient_id: Optional[str] = Query(None, description="Filter by specific patient ID"),
        doctor_id: Optional[str] = Query(None, description="Filter by specific doctor ID"),
        location: Optional[str] = Query(None, description="Filter by location"),

        # Sorting
        sort_by: Optional[Literal["created_at", "preferred_date", "updated_at", "patient_name", "doctor_name"]] = Query(
            "created_at", description="Sort by field"),
        sort_order: Optional[Literal["asc", "desc"]] = Query("desc", description="Sort order")
):
    """
    List appointments with comprehensive filtering, search, and pagination.
    """
    db = get_db()

    try:
        # Build MongoDB query
        query = {}

        # Date filters
        if from_date or to_date or appointment_date:
            date_filter = {}

            if appointment_date:
                # Filter by specific date
                date_str = appointment_date.strftime("%Y-%m-%d")
                query["preferred_date"] = date_str
            else:
                # Date range filter
                if from_date:
                    date_filter["$gte"] = from_date.strftime("%Y-%m-%d")
                if to_date:
                    date_filter["$lte"] = to_date.strftime("%Y-%m-%d")

                if date_filter:
                    query["preferred_date"] = date_filter

        # Status filter
        if appointment_status:
            query["status"] = {"$in": appointment_status}

        # Appointment type filter
        if appointment_type:
            query["appointment_type"] = {"$in": appointment_type}

        # Department filter
        if department:
            query["department"] = {"$in": department}

        # Location filter
        if location:
            query["location"] = {"$regex": re.escape(location), "$options": "i"}

        # Specific ID filters
        if patient_id:
            query["patient_id"] = patient_id

        if doctor_id:
            query["doctor_id"] = doctor_id

        # Search functionality
        if search:
            search_pattern = re.compile(re.escape(search), re.IGNORECASE)
            query["$or"] = [
                {"patient_name": {"$regex": search_pattern}},
                {"appointment_id": {"$regex": search_pattern}},
                {"doctor_name": {"$regex": search_pattern}},
                {"symptoms": {"$regex": search_pattern}}
            ]

        # Calculate pagination
        skip = (page - 1) * limit

        # Get total count for pagination metadata
        total_count = db.appointments.count_documents(query)

        # Determine sort direction
        sort_direction = 1 if sort_order == "asc" else -1

        # Execute query with pagination and sorting
        appointments_cursor = db.appointments.find(query).sort(sort_by, sort_direction).skip(skip).limit(limit)
        appointments = list(appointments_cursor)

        # Process appointments for response
        appointment_list = []
        for appointment in appointments:
            appointment_data = AppointmentListResponse(
                appointment_id=appointment["appointment_id"],
                patient_id=appointment["patient_id"],
                patient_name=appointment["patient_name"],
                department=appointment["department"],
                preferred_date=appointment["preferred_date"],
                preferred_time=appointment["preferred_time"],
                appointment_type=appointment["appointment_type"],
                doctor_id=appointment["doctor_id"],
                doctor_name=appointment["doctor_name"],
                status=appointment["status"],
                location=appointment["location"],
                created_at=appointment["created_at"],
                updated_at=appointment.get("updated_at")
            )
            appointment_list.append(appointment_data)

        # Calculate pagination metadata
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_previous = page > 1

        pagination = PaginationMetadata(
            current_page=page,
            total_pages=total_pages,
            total_items=total_count,
            items_per_page=limit,
            has_next=has_next,
            has_previous=has_previous
        )

        # Track applied filters for response
        filters_applied = {
            "date_range": {
                "from_date": from_date.isoformat() if from_date else None,
                "to_date": to_date.isoformat() if to_date else None,
                "appointment_date": appointment_date.isoformat() if appointment_date else None
            },
            "status": appointment_status,
            "appointment_type": appointment_type,
            "department": department,
            "search": search,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "location": location,
            "sorting": {
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }

        logger.info(
            f"Listed {len(appointment_list)} appointments for user  with {len([k for k, v in filters_applied.items() if v])} filters applied")

        return AppointmentListResponseData(
            appointments=appointment_list,
            pagination=pagination,
            filters_applied=filters_applied
        )

    except Exception as e:
        logger.error(f"Error listing appointments: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list appointments: {str(e)}"
        )


@router.get("/stats/summary")
def get_appointment_statistics(

        from_date: Optional[date] = Query(None, description="Statistics from this date"),
        to_date: Optional[date] = Query(None, description="Statistics to this date")
):
    """
    Get appointment statistics and summary data.
    """
    db = get_db()

    try:
        # Build date filter for statistics
        date_filter = {}
        if from_date or to_date:
            if from_date:
                date_filter["$gte"] = from_date.strftime("%Y-%m-%d")
            if to_date:
                date_filter["$lte"] = to_date.strftime("%Y-%m-%d")

        match_stage = {}
        if date_filter:
            match_stage["preferred_date"] = date_filter

        # Status distribution
        status_pipeline = [
            {"$match": match_stage},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        status_distribution = list(db.appointments.aggregate(status_pipeline))

        # Department distribution
        department_pipeline = [
            {"$match": match_stage},
            {"$group": {"_id": "$department", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        department_distribution = list(db.appointments.aggregate(department_pipeline))

        # Appointment type distribution
        type_pipeline = [
            {"$match": match_stage},
            {"$group": {"_id": "$appointment_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        type_distribution = list(db.appointments.aggregate(type_pipeline))

        # Location distribution
        location_pipeline = [
            {"$match": match_stage},
            {"$group": {"_id": "$location", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        location_distribution = list(db.appointments.aggregate(location_pipeline))

        # Total counts
        total_appointments = db.appointments.count_documents(match_stage)

        # Today's appointments
        today = date.today().strftime("%Y-%m-%d")
        today_match = {**match_stage, "preferred_date": today}
        today_appointments = db.appointments.count_documents(today_match)

        # This week's appointments
        from datetime import timedelta
        week_start = (date.today() - timedelta(days=date.today().weekday())).strftime("%Y-%m-%d")
        week_end = (date.today() + timedelta(days=6 - date.today().weekday())).strftime("%Y-%m-%d")

        week_match = {**match_stage, "preferred_date": {"$gte": week_start, "$lte": week_end}}
        week_appointments = db.appointments.count_documents(week_match)

        statistics = {
            "total_appointments": total_appointments,
            "today_appointments": today_appointments,
            "week_appointments": week_appointments,
            "status_distribution": status_distribution,
            "department_distribution": department_distribution,
            "appointment_type_distribution": type_distribution,
            "location_distribution": location_distribution,
            "date_range": {
                "from_date": from_date.isoformat() if from_date else None,
                "to_date": to_date.isoformat() if to_date else None
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        logger.info(f"Generated appointment statistics for user ")

        return {
            "success": True,
            "statistics": statistics
        }

    except Exception as e:
        logger.error(f"Error generating appointment statistics: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate statistics: {str(e)}"
        )


@router.put("/{appointment_id}")
def update_appointment(
        appointment_id: str,
        update_data: AppointmentUpdateRequest
):
    """
    Update an existing appointment.
    """
    db = get_db()

    try:
        # Find the appointment by appointment_id (not _id)
        existing_appointment = db.appointments.find_one({"appointment_id": appointment_id})

        if not existing_appointment:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with ID {appointment_id} not found"
            )

        # Prepare update data - only include fields that are not None
        update_fields = {}
        for field, value in update_data.dict(exclude_unset=True).items():
            if value is not None:
                update_fields[field] = value

        # Add updated_at timestamp
        update_fields["updated_at"] = datetime.now(timezone.utc)
        update_fields["updated_by"] = "EMMA"

        if not update_fields:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update"
            )

        # Validate doctor exists if doctor_id is being updated
        if "doctor_id" in update_fields:
            doctor = db.doctors.find_one({"doctor_id": update_fields["doctor_id"]})
            if not doctor:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Doctor with ID {update_fields['doctor_id']} not found"
                )
            # Auto-update doctor_name if doctor_id is changed
            update_fields["doctor_name"] = doctor.get("name", "Unknown Doctor")

        # Validate patient exists if patient_id is being updated
        if "patient_id" in update_fields:
            patient = db.patients.find_one({"patient_id": update_fields["patient_id"]})
            if not patient:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Patient with ID {update_fields['patient_id']} not found"
                )

        # Perform the update
        result = db.appointments.update_one(
            {"appointment_id": appointment_id},
            {"$set": update_fields}
        )

        if result.modified_count == 0:
            logger.warning(f"No changes made to appointment {appointment_id}")

        # Fetch and return updated appointment
        updated_appointment = db.appointments.find_one({"appointment_id": appointment_id})

        # Convert ObjectId to string for response
        updated_appointment["_id"] = str(updated_appointment["_id"])

        # Log the update activity
        logger.info(f"Appointment {appointment_id} updated by EMMA")

        # Log activity in appointment history
        activity_log = {
            "appointment_id": appointment_id,
            "action": "updated",
            "updated_fields": list(update_fields.keys()),
            "updated_by": "EMMA",
            "timestamp": datetime.now(timezone.utc)
        }
        db.appointment_history.insert_one(activity_log)

        return {
            "success": True,
            "message": "Appointment updated successfully",
            "appointment": updated_appointment,
            "modified_count": result.modified_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating appointment {appointment_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update appointment: {str(e)}"
        )


@router.patch("/{appointment_id}/status")
def update_appointment_status(
        appointment_id: str,
        status_update: Literal["scheduled", "confirmed", "cancelled", "completed", "rescheduled"],
        cancellation_reason: Optional[str] = None
):
    """
    Update only the appointment status.
    """
    db = get_db()

    try:
        # Validate cancellation reason if status is cancelled
        if status_update == "cancelled" and not cancellation_reason:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Cancellation reason is required when cancelling an appointment"
            )

        # Find the appointment
        existing_appointment = db.appointments.find_one({"appointment_id": appointment_id})

        if not existing_appointment:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with ID {appointment_id} not found"
            )

        # Prepare update data
        update_data = {
            "status": status_update,
            "updated_at": datetime.now(timezone.utc),
            "updated_by": "Emma"
        }

        if status_update == "cancelled" and cancellation_reason:
            update_data["cancellation_reason"] = cancellation_reason
            update_data["cancelled_at"] = datetime.now(timezone.utc)
        elif status_update == "completed":
            update_data["completed_at"] = datetime.now(timezone.utc)
        elif status_update == "confirmed":
            update_data["confirmed_at"] = datetime.now(timezone.utc)

        # Update the appointment
        result = db.appointments.update_one(
            {"appointment_id": appointment_id},
            {"$set": update_data}
        )

        # Log the status change
        activity_log = {
            "appointment_id": appointment_id,
            "action": "status_changed",
            "old_status": existing_appointment.get("status"),
            "new_status": status_update,
            "reason": cancellation_reason if status_update == "cancelled" else None,
            "updated_by": "Emma",
            "timestamp": datetime.now(timezone.utc)
        }
        db.appointment_history.insert_one(activity_log)

        logger.info(f"Appointment {appointment_id} status changed to {status_update} by Emma")

        return {
            "success": True,
            "message": f"Appointment status updated to {status_update}",
            "appointment_id": appointment_id,
            "new_status": status_update,
            "modified_count": result.modified_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating appointment status {appointment_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update appointment status: {str(e)}"
        )


@router.get("/{appointment_id}")
def get_appointment(
        appointment_id: str

):
    """
    Get appointment details by appointment ID.
    """
    db = get_db()

    try:
        appointment = db.appointments.find_one({"appointment_id": appointment_id})

        if not appointment:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with ID {appointment_id} not found"
            )

        # Convert ObjectId to string
        appointment["_id"] = str(appointment["_id"])

        return {
            "success": True,
            "appointment": appointment
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching appointment {appointment_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch appointment: {str(e)}"
        )


@router.get("/{appointment_id}/history")
def get_appointment_history(
        appointment_id: str
):
    """
    Get appointment update history.
    """
    db = get_db()

    try:
        # Verify appointment exists
        appointment = db.appointments.find_one({"appointment_id": appointment_id})
        if not appointment:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with ID {appointment_id} not found"
            )

        # Get history
        history = list(db.appointment_history.find(
            {"appointment_id": appointment_id},
            {"_id": 0}
        ).sort("timestamp", -1))

        return {
            "success": True,
            "appointment_id": appointment_id,
            "history": history
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching appointment history {appointment_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch appointment history: {str(e)}"
        )


@router.patch("/edit")
async def edit_appointment(
        appointment_data: EditAppointmentRequest,
        db=Depends(get_db)
):
    try:
        # Verify appointment exists
        appointment = db.appointments.find_one({"appointment_id": appointment_data.appointment_id})
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        # Create update document with only the fields that are provided
        update_fields = {}

        if hasattr(appointment_data, 'patient_name') and appointment_data.patient_name:
            update_fields['patient_name'] = appointment_data.patient_name

        if hasattr(appointment_data, 'doctor_name') and appointment_data.doctor_name:
            update_fields['doctor_name'] = appointment_data.doctor_name

        if hasattr(appointment_data, 'department') and appointment_data.department:
            update_fields['department'] = appointment_data.department

        if hasattr(appointment_data, 'preferred_Date') and appointment_data.preferred_Date:
            update_fields['preferred_date'] = appointment_data.preferred_Date

        if hasattr(appointment_data, 'preferred_Time') and appointment_data.preferred_Time:
            update_fields['preferred_time'] = appointment_data.preferred_Time

        if hasattr(appointment_data, 'status') and appointment_data.status:
            update_fields['status'] = appointment_data.status

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields provided for update")

        # Add updated_at timestamp
        update_fields['updated_at'] = datetime.now(timezone.utc)

        # Perform the update
        result = db.appointments.update_one(
            {"appointment_id": appointment_data.appointment_id},
            {"$set": update_fields}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes were made to the appointment")

        logger.info(f"Appointment {appointment_data.appointment_id} updated successfully")

        return {
            "success": True,
            "message": "Appointment updated successfully",
            "appointment_id": appointment_data.appointment_id,
            "modified_count": result.modified_count
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating appointment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update appointment: {str(e)}")