# UnoXdue — Migrazione FARM → Next.js (Emergent) — Approccio "PONTE"

> **Obiettivo:** andare online su Emergent Hosting con SEO perfetta, **riusando il 100%
> del lavoro già fatto** (SSR Jinja2 + FastAPI + Object Store). Il frontend Next.js fa
> solo da **ponte**: recupera lato server l'HTML già pronto da FastAPI `/api/seo/*` e lo
> serve ai motori. **NON si riscrive il sito.**

---

## ⚠️ REGOLA D'ORO PER L'AGENTE DEL NUOVO PROGETTO
**NON ricostruire il sito pubblico da zero.** Tutto il sito pubblico (home, episodi,
interviste, pronostici, team, trascrizioni, pagine istituzionali, sitemap, robots, JSON-LD,
Schema.org) è GIÀ generato server-side da FastAPI sotto `/api/seo/*` e `/api/sitemap.xml`,
`/api/robots.txt`. Il tuo compito è SOLO:
1. Mantenere il backend FastAPI **identico** (cartella `backend/`, porta 8001, prefisso `/api`).
2. Creare un frontend Next.js che **inoltri (proxy/rewrite) le URL pubbliche all'SSR FastAPI**.
3. Portare il **pannello admin React** (già esistente) dentro Next.js come area client su `/admin`.
4. Ripristinare il database (dump incluso) e le variabili d'ambiente.

I componenti React del sito pubblico (`frontend/src/components/*`, `frontend/src/pages/PublicSite.jsx`,
`frontend/src/mock.js`) sono solo una **vetrina con dati finti**: NON servono e vanno scartati.

---

## A) BACKEND — copiare così com'è
- Copia l'intera cartella `backend/` nel nuovo progetto, invariata. Punti chiave già pronti:
  - SSR Jinja2: `backend/seo.py`, `backend/seo_content.py`, `backend/templates/*.html`.
  - Route SSR pubbliche: `GET /api/seo/home`, `/api/seo/episodi`, `/api/seo/episodi/{slug}`,
    `/api/seo/episodi/{slug}/trascrizione`, `/api/seo/interviste(...)`, `/api/seo/pronostici`,
    `/api/seo/pronostici/serie-a/{season}/giornata-{round}`, `/api/seo/team`, `/api/seo/team/{slug}`,
    `/api/seo/il-podcast`, `/api/seo/collaborazioni`, `/api/seo/contatti`, `/api/seo/privacy`,
    `/api/seo/cookie`, `/api/seo/parlano-di-noi`, e catch-all `/api/seo/{full_path}` (404 SSR stilizzato).
  - SEO file: `GET /api/sitemap.xml`, `/api/video-sitemap.xml`, `/api/robots.txt`.
  - Redirect QR live: `GET /api/live` (e `@app.get("/live")`).
  - **Object Store già integrato**: `backend/storage.py` + endpoint pubblico `GET /api/media/{path}`
    (copertine, loghi, grafiche). Usa `EMERGENT_LLM_KEY`. **Non modificare.**
- `requirements.txt` invariato. Include Playwright/Chromium (generazione copertine):
  in fase di build eseguire `playwright install --with-deps chromium`.

## B) FRONTEND NEXT.JS — il "ponte"
Implementa il routing pubblico→SSR con il meccanismo Next.js più adatto al template Emergent
(consigliato: **rewrites in `next.config.js`**; in alternativa `middleware.ts` o un Route Handler
catch-all che restituisce `new Response(html, { status, headers: {'content-type':'text/html'} })`).

**Regole di routing (identiche al `deploy/nginx.conf` di riferimento):**
| URL pubblica                                   | Inoltra a (FastAPI)                                  |
|------------------------------------------------|------------------------------------------------------|
| `/`                                            | `/api/seo/home`                                      |
| `/sitemap.xml`                                 | `/api/sitemap.xml`                                   |
| `/video-sitemap.xml`                           | `/api/video-sitemap.xml`                             |
| `/robots.txt`                                  | `/api/robots.txt`                                    |
| `/live`, `/live/`                              | `/api/live`                                          |
| **qualsiasi altra URL pubblica** `/:path*`     | `/api/seo/:path*`  (il backend dà 404 SSR se assente)|

**Escludere dal ponte** (li gestisce Next.js): `/admin` e `/admin/*`, `/api/*`, gli asset Next (`/_next/*`),
e i file statici per estensione (`.js .css .png .jpg .webp .svg .ico .woff2 .json .map`).

- **Destinazione del proxy lato server**: usare l'URL interno del backend (es. `http://localhost:8001`)
  per le rewrites SSR; le chiamate `/api/*` del browser (admin) passano dal routing standard della piattaforma.
- Il proxy deve **propagare lo status code** (200/404) e l'header `content-type` della risposta FastAPI.

## C) ADMIN — portare il pannello React esistente
- Riusa **tutto** `frontend/src/admin/*` (AdminApp.jsx, api.js, Dashboard, Contents, Graphics,
  Predictions, PredictionsAI, Press, Results, SlipUploader, TranscriptSEO, YouTube, AIGen, Integrations,
  Logs, SitePages) e i componenti shadcn in `frontend/src/components/ui/*`.
