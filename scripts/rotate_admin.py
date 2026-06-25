"""Rotazione protetta delle credenziali admin.
- Genera una password forte casuale.
- La salva SOLO nella variabile ambiente ADMIN_PASSWORD (backend/.env).
- Aggiorna l'hash nel DB, azzera must_change_password e incrementa token_version
  (=> tutti i JWT emessi prima vengono invalidati).
- NON stampa mai la password in chiaro (solo mascherata).
Uso: python scripts/rotate_admin.py
"""
import asyncio
import secrets
import string
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / "backend" / ".env"


def _gen_password(n: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!#$%&*+-?@"
    # garantisce almeno un carattere per classe
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(n))
        if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                and any(c.isdigit() for c in pw) and any(c in "!#$%&*+-?@" for c in pw)):
            return pw


def _write_env_password(pw: str):
    lines = ENV_PATH.read_text().splitlines()
    out, found = [], False
    for ln in lines:
        if ln.startswith("ADMIN_PASSWORD="):
            out.append(f'ADMIN_PASSWORD="{pw}"')
            found = True
        else:
            out.append(ln)
    if not found:
        out.append(f'ADMIN_PASSWORD="{pw}"')
    ENV_PATH.write_text("\n".join(out) + "\n")


async def _rotate_db(pw: str):
    import sys
    sys.path.insert(0, str(ENV_PATH.parent))
    from config_db import db, ADMIN_EMAIL
    from auth import _hash
    user = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
    tv = (user.get("token_version", 1) + 1) if user else 1
    await db.users.update_one(
        {"email": ADMIN_EMAIL.lower()},
        {"$set": {"password_hash": _hash(pw), "must_change_password": False, "token_version": tv}},
        upsert=True,
    )


def main():
    pw = _gen_password()
    _write_env_password(pw)
    asyncio.run(_rotate_db(pw))
    print("Credenziali amministratore ruotate e archiviate nelle variabili ambiente.")
    print("Password: " + "*" * 8)


if __name__ == "__main__":
    main()
