"""Emergent Object Store — persistenza media in produzione.

Il filesystem del container in produzione è EFFIMERO: ogni media generato o caricato
(copertine WebP, grafiche schedine, loghi rassegna stampa, upload OCR) va salvato qui.

Vincoli dell'Object Store:
- Niente delete/overwrite: un PUT su un path esistente può dare 409 -> usiamo path con
  content-hash/uuid (stabili e univoci), nessuna cancellazione necessaria.
- Niente URL pubblici diretti / presigned: ogni accesso passa dal backend.
  Gli asset sono pubblici -> serviti via GET /api/media/{path} (passthrough, no auth).
- `storage_key` è di sessione: si inizializza una volta e si riusa; su 403 si rinnova.
"""
import os
import logging
import threading

import requests

logger = logging.getLogger("uvicorn.error")

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_PREFIX = "unoxdue"

_storage_key = None
_lock = threading.Lock()

# Cache in-memory degli asset serviti (piccoli: copertine/loghi/grafiche).
_cache = {}
_CACHE_MAX = 256


def _init(force: bool = False) -> str:
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    with _lock:
        if _storage_key and not force:
            return _storage_key
        resp = requests.post(f"{STORAGE_URL}/init",
                             json={"emergent_key": os.environ.get("EMERGENT_LLM_KEY")}, timeout=30)
        resp.raise_for_status()
        _storage_key = resp.json()["storage_key"]
        logger.info("Object Store: storage_key inizializzata")
    return _storage_key


def init_storage() -> str:
    return _init()


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Carica i byte sul path indicato. 409 (già presente, stesso content-hash) = ok."""
    def _do(k):
        return requests.put(f"{STORAGE_URL}/objects/{path}",
                            headers={"X-Storage-Key": k, "Content-Type": content_type},
                            data=data, timeout=120)
    resp = _do(_init())
    if resp.status_code == 403:
        resp = _do(_init(force=True))
    if resp.status_code == 409:
        return {"path": path, "size": len(data), "existing": True}
    resp.raise_for_status()
    _cache.pop(path, None)
    try:
        return resp.json()
    except Exception:
        return {"path": path, "size": len(data)}


def get_object(path: str):
    """Scarica i byte. Ritorna (content, content_type). Solleva su 404."""
    def _do(k):
        return requests.get(f"{STORAGE_URL}/objects/{path}",
                            headers={"X-Storage-Key": k}, timeout=60)
    resp = _do(_init())
    if resp.status_code == 403:
        resp = _do(_init(force=True))
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def cached_get(path: str):
    if path in _cache:
        return _cache[path]
    data, ctype = get_object(path)
    if len(_cache) >= _CACHE_MAX:
        _cache.pop(next(iter(_cache)))
    _cache[path] = (data, ctype)
    return data, ctype


def public_url(path: str) -> str:
    from config_db import SITE_URL
    return f"{SITE_URL}/api/media/{path}"
