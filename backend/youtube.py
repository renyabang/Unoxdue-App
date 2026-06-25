"""Step 3 — Archivio YouTube completo via Data API v3, WebSub (PubSubHubbub)
e trascrizioni via OAuth. Tutto in MODALITA' DEMO chiara quando mancano le credenziali.

Regole rispettate:
- NESSUNA trascrizione/citazione inventata: senza sottotitoli reali transcription_status resta 'pending'.
- Senza YOUTUBE_API_KEY il backfill completo NON e' possibile: si ripiega sul feed RSS (dati reali ma
  limitati ai video recenti) marcando il risultato come demo.
- I segreti restano nelle variabili ambiente: mai in chiaro nei log/risposte.
"""
import re
import hmac
import hashlib
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import requests

from config_db import (
    db, SITE_URL, YOUTUBE_CHANNEL_ID, YOUTUBE_API_KEY,
    GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REFRESH_TOKEN,
    WEBSUB_HUB, WEBSUB_SECRET,
)
from automations import classify_video, slugify, log_automation

ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}
OAUTH_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"


# ----------------------- helpers durata -----------------------
def parse_iso_duration(s: str) -> int:
    """ISO 8601 (PT1H2M3S) -> secondi."""
    m = re.match(r"P(?:\d+D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return 0
    h, mi, se = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + se


def human_duration(sec: int) -> str:
    sec = int(sec or 0)
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ----------------------- Data API v3 (sync, wrappato in executor) -----------------------
def _service():
    from googleapiclient.discovery import build
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY, cache_discovery=False)


def _channel_info_sync():
    yt = _service()
    resp = yt.channels().list(part="snippet,statistics,contentDetails", id=YOUTUBE_CHANNEL_ID).execute()
    items = resp.get("items", [])
    if not items:
        return None
    it = items[0]
    thumbs = it["snippet"].get("thumbnails", {})
    thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url")
    return {
        "channel_id": YOUTUBE_CHANNEL_ID,
        "title": it["snippet"].get("title"),
        "uploads_playlist": it["contentDetails"]["relatedPlaylists"]["uploads"],
        "subscriber_count": int(it["statistics"].get("subscriberCount", 0)),
        "view_count": int(it["statistics"].get("viewCount", 0)),
        "video_count": int(it["statistics"].get("videoCount", 0)),
        "thumbnail": thumb,
    }


def _list_uploads_sync(uploads_playlist: str, page_token: str = None):
    yt = _service()
    return yt.playlistItems().list(
        part="snippet", playlistId=uploads_playlist, maxResults=50, pageToken=page_token
    ).execute()


def _video_details_sync(ids):
    yt = _service()
    return yt.videos().list(part="contentDetails,status", id=",".join(ids)).execute()


# ----------------------- channel stats -----------------------
async def channel_stats() -> dict:
    imported = await db.episodes.count_documents({})
    if not YOUTUBE_API_KEY:
        return {
            "ok": True, "demo": True, "channel_id": YOUTUBE_CHANNEL_ID, "imported": imported,
            "video_count": None, "subscriber_count": None, "view_count": None, "title": None,
            "note": "Statistiche reali del canale richiedono YOUTUBE_API_KEY (Google Cloud Console).",
        }
    try:
        info = await asyncio.get_event_loop().run_in_executor(None, _channel_info_sync)
    except Exception as e:
        await log_automation("youtube_stats", "error", f"channels.list fallita: {e}")
        return {"ok": False, "error": str(e)}
    if not info:
        return {"ok": False, "error": "Canale non trovato"}
    info.update({"ok": True, "demo": False, "imported": imported})
    return info


