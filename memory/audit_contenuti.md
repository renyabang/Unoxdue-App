# Audit contenuti UnoXdue — pre-modifica slug/metadati (giugno 2026)

> SOLO ANALISI. Nessuna modifica in produzione finché l'utente non approva la matrice.

## Verifica stagione (NON dedotta dal titolo)
- I 10 episodi "appuntamento" coprono **Serie A 2025/2026, giornate 29→38**.
- Evidenze indipendenti dal titolo:
  - Cadenza di pubblicazione settimanale 14/03 → 22/05/2026 con buco 22/03→03/04 = sosta nazionali fine marzo 2026 (coerente col calendario reale).
  - Round pronostici reale in DB `season=2025-2026 round=38` con squadre Pisa/Cremonese/Como/Sassuolo → neopromosse Serie A 2025/26.
  - Le trascrizioni quasi mai citano l'anno esplicito (correttamente non usato come prova).
- `episode_number` = ordine editoriale (Primo=1 … Decimo=10) → giornata = 28 + episode_number.

## Matrice (13 contenuti)
| # | tipo | yt_id | data pub | stagione | comp. principale | giornata | n. ep | slug attuale | slug proposto | redirect |
|---|------|-------|----------|----------|------------------|----------|-------|--------------|---------------|----------|
| 1 | episodio | b0xDcw9mYNM | 2026-03-14 | 2025-2026 | Serie A | 29 | 1 | studio-serie-a-38-giornata ⚠️ | serie-a-2025-2026-giornata-29-primo-appuntamento | 301 |
| 2 | episodio | Dwwyl4nx0dE | 2026-03-22 | 2025-2026 | Serie A | 30 | 2 | secondo-appuntamento-unoxdue-live-studio-serie-a-30-di-campionato-calcio-analisi | serie-a-2025-2026-giornata-30-secondo-appuntamento | 301 |
| 3 | episodio | 7m82PWSRcrM | 2026-04-03 | 2025-2026 | Serie A | 31 | 3 | terzo-appuntamento-di-unoxdue-live-studio-serie-a-31-giornata-calcio-e-news | serie-a-2025-2026-giornata-31-terzo-appuntamento | 301 |
| 4 | episodio | JBlPeaOY0vA | 2026-04-10 | 2025-2026 | Serie A | 32 | 4 | quarto-appuntamento-di-unoxdue-live-studio-serie-a-32-giornata-calcio-e-news | serie-a-2025-2026-giornata-32-quarto-appuntamento | 301 |
| 5 | episodio | -dyr2ruG1r8 | 2026-04-16 | 2025-2026 | Serie A | 33 | 5 | quinto-appuntamento-di-unoxdue-live-studio-serie-a-33-giornata-calcio-pronostici | serie-a-2025-2026-giornata-33-quinto-appuntamento | 301 |
| 6 | episodio | pWmfVNlhz6w | 2026-04-24 | 2025-2026 | Serie A | 34 | 6 | sesto-appuntamento-di-unoxdue-live-studio-serie-a-34-giornata-calcio-pronostici- | serie-a-2025-2026-giornata-34-sesto-appuntamento | 301 |
| 7 | episodio | qkDu5MzURiE | 2026-04-30 | 2025-2026 | Serie A | 35 | 7 | settimo-appuntamento-di-unoxdue-live-studio-serie-a-35-giornata-calcio-pronostic | serie-a-2025-2026-giornata-35-settimo-appuntamento | 301 |
| 8 | episodio | Tazb-A0qIcM | 2026-05-08 | 2025-2026 | Serie A | 36 | 8 | ottavo-appuntamento-di-unoxdue-live-studio-serie-a-36-giornata-calcio-pronostici | serie-a-2025-2026-giornata-36-ottavo-appuntamento | 301 |
| 9 | episodio | XZozhKAPX0g | 2026-05-15 | 2025-2026 | Serie A | 37 | 9 | nono-appuntamento-di-unoxdue-live-studio-serie-a-37-giornata-calcio-pronostici-e | serie-a-2025-2026-giornata-37-nono-appuntamento | 301 |
| 10 | episodio | 6TygRGNyIi4 | 2026-05-22 | 2025-2026 | Serie A | 38 | 10 | decimo-appuntamento-di-unoxdue-live-studio-serie-a-38-giornata-calcio-pronostici | serie-a-2025-2026-giornata-38-decimo-appuntamento | 301 |
| 11 | intervista | MxHqU7AK97I | 2026-05-27 | n/a | — (intervista) | — | — | allan-baclet-playoff-cosenza | allan-baclet-playoff-cosenza (INVARIATO) | no |
| 12 | episodio/speciale | KXkkQhzzvkQ | 2026-06-11 | n/a | Coppa del Mondo FIFA 2026 | — | — | speciale-mondiali-unoxdue-podcast ⚠️ | speciale-mondiali-2026 (o speciale-mondiali-11-giugno-2026) | 301 |
| 13 | intervista | 7035L7empWg | 2026-06-23 | n/a | — (intervista) | — | — | fabio-ceravolo-130-gol-carriera | fabio-ceravolo-130-gol-carriera (INVARIATO) | no |

