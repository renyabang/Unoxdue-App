"""Estrazione automatica del logo della testata per la rassegna stampa "Parlano di noi".

Gerarchia (ordine stretto richiesto dall'utente):
  1. logo editore/publisher nel JSON-LD (Organization/NewsMediaOrganization.logo / publisher.logo)
  2. logo dichiarato nei metadata (og:logo, itemprop=logo, link rel=image_src, msapplication-TileImage)
  3. apple-touch-icon
  4. favicon (link rel icon / shortcut icon)  e, in ultima istanza, /favicon.ico
  5. logo caricato manualmente (gestito a parte)
  6. fallback grafico con iniziali della testata/dominio

NON si usano mai: immagine principale dell'articolo, foto autore, thumbnail social, screenshot,
loghi di servizi terzi non legati alla testata. Si scarica e si salva una copia LOCALE ottimizzata
(WebP) — niente hotlink permanente. Ogni logo salva metadati completi (dominio, fonte, metodo, data,
mime, dimensioni originali/ottimizzate, hash, stato HTTP, errore, stato di revisione).
"""
import io
import json
import re
import hashlib
import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin

import requests
from PIL import Image

from config_db import db, SITE_URL, ROOT_DIR

LOGO_DIR = ROOT_DIR / "static" / "press_logos"
LOGO_DIR.mkdir(parents=True, exist_ok=True)

MIN_DIM = 32          # px: sotto questa soglia il logo è inutilizzabile
MAX_DIM = 512         # px: lato massimo dell'output ottimizzato
MAX_RATIO = 6.0       # rapporto massimo (oltre = banner/striscia, non un logo)
ACCEPTED_RASTER = ("png", "webp", "jpeg", "jpg", "ico", "gif", "bmp")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _domain(u: str) -> str:
    try:
        h = urlparse(u).netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def initials_for(source: str, url: str) -> str:
    """Iniziali della testata (fallback grafico)."""
    name = (source or "").strip()
    if not name:
        name = _domain(url).split(".")[0]
    words = [w for w in re.split(r"[\s.\-_]+", name) if w]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


# ----------------------- fetch -----------------------
def _get(url: str, timeout: int = 10):
    try:
        r = requests.get(url, timeout=timeout, headers=HEADERS, allow_redirects=True)
        return r
    except Exception:
        return None


