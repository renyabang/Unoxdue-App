"""Step 7B — Rassegna stampa: ricerca web astratta + provider-agnostica.

Regole di generazione query, finestre temporali, esclusioni e pertinenza implementate
ALLA LETTERA secondo le specifiche dell'utente (configurazione modificabile dall'admin).

- PressProvider: interfaccia astratta `search(query, date_filter)`.
- FixturePressProvider: dataset deterministico (demo).
- PerplexityPressProvider: ricerca reale (Sonar `chat/completions`) con domain denylist,
  filtri data (recency/after) e structured output JSON. Attivo SOLO con PERPLEXITY_API_KEY.
- Modello dati: testata, titolo, url, canonical_url, data, sintesi originale (NO testo integrale),
  contenuto UnoXdue collegato, query, data di rilevamento, stato, confidence.
- Dedup per URL canonica + titolo (copie/syndication), verifica raggiungibilità, associazione,
  regola di pertinenza (false positive se manca il collegamento al podcast), NESSUNA pubblicazione automatica.
"""
import re
import json
import uuid
import calendar
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta

from urllib.parse import urlparse, urlunparse

import requests

from config_db import db, SITE_URL, PERPLEXITY_API_KEY
import automations as auto

ALLOWED_STATUS = {"found", "verified", "review", "published", "discarded", "error"}
CURATED = {"published", "discarded", "verified"}  # non sovrascritti dal re-run
LOW_CONF = 0.6
SECTION = {"episode": "episodi", "interview": "interviste", "team": "team"}
LINK_LABEL = {"episode": "Episodio collegato", "interview": "Intervista collegata",
              "team": "Membro del team collegato"}
BRAND_TERMS = ["unoxdue", "uno x due", "uno per due"]

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"

# ----------------------- Configurazione (admin-modificabile) -----------------------
DEFAULT_CONFIG = {
    "default_query": '"UnoXdue" podcast',
    "brand_queries": [
        '"UnoXdue" podcast',
        '"UnoXdue" Serie A',
        '"UnoXdue" intervista',
        '"UnoXdue" calcio',
        '"UnoXdue" pronostici',
    ],
    "team_members": ["Sono Micuccio", "Il Ninja", "Il Marziano", "Antonello Santopaolo"],
    "excluded_domains": ["unoxdue.net", "youtube.com", "twitch.tv", "instagram.com", "tiktok.com"],
    "model": "sonar",
    "max_results_per_run": 10,
    "max_queries_per_run": 14,
    "recent_content_limit": 4,
    "auto_publish": False,
    "historical_backfill_done": False,
    # tariffe per stima costo (USD per 1M token + costo/richiesta). Modificabili dall'admin.
    "cost_rates": {
        "sonar": {"in": 1.0, "out": 1.0, "req": 0.005},
        "sonar-pro": {"in": 3.0, "out": 15.0, "req": 0.005},
    },
}


async def get_config() -> dict:
    doc = await db.press_config.find_one({"_id": "press"}) or {}
    cfg = dict(DEFAULT_CONFIG)
    for k, v in doc.items():
        if k == "_id":
            continue
        cfg[k] = v
    return cfg


async def set_config(patch: dict) -> dict:
    clean = {k: v for k, v in (patch or {}).items() if k in DEFAULT_CONFIG}
    if clean:
        await db.press_config.update_one({"_id": "press"}, {"$set": clean}, upsert=True)
    return await get_config()


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


def _norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", (t or "").lower())).strip()


