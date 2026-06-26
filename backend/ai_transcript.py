"""Generazione SEO dalle trascrizioni reali (map -> reduce + anti-invenzione) — v2.

Novità v2 (parametri editoriali concordati con l'utente):
- Introduzione 80-120 parole (max 150 se serve).
- Sommario STRUTTURATO `summary_sections` (H2/H3) con lunghezza adattiva alla durata:
  <=45min 400-600, 45-90min 500-750, >90min 650-900 parole. Ogni sezione conserva i
  riferimenti ai segmenti SRT usati (`source_segment_ids`) + confidence.
- Capitoli 6-10 (max 12), dedup <90s, niente minimo artificiale, timestamp dall'SRT.
- Citazioni 2-5 (max 6 per interviste ricche), solo passaggi significativi, verbatim,
  speaker solo se affidabile.
- Qualita' > soglie: non allungare, non creare capitoli/citazioni inutili.
- Workflow ANTEPRIMA: non sovrascrive il pubblico finche' l'admin non pubblica.
- gpt-5.4-mini default; fallback gpt-5.4 max 1 volta se i controlli falliscono.
"""
import json
import re
import uuid
import unicodedata
from datetime import datetime, timezone

from config_db import db, EMERGENT_LLM_KEY
import automations as auto
import srt_utils as su

MODEL_DEFAULT = "gpt-5.4-mini"
MODEL_FALLBACK = "gpt-5.4"
CHUNK_CHARS = 7000
MAX_CHAPTERS = 12
CHAPTER_DEDUP_SECONDS = 90
PROCESSING_VERSION = "transcript-seo-v2"

SYSTEM_MAP = (
    "Sei un editor SEO del podcast italiano di calcio UnoXdue (Serie A). "
    "Analizzi un ESTRATTO di trascrizione reale con marcatori temporali [t=M:SS]. "
    "NON inventare nulla: usa solo cio' che e' scritto nell'estratto. "
    "I timestamp dei capitoli devono essere SCELTI tra i marcatori [t=...] presenti. "
    "Le citazioni devono essere VERBATIM e significative. "
    "Non alterare/anglicizzare i nomi propri. "
    "Rispondi ESCLUSIVAMENTE con JSON valido."
)

SYSTEM_REDUCE = (
    "Sei un caporedattore SEO del podcast italiano di calcio UnoXdue (Serie A). "
    "Sintetizzi note editoriali gia' estratte (verificate sul testo) in una scheda finale "
    "con sommario STRUTTURATO in sezioni H2/H3. "
    "NON inventare dichiarazioni, nomi, risultati o eventi non presenti nelle note. "
    "REGOLA NOMI: scrivi i nomi propri ESATTAMENTE come nel TITOLO fornito; NON tradurli, "
    "NON anglicizzarli, NON 'correggerli' (i sottotitoli automatici possono sbagliare i nomi). "
    "Privilegia qualita' e leggibilita': non allungare artificialmente, non creare sezioni inutili. "
    "Scrivi in italiano naturale, senza keyword stuffing. Rispondi ESCLUSIVAMENTE con JSON valido."
)


# ----------------------------- utility -----------------------------
def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)[:60] or "sezione"


def _words(s: str) -> int:
    return len((s or "").split())


def _summary_target(duration_seconds: int) -> tuple:
    m = (duration_seconds or 0) / 60.0
    if m <= 45:
        return (400, 600)
    if m <= 90:
        return (500, 750)
    return (650, 900)


def _annotate_chunk(chunk_segments_clean: list) -> tuple:
    parts, valid_times, last_mark = [], set(), -999
    for cs in chunk_segments_clean:
        if not cs["clean"].strip():
            continue
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


async def _llm_json(model: str, system: str, prompt: str, retries: int = 1):
    last = None
    for _ in range(retries + 1):
        raw = await _call_llm(model, system, prompt)
        try:
            return json.loads(auto._strip_json(raw)), len(prompt) + len(raw)
        except Exception as e:
            last = e
    raise ValueError(f"JSON non valido dal modello: {last}")


