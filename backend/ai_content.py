"""Step 4 — Classificazione AI e generazione automatica (gpt-5.4-mini via Emergent LLM key).

REGOLE FERREE (richieste dall'utente):
- Si generano SOLO: classificazione, titolo SEO, meta description, sommario PROVVISORIO,
  testo introduttivo, argomenti e keyword — partendo da TITOLO + DESCRIZIONE del video.
- NON si generano trascrizioni, citazioni o capitoli con timestamp finché non esiste una fonte reale.
- transcription_status resta "pending" finché non arrivano sottotitoli/audio (Step 3 + OAuth).
- La pagina è pubblicabile anche senza trascrizione.
- Niente virgolette senza fonte, niente timestamp inventati.
"""
import json
import uuid
from datetime import datetime, timezone

from config_db import db, EMERGENT_LLM_KEY
import automations as auto

AI_MODEL_DEFAULT = "gpt-5.4-mini"

DEFAULT_AI_SETTINGS = {
    "enabled": True,
    "auto_on_sync": False,      # durante i test: OFF (poi ON dall'utente)
    "auto_shorts": False,       # gli Short non vengono elaborati salvo attivazione
    "model": AI_MODEL_DEFAULT,
    "components": {
        "classification": True,
        "summary": True,
        "seo": True,
        "structured_data": True,
        "transcription": False,  # disattivata finché non c'è una fonte reale
    },
    "daily_limit": 100,
    "monthly_limit": 1000,
    "price_per_1k": 0.0006,      # stima costo (USD per 1k token) — solo indicativa
}

SYSTEM_MSG = (
    "Sei un editor SEO esperto del podcast italiano di calcio UnoXdue (Serie A). "
    "Lavori SOLO con il titolo e la descrizione forniti del video YouTube. "
    "NON inventare citazioni testuali, NON inventare capitoli con minutaggi, NON inventare "
    "dichiarazioni o eventi non presenti nel testo. Scrivi in italiano naturale e professionale. "
    "Rispondi ESCLUSIVAMENTE con JSON valido, senza testo prima o dopo."
)


def _build_prompt(title: str, description: str) -> str:
    desc = (description or "").strip()[:4000] or "(nessuna descrizione disponibile)"
    return (
        "Dati del video:\n"
        f"TITOLO: {title}\n"
        f"DESCRIZIONE: {desc}\n\n"
        "Genera SOLO sulla base di questi dati il seguente JSON:\n"
        "{\n"
        '  "type": "episodio | intervista | short",\n'
        '  "h1": "titolo H1 chiaro per la pagina (max ~70 caratteri)",\n'
        '  "seo_title": "title tag ottimizzato, includi UnoXdue (max ~60 caratteri)",\n'
        '  "meta_description": "meta description coinvolgente (120-158 caratteri)",\n'
        '  "intro": "1 paragrafo introduttivo (40-80 parole) basato sul contenuto reale",\n'
        '  "summary": ["2-4 brevi paragrafi di sommario PROVVISORIO derivati da titolo/descrizione"],\n'
        '  "topics": ["4-8 argomenti/temi chiave"],\n'
        '  "seo_keywords": ["5-10 keyword pertinenti"],\n'
        '  "guest_name": "nome dell\'ospite se è un\'intervista, altrimenti null"\n'
        "}\n"
        "Regole: classifica 'intervista' se è chiaramente un'intervista a un ospite; 'short' se è una clip breve; "
        "altrimenti 'episodio'. NON includere citazioni tra virgolette, NON includere orari/minutaggi, "
        "NON aggiungere campi extra. Solo JSON."
    )


async def _call_llm(model: str, prompt: str) -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"ai-{uuid.uuid4().hex[:8]}",
        system_message=SYSTEM_MSG,
    ).with_model("openai", model)
    resp = await chat.send_message(UserMessage(text=prompt))
    return resp if isinstance(resp, str) else str(resp)


