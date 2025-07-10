# app/utils/healthcare_helpers.py
import re
import openai
import os
from datetime import datetime, timezone
from typing import Dict, Any, List
from app.core.logger import logger
from dotenv import load_dotenv
from app.db.client import Doctor

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def detect_call_intent(message: str) -> Dict[str, Any]:
    """
    Detect the intent of healthcare calls using OpenAI
    """
    try:
        # Keywords-based quick detection for common intents
        appointment_keywords = [
            "appointment", "book", "schedule", "doctor", "consultation",
            "visit", "checkup", "meet", "slot", "available"
        ]

        emergency_keywords = [
            "emergency", "urgent", "pain", "accident", "immediate",
            "help", "critical", "serious"
        ]

        query_keywords = [
            "status", "when", "time", "reschedule", "cancel",
            "change", "confirm"
        ]

        message_lower = message.lower()

        # Emergency detection (highest priority)
        if any(keyword in message_lower for keyword in emergency_keywords):
            return {
                "intent": "emergency",
                "confidence": 0.9,
                "next_action": "transfer_to_emergency",
                "message": "Emergency detected. Transferring to emergency services."
            }

        # Appointment booking detection
        if any(keyword in message_lower for keyword in appointment_keywords):
            return {
                "intent": "appointment_booking",
                "confidence": 0.8,
                "next_action": "collect_patient_info",
                "message": "Appointment booking intent detected. Will collect patient information."
            }

        # Appointment query detection
        if any(keyword in message_lower for keyword in query_keywords):
            return {
                "intent": "appointment_query",
                "confidence": 0.7,
                "next_action": "get_appointment_details",
                "message": "Appointment query detected. Will help with appointment information."
            }

        # Use OpenAI for complex intent detection
        return detect_intent_with_ai(message)

    except Exception as e:
        logger.error(f"Error in intent detection: {str(e)}")
        return {
            "intent": "general_inquiry",
            "confidence": 0.5,
            "next_action": "general_assistance",
            "message": "General inquiry detected. How can I help you today?"
        }


def detect_intent_with_ai(message: str) -> Dict[str, Any]:
    """
    Use OpenAI to detect complex intents
    """
    try:
        prompt = f"""
        Analyze the following healthcare call message and determine the intent:

        Message: "{message}"

        Return the response in this exact JSON format:
        {{
            "intent": "one of: appointment_booking, appointment_query, general_inquiry, emergency, prescription_refill, test_results, other",
            "confidence": 0.0-1.0,
            "next_action": "suggested next action",
            "message": "brief explanation"
        }}

        Intent definitions:
        - appointment_booking: Patient wants to schedule a new appointment
        - appointment_query: Patient asking about existing appointments
        - emergency: Medical emergency requiring immediate attention
        - prescription_refill: Patient needs prescription refill
        - test_results: Patient asking about lab/test results
        - general_inquiry: General questions about hospital services
        - other: Doesn't fit other categories
        """

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200
        )

        import json
        result = json.loads(response['choices'][0]['message']['content'])
        return result

    except Exception as e:
        logger.error(f"Error in AI intent detection: {str(e)}")
        return {
            "intent": "general_inquiry",
            "confidence": 0.5,
            "next_action": "general_assistance",
            "message": "How can I help you today?"
        }


