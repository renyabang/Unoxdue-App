"""Step 7B — Rassegna stampa: ricerca web astratta + provider-agnostica.

Regole di generazione query, finestre temporali, esclusioni e pertinenza implementate
ALLA LETTERA secondo le specifiche dell'utente (configurazione modificabile dall'admin).

Pipeline a categorie ESCLUSIVE:
  grezzi -> (duplicati) -> (social esclusi) -> (pagine non-articolo) -> (irraggiungibili)
  -> reachable: falsi positivi | validi -> validi salvati in revisione (cap).
I falsi positivi / non-articolo / irraggiungibili NON entrano nell'editoriale: vanno nel log tecnico `press_rejected`.
Auto-associazione solo con menzione esplicita UnoXdue + corrispondenza DB ANCORATA AL TITOLO + confidence >= soglia.
NESSUNA pubblicazione automatica. Storico esecuzioni in `press_runs` (riepilogo admin).
"""
import re
import uuid
import html
import calendar
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urlunparse

import requests

from config_db import db, SITE_URL, PERPLEXITY_API_KEY
import automations as auto
import press_logos as pl

ALLOWED_STATUS = {"found", "verified", "review", "published", "discarded", "error"}
CURATED = {"published", "discarded", "verified"}  # non sovrascritti dal re-run
SECTION = {"episode": "episodi", "interview": "interviste", "team": "team"}
LINK_LABEL = {"episode": "Episodio collegato", "interview": "Intervista collegata",
              "team": "Membro del team collegato"}
BRAND_TERMS = ["unoxdue", "uno x due"]
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
# parole di taccuino/tassonomia che identificano pagine NON-articolo
TAXONOMY = ["/tag/", "/tags/", "/category/", "/categoria/", "/categorie/", "/argomenti/", "/argomento/",
            "/topics/", "/topic/", "/search/", "/cerca/", "/ricerca/", "/archivio/", "/archive/",
            "/sezione/", "/sezioni/", "/author/", "/autore/", "/page/", "/pagina/", "/feed/", "/rss/", "/amp/"]

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
    # social + dominio proprio esclusi (Facebook incluso)
    "excluded_domains": ["unoxdue.net", "facebook.com", "youtube.com", "twitch.tv",
                         "instagram.com", "tiktok.com", "x.com", "twitter.com"],
    "model": "sonar",
    "max_results_per_run": 10,
    "max_queries_per_run": 14,
    "recent_content_limit": 4,
    "auto_link_min_confidence": 0.85,
    "auto_publish": False,
    "historical_backfill_done": False,
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
    t = re.sub(r"#\w+", "", t or "")
    t = re.sub(r"[^\w\sàèéìòùÀÈÉÌÒÙ'\-]", "", t)
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
    d = _domain_of(u)
    return d.split(".")[0].capitalize() + ("." + ".".join(d.split(".")[1:]) if "." in d else "") if d else u


def _is_excluded_domain(url: str, excluded: list) -> bool:
    dom = _domain_of(url)
    return any(dom == d or dom.endswith("." + d) for d in excluded)


def _is_non_article(url: str):
    """Riconosce homepage, pagine tassonomia (tag/categoria/archivio/ricerca) e sezioni generiche."""
    try:
        p = urlparse(url)
    except Exception:
        return True, "url non valido"
    path = (p.path or "/")
    low = (path + "/").lower()
    segs = [s for s in path.split("/") if s]
    if not segs:
        return True, "homepage"
    if any(t in low for t in TAXONOMY):
        return True, "pagina tassonomia (tag/categoria/archivio/ricerca)"
    last = segs[-1]
    words = [w for w in re.split(r"[-_]", last) if w]
    if len(segs) <= 2 and len(words) <= 3 and not any(c.isdigit() for c in last):
        return True, "sezione/categoria generica"
    return False, None


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
    return await db.episodes.find({}, {"_id": 0, "title": 1, "guest_name": 1, "type": 1}).sort(
        "published_at", -1).to_list(limit)