## Competizioni citate (da topics/meta; i 4 con SEO non rigenerato vanno riconfermati)
- 1 Primo: Champions (Atalanta-Bayern), Europa League (Bologna-Roma)
- 2 Secondo: Europa League (Bologna)
- 3 Terzo: (SEO/topics da rigenerare) — segnali: Champions, Europa League
- 4 Quarto: (SEO/topics da rigenerare) — segnali: Coppa Italia, Champions
- 5 Quinto: Champions (semifinali: Real, Bayern, PSG, Atletico)
- 6 Sesto: Coppa Italia (Inter-Como semifinale), Champions
- 7 Settimo: (SEO/topics da rigenerare) — segnali: Coppa Italia, Champions
- 8 Ottavo: Champions (finale), scudetto Inter
- 9 Nono: (SEO/topics da rigenerare) — segnali: Coppa Italia, Champions
- 10 Decimo: solo Serie A (ultima giornata)

## Campi metadati da introdurre (per ogni episodio)
episode_number, primary_competition, competitions_mentioned[], season, matchday,
recording_date, youtube_video_id, youtube_title_original, youtube_title_current,
website_title, slug.
- recording_date: disponibile solo `published_at` (data, non orario live). Si propone recording_date = published_at.
- youtube_title_original = youtube_title_current = titolo attuale (NESSUNA modifica di massa ora).
- Lo slug NON si rigenera al cambio del titolo YouTube. Il link al video usa sempre youtube_video_id.

## Proposta titoli YouTube uniformi (NON applicare ora)
Formato: `UnoXdue | Serie A [stagione], [giornata] | [numero puntata]`
Es. ep.1: `UnoXdue | Serie A 2025/26, 29ª giornata | Primo appuntamento`
(conservare youtube_title_original + youtube_title_current nel DB)

## Note duplicati / integrità
- 13 record, tutti youtube_id e slug distinti. Nessun duplicato. Nessuna seconda pagina.
- Interviste fuori dalla regola Serie A: slug già puliti (persona-based), nessun redirect.

