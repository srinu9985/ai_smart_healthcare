from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in the environment")

client = MongoClient(MONGO_URI)
db = client["emma_healthcare"]

patients_collection = db["patients"]
appointments_collection = db["appointments"]
doctors_collection = db["doctors"]
Doctor=db["Doctors_data"]

def get_db():
    return db
def init_db():
    print("MongoDB connected to healthcare")

def get_database():
    return db