async def build_queries(cfg: dict, mode: str = "ordinary") -> list:
    out = []

    def add(q, kind):
        q = q.strip()
        if q and not any(x["q"] == q for x in out):
            out.append({"q": q, "kind": kind})

    for q in cfg.get("brand_queries", []):
        add(q, "brand")
    for name in cfg.get("team_members", []):
        add(f'"{name}" "UnoXdue"', "team")
    for g in await _guest_names():
        add(f'"{g}" "UnoXdue"', "guest")
        add(f'"{g}" intervista "UnoXdue"', "guest")
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
    name = "fixture"
    RESULTS = [
        {"source": "La Gazzetta dello Sport",
         "title": "UnoXdue, il podcast Serie A di Sono Micuccio conquista il pubblico",
         "url": "https://www.gazzetta.it/calcio/podcast/unoxdue-sono-micuccio-12345", "date": "2026-05-20",
         "summary": "Il podcast UnoXdue cresce negli ascolti grazie alle analisi di Sono Micuccio.",
         "confidence": 0.9},
        {"source": "Tuttomercatoweb",
         "title": "L'ospite di UnoXdue parla di calciomercato",
         "url": "https://www.tuttomercatoweb.com/serie-a/unoxdue-ospite-mercato-67890", "date": "2026-05-18",
         "summary": "Nell'ultima puntata di UnoXdue l'ospite ha commentato il mercato di Serie A.",
         "confidence": 0.78},
    ]

    async def search(self, query: str, date_filter: dict = None) -> dict:
        return {"results": [dict(r) for r in self.RESULTS], "usage": {}}


