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
- OpenAI Vision (OCR grafiche comparative pronostici) — Emergent LLM Key via `emergentintegrations` (modello gpt-5.4). ATTIVO.
- YouTube — sync RSS + Data API v3 (Step 3, demo finché manca YOUTUBE_API_KEY) + WebSub + OAuth sottotitoli (demo finché mancano GOOGLE_OAUTH_*).
- Perplexity (rassegna stampa) — ATTIVO (Perplexity Sonar 'sonar'; usa search_results + domain denylist + filtri data). Step 7B.
- **Comparatore quote esterno (The Odds API/Odds API) — DEPRECATO/DISATTIVATO.** Le quote provengono SOLO dall'OCR
  della grafica comparativa fornita dal team. `ODDS_API_*` restano come funzione futura disattivata, senza sviluppo prioritario.
- Risultati/stato eventi (Step 6) — da integrare con API-Football o equivalente SOLO per risultati/fixture/stato (non per quote).

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

## Backlog (ordine stretto richiesto dall'utente, messaggio #205 + #342 + correzione Step 7A)
- **P0 — Step 3: Archivio completo YouTube / WebSub / OAuth / trascrizioni** ✅ COMPLETATO + testato (giugno 2026, demo).
- **P1 — Step 7A (REVISIONATO): OCR grafiche comparative + persistenza quote** ✅ COMPLETATO + testato (giugno 2026).
  Le quote vengono dalla grafica del team (OCR Vision), NON da API esterne. The Odds API rimosso dal piano (funzione futura disattivata).
- **P2 — Step 6: Risultati, storico e pubblicazione condizionata** ✅ COMPLETATO + testato (giugno 2026, modalità fixture).
- **P2 — Step 7B: Rassegna stampa (Perplexity)** ✅ COMPLETATO + testato (giugno 2026, modalità fixture).
- **P3 — Refactoring finale**: split server.py in routes/services/models/integrations/jobs/utilities. Prima: checkpoint stabile,
  suite test, inventario endpoint, mappa dipendenze, backup DB. NON cambiare API/URL pubbliche/schema/comportamento automazioni.
  ⚠️ NON iniziare prima che i 3 flussi reali (Step 3, 6, 7B con chiavi) siano verificati: gli adapter potrebbero richiedere modifiche a modelli/servizi.

### Ordine concordato dopo Step 7B (messaggio utente)
1. inserimento credenziali YouTube API + Google OAuth → 2. test reale Step 3 → 3. inserimento provider risultati (SPORT_RESULTS_API_KEY + provider=apifootball) →
4. test reale Step 6 → 5. inserimento Perplexity → 6. test reale Step 7B → 7. test e2e completo → 8. backup+checkpoint → 9. refactoring finale.

### [25/06/2026] Step 7B REALE — Regole query Perplexity + primo test reale. COMPLETATO + testato (reale, e2e).
- PERPLEXITY_API_KEY inserita in `.env`. Provider reale attivo (`sonar`).
- `press.py` riscritto con le regole dell'utente ALLA LETTERA + configurazione modificabile dall'admin (`db.press_config`):
  - Query brand (5), team (4 nomi, mai da soli), ospiti dinamici dal DB (×2 forme), contenuti recenti (no intero archivio).
  - Finestre: ordinary=30gg (`search_recency_filter:"month"`), weekly=90gg (`search_after_date_filter`),
    backfill=24 mesi CALENDARIO (non 720gg fissi). Backfill una tantum.
  - Esclusioni via `search_domain_filter` denylist (`-unoxdue.net -youtube.com -twitch.tv -instagram.com -tiktok.com`) + filtro locale.
  - Fonte dati = `search_results` di Perplexity (URL realmente trovati), più affidabile dello structured output.
  - Pertinenza: rilevante solo se cita UnoXdue o riprende un contenuto UnoXdue; altrimenti FALSO POSITIVO (non associato, non pubblicato).
  - Dedup per URL canonica + titolo (copie/syndication); verifica raggiungibilità; confidence euristica; cap risultati (default 10).
  - NESSUNA pubblicazione automatica: stati found/review. Costo REALE letto da `usage.cost.total_cost`.
- Endpoint: `/admin/press/run` (mode + query manuale opzionale + max_queries/max_results), `/admin/press/config` (GET/POST).
- Admin `Press.jsx`: selettore finestra (Ordinaria/Estesa/Backfill), query manuale opzionale, riquadro statistiche (query eseguite,
  trovati, duplicati, irraggiungibili, validi, falsi positivi, salvati, costo reale), badge "Falso positivo" + motivo in anteprima.
- PRIMO TEST REALE (backfill 24 mesi, 14 query): 46 grezzi → 35 unici (11 duplicati) → 14 irraggiungibili → 6 validi, 28 falsi positivi,
  10 salvati (3 Trovato auto-linkati: Cosenzachannel→Baclet×2, Parmalive→Ceravolo; 7 Da revisionare). Costo REALE $0.0745. Nessuna pubblicazione automatica.
- Smoke test UI superato (login, lista 10, badge falso positivo + motivo, collegamenti auto). API e2e verificate via curl.

