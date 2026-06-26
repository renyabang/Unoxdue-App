# Deploy UnoXdue su hosting esterno (Docker + Nginx)

Stack: **React (SPA admin) + FastAPI + Jinja2 (SSR pubblico) + MongoDB**, dietro **Nginx**.
Emergent è usato SOLO come ambiente di sviluppo/test. Questo percorso rende il sito portabile e
mantiene il routing ibrido: **pubblico = SSR**, **/admin = SPA React**.

> ⚠️ Perché non l'hosting gestito Emergent per il pubblico: l'ingress gestito instrada tutto ciò che
> non è `/api/*` alla build statica React, quindi le URL pubbliche pulite (`/episodi/...`) verrebbero
> servite dalla SPA e NON dall'SSR. Con Nginx controlliamo noi il routing.

---

## 1. File di deploy (creati/verificati)

| File | Ruolo |
|---|---|
| `Dockerfile.backend` | Backend FastAPI + SSR. Multi-stage: ricompila il CSS Tailwind condiviso e installa Chromium (Playwright) per le grafiche. Healthcheck su `/api/health`. |
| `Dockerfile.admin` | Web tier: build React (SPA admin) + Nginx (reverse proxy + routing SSR). Healthcheck su `/admin`. |
| `deploy/nginx.conf` | Routing definitivo (pubblico→SSR, `/api/`→FastAPI, `/admin/`→React, fallback pubblico→404 SSR). |
| `docker-compose.yml` | Orchestrazione `mongo` + `backend` + `web`; volumi persistenti `mongo_data` e `backend_uploads`. |
| `.env.example` | Template variabili (valori reali SOLO sul server). |
| `deploy/start.sh` | Avvio con verifica variabili obbligatorie + attesa health backend. |
| `scripts/backup_mongo.sh` | Backup MongoDB (formato `--archive`). |
| `scripts/restore_mongo.sh` | Restore da `--archive` o da cartella mongodump (`--out`). |
| `scripts/smoke_test.sh` | Checklist post-deploy (status + SSR/SPA per ogni route chiave). |
| `scripts/build_ssr_css.sh`, `scripts/fetch_fonts.py` | Build CSS SSR / font locali (riprodotti anche nel Dockerfile). |

---

## 2. Matrice di routing (gestita da `deploy/nginx.conf`)

| URL pubblica | Destinazione | Tipo |
|---|---|---|
| `/` | `→ /api/seo/home` | SSR |
| `/il-podcast/` | `→ /api/seo/il-podcast` | SSR |
| `/episodi/` · `/episodi/{slug}/` | `→ /api/seo/episodi[...]` | SSR |
| `/episodi/{slug}/trascrizione/` | `→ /api/seo/episodi/{slug}/trascrizione` | SSR |
| `/interviste/` · `/interviste/{slug}/` · `…/trascrizione/` | `→ /api/seo/interviste[...]` | SSR |
| `/pronostici/` · `/pronostici/serie-a/{stagione}/giornata-{n}/` | `→ /api/seo/pronostici[...]` | SSR |
| `/team/` · `/team/{slug}/` | `→ /api/seo/team[...]` | SSR |
| `/parlano-di-noi/`, `/contatti/`, `/collaborazioni/`, `/privacy/`, `/cookie/` | `→ /api/seo/...` | SSR |
| **qualsiasi altra URL pubblica (anche inesistente)** | `→ /api/seo$request_uri` (catch-all) | **404 HTML SSR** |
| `/sitemap.xml`, `/video-sitemap.xml`, `/robots.txt` | `→ /api/...` | FastAPI |
| `/live/` | `→ /api/live` (302 redirect gestito da admin) | FastAPI |
| `/api/*` (incl. `/api/static/css/unoxdue.css`, `/api/static/fonts/*.woff2`, `/api/uploads/*`) | FastAPI | API/SSR asset |
| `/admin`, `/admin/*` (refresh incluso) | `index.html` React | SPA (noindex) |
| asset build React (`/logo.jpg`, `/static/*`, favicon, manifest) | filesystem | statico |

**Garanzie**: nessun fallback pubblico restituisce `index.html` della SPA; le route pubbliche inesistenti
danno **404 HTML reale** (noindex) dal backend; le URL tecniche `/api/seo/...` restano interne (mai in
canonical/sitemap). Le URL pulite con slash finale sono mappate alle route backend **senza** slash finale
(niente redirect 307 che farebbero trapelare `/api/seo/...`).

---

## 3. Variabili necessarie (`.env`, dal template `.env.example`)

