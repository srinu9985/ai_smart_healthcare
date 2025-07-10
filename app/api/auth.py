# app/api/auth.py

import os
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from app.models.schemas import UserRegisterModel, PasswordResetRequest, PasswordResetOTP

from app.core.security import create_access_token, authenticate_user, hash_password, verify_invite_token
from app.db.client import get_db
from app.models.schemas import UserCompleteRegistration
from app.core.logger import logger

from app.services.connectorio import send_connectorio_email

import random
import string
reset_otp_store = {}
reset_token_store = {}


router = APIRouter(tags=["Registration"])
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))


@router.post("/register")
def register_user(user: UserRegisterModel):
    db = get_db()

    # Check if email already exists
    if db["users"].find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password before storing
    hashed_password = hash_password(user.password)

    # Build user document with doctor-specific fields
    current_time = datetime.now(timezone.utc)
    user_doc = {
        "email": user.email,
        "password": hashed_password,
        "emp_id": user.emp_id,
        "role": user.role,
        "hospital_name": user.hospital_name,
        "is_active": True,
        "last_login": current_time,
        "created_at": current_time,
        "updated_at": current_time
    }

    db["users"].insert_one(user_doc)

    return {
        "message": "Doctor registered successfully.",
        "employee_id": str(user_doc["emp_id"]),
        "email": user.email
    }


@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username
    password = form_data.password

    # Authenticate user
    user = authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Check if user is active
    if not user.get("is_active", False):
        raise HTTPException(
            status_code=403,
            detail="Your account has been deactivated. Please contact administrator."
        )

    # Update user's last login time
    db = get_db()
    current_time = datetime.now(timezone.utc)

    try:
        db.users.update_one(
            {"email": email},
            {"$set": {"last_login_at": current_time}}
        )
        logger.info(f"User {email} logged in successfully")
    except Exception as e:
        logger.error(f"Failed to update login time for {email}: {str(e)}")
        # Continue with login even if update fails

    # Create access token
    access_token = create_access_token(
        data={"sub": user["email"], "role": user["role"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}

## Registration for Invited candidates
@router.post("/complete-registration", status_code=201)
def complete_registration(data: UserCompleteRegistration):
    db = get_db()

    # 1. Verify token and extract IMMUTABLE fields
    try:
        token_data = verify_invite_token(data.token)  # Contains email, hospital_name, role
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # 2. Check if user already exists
    if db.users.find_one({"email": token_data["email"]}):
        raise HTTPException(status_code=400, detail="User already registered")

    # 3. Create user (ONLY allow mutable fields from request)
    current_time = datetime.now(timezone.utc)
    user_data = {
        # Immutable (from token)
        "email": token_data["email"],
        "hospital_name": token_data["hospital_name"],
        "role": token_data["role"],

        # Mutable (from user input)
        "full_name": data.full_name,
        "department": data.department,
        "password": hash_password(data.password),

        # System fields
        "created_at": current_time,
        "updated_at": current_time,
        "last_login_at": None,
        "is_active": True
    }

    result = db["users"].insert_one(user_data)

    return {"message": "Registration complete. Please log in to your account.",
            "user_id": str(result.inserted_id)
            }


@router.post("/forgot-password/otp")
def send_otp(request: PasswordResetRequest, background_tasks: BackgroundTasks):
    db = get_db()
    user = db["users"].find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp = ''.join(random.choices(string.digits, k=6))
    expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    reset_otp_store[request.email] = {"otp": otp, "expires_at": expiry}

    # send_email(to=request.email, subject="Your OTP Code", body=f"Your OTP is: {otp}")
    # Send email via ConnectorIO
    background_tasks.add_task(
        send_connectorio_email,
        subject="Your OTP Code",
        body=f"Your OTP is: {otp}",
        toRecipients=[request.email]
    )

    return {"message": "OTP sent successfully to your email"}


@router.post("/reset-password/otp")
def reset_password_otp(data: PasswordResetOTP):
    entry = reset_otp_store.get(data.email)
    if not entry or entry["otp"] != data.otp or datetime.now(timezone.utc) > entry["expires_at"]:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    db = get_db()
    hashed_pw = hash_password(data.new_password)
    db["users"].update_one({"email": data.email}, {"$set": {"password": hashed_pw}})
    del reset_otp_store[data.email]

    return {"message": "Password reset successful using OTP"}