## ESITO MIGRAZIONE (25/06/2026) — COMPLETATA + verificata
- Formato slug finale approvato: `serie-a-2025-2026-giornata-[g]-puntata-[k]` (10 episodi) + `speciale-mondiali-2026-puntata-12`.
- Cross-check calendario reale football-data.org: per ogni giornata 29-38, 10/10 partite citate in trascrizione; date allineate alla pubblicazione. Stagione 2025/26 confermata.
- Pilota (puntata 1) validato, poi batch (2-10 + 12). Interviste Baclet/Ceravolo INVARIATE.
- Per ogni episodio migrato: vecchio URL 301 diretto (1 hop) → nuovo URL 200; canonical=nuovo; presente in sitemap+video-sitemap; vecchio assente; JSON-LD nuovo; trascrizione ri-keyata (db.transcriptions.slug aggiornato); link interni `related` aggiornati (slug+titolo puliti); 0 catene di redirect; 0 duplicati.
- Casing brand corretto ovunque (`Unoxdue`→`UnoXdue`): 0 occorrenze errate sulle pagine.
- Breadcrumb breve via campo `breadcrumb_label`; H1 descrittivo "{Ordinale} appuntamento UnoXdue: Serie A 2025/26, {g}ª giornata"; campi distinti: youtube_title_original/current (literal), website_title, seo_title, breadcrumb_label, slug.
- Bug corretto: `ssr_episode` reindirizzava per errore a `/trascrizione/` (logica `"trascrizione" not in slug` invertita).
- Script: `scripts/slug_migration.py` (plan/backup/titles/migrate/refresh-related/rollback). Backup+rollback includono episodes+transcriptions.
- Rollback disponibile e validato: `/app/backups/slug_migration_20260625_192942` (13 ep + 13 trascr, caricabili) → `python slug_migration.py rollback <dir>`.
- Speciale + puntate 3/4/7/9 senza pagina trascrizione (anteprima, transcription_seo_status non generato): atteso, nessuna regressione.

## STEP 3 (25/06/2026) — Pubblicazione 4 approved_short. COMPLETATA + verificata
- Pubblicati in modo indipendente: Terzo(31ª/p3), Quarto(32ª/p4), Settimo(35ª/p7), Nono(37ª/p9). Tutti PASS controlli bloccanti (sezioni>=3 con >=2 H2, capitoli con timestamp reali, >=2 citazioni VERBATIM verificate, topics, trascrizione presente).
- Flusso: `scripts/publish_short.py --publish` (publish_preview) -> ri-applicato `slug_migration.py titles` (casing/H1 descrittivo) + `refresh-related`.
- Verifica per episodio: ep 200, trascrizione 200 (119-129 paragrafi), H1 descrittivo UnoXdue+stagione+giornata, breadcrumb breve, 5-6 H2, 12 capitoli, 5 citazioni, 14 topics, canonical=nuovo, JSON-LD (PodcastEpisode+12 Clip+transcript+BreadcrumbList), OG ok, meta ok, 0 "Unoxdue", presente in sitemap+video-sitemap.
- Ora 12/13 con has_transcript_page + transcription_seo_status=published. Resta solo Speciale Mondiali (Step 4).
- Rollback pre-pubblicazione: `/app/backups/slug_migration_20260625_200003`.

## STEP 4 (25/06/2026) — Speciale Mondiali espanso + pubblicato. COMPLETATO + verificato
- Rigenerata anteprima (solo da trascrizione, anti-invenzione): intro 81w, 5 H2, sommario 307w (approved_short, tutti i temi coperti — niente padding), 5 capitoli (timestamp reali), 5 citazioni verbatim. Gruppi A-L con squadre, Iran, favorita (FRA/ENG/ARG), gioco albo d'oro, saluti.
- Pubblicazione MIRATA (solo corpo) preservando H1/seo_title/meta gia' corretti (NON usate le versioni ai_preview con casing "Unoxdue").
- Smoke: episodio 200, trascrizione 200 (33 parag.), vecchio URL `speciale-mondiali-unoxdue-podcast` → 301, canonical self, JSON-LD (Episode+5 Clip+transcript+Breadcrumb), in sitemap+video-sitemap, 0 "Unoxdue".
- Ora 13/13 con SEO + trascrizione pubblicati. Rollback: `/app/backups/slug_migration_20260625_201101`.