# ----------------------------- prompt -----------------------------
def _map_prompt(chunk_text: str) -> str:
    return (
        "Estratto di trascrizione (con marcatori temporali [t=M:SS]):\n\n"
        f"{chunk_text}\n\n"
        "Restituisci questo JSON sulla SOLA base dell'estratto:\n"
        "{\n"
        '  "section": {"heading":"titolo del tema principale di questo estratto","paragraph":"2-4 frasi che lo riassumono"},\n'
        '  "topics": ["argomenti trattati"],\n'
        '  "people": ["persone citate (nomi propri)"],\n'
        '  "teams": ["squadre citate"],\n'
        '  "competitions": ["competizioni citate"],\n'
        '  "chapters": [{"time":"M:SS (da un [t=...])","title":"titolo capitolo specifico","description":"breve descrizione"}],\n'
        '  "quotes": [{"text":"frase VERBATIM significativa","time":"M:SS da [t=...]","speaker":"nome o null"}]\n'
        "}\n"
        "Regole: 0-2 capitoli per estratto (solo veri cambi di tema, titoli specifici NON vaghi); "
        "time SOLO tra i [t=...]; 0-2 citazioni solo se davvero significative (>=6 parole), speaker solo se chiaro; niente invenzioni."
    )


def _reduce_prompt(title: str, duration_min: float, notes: dict) -> str:
    lo, hi = _summary_target(int(duration_min * 60))
    return (
        f"TITOLO (fonte canonica per i nomi propri): {title}\n"
        f"DURATA: ~{int(duration_min)} minuti. Lunghezza sommario target: {lo}-{hi} parole "
        "(adatta al numero reale di argomenti: non allungare se gli argomenti sono pochi).\n\n"
        "NOTE per sezione (ognuna ha un indice i, un orario e i temi dell'estratto):\n"
        f"{json.dumps(notes['sections'], ensure_ascii=False)[:8000]}\n\n"
        f"Argomenti: {json.dumps(notes['topics'][:20], ensure_ascii=False)}\n"
        f"Entita': {json.dumps(notes['entities'], ensure_ascii=False)}\n\n"
        "Genera la scheda finale come JSON:\n"
        "{\n"
        '  "type": "episodio | intervista",\n'
        '  "guest_name": "se intervista, nome ospite ESATTAMENTE come nel TITOLO; altrimenti null",\n'
        '  "h1": "H1 chiaro (max ~70 caratteri)",\n'
        '  "seo_title": "title tag con UnoXdue (max ~60 caratteri)",\n'
        '  "meta_description": "meta description (120-158 caratteri)",\n'
        '  "intro": "introduzione 80-120 parole: tema, partecipanti, contesto. Niente frasi generiche.",\n'
        '  "summary_sections": [\n'
        '     {"level":2,"heading":"titolo sezione (vero argomento)","paragraphs":["par.1","par.2"],"sources":[indici i delle note usate]},\n'
        '     {"level":3,"heading":"sottosezione reale di un H2 precedente","paragraphs":["..."],"sources":[i]}\n'
        "  ],\n"
        '  "key_passages": ["3-6 punti salienti"]\n'
        "}\n"
        "Regole sommario: 3-6 sezioni H2; H3 SOLO come sottosezione reale di un H2 (mai come prima sezione); "
        "heading non vuoti e non duplicati; paragrafi brevi e leggibili; ogni sezione cita in 'sources' gli indici i delle note che la supportano; "
        "i nomi propri usano la grafia del TITOLO; niente keyword stuffing; niente citazioni inventate. Solo JSON."
    )


# ----------------------------- bundle -----------------------------
async def ensure_bundle(slug: str) -> dict:
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


# ----------------------------- validatori -----------------------------
def _dedupe_keep_order(items):
    seen, out = set(), []
    for it in items:
        k = it.lower().strip() if isinstance(it, str) else it
        if k and k not in seen:
            seen.add(k)
            out.append(it)
    return out


def _t2s(t):
    p = [int(x) for x in str(t).split(":")]
    return p[0] * 60 + p[1] if len(p) == 2 else p[0] * 3600 + p[1] * 60 + p[2]


def _validate_chapters(raw_chapters: list, valid_times: set) -> list:
    good = []
    for c in raw_chapters:
        t = str(c.get("time", "")).strip()
        if t in valid_times and c.get("title"):
            good.append({"time": t, "label": str(c["title"])[:90],
                         "description": str(c.get("description", ""))[:200], "_sec": _t2s(t)})
    good.sort(key=lambda x: x["_sec"])
    pruned = []
    for c in good:
        if pruned and c["_sec"] - pruned[-1]["_sec"] < CHAPTER_DEDUP_SECONDS:
            continue
        pruned.append(c)
    for c in pruned:
        c.pop("_sec", None)
    return pruned[:MAX_CHAPTERS]


