"""Configurazione condivisa: client MongoDB, variabili ambiente, costanti.
Indipendente dall'hosting: tutto viene da variabili ambiente con fallback.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "unoxdue")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# URL pubblico del sito (canonical / OG / sitemap). In produzione = dominio reale.
SITE_URL = os.environ.get("SITE_URL", "http://localhost:3000").rstrip("/")

# Auth admin
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@unoxdue.net")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "unoxdue2026")

# Integrazioni / automazioni
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
VISION_MODEL = os.environ.get("VISION_MODEL", "gpt-5.4")
YOUTUBE_CHANNEL_ID = os.environ.get("YOUTUBE_CHANNEL_ID", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
ODDS_API_URL = os.environ.get("ODDS_API_URL", "")
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_API_PROVIDER = os.environ.get("ODDS_API_PROVIDER", "")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
OPENAI_AUDIO_API_KEY = os.environ.get("OPENAI_AUDIO_API_KEY", "")
CRON_SECRET = os.environ.get("CRON_SECRET", "")

# YouTube OAuth (sottotitoli/trascrizioni) e WebSub (PubSubHubbub)
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REFRESH_TOKEN = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")
WEBSUB_HUB = os.environ.get("WEBSUB_HUB", "https://pubsubhubbub.appspot.com/subscribe")
WEBSUB_SECRET = os.environ.get("WEBSUB_SECRET", "")

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
