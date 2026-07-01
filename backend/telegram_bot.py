"""Integrazione Telegram Bot API — pubblicazione sul canale UnoXdue.

Solo outbound (niente webhook): il bot pubblica messaggi/foto/sondaggi sul canale.
Token e canale sono salvati in db.settings._id="global" sotto la chiave "telegram"
(mai rimostrati in chiaro nella UI: la API li ritorna mascherati).
"""
import html
import logging
import uuid
from datetime import datetime, timezone

import httpx

from config_db import db, SITE_URL

logger = logging.getLogger("uvicorn.error")
API = "https://api.telegram.org"

# Modelli messaggio di default (HTML parse_mode). Tutti modificabili dall'admin.
DEFAULT_TEMPLATES = {
    "episode": (
        "🎙️ <b>NUOVA PUNTATA — UnoXdue</b>\n\n"
        "«{title}»\n\n"
        "{excerpt}\n\n"
        "▶️ Ascolta/Guarda: {url}\n"
        "📺 Su YouTube: {youtube}\n\n"
        "#UnoXdue #SerieA #Podcast"
    ),
    "live": (
        "🔴 <b>SIAMO LIVE ORA!</b>\n\n"
        "{text}\n\n"
        "🎮 Entra qui 👉 {twitch}\n"
        "Ti aspettiamo in chat!\n\n"
        "#UnoXdue #Live"
    ),
    "prediction": (
        "🎯 <b>PRONOSTICO — {tipster}</b>\n"
        "🏆 {competition} · Giornata {round}\n\n"
        "{selections}\n\n"
        "💰 Quota totale: {total_odds}\n\n"
        "📊 Analisi completa: {url}\n\n"
        "⚠️ Contenuto informativo. Gioco responsabile. Solo +18.\n"
        "#UnoXdue #SerieA #Pronostici"
    ),
}

DEFAULT_LIVE_TEXT = "Commentiamo in diretta la giornata di Serie A. Pronostici, analisi e tanto altro."
DEFAULT_TWITCH = "https://www.twitch.tv/unoxdue_"


class _SafeDict(dict):
    def __missing__(self, key):
        return ""


def _esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=False)


def _fmt(template: str, **kw) -> str:
    try:
        return template.format_map(_SafeDict(**kw))
    except Exception:
        return template


# ----------------------------- Config -----------------------------
async def get_config() -> dict:
    s = await db.settings.find_one({"_id": "global"}, {"_id": 0, "telegram": 1}) or {}
    return s.get("telegram") or {}


def _mask(token: str) -> str:
    if not token:
        return ""
    if len(token) <= 12:
        return "•••"
    return f"{token[:6]}…{token[-4:]}"


async def admin_config_view() -> dict:
    cfg = await get_config()
    token = cfg.get("bot_token") or ""
    templates = {**DEFAULT_TEMPLATES, **(cfg.get("templates") or {})}
    return {
        "configured": bool(token and cfg.get("channel_id")),
        "token_set": bool(token),
        "token_masked": _mask(token),
        "channel_id": cfg.get("channel_id", ""),
        "twitch_url": cfg.get("twitch_url", "") or DEFAULT_TWITCH,
        "notify_chat_id": cfg.get("notify_chat_id", ""),
        "enabled": bool(cfg.get("enabled", False)),
        "auto_episode": bool(cfg.get("auto_episode", False)),
        "auto_prediction": bool(cfg.get("auto_prediction", False)),
        "templates": templates,
        "default_templates": DEFAULT_TEMPLATES,
        "status": cfg.get("status") or {},
    }


