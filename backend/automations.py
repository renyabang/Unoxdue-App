"""Automazioni: YouTube sync (feed RSS), OCR schedine (OpenAI Vision via Emergent),
connettore quote e connettore rassegna stampa. Connettori con MODALITA' DEMO
chiara quando mancano le credenziali. Logging di ogni operazione.
"""
import re
import json
import base64
import uuid
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests

from config_db import (
    db, EMERGENT_LLM_KEY, VISION_MODEL, YOUTUBE_CHANNEL_ID, YOUTUBE_API_KEY,
    ODDS_API_URL, ODDS_API_KEY, ODDS_API_PROVIDER, PERPLEXITY_API_KEY,
)

# ----------------------- helpers -----------------------

def slugify(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")[:80] or uuid.uuid4().hex[:8]


def compute_season(dt: datetime) -> str:
    """Serie A: ago-dic -> anno/anno+1; gen-lug -> anno-1/anno."""
    y = dt.year
    if dt.month >= 8:
        return f"{y}-{y+1}"
    return f"{y-1}-{y}"


async def log_automation(kind: str, status: str, message: str, meta: dict = None):
    doc = {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "status": status,  # ok | error | warning | info
        "message": message,
        "meta": meta or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.automation_logs.insert_one(dict(doc))
    except Exception:
        pass
    return doc


def classify_video(title: str, description: str, seconds: int = 0) -> str:
    t = f"{title} {description}".lower()
    if "intervista" in t or "intervist" in t:
        return "intervista"
    if "#shorts" in t or (0 < seconds <= 90):
        return "short"
    return "episodio"


# ----------------------- YouTube sync (RSS feed) -----------------------
YT_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def _fetch_feed_sync(channel_id: str):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    r = requests.get(url, timeout=15, headers={"User-Agent": "UnoXdueBot/1.0"})
    r.raise_for_status()
    return r.text


async def youtube_sync(channel_id: str = None, auto_publish: bool = True) -> dict:
    channel_id = channel_id or YOUTUBE_CHANNEL_ID
    if not channel_id:
        await log_automation("youtube_sync", "error", "Channel ID mancante")
        return {"ok": False, "error": "YOUTUBE_CHANNEL_ID non configurato"}
    try:
        xml_text = await asyncio.get_event_loop().run_in_executor(None, _fetch_feed_sync, channel_id)
    except Exception as e:
        await log_automation("youtube_sync", "error", f"Feed non raggiungibile: {e}")
        return {"ok": False, "error": str(e)}

    root = ET.fromstring(xml_text)
    entries = root.findall("atom:entry", YT_NS)
    found, created, updated, skipped = 0, 0, 0, 0
    for entry in entries:
        found += 1
        vid = entry.find("yt:videoId", YT_NS)
        title_el = entry.find("atom:title", YT_NS)
        pub_el = entry.find("atom:published", YT_NS)
        group = entry.find("media:group", YT_NS)
        desc = ""
        if group is not None:
            d = group.find("media:description", YT_NS)
            if d is not None and d.text:
                desc = d.text
        if vid is None or title_el is None:
            continue
        youtube_id = vid.text
        title = (title_el.text or "").strip()
        published = pub_el.text[:10] if pub_el is not None and pub_el.text else None
        kind = classify_video(title, desc)
        if kind == "short":
            skipped += 1
            continue
        slug = slugify(title)
        existing = await db.episodes.find_one({"youtube_id": youtube_id})
        doc = {
            "slug": existing["slug"] if existing else slug,
            "type": existing.get("type") if existing else kind,
            "title": title,
            "youtube_id": youtube_id,
            "published_at": published,
            "thumbnail": f"https://img.youtube.com/vi/{youtube_id}/maxresdefault.jpg",
            "excerpt": (desc[:240] if desc else title),
            "source": "youtube_feed",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        # contenuto incompleto -> da verificare
        if not desc or len(desc) < 20:
            doc["status"] = "da_verificare"
        else:
            doc["status"] = "pubblicato" if auto_publish else "bozza"
        if existing:
            await db.episodes.update_one({"youtube_id": youtube_id}, {"$set": doc})
            updated += 1
        else:
            doc["created_at"] = doc["updated_at"]
            await db.episodes.insert_one(dict(doc))
            created += 1
    summary = {"ok": True, "found": found, "created": created, "updated": updated, "skipped_shorts": skipped}
    await log_automation("youtube_sync", "ok", f"Sync completato: {created} nuovi, {updated} aggiornati", summary)
    return summary


# ----------------------- OCR schedine (OpenAI Vision via Emergent) -----------------------
SENSITIVE_KEYS = {"importo", "puntata", "bonus", "vincita", "saldo", "stake", "payout", "winnings", "balance"}

OCR_PROMPT = (
    "Sei un estrattore di dati da schedine di scommesse sportive. "
    "Analizza l'immagine ed estrai SOLO i dati sportivi in JSON valido. "
    "IGNORA e NON includere: importo giocato, puntata, bonus, vincita potenziale, "
    "saldo, dati personali, numeri identificativi e il logo/branding dell'operatore. "
    "Restituisci esclusivamente questo JSON: "
    '{"type": "Multipla|Singola", "selections": [{"competition": "", "date": "", "match": "", "market": "", "pick": "", "odds": ""}], "total_odds": ""}. '
    "Non aggiungere testo prima o dopo il JSON."
)


def _strip_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


async def ocr_slip(image_bytes: bytes, mime: str = "image/jpeg") -> dict:
    if not EMERGENT_LLM_KEY:
        return {"ok": False, "demo": True, "error": "EMERGENT_LLM_KEY non configurata"}
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"ocr-{uuid.uuid4().hex[:8]}",
            system_message="Estrai dati strutturati da immagini di schedine. Rispondi solo con JSON.",
        ).with_model("openai", VISION_MODEL)
        msg = UserMessage(text=OCR_PROMPT, file_contents=[ImageContent(image_base64=b64)])
        resp = await chat.send_message(msg)
        raw = resp if isinstance(resp, str) else str(resp)
        data = json.loads(_strip_json(raw))
        # sanitizzazione difensiva
        for sel in data.get("selections", []):
            for k in list(sel.keys()):
                if k.lower() in SENSITIVE_KEYS:
                    sel.pop(k, None)
        data.pop("importo", None)
        data.pop("bonus", None)
        data.pop("vincita", None)
        await log_automation("ocr_slip", "ok", f"Estratte {len(data.get('selections', []))} selezioni")
        return {"ok": True, "data": data}
    except json.JSONDecodeError as e:
        await log_automation("ocr_slip", "error", f"JSON non valido dall'OCR: {e}")
        return {"ok": False, "error": "Risposta OCR non interpretabile", "raw": raw if 'raw' in dir() else ""}
    except Exception as e:
        await log_automation("ocr_slip", "error", f"OCR fallito: {e}")
        return {"ok": False, "error": str(e)}


# ----------------------- Connettore quote (astratto, demo mode) -----------------------
async def get_odds(match: str, market: str, pick: str) -> dict:
    """Recupera la quota dal comparatore. Demo se non configurato."""
    if not (ODDS_API_URL and ODDS_API_KEY):
        return {"ok": True, "demo": True, "provider": ODDS_API_PROVIDER or "demo",
                "odds": None, "note": "Connettore quote in modalita' demo: nessuna quota reale."}
    try:
        def _call():
            r = requests.get(ODDS_API_URL, params={"match": match, "market": market, "pick": pick},
                             headers={"Authorization": f"Bearer {ODDS_API_KEY}"}, timeout=12)
            r.raise_for_status()
            return r.json()
        data = await asyncio.get_event_loop().run_in_executor(None, _call)
        return {"ok": True, "demo": False, "provider": ODDS_API_PROVIDER, "data": data,
                "updated_at": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        await log_automation("odds", "error", f"Quote non disponibili: {e}")
        return {"ok": False, "error": str(e)}


# ----------------------- Connettore rassegna stampa (Perplexity, demo) -----------------------
async def search_press(query: str = "UnoXdue podcast") -> dict:
    if not PERPLEXITY_API_KEY:
        return {"ok": True, "demo": True,
                "note": "Connettore rassegna stampa in modalita' demo: nessuna ricerca reale.",
                "results": []}
    try:
        def _call():
            r = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"},
                json={"model": "sonar", "messages": [{"role": "user",
                       "content": f"Trova articoli recenti che menzionano '{query}'. Restituisci testata, titolo, url, data."}]},
                timeout=25,
            )
            r.raise_for_status()
            return r.json()
        data = await asyncio.get_event_loop().run_in_executor(None, _call)
        await log_automation("press", "ok", "Ricerca rassegna stampa completata")
        return {"ok": True, "demo": False, "raw": data}
    except Exception as e:
        await log_automation("press", "error", f"Ricerca stampa fallita: {e}")
        return {"ok": False, "error": str(e)}
