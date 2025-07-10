# app/core/security.py

import os
import datetime
import bcrypt
from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from app.db.client import get_db
from itsdangerous import URLSafeTimedSerializer

# Config
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Hash password using bcrypt
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# Verify and return user if credentials are valid
def authenticate_user(email: str, password: str):
    db = get_db()
    user = db["users"].find_one({"email": email})
    if not user or not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
        return None
    return user

# Create JWT token with expiration
def create_access_token(data: dict, expires_delta: datetime.timedelta):
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.UTC) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Get current user from token
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = get_db()
    user = db["users"].find_one({"email": email})
    if not user:
        raise credentials_exception

    return user

#  Role-based access control
def require_role(allowed_roles: list[str]):
    def _role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Access forbidden: insufficient role")
        return current_user
    return _role_checker

# Generating Token
def generate_invite_token(email: str, company_name: str, role: str) -> str:
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps(
        {"email": email, "company_name": company_name, "role": role},
        salt="invite"
    )

# Verifying Token
def verify_invite_token(token: str, max_age: int = 86400) -> dict:
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    # return serializer.loads(token, salt="invite", max_age=max_age)  # Expires in 24h
    try:
        return serializer.loads(token, salt="invite", max_age=max_age)
    except Exception as e:
        print(f"[TOKEN ERROR] {e}")  # or use logger.error(...)
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired token"
        )
