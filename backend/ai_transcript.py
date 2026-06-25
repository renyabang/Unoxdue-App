"""Generazione SEO dalle trascrizioni reali (map -> reduce + anti-invenzione).

REGOLE (richieste dall'utente):
- Ogni informazione deve essere verificabile nella trascrizione: niente dichiarazioni,
  nomi, risultati, quote, ospiti, pronostici, timestamp o citazioni inventati.
- Capitoli derivati dai timestamp REALI dei segmenti SRT (mai inventati, mai dal solo titolo).
- Citazioni usate SOLO se realmente presenti nel testo; altrimenti omesse.
- gpt-5.4-mini di default; fallback a gpt-5.4 UNA sola volta se i controlli non passano.
- Workflow anteprima: NON sovrascrive i campi pubblici finche' l'admin non pubblica.
"""
import json
import uuid
import asyncio
from datetime import datetime, timezone

from config_db import db, EMERGENT_LLM_KEY
import automations as auto
import srt_utils as su

MODEL_DEFAULT = "gpt-5.4-mini"
MODEL_FALLBACK = "gpt-5.4"
CHUNK_CHARS = 7000
MIN_CHAPTERS = 5
MAX_CHAPTERS = 15
PROCESSING_VERSION = "transcript-seo-v1"

SYSTEM_MAP = (
    "Sei un editor SEO del podcast italiano di calcio UnoXdue (Serie A). "
    "Analizzi un ESTRATTO di trascrizione reale con marcatori temporali [t=M:SS]. "
    "NON inventare nulla: usa solo cio' che e' scritto nell'estratto. "
    "I timestamp dei capitoli devono essere SCELTI tra i marcatori [t=...] presenti. "
    "Le citazioni devono essere VERBATIM dall'estratto. "
    "Rispondi ESCLUSIVAMENTE con JSON valido."
)

SYSTEM_REDUCE = (
    "Sei un caporedattore SEO del podcast italiano di calcio UnoXdue (Serie A). "
    "Sintetizzi note editoriali gia' estratte (verificate sul testo) in una scheda finale. "
    "NON inventare dichiarazioni, nomi, risultati o eventi non presenti nelle note. "
    "Scrivi in italiano naturale e professionale, senza ripetere keyword in modo artificiale. "
    "Rispondi ESCLUSIVAMENTE con JSON valido."
)


def _annotate_chunk(chunk_segments_clean: list) -> tuple:
    """Costruisce il testo del chunk con marcatori [t=M:SS] e l'insieme dei tempi validi."""
    parts = []
    valid_times = set()
    last_mark = -999
    for cs in chunk_segments_clean:
        if not cs["clean"].strip():
            continue
        # marcatore ogni >= 25s per non intasare
        if cs["start"] - last_mark >= 25:
            parts.append(f"[t={cs['start_hms']}]")
            valid_times.add(cs["start_hms"])
            last_mark = cs["start"]
        parts.append(cs["clean"].strip())
    return " ".join(parts), valid_times


async def _call_llm(model: str, system: str, prompt: str) -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"trsc-{uuid.uuid4().hex[:8]}",
                   system_message=system).with_model("openai", model)
    resp = await chat.send_message(UserMessage(text=prompt))
    return resp if isinstance(resp, str) else str(resp)


async def _llm_json(model: str, system: str, prompt: str, retries: int = 1) -> dict:
    last = None
    for _ in range(retries + 1):
        raw = await _call_llm(model, system, prompt)
        try:
            return json.loads(auto._strip_json(raw)), len(prompt) + len(raw)
        except Exception as e:
            last = e
    raise ValueError(f"JSON non valido dal modello: {last}")


