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
| `/api/*` | FastAPI |
| asset (`/logo.jpg`, `/hosts/*`, `/team/*.jpg`, JS/CSS) | statici dal build |

Le URL tecniche `/api/seo/...` sono interne: non vanno nei canonical ne' nelle sitemap.

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