async def save_config(data: dict) -> dict:
    patch = {}
    # token: aggiorna solo se fornito uno nuovo (non il placeholder mascherato)
    token = (data.get("bot_token") or "").strip()
    if token and "…" not in token and "•" not in token:
        patch["telegram.bot_token"] = token
    if "channel_id" in data:
        patch["telegram.channel_id"] = (data.get("channel_id") or "").strip()
    if "twitch_url" in data:
        patch["telegram.twitch_url"] = (data.get("twitch_url") or "").strip()
    if "notify_chat_id" in data:
        patch["telegram.notify_chat_id"] = (data.get("notify_chat_id") or "").strip()
    if "enabled" in data:
        patch["telegram.enabled"] = bool(data.get("enabled"))
    if "auto_episode" in data:
        patch["telegram.auto_episode"] = bool(data.get("auto_episode"))
    if "auto_prediction" in data:
        patch["telegram.auto_prediction"] = bool(data.get("auto_prediction"))
    if isinstance(data.get("templates"), dict):
        clean = {k: v for k, v in data["templates"].items() if k in DEFAULT_TEMPLATES}
        patch["telegram.templates"] = clean
    if patch:
        await db.settings.update_one({"_id": "global"}, {"$set": patch}, upsert=True)
    return await admin_config_view()


# ----------------------------- Telegram API -----------------------------
async def _call(method: str, payload: dict, token: str) -> dict:
    if not token:
        raise RuntimeError("Token Telegram non configurato")
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{API}/bot{token}/{method}", json=payload)
    try:
        data = r.json()
    except Exception:
        raise RuntimeError(f"Risposta non valida da Telegram (HTTP {r.status_code})")
    if not data.get("ok"):
        raise RuntimeError(data.get("description") or f"Errore Telegram (HTTP {r.status_code})")
    return data.get("result", {})


