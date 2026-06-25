# Deploy UnoXdue su hosting esterno

Stack: **React (build statico) + FastAPI + Jinja2 (SSR) + MongoDB**, dietro **Nginx**.
Emergent e' usato solo come ambiente di sviluppo/test. Il progetto e' portabile.

## 1. Requisiti
- Docker + Docker Compose
- Un dominio (es. `unoxdue.net`) puntato al server
- (consigliato) Certbot/Let's Encrypt o un proxy TLS davanti a Nginx

## 2. Configurazione
```bash
cp .env.example .env
# Compila: NEXT_PUBLIC_SITE_URL, SITE_URL (dominio reale), JWT_SECRET,
# ADMIN_PASSWORD, EMERGENT_LLM_KEY (o chiave OpenAI), CRON_SECRET e le API che hai.
```
`SITE_URL` e `NEXT_PUBLIC_SITE_URL` DEVONO essere il dominio pubblico definitivo:
canonical, Open Graph, sitemap e link interni useranno solo URL pulite (niente `/api/seo/`).

## 3. Avvio con un comando
```bash
docker compose up -d --build
```
Servizi: `mongo`, `backend` (FastAPI:8001), `frontend` (Nginx:80 con reverse proxy + SSR routing).

## 4. Routing definitivo (gestito da `deploy/nginx.conf`)
| URL pubblica | Sorgente |
|---|---|
| `/` | SSR `/api/seo/home` |
| `/il-podcast/` | SSR |
| `/episodi/` e `/episodi/[slug]/` | SSR |
| `/interviste/` e `/interviste/[slug]/` | SSR |
| `/pronostici/` e `/pronostici/serie-a/[stagione]/giornata-[n]/` | SSR |
| `/team/` e `/team/[slug]/` | SSR |
| `/parlano-di-noi/` | SSR |
| `/sitemap.xml`, `/video-sitemap.xml`, `/robots.txt` | FastAPI |
| `/admin` e `/admin/*` | React SPA (non indicizzato) |
| `/api/*` (incl. `/api/static/css/unoxdue.css`, `/api/static/fonts/*.woff2`) | FastAPI |
| asset SPA (`/logo.jpg`, `/hosts/*`, `/team/*.jpg`, JS/CSS del build React) | statici dal build |

> Nota nginx: la location API usa `location ^~ /api/` così le richieste come
> `/api/static/css/unoxdue.css` o `/api/static/fonts/*.woff2` vanno al backend e NON vengono
> intercettate dalla regex degli asset statici (che altrimenti darebbe 404).

Le URL tecniche `/api/seo/...` sono interne: non vanno nei canonical ne' nelle sitemap.

## 4.bis CSS condiviso e font (pagine SSR)
Il design delle pagine SSR usa lo **stesso CSS Tailwind** del frontend React, ma servito come file
statico locale (niente CDN, niente generazione lato browser):
- `Dockerfile.backend` è **multi-stage**: lo stage `css-build` (node:20) ricompila il CSS
  analizzando `frontend/src/**` + `backend/templates/**` e produce `backend/static/css/unoxdue.css`
  (minificato, classi inutilizzate rimosse). L'immagine NON dipende da CSS pre-generati nell'ambiente di sviluppo.
- I **font sono ospitati localmente** in `backend/static/fonts/*.woff2` (Anton, Archivo, Inter — subset
  latin + latin-ext). Sono asset sorgente versionati nel repo.
- **Cache busting**: il backend serve gli asset con `?v=<mtime>` (helper `asset()` in `backend/seo.py`).
- Build locale (per l'anteprima): `bash scripts/build_ssr_css.sh` (usa la stessa CLI standalone del Docker).
- Per ri-scaricare i font: `python scripts/fetch_fonts.py`.

## 4.ter Grafiche pronostici (Playwright/Chromium)
Le grafiche social (Step 5) sono renderizzate da HTML/CSS/SVG con Playwright/Chromium headless -> PNG + WebP.
- Dipendenze Python: `playwright`, `qrcode`, `pillow`, `httpx` (in `backend/requirements.txt`).
- Il `Dockerfile.backend` installa il browser con `python -m playwright install --with-deps chromium`.
- In sviluppo Emergent i browser sono in `/pw-browsers` (auto-rilevato da `backend/graphics.py`); in Docker si usa il path di default.
- Font e immagini (logo, foto tipster) sono embeddati in base64 a runtime -> rendering deterministico, niente attese di rete. Gli asset brand sono in `backend/static/public/` (copiati dal frontend) cosi' il backend è autosufficiente anche in Docker.
- Le immagini generate sono salvate in `backend/uploads/graphics/...` e servite da `/api/uploads/...`.
- Una sola istanza Chromium viene avviata e riusata; viene chiusa allo shutdown del backend.

## 4.quater /live/ (destinazione QR redirezionabile)
La route `/live/` reindirizza (302) verso una destinazione gestita dall'admin (Twitch / live YouTube /
ultimo episodio / URL personalizzata). In produzione Nginx la inoltra al backend
(`location ~ ^/live/?$ { proxy_pass .../api/live; }`); in dev si usa `/api/live`.

## Sicurezza credenziali
La password admin NON è mai in chiaro in report/log/seed. È solo in `ADMIN_PASSWORD` (env).
Rotazione: `python scripts/rotate_admin.py` (nuova password casuale + invalidazione JWT via token_version).

## 5. TLS / dominio
Mettere un proxy TLS (Caddy/Traefik/Nginx+Certbot) davanti, oppure terminare HTTPS sul load balancer e inoltrare alla porta 80 del container `frontend`.

## 6. Backup e seed dati
```bash
# Backup
bash scripts/backup_mongo.sh         # crea ./backups/unoxdue-YYYYmmdd.archive
# Restore
mongorestore --archive=backups/unoxdue-XXXX.archive --nsInclude='unoxdue.*'
```
Il seed iniziale (team, contenuti, pronostici) viene applicato all'avvio solo se le collezioni sono vuote.

## 7. Automazioni / scheduler esterno
Lo scheduler del nuovo hosting (cron) deve chiamare endpoint protetti del backend:
```bash
# Riconciliazione YouTube (ogni 15-30 min)
curl -X POST "https://unoxdue.net/api/cron/youtube?secret=$CRON_SECRET"
```
Tutta la logica resta nel backend e visibile nel pannello `/admin`.

## 8. Health check
- Backend: `GET /api/health`
- Database: `GET /api/health/db`

## 9. Note di portabilita'
- L'OCR usa `emergentintegrations` + Emergent LLM key (installabile via pip). Per piena
  indipendenza si puo' sostituire con il client OpenAI ufficiale in `backend/automations.py`
  (funzione `ocr_slip`) usando una propria `OPENAI_API_KEY`.
- Nessuna altra dipendenza e' legata all'hosting Emergent.
