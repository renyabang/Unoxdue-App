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

## Backlog (ordine stretto richiesto dall'utente, messaggio #205)
- **P1 — Step 3: Archivio completo YouTube** via Data API (backfill paginato playlist Uploads,
  anti-duplicati, gestione stati video, webhook PubSubHubbub/WebSub per i futuri video). Richiede YOUTUBE_API_KEY utente.
- **P1 — Step 4: Classificazione AI + generazione automatica** (classifica episodio/intervista/short,
  trascrizioni, capitoli, titoli/meta SEO, structured data).
- **P1 — Step 5: Generazione automatica grafica pronostici** (template HTML/SVG -> export PNG/WebP
  orizzontale, quadrato, 9:16; nessun dato sensibile utente/bookmaker).
- **P2 — Step 6: Risultati, storico e pubblicazione condizionata** (aggiornamento risultati,
  stato complessivo schedina, log storico, auto-pubblicazione).
- **P2 — Step 7: Integrazioni Rassegna stampa (Perplexity) e comparatore quote (Odds API)**,
  in Demo finché l'utente non fornisce le chiavi.

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
