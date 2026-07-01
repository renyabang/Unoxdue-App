"""Newsletter via Resend — iscrizioni (single opt-in), invio campagne e notifiche.

Chiave API da env RESEND_API_KEY. Mittente e template modificabili da admin (db.settings.newsletter).
Iscritti in db.subscribers. Ogni email include il link di disiscrizione (obbligatorio).
"""
import os
import re
import uuid
import asyncio
import logging
from datetime import datetime, timezone

import resend

from config_db import db, SITE_URL

logger = logging.getLogger("uvicorn.error")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEFAULT_SENDER = "newsletter@unoxdue.net"
DEFAULT_FROM_NAME = "UnoXdue"

DEFAULT_TEMPLATES = {
    "episode": {
        "subject": "🎙️ Nuova puntata UnoXdue: {title}",
        "intro": "È online una nuova puntata di UnoXdue. Buon ascolto!",
    },
    "live": {
        "subject": "🔴 UnoXdue è LIVE ora!",
        "intro": "Stiamo iniziando la diretta: entra ora e commenta con noi.",
    },
}


# ----------------------------- Config -----------------------------
async def get_config() -> dict:
    s = await db.settings.find_one({"_id": "global"}, {"_id": 0, "newsletter": 1}) or {}
    return s.get("newsletter") or {}


async def admin_config_view() -> dict:
    cfg = await get_config()
    templates = {**{k: dict(v) for k, v in DEFAULT_TEMPLATES.items()}, **(cfg.get("templates") or {})}
    active = await db.subscribers.count_documents({"status": "active"})
    total = await db.subscribers.count_documents({})
    return {
        "api_key_set": bool(os.environ.get("RESEND_API_KEY")),
        "sender_email": cfg.get("sender_email") or DEFAULT_SENDER,
        "from_name": cfg.get("from_name") or DEFAULT_FROM_NAME,
        "owner_email": cfg.get("owner_email") or os.environ.get("ADMIN_EMAIL", ""),
        "enabled": bool(cfg.get("enabled", False)),
        "auto_episode": bool(cfg.get("auto_episode", False)),
        "templates": templates,
        "default_templates": DEFAULT_TEMPLATES,
        "subscribers_active": active,
        "subscribers_total": total,
        "status": cfg.get("status") or {},
    }


async def save_config(data: dict) -> dict:
    patch = {}
    for k in ("sender_email", "from_name", "owner_email"):
        if k in data:
            patch[f"newsletter.{k}"] = (data.get(k) or "").strip()
    for k in ("enabled", "auto_episode"):
        if k in data:
            patch[f"newsletter.{k}"] = bool(data.get(k))
    if isinstance(data.get("templates"), dict):
        clean = {k: v for k, v in data["templates"].items() if k in DEFAULT_TEMPLATES}
        patch["newsletter.templates"] = clean
    if patch:
        await db.settings.update_one({"_id": "global"}, {"$set": patch}, upsert=True)
    return await admin_config_view()


# ----------------------------- Iscritti -----------------------------
async def subscribe(email: str, source: str = "sito") -> dict:
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email):
        return {"ok": False, "error": "Email non valida"}
    existing = await db.subscribers.find_one({"email": email})
    if existing:
        if existing.get("status") != "active":
            await db.subscribers.update_one({"email": email}, {"$set": {"status": "active"}})
        return {"ok": True, "already": True}
    await db.subscribers.insert_one({
        "id": str(uuid.uuid4()), "email": email, "status": "active", "source": source,
        "unsub_token": uuid.uuid4().hex, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True}


async def unsubscribe(token: str) -> bool:
    if not token:
        return False
    r = await db.subscribers.update_one({"unsub_token": token}, {"$set": {"status": "unsub"}})
    return r.matched_count > 0


async def list_subscribers(limit: int = 1000) -> list:
    return await db.subscribers.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)


# ----------------------------- Email HTML -----------------------------
def _unsub_url(token: str) -> str:
    return f"{SITE_URL}/api/newsletter/unsubscribe?token={token}"


