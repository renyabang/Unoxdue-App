from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Query, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import os
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from config_db import db, client, SITE_URL, UPLOAD_DIR, CRON_SECRET, YOUTUBE_CHANNEL_ID, ROOT_DIR
from auth import auth_router, get_current_admin, ensure_admin
import seo
import automations as auto
import ai_content as ai
import graphics as gfx
import youtube as yt
import results_provider as rp
import settlement as settle
import press
import ai_transcript as ait
from seo_content import SEED_EPISODES, SEED_TEAM, SEED_PREDICTIONS

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="UnoXdue API")
api_router = APIRouter(prefix="/api")


# ============================ Health ============================
@api_router.get("/")
async def root():
    return {"service": "UnoXdue", "status": "ok"}


@api_router.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@api_router.get("/health/db")
async def health_db():
    try:
        await db.command("ping")
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB non raggiungibile: {e}")


# ============================ Public read APIs ============================
@api_router.get("/episodes")
async def list_episodes(type: Optional[str] = None):
    q = {"type": type} if type else {}
    items = await db.episodes.find(q, {"_id": 0}).to_list(1000)
    return [{"slug": i["slug"], "type": i.get("type"), "title": i.get("title"),
             "thumbnail": i.get("thumbnail"), "status": i.get("status", "pubblicato")} for i in items]


@api_router.get("/team")
async def list_team():
    items = await db.team.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    return items


@api_router.get("/predictions")
async def list_predictions():
    items = await db.predictions.find({}, {"_id": 0}).to_list(500)
    for p in items:
        p["url"] = f'{SITE_URL}/pronostici/serie-a/{p.get("season")}/giornata-{p.get("round")}/'
    return items


@api_router.get("/press")
async def list_press():
    items = await db.press.find(
        {"$or": [{"status": "published"}, {"status": {"$exists": False}}]}, {"_id": 0}).to_list(500)
    return items


# ============================ Admin: contenuti ============================
class EpisodeIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    slug: str
    type: str = "episodio"
    title: str
    youtube_id: str
    duration: Optional[str] = "—"
    published_at: Optional[str] = None
    excerpt: Optional[str] = ""
    summary: List[str] = []
    topics: List[str] = []
    chapters: List[dict] = []
    quotes: List[str] = []
    participants: List[dict] = []
    related: List[dict] = []
    guest_name: Optional[str] = None
    status: str = "pubblicato"


@api_router.post("/admin/episodes")
async def upsert_episode(payload: EpisodeIn, admin: str = Depends(get_current_admin)):
    doc = payload.model_dump()
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.episodes.update_one({"slug": doc["slug"]}, {"$set": doc}, upsert=True)
    section = "interviste" if doc["type"] == "intervista" else "episodi"
    return {"ok": True, "slug": doc["slug"], "public_url": f'{SITE_URL}/{section}/{doc["slug"]}/'}


@api_router.get("/admin/episodes")
async def admin_list_episodes(admin: str = Depends(get_current_admin)):
    return await db.episodes.find({}, {"_id": 0}).to_list(1000)


@api_router.delete("/admin/episodes/{slug}")
async def delete_episode(slug: str, admin: str = Depends(get_current_admin)):
    res = await db.episodes.delete_one({"slug": slug})
    return {"ok": True, "deleted": res.deleted_count}


# ============================ Admin: predictions ============================
class PredictionIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    competition: str = "Serie A"
    season: str
    round: int
    intro: Optional[str] = ""
    picks: List[dict] = []
    status: str = "pubblicato"
    episode_url: Optional[str] = None


@api_router.post("/admin/predictions")
async def upsert_prediction(payload: PredictionIn, admin: str = Depends(get_current_admin)):
    doc = payload.model_dump()
    doc["updated_at"] = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    # vincolo univoco: competizione + stagione + giornata
    await db.predictions.update_one(
        {"competition": doc["competition"], "season": doc["season"], "round": doc["round"]},
        {"$set": doc}, upsert=True,
    )
    url = f'{SITE_URL}/pronostici/serie-a/{doc["season"]}/giornata-{doc["round"]}/'
    return {"ok": True, "public_url": url}


class PickIn(BaseModel):
    competition: str = "Serie A"
    season: str
    round: int
    tipster: str
    type: str = "Multipla"
    total_odds: str = ""
    selections: List[dict] = []
    intro: Optional[str] = None
    source_image: Optional[str] = None
    ocr_upload_id: Optional[str] = None
    mapping_version: Optional[str] = None
    needs_review: bool = False


@api_router.post("/admin/predictions/add-pick")
async def add_pick(payload: PickIn, admin: str = Depends(get_current_admin)):
    """Aggiunge/aggiorna la giocata di UN tipster nella pagina della giornata.
    Vincolo: una sola giocata per tipster per giornata.
    Le quote restano quelle rilevate dalla grafica del team (mai aggiornate da API esterne)."""
    key = {"competition": payload.competition, "season": payload.season, "round": payload.round}
    pick = {"tipster": payload.tipster, "type": payload.type,
            "total_odds": payload.total_odds, "selections": payload.selections,
            "source_image": payload.source_image, "ocr_upload_id": payload.ocr_upload_id,
            "mapping_version": payload.mapping_version, "needs_review": payload.needs_review,
            "odds_disclaimer": auto.ODDS_DISCLAIMER}
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    doc = await db.predictions.find_one(key)
    if not doc:
        newdoc = {**key, "intro": payload.intro or f'Pronostici {payload.competition} {payload.season} — {payload.round}ª giornata.',
                  "picks": [pick], "status": "pubblicato", "updated_at": now}
        await db.predictions.insert_one(dict(newdoc))
    else:
        picks = [p for p in doc.get("picks", []) if p.get("tipster") != payload.tipster]
        picks.append(pick)
        await db.predictions.update_one(key, {"$set": {"picks": picks, "updated_at": now}})
    # marca l'upload OCR come confermato
    if payload.ocr_upload_id:
        await db.slip_uploads.update_one({"id": payload.ocr_upload_id},
                                         {"$set": {"status": "confermato",
                                                   "confirmed_at": datetime.now(timezone.utc).isoformat()}})
    # pubblicazione condizionata (publish_min_valid)
    pub = await settle.apply_publish_rule(payload.competition, payload.season, payload.round)
    url = f'{SITE_URL}/pronostici/serie-a/{payload.season}/giornata-{payload.round}/'
    await auto.log_automation("prediction", "ok", f"Giocata di {payload.tipster} salvata (giornata {payload.round})")
    return {"ok": True, "public_url": url, "published": pub}