def _clean_title_for_query(t: str) -> str:
    """Rimuove emoji/hashtag e rumore da un titolo per usarlo come frase di ricerca."""
    t = re.sub(r"#\w+", "", t or "")
    t = re.sub(r"[^\w\sàèéìòùÀÈÉÌÒÙ'\-]", "", t)  # via emoji e simboli
    t = re.sub(r"\bEP\.?\s*\d+\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:90]


def _domain_of(u: str) -> str:
    try:
        h = urlparse(u).netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def _pub_name(u: str) -> str:
    """Nome testata leggibile derivato dal dominio (es. calabria7.news -> Calabria7.news)."""
    d = _domain_of(u)
    return d.split(".")[0].capitalize() + ("." + ".".join(d.split(".")[1:]) if "." in d else "") if d else u


# ----------------------- finestre temporali -----------------------
def _months_ago(n: int):
    d = datetime.now(timezone.utc).date()
    idx = d.month - 1 - n
    y = d.year + idx // 12
    m = idx % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return datetime(y, m, day)


def date_filter_for(mode: str) -> dict:
    """ordinary=30gg (recency 'month'); weekly=90gg (after); backfill=24 mesi calendario (after)."""
    if mode == "weekly":
        after = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%m/%d/%Y")
        return {"search_after_date_filter": after}
    if mode == "backfill":
        after = _months_ago(24).strftime("%m/%d/%Y")
        return {"search_after_date_filter": after}
    return {"search_recency_filter": "month"}


WINDOW_LABEL = {"ordinary": "ultimi 30 giorni", "weekly": "ultimi 90 giorni",
                "backfill": "ultimi 24 mesi (calendario)"}


# ----------------------- generazione query -----------------------
async def _guest_names() -> list:
    names, seen = [], set()
    eps = await db.episodes.find({"type": "intervista"},
                                 {"_id": 0, "guest_name": 1}).sort("published_at", -1).to_list(500)
    for e in eps:
        gn = (e.get("guest_name") or "").strip()
        if gn and len(gn) > 2 and gn.lower() not in seen:
            seen.add(gn.lower())
            names.append(gn)
    return names


async def _recent_contents(limit: int) -> list:
    eps = await db.episodes.find({}, {"_id": 0, "title": 1, "guest_name": 1, "type": 1}).sort(
        "published_at", -1).to_list(limit)
    return eps


async def build_queries(cfg: dict, mode: str = "ordinary") -> list:
    """Costruisce l'insieme di query secondo le regole (brand, team, ospiti, contenuti recenti)."""
    out = []

    def add(q, kind):
        q = q.strip()
        if q and not any(x["q"] == q for x in out):
            out.append({"q": q, "kind": kind})

    # Brand
    for q in cfg.get("brand_queries", []):
        add(q, "brand")
    # Membri del team (mai cercati da soli)
    for name in cfg.get("team_members", []):
        add(f'"{name}" "UnoXdue"', "team")
    # Ospiti dinamici
    for g in await _guest_names():
        add(f'"{g}" "UnoXdue"', "guest")
        add(f'"{g}" intervista "UnoXdue"', "guest")
    # Contenuti recenti (NON tutto l'archivio)
    for c in await _recent_contents(cfg.get("recent_content_limit", 4)):
        ct = _clean_title_for_query(c.get("title", ""))
        if len(ct) >= 12:
            add(f'"{ct}" "UnoXdue"', "recent")
    return out


# ----------------------- Provider -----------------------
class PressProvider(ABC):
    name = "base"

    @abstractmethod
    async def search(self, query: str, date_filter: dict = None) -> dict:
        ...


class FixturePressProvider(PressProvider):
    """Dataset demo deterministico (menzioni UnoXdue + membri team + un URL non raggiungibile)."""
    name = "fixture"

    RESULTS = [
        {"source": "La Gazzetta dello Sport",
         "title": "UnoXdue, il podcast Serie A di Sono Micuccio conquista il pubblico",
         "url": "https://www.gazzetta.it/", "date": "2026-05-20",
         "summary": "Il podcast UnoXdue cresce negli ascolti grazie alle analisi di Sono Micuccio.",
         "confidence": 0.9},
        {"source": "Tuttomercatoweb",
         "title": "L'ospite di UnoXdue parla di calciomercato: le dichiarazioni",
         "url": "https://www.tuttomercatoweb.com/", "date": "2026-05-18",
         "summary": "Nell'ultima puntata di UnoXdue l'ospite ha commentato il mercato di Serie A.",
         "confidence": 0.78},
        {"source": "Corriere dello Sport",
         "title": "Il Ninja e Il Marziano analizzano la giornata su UnoXdue",
         "url": "https://www.corrieredellosport.it/", "date": "2026-05-15",
         "summary": "I tipster Il Ninja e Il Marziano di UnoXdue discutono i pronostici della giornata.",
         "confidence": 0.82},
        {"source": "Blog demo",
         "title": "Pronostici della settimana",
         "url": "https://nonexistent-uxd-demo.invalid/articolo", "date": "2026-05-10",
         "summary": "Articolo senza menzione diretta del podcast.", "confidence": 0.3},
    ]

    async def search(self, query: str, date_filter: dict = None) -> dict:
        return {"results": [dict(r) for r in self.RESULTS], "usage": {}}


class PerplexityPressProvider(PressProvider):
    """Ricerca reale Perplexity Sonar. Usa `search_results` (URL realmente trovati) + domain denylist + filtri data."""
    name = "perplexity"

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.model = cfg.get("model", "sonar")
        self.excluded = cfg.get("excluded_domains", [])

    async def search(self, query: str, date_filter: dict = None) -> dict:
        def _call():
            prompt = (
                "Sei un assistente di rassegna stampa per il podcast italiano di Serie A 'UnoXdue'. "
                f"Trova articoli di testate giornalistiche/siti di informazione online che parlano di: {query}. "
                "Elenca solo articoli con testata, titolo e URL. Escludi social network e duplicati."
            )
            body = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
            if self.excluded:
                body["search_domain_filter"] = [f"-{d}" for d in self.excluded][:20]
            if date_filter:
                body.update(date_filter)
            return requests.post(
                PERPLEXITY_URL,
                headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                         "Content-Type": "application/json"},
                json=body, timeout=45)

        loop = asyncio.get_event_loop()
        r = await loop.run_in_executor(None, _call)
        r.raise_for_status()
        data = r.json()
        out = []
        for s in (data.get("search_results") or []):
            url = (s.get("url") or "").strip()
            if not url:
                continue
            out.append({
                "source": _pub_name(url),
                "title": s.get("title", ""),
                "url": url,
                "date": s.get("date") or "",
                "summary": (s.get("snippet") or "")[:240],
                "confidence": None,  # calcolata dalla pipeline in base ai segnali di pertinenza
            })
        return {"results": out, "usage": data.get("usage", {}) or {}}


