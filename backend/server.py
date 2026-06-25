from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from config_db import db, client, SITE_URL, UPLOAD_DIR, CRON_SECRET, YOUTUBE_CHANNEL_ID
from auth import auth_router, get_current_admin
import seo
import automations as auto
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
    items = await db.press.find({}, {"_id": 0}).to_list(500)
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


@api_router.post("/admin/predictions/add-pick")
async def add_pick(payload: PickIn, admin: str = Depends(get_current_admin)):
    """Aggiunge/aggiorna la giocata di UN tipster nella pagina della giornata.
    Vincolo: una sola giocata per tipster per giornata."""
    key = {"competition": payload.competition, "season": payload.season, "round": payload.round}
    pick = {"tipster": payload.tipster, "type": payload.type,
            "total_odds": payload.total_odds, "selections": payload.selections}
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
    url = f'{SITE_URL}/pronostici/serie-a/{payload.season}/giornata-{payload.round}/'
    await auto.log_automation("prediction", "ok", f"Giocata di {payload.tipster} salvata (giornata {payload.round})")
    return {"ok": True, "public_url": url}


@api_router.post("/admin/predictions/ocr")
async def predictions_ocr(image: UploadFile = File(...), admin: str = Depends(get_current_admin)):
    """Carica l'immagine della schedina -> OCR Vision -> dati strutturati (senza dati sensibili)."""
    content = await image.read()
    mime = image.content_type or "image/jpeg"
    # salva file caricato
    ext = ".png" if "png" in mime else ".jpg"
    fname = f"slip-{uuid.uuid4().hex[:10]}{ext}"
    (UPLOAD_DIR / fname).write_bytes(content)
    result = await auto.ocr_slip(content, mime)
    result["uploaded_file"] = f"/api/uploads/{fname}"
    if result.get("ok"):
        # suggerisci stagione
        result["suggested_season"] = auto.compute_season(datetime.now())
    return result


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
    return await auto.youtube_sync()


@api_router.get("/admin/press/search")
async def admin_press_search(q: str = "UnoXdue podcast", admin: str = Depends(get_current_admin)):
    return await auto.search_press(q)


@api_router.get("/admin/odds")
async def admin_odds(match: str, market: str, pick: str, admin: str = Depends(get_current_admin)):
    return await auto.get_odds(match, market, pick)


# ============================ Cron protetto (scheduler esterno) ============================
@api_router.post("/cron/youtube")
async def cron_youtube(secret: str = Query(...)):
    if not CRON_SECRET or secret != CRON_SECRET:
        raise HTTPException(status_code=403, detail="Cron secret non valido")
    return await auto.youtube_sync()


# ============================ Public SSR pages ============================
def _enrich_status_filter():
    return {"status": {"$ne": "bozza"}}


@api_router.get("/seo/home", response_class=HTMLResponse)
async def ssr_home():
    eps = await db.episodes.find({"type": "episodio"}, {"_id": 0}).sort("published_at", -1).to_list(6)
    ints = await db.episodes.find({"type": "intervista"}, {"_id": 0}).sort("published_at", -1).to_list(6)
    def card(i):
        sec = "interviste" if i.get("type") == "intervista" else "episodi"
        return {"url": f'{SITE_URL}/{sec}/{i["slug"]}/', "title": i.get("title"),
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


@api_router.get("/seo/parlano-di-noi", response_class=HTMLResponse)
async def ssr_press():
    items = await db.press.find({}, {"_id": 0}).to_list(200)
    cards = [{"url": p.get("url"), "title": p.get("title"), "kicker": p.get("source", ""),
              "thumbnail": None} for p in items]
    return HTMLResponse(seo.render_archive("Parlano di noi",
        "Le interviste e i contenuti di UnoXdue ripresi dalle principali testate sportive.",
        "/parlano-di-noi/", cards))


@api_router.get("/seo/episodi", response_class=HTMLResponse)
async def ssr_episodi():
    items = await db.episodes.find({"type": "episodio"}, {"_id": 0}).sort("published_at", -1).to_list(500)
    cards = [{"url": f'{SITE_URL}/episodi/{i["slug"]}/', "title": i.get("title"), "kicker": "Episodio",
              "thumbnail": i.get("thumbnail")} for i in items]
    return HTMLResponse(seo.render_archive("Episodi",
        "Tutti gli episodi del podcast UnoXdue dedicati alla Serie A.", "/episodi/", cards))


@api_router.get("/seo/interviste", response_class=HTMLResponse)
async def ssr_interviste():
    items = await db.episodes.find({"type": "intervista"}, {"_id": 0}).sort("published_at", -1).to_list(500)
    cards = [{"url": f'{SITE_URL}/interviste/{i["slug"]}/', "title": i.get("title"), "kicker": "Intervista",
              "thumbnail": i.get("thumbnail")} for i in items]
    return HTMLResponse(seo.render_archive("Interviste",
        "Le interviste esclusive di UnoXdue ai protagonisti del calcio italiano.", "/interviste/", cards))


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
    return HTMLResponse(seo.render_team_member(m, rel))


@api_router.get("/seo/episodi/{slug}", response_class=HTMLResponse)
async def ssr_episode(slug: str):
    ep = await db.episodes.find_one({"slug": slug})
    if not ep:
        raise HTTPException(status_code=404, detail="Contenuto non trovato")
    return HTMLResponse(seo.render_episode(ep))


@api_router.get("/seo/interviste/{slug}", response_class=HTMLResponse)
async def ssr_interview(slug: str):
    ep = await db.episodes.find_one({"slug": slug})
    if not ep:
        raise HTTPException(status_code=404, detail="Contenuto non trovato")
    return HTMLResponse(seo.render_episode(ep))


# ============================ Sitemap / robots / RSS ============================
@api_router.get("/sitemap.xml")
async def sitemap():
    eps = await db.episodes.find({}, {"_id": 0}).to_list(2000)
    preds = await db.predictions.find({}, {"_id": 0}).to_list(2000)
    team = await db.team.find({}, {"_id": 0}).to_list(200)
    urls = [f"{SITE_URL}/", f"{SITE_URL}/il-podcast/", f"{SITE_URL}/episodi/",
            f"{SITE_URL}/interviste/", f"{SITE_URL}/pronostici/", f"{SITE_URL}/team/",
            f"{SITE_URL}/parlano-di-noi/"]
    for i in eps:
        sec = "interviste" if i.get("type") == "intervista" else "episodi"
        urls.append(f'{SITE_URL}/{sec}/{i["slug"]}/')
    for p in preds:
        urls.append(f'{SITE_URL}/pronostici/serie-a/{p.get("season")}/giornata-{p.get("round")}/')
    for m in team:
        urls.append(f'{SITE_URL}/team/{m["slug"]}/')
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        body.append(f"  <url><loc>{u}</loc></url>")
    body.append("</urlset>")
    return Response("\n".join(body), media_type="application/xml")


@api_router.get("/video-sitemap.xml")
async def video_sitemap():
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
        body += ["  <url>", f"    <loc>{loc}</loc>", "    <video:video>",
                 f"      <video:thumbnail_loc>{thumb}</video:thumbnail_loc>",
                 f"      <video:title>{i.get('title','')}</video:title>",
                 f"      <video:description>{desc}</video:description>",
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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
