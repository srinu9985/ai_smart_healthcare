# app/utils/healthcare_ultravox_helper.py

import os
import requests
from app.core.logger import logger
from app.utils.healthcare_helpers import generate_healthcare_system_prompt
from dotenv import load_dotenv

load_dotenv()

ULTRAVOX_API_URL = os.getenv("ULTRAVOX_API_URL")
ULTRAVOX_API_KEY = os.getenv("ULTRAVOX_API_KEY")
NGROK_URL = os.getenv("NGROK_URL")
Interview_scheduling_url = os.getenv("Interview_scheduling_url")





def get_healthcare_ultravox_config() -> dict:
    """
    Build Ultravox configuration for healthcare calls with patient management tools
    """
    system_prompt =  generate_healthcare_system_prompt()

    return {
        "systemPrompt": system_prompt,
        "model": "fixie-ai/ultravox-gemma3-27b-preview", # fixie-ai/ultravox-qwen3-32b-preview,fixie-ai/ultravox-gemma3-27b-preview,fixie-ai/ultravox-70B
        "voice": "Saavi-English-Indian",
        "inactivityMessages": [
            {
                "duration": "10s",
                "message": "Are you still there?"
            },
            {
                "duration": "5s",
                "message": "If there's nothing else, may I end the call?"
            },
            {
                "duration": "1s",
                "message": "Thank you for calling. Have a great day. Goodbye.",
                "endBehavior": "END_BEHAVIOR_HANG_UP_SOFT"
            }
        ],
        # "externalVoice": {
            #     "elevenLabs": {
            #         "voiceId": "n6OsFJUGjxuP7WObn8kd",
            #         "model": "eleven_turbo_v2_5"
            #     }
            # },
        "experimentalSettings": {
            "backgroundNoiseFilter": True,
            "dynamicEndpointing": True

        },
        "temperature": 0.1,
        "firstSpeaker": "FIRST_SPEAKER_AGENT",
        "languageHint": "en-IN",
        "medium": {
            "exotel": {}
        },
        "vadSettings": {
            "turnEndpointDelay": "0.480s",  #0.384
            "minimumTurnDuration": "0s",#0s
            "minimumInterruptionDuration": "0.09s", #0.09s (90ms)
            "frameActivationThreshold": 0.1 # 0.1
        },
        "selectedTools": [
            {
                "temporaryTool": {
                    "modelToolName": "create_patient",
                    "description": "Create a new patient record with all required demographics. Only use this for NEW patients after collecting all required information.",
                    "automaticParameters": [],
                    "dynamicParameters": [
                        {
                            "name": "fullName",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Patient's full name as provided"
                            },
                            "required": True
                        },
                        {
                            "name": "contactNumber",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Patient's primary contact number"
                            },
                            "required": True
                        },
                        {
                            "name": "dateOfBirth",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Date of birth in Date-Month-Year format"
                            },
                            "required": True
                        },
                        {
                            "name": "gender",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Patient's gender"
                            },
                            "required": True
                        },

                        {
                            "name": "locality",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Patient's Locality"
                            },
                            "required": True
                        },

                    ],
                    "http": {
                        "baseUrlPattern": f"{NGROK_URL}/patients/create",
                        "httpMethod": "POST"
                    }
                }
            },
            {
                "temporaryTool": {
                    "modelToolName": "search_patient",
                    "description": "Search for existing patient by contact number to avoid duplicates.",
                    "automaticParameters": [],
                    "dynamicParameters": [
                        {
                            "name": "patientId",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Patient's ID to Search"
                            },
                            "required": False
                        },
                        {
                            "name": "contactNumber",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Patient's contact number to search"
                            },
                            "required": False
                        },
                        {
                            "name": "fullName",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Patient's full name to search"
                            },
                            "required": False
                        },

                    ],
                    "http": {
                        "baseUrlPattern": f"{NGROK_URL}/patients/search",
                        "httpMethod": "POST"
                    }
                }
            },
            {
                "temporaryTool": {
                    "modelToolName": "checkDoctorAvailability",
                    "description": "Check available time slots for doctor appointments based on the patient's preferred date and time range.",
                    "dynamicParameters": [
                        {
                            "name": "doctor_name",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Full name of the doctor selected by the patient or mentioned during the conversation."
                            },
                            "required": True
                        },
                        {
                            "name": "department",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Medical department/specialization (e.g., Cardiology, Ent, General)",
                                "enum": ["Cardiology", "ent", "Dermatologist", "General", "orthopedics", "pediatrics",
                                         "neurology"]
                            },
                            "required": True
                        },
                        {
                            "name": "start_date",
                            "location": "PARAMETER_LOCATION_QUERY",
                            "schema": {
                                "type": "string",
                                "description": "Preferred appointment date in YYYY-MM-DD format or use 'today' or 'tomorrow' or 'dayaftertomorrow' as keywords (do not convert these to dates)",
                                "example": "2025-06-17 or 'today' or 'tomorrow' or 'dayaftertomorrow'"
                            },
                            "required": True
                        },
                        {
                            "name": "start_time",
                            "location": "PARAMETER_LOCATION_QUERY",
                            "schema": {
                                "type": "string",
                                "description": "Preferred start time in HH:MM format (24-hour)",
                                "example": "12:00"
                            },
                            "required": False
                        },
                        {
                            "name": "end_time",
                            "location": "PARAMETER_LOCATION_QUERY",
                            "schema": {
                                "type": "string",
                                "description": "Preferred end time in HH:MM format (24-hour)",
                                "example": "18:00"
                            },
                            "required": False
                        }
                    ],
                    "http": {
                        "baseUrlPattern": f"{Interview_scheduling_url}/available-slots",
                        "httpMethod": "POST"
                    }
                }
            },
            {
                "temporaryTool": {
                    "modelToolName": "schedule_appointment",
                    "description": "Create a new appointment for an existing patient. Only use after patient is confirmed to exist.",
                    "automaticParameters": [
                        {
                            "name": "uvx_id",
                            "location": "PARAMETER_LOCATION_BODY",
                            "knownValue": "KNOWN_PARAM_CALL_ID"
                        }
                    ],
                    "dynamicParameters": [
                        {
                            "name": "patient_id",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "patient id of the appointment"
                            },
                            "required": True
                        },
                        {
                            "name": "patient_name",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "patient name for the appointment"
                            },
                            "required": True
                        },
                        {
                            "name": "department",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Medical department for the appointment"
                            },
                            "required": True
                        },
                        {
                            "name": "preferredDate",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Preferred date for appointment in YYYY-MM-DD format"
                            },
                            "required": True
                        },
                        {
                            "name": "preferredTime",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Preferred time for appointment in HH:MM format"
                            },
                            "required": True
                        },
                        {
                            "name": "appointmentType",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "enum": ["Consultation", "Follow-up", "Emergency", "Checkup"],
                                "description": "Type of appointment"
                            },
                            "required": True
                        },
                        {
                            "name": "bookingSource",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "enum": ["online", "app", "website", "phone", "walk-in"],
                                "description": "Source of the appointment booking"
                            },
                            "required": True
                        },
                        {
                            "name": "symptoms",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Patient symptoms or reason for visit"
                            },
                            "required": False
                        },
                        {
                            "name": "doctorPreference",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Preferred doctor name if any"
                            },
                            "required": False
                        },
                        {
                            "name": "doctorId",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "ID of the Assigned doctor which get from the checkdoctoravailability tool"
                            },
                            "required": True
                        },
                        {
                            "name": "doctorName",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Name of the Assigned doctor which get from the checkdoctoravailability tool"
                            },
                            "required": True
                        },
                        {
                            "name": "Location",
                            "location": "PARAMETER_LOCATION_BODY",
                            "schema": {
                                "type": "string",
                                "description": "Hospital location for the appointment"
                            },
                            "required": True
                        }
                    ],
                    "http": {
                        "baseUrlPattern": f"{NGROK_URL}/healthcare/appointments/create",
                        "httpMethod": "POST"
                    }
                }
            },



            {
                "toolName": "hangUp"
            }

        ]
   }

def create_healthcare_ultravox_call() -> dict:
    """
    Create Ultravox call specifically for healthcare use cases
    """
    try:
        payload = get_healthcare_ultravox_config()

        logger.info("Creating healthcare Ultravox call")

        response = requests.post(
            ULTRAVOX_API_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": ULTRAVOX_API_KEY
            },
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        logger.info("Healthcare Ultravox call created successfully")
        print(f"ultravox data is {data}")
        return data

    except requests.RequestException as e:
        logger.error(f"Error creating healthcare Ultravox call: {e}")
        return None


