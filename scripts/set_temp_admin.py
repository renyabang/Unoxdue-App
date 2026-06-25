"""Imposta una password TEMPORANEA nota per l'admin e forza il cambio al primo accesso.
- Scrive la password in ADMIN_PASSWORD (backend/.env).
- Aggiorna l'hash pbkdf2 nel DB, imposta must_change_password=True e incrementa token_version
  (=> tutti i JWT precedenti vengono invalidati).
Uso: python scripts/set_temp_admin.py "PasswordTemporanea"
"""
import asyncio
import sys
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / "backend" / ".env"


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


async def _update_db(pw: str):
    sys.path.insert(0, str(ENV_PATH.parent))
    from config_db import db, ADMIN_EMAIL
    from auth import _hash
    user = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
    tv = (user.get("token_version", 1) + 1) if user else 1
    await db.users.update_one(
        {"email": ADMIN_EMAIL.lower()},
        {"$set": {"password_hash": _hash(pw), "must_change_password": True, "token_version": tv}},
        upsert=True,
    )


def main():
    pw = sys.argv[1]
    _write_env_password(pw)
    asyncio.run(_update_db(pw))
    print("Password temporanea impostata; cambio richiesto al primo accesso.")


if __name__ == "__main__":
    main()