async def get_provider(cfg: dict = None) -> PressProvider:
    cfg = cfg or await get_config()
    if PERPLEXITY_API_KEY:
        return PerplexityPressProvider(cfg)
    return FixturePressProvider()


def provider_status() -> dict:
    active = "perplexity" if PERPLEXITY_API_KEY else "fixture"
    return {"configured": bool(PERPLEXITY_API_KEY), "provider": active, "active": active,
            "demo": active == "fixture",
            "note": ("Rassegna stampa REALE attiva (Perplexity Sonar)." if PERPLEXITY_API_KEY else
                     "Modalità fixture (demo). Inserisci PERPLEXITY_API_KEY per la ricerca reale.")}


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


# ----------------------- associazione contenuti (multipla) -----------------------
async def _associate_all(text: str):
    """Trova TUTTI i contenuti pertinenti (team, episodi, interviste) menzionati nel testo."""
    t = (text or "").lower()
    out = []
    team = await db.team.find({}, {"_id": 0, "slug": 1, "name": 1}).to_list(100)
    for m in team:
        nm = (m.get("name") or "").lower()
        if nm and len(nm) > 3 and nm in t:
            out.append({"type": "team", "slug": m.get("slug"), "title": m.get("name"), "source": "auto"})
    eps = await db.episodes.find({}, {"_id": 0, "slug": 1, "title": 1, "type": 1, "guest_name": 1}).to_list(2000)
    for e in eps:
        gn = (e.get("guest_name") or "").lower()
        if gn and len(gn) > 3 and gn in t:
            out.append({"type": "interview" if e.get("type") == "intervista" else "episode",
                        "slug": e.get("slug"), "title": e.get("title"), "source": "auto"})
    seen, ded = set(), []
    for l in out:
        k = (l["type"], l["slug"])
        if k in seen:
            continue
        seen.add(k)
        ded.append(l)
    return ded


