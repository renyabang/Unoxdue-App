"""Macro B — Pipeline testi unici per giornata Pronostici.

Flusso (nessuna pubblicazione automatica):
  1. recupero fonti verificabili con Perplexity (contesto giornata, calendario, squadre, notizie)
  2. salvataggio URL / editore / titolo / data delle fonti
  3. generazione bozza editoriale (gpt-5.4-mini via Emergent) attorno ALLE GIOCATE REALI già presenti
     nel documento (intro, contesto, partite, riepilogo pronostici reali, link episodio, risultati, disclaimer)
  4. controllo similarità con le altre giornate (shingle Jaccard)
  5. controllo antiallucinazione (partite/quote solo dai dati reali; niente esiti inventati)
  6. stato `ai_preview` sul documento (mai `pubblicato`)

REGOLE FERREE: l'AI scrive SOLO testo editoriale. Non inventa selezioni, quote, risultati o statistiche.
Le giocate, i mercati e le quote restano quelli reali inseriti dal team (OCR/CMS).
"""
import re
import json
import uuid
import asyncio
from datetime import datetime, timezone

import requests

from config_db import db, EMERGENT_LLM_KEY, PERPLEXITY_API_KEY, SITE_URL
import automations as auto

AI_MODEL = "gpt-5.4-mini"
SIMILARITY_THRESHOLD = 0.55
ODDS_RE = re.compile(r"\b\d{1,2}[.,]\d{2}\b")

SYSTEM_MSG = (
    "Sei un editor sportivo del podcast italiano UnoXdue (Serie A). Scrivi testi editoriali originali, "
    "chiari e utili in italiano. REGOLE FERREE: usa ESCLUSIVAMENTE le partite, i mercati e le quote forniti "
    "nei dati; NON inventare selezioni, quote, statistiche, formazioni o risultati; NON dichiarare esiti di "
    "partite non ancora giocate; cita solo informazioni di contesto verificabili dalle fonti fornite. "
    "Rispondi ESCLUSIVAMENTE con JSON valido."
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _domain(u: str) -> str:
    m = re.search(r"https?://([^/]+)/?", u or "")
    h = (m.group(1).lower() if m else "")
    return h[4:] if h.startswith("www.") else h


# ----------------------- estrazione dati reali dalle giocate -----------------------
def _matches_and_odds(picks):
    matches, odds = [], set()
    for pk in picks or []:
        if pk.get("total_odds"):
            odds.add(str(pk["total_odds"]).replace(",", "."))
        for sel in pk.get("selections", []):
            mt = (sel.get("match") or "").strip()
            if mt and mt not in matches:
                matches.append(mt)
            if sel.get("odds"):
                odds.add(str(sel["odds"]).replace(",", "."))
    return matches, odds


def _teams_from_matches(matches):
    teams = set()
    for m in matches:
        for part in re.split(r"\s*[-–]\s*", m):
            t = part.strip().lower()
            if t:
                teams.add(t)
    return teams


# ----------------------- Perplexity: fonti verificabili -----------------------
def _perplexity_sync(season, round_, matches):
    if not PERPLEXITY_API_KEY:
        return {"ok": False, "demo": True, "text": "", "sources": []}
    match_list = "; ".join(matches[:12]) or "le partite della giornata"
    prompt = (
        f"Contesto per la {round_}ª giornata di Serie A {season}. Partite di riferimento: {match_list}. "
        "Riassumi in modo sintetico e verificabile: stato delle squadre, posizione in classifica, notizie "
        "recenti rilevanti (assenze, momento di forma) e calendario. Indica solo fatti verificabili e cita le fonti."
    )
    try:
        r = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"},
            json={"model": "sonar",
                  "messages": [{"role": "system", "content": "Sei un ricercatore sportivo. Rispondi in italiano, conciso, con fatti verificabili."},
                               {"role": "user", "content": prompt}]},
            timeout=40,
        )
        r.raise_for_status()
        data = r.json()
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        cites = data.get("citations") or []
        sources = []
        for c in cites:
            url = c if isinstance(c, str) else (c.get("url") if isinstance(c, dict) else None)
            if not url:
                continue
            title = (c.get("title") if isinstance(c, dict) else "") or ""
            date = (c.get("date") if isinstance(c, dict) else "") or ""
            sources.append({"url": url, "publisher": _domain(url), "title": title, "date": date})
        return {"ok": True, "demo": False, "text": text, "sources": sources}
    except Exception as e:
        return {"ok": False, "error": str(e), "text": "", "sources": []}