async def get_ai_settings() -> dict:
    s = await db.settings.find_one({"_id": "global"}) or {}
    ai = s.get("ai") or {}
    merged = {**DEFAULT_AI_SETTINGS, **ai}
    merged["components"] = {**DEFAULT_AI_SETTINGS["components"], **(ai.get("components") or {})}
    return merged


async def set_ai_settings(patch: dict) -> dict:
    cur = await get_ai_settings()
    if "components" in patch and isinstance(patch["components"], dict):
        patch["components"] = {**cur["components"], **patch["components"]}
    new = {**cur, **patch}
    await db.settings.update_one({"_id": "global"}, {"$set": {"ai": new}}, upsert=True)
    return new


async def usage_counts() -> dict:
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")
    daily = await db.automation_logs.count_documents(
        {"kind": "ai_generate", "status": "ok", "created_at": {"$regex": f"^{day}"}})
    monthly = await db.automation_logs.count_documents(
        {"kind": "ai_generate", "status": "ok", "created_at": {"$regex": f"^{month}"}})
    return {"daily": daily, "monthly": monthly}


def _apply_components(ep: dict, data: dict, comp: dict) -> dict:
    """Costruisce l'update applicando solo i campi dei componenti abilitati."""
    upd = {}
    if comp.get("classification") and data.get("type") in ("episodio", "intervista", "short"):
        upd["type"] = data["type"]
        if data.get("guest_name"):
            upd["guest_name"] = data["guest_name"]
    if comp.get("seo"):
        for k in ("h1", "seo_title", "meta_description"):
            if data.get(k):
                upd[k] = data[k]
    if comp.get("summary"):
        if data.get("intro"):
            upd["excerpt"] = data["intro"]
        if isinstance(data.get("summary"), list) and data["summary"]:
            upd["summary"] = [str(x) for x in data["summary"]][:6]
        if isinstance(data.get("topics"), list) and data["topics"]:
            upd["topics"] = [str(x) for x in data["topics"]][:10]
    if comp.get("structured_data") and isinstance(data.get("seo_keywords"), list):
        upd["seo_keywords"] = [str(x) for x in data["seo_keywords"]][:12]
    return upd


