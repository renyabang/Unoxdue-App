# UnoXdue — PRD / Stato di progetto

## Problema (problem statement)
Ricostruire **UnoXdue**, sito podcast sulla Serie A, ottimizzato SEO e fortemente
automatizzato. Funzioni chiave: sync automatico YouTube, generazione contenuti via AI,
sistema automatico di pronostici (schedine) con OCR (OpenAI Vision) che estrae le giocate
da immagini, rimuove i dati sensibili, recupera le quote da un comparatore e genera grafiche
brandizzate UnoXdue. Lingua di tutta l'app e delle interazioni: **ITALIANO**.

## Architettura (concordata con l'utente)
- **Frontend React SPA** (`/app/frontend`): sito pubblico (mock UI) + CMS sicuro su `/admin`.
- **Backend FastAPI + MongoDB** (`/app/backend`): API `/api/...`, job automatici, e
  **SSR Jinja2** per le pagine pubbliche SEO (`/api/seo/...`).
- **Deploy esterno** previsto via Docker + Nginx (`/app/deploy/nginx.conf`): in produzione le
  URL pulite (`/episodi/...`) vengono servite dall'SSR FastAPI; `/admin` dalla SPA React.
- **Limite ambiente dev (accettato dall'utente):** in preview le URL pulite vengono instradate
  alla SPA React; le pagine SSR si testano su `/api/seo/...`. NON modificare il routing dell'ambiente.

## Integrazioni
- OpenAI Vision (OCR schedine) — Emergent LLM Key via `emergentintegrations` (modello gpt-5.4). ATTIVO.
- YouTube — attualmente sync via feed RSS. (Data API completa = task futuro, richiede API key utente.)
- Perplexity (rassegna stampa) — DEMO (manca chiave utente).
- Odds API (comparatore quote) — DEMO (manca chiave utente).

## Stato implementazione
### Completato
- [27/2026 sessioni precedenti] Replica React pixel-perfect del sito pubblico.
- Backend FastAPI + MongoDB; seed contenuti/team/pronostici; indici univoci.
- SSR Jinja2 pagine pubbliche (home, episodio, intervista, archivi, pronostici, team, pagine statiche).
- CMS React `/admin`: login JWT, cambio password forzato al primo accesso, dashboard,
  contenuti, schedine/OCR, log, integrazioni.
- Sicurezza admin: hash pbkdf2, must_change_password, token_version (invalidazione), rate limiting.
- Sync YouTube via RSS; OCR schedine Vision (senza dati sensibili); sitemap/video-sitemap/robots dinamici.
- **Step 0 (sicurezza) e Step 1 (E2E admin) — testati (backend 32/32, frontend 19/19).**
- **[25/06/2026] Step 2 — Uniformare il design SSR + chiusura deploy. COMPLETATO + verificato.**
  - Build CSS condiviso con Tailwind (scansione `frontend/src/**` + `backend/templates/**`),
    output minificato `backend/static/css/unoxdue.css`, classi inutilizzate rimosse, cache-busting `?v=mtime`.
  - Font ospitati localmente (`backend/static/fonts/*.woff2`, subset latin + latin-ext): Anton, Archivo, Inter. Nessun CDN.
  - Template Jinja2 riscritti con le stesse classi/colori/font/spaziature/radius del React
    (navbar dark, hero con glow + marquee, card, slip pronostici, footer 3 colonne, pagine profilo team).
  - Macro condivise (`backend/templates/_macros.html`: icone SVG lucide, card, marquee) per evitare duplicazione.
  - SEO preservato: canonical, JSON-LD, OG, H1 presenti su tutte le pagine; 404 corretto.
  - **Deploy:** `Dockerfile.backend` ora MULTI-STAGE: ricompila il CSS dentro l'immagine (stage node) senza
    dipendere da file generati in Emergent; `nginx.conf` con `location ^~ /api/` (asset SSR .css/.woff2 vanno al backend).
    Validato eseguendo lo stage di build da cartella pulita → output byte-identico al CSS committato (incl. prefisso -webkit Safari).
    ⚠️ Docker daemon NON disponibile nell'anteprima Emergent: non è stato possibile eseguire `docker build/run` reale qui.
  - Script riproducibili: `scripts/fetch_fonts.py`, `scripts/build_ssr_css.sh` (CLI standalone, coerente col Docker).
- **[25/06/2026] Step 4 — Classificazione AI e generazione automatica (P1). COMPLETATO + testato.**
  - Modulo `backend/ai_content.py` con gpt-5.4-mini via Emergent LLM key (emergentintegrations).
  - Genera SOLO da titolo+descrizione: classificazione (episodio/intervista/short + ospite), seo_title,
    meta_description, h1, intro, sommario PROVVISORIO, topics, seo_keywords. NIENTE trascrizioni/citazioni/capitoli.
    `transcription_status: "pending"` su ogni contenuto; contenuti falliti → stato "da_verificare" (max 1 retry automatico).
  - Endpoint: `/api/admin/ai/settings` (GET/PUT), `/api/admin/ai/process/{slug}` (POST), `/api/admin/ai/process-batch` (POST).
    Limiti giornaliero/mensile, stima costo+token loggati in automation_logs (kind="ai_generate").
  - Hook automatico (OFF di default) dopo la sync YouTube: elabora i nuovi episodi/interviste se `auto_on_sync` attivo (cap 10).
  - Admin UI: pagina "AI / SEO" (`AIGen.jsx`) con interruttori (globale, auto-sync, short, componenti, limiti, modello),
    pulsante batch; in "Contenuti" colonna AI + pulsante "Elabora con AI" per riga + batch archivio.
  - Testato: testing_agent frontend 6/6 flussi PASS (100%); backend verificato via curl (process singolo + batch + SSR riflette i contenuti).
- **[25/06/2026] Sicurezza — rotazione credenziali admin.**
  - Password admin ruotata e archiviata SOLO in `ADMIN_PASSWORD` (env). Mai in chiaro in report/log/seed/risposte.
  - Procedura: `scripts/rotate_admin.py` (password casuale, hash pbkdf2 nel DB, token_version++ => JWT precedenti invalidati, must_change_password=false).
- **[25/06/2026] Step 4 (miglioramento) — Contenuti: filtro stato AI + badge "Da verificare" + rielabora selezionati. TESTATO.**
  - Filtro (tutti/da_verificare/errore/non elaborato/elaborato/pubblicato), badge contatore cliccabile, ordinamento problematici-primi,
    checkbox multi-selezione + "Rielabora selezionati" (batch su slug specifici). 
- **[25/06/2026] Step 5 — Generazione automatica grafiche pronostici (P1). COMPLETATO + testato.**
  - `backend/graphics.py`: HTML/CSS/SVG -> Playwright/Chromium headless -> PNG + WebP, 3 formati (1200x630, 1080x1080, 1080x1920 @2x).
  - Contenuti: logo + watermark UnoXdue, foto/nome tipster (fallback iniziali), Serie A/stagione/giornata, partite/mercati/selezioni,
    quote reali o "Quota non disponibile", quota totale, disclaimer 18+/gioco responsabile/quote variabili, data agg.
  - QR verso la pagina del pronostico (o /live/); leggibile, contrasto, spazio, non sovrapposto, con etichetta. Route `/live/` redirezionabile da admin.
  - Vietati esclusi: importo/bonus/vincita/saldo/ID/dati personali/branding operatore — si rende SOLO il dato strutturato (nessuna quota inventata).
  - Robustezza: auto-scala anti-taglio (1..6+ selezioni, nomi/mercati lunghi), una sola istanza Chromium riusata, timeout+retry, errori loggati (kind="graphics").
  - Admin: pagina "Grafiche" (anteprima 3 formati, genera/rigenera, download PNG/WebP, copia URL, retry, modifica dati pre-rigenerazione) + card /live/.
  - Testato: testing_agent frontend 10/11 -> dopo fix 11/11 (retest 100%); backend verificato via curl + screenshot reali dei 3 formati e casi limite.
  - Docker: `Dockerfile.backend` installa Chromium (`playwright install --with-deps chromium`); asset brand in `backend/static/public/`.

## Backlog (ordine stretto richiesto dall'utente, messaggio #205 + #342)
- **P0 — Step 3: Archivio completo YouTube / WebSub / OAuth / trascrizioni** ✅ COMPLETATO + testato (giugno 2026, demo).
- **P1 — Step 7A: Comparatore quote reale** (verifica struttura provider: ID stabile, settlement, eventi sospesi;
  connettore separato SPORT_RESULTS_API se manca il settlement). PROSSIMO.
- **P2 — Step 6: Risultati, storico e pubblicazione condizionata** (storico quote, override manuali,
  calcolo esito vinta/persa/void, auto-pubblicazione condizionata).
- **P2 — Step 7B: Rassegna stampa (Perplexity)** — news rilevanti UnoXdue + ospiti.
- **P3 — Refactoring finale**: split server.py in routes/services/models/integrations/jobs/utility
  (solo tecnico, senza cambiare comportamento testato).

### [giugno 2026] Step 3 — Archivio YouTube completo, WebSub, OAuth, trascrizioni (P0). COMPLETATO + testato (demo).
- Nuovo modulo `backend/youtube.py`: connettore Data API v3 (channels.list -> uploads playlist,
  playlistItems.list paginato, videos.list batch 50 per durata ISO8601), upsert anti-duplicati,
  classificazione (short esclusi). Senza YOUTUBE_API_KEY -> fallback feed RSS marcato `demo:true`.
- WebSub/PubSubHubbub: subscribe/unsubscribe verso hub, callback PUBBLICO `/api/youtube/websub/callback`
  (GET echo hub.challenge, POST parse Atom + verifica firma HMAC sha1/sha256), log eventi + stato sottoscrizioni.
- OAuth (struttura) per sottotitoli: `GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN`; captions.list+download (it preferito),
  transcription_status pending->done SOLO con sottotitoli reali (mai inventati); unavailable/error gestiti.
- Endpoint admin: `/api/admin/youtube/stats|backfill|websub|websub/subscribe|oauth/status|transcripts|transcript/{slug}`.
- Admin UI nuova pagina "YouTube" (`frontend/src/admin/YouTube.jsx`): statistiche canale, backfill+toggle auto-publish,
  pannello WebSub (callback/topic, iscrivi/disiscrivi, eventi), OAuth+tabella trascrizioni con stato e "Recupera".
  Voce di menu + route in AdminApp; riga "YouTube OAuth" in Integrazioni.
- Env aggiunte: GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN, WEBSUB_HUB, WEBSUB_SECRET.
- Dipendenze: google-api-python-client, google-auth, google-auth-oauthlib (in requirements.txt).
- Testato: backend via curl (stats demo, backfill RSS 15, websub GET/POST+HMAC valida/non valida, oauth, transcripts);
  frontend testing_agent 100% (iteration_6.json), zero errori JS, non-regressione admin OK.
- BLOCCATO da credenziali utente: stats/backfill reali (YOUTUBE_API_KEY) e trascrizioni reali (GOOGLE_OAUTH_*).



## File chiave
- `backend/auth.py` (sicurezza), `backend/seo.py` (+helper `asset()` versioning), `backend/server.py`
  (route, mount `/api/static`), `backend/templates/*.html` (+ `_macros.html`), `backend/automations.py`.
- `frontend/tailwind.ssr.config.js`, `frontend/src/ssr.css` (build CSS SSR), `frontend/src/admin/*`.
- `scripts/build_ssr_css.sh`, `scripts/fetch_fonts.py`, `deploy/nginx.conf`, `DEPLOY.md`.

## Note per il deploy
Dopo modifiche ai template/classi, in locale rieseguire `bash scripts/build_ssr_css.sh` per
rigenerare `backend/static/css/unoxdue.css` (anteprima Emergent). In produzione NON serve:
il multi-stage `Dockerfile.backend` ricompila il CSS automaticamente dentro l'immagine.
I font sono già in `backend/static/fonts/` (versionati nel repo).
TODO deploy futuro: split di `server.py` in `routes/`+`models/` quando il file diventa difficile da mantenere.

## Specifiche Step 5 (grafiche pronostici) — da implementare
- Watermark/logo UnoXdue discreto ma sempre visibile; branding coerente nei 3 formati (orizzontale, quadrato, 9:16).
- QR code nelle grafiche social che NON punta direttamente a Twitch ma a una URL stabile sul dominio:
  `https://unoxdue.net/live/` (grafiche generali) oppure la pagina del pronostico specifico quando disponibile.
- Route `/live/` redirezionabile dal pannello admin verso: prossima diretta Twitch / live YouTube / ultimo episodio /
  altra destinazione → così si cambia il target senza rigenerare le immagini già pubblicate.
- QR: realmente leggibile, contrasto sufficiente, non coprire quote/selezioni, testato su smartphone,
  etichetta breve ("Guarda la puntata" / "Segui la diretta"), escluso quando la grafica è troppo affollata.