async def gather_sources(season, round_, matches):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _perplexity_sync, season, round_, matches)


# ----------------------- LLM: bozza editoriale -----------------------
def _build_prompt(season, round_, comp, matches, picks, context_text, episode_url):
    picks_lines = []
    for pk in picks or []:
        sels = "; ".join(f'{s.get("match")} — {s.get("market")}: {s.get("pick")} @ {s.get("odds")}'
                         for s in pk.get("selections", []))
        picks_lines.append(f'{pk.get("tipster")} ({pk.get("type")}, quota totale {pk.get("total_odds")}): {sels}')
    picks_block = "\n".join(picks_lines) or "(nessuna giocata)"
    ctx = (context_text or "").strip()[:2500] or "(nessun contesto disponibile)"
    return (
        f"Giornata: {round_}ª di {comp} {season}.\n"
        f"PARTITE COINVOLTE (usa SOLO queste): {', '.join(matches) or 'n/d'}\n\n"
        f"GIOCATE REALI DEL TEAM (usa SOLO queste, non modificarle):\n{picks_block}\n\n"
        f"CONTESTO VERIFICABILE (dalle fonti, usalo con cautela):\n{ctx}\n\n"
        f"Link episodio (se presente): {episode_url or 'nessuno'}\n\n"
        "Genera un JSON con questa struttura:\n"
        "{\n"
        '  "intro": "1 paragrafo (50-90 parole) che introduce la giornata e le giocate di UnoXdue",\n'
        '  "context": "1-2 paragrafi di contesto della giornata basati SOLO sul contesto fornito (niente dati inventati)",\n'
        '  "matches": [{"match": "Squadra - Squadra (solo dalle partite coinvolte)", "comment": "1-2 frasi di lettura della partita legate al mercato giocato"}],\n'
        '  "picks_summary": "1 paragrafo che riassume le giocate del team citando i mercati reali (NON inventare quote diverse)",\n'
        '  "episode_link_text": "1 frase che invita ad ascoltare la puntata collegata (o stringa vuota se non c\'è episodio)",\n'
        '  "results_note": "1 frase neutra: i risultati verranno verificati con gli esiti ufficiali a fine giornata (NON dichiarare esiti)",\n'
        '  "disclaimer": "1 frase: contenuto editoriale a scopo di intrattenimento, 18+, gioca responsabilmente"\n'
        "}\n"
        "Solo JSON, nessun testo prima o dopo."
    )


async def _call_llm(prompt):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"pred-{uuid.uuid4().hex[:8]}",
                   system_message=SYSTEM_MSG).with_model("openai", AI_MODEL)
    resp = await chat.send_message(UserMessage(text=prompt))
    return resp if isinstance(resp, str) else str(resp)


# ----------------------- controlli -----------------------
def _shingles(text, k=5):
    words = re.findall(r"\w+", (text or "").lower())
    return set(tuple(words[i:i + k]) for i in range(max(0, len(words) - k + 1)))


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return round(inter / union, 4) if union else 0.0


def _draft_text(d):
    parts = [d.get("intro", ""), d.get("context", ""), d.get("picks_summary", "")]
    parts += [m.get("comment", "") for m in d.get("matches", [])]
    return " ".join(p for p in parts if p)