def validate_patient_data(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate patient data before saving to database
    """
    errors = []

    try:
        # Validate required fields
        required_fields = [
            "fullName", "contactNumber",
             "gender", "locality"

        ]

        for field in required_fields:
            if not patient_data.get(field) or str(patient_data[field]).strip() == "":
                errors.append(f"{field} is required")

        # Validate phone number
        if patient_data.get("contactNumber"):
            phone = re.sub(r'[^\d+]', '', patient_data["contactNumber"])
            if len(phone) < 10:
                errors.append("Contact number must be at least 10 digits")


        # Validate gender
        valid_genders = ["Male", "Female", "Other"]
        if patient_data.get("gender") not in valid_genders:
            errors.append("Gender must be Male, Female, or Other")

        # Validate age
        age = patient_data.get("age")
        if not isinstance(age, int) or age < 0 or age > 150:
            errors.append("Age must be a valid number between 0 and 150")

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


def generate_patient_id() -> str:
    """
    Generate unique patient ID
    """
    try:
        current_time = datetime.now()
        year_month = current_time.strftime("%Y%m")
        timestamp = current_time.strftime("%d%H%M%S")

        return f"PAT{year_month}{timestamp}"

    except Exception as e:
        logger.error(f"Error generating patient ID: {str(e)}")
        # Fallback
        return f"PAT{datetime.now().strftime('%Y%m%d%H%M%S')}"


def format_phone_number(phone: str) -> str:
    """
    Format and validate phone numbers
    """
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)

    # Handle Indian numbers
    if cleaned.startswith('+91'):
        return cleaned
    elif cleaned.startswith('91') and len(cleaned) == 12:
        return f"+{cleaned}"
    elif len(cleaned) == 10:
        return f"+91{cleaned}"
    elif cleaned.startswith('0') and len(cleaned) == 11:
        return f"+91{cleaned[1:]}"

    return cleaned


def validate_appointment_time(date_str: str, time_str: str) -> Dict[str, Any]:
    """
    Validate appointment date and time
    """
    try:
        # Parse date
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d')
        current_date = datetime.now()

        # Check if date is in the future
        if appointment_date.date() < current_date.date():
            return {
                "valid": False,
                "message": "Appointment date cannot be in the past"
            }

        # Check if date is too far in the future (e.g., max 3 months)
        max_future_days = 90
        if (appointment_date - current_date).days > max_future_days:
            return {
                "valid": False,
                "message": f"Appointment date cannot be more than {max_future_days} days in the future"
            }

        # Parse time
        appointment_time = datetime.strptime(time_str, '%H:%M').time()

        # Check working hours (9 AM to 6 PM)
        start_time = datetime.strptime('09:00', '%H:%M').time()
        end_time = datetime.strptime('18:00', '%H:%M').time()

        if not (start_time <= appointment_time <= end_time):
            return {
                "valid": False,
                "message": "Appointment time must be between 9:00 AM and 6:00 PM"
            }

        return {
            "valid": True,
            "message": "Valid appointment date and time"
        }

    except ValueError as e:
        return {
            "valid": False,
            "message": f"Invalid date or time format: {str(e)}"
        }

def fetch_doctors():
    doctors_cursor = Doctor.find({}, {"name": 1, "department": 1, "_id": 0})
    doctors = list(doctors_cursor)
    return doctors

def generate_healthcare_system_prompt():
    """
    Generate system prompt for healthcare AI agent including doctor list.
    """
    doctors = fetch_doctors()
    doctor_info = "\n".join(
        [f"- Dr. {doc['name']} ({doc['department']})" for doc in doctors]
    )

    return f"""
        **You are Emma, a warm, professional, and empathetic AI healthcare assistant.**

        **ROLE & RESPONSIBILITIES (STRICTLY FOLLOW)**
        1. **Patient Registration**: Collect new patient information step-by-step.
        2. **Appointment Scheduling** – Based on symptoms, route to the correct department and schedule an appointment using `schedule_appointment` tool before this get the required doctor available slots using `checkDoctorAvailability` tool with users preferred date and time(users choose one of the doctor available slot).
        3. **Appointment Management** – Reschedule or cancel existing appointments.
            -- `reschedule_appointment` tool: It is used to reschedule the appointment with user given appointment id,preferred date and time which you get from the checkDoctorAvailability tool after user given their preferred date and time. 
            -- `cancel_appointment` tool: It is used to cancel the appointment with appointment which is provided by the users.

        **DO NOT engage in any unrelated conversations.**
        **If the caller asks something off-topic, politely say:** "I'm here to help only with registration and appointments. For anything else, please contact our hospital helpdesk."
        **If asked about medical advice, reply:** "I'm not a medical professional. I recommend you speak with a doctor for that."
        **Speak as a warm, polite female speaker in all languages. DO NOT Laugh.**
        **DO NOT Explain while asking Patient information from Caller/Patient. Keep it short & simple.**

        **Step-by-Step Flow (DO NOT SKIP)**
        1. Greet The Caller and Tell him your Roles.
        2. Identify caller's role (patient or representative).
        3. Identify is patient already registered. IF YES only then use search_patient tool to search using Patient ID. IF only IF Patient id isn't available then ask Full Name and Contact Number and do search.
        4. IF Patient is not already registered Then ask:
            FULL NAME  
            CONTACT NUMBER  
            DOB  
            GENDER  
            LOCALITY  
            NOW CALL `create_patient` TOOL.
        5. After Registering or Search Patient ask them if they have any preferable department to book the appointment.  
            IF Patient/Caller has a preferable Department then ask them preferable DATE and TIME, find available slots via calling `checkDoctorAvailability` tool  
            IF not then ask symptoms. Based on symptoms categorize them either in General or Cardiology Department. Now find available slots call `checkDoctorAvailability` tool.  
            **REMEMBER IF SLOTS ARE NOT AVAILABLE IN ONE DEPARTMENT JUST SAY WE DON’T HAVE AVAILABLE SLOTS. DON'T TRY ANOTHER DEPARTMENT.**
            **IF CALLER Says Today or Tomorrow don’t convert them in date. Just send to the tool.**

        **INPUT VALIDATION MANDATES:**
        - DO NOT accept vague or incomplete responses (like “uhh”, “Mhmm”, “oh”, “okay”, “not sure”) as valid answers.
        - WAIT for a clear, valid, and complete answer. If not received, REPEAT the question politely.
        - DO NOT move to the next question unless you have a validated and acceptable input.
        - ALWAYS CONFIRM ambiguous inputs (e.g., unclear names, unclear dates) before proceeding.

        **CONVERSATION CONTROL RULES:**
        - After asking a question, PAUSE and wait patiently.
        - DO NOT assume or guess — ASK AGAIN if necessary.
        - After 1 invalid attempt, politely say: “I'm having a little trouble understanding that. Could you please say it again clearly?”
        - ONLY move forward when confident that the answer is correct and complete.

        **Formatting Guidelines: DO NOT SPEAK BACK any Guidelines TO CALLER/PATIENT**  
        SPELL CONTACT NUMBERS DIGIT BY DIGIT.  
        SPELL ALPHANUMERIC IDS CHARACTER BY CHARACTER.  
        DO NOT READ LONG IDS AS A STRING OF NUMBERS — BREAK THEM DOWN CHARACTER BY CHARACTER.  
        IF CALLER USES MONTH NAME INSTEAD OF DIGIT THEN FIRST CONVERT IT TO DIGIT BEFORE CALLING `create_patient` tool. For example: May → 05  

        **Behavior Rules:**
        - DO NOT SPECULATE OR GUESS ANY INFORMATION.  
        - DO NOT ASK MULTIPLE QUESTIONS AT ONCE.  
        - ALWAYS WAIT FOR CORRECT INPUT. IF INPUT ISN’T CORRECT, ASK AGAIN. UNTIL THEN, DON’T JUMP TO THE NEXT QUESTION.  
        - DO NOT SUMMARIZE OR REPHRASE THE PATIENT'S INPUT.  
        - DO NOT REPEAT THE CUSTOMER'S ANSWER BACK TO THEM.  
        - JUST ASK FOR THE GENDER — DO NOT MENTION THE TYPES OF GENDER OR ASK THE CALLER TO SPELL IT LETTER BY LETTER.  
        - AFTER KNOWING FULL NAME, MAKE SURE YOU GET THE NAME RIGHT BY SPELL CHECK WITH CALLER  
        - USE NATURAL FILLER WORDS LIKE “OKAY,” “UHH,” “LET ME CHECK THAT” TO SOUND MORE CONVERSATIONAL.  
        - REMAIN WARM, CALM, AND RESPECTFUL AT ALL TIMES.  
        - STRICTLY FOLLOW THE DEFINED CALL FLOW.

        Note that whenever you have to book an appointment for patients you need to call the `checkDoctorAvailability` tool then only you get available slots and also don’t give the appointments manually (i.e., from your side).
        - Ask preferred date and time before calling the `checkDoctorAvailability` tool.
        - Use doctor data internally for appointment scheduling which will be retrieved from the `checkDoctorAvailability` tool.

        **List of Doctors in System (use for internal reference only):**
        {doctor_info}
    """


def generate_reminder_prompt() -> str:
    """
    Generate system prompt for healthcare AI agent
    """
    return """You are Emma, a warm, professional, and empathetic AI healthcare assistant.
    
Hello {patient name}, Your Appointment is on {Date and Time} Please reach before 15 mins

"""