def _merge_links(existing_links, auto_links):
    """Mantiene i collegamenti manuali esistenti e fonde gli auto, dedup per (type, slug)."""
    manual = [l for l in (existing_links or []) if l.get("source") == "manual"]
    seen, merged = set(), []
    for l in manual + auto_links:
        k = (l.get("type"), l.get("slug"))
        if k in seen:
            continue
        seen.add(k)
        merged.append(l)
    return merged


# ----------------------- pertinenza -----------------------
def _mentions_brand(text: str) -> bool:
    low = (text or "").lower()
    return any(b in low for b in BRAND_TERMS)


async def _content_title_hit(text: str) -> bool:
    """True se l'articolo riprende il titolo di un contenuto UnoXdue."""
    low = (text or "").lower()
    eps = await db.episodes.find({}, {"_id": 0, "title": 1}).to_list(2000)
    for e in eps:
        nt = _norm_title(e.get("title", ""))
        if len(nt) >= 18 and nt in re.sub(r"[^\w\s]", "", low):
            return True
    return False


def _decide_status(reachable, relevant, confidence, linked):
    if not reachable:
        return "error"
    if not relevant:
        return "review"  # falso positivo: non associato, non pubblicabile
    c = confidence if confidence is not None else 0.5
    if c < LOW_CONF or not linked:
        return "review"
    return "found"  # nessuna pubblicazione automatica