async def _log(kind: str, text: str, ok: bool, error: str = None, result: dict = None):
    try:
        await db.telegram_messages.insert_one({
            "id": str(uuid.uuid4()),
            "kind": kind,
            "text": (text or "")[:1200],
            "ok": ok,
            "error": error,
            "message_id": (result or {}).get("message_id"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass


async def test_connection() -> dict:
    cfg = await get_config()
    token = cfg.get("bot_token")
    channel = cfg.get("channel_id")
    out = {"ok": False, "bot": None, "channel": None, "can_post": None, "error": None}
    try:
        me = await _call("getMe", {}, token)
        out["bot"] = {"id": me.get("id"), "username": me.get("username"), "name": me.get("first_name")}
        if channel:
            chat = await _call("getChat", {"chat_id": channel}, token)
            out["channel"] = {"title": chat.get("title"), "type": chat.get("type"), "username": chat.get("username")}
            try:
                member = await _call("getChatMember", {"chat_id": channel, "user_id": me.get("id")}, token)
                st = member.get("status")
                if st == "creator":
                    out["can_post"] = True
                elif st == "administrator":
                    out["can_post"] = bool(member.get("can_post_messages", True))
                else:
                    out["can_post"] = False
            except Exception:
                out["can_post"] = None
        out["ok"] = True
    except Exception as e:
        out["error"] = str(e)
    await db.settings.update_one(
        {"_id": "global"},
        {"$set": {"telegram.status": {**out, "checked_at": datetime.now(timezone.utc).isoformat()}}},
        upsert=True,
    )
    return out


async def _send_message(text: str, token: str, channel: str, disable_preview: bool = False) -> dict:
    return await _call("sendMessage", {
        "chat_id": channel, "text": text, "parse_mode": "HTML",
        "disable_web_page_preview": disable_preview,
    }, token)


async def _send_photo(photo_url: str, caption: str, token: str, channel: str) -> dict:
    cap = caption if len(caption) <= 1024 else caption[:1021] + "…"
    return await _call("sendPhoto", {
        "chat_id": channel, "photo": photo_url, "caption": cap, "parse_mode": "HTML",
    }, token)


async def _send_photo_or_text(photo_url, text, token, channel) -> dict:
    """Prova con foto; se Telegram rifiuta l'immagine (es. webp/URL non scaricabile),
    ripiega sul messaggio di solo testo (con anteprima link)."""
    if photo_url:
        try:
            return await _send_photo(photo_url, text, token, channel)
        except Exception as e:
            logger.warning("Telegram sendPhoto fallita (%s), fallback testo", e)
    return await _send_message(text, token, channel)


# ----------------------------- Rendering -----------------------------
def render_episode(ep: dict, template: str) -> str:
    section = "interviste" if ep.get("type") == "intervista" else "episodi"
    url = f"{SITE_URL}/{section}/{ep.get('slug')}/"
    yid = ep.get("youtube_id")
    youtube = f"https://youtu.be/{yid}" if yid else ""
    excerpt = (ep.get("archive_excerpt") or ep.get("excerpt") or "")
    if len(excerpt) > 300:
        excerpt = excerpt[:297] + "…"
    return _fmt(template, title=_esc(ep.get("title")), excerpt=_esc(excerpt),
                url=url, youtube=youtube)


def render_prediction(pred: dict, pick: dict, template: str) -> str:
    url = f"{SITE_URL}/pronostici/serie-a/{pred.get('season')}/giornata-{pred.get('round')}/"
    lines = []
    for s in pick.get("selections", []):
        match = s.get("match") or s.get("event") or ""
        market = s.get("market") or ""
        sel = s.get("pick") or s.get("selection") or ""
        odds = s.get("odds") or ""
        part = "• " + _esc(match)
        bits = []
        if market:
            bits.append(_esc(market))
        if sel:
            bits.append(_esc(sel))
        if bits:
            part += " → " + ": ".join(bits)
        if odds:
            part += f" @ {_esc(odds)}"
        lines.append(part)
    return _fmt(template, tipster=_esc(pick.get("tipster")),
                competition=_esc(pred.get("competition") or "Serie A"),
                round=_esc(pred.get("round")), selections="\n".join(lines),
                total_odds=_esc(pick.get("total_odds") or "—"), url=url)


def render_live(text: str, twitch: str, template: str) -> str:
    return _fmt(template, text=_esc(text or DEFAULT_LIVE_TEXT), twitch=twitch or DEFAULT_TWITCH)


def _prediction_photo(pred: dict, pick: dict):
    g = (pick.get("graphics") or {}).get("formats") or {}
    for fmt in ("square", "vertical", "horizontal"):
        if g.get(fmt):
            return g[fmt].get("png") or g[fmt].get("webp")
    cov = (pred.get("cover") or {}).get("formats") or {}
    for fmt in ("square", "horizontal", "thumb"):
        if cov.get(fmt) and cov[fmt].get("url"):
            return cov[fmt]["url"]
    return None


# ----------------------------- Preview (admin) -----------------------------
async def preview(kind: str, slug: str = None, season: str = None, round_: int = None,
                  pick_index: int = 0, text: str = None) -> dict:
    cfg = await get_config()
    templates = {**DEFAULT_TEMPLATES, **(cfg.get("templates") or {})}
    if kind == "episode":
        ep = await db.episodes.find_one({"slug": slug}, {"_id": 0})
        if not ep:
            return {"ok": False, "error": "Contenuto non trovato"}
        return {"ok": True, "text": render_episode(ep, templates["episode"]), "photo": ep.get("thumbnail")}
    if kind == "prediction":
        pred = await db.predictions.find_one({"season": season, "round": int(round_)}, {"_id": 0})
        if not pred or not pred.get("picks"):
            return {"ok": False, "error": "Pronostico o giocate non trovati"}
        idx = max(0, min(int(pick_index), len(pred["picks"]) - 1))
        pick = pred["picks"][idx]
        return {"ok": True, "text": render_prediction(pred, pick, templates["prediction"]),
                "photo": _prediction_photo(pred, pick)}
    if kind == "live":
        return {"ok": True, "text": render_live(text, cfg.get("twitch_url"), templates["live"]), "photo": None}
    return {"ok": False, "error": "Tipo non valido"}


# ----------------------------- Publish (manuale + auto) -----------------------------
async def _ready():
    cfg = await get_config()
    if not (cfg.get("bot_token") and cfg.get("channel_id")):
        return None, None, None
    return cfg, cfg["bot_token"], cfg["channel_id"]


async def publish_episode(slug: str) -> dict:
    cfg, token, channel = await _ready()
    if not token:
        return {"ok": False, "error": "Telegram non configurato (token o canale mancante)"}
    ep = await db.episodes.find_one({"slug": slug}, {"_id": 0})
    if not ep:
        return {"ok": False, "error": "Episodio non trovato"}
    templates = {**DEFAULT_TEMPLATES, **(cfg.get("templates") or {})}
    text = render_episode(ep, templates["episode"])
    try:
        res = await _send_photo_or_text(ep.get("thumbnail"), text, token, channel)
        await _log("episode", text, True, result=res)
        return {"ok": True, "message_id": res.get("message_id")}
    except Exception as e:
        await _log("episode", text, False, error=str(e))
        return {"ok": False, "error": str(e)}


async def publish_prediction(season: str, round_: int, pick_index: int = 0) -> dict:
    cfg, token, channel = await _ready()
    if not token:
        return {"ok": False, "error": "Telegram non configurato (token o canale mancante)"}
    pred = await db.predictions.find_one({"season": season, "round": int(round_)}, {"_id": 0})
    if not pred or not pred.get("picks"):
        return {"ok": False, "error": "Pronostico o giocate non trovati"}
    idx = max(0, min(int(pick_index), len(pred["picks"]) - 1))
    pick = pred["picks"][idx]
    templates = {**DEFAULT_TEMPLATES, **(cfg.get("templates") or {})}
    text = render_prediction(pred, pick, templates["prediction"])
    photo = _prediction_photo(pred, pick)
    try:
        res = await _send_photo_or_text(photo, text, token, channel)
        await _log("prediction", text, True, result=res)
        return {"ok": True, "message_id": res.get("message_id")}
    except Exception as e:
        await _log("prediction", text, False, error=str(e))
        return {"ok": False, "error": str(e)}


async def publish_live(text: str = None) -> dict:
    cfg, token, channel = await _ready()
    if not token:
        return {"ok": False, "error": "Telegram non configurato (token o canale mancante)"}
    templates = {**DEFAULT_TEMPLATES, **(cfg.get("templates") or {})}
    msg = render_live(text, cfg.get("twitch_url"), templates["live"])
    try:
        res = await _send_message(msg, token, channel)
        await _log("live", msg, True, result=res)
        return {"ok": True, "message_id": res.get("message_id")}
    except Exception as e:
        await _log("live", msg, False, error=str(e))
        return {"ok": False, "error": str(e)}


async def publish_poll(question: str, options: list) -> dict:
    cfg, token, channel = await _ready()
    if not token:
        return {"ok": False, "error": "Telegram non configurato (token o canale mancante)"}
    opts = [o.strip() for o in (options or []) if o and o.strip()][:10]
    if not question or not question.strip():
        return {"ok": False, "error": "Domanda mancante"}
    if len(opts) < 2:
        return {"ok": False, "error": "Servono almeno 2 opzioni"}
    try:
        res = await _call("sendPoll", {
            "chat_id": channel, "question": question.strip()[:300],
            "options": [o[:100] for o in opts], "is_anonymous": True,
        }, token)
        await _log("poll", question, True, result=res)
        return {"ok": True, "message_id": res.get("message_id")}
    except Exception as e:
        await _log("poll", question, False, error=str(e))
        return {"ok": False, "error": str(e)}


async def send_test() -> dict:
    cfg, token, channel = await _ready()
    if not token:
        return {"ok": False, "error": "Telegram non configurato (token o canale mancante)"}
    msg = "✅ <b>UnoXdue Bot</b> collegato correttamente.\nQuesto è un messaggio di prova dal pannello admin."
    try:
        res = await _send_message(msg, token, channel)
        await _log("test", msg, True, result=res)
        return {"ok": True, "message_id": res.get("message_id")}
    except Exception as e:
        await _log("test", msg, False, error=str(e))
        return {"ok": False, "error": str(e)}


async def recent_messages(limit: int = 20) -> list:
    return await db.telegram_messages.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)


async def get_updates() -> dict:
    """Legge gli ultimi update del bot per ricavare i chat_id (utile per configurare le notifiche)."""
    cfg = await get_config()
    token = cfg.get("bot_token")
    if not token:
        return {"ok": False, "error": "Token Telegram non configurato", "chats": []}
    try:
        updates = await _call("getUpdates", {"limit": 50, "timeout": 0}, token)
    except Exception as e:
        return {"ok": False, "error": str(e), "chats": []}
    seen, chats = set(), []
    for u in updates:
        for key in ("message", "channel_post", "my_chat_member", "edited_message"):
            obj = u.get(key)
            chat = (obj or {}).get("chat")
            if chat and chat.get("id") not in seen:
                seen.add(chat.get("id"))
                title = chat.get("title") or " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")])) or chat.get("username") or ""
                chats.append({"id": chat.get("id"), "title": title, "type": chat.get("type")})
    return {"ok": True, "chats": chats}