async def generate_for_slug(slug: str, components: dict = None, is_auto: bool = False) -> dict:
    settings = await get_ai_settings()
    if not settings.get("enabled"):
        return {"ok": False, "error": "Generazione AI disattivata nelle Impostazioni."}
    if not EMERGENT_LLM_KEY:
        return {"ok": False, "error": "EMERGENT_LLM_KEY non configurata."}

    ep = await db.episodes.find_one({"slug": slug})
    if not ep:
        return {"ok": False, "error": "Contenuto non trovato."}

    # limiti d'uso
    use = await usage_counts()
    if use["daily"] >= int(settings.get("daily_limit", 0) or 0):
        await auto.log_automation("ai_generate", "warning", f"Limite giornaliero raggiunto ({use['daily']})", {"slug": slug})
        return {"ok": False, "error": "Limite giornaliero AI raggiunto."}
    if use["monthly"] >= int(settings.get("monthly_limit", 0) or 0):
        await auto.log_automation("ai_generate", "warning", f"Limite mensile raggiunto ({use['monthly']})", {"slug": slug})
        return {"ok": False, "error": "Limite mensile AI raggiunto."}

    comp = components or settings.get("components", {})
    model = settings.get("model", AI_MODEL_DEFAULT)
    prompt = _build_prompt(ep.get("title", ""), ep.get("excerpt") or ep.get("description") or "")
    max_retries = 1 if is_auto else 0  # un solo retry automatico

    raw = ""
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            raw = await _call_llm(model, prompt)
            data = json.loads(auto._strip_json(raw))
            upd = _apply_components(ep, data, comp)
            tokens = (len(prompt) + len(raw)) // 4
            cost = round(tokens / 1000.0 * float(settings.get("price_per_1k", 0) or 0), 5)
            now = datetime.now(timezone.utc).isoformat()
            ai_meta = {
                "status": "ok",
                "model": model,
                "last_run": now,
                "components_done": {k: bool(comp.get(k)) for k in DEFAULT_AI_SETTINGS["components"]},
                "transcription_status": "pending",
                "retries": attempt,
                "tokens": tokens,
                "cost_estimate": cost,
                "error": None,
            }
            upd["ai"] = ai_meta
            upd["updated_at"] = now
            # pubblicabile dopo l'elaborazione (a meno che sia esplicitamente in bozza)
            if ep.get("status") != "bozza":
                upd["status"] = "pubblicato"
            await db.episodes.update_one({"slug": slug}, {"$set": upd})
            await auto.log_automation(
                "ai_generate", "ok",
                f"AI generata per '{ep.get('title','')[:60]}' (modello {model}, ~{tokens} token, ~${cost})",
                {"slug": slug, "model": model, "tokens": tokens, "cost_estimate": cost, "components": comp},
            )
            return {"ok": True, "slug": slug, "ai": ai_meta, "fields": {k: upd[k] for k in upd if k not in ("ai", "updated_at")}}
        except json.JSONDecodeError as e:
            last_err = f"JSON non valido: {e}"
        except Exception as e:
            last_err = str(e)

    # fallita dopo i tentativi -> Da verificare
    now = datetime.now(timezone.utc).isoformat()
    await db.episodes.update_one({"slug": slug}, {"$set": {
        "status": "da_verificare",
        "ai": {"status": "failed", "model": model, "last_run": now, "error": last_err,
               "transcription_status": "pending", "retries": max_retries},
        "updated_at": now,
    }})
    await auto.log_automation("ai_generate", "error", f"AI fallita per '{ep.get('title','')[:60]}': {last_err}", {"slug": slug})
    return {"ok": False, "error": last_err, "slug": slug}


async def process_batch(only_missing: bool = True, types=None, limit: int = 20, slugs=None) -> dict:
    if slugs:
        target = list(slugs)[:int(limit) if limit else len(slugs)] if limit else list(slugs)
    else:
        q = {}
        if only_missing:
            q["$or"] = [{"ai": {"$exists": False}}, {"ai.status": {"$ne": "ok"}}]
        if types:
            q["type"] = {"$in": types}
        items = await db.episodes.find(q, {"slug": 1, "_id": 0}).limit(int(limit)).to_list(int(limit))
        target = [i["slug"] for i in items]
    ok = failed = 0
    results = []
    for s in target:
        r = await generate_for_slug(s, is_auto=False)
        results.append({"slug": s, "ok": r.get("ok", False), "error": r.get("error")})
        if r.get("ok"):
            ok += 1
        else:
            failed += 1
    await auto.log_automation("ai_generate", "info", f"Batch AI: {ok} ok, {failed} falliti su {len(target)}",
                              {"ok": ok, "failed": failed, "total": len(target)})
    return {"ok": True, "processed": len(target), "succeeded": ok, "failed": failed, "results": results,
            "remaining_hint": "Riesegui per elaborare i contenuti rimanenti." if (not slugs and len(target) == int(limit)) else ""}


async def maybe_autorun_after_sync(sync_result: dict) -> dict:
    """Chiamato dopo la sync YouTube: elabora con AI i nuovi/aggiornati se l'automatico è attivo."""
    settings = await get_ai_settings()
    if not (settings.get("enabled") and settings.get("auto_on_sync")):
        return {"ran": False}
    affected = sync_result.get("affected", [])[:10]  # cap di sicurezza per non bloccare la risposta
    ok = 0
    for slug in affected:
        r = await generate_for_slug(slug, is_auto=True)
        if r.get("ok"):
            ok += 1
    return {"ran": True, "processed": len(affected), "succeeded": ok}