### [25/06/2026] Step 7B — Correzioni precisione (msg utente) + SECONDO test reale. COMPLETATO + verificato.
- (1) Facebook/x.com/twitter.com aggiunti ai domini esclusi. (2) Esclusione pagine non-articolo (homepage, tag/categoria/archivio/ricerca, sezioni generiche tipo `/reggio-calabria/`). (3) Soglia auto-link alzata a 0.85 (`auto_link_min_confidence`). (4) Auto-link SOLO con menzione esplicita UnoXdue + corrispondenza DB ANCORATA AL TITOLO. (5) Garritano (Baclet solo nel teaser) → revisione, non auto-link. (6) "Reggio Calabria Notizie"/pagine-lista → scartate come non-articolo. (7) Falsi positivi NON in editoriale: solo nel log tecnico `press_rejected`. (8) Funnel a categorie ESCLUSIVE (grezzi−duplicati=unici=social+non-articolo+irraggiungibili+FP+validi), con flag `funnel_balanced`.
- Pertinenza ora sul TESTO della pagina (un solo GET per candidato: raggiungibilità + contenuto), non sullo snippet variabile di Perplexity → recupera menzioni reali senza perdere precisione. Termini brand ristretti a `unoxdue`/`uno x due` (rimosso "uno per due" che generava falsi match).
- Scheduler: `POST /api/cron/press?secret=&schedule=weekly|monthly` (weekly=30gg, monthly=90gg; backfill NON automatico). Storico in `press_runs`; log tecnico `press_rejected`; endpoint `/admin/press/runs` e `/admin/press/rejected`. UI: selettore finestra, statistiche esclusive, suggeriti con conferma, pannello "Ultime esecuzioni", "Log tecnico (scartati)".
- SECONDO test reale (backfill, 14 query, sonar): grezzi 41 − dup 11 = 30 unici → social 0, non-articolo 6, irraggiungibili 3, FP 16, validi 5 (4 found auto-linkati Baclet/Ceravolo + 1 review Garritano). 0 menzioni reali perse. Costo REALE $0.074. Nessuna pubblicazione automatica. Modello resta `sonar` (A/B con sonar-pro solo se necessario).

