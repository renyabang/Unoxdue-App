"""Step 7B — Rassegna stampa: ricerca web astratta + provider-agnostica.

- PressProvider: interfaccia astratta `search(query)`.
- FixturePressProvider: dataset deterministico (demo) per i test.
- PerplexityPressProvider: PREDISPOSTO ma attivo SOLO con PERPLEXITY_API_KEY (ricerca reale disattivata in demo).
- Modello dati: testata, titolo, url, canonical_url, data, sintesi originale (NO testo integrale),
  contenuto UnoXdue collegato, query, data di rilevamento, stato, confidence.
- Dedup per URL canonica, verifica raggiungibilità, associazione a episodio/intervista/ospite/team,
  stati (found/verified/review/published/discarded/error), log, retry, anteprima prima della pubblicazione.
"""
import re
import json
import uuid
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

import requests

from config_db import db, PERPLEXITY_API_KEY
import automations as auto

ALLOWED_STATUS = {"found", "verified", "review", "published", "discarded", "error"}
CURATED = {"published", "discarded", "verified"}  # non sovrascritti dal re-run
PERPLEXITY_MODEL = "sonar"
LOW_CONF = 0.6


def _now():
    return datetime.now(timezone.utc).isoformat()


def canonical_url(u: str) -> str:
    try:
        p = urlparse((u or "").strip())
        host = p.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        path = p.path.rstrip("/") or "/"
        scheme = (p.scheme or "https").lower()
        return urlunparse((scheme, host, path, "", "", ""))
    except Exception:
        return (u or "").strip()


# ----------------------- Provider -----------------------
class PressProvider(ABC):
    name = "base"

    @abstractmethod
    async def search(self, query: str):
        ...


class FixturePressProvider(PressProvider):
    """Dataset demo deterministico (menzioni UnoXdue + membri team + un URL non raggiungibile)."""
    name = "fixture"

    RESULTS = [
        {"source": "La Gazzetta dello Sport",
         "title": "UnoXdue, il podcast Serie A di Sono Micuccio conquista il pubblico",
         "url": "https://www.gazzetta.it/",
         "date": "2026-05-20",
         "summary": "Il podcast UnoXdue cresce negli ascolti grazie alle analisi di Sono Micuccio.",
         "confidence": 0.9},
        {"source": "Tuttomercatoweb",
         "title": "L'ospite di UnoXdue parla di calciomercato: le dichiarazioni",
         "url": "https://www.tuttomercatoweb.com/",
         "date": "2026-05-18",
         "summary": "Nell'ultima puntata di UnoXdue l'ospite ha commentato il mercato di Serie A.",
         "confidence": 0.78},
        {"source": "Corriere dello Sport",
         "title": "Il Ninja e Il Marziano analizzano la giornata su UnoXdue",
         "url": "https://www.corrieredellosport.it/",
         "date": "2026-05-15",
         "summary": "I tipster Il Ninja e Il Marziano di UnoXdue discutono i pronostici della giornata.",
         "confidence": 0.82},
        {"source": "Blog demo",
         "title": "Pronostici della settimana",
         "url": "https://nonexistent-uxd-demo.invalid/articolo",
         "date": "2026-05-10",
         "summary": "Articolo senza menzione diretta del podcast.",
         "confidence": 0.3},
    ]

    async def search(self, query: str):
        return [dict(r) for r in self.RESULTS]


class PerplexityPressProvider(PressProvider):
    """Predisposto per Perplexity. Attivo solo con PERPLEXITY_API_KEY."""
    name = "perplexity"

    async def search(self, query: str):
        def _call():
            prompt = (
                f"Trova articoli di stampa recenti che menzionano '{query}'. "
                "Rispondi SOLO con un array JSON di oggetti con campi: source (testata), title, url, "
                "date (YYYY-MM-DD), summary (1-2 frasi TUE, NON copiare il testo dell'articolo), "
                "confidence (0..1). Nessun testo fuori dal JSON."
            )
            r = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"},
                json={"model": PERPLEXITY_MODEL, "messages": [{"role": "user", "content": prompt}]},
                timeout=30)
            r.raise_for_status()
            return r.json()

        data = await asyncio.get_event_loop().run_in_executor(None, _call)
        content = (data.get("choices", [{}])[0].get("message", {}) or {}).get("content", "")
        content = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", (content or "").strip())
        try:
            arr = json.loads(content)
        except Exception:
            arr = []
        out = []
        for it in (arr if isinstance(arr, list) else []):
            out.append({"source": it.get("source", ""), "title": it.get("title", ""),
                        "url": it.get("url", ""), "date": it.get("date", ""),
                        "summary": it.get("summary", ""), "confidence": it.get("confidence")})
        return out


def get_provider() -> PressProvider:
    if PERPLEXITY_API_KEY:
        return PerplexityPressProvider()
    return FixturePressProvider()


def provider_status() -> dict:
    active = get_provider().name
    return {"configured": bool(PERPLEXITY_API_KEY), "provider": active, "active": active,
            "demo": active == "fixture",
            "note": ("Rassegna stampa in modalità fixture (demo). Inserisci PERPLEXITY_API_KEY per la ricerca reale, "
                     "senza modificare il modello dati.")}


