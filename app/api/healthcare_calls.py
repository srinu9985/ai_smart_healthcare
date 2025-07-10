# app/api/healthcare_calls.py
import os

from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, Query
from app.db.client import get_db
from app.core.logger import logger
from app.models.schemas import CallResponse
from app.utils.healthcare_ultravox_helper import create_healthcare_ultravox_call
from app.services.healthcare_service import HealthcareService
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import re
import requests

router = APIRouter(
    prefix="/calls",
    tags=["Healthcare Calls"]
)

healthcare_service = HealthcareService()


@router.get("/inbound")
async def handle_incoming_call(CallSid: str = Query(default=None)):
    """
    Webhook called by hospital phone system when patient calls
    """

    print("CallSid",CallSid)
    db=get_db()
    
    # Start Emma AI for incoming call
    response = create_healthcare_ultravox_call()
    join_url = response.get('joinUrl')
    #id which is unique for the data we are saving 
    callId = response.get('callId')
    result=db.healthcare_call_logs.insert_one({"call_sid":CallSid,"uvx_id":callId,"call_status":"Answered"})
    print(result)
    # Connect patient to Emma
    return CallResponse(url=join_url)

@router.get("/start-session")
async def start_openai_realtime_session():
    """
    Start a new OpenAI Realtime session (used by Emma/Voice AI)
    """
    try:
        url = "https://api.openai.com/v1/realtime/sessions"
        payload = {
            "model": "gpt-4o-realtime-preview-2024-12-17",
            "modalities": ["audio", "text"],
            "instructions": "You are a friendly assistant."
        }
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        logger.error(f"Failed to create OpenAI session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create OpenAI session")


@router.post("/save-summary")
async def save_healthcare_call_summary(request: Request):
    """
    Save summary of healthcare call - Called by Ultravox tool
    """
    try:
        data = await request.json()
        call_id = data.get("callId")
        summary = data.get("summary")
        intent = data.get("intent")
        outcome = data.get("outcome")
        patient_id = data.get("patient_id")

        if not call_id or not summary:
            raise HTTPException(status_code=400, detail="callId and summary are required")

        db = get_db()

        # Update healthcare call log
        update_data = {
            "call_summary": summary,
            "call_intent": intent,
            "call_outcome": outcome,
            "summary_saved_at": datetime.now(timezone.utc)
        }

        if patient_id:
            update_data["patient_id"] = patient_id
            update_data["patient_created"] = True

        # Try to find existing call log
        call_log = db.healthcare_call_logs.find_one({"ultravox_call_id": call_id})

        if call_log:
            # Update existing log
            db.healthcare_call_logs.update_one(
                {"ultravox_call_id": call_id},
                {"$set": update_data}
            )
        else:
            # Create new call log
            call_log_data = {
                "ultravox_call_id": call_id,
                "call_status": "completed",
                "created_at": datetime.now(timezone.utc),
                **update_data
            }
            db.healthcare_call_logs.insert_one(call_log_data)

        logger.info(f"Healthcare call summary saved for call {call_id}")

        return {
            "success": True,
            "message": "Call summary saved successfully",
            "call_id": call_id
        }

    except Exception as e:
        logger.error(f"Error saving healthcare call summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save summary: {str(e)}")


@router.post("/schedule-callback")
async def schedule_healthcare_callback(request: Request):
    """
    Schedule a callback for healthcare services - Called by Ultravox tool
    """
    try:
        data = await request.json()
        call_id = data.get("call_id")
        patient_name = data.get("patient_name")
        contact_number = data.get("contact_number")
        callback_time = data.get("callback_time")
        reason = data.get("reason")

        if not all([call_id, patient_name, contact_number, callback_time, reason]):
            raise HTTPException(
                status_code=400,
                detail="All fields (call_id, patient_name, contact_number, callback_time, reason) are required"
            )

        # Process callback time
        processed_time = process_callback_time(callback_time)

        db = get_db()

        # Create callback record
        callback_data = {
            "_id": ObjectId(),
            "original_call_id": call_id,
            "patient_name": patient_name,
            "contact_number": contact_number,
            "callback_time": processed_time,
            "reason": reason,
            "status": "scheduled",
            "created_at": datetime.now(timezone.utc),
            "callback_type": "healthcare"
        }

        result = db.healthcare_callbacks.insert_one(callback_data)

        # Update original call log
        db.healthcare_call_logs.update_one(
            {"ultravox_call_id": call_id},
            {"$set": {
                "callback_scheduled": True,
                "callback_id": str(result.inserted_id),
                "callback_time": processed_time
            }}
        )

        logger.info(f"Healthcare callback scheduled for {patient_name} at {processed_time}")

        return {
            "success": True,
            "message": f"Callback scheduled for {patient_name} at {processed_time.strftime('%Y-%m-%d %H:%M')}",
            "callback_id": str(result.inserted_id),
            "callback_time": processed_time.isoformat()
        }

    except Exception as e:
        logger.error(f"Error scheduling healthcare callback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule callback: {str(e)}")