def _map_prompt(chunk_text: str) -> str:
    return (
        "Estratto di trascrizione (con marcatori temporali [t=M:SS]):\n\n"
        f"{chunk_text}\n\n"
        "Restituisci questo JSON sulla SOLA base dell'estratto:\n"
        "{\n"
        '  "summary": "2-3 frasi di sintesi di questo estratto",\n'
        '  "topics": ["argomenti trattati in questo estratto"],\n'
        '  "people": ["persone citate (nomi propri)"],\n'
        '  "teams": ["squadre citate"],\n'
        '  "competitions": ["competizioni citate (es. Serie A, Coppa Italia)"],\n'
        '  "chapters": [{"time":"M:SS (preso da un [t=...])","title":"titolo capitolo","description":"breve descrizione"}],\n'
        '  "quotes": [{"text":"frase VERBATIM dall estratto","time":"M:SS da [t=...]","speaker":"nome o null"}]\n'
        "}\n"
        "Regole: 0-3 capitoli per estratto (solo cambi di tema rilevanti); time SOLO tra i [t=...]; "
        "quotes solo se davvero presenti (max 2), speaker solo se chiaro altrimenti null; niente invenzioni."
    )


def _reduce_prompt(title: str, notes: dict) -> str:
    return (
        f"Titolo del contenuto: {title}\n\n"
        "Note editoriali estratte (verificate sul testo):\n"
        f"{json.dumps(notes, ensure_ascii=False)[:9000]}\n\n"
        "Genera la scheda finale come JSON:\n"
        "{\n"
        '  "type": "episodio | intervista",\n'
        '  "guest_name": "nome ospite se intervista, altrimenti null",\n'
        '  "h1": "H1 chiaro (max ~70 caratteri)",\n'
        '  "seo_title": "title tag con UnoXdue (max ~60 caratteri)",\n'
        '  "meta_description": "meta description (120-158 caratteri)",\n'
        '  "intro": "1 paragrafo introduttivo (40-80 parole)",\n'
        '  "summary": ["3-6 paragrafi di sommario editoriale esteso basato sulle note"],\n'
        '  "topics": ["6-12 argomenti principali, deduplicati"],\n'
        '  "key_passages": ["3-6 passaggi/punti salienti"]\n'
        "}\n"
        "Niente citazioni inventate, niente keyword ripetute artificialmente. Solo JSON."
    )


async def ensure_bundle(slug: str) -> dict:
    """Parsa l'SRT salvato sull'episodio e crea il bundle in db.transcriptions."""
    ep = await db.episodes.find_one({"slug": slug})
    if not ep:
        return {"ok": False, "error": "Contenuto non trovato"}
    srt = ep.get("transcription") or ""
    if "-->" not in srt:
        return {"ok": False, "error": "Nessun SRT disponibile (trascrizione mancante)"}
    segments = su.parse_srt(srt)
    clean = su.clean_text(segments)
    bundle = {
        "slug": slug, "srt": srt, "clean": clean, "segments": segments,
        "lang": ep.get("transcription_lang"), "track_id": ep.get("caption_track_id"),
        "imported_at": ep.get("transcription_at") or datetime.now(timezone.utc).isoformat(),
        "chars_srt": len(srt), "chars_clean": len(clean), "n_segments": len(segments),
    }
    await db.transcriptions.update_one({"slug": slug}, {"$set": bundle}, upsert=True)
    return {"ok": True, "segments": len(segments), "chars_clean": len(clean)}


def _all_segment_times(segments: list) -> set:
    return {s["start_hms"] for s in segments}


def _dedupe_keep_order(items, key=lambda x: x):
    seen, out = set(), []
    for it in items:
        k = key(it).lower().strip() if isinstance(key(it), str) else key(it)
        if k and k not in seen:
            seen.add(k)
            out.append(it)
    return out


