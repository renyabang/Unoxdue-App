"""Autenticazione admin sicura:
- credenziali in DB (hash pbkdf2), mai hardcoded nel codice;
- bootstrap dell'admin iniziale da variabili ambiente;
- cambio password obbligatorio al primo accesso;
- versione token (cambio password -> invalida i token precedenti);
- rate limiting con blocco temporaneo dopo tentativi falliti;
- nessuna password nei log o nelle risposte.
"""
import time
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from passlib.context import CryptContext

from config_db import db, JWT_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD

auth_router = APIRouter(prefix="/api/admin")
security = HTTPBearer(auto_error=True)
pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Rate limiting in-memory (per processo). Soglia e finestra.
MAX_ATTEMPTS = 5
LOCK_SECONDS = 300  # 5 minuti
_attempts = {}  # key -> {"count": int, "locked_until": float}


class LoginInput(BaseModel):
    email: str
    password: str


class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str


def _hash(p: str) -> str:
    return pwd_ctx.hash(p)


def _verify(p: str, h: str) -> bool:
    try:
        return pwd_ctx.verify(p, h)
    except Exception:
        return False


async def ensure_admin():
    """Crea l'admin iniziale dalle variabili ambiente, se non esiste."""
    existing = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
    if not existing:
        await db.users.insert_one({
            "email": ADMIN_EMAIL.lower(),
            "password_hash": _hash(ADMIN_PASSWORD),
            "role": "admin",
            "token_version": 1,
            "must_change_password": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })


def create_token(user: dict) -> str:
    payload = {
        "sub": user["email"],
        "role": user.get("role", "admin"),
        "tv": user.get("token_version", 1),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _rl_key(request: Request, email: str) -> str:
    ip = request.client.host if request.client else "?"
    return f"{ip}:{email.lower()}"


def _check_lock(key: str):
    rec = _attempts.get(key)
    if rec and rec.get("locked_until", 0) > time.time():
        wait = int(rec["locked_until"] - time.time())
        raise HTTPException(status_code=429, detail=f"Troppi tentativi. Riprova tra {wait}s.")


def _register_fail(key: str):
    rec = _attempts.get(key, {"count": 0, "locked_until": 0})
    rec["count"] += 1
    if rec["count"] >= MAX_ATTEMPTS:
        rec["locked_until"] = time.time() + LOCK_SECONDS
        rec["count"] = 0
    _attempts[key] = rec


def _reset_fail(key: str):
    _attempts.pop(key, None)


async def get_current_admin(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessione scaduta")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token non valido")
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accesso negato")
    user = await db.users.find_one({"email": payload.get("sub")}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utente non valido")
    if payload.get("tv") != user.get("token_version", 1):
        raise HTTPException(status_code=401, detail="Token revocato, effettua di nuovo l'accesso")
    return user


@auth_router.post("/login")
async def login(data: LoginInput, request: Request):
    key = _rl_key(request, data.email)
    _check_lock(key)
    user = await db.users.find_one({"email": data.email.strip().lower()})
    if not user or not _verify(data.password, user.get("password_hash", "")):
        _register_fail(key)
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    _reset_fail(key)
    return {
        "token": create_token(user),
        "email": user["email"],
        "must_change_password": bool(user.get("must_change_password")),
    }


@auth_router.get("/me")
async def me(admin: dict = Depends(get_current_admin)):
    return {"email": admin["email"], "role": admin.get("role"),
            "must_change_password": bool(admin.get("must_change_password"))}


@auth_router.post("/change-password")
async def change_password(data: ChangePasswordInput, admin: dict = Depends(get_current_admin)):
    user = await db.users.find_one({"email": admin["email"]})
    if not _verify(data.current_password, user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Password attuale errata")
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="La nuova password deve avere almeno 8 caratteri")
    if _verify(data.new_password, user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="La nuova password deve essere diversa")
    new_tv = user.get("token_version", 1) + 1
    await db.users.update_one({"email": admin["email"]}, {"$set": {
        "password_hash": _hash(data.new_password),
        "must_change_password": False,
        "token_version": new_tv,
    }})
    fresh = await db.users.find_one({"email": admin["email"]})
    # nuovo token con versione aggiornata: i token precedenti diventano invalidi
    return {"ok": True, "token": create_token(fresh)}