def _validate_quotes(raw_quotes: list, clean: str, valid_times: set, cap: int) -> list:
    out, seen = [], set()
    for q in raw_quotes:
        txt = str(q.get("text", "")).strip()
        if not txt or len(txt.split()) < 6 or not su.quote_in_transcript(txt, clean, min_words=6):
            continue
        key = su.normalize_for_match(txt)[:80]
        if key in seen:
            continue
        seen.add(key)
        item = {"text": txt[:400], "time": q.get("time") if q.get("time") in valid_times else None}
        sp = q.get("speaker")
        if sp and isinstance(sp, str) and sp.strip().lower() not in ("null", "none", ""):
            item["speaker"] = sp.strip()[:60]
        out.append(item)
    return out[:cap]


def _entity_present(name, clean_norm):
    n = su.normalize_for_match(name)
    return bool(n) and n in clean_norm


def _build_sections(raw_sections: list, chunk_meta: list) -> tuple:
    """Costruisce summary_sections semanticamente valide (H2/H3, id univoci, source ref reali)."""
    sections, used_ids = [], set()
    order = 0
    last_was_h2 = False
    for s in raw_sections:
        heading = str(s.get("heading", "")).strip()
        paragraphs = [str(p).strip() for p in (s.get("paragraphs") or []) if str(p).strip()]
        if not heading or not paragraphs:
            continue
        level = 2 if int(s.get("level", 2)) <= 2 else 3
        if level == 3 and not last_was_h2:
            level = 2  # niente H3 senza un H2 precedente
        # id univoco
        base = _slugify(heading)
        sid = base
        k = 2
        while sid in used_ids:
            sid = f"{base}-{k}"
            k += 1
        used_ids.add(sid)
        # source_segment_ids reali (dai chunk citati)
        srcs = []
        for i in (s.get("sources") or []):
            try:
                cm = chunk_meta[int(i)]
                srcs.append(f"seg-{cm['seg_from']}..{cm['seg_to']}")
            except Exception:
                continue
        confidence = 0.92 if srcs else 0.6
        order += 1
        sections.append({
            "id": sid, "level": level, "heading": heading[:120], "paragraphs": paragraphs,
            "source_segment_ids": srcs, "confidence": confidence, "order": order,
        })
        last_was_h2 = level == 2
    # dedup heading identici
    seen_h, dedup = set(), []
    for s in sections:
        hk = s["heading"].lower().strip()
        if hk in seen_h:
            continue
        seen_h.add(hk)
        dedup.append(s)
    # la prima deve essere H2
    if dedup and dedup[0]["level"] != 2:
        dedup[0]["level"] = 2
    # cap a max 6 sezioni H2: le eccedenze vengono unite alla sezione precedente (niente perdita di testo)
    MAX_H2 = 6
    capped, h2n = [], 0
    for s in dedup:
        if s["level"] == 2:
            if h2n >= MAX_H2 and capped:
                capped[-1]["paragraphs"].extend(s["paragraphs"])
                capped[-1]["source_segment_ids"] = capped[-1]["source_segment_ids"] + s["source_segment_ids"]
                continue
            h2n += 1
        elif not capped:
            s["level"] = 2
            h2n += 1
        capped.append(s)
    for i, s in enumerate(capped, 1):
        s["order"] = i
    toc = [{"id": s["id"], "heading": s["heading"]} for s in capped if s["level"] == 2]
    return capped, toc


def _sections_to_flat(sections: list) -> list:
    flat = []
    for s in sections:
        flat.extend(s["paragraphs"])
    return flat


def _final_valid(final: dict) -> bool:
    if not isinstance(final, dict):
        return False
    if not final.get("h1") or not final.get("meta_description"):
        return False
    if not isinstance(final.get("summary_sections"), list) or len(final["summary_sections"]) < 2:
        return False
    md = final.get("meta_description") or ""
    return 80 <= len(md) <= 220