@api_router.post("/admin/predictions/ocr")
async def predictions_ocr(image: UploadFile = File(...), admin: str = Depends(get_current_admin)):
    """Carica la grafica comparativa -> OCR Vision -> dati strutturati (quote per bookmaker, senza dati sensibili).
    Persiste immagine sorgente + testo OCR + dati normalizzati + versione mapping."""
    content = await image.read()
    mime = image.content_type or "image/jpeg"
    ext = ".png" if "png" in mime else ".jpg"
    fname = f"slip-{uuid.uuid4().hex[:10]}{ext}"
    (UPLOAD_DIR / fname).write_bytes(content)
    image_url = f"/api/uploads/{fname}"
    result = await auto.ocr_slip(content, mime)
    upload_id = str(uuid.uuid4())
    upload_doc = {
        "id": upload_id,
        "image_path": image_url,
        "ocr_raw": result.get("raw_text", "") if result.get("ok") else result.get("raw", ""),
        "extracted": result.get("data") if result.get("ok") else None,
        "mapping_version": auto.MAPPING_VERSION,
        "ok": bool(result.get("ok")),
        "error": result.get("error"),
        "status": "da_verificare",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.slip_uploads.insert_one(dict(upload_doc))
    result["uploaded_file"] = image_url
    result["upload_id"] = upload_id
    result["disclaimer"] = auto.ODDS_DISCLAIMER
    if result.get("ok"):
        if not (result["data"].get("round")):
            result["suggested_season"] = auto.compute_season(datetime.now())
        else:
            result["suggested_season"] = auto.compute_season(datetime.now())
    return result


@api_router.get("/admin/slip-uploads")
async def admin_slip_uploads(limit: int = 30, admin: str = Depends(get_current_admin)):
    items = await db.slip_uploads.find({}, {"_id": 0}).sort("uploaded_at", -1).to_list(limit)
    return items


# ============================ Admin: team & press ============================
@api_router.post("/admin/team")
async def upsert_team(member: dict, admin: str = Depends(get_current_admin)):
    if not member.get("slug"):
        raise HTTPException(status_code=400, detail="slug richiesto")
    await db.team.update_one({"slug": member["slug"]}, {"$set": member}, upsert=True)
    return {"ok": True}


@api_router.post("/admin/press")
async def upsert_press(item: dict, admin: str = Depends(get_current_admin)):
    item.setdefault("id", str(uuid.uuid4()))
    await db.press.update_one({"id": item["id"]}, {"$set": item}, upsert=True)
    return {"ok": True, "id": item["id"]}


# ============================ Admin: logs & settings ============================
@api_router.get("/admin/logs")
async def admin_logs(limit: int = 100, admin: str = Depends(get_current_admin)):
    items = await db.automation_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return items


@api_router.get("/admin/settings")
async def get_settings(admin: str = Depends(get_current_admin)):
    s = await db.settings.find_one({"_id": "global"}, {"_id": 0})
    integrations = {
        "youtube_channel": bool(YOUTUBE_CHANNEL_ID),
        "youtube_api_key": bool(auto.YOUTUBE_API_KEY),
        "youtube_oauth": bool(yt._oauth_configured()),
        "vision_ocr": bool(auto.EMERGENT_LLM_KEY),
        "odds_api": bool(auto.ODDS_API_URL and auto.ODDS_API_KEY),
        "perplexity": bool(auto.PERPLEXITY_API_KEY),
        "audio_transcription": bool(os.environ.get("OPENAI_AUDIO_API_KEY")),
    }
    return {"settings": s or {}, "integrations": integrations}


@api_router.put("/admin/settings")
async def put_settings(data: dict, admin: str = Depends(get_current_admin)):
    data["_id"] = "global"
    await db.settings.update_one({"_id": "global"}, {"$set": data}, upsert=True)
    return {"ok": True}


# ============================ Admin: automazioni (trigger) ============================
@api_router.post("/admin/sync/youtube")
async def admin_sync_youtube(admin: str = Depends(get_current_admin)):
    res = await auto.youtube_sync()
    try:
        res["ai_autorun"] = await ai.maybe_autorun_after_sync(res)
    except Exception as e:
        logger.error("AI autorun error: %s", e)
    return res


# ============================ Admin: generazione AI (Step 4) ============================
@api_router.get("/admin/ai/settings")
async def admin_get_ai_settings(admin: str = Depends(get_current_admin)):
    return {"settings": await ai.get_ai_settings(), "usage": await ai.usage_counts()}


@api_router.put("/admin/ai/settings")
async def admin_put_ai_settings(data: dict, admin: str = Depends(get_current_admin)):
    return {"ok": True, "settings": await ai.set_ai_settings(data)}


@api_router.post("/admin/ai/process/{slug}")
async def admin_ai_process(slug: str, admin: str = Depends(get_current_admin)):
    return await ai.generate_for_slug(slug, is_auto=False)


class AIBatchIn(BaseModel):
    only_missing: bool = True
    types: Optional[List[str]] = None
    limit: int = 15
    slugs: Optional[List[str]] = None


@api_router.post("/admin/ai/process-batch")
async def admin_ai_batch(payload: AIBatchIn, admin: str = Depends(get_current_admin)):
    return await ai.process_batch(payload.only_missing, payload.types, payload.limit, payload.slugs)


# ============================ Admin: SEO da trascrizioni (P1) ============================
@api_router.get("/admin/transcripts/seo/status")
async def admin_transcripts_seo_status(admin: str = Depends(get_current_admin)):
    return await ait.list_status()


@api_router.post("/admin/transcripts/seo/generate/{slug}")
async def admin_transcripts_seo_generate(slug: str, admin: str = Depends(get_current_admin)):
    return await ait.generate_preview(slug)


@api_router.get("/admin/transcripts/seo/preview/{slug}")
async def admin_transcripts_seo_preview(slug: str, admin: str = Depends(get_current_admin)):
    return await ait.get_preview(slug)


class SectionsIn(BaseModel):
    sections: List[dict]


@api_router.put("/admin/transcripts/seo/preview/{slug}/sections")
async def admin_transcripts_seo_save_sections(slug: str, payload: SectionsIn, admin: str = Depends(get_current_admin)):
    return await ait.save_preview_sections(slug, payload.sections)


@api_router.post("/admin/transcripts/seo/publish/{slug}")
async def admin_transcripts_seo_publish(slug: str, admin: str = Depends(get_current_admin)):
    return await ait.publish_preview(slug)


class TranscriptBatchIn(BaseModel):
    slugs: Optional[List[str]] = None
    only_missing: bool = True
    limit: int = 10


@api_router.post("/admin/transcripts/seo/generate-batch")
async def admin_transcripts_seo_batch(payload: TranscriptBatchIn, admin: str = Depends(get_current_admin)):
    if payload.slugs:
        targets = payload.slugs[:payload.limit]
    else:
        q = {"transcription_status": "done"}
        if payload.only_missing:
            q["ai_preview_at"] = {"$exists": False}
        items = await db.episodes.find(q, {"slug": 1, "_id": 0}).limit(payload.limit).to_list(payload.limit)
        targets = [i["slug"] for i in items]
    ok = failed = 0
    results = []
    for s in targets:
        r = await ait.generate_preview(s)
        results.append({"slug": s, "ok": r.get("ok", False), "error": r.get("error")})
        ok += 1 if r.get("ok") else 0
        failed += 0 if r.get("ok") else 1
    return {"ok": True, "processed": len(targets), "succeeded": ok, "failed": failed, "results": results}


# ============================ Admin: grafiche pronostici (Step 5) ============================
@api_router.get("/admin/predictions")
async def admin_list_predictions(admin: str = Depends(get_current_admin)):
    return await db.predictions.find({}, {"_id": 0}).sort([("season", -1), ("round", -1)]).to_list(500)


class GraphicsIn(BaseModel):
    season: str
    round: int
    pick_index: int


@api_router.post("/admin/graphics/generate")
async def admin_graphics_generate(payload: GraphicsIn, admin: str = Depends(get_current_admin)):
    return await gfx.generate_pick(payload.season, payload.round, payload.pick_index)


class PickEditIn(BaseModel):
    season: str
    round: int
    pick_index: int
    type: Optional[str] = None
    total_odds: Optional[str] = None
    selections: Optional[List[dict]] = None


@api_router.put("/admin/predictions/pick")
async def admin_edit_pick(payload: PickEditIn, admin: str = Depends(get_current_admin)):
    pred = await db.predictions.find_one({"season": payload.season, "round": payload.round})
    if not pred:
        raise HTTPException(status_code=404, detail="Pronostico non trovato")
    picks = pred.get("picks", [])
    if payload.pick_index < 0 or payload.pick_index >= len(picks):
        raise HTTPException(status_code=400, detail="Indice giocata non valido")
    p = picks[payload.pick_index]
    if payload.type is not None:
        p["type"] = payload.type
    if payload.total_odds is not None:
        p["total_odds"] = payload.total_odds
    if payload.selections is not None:
        p["selections"] = payload.selections
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    await db.predictions.update_one({"season": payload.season, "round": payload.round},
                                    {"$set": {"picks": picks, "updated_at": now}})
    return {"ok": True}


# ---- /live/ : destinazione redirezionabile dall'admin (per QR e link) ----
DEFAULT_LIVE = {"target": "twitch", "url": ""}
LIVE_PRESETS = {
    "twitch": "https://www.twitch.tv/unoxdue_",
    "youtube": "https://www.youtube.com/@unoXdue/live",
}


async def _resolve_live() -> str:
    s = await db.settings.find_one({"_id": "global"}) or {}
    live = s.get("live") or DEFAULT_LIVE
    t = live.get("target", "twitch")
    if t == "custom" and live.get("url"):
        return live["url"]
    if t == "latest_episode":
        ep = await db.episodes.find_one({"type": "episodio", "status": "pubblicato"},
                                        {"_id": 0, "slug": 1}, sort=[("published_at", -1)])
        if ep:
            return f"{SITE_URL}/episodi/{ep['slug']}/"
    return LIVE_PRESETS.get(t, LIVE_PRESETS["twitch"])


@api_router.get("/admin/live")
async def admin_get_live(admin: str = Depends(get_current_admin)):
    s = await db.settings.find_one({"_id": "global"}) or {}
    return {"live": s.get("live") or DEFAULT_LIVE, "resolved": await _resolve_live()}


@api_router.put("/admin/live")
async def admin_put_live(data: dict, admin: str = Depends(get_current_admin)):
    live = {"target": data.get("target", "twitch"), "url": data.get("url", "")}
    await db.settings.update_one({"_id": "global"}, {"$set": {"live": live}}, upsert=True)
    return {"ok": True, "live": live, "resolved": await _resolve_live()}


@api_router.get("/live")
async def api_live_redirect():
    return RedirectResponse(url=await _resolve_live(), status_code=302)


@api_router.get("/admin/press/search")
async def admin_press_search(q: str = "UnoXdue podcast", admin: str = Depends(get_current_admin)):
    return await auto.search_press(q)


# ============================ Admin: Rassegna stampa (Step 7B) ============================
@api_router.get("/admin/press/status")
async def admin_press_status(admin: str = Depends(get_current_admin)):
    data = await press.list_all()
    return {"provider": press.provider_status(), "counts": data["counts"]}


class PressRunIn(BaseModel):
    query: Optional[str] = None
    mode: str = "ordinary"  # ordinary=30gg | weekly=90gg | backfill=24 mesi
    max_queries: Optional[int] = None
    max_results: Optional[int] = None


@api_router.post("/admin/press/run")
async def admin_press_run(payload: PressRunIn, admin: str = Depends(get_current_admin)):
    return await press.run_search(query=payload.query, mode=payload.mode, actor="admin",
                                  max_queries=payload.max_queries, max_results=payload.max_results)


@api_router.get("/admin/press/config")
async def admin_press_config_get(admin: str = Depends(get_current_admin)):
    return await press.get_config()


class PressConfigIn(BaseModel):
    config: dict


@api_router.post("/admin/press/config")
async def admin_press_config_set(payload: PressConfigIn, admin: str = Depends(get_current_admin)):
    return await press.set_config(payload.config)


@api_router.get("/admin/press/list")
async def admin_press_list(status: Optional[str] = None, limit: int = 100,
                           admin: str = Depends(get_current_admin)):
    return await press.list_all(status, limit)


class PressStatusIn(BaseModel):
    id: str
    status: str


@api_router.post("/admin/press/set-status")
async def admin_press_set_status(payload: PressStatusIn, admin: str = Depends(get_current_admin)):
    return await press.set_status(payload.id, payload.status, actor="admin")


class PressLinkIn(BaseModel):
    id: str
    action: str = "add"
    type: Optional[str] = None
    slug: Optional[str] = None
    title: Optional[str] = None


@api_router.post("/admin/press/link")
async def admin_press_link(payload: PressLinkIn, admin: str = Depends(get_current_admin)):
    return await press.set_link(payload.id, payload.action, payload.type, payload.slug, payload.title)


@api_router.get("/admin/press/link-options")
async def admin_press_link_options(admin: str = Depends(get_current_admin)):
    return await press.link_options()


@api_router.get("/admin/press/rejected")
async def admin_press_rejected(category: Optional[str] = None, limit: int = 200,
                               admin: str = Depends(get_current_admin)):
    return await press.list_rejected(category, limit)


@api_router.get("/admin/press/runs")
async def admin_press_runs(limit: int = 20, admin: str = Depends(get_current_admin)):
    return await press.list_runs(limit)


# Cron protetto (scheduler esterno). schedule: weekly=30gg, monthly=90gg. Backfill NON automatico.
@api_router.post("/cron/press")
async def cron_press(secret: str = Query(...), schedule: str = Query("weekly")):
    if not CRON_SECRET or secret != CRON_SECRET:
        raise HTTPException(status_code=403, detail="Cron secret non valido")
    mode = "weekly" if schedule == "monthly" else "ordinary"  # monthly->90gg, weekly->30gg
    return await press.run_search(mode=mode, actor="cron", trigger=f"cron:{schedule}")


@api_router.get("/admin/odds")
async def admin_odds(match: str, market: str, pick: str, admin: str = Depends(get_current_admin)):
    return await auto.get_odds(match, market, pick)


# ============================ Admin: YouTube archivio/WebSub/OAuth (Step 3) ============================
@api_router.get("/admin/youtube/stats")
async def admin_youtube_stats(admin: str = Depends(get_current_admin)):
    return await yt.channel_stats()


class BackfillIn(BaseModel):
    max_pages: int = 40
    auto_publish: bool = True


@api_router.post("/admin/youtube/backfill")
async def admin_youtube_backfill(payload: BackfillIn, admin: str = Depends(get_current_admin)):
    res = await yt.backfill(payload.max_pages, payload.auto_publish)
    try:
        res["ai_autorun"] = await ai.maybe_autorun_after_sync(res)
    except Exception as e:
        logger.error("AI autorun error: %s", e)
    return res


@api_router.get("/admin/youtube/websub")
async def admin_websub_status(admin: str = Depends(get_current_admin)):
    return await yt.websub_status()


@api_router.get("/admin/youtube/exclusions")
async def admin_youtube_exclusions(admin: str = Depends(get_current_admin)):
    return await yt.exclusions_list()


class WebsubIn(BaseModel):
    mode: str = "subscribe"


@api_router.post("/admin/youtube/websub/subscribe")
async def admin_websub_subscribe(payload: WebsubIn, admin: str = Depends(get_current_admin)):
    return await yt.websub_subscribe(payload.mode)


@api_router.get("/admin/youtube/oauth/status")
async def admin_youtube_oauth_status(admin: str = Depends(get_current_admin)):
    return await yt.oauth_status()


@api_router.get("/admin/youtube/oauth/start")
async def admin_youtube_oauth_start(origin: str = Query(...), admin: str = Depends(get_current_admin)):
    import youtube_oauth as yto
    if not yto.client_configured():
        return {"ok": False, "error": "GOOGLE_OAUTH_CLIENT_ID/SECRET non configurati."}
    state = await yto.create_state(origin)
    return {"ok": True, "auth_url": yto.build_auth_url(yto.callback_uri(origin), state)}


@api_router.get("/admin/youtube/oauth/callback")
async def admin_youtube_oauth_callback(code: str = Query(None), state: str = Query(None),
                                       error: str = Query(None)):
    import youtube_oauth as yto
    st = await yto.consume_state(state) if state else None
    origin = (st or {}).get("origin") or ""
    dest = f"{origin}/admin/youtube" if origin else "/admin/youtube"
    if error or not code or not st:
        return RedirectResponse(url=f"{dest}?oauth=error", status_code=302)
    res = await yto.handle_callback(code, st["redirect_uri"], asyncio.get_event_loop())
    flag = "connected" if res.get("ok") else "error"
    return RedirectResponse(url=f"{dest}?oauth={flag}", status_code=302)


@api_router.post("/admin/youtube/oauth/disconnect")
async def admin_youtube_oauth_disconnect(admin: str = Depends(get_current_admin)):
    import youtube_oauth as yto
    return await yto.disconnect()


@api_router.get("/admin/youtube/transcripts")
async def admin_youtube_transcripts(admin: str = Depends(get_current_admin)):
    return await yt.transcripts_list()


@api_router.post("/admin/youtube/transcript/{slug}")
async def admin_youtube_transcript(slug: str, admin: str = Depends(get_current_admin)):
    return await yt.fetch_transcript(slug)


# ---- WebSub callback PUBBLICO (senza auth: lo chiama l'hub PubSubHubbub) ----
@api_router.get("/youtube/websub/callback")
async def websub_callback_verify(request: Request):
    challenge = await yt.websub_verify(dict(request.query_params))
    if challenge is None:
        raise HTTPException(status_code=400, detail="hub.challenge mancante")
    return Response(challenge, media_type="text/plain")


@api_router.post("/youtube/websub/callback")
async def websub_callback_notify(request: Request):
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature")
    res = await yt.websub_notify(body, sig)
    return JSONResponse(res, status_code=200)


# ============================ Cron protetto (scheduler esterno) ============================
@api_router.post("/cron/youtube")
async def cron_youtube(secret: str = Query(...)):
    if not CRON_SECRET or secret != CRON_SECRET:
        raise HTTPException(status_code=403, detail="Cron secret non valido")
    res = await auto.youtube_sync()
    try:
        res["ai_autorun"] = await ai.maybe_autorun_after_sync(res)
    except Exception as e:
        logger.error("AI autorun error: %s", e)
    return res


# ============================ Admin: Risultati & settlement (Step 6) ============================
@api_router.get("/admin/results/status")
async def admin_results_status(admin: str = Depends(get_current_admin)):
    s = await db.settings.find_one({"_id": "global"}) or {}
    return {"provider": rp.provider_status(), "settings": (s.get("results") or {"publish_min_valid": 1})}


@api_router.put("/admin/results/settings")
async def admin_results_settings(data: dict, admin: str = Depends(get_current_admin)):
    mv = int(data.get("publish_min_valid", 1))
    mv = 1 if mv < 1 else (3 if mv > 3 else mv)
    results = {"publish_min_valid": mv}
    await db.settings.update_one({"_id": "global"}, {"$set": {"results": results}}, upsert=True)
    return {"ok": True, "results": results}


class SettleIn(BaseModel):
    competition: str = "Serie A"
    season: str
    round: int
    dry_run: bool = False


@api_router.post("/admin/results/settle")
async def admin_results_settle(payload: SettleIn, admin: str = Depends(get_current_admin)):
    return await settle.compute_round(payload.competition, payload.season, payload.round,
                                      source="manual", actor="admin", dry_run=payload.dry_run)


@api_router.get("/admin/results/{season}/{round_}")
async def admin_results_view(season: str, round_: int, admin: str = Depends(get_current_admin)):
    pred = await db.predictions.find_one({"season": season, "round": round_}, {"_id": 0})
    if not pred:
        raise HTTPException(status_code=404, detail="Pronostico non trovato")
    try:
        events = await rp.get_provider().get_events(pred.get("competition", "Serie A"), season, round_)
    except Exception:
        events = []
    return {"prediction": pred, "events": events, "provider": rp.provider_status()}


class CorrectIn(BaseModel):
    competition: str = "Serie A"
    season: str
    round: int
    pick_index: int
    selection_index: Optional[int] = None
    new_status: str
    note: Optional[str] = None


@api_router.post("/admin/results/correct")
async def admin_results_correct(payload: CorrectIn, admin: str = Depends(get_current_admin)):
    return await settle.correct(payload.competition, payload.season, payload.round,
                                payload.pick_index, payload.selection_index,
                                payload.new_status, payload.note, "admin")


@api_router.post("/cron/settle")
async def cron_settle(secret: str = Query(...), season: str = Query(...), round: int = Query(...)):
    if not CRON_SECRET or secret != CRON_SECRET:
        raise HTTPException(status_code=403, detail="Cron secret non valido")
    return await settle.compute_round("Serie A", season, round, source="cron")


# ============================ Public SSR pages ============================
def _enrich_status_filter():
    return {"status": {"$ne": "bozza"}}


@api_router.get("/seo/home", response_class=HTMLResponse)
async def ssr_home():
    eps = await db.episodes.find({"type": "episodio"}, {"_id": 0}).sort("published_at", -1).to_list(6)
    ints = await db.episodes.find({"type": "intervista"}, {"_id": 0}).sort("published_at", -1).to_list(6)
    def card(i):
        sec = "interviste" if i.get("type") == "intervista" else "episodi"
        return {"url": f'{SITE_URL}/{sec}/{i["slug"]}/', "title": i.get("website_title") or i.get("title"),
                "thumbnail": i.get("thumbnail") or f'https://img.youtube.com/vi/{i.get("youtube_id","")}/maxresdefault.jpg'}
    return HTMLResponse(seo.render_home([card(i) for i in eps], [card(i) for i in ints]))


@api_router.get("/seo/il-podcast", response_class=HTMLResponse)
async def ssr_il_podcast():
    body = (
        "<p class='lead'>UnoXdue e' il podcast sulla Serie A con tre tipster e un host.</p>"
        "<p>Ogni settimana Sono Micuccio, il Ninja e il Marziano si ritrovano in diretta "
        "insieme all'host Antonello Santopaolo per analizzare le giornate di Serie A, studiare i "
        "palinsesti, commentare partite e notizie e presentare i pronostici. Spazio anche alle "
        "interviste ai protagonisti del calcio e, occasionalmente, ad altri sport.</p>"
        "<h2>Cosa trovi</h2><ul>"
        "<li>Dirette settimanali su Twitch</li><li>Episodi completi su YouTube</li>"
        "<li>Interviste esclusive ai calciatori</li><li>Pronostici per ogni giornata di Serie A</li></ul>"
    )
    return HTMLResponse(seo.render_page("Il podcast",
        "Scopri UnoXdue: il podcast sulla Serie A con tre tipster e un host.", "/il-podcast/", body))


@api_router.get("/seo/collaborazioni", response_class=HTMLResponse)
async def ssr_collaborazioni():
    body = (
        "<p class='lead'>Vuoi collaborare con UnoXdue? Siamo aperti a partnership, sponsorizzazioni e progetti editoriali nel mondo del calcio.</p>"
        "<p>UnoXdue è un podcast settimanale dedicato alla Serie A, con dirette su Twitch, episodi su YouTube, "
        "interviste ai protagonisti e pronostici per ogni giornata. Collaboriamo con brand, testate e realtà sportive "
        "che condividono la nostra passione per il calcio italiano.</p>"
        "<h2>Tipi di collaborazione</h2><ul>"
        "<li>Sponsorizzazioni di episodi e dirette</li>"
        "<li>Contenuti editoriali e branded content</li>"
        "<li>Interviste e ospitate</li>"
        "<li>Partnership con media e creator</li></ul>"
        "<h2>Come proporre una collaborazione</h2>"
        "<p>Scrivici tramite la pagina <a href=\"" + SITE_URL + "/contatti/\">Contatti</a> o contattaci sui nostri canali social. "
        "Ti risponderemo con i dettagli su formati, pubblico e modalità.</p>"
    )
    return HTMLResponse(seo.render_page("Collaborazioni",
        "Collabora con UnoXdue: sponsorizzazioni, partnership e progetti editoriali sul calcio e la Serie A.",
        "/collaborazioni/", body))


@api_router.get("/seo/contatti", response_class=HTMLResponse)
async def ssr_contatti():
    body = (
        "<p class='lead'>Mettiti in contatto con UnoXdue.</p>"
        "<p>Per collaborazioni, interviste, segnalazioni o semplici domande, puoi raggiungerci sui nostri canali ufficiali.</p>"
        "<h2>Dove trovarci</h2><ul>"
        "<li><a href=\"https://www.twitch.tv/unoxdue_\" target=\"_blank\" rel=\"noopener noreferrer\">Twitch — dirette settimanali</a></li>"
        "<li><a href=\"https://www.youtube.com/@unoXdue\" target=\"_blank\" rel=\"noopener noreferrer\">YouTube — episodi completi</a></li>"
        "<li><a href=\"https://www.instagram.com/unoxdue_\" target=\"_blank\" rel=\"noopener noreferrer\">Instagram</a></li>"
        "<li><a href=\"https://www.tiktok.com/@unoxdue_\" target=\"_blank\" rel=\"noopener noreferrer\">TikTok</a></li></ul>"
        "<p>Per proposte di collaborazione visita anche la pagina <a href=\"" + SITE_URL + "/collaborazioni/\">Collaborazioni</a>.</p>"
    )
    return HTMLResponse(seo.render_page("Contatti",
        "Contatta UnoXdue: Twitch, YouTube, Instagram e TikTok. Collaborazioni, interviste e segnalazioni.",
        "/contatti/", body))


@api_router.get("/seo/privacy", response_class=HTMLResponse)
async def ssr_privacy():
    body = (
        "<p class='lead'>La presente informativa descrive come UnoXdue tratta i dati personali degli utenti del sito.</p>"
        "<h2>Titolare del trattamento</h2><p>Il titolare del trattamento è UnoXdue. Per qualsiasi richiesta relativa ai tuoi dati puoi usare la pagina Contatti.</p>"
        "<h2>Dati raccolti</h2><p>Il sito è prevalentemente informativo. Possono essere raccolti dati tecnici di navigazione "
        "(indirizzo IP, tipo di browser, pagine visitate) e, se attivati, dati statistici aggregati per misurare l'audience.</p>"
        "<h2>Contenuti di terze parti</h2><p>Le pagine possono includere contenuti incorporati da YouTube (video) e link ai social network. "
        "Questi servizi possono raccogliere dati secondo le rispettive informative privacy.</p>"
        "<h2>Diritti dell'utente</h2><p>Hai diritto di accedere, rettificare o cancellare i tuoi dati e di opporti al trattamento, "
        "contattandoci tramite la pagina <a href=\"" + SITE_URL + "/contatti/\">Contatti</a>.</p>"
        "<h2>Cookie</h2><p>Per l'uso dei cookie consulta la <a href=\"" + SITE_URL + "/cookie/\">Cookie Policy</a>.</p>"
    )
    return HTMLResponse(seo.render_page("Privacy Policy",
        "Informativa privacy di UnoXdue: trattamento dei dati, contenuti di terze parti e diritti degli utenti.",
        "/privacy/", body))


@api_router.get("/seo/cookie", response_class=HTMLResponse)
async def ssr_cookie():
    body = (
        "<p class='lead'>Questa Cookie Policy spiega come e perché UnoXdue utilizza i cookie e tecnologie simili.</p>"
        "<h2>Cosa sono i cookie</h2><p>I cookie sono piccoli file di testo memorizzati dal browser durante la navigazione, utili al funzionamento del sito e all'analisi dell'uso.</p>"
        "<h2>Tipologie utilizzate</h2><ul>"
        "<li><strong>Tecnici</strong>: necessari al funzionamento del sito.</li>"
        "<li><strong>Statistici/analitici</strong>: in forma aggregata, per misurare l'audience (attivati solo previo consenso ove richiesto).</li>"
        "<li><strong>Di terze parti</strong>: legati a contenuti incorporati come i video di YouTube.</li></ul>"
        "<h2>Gestione dei cookie</h2><p>Puoi gestire o disabilitare i cookie dalle impostazioni del tuo browser. "
        "La disattivazione di alcuni cookie potrebbe limitare alcune funzionalità.</p>"
        "<p>Per maggiori informazioni sul trattamento dei dati consulta la <a href=\"" + SITE_URL + "/privacy/\">Privacy Policy</a>.</p>"
    )
    return HTMLResponse(seo.render_page("Cookie Policy",
        "Cookie Policy di UnoXdue: tipologie di cookie, finalità e gestione delle preferenze.",
        "/cookie/", body))


@api_router.get("/seo/parlano-di-noi", response_class=HTMLResponse)
async def ssr_press():
    items = await press.published_archive()
    return HTMLResponse(seo.render_press_archive(items))


@api_router.get("/seo/episodi", response_class=HTMLResponse)
async def ssr_episodi():
    items = await db.episodes.find({"type": "episodio"}, {"_id": 0}).sort("published_at", -1).to_list(500)
    cards = [{"url": f'{SITE_URL}/episodi/{i["slug"]}/', "title": i.get("website_title") or i.get("title"), "kicker": "Episodio",
              "thumbnail": i.get("thumbnail")} for i in items]
    return HTMLResponse(seo.render_archive("Episodi",
        "Tutti gli episodi del podcast UnoXdue dedicati alla Serie A.", "/episodi/", cards, show_play=True))


@api_router.get("/seo/interviste", response_class=HTMLResponse)
async def ssr_interviste():
    items = await db.episodes.find({"type": "intervista"}, {"_id": 0}).sort("published_at", -1).to_list(500)
    cards = [{"url": f'{SITE_URL}/interviste/{i["slug"]}/', "title": i.get("website_title") or i.get("title"), "kicker": "Intervista",
              "thumbnail": i.get("thumbnail")} for i in items]
    return HTMLResponse(seo.render_archive("Interviste",
        "Le interviste esclusive di UnoXdue ai protagonisti del calcio italiano.", "/interviste/", cards, show_play=True))


@api_router.get("/seo/pronostici", response_class=HTMLResponse)
async def ssr_pronostici_archive():
    items = await db.predictions.find({}, {"_id": 0}).sort("season", -1).to_list(500)
    cards = [{"url": f'{SITE_URL}/pronostici/serie-a/{p.get("season")}/giornata-{p.get("round")}/',
              "title": f'{p.get("competition","Serie A")} {p.get("season")} — {p.get("round")}ª giornata',
              "kicker": "Pronostici", "thumbnail": None} for p in items]
    return HTMLResponse(seo.render_archive("Pronostici",
        "I pronostici di UnoXdue per ogni giornata di Serie A. 18+, gioca responsabilmente.",
        "/pronostici/", cards))


@api_router.get("/seo/pronostici/serie-a/{season}/giornata-{round_}", response_class=HTMLResponse)
async def ssr_prediction(season: str, round_: int):
    p = await db.predictions.find_one({"season": season, "round": round_})
    if not p:
        raise HTTPException(status_code=404, detail="Pronostici non trovati")
    return HTMLResponse(seo.render_prediction(p))


@api_router.get("/seo/team", response_class=HTMLResponse)
async def ssr_team_archive():
    items = await db.team.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    cards = [{"url": f'{SITE_URL}/team/{m["slug"]}/', "title": m.get("name"),
              "kicker": m.get("badge", ""),
              "thumbnail": (m.get("photo") if str(m.get("photo","")).startswith("http") else f'{SITE_URL}{m.get("photo","")}')}
             for m in items]
    return HTMLResponse(seo.render_archive("Il team",
        "Un host e tre tipster: il team di UnoXdue.", "/team/", cards))


@api_router.get("/seo/team/{slug}", response_class=HTMLResponse)
async def ssr_team_member(slug: str):
    m = await db.team.find_one({"slug": slug})
    if not m:
        raise HTTPException(status_code=404, detail="Membro non trovato")
    related = await db.episodes.find({"participants.slug": slug}, {"_id": 0}).to_list(50)
    rel = [{"section": ("interviste" if r.get("type") == "intervista" else "episodi"),
            "slug": r["slug"], "title": r.get("title")} for r in related]
    press_box = await press.published_for(slug)
    return HTMLResponse(seo.render_team_member(m, rel, press_box))


@api_router.get("/seo/episodi/{slug}", response_class=HTMLResponse)
async def ssr_episode(slug: str):
    ep = await db.episodes.find_one({"slug": slug})
    if not ep:
        red = await _slug_redirect(slug)
        if red:
            return red
        raise HTTPException(status_code=404, detail="Contenuto non trovato")
    press_box = await press.published_for(slug)
    return HTMLResponse(seo.render_episode(ep, press_box))


@api_router.get("/seo/interviste/{slug}", response_class=HTMLResponse)
async def ssr_interview(slug: str):
    ep = await db.episodes.find_one({"slug": slug})
    if not ep:
        red = await _slug_redirect(slug)
        if red:
            return red
        raise HTTPException(status_code=404, detail="Contenuto non trovato")
    press_box = await press.published_for(slug)
    return HTMLResponse(seo.render_episode(ep, press_box))


async def _slug_redirect(slug: str, transcript: bool = False):
    """301 dal vecchio slug al nuovo (campo previous_slugs)."""
    red = await db.episodes.find_one({"previous_slugs": slug})
    if not red:
        return None
    sec = "interviste" if red.get("type") == "intervista" else "episodi"
    suffix = "trascrizione/" if transcript else ""
    return RedirectResponse(url=f"{seo.SITE_URL}/{sec}/{red['slug']}/{suffix}", status_code=301)


@api_router.get("/seo/episodi/{slug}/trascrizione", response_class=HTMLResponse)
async def ssr_episode_transcript(slug: str):
    return await _render_transcript_page(slug, "episodi")


@api_router.get("/seo/interviste/{slug}/trascrizione", response_class=HTMLResponse)
async def ssr_interview_transcript(slug: str):
    return await _render_transcript_page(slug, "interviste")


@api_router.get("/seo/{full_path:path}", response_class=HTMLResponse)
async def ssr_not_found(full_path: str):
    body = (
        "<p class='lead'>La pagina che cerchi non esiste o è stata spostata.</p>"
        "<p>Torna alla <a href=\"" + SITE_URL + "/\">home</a>, esplora gli "
        "<a href=\"" + SITE_URL + "/episodi/\">episodi</a> o le "
        "<a href=\"" + SITE_URL + "/interviste/\">interviste</a>.</p>"
    )
    html = seo.render_page("Pagina non trovata", "La pagina richiesta non esiste (errore 404).",
                           "/404/", body, noindex=True)
    return HTMLResponse(html, status_code=404)


async def _render_transcript_page(slug: str, section: str):
    ep = await db.episodes.find_one({"slug": slug})
    if not ep:
        red = await _slug_redirect(slug, transcript=True)
        if red:
            return red
        raise HTTPException(status_code=404, detail="Trascrizione non disponibile")
    if not ep.get("has_transcript_page"):
        raise HTTPException(status_code=404, detail="Trascrizione non disponibile")
    b = await ait.get_transcript_clean(slug)
    clean = b.get("clean", "")
    return HTMLResponse(seo.render_transcript(ep, clean, ep.get("chapters", [])))


# ============================ Sitemap / robots / RSS ============================
@api_router.get("/sitemap.xml")
async def sitemap():
    from xml.sax.saxutils import escape
    eps = await db.episodes.find({}, {"_id": 0}).to_list(2000)
    preds = await db.predictions.find({}, {"_id": 0}).to_list(2000)
    team = await db.team.find({}, {"_id": 0}).to_list(200)
    urls = [f"{SITE_URL}/", f"{SITE_URL}/il-podcast/", f"{SITE_URL}/episodi/",
            f"{SITE_URL}/interviste/", f"{SITE_URL}/pronostici/", f"{SITE_URL}/team/",
            f"{SITE_URL}/parlano-di-noi/"]
    for i in eps:
        sec = "interviste" if i.get("type") == "intervista" else "episodi"
        urls.append(f'{SITE_URL}/{sec}/{i["slug"]}/')
        if i.get("has_transcript_page"):
            urls.append(f'{SITE_URL}/{sec}/{i["slug"]}/trascrizione/')
    for p in preds:
        urls.append(f'{SITE_URL}/pronostici/serie-a/{p.get("season")}/giornata-{p.get("round")}/')
    for m in team:
        urls.append(f'{SITE_URL}/team/{m["slug"]}/')
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        body.append(f"  <url><loc>{escape(u)}</loc></url>")
    body.append("</urlset>")
    return Response("\n".join(body), media_type="application/xml")


@api_router.get("/video-sitemap.xml")
async def video_sitemap():
    from xml.sax.saxutils import escape
    items = await db.episodes.find({}, {"_id": 0}).to_list(2000)
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">']
    for i in items:
        if not i.get("youtube_id"):
            continue
        sec = "interviste" if i.get("type") == "intervista" else "episodi"
        loc = f'{SITE_URL}/{sec}/{i["slug"]}/'
        thumb = i.get("thumbnail") or f'https://img.youtube.com/vi/{i["youtube_id"]}/maxresdefault.jpg'
        desc = (i.get("meta_description") or i.get("excerpt") or i.get("title", ""))[:200]
        body += ["  <url>", f"    <loc>{escape(loc)}</loc>", "    <video:video>",
                 f"      <video:thumbnail_loc>{escape(thumb)}</video:thumbnail_loc>",
                 f"      <video:title>{escape(i.get('title',''))}</video:title>",
                 f"      <video:description>{escape(desc)}</video:description>",
                 f"      <video:player_loc>https://www.youtube.com/embed/{i['youtube_id']}</video:player_loc>",
                 "    </video:video>", "  </url>"]
    body.append("</urlset>")
    return Response("\n".join(body), media_type="application/xml")


@api_router.get("/robots.txt")
async def robots():
    txt = f"User-agent: *\nAllow: /\nDisallow: /admin\nSitemap: {SITE_URL}/sitemap.xml\n"
    return Response(txt, media_type="text/plain")


# ============================ wiring ============================
app.include_router(api_router)
app.include_router(auth_router)
app.mount("/api/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
(ROOT_DIR / "static").mkdir(exist_ok=True)
app.mount("/api/static", StaticFiles(directory=str(ROOT_DIR / "static")), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def seed_all():
    try:
        await ensure_admin()
        if await db.episodes.count_documents({}) == 0:
            for ep in SEED_EPISODES:
                d = dict(ep); d["status"] = "pubblicato"
                d["updated_at"] = datetime.now(timezone.utc).isoformat()
                await db.episodes.update_one({"slug": d["slug"]}, {"$set": d}, upsert=True)
            logger.info("Seeded %d contenuti", len(SEED_EPISODES))
        if await db.team.count_documents({}) == 0:
            for m in SEED_TEAM:
                await db.team.update_one({"slug": m["slug"]}, {"$set": m}, upsert=True)
            logger.info("Seeded team")
        if await db.predictions.count_documents({}) == 0:
            for p in SEED_PREDICTIONS:
                await db.predictions.update_one(
                    {"competition": p["competition"], "season": p["season"], "round": p["round"]},
                    {"$set": p}, upsert=True)
            logger.info("Seeded predictions")
        # indici univoci
        await db.episodes.create_index("slug", unique=True)
        await db.episodes.create_index("youtube_id", unique=True, sparse=True)
        await db.predictions.create_index([("competition", 1), ("season", 1), ("round", 1)], unique=True)
        await db.team.create_index("slug", unique=True)
    except Exception as e:
        logger.error("Seed error: %s", e)


@app.get("/live")
@app.get("/live/")
async def live_redirect():
    return RedirectResponse(url=await _resolve_live(), status_code=302)


@app.on_event("shutdown")
async def shutdown_db_client():
    await gfx.shutdown_browser()
    client.close()