## PROSSIMO BLOCCO (richiesto utente, P0) — SSR pubblico completo + menu reale
- Problema: la homepage `/` (e route pubbliche) servono ancora la SPA React (`<div id="root"></div>`); contenuto generato solo da JS. Menu landing usa #anchor/scroll JS invece di link reali.
- Obiettivo: tutte le route pubbliche servono HTML server-rendered (H1/contenuto/canonical/metadata/JSON-LD nel sorgente senza JS). `/admin` resta React SPA. Menu con `<a href>` reali alle pagine.
- Architettura: FastAPI+Jinja2 per pubblico, React solo /admin, /api FastAPI. In preview: proxy/route coerente verso SSR Jinja2 (no anchor fittizie, un solo helper routing `PUBLIC_BASE_URL`).
- Route da coprire: / · /il-podcast/ · /episodi/ · /episodi/[slug]/ · /trascrizione/ · /interviste/ · /interviste/[slug]/ · /pronostici/ · /pronostici/serie-a/[stagione]/giornata-[n]/ · /team/ · /team/[slug]/ · /parlano-di-noi/ · /collaborazioni/ · /contatti/ · privacy · cookie.
- Pulizia produzione: rimuovere badge Emergent, Tailwind CDN, commenti CRA, codice preview; PostHog solo post-consenso. Rimuovere meta keywords. Status reali 200/301/404/401-403/500.
- DOPO questo blocco: checkpoint + refactoring (NON prima).

## SSR PUBBLICO — STATO (25/06/2026) — IMPLEMENTATO in preview, verificato via curl/screenshot
- Audit: tutte le URL pulite servivano la SPA React (root, 200 anche per route inesistenti). SSR esisteva solo su /api/seo/*.
- Soluzione preview: `frontend/src/setupProxy.js` (http-proxy-middleware) instrada le route pubbliche pulite → SSR backend (/api/seo/...), pathRewrite + filtro; esclude /admin, /static, /api, ws/hmr. `/`→/api/seo/home, /sitemap.xml→/api/sitemap.xml.
- Risultato: TUTTE le URL pulite servono HTML SSR (root assente, H1/contenuto/canonical/JSON-LD nel sorgente senza JS). /admin resta React SPA. 404 reale per route inesistenti. Title unici per route. canonical autoreferenziale.
- JSON-LD arricchito (seo.py): HOME @graph Organization+WebSite+PodcastSeries; archivi CollectionPage+ItemList; episodio @graph PodcastEpisode/Article+VideoObject(+Clip capitoli, duration ISO); team ProfilePage+Person; pronostico Article+Breadcrumb.
- OG completo + Twitter card su tutti i tipi (un solo og:type: website/article/video.other/profile), no duplicati. robots index,follow. No meta keywords. base.html SSR NON usa Tailwind CDN/Emergent/PostHog (CSS compilato unoxdue.css).
- Pagine nuove SSR: /collaborazioni/ /contatti/ /privacy/ /cookie/ (render_page) + link nel footer. Menu (desktop+mobile <details> nativo) con `<a href>` reali alle pagine, niente #anchor.
- Card archivio/home usano website_title (titoli puliti).
- ⚠️ PRODUZIONE: setupProxy.js funziona SOLO nel dev server (preview). In deploy esterno il routing URL pulita→SSR va gestito dall'ingress/reverse proxy. DA RISOLVERE prima/durante il deploy (verificare con support/deployment).
- 404: proxy INVERTITO (instrada tutto tranne admin/api/static/asset-con-estensione) + route backend catch-all `GET /seo/{full_path:path}` → pagina SSR 404 stilizzata (noindex), status 404. Route inesistenti (es. /pagina-finta/) ora danno 404 reale (non più falso 200 SPA).
- Test (iteration_14.json): 39/40 PASS al primo giro; unico FAIL (falso 200 su route sconosciute) RISOLTO e verificato via curl (404 su /pagina-finta/, /foo/bar/, /team/non-esiste/; route valide ancora 200; logo/asset 200; /admin React; sitemap/robots 200).