# ----------------------- reachability -----------------------
def _reach_sync(url: str):
    headers = {"User-Agent": "UnoXdueBot/1.0 (+https://unoxdue.net)"}
    try:
        r = requests.head(url, timeout=8, allow_redirects=True, headers=headers)
        if r.status_code >= 400:
            r = requests.get(url, timeout=8, allow_redirects=True, headers=headers, stream=True)
        return r.status_code, r.status_code < 400
    except Exception:
        return None, False


# ----------------------- associazione contenuti -----------------------
async def _associate(text: str):
    t = (text or "").lower()
    team = await db.team.find({}, {"_id": 0, "slug": 1, "name": 1}).to_list(100)
    for m in team:
        nm = (m.get("name") or "").lower()
        if nm and len(nm) > 3 and nm in t:
            return {"type": "team", "slug": m.get("slug"), "title": m.get("name")}
    eps = await db.episodes.find({}, {"_id": 0, "slug": 1, "title": 1, "type": 1, "guest_name": 1}).to_list(2000)
    for e in eps:
        gn = (e.get("guest_name") or "").lower()
        if gn and len(gn) > 3 and gn in t:
            return {"type": "interview" if e.get("type") == "intervista" else "episode",
                    "slug": e.get("slug"), "title": e.get("title")}
    return None


def _decide_status(reachable, confidence, mentions, linked) -> str:
    if not reachable:
        return "error"
    c = confidence if confidence is not None else 0.5
    if c >= 0.75 and mentions and linked:
        return "verified"
    if c < LOW_CONF or not mentions:
        return "review"
    return "found"


# ----------------------- pipeline -----------------------
async def run_search(query: str = "UnoXdue", actor: str = "admin") -> dict:
    provider = get_provider()
    raw, last = None, None
    for _ in range(2):  # retry
        try:
            raw = await provider.search(query)
            break
        except Exception as e:
            last = str(e)
    if raw is None:
        await auto.log_automation("press", "error", f"Ricerca rassegna fallita: {last}")
        return {"ok": False, "error": last or "Provider non disponibile"}

    loop = asyncio.get_event_loop()
    found = updated = skipped = errors = 0
    by_status = {}
    for it in raw:
        url = (it.get("url") or "").strip()
        if not url:
            continue
        cu = canonical_url(url)
        existing = await db.press.find_one({"canonical_url": cu}) or await db.press.find_one({"url": url})
        if existing and existing.get("status") in CURATED:
            skipped += 1
            continue
        status_code, reachable = await loop.run_in_executor(None, _reach_sync, url)
        text = f"{it.get('title', '')} {it.get('summary', '')}"
        low = text.lower()
        mentions = "unoxdue" in low or "uno x due" in low or "1x2" in low
        linked = await _associate(text)
        conf = it.get("confidence")
        try:
            conf = float(conf) if conf is not None else None
        except (TypeError, ValueError):
            conf = None
        status = _decide_status(reachable, conf, mentions, linked)
        if status == "error":
            errors += 1
        doc = {
            "id": existing["id"] if existing else str(uuid.uuid4()),
            "source": it.get("source", ""), "title": it.get("title", ""),
            "url": url, "canonical_url": cu, "date": it.get("date", ""),
            "summary": it.get("summary", ""),  # sintesi originale (no testo integrale)
            "linked": linked, "query": query, "provider": provider.name,
            "detected_at": existing.get("detected_at") if existing else _now(),
            "updated_at": _now(), "reachable": reachable, "http_status": status_code,
            "confidence": conf, "status": status,
        }
        await db.press.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
        by_status[status] = by_status.get(status, 0) + 1
        if existing:
            updated += 1
        else:
            found += 1
    summary = {"ok": True, "provider": provider.name, "demo": provider.name == "fixture",
               "found": found, "updated": updated, "skipped": skipped, "errors": errors,
               "by_status": by_status, "query": query}
    await auto.log_automation("press", "ok",
                              f"Rassegna stampa: {found} nuovi, {updated} aggiornati, {skipped} curati saltati",
                              summary)
    return summary


async def set_status(item_id: str, status: str, actor: str = "admin") -> dict:
    if status not in ALLOWED_STATUS:
        return {"ok": False, "error": f"Stato non valido: {status}"}
    doc = await db.press.find_one({"id": item_id})
    if not doc:
        return {"ok": False, "error": "Articolo non trovato"}
    prev = doc.get("status")
    await db.press.update_one({"id": item_id},
                              {"$set": {"status": status, "status_updated_at": _now(), "status_by": actor}})
    await auto.log_automation("press", "info",
                              f"Stato rassegna -> {status} ({(doc.get('title') or '')[:50]})",
                              {"id": item_id, "prev": prev, "new": status})
    return {"ok": True, "prev": prev, "status": status}


async def set_link(item_id: str, ltype: str, slug: str, title: str) -> dict:
    doc = await db.press.find_one({"id": item_id})
    if not doc:
        return {"ok": False, "error": "Articolo non trovato"}
    linked = {"type": ltype, "slug": slug, "title": title} if ltype else None
    await db.press.update_one({"id": item_id}, {"$set": {"linked": linked, "updated_at": _now()}})
    return {"ok": True, "linked": linked}


async def list_all(status: str = None, limit: int = 100) -> dict:
    q = {} if not status else {"status": status}
    items = await db.press.find(q, {"_id": 0}).sort("detected_at", -1).to_list(limit)
    counts = {}
    for it in await db.press.find({}, {"_id": 0, "status": 1}).to_list(3000):
        s = it.get("status") or "found"
        counts[s] = counts.get(s, 0) + 1
    return {"items": items, "counts": counts}