# ----------------------- candidati dal markup -----------------------
def _walk_jsonld_logos(node, out):
    """Raccoglie URL di logo da nodi JSON-LD (publisher.logo prima, poi Organization.logo, poi logo)."""
    if isinstance(node, dict):
        # publisher.logo
        pub = node.get("publisher")
        if isinstance(pub, dict):
            lg = pub.get("logo")
            if isinstance(lg, str):
                out.append(lg)
            elif isinstance(lg, dict) and lg.get("url"):
                out.append(lg["url"])
        # logo diretto (tipicamente su Organization/NewsMediaOrganization/WebSite)
        lg = node.get("logo")
        if isinstance(lg, str):
            out.append(lg)
        elif isinstance(lg, dict) and lg.get("url"):
            out.append(lg["url"])
        for v in node.values():
            _walk_jsonld_logos(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_jsonld_logos(v, out)


def _candidates(base_url: str, html_text: str) -> list:
    """Lista ordinata di (metodo, url_assoluto) secondo la gerarchia."""
    cands = []

    def add(method, href):
        if not href:
            return
        try:
            absu = urljoin(base_url, href.strip())
        except Exception:
            return
        if absu.startswith("http"):
            cands.append((method, absu))

    html_text = html_text or ""

    # 1) JSON-LD
    for block in re.findall(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>",
                            html_text, re.S | re.I):
        raw = block.strip()
        try:
            data = json.loads(raw)
        except Exception:
            try:
                data = json.loads(re.sub(r",\s*([}\]])", r"\1", raw))
            except Exception:
                continue
        logos = []
        _walk_jsonld_logos(data, logos)
        for lg in logos:
            add("jsonld", lg)

    head = html_text[:200000]

    # 2) metadata
    for pat in [
        r'<meta[^>]+property=["\']og:logo["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+itemprop=["\']logo["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']msapplication-TileImage["\'][^>]+content=["\']([^"\']+)["\']',
        r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']',
    ]:
        for m in re.findall(pat, head, re.I):
            add("metadata", m)

    # 3) apple-touch-icon (con eventuale dimensione: preferiamo la più grande)
    apple = []
    for m in re.finditer(r'<link[^>]+rel=["\'][^"\']*apple-touch-icon[^"\']*["\'][^>]*>', head, re.I):
        tag = m.group(0)
        href = re.search(r'href=["\']([^"\']+)["\']', tag, re.I)
        sizes = re.search(r'sizes=["\'](\d+)', tag, re.I)
        if href:
            apple.append((int(sizes.group(1)) if sizes else 0, href.group(1)))
    for _, href in sorted(apple, key=lambda x: -x[0]):
        add("apple-touch", href)

    # 4) favicon dichiarata
    fav = []
    for m in re.finditer(r'<link[^>]+rel=["\'][^"\']*icon[^"\']*["\'][^>]*>', head, re.I):
        tag = m.group(0)
        if "apple-touch" in tag.lower():
            continue
        href = re.search(r'href=["\']([^"\']+)["\']', tag, re.I)
        sizes = re.search(r'sizes=["\'](\d+)', tag, re.I)
        if href:
            fav.append((int(sizes.group(1)) if sizes else 0, href.group(1)))
    for _, href in sorted(fav, key=lambda x: -x[0]):
        add("favicon", href)

    # 4-bis) /favicon.ico come ultima risorsa
    try:
        p = urlparse(base_url)
        add("favicon", f"{p.scheme}://{p.netloc}/favicon.ico")
    except Exception:
        pass

    # dedup conservando l'ordine (priorità per metodo)
    seen, ordered = set(), []
    for method, u in cands:
        if u in seen:
            continue
        seen.add(u)
        ordered.append((method, u))
    return ordered


# ----------------------- validazione + ottimizzazione -----------------------
def _validate_and_optimize(content: bytes):
    """Apre, valida e ottimizza l'immagine. Ritorna dict o None se non utilizzabile."""
    try:
        im = Image.open(io.BytesIO(content))
        im.load()
    except Exception:
        return None
    fmt = (im.format or "").lower()
    # PIL non gestisce SVG (e per sicurezza non lo accettiamo senza sanitizzazione):
    # accettiamo solo formati raster noti.
    if fmt not in ACCEPTED_RASTER:
        return None
    if getattr(im, "is_animated", False):
        try:
            im.seek(0)
        except Exception:
            pass
    orig_w, orig_h = im.size
    if orig_w < MIN_DIM or orig_h < MIN_DIM:
        return None
    ratio = max(orig_w, orig_h) / max(1, min(orig_w, orig_h))
    if ratio > MAX_RATIO:
        return None
    # converti su sfondo trasparente -> RGBA; rileva immagine "vuota"
    im = im.convert("RGBA")
    extrema = im.getextrema()  # ((rmin,rmax),(gmin,gmax),(bmin,bmax),(amin,amax))
    alpha = extrema[3] if len(extrema) == 4 else (255, 255)
    if alpha[1] == 0:
        return None  # completamente trasparente
    # immagine tutta di un solo colore = placeholder vuoto
    rgb_flat = all(c[0] == c[1] for c in extrema[:3])
    if rgb_flat and alpha[0] == alpha[1]:
        return None
    # ridimensiona mantenendo proporzioni
    im.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, format="WEBP", quality=88, method=6)
    data = out.getvalue()
    return {"bytes": data, "w": im.size[0], "h": im.size[1],
            "orig_w": orig_w, "orig_h": orig_h, "src_format": fmt}


def _save_webp(item_id: str, data: bytes) -> str:
    h = hashlib.sha1(data).hexdigest()[:16]
    fname = f"{item_id}-{h}.webp"
    (LOGO_DIR / fname).write_bytes(data)
    return fname, h


# ----------------------- estrazione (sync core) -----------------------
def extract_sync(url: str, source: str, item_id: str) -> dict:
    domain = _domain(url)
    meta = {
        "domain": domain, "source_url": None, "method": None, "url": None,
        "mime": None, "orig_w": None, "orig_h": None, "w": None, "h": None,
        "sha1": None, "http_status": None, "error": None,
        "review_status": "logo_review_required", "approved": False,
        "initials": initials_for(source, url), "extracted_at": _now(),
    }
    page = _get(url)
    if page is None:
        meta["error"] = "pagina irraggiungibile"
        return meta
    meta["http_status"] = page.status_code
    if page.status_code >= 400:
        meta["error"] = f"HTTP {page.status_code}"
        return meta
    candidates = _candidates(str(page.url), page.text)
    tried = 0
    for method, cand in candidates:
        if tried >= 8:
            break
        tried += 1
        r = _get(cand, timeout=8)
        if r is None or r.status_code >= 400 or not r.content:
            continue
        opt = _validate_and_optimize(r.content)
        if not opt:
            continue
        fname, h = _save_webp(item_id, opt["bytes"])
        meta.update({
            "source_url": cand, "method": method,
            "url": f"{SITE_URL}/api/static/press_logos/{fname}",
            "mime": "image/webp", "orig_w": opt["orig_w"], "orig_h": opt["orig_h"],
            "w": opt["w"], "h": opt["h"], "sha1": h, "src_format": opt["src_format"],
            # favicon piccole/incerte -> da revisionare; altrimenti ok
            "review_status": ("ok" if (method in ("jsonld", "metadata", "apple-touch")
                                       and min(opt["orig_w"], opt["orig_h"]) >= 64)
                              else "logo_review_required"),
            "approved": False, "error": None,
        })
        return meta
    meta["error"] = "nessun logo valido trovato (fallback iniziali)"
    return meta