HEDGE_RE = re.compile(r"\b(forse|probabilmente|potrebbe|dovrebbe|sembra|pare che|si dice|"
                      r"in teoria|presumibilmente|verosimilmente|chissà)\b", re.I)


def _low_confidence(draft):
    """Segnala frasi con linguaggio incerto (da rivedere prima della pubblicazione)."""
    out = []
    blocks = [("intro", draft.get("intro", "")), ("context", draft.get("context", "")),
              ("picks_summary", draft.get("picks_summary", ""))]
    blocks += [("match", m.get("comment", "")) for m in draft.get("matches", [])]
    for where, txt in blocks:
        for sent in re.split(r"(?<=[.!?])\s+", txt or ""):
            if HEDGE_RE.search(sent):
                out.append({"where": where, "text": sent.strip()[:200]})
    return out


async def log_audit(action, season, round_, admin="admin", details=None):
    await db.audit_log.insert_one({
        "entity": "prediction_ai", "action": action, "season": season, "round": round_,
        "admin": admin, "at": _now(), "details": details or {},
    })


async def _similarity_report(draft, season, round_):
    others = await db.predictions.find(
        {"ai_draft": {"$exists": True}, "$nor": [{"season": season, "round": round_}]},
        {"_id": 0, "season": 1, "round": 1, "ai_draft": 1}).to_list(100)
    sh = _shingles(_draft_text(draft))
    worst = {"max_similarity": 0.0, "against": None}
    for o in others:
        sim = _jaccard(sh, _shingles(_draft_text(o.get("ai_draft", {}))))
        if sim > worst["max_similarity"]:
            worst = {"max_similarity": sim, "against": f'{o.get("season")} g{o.get("round")}'}
    worst["passed"] = worst["max_similarity"] < SIMILARITY_THRESHOLD
    worst["threshold"] = SIMILARITY_THRESHOLD
    return worst


def _antihallucination(draft, matches, odds):
    issues = []
    valid_teams = _teams_from_matches(matches)
    kept_matches = []
    for m in draft.get("matches", []):
        mt = (m.get("match") or "").strip()
        mteams = _teams_from_matches([mt])
        # almeno una squadra deve combaciare con le partite reali
        if mteams and (mteams & valid_teams):
            kept_matches.append(m)
        else:
            issues.append(f"partita non presente nelle giocate rimossa: '{mt}'")
    draft["matches"] = kept_matches
    # quote: segnala numeri quota non presenti nei dati reali
    text = _draft_text(draft) + " " + draft.get("results_note", "")
    found = set(o.replace(",", ".") for o in ODDS_RE.findall(text))
    real = set(o.replace(",", ".") for o in odds)
    extra = sorted(found - real)
    if extra:
        issues.append(f"possibili quote non verificate citate nel testo: {', '.join(extra)}")
    return {"passed": len([i for i in issues if 'quote' not in i]) == 0 and not extra,
            "issues": issues, "matches_kept": len(kept_matches)}


