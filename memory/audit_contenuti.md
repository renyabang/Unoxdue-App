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
