# UnoXdue — Guida al deploy esterno (Docker)

Due varianti:
- **HTTP semplice** (`docker-compose.yml`): Nginx in ascolto su `:80`, TLS demandato a un proxy/LB esterno.
- **HTTPS automatico** (`docker-compose.tls.yml`): Caddy davanti, certificati Let's Encrypt automatici.

> ⚠️ Lo stack NON è stato collaudato su un server Docker esterno reale in questo ambiente
> (qui non c'è un Docker host con DNS/porte pubbliche). I file sono pronti: vanno avviati e
> verificati sul server di destinazione. Il routing SSR/SPA è quello già validato in `deploy/nginx.conf`.

## 0. Prerequisiti
- Server Linux con Docker + Docker Compose plugin.
- DNS: record A/AAAA di `unoxdue.net` **e** `www.unoxdue.net` → IP del server.
- Porte `80` e `443` aperte e libere.

## 1. Configurazione `.env`
```bash
cp .env.example .env
```
Compila almeno:
- `SITE_URL=https://unoxdue.net`
- `DOMAIN=unoxdue.net`  e  `ACME_EMAIL=tuo@indirizzo.it` (per i certificati)
- `CORS_ORIGINS=https://unoxdue.net`
- `JWT_SECRET=` (stringa lunga e casuale)
- `ADMIN_EMAIL=` / `ADMIN_PASSWORD=` (solo bootstrap; al primo accesso cambia password)
- chiavi funzionali: `EMERGENT_LLM_KEY`, `YOUTUBE_API_KEY`, `PERPLEXITY_API_KEY`,
  `SPORT_RESULTS_API_PROVIDER=football-data` + `SPORT_RESULTS_API_KEY`, ecc.

## 2. Staging (consigliato prima della produzione)
Usa la CA di staging di Let's Encrypt per evitare i rate-limit mentre verifichi DNS/porte:
```bash
CADDY_ACME_CA=https://acme-staging-v02.api.letsencrypt.org/directory \
  docker compose -f docker-compose.tls.yml up -d --build
docker compose -f docker-compose.tls.yml ps
docker compose -f docker-compose.tls.yml logs -f caddy
```
I certificati di staging non sono "trusted" dal browser: serve solo a confermare che il flusso ACME funziona.

## 3. Produzione (HTTPS reale)
```bash
docker compose -f docker-compose.tls.yml up -d --build
```
Caddy ottiene i certificati reali, applica gli header di sicurezza e il redirect `www → unoxdue.net`.

Verifica:
```bash
bash scripts/smoke_test.sh https://unoxdue.net
curl -I https://www.unoxdue.net      # atteso: 308 -> https://unoxdue.net
curl -fsS https://unoxdue.net/api/health
```

## 4. Backup & restore del database (persistente)
Il volume `mongo_data` persiste tra i riavvii. La cartella host `./backups` è montata in `mongo:/backups`.
Backup pianificato (cron sull'host, es. ogni notte alle 3):
```bash
0 3 * * * cd /opt/unoxdue && docker compose -f docker-compose.tls.yml exec -T mongo \
  mongodump --uri="mongodb://localhost:27017" --db="$DB_NAME" --archive=/backups/unoxdue-$(date +\%Y\%m\%d).archive
```
Restore:
```bash
docker compose -f docker-compose.tls.yml exec -T mongo \
  mongorestore --uri="mongodb://localhost:27017" --archive=/backups/unoxdue-AAAAMMGG.archive --drop
```
In alternativa, dall'host con accesso diretto: `bash scripts/backup_mongo.sh` e `bash scripts/restore_mongo.sh`.

## 5. Health check
- backend: `GET /api/health` (usato dal healthcheck del container).
- web (Nginx + SPA): `GET /admin`.
- Caddy dipende dal `web` "healthy" prima di avviarsi.

## 6. Aggiornamenti
```bash
git pull
docker compose -f docker-compose.tls.yml up -d --build
```
Il CSS SSR viene ricompilato dentro l'immagine backend (stage Tailwind); nessun file generato va committato.

## 7. Note di sicurezza
- CORS ristretto a `https://unoxdue.net` (env `CORS_ORIGINS`, letto da `server.py`).
- Header HSTS/nosniff/SAMEORIGIN/Referrer-Policy/Permissions-Policy + CSP in `deploy/Caddyfile`.
- La password admin si ruota con `python scripts/rotate_admin.py` (aggiorna `.env` e invalida i token).
- Nessun segreto nel repo: solo `.env.example` con valori vuoti.
