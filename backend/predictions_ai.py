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
        "similarity": sim, "antihallucination": anti,
        "ready": anti["passed"] and sim["passed"],
    }
    await db.predictions.update_one(
        {"season": season, "round": round_},
        {"$set": {"ai_draft": ai_draft, "ai_status": "ai_preview", "updated_at": _now()}})
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