def _wrap(inner_html: str, unsub_url: str) -> str:
    return f"""<!doctype html><html><body style="margin:0;padding:0;background:#f4ebe1;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4ebe1;padding:24px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:16px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;">
  <tr><td style="background:#14100e;padding:22px 28px;">
    <span style="font-family:Arial,sans-serif;font-size:24px;font-weight:800;color:#ffffff;letter-spacing:-.5px;">Uno<span style="color:#EA4E1B;">X</span>due</span>
  </td></tr>
  <tr><td style="padding:28px 28px 8px 28px;color:#1a1411;font-size:15px;line-height:1.6;">{inner_html}</td></tr>
  <tr><td style="padding:20px 28px 28px 28px;">
    <hr style="border:none;border-top:1px solid #ecdfce;margin:0 0 16px 0;" />
    <p style="margin:0;color:#8a7a6c;font-size:12px;line-height:1.6;">
      Ricevi questa email perché ti sei iscritto alla newsletter di UnoXdue.<br/>
      <a href="{unsub_url}" style="color:#8a7a6c;">Annulla iscrizione</a> · <a href="{SITE_URL}/" style="color:#8a7a6c;">unoxdue.net</a>
    </p>
  </td></tr>
</table>
</td></tr></table></body></html>"""


def _button(label: str, url: str) -> str:
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:18px 0;"><tr>'
            f'<td style="background:#EA4E1B;border-radius:999px;">'
            f'<a href="{url}" style="display:inline-block;padding:13px 26px;color:#ffffff;font-weight:700;'
            f'font-size:14px;text-decoration:none;">{label}</a></td></tr></table>')


def render_episode(ep: dict, tmpl: dict):
    section = "interviste" if ep.get("type") == "intervista" else "episodi"
    url = f"{SITE_URL}/{section}/{ep.get('slug')}/"
    subject = (tmpl.get("subject") or DEFAULT_TEMPLATES["episode"]["subject"]).replace("{title}", ep.get("title", ""))
    intro = tmpl.get("intro") or DEFAULT_TEMPLATES["episode"]["intro"]
    thumb = ep.get("thumbnail")
    img = (f'<img src="{thumb}" alt="" width="544" style="width:100%;max-width:544px;border-radius:12px;margin:8px 0;" />'
           if thumb else "")
    excerpt = (ep.get("archive_excerpt") or ep.get("excerpt") or "")
    if len(excerpt) > 300:
        excerpt = excerpt[:297] + "…"
    inner = (f'<p style="margin:0 0 14px 0;">{intro}</p>{img}'
             f'<h2 style="margin:12px 0 8px 0;font-size:20px;color:#14100e;">{ep.get("title","")}</h2>'
             f'<p style="margin:0 0 4px 0;color:#4a3d34;">{excerpt}</p>'
             f'{_button("▶️ Guarda la puntata", url)}')
    if ep.get("youtube_id"):
        inner += f'<p style="margin:6px 0 0 0;font-size:13px;"><a href="https://youtu.be/{ep["youtube_id"]}" style="color:#EA4E1B;">Guarda su YouTube</a></p>'
    return subject, inner


def render_live(text: str, twitch: str, tmpl: dict):
    subject = tmpl.get("subject") or DEFAULT_TEMPLATES["live"]["subject"]
    intro = text or tmpl.get("intro") or DEFAULT_TEMPLATES["live"]["intro"]
    inner = (f'<p style="margin:0 0 8px 0;font-size:22px;font-weight:800;color:#EA4E1B;">🔴 Siamo LIVE ora!</p>'
             f'<p style="margin:0 0 6px 0;">{intro}</p>'
             f'{_button("🎮 Entra nella diretta", twitch or "https://www.twitch.tv/unoxdue_")}')
    return subject, inner


# ----------------------------- Invio (Resend) -----------------------------
def _api_ready():
    return bool(os.environ.get("RESEND_API_KEY"))


async def _sender():
    cfg = await get_config()
    name = cfg.get("from_name") or DEFAULT_FROM_NAME
    email = cfg.get("sender_email") or DEFAULT_SENDER
    return f"{name} <{email}>"


async def _send_one(to_email: str, subject: str, html: str) -> dict:
    resend.api_key = os.environ.get("RESEND_API_KEY")
    params = {"from": await _sender(), "to": [to_email], "subject": subject, "html": html}
    return await asyncio.to_thread(resend.Emails.send, params)