async def notify_lead(text: str) -> dict:
    """Invia una notifica (es. nuovo lead sponsor) alla chat privata/gruppo configurata."""
    cfg = await get_config()
    token = cfg.get("bot_token")
    chat = cfg.get("notify_chat_id")
    if not (token and chat):
        return {"ok": False, "error": "Chat notifiche non configurata"}
    try:
        res = await _call("sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML",
                                          "disable_web_page_preview": True}, token)
        await _log("notify", text, True, result=res)
        return {"ok": True, "message_id": res.get("message_id")}
    except Exception as e:
        await _log("notify", text, False, error=str(e))
        return {"ok": False, "error": str(e)}


# ----------------------------- Auto hooks (non bloccanti) -----------------------------
async def maybe_autopost_episode(slug: str):
    try:
        cfg = await get_config()
        if not (cfg.get("enabled") and cfg.get("auto_episode") and cfg.get("bot_token") and cfg.get("channel_id")):
            return
        ep = await db.episodes.find_one({"slug": slug}, {"_id": 0})
        if not ep or ep.get("status") != "pubblicato" or ep.get("telegram_posted"):
            return
        r = await publish_episode(slug)
        if r.get("ok"):
            await db.episodes.update_one({"slug": slug}, {"$set": {"telegram_posted": datetime.now(timezone.utc).isoformat()}})
    except Exception as e:
        logger.warning("maybe_autopost_episode(%s): %s", slug, e)


async def maybe_autopost_prediction(season: str, round_: int, tipster: str = None):
    try:
        cfg = await get_config()
        if not (cfg.get("enabled") and cfg.get("auto_prediction") and cfg.get("bot_token") and cfg.get("channel_id")):
            return
        pred = await db.predictions.find_one({"season": season, "round": int(round_)}, {"_id": 0})
        if not pred or pred.get("status") != "pubblicato" or not pred.get("picks"):
            return
        posted = set(pred.get("telegram_posted_picks") or [])
        for idx, pick in enumerate(pred["picks"]):
            tname = pick.get("tipster") or f"#{idx}"
            if tipster and tname != tipster:
                continue
            if tname in posted:
                continue
            r = await publish_prediction(season, int(round_), idx)
            if r.get("ok"):
                posted.add(tname)
        await db.predictions.update_one(
            {"season": season, "round": int(round_)},
            {"$set": {"telegram_posted_picks": list(posted)}},
        )
    except Exception as e:
        logger.warning("maybe_autopost_prediction(%s,%s): %s", season, round_, e)