class PerplexityPressProvider(PressProvider):
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
            body = {"model": self.model,
                    "messages": [{"role": "user", "content": prompt}], "stream": False}
            if self.excluded:
                body["search_domain_filter"] = [f"-{d}" for d in self.excluded][:20]
            if date_filter:
                body.update(date_filter)
            return requests.post(
                PERPLEXITY_URL,
                headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"},
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
            out.append({"source": _pub_name(url), "title": s.get("title", ""), "url": url,
                        "date": s.get("date") or "", "summary": (s.get("snippet") or "")[:240],
                        "confidence": None})
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


# ----------------------- fetch pagina (raggiungibilità + testo per pertinenza) -----------------------
def _fetch_sync(url: str):
    """GET unico: ritorna (status_code, reachable, page_text_lower).
    403/405/429 (blocco bot) = raggiungibile (ma senza testo). 404/410/5xx/errore = no."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
               "Accept-Language": "it-IT,it;q=0.9"}
    try:
        r = requests.get(url, timeout=9, allow_redirects=True, headers=headers, stream=False)
        code = r.status_code
        reachable = code < 500 and code not in (404, 410)
        text = ""
        if code < 400:
            ct = (r.headers.get("Content-Type") or "").lower()
            if "html" in ct or "text" in ct or not ct:
                body = r.text[:400000]
                body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.DOTALL | re.I)
                body = re.sub(r"<[^>]+>", " ", body)
                text = re.sub(r"\s+", " ", html.unescape(body)).lower()[:40000]
        return code, reachable, text
    except Exception:
        return None, False, ""


# ----------------------- associazione + pertinenza -----------------------
def _mentions_brand(text: str) -> bool:
    low = (text or "").lower()
    return any(b in low for b in BRAND_TERMS)


def _associate_rich(title_low: str, text_low: str, team: list, eps: list) -> list:
    """Collegamenti DB trovati nel testo, con flag in_title (ancoraggio al titolo)."""
    links = []
    for m in team:
        nm = (m.get("name") or "").lower()
        if nm and len(nm) > 3 and nm in text_low:
            links.append({"type": "team", "slug": m.get("slug"), "title": m.get("name"),
                          "source": "auto", "in_title": nm in title_low})
    for e in eps:
        gn = (e.get("guest_name") or "").lower()
        if gn and len(gn) > 3 and gn in text_low:
            toks = [t for t in re.split(r"\s+", gn) if len(t) >= 5]
            in_t = any(t in title_low for t in toks)
            links.append({"type": "interview" if e.get("type") == "intervista" else "episode",
                          "slug": e.get("slug"), "title": e.get("title"),
                          "source": "auto", "in_title": in_t})
    seen, ded = set(), []
    for l in links:
        k = (l["type"], l["slug"])
        if k in seen:
            continue
        seen.add(k)
        ded.append(l)
    return ded


def _content_title_hit(title_low: str, eps: list) -> bool:
    cleaned = re.sub(r"[^\w\s]", "", title_low)
    for e in eps:
        nt = _norm_title(e.get("title", ""))
        if len(nt) >= 18 and nt in cleaned:
            return True
    return False


def _assess(title: str, summary: str, page_text: str, team: list, eps: list, min_conf: float) -> dict:
    title_low = (title or "").lower()
    body_low = f"{title or ''} {summary or ''} {page_text or ''}".lower()
    brand_in_title = _mentions_brand(title_low)
    brand_in_body = _mentions_brand(body_low)
    brand = brand_in_title or brand_in_body
    links = _associate_rich(title_low, body_low, team, eps)
    has_match = bool(links)
    has_title_anchor = any(l["in_title"] for l in links)
    tch = _content_title_hit(title_low, eps)
    relevant = brand or tch
    if not relevant:
        return {"relevant": False, "confidence": 0.3, "links": [], "suggested": [],
                "reason": "falso positivo: nessuna menzione esplicita di UnoXdue né corrispondenza con i contenuti"}
    if tch and has_title_anchor:
        conf = 0.92
    elif tch:
        conf = 0.9
    elif brand_in_title and has_title_anchor:
        conf = 0.92
    elif (brand_in_title and has_match) or (has_title_anchor and brand):
        conf = 0.88
    elif brand and has_match:
        conf = 0.78
    else:
        conf = 0.6
    auto_ok = brand and conf >= min_conf and (has_title_anchor or tch)
    if auto_ok:
        auto_links = [l for l in links if l["in_title"]] or links
        suggested = [l for l in links if l not in auto_links]
        reason = "cita UnoXdue + corrispondenza DB ancorata al titolo"
    else:
        auto_links = []
        suggested = links
        reason = ("cita UnoXdue; associazione da confermare manualmente"
                  if has_match else "cita UnoXdue; nessun contenuto DB corrispondente")
    return {"relevant": True, "confidence": conf, "links": auto_links,
            "suggested": suggested, "reason": reason}


# ----------------------- pipeline -----------------------
async def run_search(query: str = None, mode: str = "ordinary", actor: str = "admin",
                     trigger: str = "manual", max_queries: int = None, max_results: int = None) -> dict:
    cfg = await get_config()
    provider = await get_provider(cfg)
    excluded = cfg.get("excluded_domains", [])
    min_conf = float(cfg.get("auto_link_min_confidence", 0.85))
    max_results = max_results or cfg.get("max_results_per_run", 10)
    max_queries = max_queries or cfg.get("max_queries_per_run", 14)
    date_filter = date_filter_for(mode)

    if query and query.strip():
        queries = [{"q": query.strip(), "kind": "manual"}]
    else:
        queries = (await build_queries(cfg, mode))[:max_queries]
    if not queries:
        return {"ok": False, "error": "Nessuna query generata"}

    # esecuzione concorrente
    sem = asyncio.Semaphore(4)
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    real_cost = 0.0
    query_errors = []

    async def _one(qm):
        async with sem:
            try:
                return qm, await provider.search(qm["q"], date_filter)
            except Exception as e:
                query_errors.append({"q": qm["q"], "error": str(e)})
                return qm, {"results": [], "usage": {}}

    runs = await asyncio.gather(*[_one(q) for q in queries])

    # dedup (URL canonica + titolo) + esclusione social
    raw_found = duplicates = social_excluded = 0
    by_canonical, by_title = {}, set()
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
            if _is_excluded_domain(url, excluded):
                social_excluded += 1
                continue
            cu = canonical_url(url)
            nt = _norm_title(it.get("title", ""))
            if cu in by_canonical or (nt and nt in by_title):
                duplicates += 1
                continue
            by_canonical[cu] = {"item": it, "query": qm["q"], "kind": qm["kind"]}
            if nt:
                by_title.add(nt)

    # filtro pagine non-articolo (prima della rete)
    candidates, non_article = [], 0
    rejected = []  # log tecnico
    for cu, info in by_canonical.items():
        it = info["item"]
        is_na, na_reason = _is_non_article(it.get("url", ""))
        if is_na:
            non_article += 1
            rejected.append({"item": it, "query": info["query"], "category": "non_article",
                             "reason": na_reason, "reachable": None, "http_status": None, "confidence": None})
            continue
        candidates.append((cu, info))

    # raggiungibilità + testo pagina (un solo GET per candidato)
    loop = asyncio.get_event_loop()
    fetched = await asyncio.gather(*[loop.run_in_executor(None, _fetch_sync, cu) for cu, _ in candidates])

    # dati DB per associazione (una sola volta)
    team = await db.team.find({}, {"_id": 0, "slug": 1, "name": 1}).to_list(100)
    eps = await db.episodes.find({}, {"_id": 0, "slug": 1, "title": 1, "type": 1, "guest_name": 1}).to_list(3000)

    valids, unreachable, false_positives = [], 0, 0
    for (cu, info), (code, reachable, page_text) in zip(candidates, fetched):
        it = info["item"]
        if not reachable:
            unreachable += 1
            rejected.append({"item": it, "query": info["query"], "category": "unreachable",
                             "reason": f"URL irraggiungibile (HTTP {code})", "reachable": False,
                             "http_status": code, "confidence": None})
            continue
        a = _assess(it.get("title", ""), it.get("summary", ""), page_text, team, eps, min_conf)
        if not a["relevant"]:
            false_positives += 1
            rejected.append({"item": it, "query": info["query"], "category": "false_positive",
                             "reason": a["reason"], "reachable": True, "http_status": code,
                             "confidence": a["confidence"]})
            continue
        valids.append({
            "url": it.get("url", ""), "canonical_url": cu, "source": it.get("source", ""),
            "title": it.get("title", ""), "date": it.get("date", ""), "summary": it.get("summary", ""),
            "links": a["links"], "suggested": a["suggested"], "confidence": a["confidence"],
            "reachable": True, "http_status": code,
            "status": "found" if a["links"] else "review",
            "relevant": True, "reason": a["reason"], "query": info["query"], "kind": info["kind"],
        })

    # cap: validi salvati in revisione (priorità found > review, confidence desc)
    order = {"found": 0, "review": 1}
    valids.sort(key=lambda c: (order.get(c["status"], 2), -(c["confidence"] or 0)))
    to_save = valids[:max_results]

    # salva log tecnico rejected (upsert per URL canonica)
    for r in rejected:
        it = r["item"]
        cu = canonical_url(it.get("url", ""))
        await db.press_rejected.update_one({"canonical_url": cu}, {"$set": {
            "id": str(uuid.uuid4()), "canonical_url": cu, "url": it.get("url", ""),
            "source": it.get("source", "") or _pub_name(it.get("url", "")), "title": it.get("title", ""),
            "date": it.get("date", ""), "summary": it.get("summary", ""), "query": r["query"],
            "category": r["category"], "reason": r["reason"], "reachable": r["reachable"],
            "http_status": r["http_status"], "confidence": r["confidence"], "detected_at": _now(),
        }}, upsert=True)

    # salva editoriale (solo validi)
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
            "links": links, "suggested": c["suggested"], "query": c["query"], "provider": provider.name,
            "detected_at": existing.get("detected_at") if existing else _now(),
            "updated_at": _now(), "reachable": c["reachable"], "http_status": c["http_status"],
            "confidence": c["confidence"], "status": c["status"], "relevant": True,
            "status_reason": c["reason"],
        }
        await db.press.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
        saved_items.append({**c, "id": doc["id"], "links": links})

    # costo
    cost = real_cost if real_cost > 0 else 0.0

    # verifica funnel esclusivo: unici = social + non_article + unreachable + false_pos + valid
    uniques = len(by_canonical)
    stats = {
        "queries_executed": len(queries),
        "raw_found": raw_found,
        "duplicates": duplicates,
        "unique": uniques,
        "social_excluded": social_excluded,
        "non_article_excluded": non_article,
        "unreachable": unreachable,
        "false_positives": false_positives,
        "valid": len(valids),
        "saved_in_review": len(saved_items),
        "tokens": usage_total,
        "requests": len(queries) if provider.name == "perplexity" else 0,
        "cost_usd": round(cost, 5),
        "cost_source": "reale (Perplexity)" if real_cost > 0 else "n/d",
        "funnel_balanced": (social_excluded + non_article + unreachable + false_positives + len(valids)) == uniques,
    }
    summary = {
        "ok": True, "provider": provider.name, "demo": provider.name == "fixture",
        "mode": mode, "trigger": trigger, "window_label": WINDOW_LABEL.get(mode, mode),
        "queries": [q["q"] for q in queries], "query_errors": query_errors,
        "items": saved_items, "stats": stats,
    }
    await _record_run(summary)
    await auto.log_automation(
        "press", "ok",
        f"Rassegna {provider.name}/{mode}/{trigger}: {len(queries)} query, {len(saved_items)} salvati, "
        f"{false_positives} FP, {non_article} non-articolo, {unreachable} irragg., ~${stats['cost_usd']}",
        stats)
    return summary


def _merge_links(existing_links, auto_links):
    manual = [l for l in (existing_links or []) if l.get("source") == "manual"]
    seen, merged = set(), []
    for l in manual + auto_links:
        k = (l.get("type"), l.get("slug"))
        if k in seen:
            continue
        seen.add(k)
        merged.append(l)
    return merged


async def _record_run(summary: dict):
    await db.press_runs.insert_one({
        "id": str(uuid.uuid4()), "at": _now(), "mode": summary.get("mode"),
        "trigger": summary.get("trigger"), "window_label": summary.get("window_label"),
        "queries_count": len(summary.get("queries", [])), "errors": summary.get("query_errors", []),
        "stats": summary.get("stats", {}),
    })


# ----------------------- gestione editoriale -----------------------
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
    doc = await db.press.find_one({"id": item_id})
    if not doc:
        return {"ok": False, "error": "Articolo non trovato"}
    links = list(doc.get("links") or [])
    suggested = list(doc.get("suggested") or [])
    if action == "remove":
        links = [l for l in links if not (l.get("slug") == slug and l.get("type") == ltype)]
    else:
        if not ltype or not slug:
            return {"ok": False, "error": "Tipo/slug mancanti"}
        if not any(l.get("slug") == slug and l.get("type") == ltype for l in links):
            links.append({"type": ltype, "slug": slug, "title": title, "source": "manual"})
        suggested = [s for s in suggested if not (s.get("slug") == slug and s.get("type") == ltype)]
    await db.press.update_one({"id": item_id},
                              {"$set": {"links": links, "suggested": suggested, "updated_at": _now()}})
    await auto.log_automation("press", "info", f"Associazione {action} ({ltype}:{slug})", {"id": item_id})
    return {"ok": True, "links": links, "suggested": suggested}


async def link_options() -> dict:
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
    items = await db.press.find(
        {"status": "published", "reachable": True, "links.slug": slug}, {"_id": 0}).to_list(50)
    seen, out = set(), []
    for it in sorted(items, key=lambda x: (x.get("date") or ""), reverse=True):
        cu = it.get("canonical_url") or it.get("url")
        if cu in seen:
            continue
        seen.add(cu)
        lg = pl.public_logo(it)
        out.append({"source": it.get("source"), "title": it.get("title"), "date": it.get("date"),
                    "summary": it.get("summary"), "url": it.get("url"),
                    "logo": lg["url"], "initials": lg["initials"]})
    return out


async def published_archive():
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
                    "summary": it.get("summary"), "url": it.get("url"), "internals": internals,
                    "logo": pl.public_logo(it)["url"], "initials": pl.public_logo(it)["initials"]})
    return out


async def list_all(status: str = None, limit: int = 100) -> dict:
    q = {} if not status else {"status": status}
    items = await db.press.find(q, {"_id": 0}).sort("detected_at", -1).to_list(limit)
    counts = {}
    for it in await db.press.find({}, {"_id": 0, "status": 1}).to_list(3000):
        s = it.get("status") or "found"
        counts[s] = counts.get(s, 0) + 1
    return {"items": items, "counts": counts}


async def list_rejected(category: str = None, limit: int = 200) -> dict:
    q = {} if not category else {"category": category}
    items = await db.press_rejected.find(q, {"_id": 0}).sort("detected_at", -1).to_list(limit)
    counts = {}
    for it in await db.press_rejected.find({}, {"_id": 0, "category": 1}).to_list(5000):
        c = it.get("category") or "other"
        counts[c] = counts.get(c, 0) + 1
    return {"items": items, "counts": counts}


async def list_runs(limit: int = 20) -> dict:
    items = await db.press_runs.find({}, {"_id": 0}).sort("at", -1).to_list(limit)
    return {"runs": items}