# ----------------------------- pipeline -----------------------------
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
    segments, clean = b["segments"], b["clean"]
    clean_norm = su.normalize_for_match(clean)
    all_times = {s["start_hms"] for s in segments}
    duration_min = (ep.get("duration_seconds") or (segments[-1]["end"] if segments else 0)) / 60.0

    chunks = su.chunk_segments(segments, CHUNK_CHARS)
    seg_clean = su.segment_clean_text(segments)
    map_results, chunk_meta, total_chars, model = [], [], 0, MODEL_DEFAULT
    for ci, ch in enumerate(chunks):
        sub = [s for s in seg_clean if ch["seg_from"] <= s["idx"] <= ch["seg_to"]]
        ctext, _vt = _annotate_chunk(sub)
        try:
            data, n = await _llm_json(model, SYSTEM_MAP, _map_prompt(ctext), retries=1)
        except Exception as e:
            await auto.log_automation("ai_transcript", "warning", f"Map chunk fallito ({slug}): {e}")
            continue
        total_chars += n
        map_results.append(data)
        sec = data.get("section") or {}
        chunk_meta.append({"i": ci, "time": ch["start_hms"], "seg_from": ch["seg_from"],
                           "seg_to": ch["seg_to"], "heading": sec.get("heading", ""),
                           "paragraph": sec.get("paragraph", "")})
    if not map_results:
        return {"ok": False, "error": "Nessun blocco elaborato dall'AI."}

    topics = _dedupe_keep_order([t for m in map_results for t in m.get("topics", [])])
    entities = {
        "people": [p for p in _dedupe_keep_order([p for m in map_results for p in m.get("people", [])]) if _entity_present(p, clean_norm)][:20],
        "teams": [t for t in _dedupe_keep_order([t for m in map_results for t in m.get("teams", [])]) if _entity_present(t, clean_norm)][:20],
        "competitions": [c for c in _dedupe_keep_order([c for m in map_results for c in m.get("competitions", [])]) if _entity_present(c, clean_norm)][:10],
    }
    chapters = _validate_chapters([c for m in map_results for c in m.get("chapters", [])], all_times)
    quote_cap = 6 if ep.get("type") == "intervista" else 5
    quotes = _validate_quotes([q for m in map_results for q in m.get("quotes", [])], clean, all_times, quote_cap)

    notes = {
        "sections": [{"i": cm["i"], "time": cm["time"], "heading": cm["heading"], "paragraph": cm["paragraph"]}
                     for cm in chunk_meta if cm["heading"] or cm["paragraph"]],
        "topics": topics, "entities": entities,
    }

    async def _do_reduce(mdl):
        return await _llm_json(mdl, SYSTEM_REDUCE, _reduce_prompt(ep.get("title", ""), duration_min, notes), retries=1)

    fallback_used = False
    try:
        final, n = await _do_reduce(model)
        total_chars += n
        if not _final_valid(final):
            raise ValueError("controlli finali non superati")
    except Exception:
        fallback_used = True
        model = MODEL_FALLBACK
        final, n = await _do_reduce(model)
        total_chars += n

    sections, toc = _build_sections(final.get("summary_sections", []), chunk_meta)
    flat_summary = _sections_to_flat(sections)
    intro = final.get("intro") or ""
    related, internal_links = await _compute_links(slug, ep, entities)

    # validazione qualita' / needs_review
    lo, hi = _summary_target(int(duration_min * 60))
    sum_words = sum(_words(p) for s in sections for p in s["paragraphs"])
    intro_words = _words(intro)
    review_reasons = []
    if not (75 <= intro_words <= 160):
        review_reasons.append(f"intro {intro_words} parole (target 80-120)")
    if not (lo * 0.8 <= sum_words <= hi * 1.25):
        review_reasons.append(f"sommario {sum_words} parole (target {lo}-{hi})")
    h2_count = sum(1 for s in sections if s["level"] == 2)
    if h2_count < 2:
        review_reasons.append(f"solo {h2_count} sezioni H2")
    if any(s["confidence"] < 0.7 for s in sections):
        review_reasons.append("sezione/i a bassa confidence (senza segmento sorgente)")
    if not chapters:
        review_reasons.append("0 capitoli validi")
    needs_review = bool(review_reasons) or not _final_valid(final)

    tokens = total_chars // 4
    cost = round(tokens / 1000.0 * 0.0006, 5)
    now = datetime.now(timezone.utc).isoformat()
    preview = {
        "type": final.get("type") if final.get("type") in ("episodio", "intervista") else ep.get("type"),
        "guest_name": final.get("guest_name") or None,
        "h1": final.get("h1") or ep.get("title"),
        "seo_title": final.get("seo_title"),
        "meta_description": final.get("meta_description"),
        "excerpt": intro,
        "summary_sections": sections,
        "summary": flat_summary,
        "toc": toc,
        "topics": [str(x) for x in (topics)][:14],
        "key_passages": [str(x) for x in (final.get("key_passages") or [])][:8],
        "entities": entities, "chapters": chapters, "quotes": quotes,
        "related": related, "internal_links": internal_links,
        "meta": {
            "model": model, "fallback_used": fallback_used, "tokens": tokens, "cost_estimate": cost,
            "version": PROCESSING_VERSION, "created_at": now, "n_chunks": len(chunks),
            "n_chapters": len(chapters), "n_quotes": len(quotes), "n_sections": len(sections),
            "n_h2": h2_count, "intro_words": intro_words, "summary_words": sum_words,
            "duration_min": round(duration_min, 1), "needs_review": needs_review,
            "review_reasons": review_reasons, "chars_clean": b["chars_clean"],
        },
    }
    # snapshot anteprima precedente (per confronto/rollback)
    prev = ep.get("ai_preview")
    upd = {"ai_preview": preview, "transcription_chars": b["chars_clean"], "ai_preview_at": now}
    if prev:
        upd["ai_preview_prev"] = prev
    await db.episodes.update_one({"slug": slug}, {"$set": upd})
    await auto.log_automation("ai_transcript", "ok",
        f"Anteprima SEO v2 per '{ep.get('title','')[:50]}' (modello {model}, sez {len(sections)}, "
        f"cap {len(chapters)}, cit {len(quotes)}, intro {intro_words}w, sommario {sum_words}w, ~${cost})",
        {"slug": slug, "model": model, "needs_review": needs_review, "review_reasons": review_reasons,
         "tokens": tokens, "cost_estimate": cost})
    return {"ok": True, "slug": slug, "preview": preview}


