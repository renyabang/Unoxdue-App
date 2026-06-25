"""Step 3 Fase B — Flusso OAuth 2.0 (Authorization Code) per YouTube Data API.

L'admin clicca "Connetti YouTube": nessun refresh token incollato manualmente.
- access_type=offline + prompt=consent => refresh token.
- Token cifrati a riposo (Fernet, chiave derivata da JWT_SECRET) in db.youtube_oauth.
- Refresh automatico dell'access token. Verifica che il canale autorizzato sia quello configurato.
"""
import base64
import hashlib
import secrets as _secrets
from datetime import datetime, timezone, timedelta

import requests

from config_db import (db, JWT_SECRET, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET,
                       YOUTUBE_CHANNEL_ID)

OAUTH_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
CALLBACK_PATH = "/api/admin/youtube/oauth/callback"
_DOC_ID = "youtube"


def _now():
    return datetime.now(timezone.utc)


def _fernet():
    from cryptography.fernet import Fernet
    key = base64.urlsafe_b64encode(hashlib.sha256((JWT_SECRET or "uxd").encode()).digest())
    return Fernet(key)


def _enc(s: str) -> str:
    if not s:
        return ""
    return _fernet().encrypt(s.encode()).decode()


def _dec(s: str) -> str:
    if not s:
        return ""
    try:
        return _fernet().decrypt(s.encode()).decode()
    except Exception:
        return ""


def client_configured() -> bool:
    return bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)


def callback_uri(origin: str) -> str:
    return origin.rstrip("/") + CALLBACK_PATH


# ----------------------- state CSRF -----------------------
async def create_state(origin: str) -> str:
    state = _secrets.token_urlsafe(24)
    await db.youtube_oauth_state.insert_one({
        "state": state, "origin": origin.rstrip("/"),
        "redirect_uri": callback_uri(origin),
        "created_at": _now().isoformat(),
    })
    return state


async def consume_state(state: str):
    doc = await db.youtube_oauth_state.find_one({"state": state})
    if doc:
        await db.youtube_oauth_state.delete_one({"state": state})
    return doc


def build_auth_url(redirect_uri: str, state: str) -> str:
    from urllib.parse import urlencode
    params = {
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": OAUTH_SCOPE,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


# ----------------------- scambio code / refresh -----------------------
def _exchange_code_sync(code: str, redirect_uri: str) -> dict:
    r = requests.post(TOKEN_ENDPOINT, data={
        "code": code, "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": GOOGLE_OAUTH_CLIENT_SECRET, "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }, timeout=20)
    r.raise_for_status()
    return r.json()


def _refresh_sync(refresh_token: str) -> dict:
    r = requests.post(TOKEN_ENDPOINT, data={
        "refresh_token": refresh_token, "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": GOOGLE_OAUTH_CLIENT_SECRET, "grant_type": "refresh_token",
    }, timeout=20)
    r.raise_for_status()
    return r.json()


def _channel_of_token_sync(access_token: str) -> dict:
    r = requests.get("https://www.googleapis.com/youtube/v3/channels",
                     params={"part": "snippet", "mine": "true"},
                     headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        return {}
    return {"id": items[0]["id"], "title": items[0]["snippet"].get("title")}


async def handle_callback(code: str, redirect_uri: str, loop) -> dict:
    """Scambia il code, verifica il canale e salva i token cifrati."""
    tokens = await loop.run_in_executor(None, _exchange_code_sync, code, redirect_uri)
    access = tokens.get("access_token")
    refresh = tokens.get("refresh_token")
    if not access:
        return {"ok": False, "error": "Token non ricevuto da Google"}
    channel = await loop.run_in_executor(None, _channel_of_token_sync, access)
    if YOUTUBE_CHANNEL_ID and channel.get("id") and channel["id"] != YOUTUBE_CHANNEL_ID:
        return {"ok": False, "error": f"Canale autorizzato ({channel.get('title')}) diverso da quello configurato. "
                                      "Usa l'account proprietario del canale UnoXdue."}
    if not refresh:
        existing = await db.youtube_oauth.find_one({"_id": _DOC_ID})
        refresh = _dec(existing.get("refresh_token_enc", "")) if existing else ""
        if not refresh:
            return {"ok": False, "error": "Nessun refresh token ricevuto. Revoca l'accesso dell'app "
                                          "in https://myaccount.google.com/permissions e riprova (serve prompt=consent)."}
    expiry = (_now() + timedelta(seconds=int(tokens.get("expires_in", 3600)))).isoformat()
    await db.youtube_oauth.update_one({"_id": _DOC_ID}, {"$set": {
        "_id": _DOC_ID,
        "refresh_token_enc": _enc(refresh),
        "access_token_enc": _enc(access),
        "access_expiry": expiry,
        "scope": tokens.get("scope", OAUTH_SCOPE),
        "channel_id": channel.get("id"),
        "channel_title": channel.get("title"),
        "connected_at": _now().isoformat(),
        "last_refresh_at": _now().isoformat(),
        "last_error": None,
    }}, upsert=True)
    return {"ok": True, "channel_title": channel.get("title"), "channel_id": channel.get("id")}


async def get_refresh_token() -> str:
    doc = await db.youtube_oauth.find_one({"_id": _DOC_ID})
    return _dec(doc.get("refresh_token_enc", "")) if doc else ""


async def get_access_token(loop) -> str:
    """Restituisce un access token valido, rinnovandolo se scaduto."""
    doc = await db.youtube_oauth.find_one({"_id": _DOC_ID})
    if not doc:
        return ""
    expiry = doc.get("access_expiry")
    token = _dec(doc.get("access_token_enc", ""))
    if token and expiry and datetime.fromisoformat(expiry) > _now() + timedelta(seconds=60):
        return token
    refresh = _dec(doc.get("refresh_token_enc", ""))
    if not refresh:
        return ""
    try:
        tok = await loop.run_in_executor(None, _refresh_sync, refresh)
    except Exception as e:
        await db.youtube_oauth.update_one({"_id": _DOC_ID}, {"$set": {"last_error": str(e)[:300]}})
        return ""
    access = tok.get("access_token", "")
    new_expiry = (_now() + timedelta(seconds=int(tok.get("expires_in", 3600)))).isoformat()
    await db.youtube_oauth.update_one({"_id": _DOC_ID}, {"$set": {
        "access_token_enc": _enc(access), "access_expiry": new_expiry,
        "last_refresh_at": _now().isoformat(), "last_error": None,
    }})
    return access


async def is_connected() -> bool:
    return bool(await get_refresh_token())


async def get_status() -> dict:
    doc = await db.youtube_oauth.find_one({"_id": _DOC_ID}) or {}
    connected = bool(doc.get("refresh_token_enc"))
    return {
        "client_configured": client_configured(),
        "connected": connected,
        "channel_id": doc.get("channel_id"),
        "channel_title": doc.get("channel_title"),
        "connected_at": doc.get("connected_at"),
        "last_refresh_at": doc.get("last_refresh_at"),
        "last_error": doc.get("last_error"),
        "scope": doc.get("scope") or OAUTH_SCOPE,
        "configured_channel": YOUTUBE_CHANNEL_ID,
        "note": ("Collega l'account proprietario del canale UnoXdue per scaricare i sottotitoli."
                 if not connected else "YouTube collegato."),
    }


async def disconnect() -> dict:
    await db.youtube_oauth.delete_one({"_id": _DOC_ID})
    return {"ok": True}
