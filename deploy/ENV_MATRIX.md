# UnoXdue — Matrice variabili d'ambiente (NOMI, nessun valore segreto)

Le variabili reali vivono SOLO sul server (`.env`, secret del provider, env di Docker Compose o secret manager).
Nel repository resta solo `.env.example` con valori vuoti. Questo documento è una mappa di riferimento.

| Variabile | Obbligatoria | Usata da | Note |
|---|---|---|---|
| `SITE_URL` | ✅ | backend (canonical/OG/sitemap), build React (`REACT_APP_BACKEND_URL`) | Dominio pubblico definitivo, es. `https://unoxdue.net` |
| `MONGO_URL` | ✅ | backend (`config_db`) | In Compose forzata a `mongodb://mongo:27017` |
| `DB_NAME` | ✅ | backend | Default `unoxdue` |
| `JWT_SECRET` | ✅ | auth (firma token + cifratura Fernet OAuth) | Segreto forte, mai default in prod |
| `ADMIN_EMAIL` | ✅ | seed admin | |
| `ADMIN_PASSWORD` | ✅ | seed admin (hash pbkdf2) | Solo bootstrap; poi cambio forzato/rotazione |
| `EMERGENT_LLM_KEY` | ⚠️ funzionale | OCR schedine + generazione SEO/trascrizioni | Senza: AI/OCR non operativi |
| `VISION_MODEL` | — | OCR | Default `gpt-5.4` |
| `YOUTUBE_CHANNEL_ID` | ⚠️ | sync YouTube | |
| `YOUTUBE_API_KEY` | ⚠️ | YouTube Data API v3 (archivio/sync) | Senza: fallback RSS demo |
| `GOOGLE_OAUTH_CLIENT_ID` | ⚠️ | OAuth sottotitoli/trascrizioni | |
| `GOOGLE_OAUTH_CLIENT_SECRET` | ⚠️ | OAuth | |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | — | OAuth (fallback; i token reali sono cifrati nel DB) | |
| `WEBSUB_HUB` | — | PubSubHubbub | Default hub Google |
| `WEBSUB_SECRET` | — | verifica firma WebSub | |
| `PERPLEXITY_API_KEY` | ⚠️ | rassegna stampa | Senza: provider fixture demo |
| `SPORT_RESULTS_API_PROVIDER` | — | settlement risultati | `fixture` (demo) o `football-data` (reale) |
| `SPORT_RESULTS_API_URL` | — | provider risultati | |
| `SPORT_RESULTS_API_KEY` | ⚠️ | settlement reale | Senza: solo fixture |
| `ODDS_API_PROVIDER`/`ODDS_API_URL`/`ODDS_API_KEY` | — | DEPRECATO/DISATTIVATO | Le quote vengono dall'OCR della grafica |
| `OPENAI_AUDIO_API_KEY` | — | trascrizione audio opzionale | |
| `CRON_SECRET` | ⚠️ | endpoint cron protetti (`/api/cron/*`) | Necessaria per scheduler esterno |
| `CORS_ORIGINS` | — | (attualmente NON letta dal codice: server usa `["*"]`) | ⚠️ Restringere il CORS nel codice prima del lancio |

Legenda: ✅ obbligatoria · ⚠️ richiesta per la relativa funzione · — opzionale/con default.