# ----------------------- upsert singolo video (riusato da backfill e WebSub) -----------------------
async def _upsert_video(youtube_id, title, desc, published, seconds, auto_publish=True, source="youtube_api"):
    kind = classify_video(title, desc, seconds)
    if kind == "short":
        return {"action": "skipped_short", "youtube_id": youtube_id}
    existing = await db.episodes.find_one({"youtube_id": youtube_id})
    doc = {
        "slug": existing["slug"] if existing else slugify(title),
        "type": existing.get("type") if existing else kind,
        "title": title,
        "youtube_id": youtube_id,
        "published_at": published,
        "thumbnail": f"https://img.youtube.com/vi/{youtube_id}/maxresdefault.jpg",
        "excerpt": (desc[:240] if desc else (existing.get("excerpt") if existing else title)),
        "source": source,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if seconds:
        doc["duration"] = human_duration(seconds)
        doc["duration_seconds"] = seconds
    if existing:
        await db.episodes.update_one({"youtube_id": youtube_id}, {"$set": doc})
        return {"action": "updated", "slug": doc["slug"]}
    # nuovo contenuto
    if not desc or len(desc) < 20:
        doc["status"] = "da_verificare"
    else:
        doc["status"] = "pubblicato" if auto_publish else "bozza"
    doc["transcription_status"] = "pending"
    doc["created_at"] = doc["updated_at"]
    await db.episodes.insert_one(dict(doc))
    return {"action": "created", "slug": doc["slug"]}


# ----------------------- backfill completo -----------------------
async def backfill(max_pages: int = 40, auto_publish: bool = True) -> dict:
    if not YOUTUBE_API_KEY:
        import automations as auto
        res = await auto.youtube_sync(auto_publish=auto_publish)
        res["demo"] = True
        res["note"] = ("Backfill completo dell'archivio richiede YOUTUBE_API_KEY. "
                       "In modalita' demo importati solo i video recenti dal feed RSS.")
        await log_automation("youtube_backfill", "warning", "Backfill in DEMO (feed RSS)", res)
        return res

    loop = asyncio.get_event_loop()
    try:
        info = await loop.run_in_executor(None, _channel_info_sync)
    except Exception as e:
        await log_automation("youtube_backfill", "error", f"channels.list fallita: {e}")
        return {"ok": False, "error": str(e)}
    if not info:
        return {"ok": False, "error": "Canale non trovato"}

    uploads = info["uploads_playlist"]
    items, pages, page_token = [], 0, None
    while True:
        pages += 1
        try:
            resp = await loop.run_in_executor(None, _list_uploads_sync, uploads, page_token)
        except Exception as e:
            await log_automation("youtube_backfill", "error", f"playlistItems.list fallita (pagina {pages}): {e}")
            break
        for it in resp.get("items", []):
            sn = it.get("snippet", {})
            vid = sn.get("resourceId", {}).get("videoId")
            if not vid:
                continue
            items.append({
                "id": vid,
                "title": (sn.get("title") or "").strip(),
                "desc": sn.get("description") or "",
                "published": (sn.get("publishedAt") or "")[:10] or None,
            })
        page_token = resp.get("nextPageToken")
        if not page_token or pages >= max_pages:
            break

    # durate in batch da 50
    dur_map = {}
    for i in range(0, len(items), 50):
        chunk = [x["id"] for x in items[i:i + 50]]
        try:
            dresp = await loop.run_in_executor(None, _video_details_sync, chunk)
            for d in dresp.get("items", []):
                dur_map[d["id"]] = parse_iso_duration(d.get("contentDetails", {}).get("duration", ""))
        except Exception as e:
            await log_automation("youtube_backfill", "warning", f"videos.list fallita (chunk): {e}")

    created = updated = skipped = 0
    for x in items:
        r = await _upsert_video(x["id"], x["title"], x["desc"], x["published"], dur_map.get(x["id"], 0), auto_publish)
        a = r.get("action")
        created += a == "created"
        updated += a == "updated"
        skipped += a == "skipped_short"

    summary = {"ok": True, "demo": False, "channel_video_count": info["video_count"],
               "fetched": len(items), "pages": pages, "created": created,
               "updated": updated, "skipped_shorts": skipped}
    await log_automation("youtube_backfill", "ok",
                         f"Backfill completato: {created} nuovi, {updated} aggiornati, {skipped} short saltati", summary)
    return summary


# ----------------------- WebSub / PubSubHubbub -----------------------
def _topic_url(channel_id: str) -> str:
    return f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}"


def _callback_url() -> str:
    return f"{SITE_URL}/api/youtube/websub/callback"


def _secret() -> str:
    return WEBSUB_SECRET or "uxd-websub-secret"