# ----------------------- generazione bozza -----------------------
async def generate_draft(season, round_):
    if not EMERGENT_LLM_KEY:
        return {"ok": False, "error": "EMERGENT_LLM_KEY non configurata"}
    p = await db.predictions.find_one({"season": season, "round": round_})
    if not p:
        return {"ok": False, "error": "Giornata non trovata"}
    comp = p.get("competition", "Serie A")
    picks = p.get("picks", [])
    matches, odds = _matches_and_odds(picks)
    episode_url = p.get("episode_url")

    src = await gather_sources(season, round_, matches)
    prompt = _build_prompt(season, round_, comp, matches, picks, src.get("text", ""), episode_url)

    raw = ""
    try:
        raw = await _call_llm(prompt)
        draft = json.loads(auto._strip_json(raw))
    except Exception as e:
        await auto.log_automation("predictions_ai", "error", f"Bozza fallita g{round_} {season}: {e}",
                                  {"season": season, "round": round_})
        return {"ok": False, "error": f"Generazione fallita: {e}", "raw": raw[:500]}

    anti = _antihallucination(draft, matches, odds)
    sim = await _similarity_report(draft, season, round_)
    tokens = (len(prompt) + len(raw)) // 4
    cost = round(tokens / 1000.0 * 0.0006, 5)

    ai_draft = {
        **{k: draft.get(k, "") for k in ("intro", "context", "picks_summary",
                                         "episode_link_text", "results_note", "disclaimer")},
        "matches": draft.get("matches", []),
        "generated_at": _now(), "model": AI_MODEL, "tokens": tokens, "cost_estimate": cost,
        "sources": src.get("sources", []), "sources_demo": bool(src.get("demo")),
        "external_facts": (src.get("text") or "")[:4000],
        "low_confidence": _low_confidence(draft),
        "similarity": sim, "antihallucination": anti,
        "ai_status": "ai_preview", "edited": False,
        "ready": anti["passed"] and sim["passed"],
    }
    await db.predictions.update_one(
        {"season": season, "round": round_},
        {"$set": {"ai_draft": ai_draft, "ai_status": "ai_preview", "updated_at": _now()}})
    await log_audit("generate", season, round_,
                    details={"ready": ai_draft["ready"], "sources": len(ai_draft["sources"]),
                             "similarity": sim["max_similarity"], "cost": cost})
    await auto.log_automation(
        "predictions_ai", "ok",
        f"Bozza ai_preview g{round_} {season} (sim {sim['max_similarity']}, fonti {len(ai_draft['sources'])}, ~${cost})",
        {"season": season, "round": round_, "ready": ai_draft["ready"]})
    return {"ok": True, "season": season, "round": round_, "ai_status": "ai_preview", "ai_draft": ai_draft}


async def batch_generate(season=None, rounds=None, only_missing=True, limit=10):
    q = {}
    if season:
        q["season"] = season
    if rounds:
        q["round"] = {"$in": list(rounds)}
    if only_missing:
        q["ai_draft"] = {"$exists": False}
    items = await db.predictions.find(q, {"_id": 0, "season": 1, "round": 1}).sort("round", 1).to_list(int(limit))
    results = []
    for it in items:
        r = await generate_draft(it["season"], it["round"])
        results.append({"season": it["season"], "round": it["round"], "ok": r.get("ok"),
                        "ready": (r.get("ai_draft") or {}).get("ready"), "error": r.get("error")})
    return {"ok": True, "processed": len(results), "results": results}


# ===================== Cruscotto admin "Bozze AI Pronostici" =====================
EDITABLE_FIELDS = ("intro", "context", "picks_summary", "episode_link_text", "results_note", "disclaimer")
SEASON_RE = re.compile(r"^\d{4}-\d{4}$")


async def list_drafts():
    docs = await db.predictions.find(
        {"ai_draft": {"$exists": True}},
        {"_id": 0, "season": 1, "round": 1, "competition": 1, "status": 1, "ai_status": 1,
         "episode_url": 1, "ai_draft": 1, "editorial": 1, "cover": 1, "picks": 1}
    ).sort([("season", -1), ("round", -1)]).to_list(500)
    out = []
    for d in docs:
        ad = d.get("ai_draft", {})
        warnings = list(ad.get("antihallucination", {}).get("issues", []))
        if ad.get("low_confidence"):
            warnings.append(f'{len(ad["low_confidence"])} frasi a bassa confidence')
        out.append({
            "season": d.get("season"), "round": d.get("round"),
            "competition": d.get("competition", "Serie A"),
            "status": d.get("status"), "ai_status": ad.get("ai_status") or d.get("ai_status"),
            "generated_at": ad.get("generated_at"), "sources_count": len(ad.get("sources", [])),
            "cost": ad.get("cost_estimate"),
            "similarity": ad.get("similarity", {}).get("max_similarity"),
            "similarity_passed": ad.get("similarity", {}).get("passed"),
            "warnings": warnings, "ready": ad.get("ready"),
            "episode_url": d.get("episode_url"),
            "has_published_editorial": bool(d.get("editorial")),
            "picks_count": len(d.get("picks", [])),
            "has_cover": bool((d.get("cover") or {}).get("formats", {}).get("horizontal")),
        })
    return {"ok": True, "count": len(out), "drafts": out}


