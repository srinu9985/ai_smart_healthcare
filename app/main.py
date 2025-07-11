import datetime

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api import appointments, doctors, healthcare, healthcare_calls, auth,patients
from app.api import webhooks
from contextlib import asynccontextmanager
from dotenv import load_dotenv  
from app.core.logger import logger

load_dotenv()


app = FastAPI(title= "AI Smart Healthcare", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(appointments.router)
app.include_router(auth.router)
app.include_router(doctors.router)
app.include_router(patients.router)
app.include_router(healthcare.router)
app.include_router(healthcare_calls.router)
@app.get("/")
async def root():
    return {"message": "Ai_Smart_Healthcare AI API!"}