def _validate_chapters(raw_chapters: list, valid_times: set, segments: list) -> list:
    """Tiene solo i capitoli con timestamp realmente presente; ordina; dedup vicini; cap."""
    def to_sec(t):
        p = [int(x) for x in t.split(":")]
        return p[0] * 60 + p[1] if len(p) == 2 else p[0] * 3600 + p[1] * 60 + p[2]
    good = []
    for c in raw_chapters:
        t = str(c.get("time", "")).strip()
        if t in valid_times and c.get("title"):
            good.append({"time": t, "label": str(c["title"])[:90],
                         "description": str(c.get("description", ""))[:200],
                         "_sec": to_sec(t)})
    good.sort(key=lambda x: x["_sec"])
    # dedup capitoli troppo vicini (< 60s)
    pruned = []
    for c in good:
        if pruned and c["_sec"] - pruned[-1]["_sec"] < 60:
            continue
        pruned.append(c)
    for c in pruned:
        c.pop("_sec", None)
    return pruned[:MAX_CHAPTERS]


def _validate_quotes(raw_quotes: list, clean: str, valid_times: set) -> list:
    out = []
    for q in raw_quotes:
        txt = str(q.get("text", "")).strip()
        if not txt or not su.quote_in_transcript(txt, clean):
            continue
        item = {"text": txt[:400], "time": q.get("time") if q.get("time") in valid_times else None}
        sp = q.get("speaker")
        if sp and isinstance(sp, str) and sp.strip().lower() not in ("null", "none", ""):
            item["speaker"] = sp.strip()[:60]
        out.append(item)
    return out[:6]


def _entity_present(name: str, clean_norm: str) -> bool:
    n = su.normalize_for_match(name)
    return bool(n) and n in clean_norm


