from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from seo_content import SEED_EPISODES


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Public site URL (used for canonical / OG / sitemap)
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:3000').rstrip('/')

# Jinja2 templates for server-side rendered (SSR) public SEO pages
templates = Jinja2Templates(directory=str(ROOT_DIR / 'templates'))

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks


# =========================================================
#  Contenuti (episodi / interviste) — modello + CRUD minimo
# =========================================================
class EpisodeCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    slug: str
    type: str = "episodio"
    title: str
    h1: Optional[str] = None
    seo_title: Optional[str] = None
    meta_description: Optional[str] = None
    youtube_id: str
    duration: Optional[str] = "—"
    published_at: Optional[str] = None
    thumbnail: Optional[str] = None
    excerpt: Optional[str] = ""
    summary: List[str] = []
    topics: List[str] = []
    chapters: List[dict] = []
    quotes: List[str] = []
    participants: List[dict] = []
    guest_name: Optional[str] = None
    prediction_url: Optional[str] = None
    related: List[dict] = []


def _enrich(ep: dict) -> dict:
    """Riempie i campi derivati / di default per il rendering."""
    ep = dict(ep)
    ep.pop("_id", None)
    ep.setdefault("type", "episodio")
    ep["type_label"] = ep.get("type_label") or ("Intervista" if ep["type"] == "intervista" else "Episodio")
    ep["section"] = ep.get("section") or ("interviste" if ep["type"] == "intervista" else "episodi")
    ep["section_label"] = ep.get("section_label") or ("Interviste" if ep["type"] == "intervista" else "Episodi")
    ep["h1"] = ep.get("h1") or ep["title"]
    ep["seo_title"] = ep.get("seo_title") or f'{ep["title"]} | UnoXdue'
    ep["meta_description"] = ep.get("meta_description") or (ep.get("excerpt") or ep["title"])[:160]
    if not ep.get("thumbnail") and ep.get("youtube_id"):
        ep["thumbnail"] = f'https://img.youtube.com/vi/{ep["youtube_id"]}/maxresdefault.jpg'
    if not ep.get("published_human") and ep.get("published_at"):
        try:
            d = datetime.fromisoformat(ep["published_at"])
            mesi = ["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
            ep["published_human"] = f"{d.day} {mesi[d.month-1]} {d.year}"
        except Exception:
            ep["published_human"] = ep["published_at"]
    ep.setdefault("published_human", ep.get("published_at", ""))
    ep.setdefault("summary", [])
    ep.setdefault("topics", [])
    ep.setdefault("chapters", [])
    ep.setdefault("quotes", [])
    ep.setdefault("participants", [])
    ep.setdefault("related", [])
    return ep


def _build_jsonld(ep: dict) -> str:
    canonical = f'{SITE_URL}/{ep["section"]}/{ep["slug"]}/'
    schema_type = "PodcastEpisode" if ep["type"] != "intervista" else "VideoObject"
    data = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": ep["h1"],
        "description": ep["meta_description"],
        "url": canonical,
        "datePublished": ep.get("published_at"),
        "thumbnailUrl": ep.get("thumbnail"),
        "inLanguage": "it",
        "embedUrl": f'https://www.youtube.com/embed/{ep["youtube_id"]}',
        "contentUrl": f'https://www.youtube.com/watch?v={ep["youtube_id"]}',
        "uploadDate": ep.get("published_at"),
        "publisher": {"@type": "Organization", "name": "UnoXdue", "logo": f"{SITE_URL}/logo.jpg"},
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _build_breadcrumb(ep: dict) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": ep["section_label"], "item": f'{SITE_URL}/{ep["section"]}/'},
            {"@type": "ListItem", "position": 3, "name": ep["title"], "item": f'{SITE_URL}/{ep["section"]}/{ep["slug"]}/'},
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


@api_router.post("/admin/episodes")
async def create_episode(payload: EpisodeCreate):
    """Crea/aggiorna una pagina contenuto dai dati (nessuna modifica al codice)."""
    doc = payload.model_dump()
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.episodes.update_one({"slug": doc["slug"]}, {"$set": doc}, upsert=True)
    return {"ok": True, "slug": doc["slug"], "public_url": f'{SITE_URL}/{_enrich(doc)["section"]}/{doc["slug"]}/'}


@api_router.get("/episodes")
async def list_episodes():
    items = await db.episodes.find({}, {"_id": 0}).to_list(1000)
    return [{"slug": i["slug"], "type": i.get("type"), "title": i.get("title")} for i in items]


# ---- Pagina pubblica SERVER-RENDERED (HTML completo, generato dal DB) ----
@api_router.get("/seo/{section}/{slug}", response_class=HTMLResponse)
async def render_content_page(request: Request, section: str, slug: str):
    ep = await db.episodes.find_one({"slug": slug})
    if not ep:
        raise HTTPException(status_code=404, detail="Contenuto non trovato")
    ep = _enrich(ep)
    canonical = f'{SITE_URL}/{ep["section"]}/{ep["slug"]}/'
    return templates.TemplateResponse(
        "episode.html",
        {
            "request": request,
            "ep": ep,
            "canonical": canonical,
            "site_url": SITE_URL,
            "jsonld": _build_jsonld(ep),
            "breadcrumb_jsonld": _build_breadcrumb(ep),
            "year": datetime.now().year,
        },
    )


# ---- Sitemap dinamiche ----
@api_router.get("/sitemap.xml")
async def sitemap():
    items = await db.episodes.find({}, {"_id": 0}).to_list(2000)
    urls = [f"{SITE_URL}/"]
    for i in items:
        e = _enrich(i)
        urls.append(f'{SITE_URL}/{e["section"]}/{e["slug"]}/')
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
        e = _enrich(i)
        loc = f'{SITE_URL}/{e["section"]}/{e["slug"]}/'
        body.append("  <url>")
        body.append(f"    <loc>{loc}</loc>")
        body.append("    <video:video>")
        body.append(f"      <video:thumbnail_loc>{e['thumbnail']}</video:thumbnail_loc>")
        body.append(f"      <video:title>{e['title']}</video:title>")
        body.append(f"      <video:description>{e['meta_description']}</video:description>")
        body.append(f"      <video:player_loc>https://www.youtube.com/embed/{e['youtube_id']}</video:player_loc>")
        body.append("    </video:video>")
        body.append("  </url>")
    body.append("</urlset>")
    return Response("\n".join(body), media_type="application/xml")


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def seed_content():
    """Inserisce i contenuti seed solo se la collezione è vuota."""
    try:
        count = await db.episodes.count_documents({})
        if count == 0:
            for ep in SEED_EPISODES:
                doc = dict(ep)
                doc["updated_at"] = datetime.now(timezone.utc).isoformat()
                await db.episodes.update_one({"slug": doc["slug"]}, {"$set": doc}, upsert=True)
            logger.info("Seeded %d episodi/interviste", len(SEED_EPISODES))
    except Exception as e:
        logger.error("Seed error: %s", e)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()