async def get_detail(season, round_):
    d = await db.predictions.find_one({"season": season, "round": round_}, {"_id": 0})
    if not d or not d.get("ai_draft"):
        return {"ok": False, "error": "Bozza non trovata"}
    picks_used = [{"tipster": p.get("tipster"), "type": p.get("type"), "total_odds": p.get("total_odds"),
                   "selections": [{"match": s.get("match"), "market": s.get("market"),
                                   "pick": s.get("pick"), "odds": s.get("odds")}
                                  for s in p.get("selections", [])]}
                  for p in d.get("picks", [])]
    return {"ok": True, "season": season, "round": round_, "competition": d.get("competition", "Serie A"),
            "status": d.get("status"), "ai_draft": d.get("ai_draft"),
            "picks_used": picks_used, "episode_url": d.get("episode_url"),
            "published_editorial": d.get("editorial"),
            "canonical": f'{SITE_URL}/pronostici/serie-a/{season}/giornata-{round_}/',
            "cover": d.get("cover")}


async def edit_draft(season, round_, fields, matches=None):
    d = await db.predictions.find_one({"season": season, "round": round_})
    if not d or not d.get("ai_draft"):
        return {"ok": False, "error": "Bozza non trovata"}
    ad = dict(d["ai_draft"])
    for k, v in (fields or {}).items():
        if k in EDITABLE_FIELDS and isinstance(v, str):
            ad[k] = v
    if matches is not None:
        ad["matches"] = [{"match": m.get("match", ""), "comment": m.get("comment", "")} for m in matches]
    # ricontrolla coerenza con i dati reali dopo la modifica manuale
    matches_real, odds = _matches_and_odds(d.get("picks", []))
    ad["antihallucination"] = _antihallucination(ad, matches_real, odds)
    ad["similarity"] = await _similarity_report(ad, season, round_)
    ad["low_confidence"] = _low_confidence(ad)
    ad["edited"] = True
    ad["ai_status"] = "in_review"
    ad["ready"] = ad["antihallucination"]["passed"] and ad["similarity"]["passed"]
    await db.predictions.update_one({"season": season, "round": round_},
                                    {"$set": {"ai_draft": ad, "ai_status": "in_review", "updated_at": _now()}})
    await log_audit("edit", season, round_, details={"fields": list((fields or {}).keys())})
    return {"ok": True, "ai_draft": ad}


async def set_ai_status(season, round_, action):
    mapping = {"approve": "approved", "reject": "rejected", "review": "in_review"}
    if action not in mapping:
        return {"ok": False, "error": "Azione non valida"}
    d = await db.predictions.find_one({"season": season, "round": round_})
    if not d or not d.get("ai_draft"):
        return {"ok": False, "error": "Bozza non trovata"}
    new_status = mapping[action]
    await db.predictions.update_one({"season": season, "round": round_},
                                    {"$set": {"ai_draft.ai_status": new_status, "ai_status": new_status,
                                              "updated_at": _now()}})
    await log_audit(action, season, round_)
    return {"ok": True, "ai_status": new_status}


