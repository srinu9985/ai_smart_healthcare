# app/services/patient_service.py

from typing import Optional, Dict, Any, Union
from bson import ObjectId
from datetime import datetime, timezone
import re

from app.core.logger import logger
from app.helpers.patient_helper import (
    validate_patient_data,
    generate_patient_id,
    format_patient_document,
    sanitize_phone_number
)


class PatientService:
    """
    Service class for patient-related operations
    """

    def __init__(self, db):
        """
        Initialize with database dependency

        Args:
            db: Database connection/client
        """
        if db is None:
            raise ValueError("Database connection is required")
        self.db = db

    def create_patient(self, patient_data) -> Dict[str, Any]:
        """
        Complete patient creation business logic with enhanced duplicate detection

        Args:
            patient_data: PatientCreate model instance

        Returns:
            Dictionary with operation result
        """
        try:
            # Input validation
            if not patient_data:
                return self._error_response("Patient data is required")

            # 1. Validate data
            validation_result = validate_patient_data(patient_data.model_dump())
            if not validation_result["valid"]:
                return self._error_response(f"Validation error: {validation_result['message']}")

            # 2. Enhanced duplicate check: Name + DOB + Phone
            existing_patient = self.find_existing_patient(
                contact_number=patient_data.contactNumber,
                full_name=patient_data.fullName,
            )

            if existing_patient:
                # Check if it's truly the same person or just family member with same phone
                same_name = existing_patient["full_name"].lower() == patient_data.fullName.lower()
                same_dob = existing_patient["date_of_birth"] == patient_data.dateOfBirth

                if same_name and same_dob:
                    # Genuine duplicate - same person
                    logger.info(f"Found genuine duplicate patient: {existing_patient['patient_id']}")
                    return {
                        "success": False,
                        "message": "Patient already exists in our system",
                        "patient_id": existing_patient["patient_id"],
                        "existing_patient": True,
                        "duplicate_type": "exact_match"
                    }
                else:
                    # Family member with same phone - allow registration but log
                    logger.info(
                        f"Family member registration detected - allowing creation. Existing: {existing_patient['full_name']}, New: {patient_data.fullName}")

            # 3. Create new patient
            patient_id = generate_patient_id(self.db)
            patient_document = format_patient_document(patient_data, patient_id)

            # Add audit fields
            patient_document.update({
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_active": True
            })

            result = self.db.patients.insert_one(patient_document)

            logger.info(f"New patient created: {patient_id}")

            return {
                "success": True,
                "message": "Patient created successfully",
                "patient_id": patient_id,
                "database_id": str(result.inserted_id),
                "existing_patient": False
            }

        except Exception as e:
            logger.error(f"Error creating patient: {str(e)}")
            return self._error_response("Failed to create patient")

    def find_existing_patient(
            self,
            contact_number: Optional[str] = None,
            full_name: Optional[str] = None,
            patient_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Simple and effective patient search
        Primary: Phone + Name combination (best for healthcare)
        Fallback: Individual criteria
        """
        try:
            query_conditions = []

            # 1. Search by patient ID (exact match) - Highest priority
            if patient_id and patient_id.strip():
                query_conditions.append({"patient_id": patient_id.strip()})

            # 2. Search by Phone + Name (perfect duplicate detection) - Primary method
            elif contact_number and full_name:
                clean_contact = sanitize_phone_number(contact_number)
                clean_name = full_name.strip().lower()

                if len(clean_contact) >= 10:
                    last_10_digits = clean_contact[-10:]

                    # Exact match: Same phone + Same name = Same person
                    exact_match_query = {
                        "$and": [
                            {"contact_number": {"$regex": f".*{re.escape(last_10_digits)}$"}},
                            {"full_name": {"$regex": f"^{re.escape(clean_name)}$", "$options": "i"}}
                        ]
                    }
                    query_conditions.append(exact_match_query)

            # 3. Fallback searches (for flexibility)
            elif contact_number and contact_number.strip():
                # Phone only search
                clean_contact = sanitize_phone_number(contact_number)
                if len(clean_contact) >= 10:
                    last_10_digits = clean_contact[-10:]
                    query_conditions.append({
                        "contact_number": {"$regex": f".*{re.escape(last_10_digits)}$"}
                    })

            elif full_name and full_name.strip():
                # Name only search
                clean_name = full_name.strip().lower()
                query_conditions.append({
                    "full_name": {"$regex": f"^{re.escape(clean_name)}$", "$options": "i"}
                })

            if not query_conditions:
                logger.warning("No valid search criteria provided for patient search")
                return None

            # Build final query
            query = {"$or": query_conditions} if len(query_conditions) > 1 else query_conditions[0]
            query["is_active"] = True

            patient = self.db.patients.find_one(query)

            if patient:
                logger.info(f"Found existing patient: {patient.get('patient_id', 'Unknown ID')}")

            return patient

        except Exception as e:
            logger.error(f"Error searching for existing patient: {str(e)}")
            return None

    def get_patient_by_id(self, patient_id: str) -> Optional[Dict]:
        """
        Get patient by ID

        Args:
            patient_id: Patient's unique ID

        Returns:
            Patient document if found, None otherwise
        """
        try:
            if not patient_id or not patient_id.strip():
                logger.info(f"Patient ID is: {patient_id}")
                logger.warning("Empty patient ID provided")
                return None

            patient = self.db.patients.find_one({
                "patient_id": patient_id.strip(),
                "is_active": True
            })

            return patient

        except Exception as e:
            logger.error(f"Error fetching patient {patient_id}: {str(e)}")
            return None

    def update_patient(self, patient_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update existing patient record

        Args:
            patient_id: Patient's unique ID
            update_data: Fields to update

        Returns:
            Dictionary with operation result
        """
        try:
            if not patient_id or not patient_id.strip():
                return self._error_response("Patient ID is required")

            if not update_data:
                return self._error_response("Update data is required")

            # Remove None values and add audit field
            clean_update_data = {k: v for k, v in update_data.items() if v is not None}
            clean_update_data["updated_at"] = datetime.now(timezone.utc)

            result = self.db.patients.update_one(
                {"patient_id": patient_id.strip(), "is_active": True},
                {"$set": clean_update_data}
            )

            if result.modified_count > 0:
                logger.info(f"Patient updated successfully: {patient_id}")
                return {
                    "success": True,
                    "message": "Patient updated successfully",
                    "patient_id": patient_id,
                    "modified_count": result.modified_count
                }
            else:
                logger.warning(f"No patient found to update with ID: {patient_id}")
                return self._error_response("Patient not found or no changes made")

        except Exception as e:
            logger.error(f"Error updating patient {patient_id}: {str(e)}")
            return self._error_response("Failed to update patient")

    def deactivate_patient(self, patient_id: str) -> Dict[str, Any]:
        """
        Soft delete patient (mark as inactive)

        Args:
            patient_id: Patient's unique ID

        Returns:
            Dictionary with operation result
        """
        try:
            if not patient_id or not patient_id.strip():
                return self._error_response("Patient ID is required")

            result = self.db.patients.update_one(
                {"patient_id": patient_id.strip()},
                {
                    "$set": {
                        "is_active": False,
                        "deactivated_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            if result.modified_count > 0:
                logger.info(f"Patient deactivated: {patient_id}")
                return {
                    "success": True,
                    "message": "Patient deactivated successfully",
                    "patient_id": patient_id
                }
            else:
                logger.warning(f"No patient found to deactivate with ID: {patient_id}")
                return self._error_response("Patient not found")

        except Exception as e:
            logger.error(f"Error deactivating patient {patient_id}: {str(e)}")
            return self._error_response("Failed to deactivate patient")

    def get_all_patients(self, limit: int = 100, skip: int = 0) -> Dict[str, Any]:
        """
        Get all active patients with pagination

        Args:
            limit: Maximum number of patients to return
            skip: Number of patients to skip

        Returns:
            Dictionary with patients list and metadata
        """
        try:
            # Validate pagination parameters
            limit = max(1, min(limit, 1000))  # Between 1 and 1000
            skip = max(0, skip)

            patients = list(self.db.patients.find(
                {"is_active": True}
            ).skip(skip).limit(limit))

            total_count = self.db.patients.count_documents({"is_active": True})

            return {
                "success": True,
                "patients": patients,
                "total_count": total_count,
                "returned_count": len(patients),
                "skip": skip,
                "limit": limit
            }

        except Exception as e:
            logger.error(f"Error fetching patients: {str(e)}")
            return self._error_response("Failed to fetch patients")

    def _error_response(self, message: str) -> Dict[str, Any]:
        """
        Helper method to create consistent error responses

        Args:
            message: Error message

        Returns:
            Standardized error response
        """
        return {
            "success": False,
            "message": message,
            "error": True
        }