- Montalo come area **client-only** su una rotta catch-all Next.js `/admin/[[...slug]]`
  (`dynamic(..., { ssr: false })`), mantenendo react-router-dom internamente OPPURE convertendo
  le rotte interne in rotte Next. L'admin è interamente client-side e parla via axios con `/api/*`.
- Base URL API in `admin/api.js`: usa la variabile env del backend del template Next.js
  (es. `process.env.NEXT_PUBLIC_BACKEND_URL`). Mantieni il prefisso `/api`.
- L'admin **non deve essere indicizzato** (è già escluso da robots: `Disallow: /admin`).

## D) DATABASE — ripristino contenuti reali
Il dump completo è in: **`backups/db_migration_<STAMP>/test_database/`** (vedi `backups/LATEST_DB_MIGRATION.txt`).
Contiene episodi, 13 trascrizioni reali, pronostici (incl. bozze AI), team, rassegna stampa, settings, ecc.

Nel nuovo progetto, ripristina nel database del progetto:
```bash
mongorestore --uri "$MONGO_URL" --nsInclude "test_database.*" \
  --drop backups/db_migration_<STAMP>/test_database
```
(se `DB_NAME` nel nuovo progetto è diverso da `test_database`, usa `--nsFrom 'test_database.*' --nsTo '<DB_NAME>.*'`).
Dopo il restore: verifica login admin; se la password non combacia con `ADMIN_PASSWORD`,
esegui `python scripts/rotate_admin.py` per riallinearla.

## E) OBJECT STORE — già pronto, nessuna rigenerazione necessaria (quasi)
- Le copertine/loghi caricati vivono nell'Emergent Object Store, **per-account** (stessa `EMERGENT_LLM_KEY`):
  restano accessibili dal nuovo progetto tramite `GET /api/media/{path}` (path con content-hash, stabili).
- **Dopo aver impostato il `SITE_URL` definitivo** (dominio di produzione), rigenera le copertine dal
  pannello admin (Grafiche → Genera/Rigenera): è idempotente (stesso content-hash → stesso oggetto)
  e aggiorna gli URL `og:image`/archivio al dominio corretto. Ri-estrai i loghi stampa se serve.

## F) VARIABILI D'AMBIENTE (reinserire nel nuovo progetto, valori dal progetto FARM attuale)
Backend:
`MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`, `SITE_URL`, `EMERGENT_LLM_KEY`, `VISION_MODEL`,
`JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `YOUTUBE_CHANNEL_ID`, `YOUTUBE_API_KEY`,
`PERPLEXITY_API_KEY`, `OPENAI_AUDIO_API_KEY`, `CRON_SECRET`,
`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REFRESH_TOKEN`,
`WEBSUB_HUB`, `WEBSUB_SECRET`, `SPORT_RESULTS_API_PROVIDER`, `SPORT_RESULTS_API_URL`,
`SPORT_RESULTS_API_KEY`, `ODDS_API_URL`, `ODDS_API_KEY`, `ODDS_API_PROVIDER`.
Frontend (Next.js): l'URL pubblico del backend (es. `NEXT_PUBLIC_BACKEND_URL`).
> ⚠️ Su Emergent le env si impostano nelle **impostazioni del progetto/deploy**, non in un file `.env`
> (il `.env` è escluso dal deploy). Senza env il backend risponde 520.

## G) CHECKLIST DI VERIFICA (prima del deploy)
- [ ] `/` → HTML SSR completo (NO `<div id="root">`), con H1, canonical, JSON-LD.
- [ ] `/episodi/`, `/interviste/`, `/pronostici/`, `/team/`, `/il-podcast/`, `/parlano-di-noi/` → 200 SSR.
- [ ] Pagina episodio/intervista singola + `/{...}/trascrizione/` → 200 SSR.
- [ ] `/pronostici/serie-a/2025-2026/giornata-38` → 200 SSR con `og:image` su `/api/media/...`.
- [ ] URL inesistente → **404** HTML SSR (mai la SPA).
- [ ] `/sitemap.xml`, `/video-sitemap.xml`, `/robots.txt` → 200 dal backend.
- [ ] `/admin` → pannello React, login OK, dashboard/contenuti/grafiche/pronostici-ai funzionanti.
- [ ] `/api/media/<copertina>` → 200 `image/webp`.
- [ ] Dopo dominio definitivo: `SITE_URL` aggiornato + copertine rigenerate.

---

### Prompt iniziale consigliato per l'agente del nuovo progetto Next.js
> "Migra questa app FARM a Next.js con approccio a PONTE, seguendo `MIGRATION_NEXTJS.md` alla lettera.
> NON ricostruire il sito pubblico: è già renderizzato server-side da FastAPI sotto `/api/seo/*`.
> Il frontend Next.js deve inoltrare (rewrites/proxy) tutte le URL pubbliche all'SSR FastAPI secondo la
> tabella di routing, propagando status code e content-type. Porta il pannello admin React esistente
> (`frontend/src/admin/*`) come area client su `/admin`. Mantieni il backend FastAPI invariato (porta 8001,
> prefisso `/api`, incluso `storage.py`/Object Store e gli endpoint `/api/seo/*`, `/api/media/*`, sitemap/robots).
> Ripristina il database dal dump in `backups/db_migration_<STAMP>/` e reimposta le variabili d'ambiente.
> Verifica tutta la checklist in `MIGRATION_NEXTJS.md` prima del deploy."
