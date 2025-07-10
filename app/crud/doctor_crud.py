from app.db.client import doctors_collection  # adjust import based on your project
from dotenv import load_dotenv

load_dotenv()

def create_doctor(data: dict) -> str:
    result = doctors_collection.insert_one(data)
    return str(result.inserted_id)

def serialize_doctor(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "specialty": doc.get("specialty"),
        "gender": doc.get("gender"),
        "location": doc.get("location"),
        "available_modes": doc.get("available_modes", []),
    }

def get_doctors_by_specialty(specialty: str) -> list:
    doctors = doctors_collection.find({"specialty": specialty})
    return [serialize_doctor(doc) for doc in doctors]