# ----------------------- pipeline -----------------------
async def run_search(query: str = None, mode: str = "ordinary", actor: str = "admin",
                     max_queries: int = None, max_results: int = None) -> dict:
    cfg = await get_config()
    provider = await get_provider(cfg)
    max_results = max_results or cfg.get("max_results_per_run", 10)
    max_queries = max_queries or cfg.get("max_queries_per_run", 14)
    date_filter = date_filter_for(mode)

    # 1) insieme query
    if query and query.strip():
        queries = [{"q": query.strip(), "kind": "manual"}]
    else:
        queries = (await build_queries(cfg, mode))[:max_queries]
    if not queries:
        return {"ok": False, "error": "Nessuna query generata"}

    # 2) esecuzione (concorrente, con semaforo)
    sem = asyncio.Semaphore(4)
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    real_cost = 0.0
    query_errors = []

    async def _one(qm):
        async with sem:
            try:
                res = await provider.search(qm["q"], date_filter)
                return qm, res
            except Exception as e:
                query_errors.append({"q": qm["q"], "error": str(e)})
                return qm, {"results": [], "usage": {}}

    runs = await asyncio.gather(*[_one(q) for q in queries])

    raw_found = 0
    by_canonical = {}
    by_title = set()
    duplicates = 0
    domain_excluded = 0
    for qm, res in runs:
        u = res.get("usage") or {}
        for k in usage_total:
            usage_total[k] += int(u.get(k) or 0)
        real_cost += float((u.get("cost") or {}).get("total_cost") or 0)
        for it in res.get("results", []):
            raw_found += 1
            url = (it.get("url") or "").strip()
            if not url:
                continue
            dom = _domain_of(url)
            if any(dom == d or dom.endswith("." + d) for d in cfg.get("excluded_domains", [])):
                domain_excluded += 1
                continue
            cu = canonical_url(url)
            nt = _norm_title(it.get("title", ""))
            if cu in by_canonical or (nt and nt in by_title):
                duplicates += 1
                continue
            by_canonical[cu] = {"item": it, "query": qm["q"], "kind": qm["kind"]}
            if nt:
                by_title.add(nt)

    # 3) valutazione (raggiungibilità + pertinenza + associazione)
    loop = asyncio.get_event_loop()
    uniques = list(by_canonical.items())
    reach_results = await asyncio.gather(
        *[loop.run_in_executor(None, _reach_sync, cu) for cu, _ in uniques])

    candidates = []
    unreachable = false_positives = 0
    for (cu, info), (status_code, reachable) in zip(uniques, reach_results):
        it = info["item"]
        text = f"{it.get('title', '')} {it.get('summary', '')}"
        brand = _mentions_brand(text)
        title_hit = await _content_title_hit(text) if not brand else False
        relevant = brand or title_hit
        if relevant:
            reason = "cita UnoXdue" if brand else "riprende un contenuto UnoXdue"
            auto_links = await _associate_all(text)
        else:
            reason = "solo nome ospite/team senza collegamento al podcast (falso positivo)"
            auto_links = []
        conf = it.get("confidence")
        try:
            conf = float(conf) if conf is not None else None
        except (TypeError, ValueError):
            conf = None
        if conf is None:  # confidence euristica deterministica dai segnali di pertinenza
            low = text.lower()
            title_low = (it.get("title", "") or "").lower()
            if any(b in title_low for b in BRAND_TERMS):
                conf = 0.9
            elif brand:
                conf = 0.75
            elif title_hit:
                conf = 0.65
            else:
                conf = 0.35
        status = _decide_status(reachable, relevant, conf, bool(auto_links))
        if status == "error":
            unreachable += 1
        if not relevant:
            false_positives += 1
        candidates.append({
            "url": it.get("url", ""), "canonical_url": cu, "source": it.get("source", ""),
            "title": it.get("title", ""), "date": it.get("date", ""),
            "summary": it.get("summary", ""), "links": auto_links, "confidence": conf,
            "reachable": reachable, "http_status": status_code, "status": status,
            "relevant": relevant, "reason": reason, "query": info["query"], "kind": info["kind"],
        })

    # 4) cap risultati salvati (priorità: found > review > error)
    order = {"found": 0, "review": 1, "error": 2}
    candidates.sort(key=lambda c: (order.get(c["status"], 3), -(c["confidence"] or 0)))
    to_save = candidates[:max_results]

    saved_items = []
    for c in to_save:
        existing = await db.press.find_one({"canonical_url": c["canonical_url"]}) \
            or await db.press.find_one({"url": c["url"]})
        if existing and existing.get("status") in CURATED:
            continue
        links = _merge_links(existing.get("links") if existing else None, c["links"])
        doc = {
            "id": existing["id"] if existing else str(uuid.uuid4()),
            "source": c["source"], "title": c["title"], "url": c["url"],
            "canonical_url": c["canonical_url"], "date": c["date"], "summary": c["summary"],
            "links": links, "query": c["query"], "provider": provider.name,
            "detected_at": existing.get("detected_at") if existing else _now(),
            "updated_at": _now(), "reachable": c["reachable"], "http_status": c["http_status"],
            "confidence": c["confidence"], "status": c["status"], "relevant": c["relevant"],
            "status_reason": c["reason"],
        }
        await db.press.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
        saved_items.append({**c, "id": doc["id"], "links": links})

    # 5) costo (reale dalle API Perplexity; fallback stima da tariffe)
    rates = cfg.get("cost_rates", {}).get(provider_model(cfg, provider), {"in": 1.0, "out": 1.0, "req": 0.005})
    n_req = len(queries) if provider.name == "perplexity" else 0
    if real_cost > 0:
        cost = real_cost
    else:
        cost = (usage_total["prompt_tokens"] / 1e6 * rates["in"]
                + usage_total["completion_tokens"] / 1e6 * rates["out"]
                + n_req * rates["req"]) if provider.name == "perplexity" else 0.0

    valid = sum(1 for c in candidates if c["relevant"] and c["reachable"])
    stats = {
        "queries_executed": len(queries),
        "raw_found": raw_found,
        "unique_after_dedup": len(uniques),
        "duplicates_excluded": duplicates,
        "domain_excluded": domain_excluded,
        "unreachable": unreachable,
        "valid": valid,
        "false_positives": false_positives,
        "saved": len(saved_items),
        "tokens": usage_total,
        "requests": n_req,
        "cost_usd": round(cost, 5),
        "estimated_cost_usd": round(cost, 5),
        "cost_source": "reale (Perplexity)" if real_cost > 0 else "stima",
    }
    summary = {
        "ok": True, "provider": provider.name, "demo": provider.name == "fixture",
        "mode": mode, "window_label": WINDOW_LABEL.get(mode, mode),
        "queries": [q["q"] for q in queries], "query_errors": query_errors,
        "items": saved_items, "all_candidates": candidates, "stats": stats,
        "found": len(saved_items),
    }
    await auto.log_automation(
        "press", "ok",
        f"Rassegna stampa REALE ({provider.name}, {mode}): {len(queries)} query, "
        f"{len(saved_items)} salvati, {false_positives} falsi positivi, ~${stats['estimated_cost_usd']}",
        stats)
    return summary


