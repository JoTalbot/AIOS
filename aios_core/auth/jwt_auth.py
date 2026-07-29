import os
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

USERS_DB = {
    "admin": {"password_hash": pwd_context.hash("admin123"), "role": "admin"},
    "manager": {"password_hash": pwd_context.hash("manager123"), "role": "manager"},
    "viewer": {"password_hash": pwd_context.hash("viewer123"), "role": "viewer"},
}

ROLE_PERMISSIONS = {
    "admin": ["read", "write", "delete", "manage_users"],
    "manager": ["read", "write"],
    "viewer": ["read"],
}

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = verify_token(credentials.credentials)
    username = payload.get("sub")
    if not username or username not in USERS_DB:
        raise HTTPException(status_code=401, detail="User not found")
    return {"username": username, "role": USERS_DB[username]["role"]}

def require_role(required_role: str):
    async def role_checker(user: dict = Depends(get_current_user)):
        role_hierarchy = {"viewer": 1, "manager": 2, "admin": 3}
        if role_hierarchy.get(user["role"], 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

def login(username: str, password: str) -> str | None:
    user = USERS_DB.get(username)
    if not user or not pwd_context.verify(password, user["password_hash"]):
        return None
    return create_access_token({"sub": username, "role": user["role"]})
