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
from automations import (classify_video, slugify, log_automation,
                         classify_content, record_exclusion, is_excluded_video)

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
async def _upsert_video(youtube_id, title, desc, published, seconds, auto_publish=True,
                        source="youtube_api", playlist=None):
    info = classify_content(title, desc, seconds)
    if info["excluded"]:
        await record_exclusion(youtube_id, title, info, seconds, published, source=source)
        # rimuove eventuale record editoriale pregresso dello stesso video escluso
        await db.episodes.delete_one({"youtube_id": youtube_id})
        return {"action": "excluded", "editorial_type": info["editorial_type"],
                "youtube_format": info["youtube_format"], "reason": info["reason"],
                "youtube_id": youtube_id}
    existing = await db.episodes.find_one({"youtube_id": youtube_id})
    etype = existing.get("type") if (existing and existing.get("type") in ("episodio", "intervista")) \
        else info["editorial_type"]
    doc = {
        "slug": existing["slug"] if existing else slugify(title),
        "type": etype,
        "youtube_format": "long_form",
        "editorial_type": etype,
        "title": title,
        "youtube_id": youtube_id,
        "published_at": published,
        "thumbnail": f"https://img.youtube.com/vi/{youtube_id}/maxresdefault.jpg",
        "description": desc or (existing.get("description") if existing else ""),
        "excerpt": (desc[:240] if desc else (existing.get("excerpt") if existing else title)),
        "source": source,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if playlist:
        doc["uploads_playlist"] = playlist
    if seconds:
        doc["duration"] = human_duration(seconds)
        doc["duration_seconds"] = seconds
    if existing:
        await db.episodes.update_one({"youtube_id": youtube_id}, {"$set": doc})
        return {"action": "updated", "kind": etype, "type": etype,
                "status": existing.get("status"), "slug": doc["slug"], "youtube_id": youtube_id}
    # nuovo contenuto
    if not desc or len(desc) < 20:
        doc["status"] = "da_verificare"
    else:
        doc["status"] = "pubblicato" if auto_publish else "bozza"
    doc["transcription_status"] = "pending"
    doc["created_at"] = doc["updated_at"]
    await db.episodes.insert_one(dict(doc))
    return {"action": "created", "kind": etype, "type": etype,
            "status": doc["status"], "slug": doc["slug"], "youtube_id": youtube_id}


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
    page_errors = 0
    while True:
        pages += 1
        try:
            resp = await loop.run_in_executor(None, _list_uploads_sync, uploads, page_token)
        except Exception as e:
            page_errors += 1
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
    videos_calls = 0
    for i in range(0, len(items), 50):
        chunk = [x["id"] for x in items[i:i + 50]]
        videos_calls += 1
        try:
            dresp = await loop.run_in_executor(None, _video_details_sync, chunk)
            for d in dresp.get("items", []):
                dur_map[d["id"]] = parse_iso_duration(d.get("contentDetails", {}).get("duration", ""))
        except Exception as e:
            await log_automation("youtube_backfill", "warning", f"videos.list fallita (chunk): {e}")

    created = updated = skipped = upsert_errors = 0
    excl_short = excl_clip = excl_teaser = excl_preskip = 0
    type_counts = {"episodio": 0, "intervista": 0}
    da_verificare = 0
    for x in items:
        if await is_excluded_video(x["id"]):
            excl_preskip += 1
            skipped += 1
            continue
        try:
            r = await _upsert_video(x["id"], x["title"], x["desc"], x["published"],
                                    dur_map.get(x["id"], 0), auto_publish, playlist=uploads)
        except Exception as e:
            upsert_errors += 1
            await log_automation("youtube_backfill", "warning", f"Upsert fallito {x['id']}: {e}")
            continue
        a = r.get("action")
        if a == "excluded":
            skipped += 1
            et = r.get("editorial_type")
            if r.get("youtube_format") == "short" and et not in ("clip", "teaser"):
                excl_short += 1
            elif et == "teaser":
                excl_teaser += 1
            else:
                excl_clip += 1
            continue
        created += a == "created"
        updated += a == "updated"
        t = r.get("type")
        if t in type_counts:
            type_counts[t] += 1
        if r.get("status") == "da_verificare":
            da_verificare += 1

    total_in_db = await db.episodes.count_documents({})
    excluded_total = await db.youtube_exclusions.count_documents({})
    quota = {
        "channels_list": 1,
        "playlist_items_list": pages,
        "videos_list": videos_calls,
        "total_units": 1 + pages + videos_calls,
        "daily_limit": 10000,
        "nota": "Costo standard read API: 1 unità per chiamata list. La quota residua reale è visibile nella dashboard Google Cloud.",
    }
    summary = {
        "ok": True, "demo": False,
        "channel_id": YOUTUBE_CHANNEL_ID, "channel_title": info.get("title"),
        "uploads_playlist": uploads,
        "channel_video_count": info["video_count"],
        "fetched": len(items), "pages": pages,
        "created": created, "updated": updated,
        "skipped": skipped,
        "excluded_shorts": excl_short, "excluded_clips": excl_clip, "excluded_teasers": excl_teaser,
        "excluded_already": excl_preskip,
        "episodi": type_counts["episodio"], "interviste": type_counts["intervista"],
        "non_classificati": da_verificare,
        "errors": page_errors + upsert_errors,
        "imported_total": total_in_db,
        "exclusions_total": excluded_total,
        "quota": quota,
    }
    await log_automation("youtube_backfill", "ok",
                         f"Backfill REALE: {len(items)} trovati, {created} nuovi, {updated} aggiornati, "
                         f"esclusi {excl_short} short/{excl_clip} clip/{excl_teaser} teaser, "
                         f"{type_counts['episodio']} episodi, {type_counts['intervista']} interviste, "
                         f"quota {quota['total_units']} unità", summary)
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
    import youtube_oauth as yto
    return await yto.get_status()


def _oauth_service_sync(refresh_token: str):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_OAUTH_CLIENT_ID,
        client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=[OAUTH_SCOPE],
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def _fetch_captions_sync(video_id: str, refresh_token: str) -> dict:
    yt = _oauth_service_sync(refresh_token)
    listing = yt.captions().list(part="snippet", videoId=video_id).execute()
    tracks = listing.get("items", [])
    if not tracks:
        return {"found": False}
    track = next((t for t in tracks if (t["snippet"].get("language") or "").startswith("it")), tracks[0])
    data = yt.captions().download(id=track["id"], tfmt="srt").execute()
    text = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else str(data)
    return {"found": True, "language": track["snippet"].get("language"),
            "track_id": track["id"], "text": text}


async def fetch_transcript(slug: str) -> dict:
    ep = await db.episodes.find_one({"slug": slug})
    if not ep:
        return {"ok": False, "error": "Contenuto non trovato"}
    if not ep.get("youtube_id"):
        return {"ok": False, "error": "Nessun video YouTube associato"}
    import youtube_oauth as yto
    refresh = await yto.get_refresh_token() or GOOGLE_OAUTH_REFRESH_TOKEN
    configured = bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET and refresh)
    if not configured:
        await db.episodes.update_one({"slug": slug}, {"$set": {"transcription_status": "pending"}})
        return {"ok": True, "demo": True, "transcription_status": "pending",
                "note": "OAuth non collegato: la trascrizione resta 'pending'. Nessun testo inventato."}
    try:
        res = await asyncio.get_event_loop().run_in_executor(None, _fetch_captions_sync, ep["youtube_id"], refresh)
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
    import youtube_oauth as yto
    return {"episodes": eps, "counts": counts, "oauth_configured": await yto.is_connected()}



async def exclusions_list(limit: int = 300) -> dict:
    """Tabella tecnica di esclusione (Short/clip/teaser). Non sono contenuti editoriali."""
    items = await db.youtube_exclusions.find({}, {"_id": 0}).sort("duration_seconds", 1).to_list(limit)
    counts = {}
    for it in items:
        et = it.get("editorial_type") or "altro"
        counts[et] = counts.get(et, 0) + 1
    return {"items": items, "counts": counts, "total": len(items)}
