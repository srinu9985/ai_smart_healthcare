# app/services/healthcare_service.py

from app.db.client import get_db
from app.core.logger import logger
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from bson import ObjectId
import random
import re


class HealthcareService:
    """
    Service class for healthcare-related operations
    """

    def __init__(self):
        self.db = get_db()

    def search_existing_patient(
            self,
            contact_number: Optional[str] = None,
           # aadhaar_number: Optional[str] = None,
            full_name: Optional[str] = None,
            db=None
    ) -> Optional[Dict]:
        """
        Search for existing patient using multiple criteria
        """
        if db is None:
            db = self.db

        try:
            query_conditions = []

            if contact_number:
                # Clean contact number for search
                clean_contact = re.sub(r'[^\d+]', '', contact_number)
                query_conditions.append({"contact_number": {"$regex": clean_contact[-10:]}})


            if full_name:
                # Case-insensitive name search
                query_conditions.append({
                    "full_name": {"$regex": re.escape(full_name), "$options": "i"}
                })

            if not query_conditions:
                return None

            # Use OR condition to match any of the criteria
            query = {"$or": query_conditions}

            patient = db.patients.find_one(query)
            return patient

        except Exception as e:
            logger.error(f"Error searching for existing patient: {str(e)}")
            return None