Obbligatorie: `SITE_URL`, `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.
LLM/AI: `EMERGENT_LLM_KEY` (o chiave OpenAI nel connettore), `VISION_MODEL`.
Integrazioni: `YOUTUBE_CHANNEL_ID`, `YOUTUBE_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN`,
`WEBSUB_HUB`, `WEBSUB_SECRET`, `PERPLEXITY_API_KEY`, `SPORT_RESULTS_API_PROVIDER/URL/KEY`,
`OPENAI_AUDIO_API_KEY`, `CRON_SECRET`. (Deprecate/disattivate: `ODDS_API_*`.)

> 🔐 In `docker-compose.yml`, `MONGO_URL`/`DB_NAME` sono forzati al servizio interno `mongo`.
> I segreti NON vanno nel repo: usa `.env` sul server, i secret del provider, le env di Compose o un secret manager.
> ⚠️ **CORS**: il codice usa attualmente `allow_origins=["*"]`. Da **restringere** al dominio prima del lancio definitivo.

---

## 4. Requisiti minimi del server
- Linux x86_64, **Docker + Docker Compose v2**.
- **2 vCPU / 4 GB RAM** consigliati (Chromium headless per le grafiche è il componente più pesante).
- ~5 GB disco (immagini + Mongo + uploads). Volume persistente per `mongo_data` e `backend_uploads`.
- Porte 80/443 aperte; dominio puntato al server.

---

## 5. Installazione e avvio
```bash
git clone <repo> unoxdue && cd unoxdue
cp .env.example .env
# Compila .env (SITE_URL=dominio reale, JWT_SECRET, ADMIN_PASSWORD, chiavi API...)
bash deploy/start.sh           # build + up -d + attesa health backend
# equivalente manuale:
docker compose up -d --build
docker compose ps
docker compose logs -f backend
```
Servizi: `mongo`, `backend` (FastAPI:8001 interno), `web` (Nginx:80 = reverse proxy + SSR routing + SPA admin).
Il seed iniziale (team/contenuti/pronostici) parte all'avvio SOLO se le collezioni sono vuote.

## 6. DNS
- Record **A** (e **AAAA** se IPv6) di `unoxdue.net` → IP del server.
- `www` opzionale: CNAME → `unoxdue.net` (gestisci il redirect www↔apex nel proxy TLS).
- Propaga prima di richiedere il certificato TLS.

## 7. HTTPS
Il container `web` espone HTTP:80. Termina TLS davanti, una delle due:
- **Caddy/Traefik** come reverse proxy TLS automatico verso `web:80`; oppure
- **Nginx host + Certbot**: `certbot --nginx -d unoxdue.net -d www.unoxdue.net`, proxy verso `127.0.0.1:80`.
Dopo HTTPS, imposta `SITE_URL=https://unoxdue.net` e ricostruisci (`docker compose up -d --build web`).

## 8. Backup e restore
```bash
# Backup (archivio singolo)
DB_NAME=unoxdue MONGO_URL=mongodb://localhost:27017 bash scripts/backup_mongo.sh
#   -> ./backups/unoxdue-YYYYmmdd-HHMMSS.archive
# In Docker (DB nel container mongo):
docker compose exec -T mongo sh -c 'mongodump --db unoxdue --archive' > backups/unoxdue-$(date +%F).archive

# Restore (--drop): da archivio o da cartella mongodump
DB_NAME=unoxdue bash scripts/restore_mongo.sh backups/unoxdue-YYYYmmdd-HHMMSS.archive
docker compose exec -T mongo sh -c 'mongorestore --drop --archive' < backups/unoxdue-XXXX.archive
```
Backup automatico consigliato: cron giornaliero che esegue `backup_mongo.sh` + copia off-site.

## 9. Smoke test post-deploy
```bash
bash scripts/smoke_test.sh https://unoxdue.net <slug-episodio> <slug-team>
```
Verifica per ogni route: status, render **SSR vs SPA**, e che le route pubbliche siano SSR, `/admin` SPA,
le route inesistenti **404 HTML** (non 200 SPA), `/api/health` 200, sitemap/robots 200.
Controlli manuali extra: `curl -s URL | grep '<h1'`, `grep canonical`, `grep 'application/ld+json'`.

## 10. Rollback
- **Immagini taggate**: builda con tag (`docker build -t unoxdue-backend:<git-sha> ...`) e in caso di problemi
  riavvia la versione precedente (`docker compose up -d` puntando al tag buono).
- **Codice**: ogni step su Emergent crea un checkpoint; in alternativa usa i tag/commit Git del repo.
- **Dati**: ripristina l'ultimo `.archive` con `scripts/restore_mongo.sh` (`--drop`).
- **Veloce**: `docker compose down` (mantiene i volumi) → ripristina immagine/tag precedente → `up -d`.
  `docker compose down -v` cancella i volumi (DB+uploads): usare solo per reset totale.

---

## Note tecniche
- **CSS SSR**: ricompilato nel `Dockerfile.backend` (stage node) da `frontend/src/**` + `backend/templates/**`
  → `backend/static/css/unoxdue.css`. Font locali in `backend/static/fonts/*.woff2` (no CDN). Cache-busting `?v=<mtime>`.
- **Grafiche pronostici**: Playwright/Chromium installato in immagine; in Docker usa il path browser di default
  (in Emergent `/pw-browsers`). Output in `backend/uploads/` → volume `backend_uploads`.
- **Scheduler esterno**: cron del server chiama endpoint protetti, es.
  `curl -X POST "https://unoxdue.net/api/cron/youtube?secret=$CRON_SECRET"`,
  `.../api/cron/press?secret=...&schedule=weekly`, `.../api/cron/settle?secret=...&season=...&round=...`.
- **Health**: backend `GET /api/health`, DB `GET /api/health/db`.