async def _compute_links(slug, ep, entities):
    related, internal = [], []
    team = await db.team.find({}, {"_id": 0, "slug": 1, "name": 1}).to_list(100)
    names_norm = {su.normalize_for_match(m["name"]): m for m in team}
    cited = set()
    for p in (entities.get("people", []) + entities.get("teams", [])):
        n = su.normalize_for_match(p)
        for nm, m in names_norm.items():
            if nm and len(nm) > 3 and (nm in n or n in nm):
                cited.add(m["slug"])
    for s in list(cited)[:6]:
        m = next((x for x in team if x["slug"] == s), None)
        if m:
            internal.append({"type": "team", "slug": s, "label": m["name"]})
    others = await db.episodes.find(
        {"slug": {"$ne": slug}, "status": "pubblicato"},
        {"_id": 0, "slug": 1, "title": 1, "type": 1}).sort("published_at", -1).to_list(6)
    for o in others[:4]:
        related.append({"section": "interviste" if o.get("type") == "intervista" else "episodi",
                        "slug": o["slug"], "title": o["title"]})
    return related, internal


async def save_preview_sections(slug: str, sections: list) -> dict:
    """Salva le summary_sections modificate dall'admin (riordino/edit) senza pubblicare."""
    ep = await db.episodes.find_one({"slug": slug})
    if not ep or not ep.get("ai_preview"):
        return {"ok": False, "error": "Nessuna anteprima da modificare."}
    clean_sections, toc = _build_sections(sections, [])
    # mantiene i source_segment_ids/confidence se gia' presenti (build li azzera per quelli senza sources)
    by_heading = {s["heading"].lower(): s for s in (ep["ai_preview"].get("summary_sections") or [])}
    for s in clean_sections:
        old = by_heading.get(s["heading"].lower())
        if old:
            s["source_segment_ids"] = s["source_segment_ids"] or old.get("source_segment_ids", [])
            s["confidence"] = old.get("confidence", s["confidence"])
    preview = {**ep["ai_preview"], "summary_sections": clean_sections, "toc": toc,
               "summary": _sections_to_flat(clean_sections)}
    preview["meta"] = {**preview.get("meta", {}), "summary_words": sum(_words(p) for s in clean_sections for p in s["paragraphs"]),
                       "n_sections": len(clean_sections), "n_h2": sum(1 for s in clean_sections if s["level"] == 2),
                       "edited_at": datetime.now(timezone.utc).isoformat()}
    await db.episodes.update_one({"slug": slug}, {"$set": {"ai_preview": preview}})
    return {"ok": True, "summary_sections": clean_sections, "toc": toc}


