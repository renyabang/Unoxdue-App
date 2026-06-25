"""Autenticazione admin con JWT."""
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from config_db import JWT_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD

auth_router = APIRouter(prefix="/api/admin")
security = HTTPBearer(auto_error=True)


class LoginInput(BaseModel):
    email: str
    password: str


def create_token(email: str) -> str:
    payload = {
        "sub": email,
        "role": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def get_current_admin(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=["HS256"])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Accesso negato")
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessione scaduta")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token non valido")


@auth_router.post("/login")
async def login(data: LoginInput):
    if data.email.strip().lower() == ADMIN_EMAIL.lower() and data.password == ADMIN_PASSWORD:
        return {"token": create_token(data.email), "email": ADMIN_EMAIL}
    raise HTTPException(status_code=401, detail="Credenziali non valide")


@auth_router.get("/me")
async def me(admin: str = Depends(get_current_admin)):
    return {"email": admin, "role": "admin"}