@router.get("/start-healthcare-call")
async def start_healthcare_call(
        phone_number: str,
        call_type: str = "general",  # general, appointment, emergency
        db=Depends(get_db)
):
    """
    Start a healthcare call using Ultravox
    """
    try:
        # Validate phone number
        if not phone_number or len(re.sub(r'[^\d]', '', phone_number)) < 10:
            raise HTTPException(status_code=400, detail="Valid phone number required")

        # Create Ultravox call based on type
        if call_type == "emergency":
            from app.utils.healthcare_ultravox_helper import get_emergency_ultravox_config
            ultravox_config = get_emergency_ultravox_config()
        elif call_type == "appointment":
            from app.utils.healthcare_ultravox_helper import get_appointment_only_config
            ultravox_config = get_appointment_only_config()
        else:
            from app.utils.healthcare_ultravox_helper import get_healthcare_ultravox_config
            ultravox_config = get_healthcare_ultravox_config()

        # Create Ultravox call
        response = create_healthcare_ultravox_call()

        if not response:
            raise HTTPException(status_code=500, detail="Failed to create Ultravox call")

        join_url = response.get('joinUrl')
        ultravox_call_id = response.get('callId')

        if not join_url:
            raise HTTPException(status_code=500, detail="No join URL received from Ultravox")

        # Log the healthcare call
        call_log = {
            "ultravox_call_id": ultravox_call_id,
            "phone_number": phone_number,
            "call_type": call_type,
            "call_status": "initiated",
            "created_at": datetime.now(timezone.utc)
        }

        db.healthcare_call_logs.insert_one(call_log)

        logger.info(f"Healthcare call started: {ultravox_call_id} for {phone_number}")

        return {
            "success": True,
            "join_url": join_url,
            "ultravox_call_id": ultravox_call_id,
            "call_type": call_type
        }

    except Exception as e:
        logger.error(f"Error starting healthcare call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start call: {str(e)}")