async def publish_preview(slug: str) -> dict:
    ep = await db.episodes.find_one({"slug": slug})
    if not ep or not ep.get("ai_preview"):
        return {"ok": False, "error": "Nessuna anteprima da pubblicare."}
    p = ep["ai_preview"]
    upd = {
        "type": p.get("type") or ep.get("type"),
        "h1": p.get("h1"), "seo_title": p.get("seo_title"),
        "meta_description": p.get("meta_description"), "excerpt": p.get("excerpt"),
        "summary_sections": p.get("summary_sections", []), "summary": p.get("summary", []),
        "toc": p.get("toc", []), "topics": p.get("topics", []),
        "chapters": p.get("chapters", []), "quotes": p.get("quotes", []),
        "key_passages": p.get("key_passages", []), "entities": p.get("entities", {}),
        "related": p.get("related", []), "internal_links": p.get("internal_links", []),
        "has_transcript_page": True, "transcription_seo_status": "published",
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
        meta = (e.get("ai_preview") or {}).get("meta") or {}
        e["needs_review"] = bool(meta.get("needs_review")) if meta else False
        e["quality_status"] = _quality_status(meta) if meta else None
        e["has_preview"] = bool(e.get("ai_preview_at"))
        e["seo_status"] = e.get("transcription_seo_status") or ("preview" if e["has_preview"] else "none")
        e.pop("ai_preview", None)
    return {"episodes": eps, "total": len(eps)}


def _quality_status(meta: dict) -> str:
    """approved | approved_short | needs_review (qualita' > soglie, no padding)."""
    reasons = meta.get("review_reasons") or []
    hard = [r for r in reasons if not r.startswith("sommario") and not r.startswith("intro")]
    if hard:
        return "needs_review"
    sw = meta.get("summary_words", 0)
    dur = meta.get("duration_min", 0)
    nh2 = meta.get("n_h2", 0)
    min_ok = 450 if dur > 90 else (330 if dur <= 45 else 420)
    summary_short = any(r.startswith("sommario") for r in reasons)
    intro_short = any(r.startswith("intro") for r in reasons)
    if summary_short and sw >= min_ok and nh2 >= 3 and not intro_short:
        return "approved_short"
    if not reasons:
        return "approved"
    return "needs_review"


async def get_preview(slug: str) -> dict:
    ep = await db.episodes.find_one(
        {"slug": slug},
        {"_id": 0, "slug": 1, "title": 1, "ai_preview": 1, "h1": 1, "seo_title": 1,
         "meta_description": 1, "excerpt": 1, "summary": 1, "summary_sections": 1, "topics": 1,
         "chapters": 1, "quotes": 1, "transcription_seo_status": 1})
    if not ep:
        return {"ok": False, "error": "Contenuto non trovato"}
    current = {k: ep.get(k) for k in ("h1", "seo_title", "meta_description", "excerpt",
                                      "summary", "summary_sections", "topics", "chapters", "quotes")}
    return {"ok": True, "slug": slug, "title": ep.get("title"),
            "preview": ep.get("ai_preview"), "current": current,
            "seo_status": ep.get("transcription_seo_status") or "none"}


async def get_transcript_clean(slug: str) -> dict:
    b = await db.transcriptions.find_one({"slug": slug}, {"_id": 0, "clean": 1, "chars_clean": 1})
    return b or {}


async def get_transcript_segments(slug: str) -> list:
    b = await db.transcriptions.find_one({"slug": slug}, {"_id": 0, "segments": 1})
    if not b:
        await ensure_bundle(slug)
        b = await db.transcriptions.find_one({"slug": slug}, {"_id": 0, "segments": 1})
    return (b or {}).get("segments") or []