def provider_model(cfg: dict, provider) -> str:
    return cfg.get("model", "sonar") if provider.name == "perplexity" else "fixture"


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


async def set_link(item_id: str, action: str, ltype: str, slug: str, title: str) -> dict:
    """Aggiunge o rimuove un collegamento manuale (senza eliminare l'articolo)."""
    doc = await db.press.find_one({"id": item_id})
    if not doc:
        return {"ok": False, "error": "Articolo non trovato"}
    links = list(doc.get("links") or [])
    if action == "remove":
        links = [l for l in links if not (l.get("slug") == slug and l.get("type") == ltype)]
    else:
        if not ltype or not slug:
            return {"ok": False, "error": "Tipo/slug mancanti"}
        if not any(l.get("slug") == slug and l.get("type") == ltype for l in links):
            links.append({"type": ltype, "slug": slug, "title": title, "source": "manual"})
    await db.press.update_one({"id": item_id}, {"$set": {"links": links, "updated_at": _now()}})
    await auto.log_automation("press", "info", f"Associazione {action} ({ltype}:{slug})", {"id": item_id})
    return {"ok": True, "links": links}


async def link_options() -> dict:
    """Contenuti selezionabili per l'associazione manuale (episodi/interviste/team)."""
    opts = []
    eps = await db.episodes.find({}, {"_id": 0, "slug": 1, "title": 1, "type": 1}).sort("published_at", -1).to_list(500)
    for e in eps:
        opts.append({"type": "interview" if e.get("type") == "intervista" else "episode",
                     "slug": e.get("slug"), "title": e.get("title")})
    team = await db.team.find({}, {"_id": 0, "slug": 1, "name": 1}).to_list(100)
    for m in team:
        opts.append({"type": "team", "slug": m.get("slug"), "title": m.get("name")})
    return {"options": opts}


async def published_for(slug: str):
    """Articoli pubblicati + raggiungibili collegati a uno specifico contenuto (dedup per URL canonica, recenti)."""
    items = await db.press.find(
        {"status": "published", "reachable": True, "links.slug": slug}, {"_id": 0}).to_list(50)
    seen, out = set(), []
    for it in sorted(items, key=lambda x: (x.get("date") or ""), reverse=True):
        cu = it.get("canonical_url") or it.get("url")
        if cu in seen:
            continue
        seen.add(cu)
        out.append({"source": it.get("source"), "title": it.get("title"), "date": it.get("date"),
                    "summary": it.get("summary"), "url": it.get("url")})
    return out


async def published_archive():
    """Tutti gli articoli pubblicati per la pagina 'Parlano di noi', con link interni puliti (dedup)."""
    items = await db.press.find({"status": "published"}, {"_id": 0}).sort("date", -1).to_list(200)
    seen, out = set(), []
    for it in items:
        cu = it.get("canonical_url") or it.get("url")
        if cu in seen:
            continue
        seen.add(cu)
        internals = []
        for l in (it.get("links") or []):
            sec = SECTION.get(l.get("type"))
            if sec and l.get("slug"):
                internals.append({"url": f"{SITE_URL}/{sec}/{l['slug']}/",
                                  "label": LINK_LABEL.get(l.get("type"), "Collegato"),
                                  "title": l.get("title")})
        out.append({"source": it.get("source"), "title": it.get("title"), "date": it.get("date"),
                    "summary": it.get("summary"), "url": it.get("url"), "internals": internals})
    return out


async def list_all(status: str = None, limit: int = 100) -> dict:
    q = {} if not status else {"status": status}
    items = await db.press.find(q, {"_id": 0}).sort("detected_at", -1).to_list(limit)
    counts = {}
    for it in await db.press.find({}, {"_id": 0, "status": 1}).to_list(3000):
        s = it.get("status") or "found"
        counts[s] = counts.get(s, 0) + 1
    return {"items": items, "counts": counts}