async def websub_subscribe(mode: str = "subscribe") -> dict:
    if not YOUTUBE_CHANNEL_ID:
        return {"ok": False, "error": "YOUTUBE_CHANNEL_ID mancante"}
    topic, callback = _topic_url(YOUTUBE_CHANNEL_ID), _callback_url()
    data = {
        "hub.callback": callback, "hub.topic": topic, "hub.verify": "async",
        "hub.mode": mode, "hub.secret": _secret(), "hub.lease_seconds": "432000",
    }

    def _post():
        r = requests.post(WEBSUB_HUB, data=data, timeout=15)
        return r.status_code, r.text[:300]

    try:
        status, text = await asyncio.get_event_loop().run_in_executor(None, _post)
    except Exception as e:
        await log_automation("websub", "error", f"Richiesta {mode} fallita: {e}")
        return {"ok": False, "error": str(e)}

    ok = status in (202, 204)
    await db.youtube_subscriptions.update_one(
        {"topic": topic},
        {"$set": {"topic": topic, "callback": callback, "hub": WEBSUB_HUB, "mode": mode,
                  "status": "pending" if ok else "error", "http_status": status,
                  "requested_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    await log_automation("websub", "ok" if ok else "error",
                         f"Richiesta {mode} inviata all'hub (HTTP {status})",
                         {"callback": callback, "topic": topic, "response": text})
    return {"ok": ok, "http_status": status, "callback": callback, "topic": topic,
            "note": "L'hub invia una verifica GET al callback: deve essere raggiungibile pubblicamente "
                    "(in produzione = dominio reale)."}


async def websub_verify(params: dict):
    """Verifica intent dell'hub: restituisce hub.challenge (testo) se valido."""
    mode = params.get("hub.mode")
    topic = params.get("hub.topic")
    challenge = params.get("hub.challenge")
    lease = params.get("hub.lease_seconds")
    if not challenge:
        return None
    status = "verified" if mode == "subscribe" else "unsubscribed"
    expires = None
    if lease:
        try:
            expires = (datetime.now(timezone.utc) + timedelta(seconds=int(lease))).isoformat()
        except ValueError:
            pass
    await db.youtube_subscriptions.update_one(
        {"topic": topic},
        {"$set": {"topic": topic, "status": status, "lease_seconds": lease, "expires_at": expires,
                  "verified_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    await log_automation("websub", "ok", f"Callback verificato ({mode})", {"topic": topic, "lease": lease})
    return challenge


def _verify_signature(body: bytes, header: str, secret: str) -> bool:
    try:
        algo, sent = header.split("=", 1)
    except ValueError:
        return False
    digestmod = {"sha1": hashlib.sha1, "sha256": hashlib.sha256}.get(algo.lower())
    if not digestmod:
        return False
    mac = hmac.new(secret.encode(), body, digestmod).hexdigest()
    return hmac.compare_digest(mac, sent)


async def websub_notify(body: bytes, signature_header: str = None) -> dict:
    valid = _verify_signature(body, signature_header, _secret()) if signature_header else None
    created = updated = 0
    videos = []
    try:
        root = ET.fromstring(body)
    except Exception as e:
        await log_automation("websub", "error", f"Notifica non interpretabile: {e}")
        return {"ok": False, "error": str(e)}
    for entry in root.findall("atom:entry", ATOM_NS):
        vid_el = entry.find("yt:videoId", ATOM_NS)
        title_el = entry.find("atom:title", ATOM_NS)
        pub_el = entry.find("atom:published", ATOM_NS)
        if vid_el is None or not vid_el.text:
            continue
        youtube_id = vid_el.text
        title = (title_el.text or "").strip() if title_el is not None else ""
        published = pub_el.text[:10] if pub_el is not None and pub_el.text else None
        r = await _upsert_video(youtube_id, title, "", published, 0, auto_publish=True, source="youtube_websub")
        videos.append({"youtube_id": youtube_id, "action": r.get("action")})
        created += r.get("action") == "created"
        updated += r.get("action") == "updated"
    await log_automation(
        "websub", "ok" if valid is not False else "warning",
        f"Notifica WebSub: {created} nuovi, {updated} aggiornati "
        f"(firma: {'valida' if valid else ('assente' if valid is None else 'NON valida')})",
        {"videos": videos, "signature_valid": valid},
    )
    return {"ok": True, "created": created, "updated": updated, "signature_valid": valid, "videos": videos}


async def websub_status() -> dict:
    subs = await db.youtube_subscriptions.find({}, {"_id": 0}).to_list(20)
    events = await db.automation_logs.find({"kind": "websub"}, {"_id": 0}).sort("created_at", -1).to_list(30)
    return {"subscriptions": subs, "events": events,
            "callback": _callback_url(),
            "topic": _topic_url(YOUTUBE_CHANNEL_ID) if YOUTUBE_CHANNEL_ID else None,
            "hub": WEBSUB_HUB}


# ----------------------- OAuth + sottotitoli/trascrizioni -----------------------
def _oauth_configured() -> bool:
    return bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET and GOOGLE_OAUTH_REFRESH_TOKEN)


async def oauth_status() -> dict:
    return {
        "configured": _oauth_configured(),
        "client_id": bool(GOOGLE_OAUTH_CLIENT_ID),
        "client_secret": bool(GOOGLE_OAUTH_CLIENT_SECRET),
        "refresh_token": bool(GOOGLE_OAUTH_REFRESH_TOKEN),
        "scope": OAUTH_SCOPE,
        "note": "OAuth necessario per scaricare i sottotitoli del proprio canale. "
                "Configura GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN in env.",
    }


def _oauth_service_sync():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_OAUTH_CLIENT_ID,
        client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=[OAUTH_SCOPE],
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def _fetch_captions_sync(video_id: str) -> dict:
    yt = _oauth_service_sync()
    listing = yt.captions().list(part="snippet", videoId=video_id).execute()
    tracks = listing.get("items", [])
    if not tracks:
        return {"found": False}
    track = next((t for t in tracks if (t["snippet"].get("language") or "").startswith("it")), tracks[0])
    data = yt.captions().download(id=track["id"], tfmt="srt").execute()
    text = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else str(data)
    return {"found": True, "language": track["snippet"].get("language"), "text": text}


async def fetch_transcript(slug: str) -> dict:
    ep = await db.episodes.find_one({"slug": slug})
    if not ep:
        return {"ok": False, "error": "Contenuto non trovato"}
    if not ep.get("youtube_id"):
        return {"ok": False, "error": "Nessun video YouTube associato"}
    if not _oauth_configured():
        await db.episodes.update_one({"slug": slug}, {"$set": {"transcription_status": "pending"}})
        return {"ok": True, "demo": True, "transcription_status": "pending",
                "note": "OAuth non configurato: la trascrizione resta 'pending'. Nessun testo inventato."}
    try:
        res = await asyncio.get_event_loop().run_in_executor(None, _fetch_captions_sync, ep["youtube_id"])
    except Exception as e:
        await log_automation("captions", "error", f"Download sottotitoli fallito ({slug}): {e}")
        await db.episodes.update_one({"slug": slug}, {"$set": {"transcription_status": "error"}})
        return {"ok": False, "error": str(e)}
    if not res.get("found"):
        await db.episodes.update_one({"slug": slug}, {"$set": {"transcription_status": "unavailable"}})
        await log_automation("captions", "warning", f"Nessun sottotitolo disponibile per {slug}")
        return {"ok": True, "found": False, "transcription_status": "unavailable",
                "note": "Il video non ha sottotitoli. Nessun testo inventato."}
    await db.episodes.update_one({"slug": slug}, {"$set": {
        "transcription": res["text"], "transcription_lang": res.get("language"),
        "transcription_status": "done", "transcription_at": datetime.now(timezone.utc).isoformat()}})
    await log_automation("captions", "ok", f"Sottotitoli scaricati per {slug} ({res.get('language')})")
    return {"ok": True, "found": True, "transcription_status": "done",
            "language": res.get("language"), "chars": len(res["text"])}


async def transcripts_list() -> dict:
    eps = await db.episodes.find(
        {"youtube_id": {"$ne": None}},
        {"_id": 0, "slug": 1, "title": 1, "type": 1, "youtube_id": 1, "transcription_status": 1},
    ).to_list(2000)
    counts = {}
    for e in eps:
        st = e.get("transcription_status") or "pending"
        e["transcription_status"] = st
        counts[st] = counts.get(st, 0) + 1
    eps.sort(key=lambda e: 0 if e["transcription_status"] == "pending" else 1)
    return {"episodes": eps, "counts": counts, "oauth_configured": _oauth_configured()}