@router.get("/call-logs")
async def get_healthcare_call_logs(
        page: int = 1,
        limit: int = 20,
        call_type: str = None,
        date_from: str = None,
        date_to: str = None,
        db=Depends(get_db)
):
    """
    Get healthcare call logs with filtering and pagination
    """
    try:
        query = {}

        if call_type:
            query["call_type"] = call_type

        if date_from and date_to:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query["created_at"] = {"$gte": start_date, "$lt": end_date}

        skip = (page - 1) * limit
        total_count = db.healthcare_call_logs.count_documents(query)

        call_logs = list(
            db.healthcare_call_logs.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        # Convert ObjectId to string for JSON response
        for log in call_logs:
            log["_id"] = str(log["_id"])

        return {
            "success": True,
            "call_logs": call_logs,
            "pagination": {
                "current_page": page,
                "total_pages": (total_count + limit - 1) // limit,
                "total_items": total_count,
                "items_per_page": limit
            }
        }

    except Exception as e:
        logger.error(f"Error getting healthcare call logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get call logs: {str(e)}")


@router.get("/callbacks")
async def get_scheduled_callbacks(
        status: str = "scheduled",
        db=Depends(get_db)
):
    """
    Get scheduled healthcare callbacks
    """
    try:
        query = {"status": status}

        callbacks = list(
            db.healthcare_callbacks.find(query)
            .sort("callback_time", 1)
        )

        # Convert ObjectId to string
        for callback in callbacks:
            callback["_id"] = str(callback["_id"])

        return {
            "success": True,
            "callbacks": callbacks,
            "count": len(callbacks)
        }

    except Exception as e:
        logger.error(f"Error getting callbacks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get callbacks: {str(e)}")


@router.post("/callbacks/{callback_id}/execute")
async def execute_callback(
        callback_id: str,
        background_tasks: BackgroundTasks,
        db=Depends(get_db)
):
    """
    Execute a scheduled callback
    """
    try:
        callback = db.healthcare_callbacks.find_one({"_id": ObjectId(callback_id)})

        if not callback:
            raise HTTPException(status_code=404, detail="Callback not found")

        if callback["status"] != "scheduled":
            raise HTTPException(status_code=400, detail="Callback already executed or cancelled")

        # Check if it's time for the callback
        current_time = datetime.now(timezone.utc)
        callback_time = callback["callback_time"]

        if callback_time > current_time + timedelta(minutes=5):
            raise HTTPException(
                status_code=400,
                detail="Callback is not due yet"
            )

        # Mark as executing
        db.healthcare_callbacks.update_one(
            {"_id": ObjectId(callback_id)},
            {"$set": {
                "status": "executing",
                "execution_started_at": current_time
            }}
        )

        # Start the callback call in background
        background_tasks.add_task(
            execute_healthcare_callback,
            callback["contact_number"],
            callback_id,
            callback["patient_name"]
        )

        return {
            "success": True,
            "message": "Callback execution started",
            "callback_id": callback_id
        }

    except Exception as e:
        logger.error(f"Error executing callback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to execute callback: {str(e)}")


def process_callback_time(callback_time_str: str) -> datetime:
    """
    Process callback time string and convert to datetime
    """
    try:
        current_time = datetime.now(timezone.utc)

        if "today" in callback_time_str.lower():
            time_part = callback_time_str.lower().replace("today", "").strip()
            if time_part:
                hour, minute = map(int, time_part.split(":"))
                return current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                return current_time + timedelta(hours=1)  # Default to 1 hour later

        elif "tomorrow" in callback_time_str.lower():
            time_part = callback_time_str.lower().replace("tomorrow", "").strip()
            if time_part:
                hour, minute = map(int, time_part.split(":"))
                tomorrow = current_time + timedelta(days=1)
                return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                tomorrow = current_time + timedelta(days=1)
                return tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        else:
            # Try to parse as full datetime
            return datetime.strptime(callback_time_str, '%Y-%m-%d %H:%M')

    except Exception as e:
        logger.error(f"Error processing callback time: {str(e)}")
        # Default to 1 hour from now
        return datetime.now(timezone.utc) + timedelta(hours=1)


async def execute_healthcare_callback(phone_number: str, callback_id: str, patient_name: str):
    """
    Background task to execute healthcare callback
    """
    try:
        # Start healthcare call
        response = create_healthcare_ultravox_call()

        if response:
            ultravox_call_id = response.get('callId')

            # Update callback status
            db = get_db()
            db.healthcare_callbacks.update_one(
                {"_id": ObjectId(callback_id)},
                {"$set": {
                    "status": "completed",
                    "ultravox_call_id": ultravox_call_id,
                    "executed_at": datetime.now(timezone.utc)
                }}
            )

            logger.info(f"Healthcare callback executed for {patient_name}")
        else:
            # Mark as failed
            db = get_db()
            db.healthcare_callbacks.update_one(
                {"_id": ObjectId(callback_id)},
                {"$set": {
                    "status": "failed",
                    "failure_reason": "Failed to create Ultravox call",
                    "failed_at": datetime.now(timezone.utc)
                }}
            )

    except Exception as e:
        logger.error(f"Error in healthcare callback execution: {str(e)}")

        # Mark as failed
        db = get_db()
        db.healthcare_callbacks.update_one(
            {"_id": ObjectId(callback_id)},
            {"$set": {
                "status": "failed",
                "failure_reason": str(e),
                "failed_at": datetime.now(timezone.utc)
            }}
        )