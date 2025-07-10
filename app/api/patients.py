# app/api/v1/endpoints/patients.py

from fastapi import APIRouter, Depends, HTTPException
from app.services.patient_service import PatientService  # Clear, specific import
from app.models.patients_model import PatientCreate, PatientResponse
from app.db.client import get_db
from app.core.logger import logger

router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)


def get_patient_service(db=Depends(get_db)) -> PatientService:
    """Dependency to get patient service with database"""
    return PatientService(db)


@router.post("/create")
async def create_patient_bot(
        patient_data: PatientCreate,
        patient_service: PatientService = Depends(get_patient_service)  # Clear naming
):
    """Create a new patient record"""
    try:
        # Route only orchestrates - all logic in service
        logger.info(f"Patient Data is {patient_data}")
        result = patient_service.create_patient(patient_data)

        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=400 if result.get("existing_patient") else 500,
                detail=result["message"]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_patient route: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{patient_id}")
async def get_patient(
        patient_id: str,
        patient_service: PatientService = Depends(get_patient_service)
):
    """Get patient by ID"""
    try:
        logger.info(f"f Route Patient ID: {patient_id}")
        patient = patient_service.get_patient_by_id(patient_id)

        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        return {
            "success": True,
            "patient": patient
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching patient {patient_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch patient")


@router.put("/{patient_id}")
async def update_patient(
        patient_id: str,
        update_data: dict,
        patient_service: PatientService = Depends(get_patient_service)
):
    """Update patient information"""
    try:
        success = patient_service.update_patient(patient_id, update_data)

        if not success:
            raise HTTPException(status_code=404, detail="Patient not found")

        return {
            "success": True,
            "message": "Patient updated successfully",
            "patient_id": patient_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating patient {patient_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update patient")


@router.post("/search")
async def search_patients_safe(
        search_params: dict,
        patient_service: PatientService = Depends(get_patient_service)
):
    """Search for patients - safe version"""
    try:
        patient = patient_service.find_existing_patient(
            contact_number=search_params.get("contactNumber"),
            full_name=search_params.get("fullName"),
            patient_id=search_params.get("patientId")
        )

        if patient:
            return {
                "success": True,
                "found": True,
                "patient": {
                    "patient_id": patient["patient_id"],
                    "full_name": patient["full_name"],
                    "contact_number": patient["contact_number"],
                    "age": patient.get("age"),
                    "gender": patient["gender"],
                    "locality": patient.get("locality")
                },
                "message": "Patient found"
            }
        else:
            return {
                "success": True,
                "found": False,
                "patient": None,
                "message": "No patient found"
            }

    except Exception as e:
        logger.error(f"Error searching patients: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search patients")