async def send_test(to_email: str, subject: str, inner_html: str) -> dict:
    if not _api_ready():
        return {"ok": False, "error": "RESEND_API_KEY non configurata"}
    if not EMAIL_RE.match(to_email or ""):
        return {"ok": False, "error": "Email di test non valida"}
    try:
        html = _wrap(inner_html, _unsub_url("test"))
        r = await _send_one(to_email, "[TEST] " + subject, html)
        return {"ok": True, "id": r.get("id")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def send_campaign(subject: str, inner_html: str, kind: str = "campaign") -> dict:
    if not _api_ready():
        return {"ok": False, "error": "RESEND_API_KEY non configurata"}
    subs = await db.subscribers.find({"status": "active"}, {"_id": 0, "email": 1, "unsub_token": 1}).to_list(100000)
    if not subs:
        return {"ok": False, "error": "Nessun iscritto attivo"}
    resend.api_key = os.environ.get("RESEND_API_KEY")
    sender = await _sender()
    sent, errors = 0, []
    for i in range(0, len(subs), 100):
        chunk = subs[i:i + 100]
        params = [{"from": sender, "to": [s["email"]], "subject": subject,
                   "html": _wrap(inner_html, _unsub_url(s.get("unsub_token", "")))} for s in chunk]
        try:
            await asyncio.to_thread(resend.Batch.send, params)
            sent += len(chunk)
        except Exception as e:
            errors.append(str(e))
    status = {"kind": kind, "subject": subject, "sent": sent, "total": len(subs),
              "errors": errors[:3], "at": datetime.now(timezone.utc).isoformat()}
    await db.settings.update_one({"_id": "global"}, {"$set": {"newsletter.status": status}}, upsert=True)
    return {"ok": len(errors) == 0, "sent": sent, "total": len(subs), "errors": errors[:3]}


async def notify_owner(subject: str, inner_html: str) -> dict:
    if not _api_ready():
        return {"ok": False, "error": "RESEND_API_KEY non configurata"}
    cfg = await get_config()
    owner = cfg.get("owner_email") or os.environ.get("ADMIN_EMAIL")
    if not owner:
        return {"ok": False, "error": "Email destinatario non configurata"}
    try:
        r = await _send_one(owner, subject, _wrap(inner_html, f"{SITE_URL}/"))
        return {"ok": True, "id": r.get("id")}
    except Exception as e:
        logger.warning("notify_owner: %s", e)
        return {"ok": False, "error": str(e)}


# ----------------------------- Resolve (per admin) -----------------------------
async def resolve(kind: str, slug: str = None, text: str = None, subject: str = None, html: str = None):
    cfg = await get_config()
    templates = {**{k: dict(v) for k, v in DEFAULT_TEMPLATES.items()}, **(cfg.get("templates") or {})}
    if kind == "episode":
        ep = await db.episodes.find_one({"slug": slug}, {"_id": 0})
        if not ep:
            return None, None, "Episodio non trovato"
        s, inner = render_episode(ep, templates["episode"])
        return s, inner, None
    if kind == "live":
        s, inner = render_live(text, cfg.get("twitch_url") or "https://www.twitch.tv/unoxdue_", templates["live"])
        return s, inner, None
    if kind == "generic":
        if not subject or not html:
            return None, None, "Oggetto e contenuto obbligatori"
        return subject, html, None
    return None, None, "Tipo non valido"


# ----------------------------- Auto hook -----------------------------
async def maybe_autosend_episode(slug: str):
    try:
        cfg = await get_config()
        if not (cfg.get("enabled") and cfg.get("auto_episode") and _api_ready()):
            return
        ep = await db.episodes.find_one({"slug": slug}, {"_id": 0})
        if not ep or ep.get("status") != "pubblicato" or ep.get("newsletter_sent"):
            return
        s, inner, err = await resolve("episode", slug=slug)
        if err:
            return
        r = await send_campaign(s, inner, kind="episode")
        if r.get("ok") or r.get("sent"):
            await db.episodes.update_one({"slug": slug}, {"$set": {"newsletter_sent": datetime.now(timezone.utc).isoformat()}})
    except Exception as e:
        logger.warning("maybe_autosend_episode(%s): %s", slug, e)