### [25/06/2026] Step 3 — Pulizia archivio (esclusione Short/clip/teaser) + Fase B OAuth (flusso). COMPLETATO.
- Classificatore `classify_content` (automations.py): `youtube_format` (short|long_form, soglia ≤180s o #shorts) + `editorial_type` (episodio|intervista|clip|teaser|altro). Durata/formato prevalgono sulla parola "intervista". Ammessi sul sito solo episodio/intervista long_form.
- Esclusione automatica in sync (backfill + WebSub + RSS): short/clip/teaser → tabella tecnica `youtube_exclusions` (no contenuto editoriale, no AI, no SEO, no pagine/sitemap) + skip reimport via `is_excluded_video`.
- Backup DB: `/app/backups/backup_20260625_145312`. Pulizia eseguita (dry-run verificata): 13 conservati (11 episodi + 2 interviste, tutti >1600s) | 15 esclusi (13 clip + 2 teaser; 7 RSS pregressi + 8 API), 0 dubbi. Hard delete dalle collezioni editoriali. Endpoint `/admin/youtube/exclusions`.
- Verifica: sitemap 13 URL / 0 shorts, video-sitemap 13 / 0 shorts, home/SSR/API pubbliche 0 shorts. Nessun duplicato.
- Fase B OAuth implementata (`youtube_oauth.py`): flusso Authorization Code (access_type=offline, prompt=consent), token cifrati (Fernet da JWT_SECRET) in `db.youtube_oauth`, refresh automatico, verifica canale = YOUTUBE_CHANNEL_ID, status (connesso/canale/ultimo rinnovo/ultimo errore), endpoint start/callback/disconnect, UI admin (Connetti/Disconnetti/Riconnetti). Caption usa refresh token DB (fallback env). NESSUN refresh token incollato a mano. In attesa: GOOGLE_OAUTH_CLIENT_ID/SECRET dall'utente.

### [25/06/2026] Step 3 FASE A REALE — Import archivio YouTube (Data API v3). COMPLETATO + verificato.
- YOUTUBE_API_KEY inserita in `.env`. Channel ID `UCN85Yle0zaIKue4ymUj1OCQ` verificato (canale "unoXdue", 54 video, 36 iscritti, playlist uploads `UUN85Yle0zaIKue4ymUj1OCQ`).
- `youtube.py`: `_upsert_video` ora salva descrizione completa + `uploads_playlist`; `backfill` traccia errori, classificazione e quota reale; report arricchito.
- Backfill paginato (2 pagine, 50/pag): 54 trovati = 33 Shorts esclusi + 21 episodi/interviste (11 nuovi + 10 aggiornati). Dedup per `youtube_id`. 0 errori. Quota REALE: 5 unità (1 channels.list + 2 playlistItems + 2 videos.list) su 10.000/giorno.
- Salvati: titolo, descrizione, data, durata, miniature, playlist, stato. Nessuna trascrizione avviata. Contenuti già elaborati preservati (update solo metadati, type/status/SEO intatti). SSR verificato (/api/seo/episodi = 16 card, interviste Ceravolo/Baclet).
- Da decidere con utente: (a) affinare classify_video (durata ≤90s = short anche con parola "intervista"; ri-classificare clip 2-3 min); (b) pulizia 7 voci pregresse da feed RSS.

### [giugno 2026] Step 7B BIDIREZIONALE — Collegamento rassegna stampa ⇄ contenuti (P2). COMPLETATO + testato (fixture, e2e).
- `press.py`: `links` come LISTA (auto + manuale), `_associate_all` (multi-match team/episodi/interviste), `_merge_links`
  (preserva i manuali al re-run), `set_link(action add/remove)` (rimozione/correzione senza eliminare l'articolo), `link_options`,
  `published_for(slug)` (box: published + reachable + linked, dedup canonica, recenti), `published_archive` (link interni multipli puliti).
- SSR: box "Ne hanno parlato" su `episode.html`/`team_member.html` (solo published+reachable+linked); nuova `press.html` per
  "Parlano di noi" con link esterno (target _blank + rel noopener) e link interni puliti (/episodi//interviste//team/, non /api/seo/).
  `seo.render_episode/render_team_member` accettano `press`; `render_press_archive`. Endpoint SSR episodi/interviste/team passano `published_for`.
- Admin `Press.jsx`: sezione "Contenuti collegati" con chip (auto/manual), aggiunta manuale via select (link_options), rimozione per chip.
- `server.py`: `/admin/press/link` con action add/remove, `/admin/press/link-options`.
- Test e2e (10/10 via curl) + frontend testing_agent 100% (iteration_10.json): articolo pubblicato↔intervista, box SSR, link esterno rel noopener,
  link interno dall'archivio, review/discarded non pubblici, URL duplicata non duplicata, irraggiungibile escluso, rimozione associazione aggiorna le pagine, HTML box senza JS.
- `press.py`: astrazione `PressProvider` (search) + `FixturePressProvider` (demo deterministico) + `PerplexityPressProvider`
  (predisposto, attivo solo con PERPLEXITY_API_KEY). `get_provider()` factory sostituibile. Pipeline `run_search`:
  dedup per URL canonica, verifica raggiungibilità (HEAD/GET + retry), associazione a team/episodio/intervista/ospite,
  stati found/verified/review/published/discarded/error, log. `set_status` (anteprima→pubblica/verifica/scarta), `set_link`, `list_all`.
  Salva SOLO metadati + sintesi originale (testata, titolo, url, canonical_url, data, summary, linked, query, detected_at, status, confidence). MAI testo integrale.
- `server.py`: `/admin/press/status|run|list|set-status|link`. `GET /api/press` + SSR `/parlano-di-noi` mostrano SOLO status=published (+ legacy senza status).
- `Press.jsx` (admin "Rassegna stampa"): ricerca, badge demo, tabella con stato/linked/irraggiungibile, filtri per stato, anteprima + pubblica/verifica/scarta.
- Ricerca reale disattivata finché manca PERPLEXITY_API_KEY (provider fixture).
- Testato: pipeline via curl (4 trovati, 2 verified via associazione, 1 error per URL irraggiungibile, dedup/re-run idempotente, pubblicazione→visibilità pubblica);
  frontend testing_agent 100% (iteration_9.json), non-regressione admin OK.

### [giugno 2026] Step 6 — Risultati, storico e pubblicazione condizionata (P2). COMPLETATO + testato (fixture).
- `results_provider.py`: astrazione `ResultsProvider` (get_events/get_event/get_results) + `FixtureResultsProvider` (dataset
  deterministico: finished/postponed/suspended/cancelled/AET/PEN) + `ApiFootballResultsProvider` (predisposto, attivo solo con
  SPORT_RESULTS_API_PROVIDER=apifootball + SPORT_RESULTS_API_KEY). `get_provider()` factory: sostituibile senza toccare il motore.
  Stati normalizzati, normalizzazione squadre/match, score ft/ht/et/pen.
- `settlement.py`: motore interno. `settle_selection` (1X2, Doppia Chance, DNB, Over/Under, GG/NG; combinati/sconosciuti -> manual_review),
  `aggregate_pick` (multipla: persa se una persa; pending se una pending; void/postponed/suspended/cancelled trattati come void),
  storico versionato `settlement_history`, audit `settlement_audit`, `apply_publish_rule` (publish_min_valid 1/2/3),
  correzioni manuali protette dal re-settle (manual=True). Mai AI come fonte, mai valori inventati. Log + retry.
- `server.py`: `/admin/results/status|settings|settle|{season}/{round}|correct` + cron `/cron/settle`. `add_pick` applica la pubblicazione condizionata.
- `Results.jsx` (admin "Risultati"): provider status + badge demo, selettore publish_min_valid, selezione giornata, esegui settlement,
  badge esito per giocata/selezione, correzione manuale per selezione/giocata, riga storico/audit. Pagina pubblica `prediction.html`:
  badge esito (Vinta/Persa/Void/Rinviata/Sospesa/Annullata/Da verificare) per giocata e per selezione.
- Env: SPORT_RESULTS_API_PROVIDER (default 'fixture'), SPORT_RESULTS_API_URL, SPORT_RESULTS_API_KEY.
- Testato: motore via curl (won/lost/void/postponed/suspended/cancelled/manual_review, aggregazione, correzione manuale non sovrascritta,
  storico+audit, publish 1/2/3); frontend testing_agent 100% (iteration_8.json), non-regressione admin OK.
- BLOCCATO solo per dati reali: serve SPORT_RESULTS_API_KEY (+ provider=apifootball) per i risultati veri.

### [giugno 2026] Step 7A REVISIONATO — OCR grafiche comparative + persistenza quote (P1). COMPLETATO + testato.
- `automations.py`: nuovo `OCR_PROMPT` per grafiche comparative (tipster, competition, round, type, total_odds, raw_text,
  selections con match/date/market/pick/odds/confidence + bookmakers[{bookmaker,odds,confidence,bbox}]). `_normalize_extracted`
  pulisce i dati VIETATI (importo/bonus/vincita/saldo/dati personali) a ogni livello, normalizza tipi e calcola `needs_review`
  (confidence < 0.6 o quota mancante). `ODDS_DISCLAIMER` + `MAPPING_VERSION`. NIENTE valori inventati.
- `server.py`: `POST /admin/predictions/ocr` persiste `slip_uploads` {id, image_path, ocr_raw, extracted, mapping_version, status, uploaded_at}
  e ritorna upload_id+data+raw_text+disclaimer. `add_pick` estesa con source_image/ocr_upload_id/mapping_version/needs_review + odds_disclaimer;
  marca l'upload come confermato. `GET /admin/slip-uploads` per audit.
- `SlipUploader.jsx`: revisione editabile con tabella comparativa bookmaker (add/remove), badge confidence %, flag "Da verificare",
  testo OCR audit, immagine sorgente, disclaimer, salvataggio (con stato saving).
- Pagina pubblica `prediction.html`: chip comparativi bookmaker per selezione + badge "Da verificare" + disclaimer esatto. CSS SSR ricompilato.
- Grafica social (`graphics.py`): disclaimer aggiornato al testo obbligatorio.
- Testato: OCR reale (Vision) su grafica comparativa di test estrae correttamente e IGNORA importo/bonus/vincita; add_pick + SSR verificati via curl;
  frontend testing_agent 100% (iteration_7.json), non-regressione admin OK.

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



### [25/06/2026] Step 3 FASE B REALE — OAuth YouTube collegato + trascrizioni reali. COMPLETATO + verificato.
- GOOGLE_OAUTH_CLIENT_ID/SECRET inseriti; URI redirect registrato (`/api/admin/youtube/oauth/callback`); l'utente ha collegato il canale "unoXdue".
- Test trascrizioni su 2 video OK, poi BATCH su tutti: **13/13 episodi/interviste con `transcription_status=done`** (sottotitoli IT reali, ~1,78M caratteri), 0 errori, 0 Short/clip/teaser coinvolti. Quota YouTube ampiamente nei limiti.

### [25/06/2026] P1 — Generazione SEO dalle trascrizioni reali (map->reduce + anti-invenzione). COMPLETATO + testato.
- `srt_utils.py`: parsing SRT -> segmenti con timestamp reali; dedup overlap auto-caption (es. 60k->29k char); chunking allineato ai timestamp; verifica citazioni (substring robusto).
- `ai_transcript.py`: pipeline MAP (per chunk: summary/topics/entità people-teams-competitions/capitoli con timestamp da marcatori [t=...]/citazioni verbatim) -> REDUCE (sintesi finale: type, guest, h1, seo_title, meta_description, intro, sommario esteso, topics, key_passages). gpt-5.4-mini default, **fallback gpt-5.4 max 1 volta** se i controlli falliscono. Anti-invenzione: citazioni solo se presenti nel testo; capitoli solo con timestamp reali (snap+dedup<60s, cap 15); entità solo se presenti. **Nomi propri ancorati al TITOLO** (fix hallucination 'Baclet'->'Buckley').
- Workflow **anteprima -> confronto -> pubblica** (campo `ep.ai_preview`, non sovrascrive il pubblico finché l'admin non pubblica). Bundle trascrizione in `db.transcriptions` (srt, clean, segments, lang). Costo/token loggati (`automation_logs` kind=`ai_transcript`).
- Endpoint admin: `/api/admin/transcripts/seo/status|generate/{slug}|preview/{slug}|publish/{slug}|generate-batch`.
- SSR: sezione "Capitoli" (deep-link YouTube al timestamp) + "Citazioni" (con speaker) + CTA "Trascrizione della puntata" su episode.html; nuova **pagina canonica** `/{episodi|interviste}/{slug}/trascrizione/` (template `transcript.html`: TOC capitoli, ricerca interna JS, testo pulito in paragrafi nell'HTML SSR). JSON-LD `hasPart`/`Clip` con `startOffset` + `transcript` URL.
- Admin: pagina "Trascrizioni SEO" (`TranscriptSEO.jsx`): tabella stato (Pubblicato/Anteprima/Da generare), genera/anteprima/pubblica/rigenera, batch, badge modello/costo/needs_review.
- Testato: pipeline su 3 contenuti (Quinto/Decimo/Baclet) — capitoli 12-15, citazioni 6, costo ~$0.008-0.02/contenuto; SSR verificato (15 Clip JSON-LD, 136 paragrafi pagina trascrizione); testing_agent frontend 100% (iteration_11.json); fix nome ospite verificato (0 'Buckley').
- DA FARE: generare/pubblicare gli altri 10 episodi (dopo verifica utente sui primi 2).

### [25/06/2026] P1 v2 — Sommario strutturato `summary_sections` (H2/H3) + editor admin + report QC. COMPLETATO.
- Modello dati: `summary_sections` [{id, level(2/3), heading, paragraphs[], source_segment_ids[], confidence, order}] + `toc` (H2). Campo `summary` (flat) mantenuto come fallback. Migrazione non distruttiva (SSR fa fallback al vecchio summary se mancano le sezioni). Snapshot `ai_preview_prev` per confronto/rollback.
- Parametri editoriali: intro 80-120p; sommario adattivo alla durata (<=45min 400-600, 45-90 500-750, >90 650-900); capitoli 6-10 (max 12, dedup <90s); citazioni 2-5 (max 6 interviste), >=6 parole, verbatim, speaker solo se certo; cap 6 H2 (merge eccedenze, niente perdita testo). Qualita' > soglie (no padding).
- SSR semantico: `<section class="episode-summary">` con `<h2 id>`/`<h3 id>` (slug univoci), indice "In questa puntata" se >=3 H2; presenti nell'HTML SSR (verificato via render). Endpoint admin PUT `/preview/{slug}/sections` (riordino/edit). Validazione UI blocca save se titolo vuoto/duplicato/H3-first/no-paragrafi.
- Generazione 13/13 anteprime (NON pubblicate, live intatto): 0 falliti, 0 duplicazioni SEO (h1/title/meta/slug), costo totale ~$0.21 (~347k token); 5 approvati auto, 8 da revisionare (quasi tutti per sommario sotto target su live lunghi/ripetitivi + 2 intro a 74/78p; i 2 con 8 H2 corretti a 6). Citazioni 0 non supportate, timestamp 0 dubbi, gerarchia corretta. Testing_agent frontend 100% (iteration_12.json), editor sezioni validato.
- DA FARE: approvazione utente (singola/batch) per pubblicare; eventuale tuning lunghezza sommario per >90min.

### [25/06/2026] Pubblicazione 8 contenuti SEO + Step 6 risultati REALI football-data.org. COMPLETATO + testato.
- **Pubblicati 8/13** (Ceravolo, Baclet, Primo, Sesto, Secondo, Ottavo, Quinto, Decimo) dopo controllo finale 0 errori bloccanti (slug unici, canonical, H1/title/meta non duplicati, gerarchia H2/H3, timestamp reali, citazioni verbatim, JSON-LD valido). Smoke test: tutte 200, sitemap (+pagine `/trascrizione/`, escaping XML) e video-sitemap aggiornate; le 5 in revisione hanno `/trascrizione/` 404. `ai_preview_prev` per rollback.
- Stato `approved_short`: sommari sotto target ma completi (>=450p su >90min, >=3 H2) NON sono errori (regola "qualita' > soglie"). 4 dei 5 in revisione sono `approved_short` (Nono/Settimo/Quarto/Terzo); 1 `needs_review` (Speciale Mondiali, sommario/intro corti).
- **Step 6 REALE:** `FootballDataResultsProvider` (football-data.org v4, comp SA, header X-Auth-Token; mapping squadre con alias internazionale->inter, hellas verona->verona; status/score; MAI quote). Provider attivo (`SPORT_RESULTS_API_PROVIDER=football-data`), ApiFootball e Fixture mantenuti. Motore settlement esteso: 1X2/DC/DNB/OU/GG-NG/**Multigol**/**Risultato Esatto** auto; combinati/marcatori/**statistici (corner/cartellini/tiri)** -> `manual_review`. **Dry-run** (no scrittura DB) backend + UI admin (anteprima -> "Applica e scrivi"). Attribuzione "Data provided by football-data.org" sulle pagine pronostici.
- Testato: provider reale 38a 2024-25 (10 match, mapping ok); settlement dry-run su tutti i mercati (won/lost/void/manual_review corretti, no scrittura); casi void/postponed/suspended/cancelled ok; testing_agent frontend 100% su TranscriptSEO editor (iteration_12) e Results dry-run (iteration_13).
- DA FARE: pubblicare i 4 `approved_short` (su ok utente); espandere Speciale Mondiali; test E2E completo; backup/checkpoint; poi refactoring. Slug `studio-serie-a-38-giornata` (Primo 29a) da correggere con redirect.

## File chiave
- `backend/auth.py` (sicurezza), `backend/seo.py` (+`render_transcript`, JSON-LD capitoli, `_results_attribution`, breadcrumb_label/website_title),
  `backend/server.py` (route, mount `/api/static`), `backend/templates/*.html` (+ `_macros.html`, `transcript.html`), `backend/automations.py`.
- **P1 SEO trascrizioni:** `backend/srt_utils.py` (parsing SRT/dedup/chunking), `backend/ai_transcript.py`
  (map->reduce + anti-invenzione + summary_sections), `frontend/src/admin/TranscriptSEO.jsx`.
- **Step 6 risultati:** `backend/results_provider.py` (FootballDataResultsProvider + alias squadre), `backend/settlement.py`
  (1X2/DC/DNB/OU/GG-NG/Multigol/Risultato Esatto + dry-run), `frontend/src/admin/Results.jsx`.
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

### [26/06/2026] Fix 404 SSR robusto + TEST deploy produzione Emergent + pacchetto Docker/Nginx esterno. COMPLETATO + validato.
- **404 SSR robusto**: nelle route SSR pubbliche (`ssr_prediction`, `ssr_team_member`, `ssr_episode`, `ssr_interview`, `_render_transcript_page`) sostituiti i `raise HTTPException(404)` con `return _render_ssr_404()` (HTMLResponse 404, noindex, H1/nav/footer/JSON-LD). Verificato su backend diretto E URL pubblico preview (prima il proxy restituiva JSON).
- **Test produzione Emergent gestito (msg utente #282)** su `https://sportivo.emergent.host` → **CASO A**: lavoro 100% salvo (preview SSR + DB integri = backup `predeploy_20260625_213039`, diff 0). MA: (1) routing gestito instrada TUTTE le URL pubbliche pulite alla **SPA React** (`<div id="root">`), non all'SSR → test FALLITO per il pubblico; anche route inesistenti danno 200 SPA. (2) backend `/api/*` in prod → **520** (origin down), causa probabile = `.env` escluso dal deploy (regola `.gitignore` aggiunta pre-deploy) → diagnosi `probable_missing_environment_variables` (non certezza assoluta: log runtime prod non ispezionabili). Decisione utente: NON collegare dominio, NON usare Emergent gestito per il pubblico, passare a **Docker + Nginx esterno**.
- **`.env` fuori da git** (solo `.env.example` con valori vuoti). `.gitignore` aggiornato (`.env`, `**/.env`, `**/.env.*`, `!**/.env.example`).
- **Pacchetto deploy esterno preparato+validato (Docker non disponibile in Emergent, validazione statica+funzionale):**
  - `deploy/nginx.conf` riscritto: pubblico→SSR mappato SENZA slash finale, `/api/`→FastAPI, `/admin/`→React (refresh ok), `/sitemap|robots`→FastAPI, **fallback pubblico → `/api/seo$request_uri` (404 HTML SSR, MAI la SPA)**. Aggiunte route `/episodi|interviste/{slug}/trascrizione/`, pagine statiche (contatti/collaborazioni/privacy/cookie), `/live` come match esatti.
  - Bug latente corretto: in location regex `proxy_pass` non può avere URI statica (era nel blocco `/live/`). `.html` aggiunto alla regex asset così `try_files .../index.html` serve il file (non ricade sul fallback SSR).
  - `Dockerfile.admin` (nuovo, sostituisce `Dockerfile.frontend`): build React + Nginx. `Dockerfile.backend` invariato (multi-stage CSS + Chromium). `docker-compose.yml` aggiornato (servizi mongo/backend/web, healthcheck, volumi `mongo_data` + `backend_uploads`). **`.dockerignore` nuovo** (esclude `**/.env`, node_modules, backups, uploads, __pycache__, .git → nessun segreto nell'immagine).
  - Script: `deploy/start.sh` (avvio+health+check var obbligatorie), `scripts/restore_mongo.sh`, `scripts/smoke_test.sh`. `.env.example` allineato a TUTTE le chiavi reali del backend (segreti vuoti). `DEPLOY.md` riscritto (10 sezioni: file, matrice routing, env, requisiti server, install, DNS, HTTPS, backup/restore, smoke test, rollback).
  - **Validazione**: `nginx -t` OK; backend `import server` OK; dipendenze chiave presenti; **simulazione routing funzionale** con Nginx temporaneo (config deploy) → backend reale: pubblico 200 SSR, `/admin/*` 200 SPA (refresh ok), inesistente 404 HTML SSR, asset 200 da filesystem, api/sitemap/robots OK. Scan segreti nei file deploy = 0.
  - ⚠️ **CORS** `allow_origins=["*"]` in `server.py`: da RESTRINGERE al dominio prima del lancio definitivo (non modificato ora per non toccare il codice app).
  - DA FARE deploy: l'utente esegue `docker compose up` reale sul server esterno (qui non disponibile) + smoke test; disattiva/elimina il deployment Emergent temporaneo (preferire Stop/Unpublish alla cancellazione; NON cancellare progetto/preview/DB/checkpoint/backup).

### Backlog SEO/contenuti concordato (msg utente, dopo deploy esterno) — DA FARE nell'ordine:
3. Pulizia record Pronostici (card 2026-2027 38ª da controllare→draft/noindex/fuori sitemap se test). 4. Copertine automatiche pronostici (template HTML/CSS/SVG→WebP 1200×675 + 1200×1200, brand UnoXdue, no logo bookmaker; OG/Twitter/ImageObject). 5. SEO archivio `/pronostici/` + archivio stagione `/pronostici/serie-a/2025-2026/`. 6. Testi unici per pagina giornata (450-900 parole, dati reali). 7. Pipeline Perplexity contestuale (fonti reali, anti-allucinazione, anti-duplicazione, keyword map predisposta DataForSEO/Ahrefs). 8. Contenuti SEO pagine principali (home/episodi/interviste/team/parlano-di-noi/collaborazioni). 9. Pagina "Il podcast" (hero+format+voci+FAQ, 700-1000 parole). 10. Team homepage layout (Antonello in alto orizzontale; sotto Marziano/Micuccio/Ninja; ripristinare Il Ninja) + casing corretto + rimuovere badge "Made with Emergent". 11. Aggiungere "Sono Gianmarco" (slug sono-gianmarco, IG _.sonogianmarco_, solo in /team/, non in home, campi bio/ruolo modificabili, bozza finché mancano dati). 12. Parlano di noi (solo verificate/raggiungibili/approvate, logo testata con fallback, bidirezionale, no pubblicazione auto). 13-14. Audit + test Schema.org per tutte le tipologie pagina (matrice @graph, @id stabili, no tipi inventati). 15. Esecuzione ordinata, poi E2E + backup + checkpoint.

### [26/06/2026] PARITÀ VISIVA — Homepage SSR campione allineata al design React approvato. COMPLETATO (in attesa approvazione utente).
- Obiettivo: portare il design React nei template Jinja2 SSR senza tornare alla SPA. Home = pagina campione.
- `_macros.html` ampliato: icone (radio/target/users/clapperboard/download/arrow_up_right) + macro componenti `content_card` (con variante dark), `feature_card`, `host_card`, `tipster_card`, `slip_card`, `press_card`, `social_card`, `marquee_strip`.
- `home.html` riscritto con tutte le sezioni in parità React: Hero (glow+marquee), Il podcast (About + 4 feature), Interviste (cards dark), Ultimi episodi (3 card), **Pronostici = schedine reali** (slip cards da `prediction.picks` con foto tipster, selezioni, quote — NIENTE riquadri neri), Team (host Antonello in evidenza + 3 tipster), Parlano di noi (condizionale, oggi vuoto perché press in stato found/review), Social (sezione arancione 4 piattaforme).
- `seo.render_home(episodes, interviews, team, prediction, press)` esteso: host/tipster ordinati via `HOME_TIPSTER_ORDER=[il-marziano, sono-micuccio, il-ninja]`, foto tipster mappate sulle schedine, contenuti statici (HOME_ABOUT/FEATURES/SOCIALS), JSON-LD @graph (Organization/WebSite/PodcastSeries con @id stabili).
- `server.py ssr_home` ora fetcha team+prediction(non bozza, più recente)+press(published_archive). 
- Pulizia dati: prediction **2026-2027 r38 → status `bozza`** (record di test). Escluso da home, archivio `/pronostici/`, sitemap; pagina singola in `noindex` (render_prediction+prediction.html con flag noindex). Verificato: archivio mostra solo 2025-2026.
- Brand: nessun "Uno X due" nel sorgente (wordmark = `Uno<span orange>X</span>due` → "UnoXdue"). "Uno X due" resta solo come termine di matching in `press.py` (non display).
- Verifiche: home SSR 200, 68KB, nessun `<div id="root">`, 7 sezioni presenti, ordine team Antonello→Marziano→Micuccio→Ninja, foto 200, slip con quote, screenshot desktop+mobile OK.
- DA FARE dopo approvazione homepage: applicare stessa parità a /episodi/, /interviste/, /pronostici/ (archivio+giornata), singolo episodio, trascrizione, /team/, /parlano-di-noi/, /il-podcast/. Poi backlog SEO/contenuti e deploy esterno. Copertine WebP generate (OG/social) per card archivio pronostici = backlog item 4 (sulla home si usano già le schedine).

### [26/06/2026] BLOCCO 1 — Parità visiva /il-podcast/, /pronostici/, pagina giornata + copertine WebP automatiche. COMPLETATO (in attesa approvazione utente).
- **/il-podcast/**: nuovo template `il_podcast.html` + `seo.render_il_podcast(team)`. Parità React: hero (dark+marquee), "Cos'è UnoXdue" + 4 feature card, "Come è fatta una puntata", "Le voci" (host_card Antonello + 3 tipster_card ordinati), "Tutti i canali" (social), FAQ visibili (6) con `FAQPage` JSON-LD. Testo originale, diverso dalla home. JSON-LD @graph WebPage+PodcastSeries. Route ricablata (prima usava render_page generico).
- **/pronostici/ (archivio)**: template `pronostici_archive.html` collegato via nuova `seo.render_pronostici_archive(predictions)`. Raggruppa per stagione (desc) + giornata (desc); card `pred_card` con copertina WebP reale (fallback CSS se assente); sezione metodologia (4 paragrafi) + 3 feature; FAQ visibili (4). JSON-LD `CollectionPage`+`ItemList` e `FAQPage`. og:image = prima copertina disponibile. Route ricablata (prima render_archive generico). Bozza 2026-2027 esclusa.
- **Pagina giornata** (`prediction.html`): copertina iniettata in `og:image` (+`og:image:width/height`+`og:image:alt`), `twitter:image` e JSON-LD `Article.image` come `ImageObject`. `seo.render_prediction` usa `_cover_image(p)` (fallback `/logo.jpg`).
- **Copertine WebP automatiche** (`graphics.py`): `generate_cover` ridisegnata — IDEMPOTENTE (content_hash su stagione/giornata/competizione/titolo/logo + `COVER_TEMPLATE_VERSION="1"`), path deterministici (URL stabili, nessun duplicato), metadati salvati (url, w, h, format, bytes, hash, template_version, generated_at, source). Formati: 1200×675 (OG/pagina/archivio) + 1200×1200 (social). `auto_generate_cover` con regole eleggibilità (solo status `pubblicato`, stagione/giornata valide, ≥1 pronostico reale, no demo/fixture; mai bozze/anteprime/noindex/test) — NON blocca mai la pubblicazione (errori solo loggati, fallback logo/CSS). `set_manual_cover` (source=manual, mai sovrascritta in automatico).
- **Endpoint admin**: `POST /admin/covers/generate` (idempotente, `force` per rigenerare), `/admin/covers/manual` (upload, source=manual), `/admin/covers/revert` (ripristina automatica). Hook auto-gen in `add_pick` e `upsert_prediction`.
- **Admin UI** (`Graphics.jsx` `CoverCard`): anteprima 2 formati + metadati, badge sorgente (Automatica/Manuale), "Genera/Rigenera", "Usa immagine manuale" (con conferma), "Ripristina automatica" (con conferma), stato + errori. `api.js`: coverGenerate/coverManual/coverRevert.
- **Verifiche**: copertina 2025-2026 38ª generata (WebP 60KB/74KB), idempotenza (skipped=unchanged), bozza→ineligible, ciclo manuale→protezione→revert OK, file serviti (image/webp), og:image/twitter:image/ImageObject iniettati, archivio mostra copertina, CSS SSR ricompilato (65KB). Screenshot desktop+mobile di tutte e 3 le pagine + entrambe le copertine OK.
- **DA FARE**: approvazione utente del Blocco 1 → poi Blocco 2 (/episodi/, singolo episodio, /trascrizione/, /interviste/, singola intervista) → Blocco 3 (/team/, profilo, /parlano-di-noi/, pagine istituzionali, footer) → backlog SEO/contenuti → deploy Docker/Nginx esterno.

### [26/06/2026] BLOCCO 1 — chiusura con correzioni richieste dall'utente. COMPLETATO E APPROVATO.
- Fix spazio vuoto archivio /pronostici/ (rimosso `min-h-[40vh]`): il layout si adatta al numero di giornate (verificato desktop).
- Miniatura copertine: aggiunto formato `thumb` 600×338 WebP a `COVER_FORMATS`, usata come immagine nelle card archivio; `horizontal` resta per OG/pagina, `square` per social. Tutte e 3 generate/idempotenti.
- Pagina /il-podcast/: testi (hero_lead, about, format_text, features, faqs) ora EDITABILI da admin via `db.settings.il_podcast` (fallback ai default `seo.il_podcast_defaults()`). Endpoint `GET/PUT /admin/site-content/il-podcast`. Nuova pagina admin "Pagine" (`SitePages.jsx`, rotta `/admin/pagine`). Icona `mic` aggiunta a `feature_card`. Verificato: override→SSR riflette→reset→default.
- Verifica fallback errore (record usa-e-getta, dati pubblici intatti): generazione fallita → ok=False + errori salvati, NESSUNA eccezione (pubblicazione non bloccata), pagina resa con fallback logo; admin mostra badge "Errore parziale" + "Rigenera".
- NOTA OPERATIVA: account admin `admin@unoxdue.net` ha `must_change_password=true` → al prossimo login dovrà impostare nuova password prima di vedere dashboard, tab "Pagine" e controlli copertine in "Grafiche".

### BLOCCO 3 — specifiche vincolanti registrate (DA IMPLEMENTARE nel Blocco 3, NON ora):
- **Homepage Team**: solo Antonello (card grande orizzontale in alto), poi 3 card grandi nell'ordine Il Marziano, Sono Micuccio, Il Ninja. Le foto devono mostrare i gesti delle mani: Marziano=`1`, Micuccio=`X`, Ninja=`2`. NON ritagliare nascondendo mani/gesti. Riferimento visivo: file `1-WhatsApp Image 2026-06-25 at 10.54.40.jpeg` (recuperare con get_assets_tool).
- **Pagina /team/**: 1) Antonello separato in alto; 2) Marziano+Micuccio+Ninja insieme, grandi, stesso ordine homepage; 3) sezione separata "altri componenti e collaboratori"; 4) Sono Gianmarco in questa sezione separata.
- **Sono Gianmarco** (aggiungere nel Blocco 3): public_name `Sono Gianmarco`, slug `sono-gianmarco`, Instagram `https://www.instagram.com/_.sonogianmarco_/`, immagine caricata manualmente. Visibile SOLO in /team/, NON in homepage, NON tra i 4 protagonisti. Ruolo/bio NON inventati: fino ai testi definitivi tenere scheda in bozza o mostrare solo nome+immagine+Instagram.

### [26/06/2026] BLOCCO 2 — Parità visiva archivi Episodi/Interviste. COMPLETATO (in attesa approvazione utente per Blocco 3).
- **Scoperta**: le pagine SINGOLE (episodio `episode.html`, intervista, trascrizione `transcript.html`) erano GIÀ in piena parità (hero scuro, thumbnail+play, excerpt, TOC "In questa puntata", sezioni riassunto H2/H3, capitoli con deep-link YouTube, citazioni, partecipanti, CTA pronostici/trascrizione, press box, correlati, ricerca trascrizione). Nessuna modifica necessaria.
- **Gap risolto**: i due ARCHIVI `/episodi/` e `/interviste/` usavano `render_archive` generico. Creati nuovi template `episodi_archive.html` (hero scuro + sezione chiara #f4ebe1, griglia 3 col, card bianche YouTube con play overlay, badge YouTube, badge durata, data, titolo, excerpt, "Guarda ora") e `interviste_archive.html` (tema scuro #14100e, griglia 2 col, card glass, gradiente, tag/topics, ospite, "Guarda l'intervista") — parità con i componenti React `Episodes.jsx`/`Interviews.jsx`.
- Aggiunte macro `episode_card`/`interview_card` in `_macros.html`. Nuove funzioni `seo.render_episodi_archive`/`render_interviste_archive` + `_content_card` + CollectionPage/ItemList JSON-LD. Route `ssr_episodi`/`ssr_interviste` ricablate, ora filtrano `status != bozza`. Thumbnail con fallback `onerror` (maxres→hqdefault).
- **Verifiche**: /episodi/ (11 card) e /interviste/ (2 card) HTTP 200, CollectionPage JSON-LD, canonical, link card corretti, no `<div id="root">`. Screenshot desktop+mobile di tutte e 5 le pagine (2 archivi + singolo episodio + singola intervista + trascrizione) OK. Regressione home/il-podcast/pronostici/team/parlano-di-noi/sitemap tutti 200. CSS SSR ricompilato (65.7KB).
- **DA FARE**: approvazione utente Blocco 2 → poi Blocco 3 (/team/ + profilo, /parlano-di-noi/, pagine istituzionali, footer) secondo specifiche vincolanti Team già registrate.

### Backlog confermato (dopo parità visiva, NON mescolare al Blocco 2):
- testi SEO originali su pagine e archivi; contenuti unici per ogni giornata Pronostici; pipeline Perplexity con fonti reali e stato `ai_preview`; controllo similarità tra pagine; keyword map per DataForSEO/Ahrefs; "Parlano di noi" completo; recupero automatico logo testata; approvazione manuale menzioni; audit Schema.org completo; test SSR/structured data/sitemap/canonical.

