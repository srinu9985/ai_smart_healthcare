
from app.db.client import appointments_collection
import datetime
from dotenv import load_dotenv

load_dotenv()

def create_appointment(data: dict):
    # Ensure nested appointment.date and appointment.time are datetime types
    appointment = data.get("appointment", {})

    if isinstance(appointment.get("date"), datetime.date) and not isinstance(appointment.get("date"), datetime.datetime):
        appointment["date"] = datetime.datetime.combine(appointment["date"], datetime.time())

    # No need to convert time object; MongoDB can store strings or datetime.time
    # but you may format it to string for consistency
    if isinstance(appointment.get("time"), datetime.time):
        appointment["time"] = appointment["time"].strftime("%H:%M")

    data["appointment"] = appointment  # update back

    return str(appointments_collection.insert_one(data).inserted_id)

def get_appointments_by_patient(patient_id: str):
    appointments = appointments_collection.find({"patient_id": patient_id})
    result = []
    for appt in appointments:
        appt["_id"] = str(appt["_id"])  # convert ObjectId to string
        result.append(appt)
    return result