def _reachable_sync(url):
    try:
        r = requests.head(url, timeout=8, allow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0 UnoXdueBot"})
        if r.status_code >= 400:
            r = requests.get(url, timeout=10, allow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 UnoXdueBot"}, stream=True)
        return r.status_code < 400
    except Exception:
        return False


async def publish_safety(season, round_):
    """Controlli editoriali pre-pubblicazione. Ritorna passed + checklist dettagliata."""
    d = await db.predictions.find_one({"season": season, "round": round_})
    if not d or not d.get("ai_draft"):
        return {"ok": False, "error": "Bozza non trovata"}
    ad = d["ai_draft"]
    picks = d.get("picks", [])
    has_real_pick = any(p.get("selections") for p in picks)
    sources = ad.get("sources", [])
    loop = asyncio.get_event_loop()
    reach = []
    for s in sources[:8]:
        ok = await loop.run_in_executor(None, _reachable_sync, s.get("url"))
        reach.append({"url": s.get("url"), "publisher": s.get("publisher"), "reachable": ok})
    sources_ok = (not sources) or any(r["reachable"] for r in reach)
    cover_ok = bool((d.get("cover") or {}).get("formats", {}).get("horizontal"))
    season_ok = bool(SEASON_RE.match(season or "")) and isinstance(round_, int) and 1 <= round_ <= 60
    canonical = f"{SITE_URL}/pronostici/serie-a/{season}/giornata-{round_}/"
    slug_ok = canonical.endswith(f"/giornata-{round_}/") and "/serie-a/" in canonical
    disclaimer_ok = bool((ad.get("disclaimer") or "").strip())
    checks = {
        "almeno_un_pronostico_reale": has_real_pick,
        "fonti_raggiungibili": sources_ok,
        "nessuna_informazione_inventata": ad.get("antihallucination", {}).get("passed", False),
        "similarita_sotto_soglia": ad.get("similarity", {}).get("passed", False),
        "stagione_giornata_valide": season_ok,
        "canonical_slug_corretti": slug_ok,
        "copertina_automatica_disponibile": cover_ok,
        "disclaimer_presente": disclaimer_ok,
    }
    return {"ok": True, "passed": all(checks.values()), "checks": checks,
            "sources_reachability": reach, "canonical": canonical}


async def promote(season, round_, confirm=False):
    if not confirm:
        return {"ok": False, "error": "Conferma esplicita richiesta (confirm=true)"}
    safety = await publish_safety(season, round_)
    if not safety.get("ok"):
        return safety
    if not safety["passed"]:
        await log_audit("publish_blocked", season, round_, details={"checks": safety["checks"]})
        return {"ok": False, "error": "Controlli di sicurezza non superati", "checks": safety["checks"],
                "sources_reachability": safety.get("sources_reachability")}
    d = await db.predictions.find_one({"season": season, "round": round_})
    ad = d["ai_draft"]
    editorial = {
        "intro": ad.get("intro", ""), "context": ad.get("context", ""),
        "matches": ad.get("matches", []), "picks_summary": ad.get("picks_summary", ""),
        "results_note": ad.get("results_note", ""), "disclaimer": ad.get("disclaimer", ""),
        "sources": ad.get("sources", []), "published_at": _now(), "source": "ai_promoted",
    }
    update = {"editorial": editorial, "status": "pubblicato",
              "ai_status": "published", "ai_draft.ai_status": "published", "updated_at": _now()}
    # promuovi l'intro AI solo se l'intro pubblica è assente/molto breve (NON tocca le giocate reali)
    if len((d.get("intro") or "").strip()) < 40 and ad.get("intro"):
        update["intro"] = ad["intro"]
    await db.predictions.update_one({"season": season, "round": round_}, {"$set": update})
    # assicura la copertina automatica (non blocca)
    try:
        import graphics as gfx
        await gfx.auto_generate_cover(season, round_)
    except Exception:
        pass
    await log_audit("publish", season, round_, details={"checks": safety["checks"]})
    return {"ok": True, "status": "pubblicato", "ai_status": "published",
            "public_url": f"{SITE_URL}/pronostici/serie-a/{season}/giornata-{round_}/"}