# ----------------------- API async -----------------------
async def extract_for(item_id: str) -> dict:
    doc = await db.press.find_one({"id": item_id})
    if not doc:
        return {"ok": False, "error": "Articolo non trovato"}
    url = doc.get("url") or doc.get("canonical_url")
    source = doc.get("source") or ""
    loop = asyncio.get_event_loop()
    meta = await loop.run_in_executor(None, extract_sync, url, source, item_id)
    await db.press.update_one({"id": item_id}, {"$set": {"logo": meta, "updated_at": _now()}})
    return {"ok": True, "id": item_id, "logo": meta}


async def extract_all(only_missing: bool = False) -> dict:
    items = await db.press.find({}, {"_id": 0, "id": 1, "url": 1, "source": 1, "logo": 1,
                                     "title": 1, "canonical_url": 1}).to_list(500)
    results = []
    for it in items:
        if only_missing and (it.get("logo") or {}).get("url"):
            continue
        res = await extract_for(it["id"])
        lg = res.get("logo", {})
        results.append({
            "id": it["id"], "source": it.get("source"), "domain": lg.get("domain"),
            "method": lg.get("method"), "logo_url": lg.get("url"),
            "orig": f'{lg.get("orig_w")}x{lg.get("orig_h")}' if lg.get("orig_w") else None,
            "optimized": f'{lg.get("w")}x{lg.get("h")}' if lg.get("w") else None,
            "review_status": lg.get("review_status"), "error": lg.get("error"),
            "title": (it.get("title") or "")[:60],
        })
    return {"ok": True, "count": len(results), "results": results}


async def approve_logo(item_id: str) -> dict:
    doc = await db.press.find_one({"id": item_id})
    if not doc or not (doc.get("logo") or {}).get("url"):
        return {"ok": False, "error": "Nessun logo da approvare"}
    await db.press.update_one({"id": item_id},
                              {"$set": {"logo.approved": True, "logo.review_status": "approved",
                                        "updated_at": _now()}})
    return {"ok": True}


async def use_initials(item_id: str) -> dict:
    doc = await db.press.find_one({"id": item_id})
    if not doc:
        return {"ok": False, "error": "Articolo non trovato"}
    initials = initials_for(doc.get("source", ""), doc.get("url", ""))
    await db.press.update_one({"id": item_id}, {"$set": {
        "logo": {"domain": _domain(doc.get("url", "")), "method": "initials", "url": None,
                 "initials": initials, "review_status": "approved", "approved": True,
                 "extracted_at": _now()},
        "updated_at": _now()}})
    return {"ok": True, "initials": initials}


async def set_manual(item_id: str, image_url: str, w: int, h: int, mime: str) -> dict:
    doc = await db.press.find_one({"id": item_id})
    if not doc:
        return {"ok": False, "error": "Articolo non trovato"}
    await db.press.update_one({"id": item_id}, {"$set": {
        "logo": {"domain": _domain(doc.get("url", "")), "method": "manual", "url": image_url,
                 "source_url": "upload", "mime": mime, "w": w, "h": h,
                 "initials": initials_for(doc.get("source", ""), doc.get("url", "")),
                 "review_status": "approved", "approved": True, "extracted_at": _now()},
        "updated_at": _now()}})
    return {"ok": True}


def public_logo(doc: dict) -> dict:
    """Logo da mostrare nel sito pubblico: solo se approvato. Altrimenti iniziali."""
    lg = doc.get("logo") or {}
    if lg.get("approved") and lg.get("url"):
        return {"url": lg["url"], "initials": lg.get("initials")}
    return {"url": None, "initials": lg.get("initials") or initials_for(doc.get("source", ""), doc.get("url", ""))}
