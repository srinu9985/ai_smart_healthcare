# app/helpers/patient_helper.py

import re
from datetime import datetime, date, timezone
from typing import Dict, Any
from bson import ObjectId
from app.core.logger import logger


def generate_patient_id(db) -> str:

    today = datetime.now().strftime("%y%m%d")

    try:
        # Use MongoDB's atomic findOneAndUpdate to increment counter
        counter_doc = db.counters.find_one_and_update(
            {"_id": f"patient_counter_{today}"},  # Daily counter
            {"$inc": {"sequence": 1}},  # Atomic increment
            upsert=True,  # Create if doesn't exist
            return_document=True  # Return updated document
        )

        # Format sequence number with leading zeros
        next_number = str(counter_doc["sequence"]).zfill(3)
        patient_id = f"PAT-{today}-{next_number}"

        logger.info(f"Generated atomic patient ID: {patient_id}")
        return patient_id

    except Exception as e:
        logger.error(f"Error with atomic ID generation: {str(e)}")
        # Fallback to timestamp-based ID if atomic operation fails
        timestamp = datetime.now().strftime("%H%M%S")
        fallback_id = f"PAT-{today}-T{timestamp}"
        logger.warning(f"Using fallback timestamp-based ID: {fallback_id}")
        return fallback_id


def validate_patient_data(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate patient data before saving to database
    """
    errors = []

    try:
        # Validate required fields
        required_fields = [
            "fullName", "contactNumber", "dateOfBirth", "gender", "locality"
        ]

        for field in required_fields:
            if not patient_data.get(field) or str(patient_data[field]).strip() == "":
                errors.append(f"{field} is required")

        # Validate phone number
        if patient_data.get("contactNumber"):
            phone = re.sub(r'[^\d+]', '', patient_data["contactNumber"])
            if len(phone) < 10:
                errors.append("Contact number must be at least 10 digits")

        # Validate date of birth
        if patient_data.get("dateOfBirth"):
            try:
                dob = datetime.strptime(patient_data["dateOfBirth"], '%d-%m-%Y')

                # Check if DOB is not in the future
                if dob.date() > datetime.now().date():
                    errors.append("Date of birth cannot be in the future")

                # Check if person is not too old (reasonable age limit)
                today = datetime.now()
                calculated_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

                if calculated_age > 150:
                    errors.append("Age calculated from date of birth exceeds 150 years")
                elif calculated_age < 0:
                    errors.append("Invalid date of birth")

            except ValueError:
                errors.append("Invalid date of birth format. Use DD-MM-YYYY")

        # Validate gender
        valid_genders = ["Male", "Female", "Other"]
        if patient_data.get("gender") not in valid_genders:
            errors.append("Gender must be Male, Female, or Other")

        # Validate locality
        if patient_data.get("locality") and len(patient_data["locality"].strip()) < 5:
            errors.append("Locality isn't correct.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "message": "; ".join(errors) if errors else "Validation successful"
        }

    except Exception as e:
        logger.error(f"Error validating patient data: {str(e)}")
        return {
            "valid": False,
            "errors": [str(e)],
            "message": f"Validation error: {str(e)}"
        }


def format_patient_document(patient_data, patient_id: str) -> Dict[str, Any]:
    """
    Format patient data for database insertion
    """
    from app.utils.date_utils import calculate_age

    return {
        "_id": ObjectId(),
        "patient_id": patient_id,
        "full_name": patient_data.fullName,
        "contact_number": patient_data.contactNumber,
        "date_of_birth": patient_data.dateOfBirth,
        "age": calculate_age(patient_data.dateOfBirth),
        "gender": patient_data.gender,
        "locality": patient_data.locality,
        "registration_date": datetime.now(timezone.utc),
        "is_active": True,
        "created_by": "Bot",
        "medical_history": [],
        "appointments": [],
        "emergency_contacts": []
    }


def sanitize_phone_number(phone: str) -> str:
    """
    Clean and format phone number
    """
    if not phone:
        return ""

    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)

    # Add country code if missing (assuming India +91)
    if not cleaned.startswith('+') and len(cleaned) == 10:
        cleaned = f"+91{cleaned}"

    return cleaned


def validate_date_format(date_string: str, format_string: str = '%d-%m-%Y') -> bool:  #
    """
    Validate if a date string matches the expected format
    """
    try:
        datetime.strptime(date_string, format_string)
        return True
    except ValueError:
        return False


def clean_mongo_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean MongoDB document for JSON serialization
    Converts ObjectId to string and removes MongoDB-specific fields
    """
    if not doc:
        return doc

    cleaned = {}
    for key, value in doc.items():
        if key == "_id":
            cleaned[key] = str(value)  # Convert ObjectId to string
        elif isinstance(value, ObjectId):
            cleaned[key] = str(value)
        elif isinstance(value, datetime):
            cleaned[key] = value.isoformat()  # Convert datetime to ISO string
        else:
            cleaned[key] = value

    return cleaned