async def generate_preview(slug: str) -> dict:
    if not EMERGENT_LLM_KEY:
        return {"ok": False, "error": "EMERGENT_LLM_KEY non configurata."}
    b = await db.transcriptions.find_one({"slug": slug})
    if not b:
        r = await ensure_bundle(slug)
        if not r.get("ok"):
            return r
        b = await db.transcriptions.find_one({"slug": slug})
    ep = await db.episodes.find_one({"slug": slug})
    segments = b["segments"]
    clean = b["clean"]
    clean_norm = su.normalize_for_match(clean)
    all_times = _all_segment_times(segments)

    chunks = su.chunk_segments(segments, CHUNK_CHARS)
    seg_clean = su.segment_clean_text(segments)
    # raggruppa i segmenti puliti per chunk (per ricostruire i marcatori)
    map_results = []
    total_chars = 0
    model = MODEL_DEFAULT
    for ch in chunks:
        sub = [s for s in seg_clean if ch["seg_from"] <= s["idx"] <= ch["seg_to"]]
        ctext, vt = _annotate_chunk(sub)
        try:
            data, n = await _llm_json(model, SYSTEM_MAP, _map_prompt(ctext), retries=1)
        except Exception as e:
            await auto.log_automation("ai_transcript", "warning", f"Map chunk fallito ({slug}): {e}")
            continue
        total_chars += n
        # tieni i capitoli/quote GREZZI; la validazione finale avviene in aggregazione
        map_results.append(data)

    if not map_results:
        return {"ok": False, "error": "Nessun blocco elaborato dall'AI."}

    # ---- aggregazione note ----
    notes = {
        "partial_summaries": [m.get("summary", "") for m in map_results if m.get("summary")],
        "topics": _dedupe_keep_order([t for m in map_results for t in m.get("topics", [])]),
        "people": _dedupe_keep_order([p for m in map_results for p in m.get("people", [])]),
        "teams": _dedupe_keep_order([t for m in map_results for t in m.get("teams", [])]),
        "competitions": _dedupe_keep_order([c for m in map_results for c in m.get("competitions", [])]),
    }
    # entita' verificate (presenti nel testo)
    entities = {
        "people": [p for p in notes["people"] if _entity_present(p, clean_norm)][:20],
        "teams": [t for t in notes["teams"] if _entity_present(t, clean_norm)][:20],
        "competitions": [c for c in notes["competitions"] if _entity_present(c, clean_norm)][:10],
    }
    chapters = _validate_chapters(
        [c for m in map_results for c in m.get("chapters", [])], all_times, segments)
    quotes = []
    for m in map_results:
        quotes.extend(m.get("quotes", []))
    quotes = _validate_quotes(quotes, clean, all_times)

    # ---- reduce (sintesi finale) ----
    notes_for_reduce = {**notes, "entities": entities, "n_chapters": len(chapters)}

    async def _do_reduce(mdl):
        return await _llm_json(mdl, SYSTEM_REDUCE, _reduce_prompt(ep.get("title", ""), notes_for_reduce), retries=1)

    fallback_used = False
    try:
        final, n = await _do_reduce(model)
        total_chars += n
        if not _final_valid(final):
            raise ValueError("controlli finali non superati")
    except Exception:
        fallback_used = True
        final, n = await _do_reduce(MODEL_FALLBACK)
        total_chars += n
        model = MODEL_FALLBACK

    # ---- collegamenti interni / correlati (dal DB, niente invenzioni) ----
    related, internal_links = await _compute_links(slug, ep, entities)

    needs_review = len(chapters) < MIN_CHAPTERS or not _final_valid(final)
    tokens = total_chars // 4
    cost = round(tokens / 1000.0 * 0.0006, 5)
    now = datetime.now(timezone.utc).isoformat()
    preview = {
        "type": final.get("type") if final.get("type") in ("episodio", "intervista") else ep.get("type"),
        "guest_name": (final.get("guest_name") or None),
        "h1": final.get("h1") or ep.get("title"),
        "seo_title": final.get("seo_title"),
        "meta_description": final.get("meta_description"),
        "excerpt": final.get("intro"),
        "summary": [str(x) for x in (final.get("summary") or [])][:8],
        "topics": [str(x) for x in (final.get("topics") or notes["topics"])][:14],
        "key_passages": [str(x) for x in (final.get("key_passages") or [])][:8],
        "entities": entities,
        "chapters": chapters,
        "quotes": quotes,
        "related": related,
        "internal_links": internal_links,
        "meta": {
            "model": model, "fallback_used": fallback_used, "tokens": tokens,
            "cost_estimate": cost, "version": PROCESSING_VERSION, "created_at": now,
            "n_chunks": len(chunks), "n_chapters": len(chapters), "n_quotes": len(quotes),
            "needs_review": needs_review, "chars_clean": b["chars_clean"],
        },
    }
    await db.episodes.update_one({"slug": slug}, {"$set": {
        "ai_preview": preview, "transcription_chars": b["chars_clean"],
        "ai_preview_at": now,
    }})
    await auto.log_automation("ai_transcript", "ok",
        f"Anteprima SEO generata per '{ep.get('title','')[:50]}' (modello {model}, "
        f"capitoli {len(chapters)}, citazioni {len(quotes)}, ~{tokens} token, ~${cost})",
        {"slug": slug, "model": model, "fallback_used": fallback_used, "tokens": tokens,
         "cost_estimate": cost, "needs_review": needs_review})
    return {"ok": True, "slug": slug, "preview": preview}


def _final_valid(final: dict) -> bool:
    if not isinstance(final, dict):
        return False
    if not final.get("h1") or not final.get("meta_description"):
        return False
    if not isinstance(final.get("summary"), list) or len(final.get("summary")) < 2:
        return False
    md = final.get("meta_description") or ""
    return 80 <= len(md) <= 200


async def _compute_links(slug: str, ep: dict, entities: dict) -> tuple:
    """Correlati e collegamenti interni dedotti dal DB (team + altri episodi). Niente invenzioni."""
    related, internal = [], []
    # team members citati per nome
    team = await db.team.find({}, {"_id": 0, "slug": 1, "name": 1}).to_list(100)
    names_norm = {su.normalize_for_match(m["name"]): m for m in team}
    cited = set()
    for p in (entities.get("people", []) + entities.get("teams", [])):
        n = su.normalize_for_match(p)
        for nm, m in names_norm.items():
            if nm and (nm in n or n in nm):
                cited.add(m["slug"])
    for s in list(cited)[:6]:
        m = next((x for x in team if x["slug"] == s), None)
        if m:
            internal.append({"type": "team", "slug": s, "label": m["name"]})
    # altri episodi/interviste recenti (correlati editoriali)
    others = await db.episodes.find(
        {"slug": {"$ne": slug}, "status": "pubblicato"},
        {"_id": 0, "slug": 1, "title": 1, "type": 1}).sort("published_at", -1).to_list(6)
    for o in others[:4]:
        related.append({"section": "interviste" if o.get("type") == "intervista" else "episodi",
                        "slug": o["slug"], "title": o["title"]})
    return related, internal


async def publish_preview(slug: str) -> dict:
    ep = await db.episodes.find_one({"slug": slug})
    if not ep or not ep.get("ai_preview"):
        return {"ok": False, "error": "Nessuna anteprima da pubblicare."}
    p = ep["ai_preview"]
    upd = {
        "type": p.get("type") or ep.get("type"),
        "h1": p.get("h1"), "seo_title": p.get("seo_title"),
        "meta_description": p.get("meta_description"), "excerpt": p.get("excerpt"),
        "summary": p.get("summary", []), "topics": p.get("topics", []),
        "chapters": p.get("chapters", []), "quotes": p.get("quotes", []),
        "key_passages": p.get("key_passages", []), "entities": p.get("entities", {}),
        "related": p.get("related", []), "internal_links": p.get("internal_links", []),
        "has_transcript_page": True,
        "transcription_seo_status": "published",
        "transcription_seo_at": datetime.now(timezone.utc).isoformat(),
        "ai_transcript_meta": p.get("meta", {}),
    }
    if p.get("guest_name"):
        upd["guest_name"] = p["guest_name"]
    if ep.get("status") != "bozza":
        upd["status"] = "pubblicato"
    await db.episodes.update_one({"slug": slug}, {"$set": upd})
    await auto.log_automation("ai_transcript", "ok", f"Anteprima SEO pubblicata per {slug}")
    return {"ok": True, "slug": slug}


async def list_status() -> dict:
    eps = await db.episodes.find(
        {"transcription_status": "done"},
        {"_id": 0, "slug": 1, "title": 1, "type": 1, "transcription_status": 1,
         "transcription_seo_status": 1, "ai_preview_at": 1, "transcription_chars": 1,
         "ai_preview.meta": 1}).to_list(500)
    for e in eps:
        ap = (e.get("ai_preview") or {}).get("meta") if e.get("ai_preview") else None
        e["has_preview"] = bool(e.get("ai_preview_at"))
        e["seo_status"] = e.get("transcription_seo_status") or ("preview" if e["has_preview"] else "none")
        e.pop("ai_preview", None)
    return {"episodes": eps, "total": len(eps)}


async def get_preview(slug: str) -> dict:
    ep = await db.episodes.find_one(
        {"slug": slug},
        {"_id": 0, "slug": 1, "title": 1, "ai_preview": 1, "h1": 1, "seo_title": 1,
         "meta_description": 1, "excerpt": 1, "summary": 1, "topics": 1, "chapters": 1,
         "quotes": 1, "transcription_seo_status": 1})
    if not ep:
        return {"ok": False, "error": "Contenuto non trovato"}
    current = {k: ep.get(k) for k in ("h1", "seo_title", "meta_description", "excerpt",
                                      "summary", "topics", "chapters", "quotes")}
    return {"ok": True, "slug": slug, "title": ep.get("title"),
            "preview": ep.get("ai_preview"), "current": current,
            "seo_status": ep.get("transcription_seo_status") or "none"}


async def get_transcript_clean(slug: str) -> dict:
    b = await db.transcriptions.find_one({"slug": slug}, {"_id": 0, "clean": 1, "chars_clean": 1})
    return b or {}
