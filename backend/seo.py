"""Rendering SSR (HTML completo) per le pagine pubbliche. URL pulite nei canonical."""
import json
import os
import re
import unicodedata
from datetime import datetime
import srt_utils as su
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config_db import SITE_URL, ROOT_DIR

STATIC_DIR = ROOT_DIR / "static"

env = Environment(
    loader=FileSystemLoader(str(ROOT_DIR / "templates")),
    autoescape=select_autoescape(["html", "xml"]),
)


def asset(path: str) -> str:
    """URL versionata di un asset statico servito dal backend (cache-busting)."""
    f = STATIC_DIR / path
    v = int(f.stat().st_mtime) if f.exists() else 0
    return f"{SITE_URL}/api/static/{path}?v={v}"


env.globals["asset"] = asset
env.globals["ga_measurement_id"] = os.environ.get("GA_MEASUREMENT_ID", "").strip()
env.globals["google_site_verification"] = os.environ.get("GOOGLE_SITE_VERIFICATION", "").strip()
env.globals["bing_site_verification"] = os.environ.get("BING_SITE_VERIFICATION", "").strip()


def apply_seo_config(cfg):
    """Aggiorna a runtime i codici SEO (GA4 + verifiche) iniettati nell'<head> SSR.
    I valori salvati da admin (DB) sovrascrivono i default da variabili ambiente."""
    if not isinstance(cfg, dict):
        return
    for k in ("ga_measurement_id", "google_site_verification", "bing_site_verification"):
        if k in cfg:
            env.globals[k] = (cfg.get(k) or "").strip()

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def _year():
    return datetime.now().year


def _t2s(t: str) -> int:
    try:
        parts = [int(x) for x in str(t).split(":")]
    except Exception:
        return 0
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0


def enrich(ep: dict) -> dict:
    ep = dict(ep)
    ep.pop("_id", None)
    ep.setdefault("type", "episodio")
    ep["type_label"] = ep.get("type_label") or ("Intervista" if ep["type"] == "intervista" else "Episodio")
    ep["section"] = ep.get("section") or ("interviste" if ep["type"] == "intervista" else "episodi")
    ep["section_label"] = ep.get("section_label") or ("Interviste" if ep["type"] == "intervista" else "Episodi")
    ep["h1"] = ep.get("h1") or ep.get("title", "")
    ep["website_title"] = ep.get("website_title") or ep["h1"]
    ep.setdefault("breadcrumb_label", "")
    ep["seo_title"] = ep.get("seo_title") or f'{ep.get("title", "")} | UnoXdue'
    ep["meta_description"] = ep.get("meta_description") or (ep.get("excerpt") or ep.get("title", ""))[:160]
    if not ep.get("thumbnail") and ep.get("youtube_id"):
        ep["thumbnail"] = f'https://img.youtube.com/vi/{ep["youtube_id"]}/maxresdefault.jpg'
    if not ep.get("published_human") and ep.get("published_at"):
        try:
            d = datetime.fromisoformat(ep["published_at"])
            ep["published_human"] = f"{d.day} {MESI[d.month - 1]} {d.year}"
        except Exception:
            ep["published_human"] = ep["published_at"]
    ep.setdefault("published_human", ep.get("published_at", ""))
    ep.setdefault("duration", "\u2014")
    for k in ("summary", "topics", "chapters", "quotes", "participants", "related", "summary_sections", "toc"):
        ep.setdefault(k, [])
    # summary_sections: garantisci id univoci + toc dagli H2
    if ep["summary_sections"]:
        used, toc = set(), []
        for s in ep["summary_sections"]:
            sid = s.get("id") or "sezione"
            base, k2 = sid, 2
            while sid in used:
                sid = f"{base}-{k2}"; k2 += 1
            used.add(sid); s["id"] = sid
            if int(s.get("level", 2)) == 2:
                toc.append({"id": sid, "heading": s.get("heading", "")})
        if not ep["toc"]:
            ep["toc"] = toc
    # deep-link dei capitoli al timestamp YouTube
    yid = ep.get("youtube_id")
    norm_ch = []
    for c in ep["chapters"]:
        if isinstance(c, dict) and c.get("time"):
            sec = _t2s(c["time"])
            cc = {"time": c["time"], "label": c.get("label") or c.get("title", ""),
                  "description": c.get("description", ""), "seconds": sec}
            if yid:
                cc["yt_url"] = f"https://www.youtube.com/watch?v={yid}&t={sec}s"
            norm_ch.append(cc)
    ep["chapters"] = norm_ch
    # normalizza quotes: accetta stringa o dict {text, speaker, time}
    norm_q = []
    for q in ep["quotes"]:
        if isinstance(q, str):
            norm_q.append({"text": q})
        elif isinstance(q, dict) and q.get("text"):
            norm_q.append(q)
    ep["quotes"] = norm_q
    return ep


def _iso_duration(seconds) -> str:
    seconds = int(seconds or 0)
    if seconds <= 0:
        return None
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    out = "PT"
    if h:
        out += f"{h}H"
    if m:
        out += f"{m}M"
    if s:
        out += f"{s}S"
    return out


def episode_jsonld(ep: dict) -> str:
    canonical = f'{SITE_URL}/{ep["section"]}/{ep["slug"]}/'
    yt = ep.get("youtube_id", "")
    publisher = {"@type": "Organization", "name": "UnoXdue", "logo": f"{SITE_URL}/logo.jpg"}
    video = {
        "@type": "VideoObject",
        "name": ep["h1"], "description": ep["meta_description"], "url": canonical,
        "thumbnailUrl": ep.get("thumbnail"), "uploadDate": ep.get("published_at"),
        "inLanguage": "it",
        "embedUrl": f'https://www.youtube.com/embed/{yt}',
        "contentUrl": f'https://www.youtube.com/watch?v={yt}',
        "publisher": publisher,
    }
    dur = _iso_duration(ep.get("duration_seconds"))
    if dur:
        video["duration"] = dur
    if ep.get("chapters"):
        video["hasPart"] = [
            {"@type": "Clip", "name": c["label"], "startOffset": c.get("seconds", 0),
             "url": f'{canonical}#t-{c.get("seconds", 0)}'}
            for c in ep["chapters"] if c.get("label")
        ]
    main_type = "PodcastEpisode" if ep["type"] != "intervista" else "Article"
    main = {
        "@type": main_type, "name": ep["h1"], "headline": ep["h1"],
        "description": ep["meta_description"], "url": canonical,
        "datePublished": ep.get("published_at"), "inLanguage": "it",
        "publisher": publisher,
        "associatedMedia": {"@type": "VideoObject", "embedUrl": f'https://www.youtube.com/embed/{yt}'},
    }
    if ep.get("has_transcript_page"):
        main["transcript"] = f'{canonical}trascrizione/'
    return json.dumps({"@context": "https://schema.org", "@graph": [main, video]}, ensure_ascii=False, indent=2)


def breadcrumb_jsonld(items) -> str:
    data = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u}
            for i, (n, u) in enumerate(items)
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def render_episode(ep: dict, press=None) -> str:
    ep = enrich(ep)
    canonical = f'{SITE_URL}/{ep["section"]}/{ep["slug"]}/'
    bc = breadcrumb_jsonld([
        ("Home", f"{SITE_URL}/"),
        (ep["section_label"], f'{SITE_URL}/{ep["section"]}/'),
        (ep.get("breadcrumb_label") or ep["title"], canonical),
    ])
    return env.get_template("episode.html").render(
        ep=ep, canonical=canonical, site_url=SITE_URL,
        jsonld=episode_jsonld(ep), breadcrumb_jsonld=bc, year=_year(),
        press=press or [],
    )


def render_archive(page_title, page_desc, canonical_path, items, show_play=False) -> str:
    canonical = f"{SITE_URL}{canonical_path}"
    bc = breadcrumb_jsonld([("Home", f"{SITE_URL}/"), (page_title, canonical)])
    item_list = [
        {"@type": "ListItem", "position": i + 1, "url": it.get("url"), "name": it.get("title")}
        for i, it in enumerate(items) if it.get("url")
    ]
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": page_title, "description": page_desc, "url": canonical, "inLanguage": "it",
        "isPartOf": {"@type": "WebSite", "@id": f"{SITE_URL}/#website"},
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(item_list),
                       "itemListElement": item_list},
    }, ensure_ascii=False, indent=2)
    return env.get_template("archive.html").render(
        page_title=page_title, page_desc=page_desc, canonical=canonical,
        items=items, site_url=SITE_URL, breadcrumb_jsonld=bc, jsonld=jsonld, year=_year(),
        show_play=show_play,
    )


def render_prediction(p: dict, noindex: bool = False) -> str:
    p = dict(p); p.pop("_id", None)
    season = p.get("season"); rnd = p.get("round")
    p["h1"] = p.get("h1") or f'Pronostici {p.get("competition", "Serie A")} {season} \u2014 {rnd}a giornata'
    p["seo_title"] = p.get("seo_title") or f'{p["h1"]} | UnoXdue'
    p["meta_description"] = p.get("meta_description") or p.get("intro", p["h1"])[:160]
    p.setdefault("intro", "")
    p.setdefault("picks", [])
    canonical = f'{SITE_URL}/pronostici/serie-a/{season}/giornata-{rnd}/'
    ci = _cover_image(p)
    article = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": p["h1"], "description": p["meta_description"], "url": canonical,
        "inLanguage": "it",
        "publisher": {"@type": "Organization", "name": "UnoXdue", "logo": f"{SITE_URL}/logo.jpg"},
    }
    if ci["has_cover"]:
        article["image"] = {"@type": "ImageObject", "url": ci["og"], "width": ci["w"], "height": ci["h"]}
    else:
        article["image"] = f"{SITE_URL}/logo.jpg"
    jsonld = json.dumps(article, ensure_ascii=False, indent=2)
    bc = breadcrumb_jsonld([
        ("Home", f"{SITE_URL}/"),
        ("Pronostici", f"{SITE_URL}/pronostici/"),
        (f'{p.get("competition", "Serie A")} {season} - {rnd}a giornata', canonical),
    ])
    return env.get_template("prediction.html").render(
        p=p, canonical=canonical, site_url=SITE_URL, jsonld=jsonld,
        breadcrumb_jsonld=bc, year=_year(),
        results_attribution=_results_attribution(), noindex=noindex,
        og_image=ci["og"], og_image_w=ci["w"], og_image_h=ci["h"], og_image_alt=ci["alt"],
    )


def _results_attribution():
    from config_db import SPORT_RESULTS_API_PROVIDER
    return "Data provided by football-data.org" if (SPORT_RESULTS_API_PROVIDER or "").lower() == "football-data" else None


def render_team_member(m: dict, related, press=None) -> str:
    m = dict(m); m.pop("_id", None)
    m["meta_description"] = (m.get("bio") or m.get("name", ""))[:160]
    photo = m.get("photo", "/logo.jpg")
    m["photo_abs"] = photo if photo.startswith("http") else f"{SITE_URL}{photo}"
    canonical = f'{SITE_URL}/team/{m["slug"]}/'
    same_as = [m["instagram"]] if m.get("instagram") else []
    person = {
        "@type": "Person", "@id": f"{canonical}#person",
        "name": m["name"], "description": m["meta_description"], "url": canonical,
        "image": m["photo_abs"], "jobTitle": m.get("role", ""), "sameAs": same_as,
        "worksFor": {"@type": "Organization", "name": "UnoXdue"},
    }
    profile = {
        "@type": "ProfilePage", "url": canonical, "inLanguage": "it",
        "mainEntity": {"@id": f"{canonical}#person"},
    }
    jsonld = json.dumps({"@context": "https://schema.org", "@graph": [profile, person]},
                        ensure_ascii=False, indent=2)
    bc = breadcrumb_jsonld([
        ("Home", f"{SITE_URL}/"), ("Il team", f"{SITE_URL}/team/"), (m["name"], canonical),
    ])
    return env.get_template("team_member.html").render(
        m_=m, canonical=canonical, site_url=SITE_URL, jsonld=jsonld,
        breadcrumb_jsonld=bc, related=related, year=_year(), press=press or [],
    )


def render_press_archive(items) -> str:
    canonical = f"{SITE_URL}/parlano-di-noi/"
    page_desc = ("Parlano di noi: la rassegna stampa di UnoXdue. Articoli e menzioni reali del podcast "
                 "sulla Serie A e dei suoi protagonisti, con link alle fonti originali.")
    item_list = [{"@type": "ListItem", "position": i + 1, "url": a.get("url"), "name": a.get("title")}
                 for i, a in enumerate(items) if a.get("url")]
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": "Parlano di noi", "description": page_desc, "url": canonical, "inLanguage": "it",
        "isPartOf": {"@type": "WebSite", "@id": f"{SITE_URL}/#website"},
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(item_list), "itemListElement": item_list},
    }, ensure_ascii=False, indent=2)
    bc = breadcrumb_jsonld([("Home", f"{SITE_URL}/"), ("Parlano di noi", canonical)])
    return env.get_template("press.html").render(
        items=items, canonical=canonical, site_url=SITE_URL, intro=PRESS_INTRO,
        breadcrumb_jsonld=bc, jsonld=jsonld, year=_year(),
    )


def render_team(team) -> str:
    """Pagina /team/: host in alto, i 3 tipster (gesti 1·X·2), poi altri componenti/collaboratori."""
    host, tip_by_slug, collaborators = None, {}, []
    for t in team:
        t = dict(t); t.pop("_id", None)
        t["photo_abs"] = _abs_url(t.get("photo"))
        if t.get("is_host"):
            host = t
        elif t.get("slug") in HOME_TIPSTER_ORDER:
            tip_by_slug[t.get("slug")] = t
        else:
            t["draft"] = (t.get("status") == "bozza")
            collaborators.append(t)
    tipsters = [tip_by_slug[s] for s in HOME_TIPSTER_ORDER if s in tip_by_slug]
    collaborators.sort(key=lambda x: x.get("order", 999))

    canonical = f"{SITE_URL}/team/"
    page_desc = ("Un host e tre tipster, più gli altri componenti e collaboratori: scopri le voci di "
                 "UnoXdue, il podcast sulla Serie A.")
    members = ([host] if host else []) + tipsters + collaborators
    item_list = [{"@type": "ListItem", "position": i + 1,
                  "url": f'{SITE_URL}/team/{mm.get("slug")}/', "name": mm.get("name")}
                 for i, mm in enumerate(members) if mm.get("slug")]
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": "Il team | UnoXdue", "description": page_desc, "url": canonical, "inLanguage": "it",
        "isPartOf": {"@type": "WebSite", "@id": f"{SITE_URL}/#website"},
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(item_list), "itemListElement": item_list},
    }, ensure_ascii=False, indent=2)
    bc = breadcrumb_jsonld([("Home", f"{SITE_URL}/"), ("Il team", canonical)])
    return env.get_template("team.html").render(
        host=host, tipsters=tipsters, collaborators=collaborators,
        canonical=canonical, page_desc=page_desc, site_url=SITE_URL,
        jsonld=jsonld, breadcrumb_jsonld=bc, year=_year(),
    )


def _abs_url(u: str) -> str:
    if not u:
        return f"{SITE_URL}/logo.jpg"
    return u if u.startswith("http") else f"{SITE_URL}{u}"


def _season_short(season: str) -> str:
    parts = (season or "").split("-")
    if len(parts) == 2 and len(parts[1]) == 4:
        return f"{parts[0]}/{parts[1][2:]}"
    return season or ""


def _cover_image(p: dict) -> dict:
    """Estrae la copertina (WebP automatica o manuale) per OG/Twitter/JSON-LD, con fallback al logo."""
    cover = p.get("cover") or {}
    fmts = cover.get("formats") or {}
    hor = fmts.get("horizontal") or {}
    sq = fmts.get("square") or {}
    has = bool(hor.get("url"))
    return {
        "og": hor.get("url") or f"{SITE_URL}/logo.jpg",
        "square": sq.get("url"),
        "w": hor.get("w") or 1200,
        "h": hor.get("h") or 630,
        "alt": cover.get("alt") or p.get("h1") or "Pronostici UnoXdue",
        "has_cover": has,
    }


# Ordine fisso del team in homepage (host in evidenza + tipster). Modificabile da qui.
HOME_TIPSTER_ORDER = ["il-marziano", "sono-micuccio", "il-ninja"]

HOME_ABOUT = [
    "UnoXdue è il podcast sulla Serie A con tre tipster e un host: analisi tattica, pronostici e "
    "dibattito appassionato si incontrano per offrirti uno sguardo unico sul calcio italiano.",
    "Ogni settimana Sono Micuccio, il Ninja e il Marziano si ritrovano in diretta insieme all'host "
    "Antonello Santopaolo per discutere della Serie A, analizzare le partite più importanti e "
    "confrontarsi sui temi caldi del calcio italiano ed europeo.",
    "Dalle giornate di campionato ai palinsesti, dalle giocate alle interviste ai protagonisti, "
    "UnoXdue è il punto di ritrovo per gli appassionati che cercano contenuti autentici e approfonditi.",
]
HOME_FEATURES = [
    {"icon": "radio", "title": "Dirette settimanali", "text": "Live su Twitch con analisi e dibattito in tempo reale."},
    {"icon": "target", "title": "Focus Serie A", "text": "Approfondimenti su tutte le partite del campionato italiano."},
    {"icon": "users", "title": "Tre tipster e un host", "text": "Quattro punti di vista diversi per un'analisi completa."},
    {"icon": "clapperboard", "title": "Contenuti multipli", "text": "Clip, highlights ed esclusive su tutti i social."},
]
HOME_SOCIALS = [
    {"key": "twitch", "label": "Twitch", "handle": "@unoxdue_", "desc": "Dirette live ogni settimana", "url": "https://www.twitch.tv/unoxdue_", "color": "#9146FF"},
    {"key": "youtube", "label": "YouTube", "handle": "@unoXdue", "desc": "Episodi completi e interviste", "url": "https://www.youtube.com/@unoXdue", "color": "#FF0000"},
    {"key": "instagram", "label": "Instagram", "handle": "@unoxdue_", "desc": "Clip, news e dietro le quinte", "url": "https://www.instagram.com/unoxdue_", "color": "#E1306C"},
    {"key": "tiktok", "label": "TikTok", "handle": "@unoxdue_", "desc": "I momenti migliori in breve", "url": "https://www.tiktok.com/@unoxdue_", "color": "#111111"},
]


def render_home(episodes, interviews, team=None, prediction=None, press=None) -> str:
    team = team or []
    photo_by_name = {t.get("name"): t.get("photo") for t in team}

    host = None
    tipsters_by_slug = {}
    for t in team:
        t = dict(t); t.pop("_id", None)
        t["photo_abs"] = _abs_url(t.get("photo"))
        if t.get("is_host"):
            host = t
        else:
            tipsters_by_slug[t.get("slug")] = t
    tipsters = [tipsters_by_slug[s] for s in HOME_TIPSTER_ORDER if s in tipsters_by_slug]

    pred = None
    if prediction:
        pred = dict(prediction); pred.pop("_id", None)
        picks = []
        for p in (pred.get("picks") or []):
            p = dict(p)
            p["photo_abs"] = _abs_url(photo_by_name.get(p.get("tipster")))
            picks.append(p)
        pred["picks"] = picks

    socials_same_as = [s["url"] for s in HOME_SOCIALS]
    org = {
        "@type": "Organization", "@id": f"{SITE_URL}/#organization", "name": "UnoXdue",
        "url": f"{SITE_URL}/", "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/logo.jpg"},
        "sameAs": socials_same_as,
    }
    website = {
        "@type": "WebSite", "@id": f"{SITE_URL}/#website", "name": "UnoXdue",
        "url": f"{SITE_URL}/", "inLanguage": "it", "publisher": {"@id": f"{SITE_URL}/#organization"},
    }
    series = {
        "@type": "PodcastSeries", "@id": f"{SITE_URL}/#podcast", "name": "UnoXdue",
        "url": f"{SITE_URL}/", "image": f"{SITE_URL}/logo.jpg", "inLanguage": "it",
        "genre": "Sport", "publisher": {"@id": f"{SITE_URL}/#organization"}, "sameAs": socials_same_as,
    }
    jsonld = json.dumps({"@context": "https://schema.org", "@graph": [org, website, series]},
                        ensure_ascii=False, indent=2)
    return env.get_template("home.html").render(
        episodes=episodes, interviews=interviews, site_url=SITE_URL,
        jsonld=jsonld, year=_year(),
        about_text=HOME_ABOUT, features=HOME_FEATURES, socials=HOME_SOCIALS,
        host=host, tipsters=tipsters, prediction=pred, press=press or [],
    )


def render_page(page_title, page_desc, canonical_path, body_html, noindex=False,
                page_type="WebPage", faqs=None):
    canonical = f"{SITE_URL}{canonical_path}"
    bc = breadcrumb_jsonld([("Home", f"{SITE_URL}/"), (page_title, canonical)])
    page_node = {
        "@type": page_type, "@id": f"{canonical}#webpage", "url": canonical,
        "name": f"{page_title} | UnoXdue", "description": page_desc, "inLanguage": "it",
        "isPartOf": {"@type": "WebSite", "@id": f"{SITE_URL}/#website"},
        "publisher": {"@type": "Organization", "name": "UnoXdue", "logo": f"{SITE_URL}/logo.jpg"},
    }
    page_jsonld = json.dumps({"@context": "https://schema.org", "@graph": [page_node]},
                             ensure_ascii=False, indent=2)
    faq_jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": f["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faqs],
    }, ensure_ascii=False, indent=2) if faqs else None
    return env.get_template("page.html").render(
        page_title=page_title, page_desc=page_desc, canonical=canonical,
        body_html=body_html, site_url=SITE_URL, breadcrumb_jsonld=bc, year=_year(),
        noindex=noindex, page_jsonld=page_jsonld, faq_jsonld=faq_jsonld, faqs=faqs or [],
    )


def _paragraphs(text: str, target: int = 700) -> list:
    """Spezza il testo pulito in paragrafi leggibili (~target caratteri).
    Usa i confini di frase; se i sottotitoli sono privi di punteggiatura, spezza per parole."""
    text = (text or "").strip()
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?\u2026])\s+", text)
    units = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if len(s) > target * 1.5:  # blocco senza punteggiatura: spezza per parole
            chunk = ""
            for w in s.split():
                if len(chunk) + len(w) + 1 > target and chunk:
                    units.append(chunk.strip())
                    chunk = ""
                chunk = f"{chunk} {w}".strip()
            if chunk:
                units.append(chunk.strip())
        else:
            units.append(s)
    paras, buf = [], ""
    for u in units:
        if len(buf) + len(u) + 1 > target and buf:
            paras.append(buf.strip())
            buf = ""
        buf = f"{buf} {u}".strip()
    if buf:
        paras.append(buf.strip())
    return paras


def _split_transcript_by_chapters(segments, chapters):
    if not segments or not chapters:
        return None
    seg_clean = su.segment_clean_text(segments)
    chs = sorted([c for c in chapters if c.get("label")], key=lambda c: c.get("seconds", 0))
    if not chs:
        return None
    sections, used, n = [], set(), len(chs)
    for i, c in enumerate(chs):
        start = chs[i].get("seconds", 0)
        end = chs[i + 1].get("seconds", 0) if i + 1 < n else float("inf")
        lo = -1 if i == 0 else start  # il primo capitolo assorbe il testo iniziale
        text = " ".join(s["clean"].strip() for s in seg_clean
                         if lo <= s.get("start", 0) < end and s.get("clean", "").strip())
        if not text.strip():
            continue
        base = _slug_anchor(c.get("label"))
        sid, k = base, 2
        while sid in used:
            sid = f"{base}-{k}"; k += 1
        used.add(sid)
        sections.append({
            "id": sid, "time": c.get("time"), "seconds": c.get("seconds", 0),
            "label": c.get("label"), "yt_url": c.get("yt_url"),
            "paragraphs": _paragraphs(text, target=600),
        })
    return sections or None


def render_transcript(ep: dict, clean: str, chapters: list, segments=None) -> str:
    ep = enrich(ep)
    canonical = f'{SITE_URL}/{ep["section"]}/{ep["slug"]}/trascrizione/'
    episode_url = f'{SITE_URL}/{ep["section"]}/{ep["slug"]}/'
    sections = _split_transcript_by_chapters(segments, ep.get("chapters", []))
    paras = None if sections else _paragraphs(clean)
    _wt = ep.get("website_title") or ep["title"]
    bc = breadcrumb_jsonld([
        ("Home", f"{SITE_URL}/"),
        (ep["section_label"], f'{SITE_URL}/{ep["section"]}/'),
        (ep.get("breadcrumb_label") or ep["title"], episode_url),
        ("Trascrizione", canonical),
    ])
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "WebPage",
        "@id": f"{canonical}#webpage",
        "name": f'Trascrizione — {_wt}',
        "headline": f'Trascrizione — {_wt}',
        "description": f'Trascrizione completa della puntata: {_wt}.',
        "url": canonical, "inLanguage": "it",
        "isPartOf": {"@type": "WebPage", "@id": episode_url},
        "datePublished": ep.get("published_at"),
        "publisher": {"@type": "Organization", "name": "UnoXdue", "logo": f"{SITE_URL}/logo.jpg"},
    }, ensure_ascii=False, indent=2)
    return env.get_template("transcript.html").render(
        ep=ep, canonical=canonical, episode_url=episode_url, site_url=SITE_URL,
        sections=sections, paragraphs=paras, chapters=ep.get("chapters", []), jsonld=jsonld,
        breadcrumb_jsonld=bc, year=_year(),
    )


# ============================ Archivio Pronostici ============================
PRONOSTICI_INTRO = [
    "I pronostici di UnoXdue nascono dal lavoro settimanale del team: Sono Micuccio, il Ninja e il "
    "Marziano studiano la giornata di Serie A e propongono le loro selezioni, partita per partita. "
    "In questa sezione raccogliamo le giocate di ogni turno, così come sono state presentate in diretta "
    "e nelle puntate del podcast.",
    "Pubblichiamo solo dati reali. Per ogni selezione indichiamo competizione, partita, mercato ed esito "
    "proposto; le quote riportate sono quelle rilevate dalla grafica comparativa fornita dal team al "
    "momento della pubblicazione e hanno valore puramente indicativo, perché possono variare nel tempo e "
    "tra i diversi operatori.",
    "Dopo le partite verifichiamo l'esito di ogni selezione con i risultati ufficiali e ne tracciamo lo "
    "stato (vinta, persa, void o da verificare). L'obiettivo non è inseguire la giocata perfetta, ma "
    "raccontare un metodo: come si legge una partita, perché si sceglie un mercato e cosa è successo "
    "davvero in campo.",
    "I contenuti di questa sezione sono editoriali e pensati per l'intrattenimento e l'approfondimento. "
    "Non costituiscono un invito al gioco né una garanzia di vincita: 18+, gioca responsabilmente.",
]
PRONOSTICI_FAQS = [
    {"q": "Ogni quanto pubblicate i pronostici?",
     "a": "Pubblichiamo le giocate del team per ogni giornata di Serie A, in concomitanza con le dirette su Twitch e le puntate settimanali del podcast."},
    {"q": "Da dove provengono le quote?",
     "a": "Le quote sono rilevate dalla grafica comparativa fornita dal team al momento della pubblicazione. Sono indicative e possono variare nel tempo e tra i diversi operatori: non vengono mai inventate né aggiornate automaticamente."},
    {"q": "Verificate i risultati delle selezioni?",
     "a": "Sì. Dopo le partite confrontiamo ogni selezione con i risultati ufficiali e ne aggiorniamo lo stato (vinta, persa, void o da verificare) sulla pagina della giornata."},
    {"q": "I pronostici garantiscono una vincita?",
     "a": "No. Sono contenuti editoriali a scopo di intrattenimento e non garantiscono alcun risultato. Il gioco è riservato ai maggiorenni: 18+, gioca responsabilmente."},
]


def render_pronostici_archive(predictions) -> str:
    canonical = f"{SITE_URL}/pronostici/"
    page_title = "Pronostici Serie A"
    page_desc = ("I pronostici di UnoXdue per ogni giornata di Serie A: le giocate reali del team, "
                 "quote indicative e verifica dei risultati. 18+, gioca responsabilmente.")
    groups, order = {}, []
    for p in predictions:
        s = p.get("season", "")
        if s not in groups:
            groups[s] = []; order.append(s)
        cover = p.get("cover") or {}
        fmts = cover.get("formats") or {}
        hor = fmts.get("horizontal") or {}
        thumb = fmts.get("thumb") or {}
        groups[s].append({
            "url": f'{SITE_URL}/pronostici/serie-a/{p.get("season")}/giornata-{p.get("round")}/',
            "cover": thumb.get("url") or hor.get("url"),
            "alt": cover.get("alt") or f'Pronostici {p.get("competition","Serie A")} {_season_short(s)} {p.get("round")}ª giornata — UnoXdue',
            "logo": f"{SITE_URL}/logo.jpg",
            "season_short": _season_short(s),
            "round": p.get("round"),
            "competition": p.get("competition", "Serie A"),
            "season": s,
        })
    order.sort(reverse=True)
    seasons = [{"season": s, "cards": sorted(groups[s], key=lambda c: (c["round"] or 0), reverse=True)}
               for s in order]

    item_list, pos = [], 1
    for grp in seasons:
        for c in grp["cards"]:
            item_list.append({"@type": "ListItem", "position": pos, "url": c["url"],
                              "name": f'{c["competition"]} {c["season"]} — {c["round"]}ª giornata'})
            pos += 1
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": page_title, "description": page_desc, "url": canonical, "inLanguage": "it",
        "isPartOf": {"@type": "WebSite", "@id": f"{SITE_URL}/#website"},
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(item_list), "itemListElement": item_list},
    }, ensure_ascii=False, indent=2)
    faq_jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": f["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in PRONOSTICI_FAQS],
    }, ensure_ascii=False, indent=2) if PRONOSTICI_FAQS else None
    bc = breadcrumb_jsonld([("Home", f"{SITE_URL}/"), (page_title, canonical)])

    og_image = f"{SITE_URL}/logo.jpg"
    for grp in seasons:
        hit = next((c["cover"] for c in grp["cards"] if c["cover"]), None)
        if hit:
            og_image = hit; break

    return env.get_template("pronostici_archive.html").render(
        page_title=page_title, page_desc=page_desc, canonical=canonical, site_url=SITE_URL,
        seasons=seasons, intro=PRONOSTICI_INTRO, faqs=PRONOSTICI_FAQS,
        breadcrumb_jsonld=bc, jsonld=jsonld, faq_jsonld=faq_jsonld, og_image=og_image, year=_year(),
    )


# ============================ Pagina "Il podcast" ============================
IL_PODCAST_LEAD = (
    "UnoXdue è il podcast indipendente dedicato alla Serie A: un host e tre tipster che ogni settimana "
    "trasformano l'analisi del campionato in un racconto vivo, tra tattica, numeri, pronostici e "
    "interviste ai protagonisti."
)
IL_PODCAST_ABOUT = [
    "Nato dalla passione per il calcio italiano, UnoXdue mette al centro il confronto: non un monologo, "
    "ma quattro voci che discutono, si sfidano e leggono la Serie A da prospettive diverse. Il risultato "
    "è un podcast in cui l'analisi tecnica convive con l'ironia e con il gusto della scommessa ragionata.",
    "Ogni puntata parte dalle partite di giornata e arriva ai temi caldi del campionato: moduli e scelte "
    "degli allenatori, momenti di forma, calendario, mercato e ripercussioni sulla corsa per lo scudetto, "
    "per l'Europa e per la salvezza. Quando l'attualità lo richiede, lo sguardo si allarga anche al calcio "
    "internazionale e ad altri sport.",
    "UnoXdue non è solo diretta: è un archivio in continua crescita di episodi, interviste e pronostici, "
    "pensato per chi vuole capire la Serie A più a fondo e ritrovare i contenuti quando vuole.",
]
IL_PODCAST_FEATURES = [
    {"icon": "radio", "title": "Dirette settimanali",
     "text": "Appuntamento live su Twitch per commentare la giornata in tempo reale, rispondere al pubblico e costruire le giocate insieme."},
    {"icon": "clapperboard", "title": "Episodi on demand",
     "text": "Ogni puntata resta disponibile su YouTube e in archivio sul sito, con titoli, sommari e capitoli per ritrovare i momenti chiave."},
    {"icon": "target", "title": "Pronostici di giornata",
     "text": "Le selezioni reali dei tipster per ogni turno di Serie A, con quote indicative e verifica dei risultati a fine giornata."},
    {"icon": "users", "title": "Interviste esclusive",
     "text": "Calciatori, allenatori e protagonisti del calcio italiano raccontati senza filtri, in conversazioni lunghe e curate."},
]
IL_PODCAST_FORMAT = [
    "Una puntata tipo di UnoXdue segue un ritmo riconoscibile: si apre con il quadro della giornata, si "
    "entra nell'analisi delle partite più importanti, si confrontano le letture tattiche dei tipster e si "
    "chiude con le giocate proposte per il turno.",
    "Le interviste vivono invece di tempi propri: nessuna fretta, domande preparate e spazio al racconto, "
    "perché ogni ospite possa restituire la sua storia e la sua visione del gioco.",
]
IL_PODCAST_FAQS = [
    {"q": "Ogni quanto esce un nuovo episodio di UnoXdue?",
     "a": "Pubblichiamo nuove puntate con cadenza settimanale, in concomitanza con le giornate di Serie A. Le dirette vanno in onda su Twitch e gli episodi completi restano poi disponibili su YouTube e in archivio sul sito."},
    {"q": "Dove posso ascoltare e guardare il podcast?",
     "a": "Le dirette sono su Twitch (@unoxdue_), gli episodi completi su YouTube (@unoXdue) e una selezione di clip e contenuti brevi su Instagram e TikTok. Tutti i canali sono raggiungibili dal sito."},
    {"q": "Di cosa parla UnoXdue?",
     "a": "Soprattutto di Serie A: analisi delle partite, tattica, momenti di forma, calendario e mercato. Trovano spazio anche i pronostici di giornata, le interviste ai protagonisti e, all'occorrenza, il calcio internazionale e altri sport."},
    {"q": "Chi compone il team?",
     "a": "Il podcast è condotto dall'host Antonello Santopaolo insieme ai tre tipster Sono Micuccio, il Ninja e il Marziano. Ognuno porta uno stile e una specialità diversi all'analisi della giornata."},
    {"q": "I pronostici garantiscono una vincita?",
     "a": "No. I pronostici di UnoXdue sono contenuti editoriali a scopo di intrattenimento: pubblichiamo le giocate reali del team con quote indicative, senza alcuna garanzia di risultato. Il gioco è riservato ai maggiorenni: 18+, gioca responsabilmente."},
    {"q": "Come posso proporre una collaborazione o un'intervista?",
     "a": "Puoi scriverci attraverso la pagina Contatti o i nostri canali social. Per partnership e progetti editoriali trovi i dettagli nella pagina Collaborazioni."},
]


def il_podcast_defaults() -> dict:
    import copy
    return {
        "hero_lead": IL_PODCAST_LEAD,
        "about": list(IL_PODCAST_ABOUT),
        "format_text": list(IL_PODCAST_FORMAT),
        "features": copy.deepcopy(IL_PODCAST_FEATURES),
        "faqs": copy.deepcopy(IL_PODCAST_FAQS),
    }


def render_il_podcast(team=None, content=None) -> str:
    team = team or []
    host, tipsters_by_slug = None, {}
    for t in team:
        t = dict(t); t.pop("_id", None)
        t["photo_abs"] = _abs_url(t.get("photo"))
        if t.get("is_host"):
            host = t
        else:
            tipsters_by_slug[t.get("slug")] = t
    tipsters = [tipsters_by_slug[s] for s in HOME_TIPSTER_ORDER if s in tipsters_by_slug]

    # contenuti editoriali modificabili dall'admin (fallback ai default)
    c = il_podcast_defaults()
    if content:
        for k in c:
            if content.get(k):
                c[k] = content[k]
    hero_lead, about, format_text, features, faqs = (
        c["hero_lead"], c["about"], c["format_text"], c["features"], c["faqs"])

    canonical = f"{SITE_URL}/il-podcast/"
    page_title = "Il podcast"
    page_desc = ("Scopri UnoXdue: il podcast sulla Serie A con un host e tre tipster. Format, voci, "
                 "dirette, episodi, interviste e pronostici di giornata.")
    webpage = {
        "@type": "WebPage", "@id": f"{canonical}#webpage", "url": canonical,
        "name": f"{page_title} | UnoXdue", "description": page_desc, "inLanguage": "it",
        "isPartOf": {"@type": "WebSite", "@id": f"{SITE_URL}/#website"},
        "about": {"@id": f"{SITE_URL}/#podcast"},
    }
    series = {
        "@type": "PodcastSeries", "@id": f"{SITE_URL}/#podcast", "name": "UnoXdue",
        "url": f"{SITE_URL}/", "image": f"{SITE_URL}/logo.jpg", "inLanguage": "it",
        "genre": "Sport", "description": hero_lead,
        "sameAs": [s["url"] for s in HOME_SOCIALS],
    }
    jsonld = json.dumps({"@context": "https://schema.org", "@graph": [webpage, series]},
                        ensure_ascii=False, indent=2)
    faq_jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": f["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faqs],
    }, ensure_ascii=False, indent=2) if faqs else None
    bc = breadcrumb_jsonld([("Home", f"{SITE_URL}/"), (page_title, canonical)])

    return env.get_template("il_podcast.html").render(
        page_title=page_title, page_desc=page_desc, canonical=canonical, site_url=SITE_URL,
        hero_lead=hero_lead, about=about, features=features,
        format_text=format_text, faqs=faqs, host=host, tipsters=tipsters,
        socials=HOME_SOCIALS, jsonld=jsonld, faq_jsonld=faq_jsonld, breadcrumb_jsonld=bc, year=_year(),
    )


# ============================ Collabora con noi (Sponsor B2B) ============================
SPONSOR_PACKAGES = [
    {"name": "Starter — Presenza digitale", "tagline": "Ideale per una prima campagna sulla community.",
     "highlight": False, "badge": None, "features": [
        {"text": "Banner a rotazione su unoxdue.net per 30 giorni"},
        {"text": "1 post sul canale Telegram"},
        {"text": "1 spazio nella newsletter"},
        {"text": "Link e citazione nelle show notes"},
        {"text": "Report finale della campagna"},
        {"text": "Nessuna integrazione durante la puntata", "no": True},
     ]},
    {"name": "Pro — Community Partner", "tagline": "Visibilità continuativa sui canali proprietari.",
     "highlight": True, "badge": "Più scelto", "features": [
        {"text": "Tutto il pacchetto Starter"},
        {"text": "Banner fisso su unoxdue.net per 30 giorni"},
        {"text": "1 contenuto social dedicato"},
        {"text": "1 storia Instagram"},
        {"text": "1 breve menzione verbale in una puntata al mese"},
        {"text": "Report con impression, visualizzazioni e interazioni"},
     ]},
    {"name": "Premium — Integrated Partner", "tagline": "Partnership multicanale personalizzata.",
     "highlight": False, "badge": None, "features": [
        {"text": "Tutto il pacchetto Pro"},
        {"text": "1 breve rubrica o attivazione sponsorizzata al mese"},
        {"text": "Presenza in un live o contenuto speciale"},
        {"text": "Contenuto social co-prodotto"},
        {"text": "Posizionamento premium sul sito"},
        {"text": "Esclusiva merceologica nella categoria concordata"},
        {"text": "Report personalizzato di fine campagna"},
     ]},
]
SPONSOR_FORMATS = [
    {"icon": "🖼️", "title": "Banner sul sito", "text": "Spazio su unoxdue.net, visibile sulle pagine del sito."},
    {"icon": "📣", "title": "Post Telegram", "text": "Annuncio diretto alla community più attiva, con link tracciabile."},
    {"icon": "✉️", "title": "Newsletter", "text": "Spazio dedicato nell'email che raggiunge gli iscritti."},
    {"icon": "📱", "title": "Contenuto social + storia IG", "text": "Post e storia Instagram costruiti attorno al tuo brand."},
    {"icon": "🎙️", "title": "Breve menzione verbale", "text": "Una citazione leggera (10-15s) durante la puntata, senza stravolgere il format."},
    {"icon": "🔴", "title": "Rubrica / live", "text": "Attivazione leggera o presenza in una diretta o contenuto speciale."},
]
SPONSOR_STEPS = [
    {"n": "01", "title": "Ci scrivi", "text": "Compili il form con obiettivi e budget. Ti inviamo il media kit completo."},
    {"n": "02", "title": "Costruiamo la proposta", "text": "Scegliamo insieme formati e pacchetto, su misura per il tuo brand."},
    {"n": "03", "title": "Si va in onda", "text": "Pianifichiamo gli inserimenti e a fine campagna ti diamo un report con i risultati."},
]
SPONSOR_PODCAST_NOTE = ("La menzione o attivazione nel podcast non comporta modifiche permanenti alla "
                        "scenografia o alla copertina degli episodi.")
SPONSOR_PACKAGE_NOTE = ("I pacchetti sono disponibili esclusivamente per brand e servizi non appartenenti al "
                        "settore betting, casinò o gioco con vincita in denaro. Tutte le integrazioni sono "
                        "subordinate alla compatibilità editoriale, merceologica e con le partnership già attive.")
SPONSOR_FAQS = [
    {"q": "Quali brand possono sponsorizzare UnoXdue?",
     "a": "Brand e servizi non appartenenti al settore betting, casinò o gioco con vincita in denaro. Le integrazioni sono soggette a compatibilità editoriale e con le partnership già attive."},
    {"q": "Come funziona una collaborazione?",
     "a": "Compili il form con obiettivi e budget, ti inviamo il media kit, costruiamo insieme la proposta e pianifichiamo gli inserimenti; a fine campagna ricevi un report."},
    {"q": "Fate contenuti dedicati dentro il podcast?",
     "a": "Sì, ma solo integrazioni leggere e compatibili con il format: nessuna modifica permanente alla scenografia o alla copertina degli episodi."},
]


def sponsor_defaults() -> dict:
    import copy
    return {
        "hero_kicker": "Sponsorizzazioni · Serie A · Podcast",
        "hero_title_a": "Porta il tuo brand dentro la community ",
        "hero_title_hl": "Serie A",
        "hero_title_b": " più appassionata.",
        "hero_lead": ("UnoXdue è il podcast e la community che vive di calcio, pronostici e Serie A. "
                      "Un pubblico fedele e coinvolto: il posto giusto per far parlare il tuo marchio."),
        "intro": [
            "Ogni settimana raccontiamo la Serie A con episodi su YouTube, dirette su Twitch, interviste ai protagonisti e pronostici di giornata.",
            "Chi ci segue non si limita a guardare: commenta, torna e partecipa. Per uno sponsor significa attenzione reale, non solo numeri.",
        ],
        "stats": [
            {"num": "Serie A", "label": "Focus 100% calcio italiano"},
            {"num": "Multicanale", "label": "YouTube · Twitch · Social · Podcast"},
            {"num": "Settimanale", "label": "Nuovi contenuti ogni settimana"},
            {"num": "Community", "label": "Pubblico fedele e in crescita"},
        ],
        "audience": [
            {"title": "Pubblico adulto e attivo", "text": "Appassionati di calcio con reale interesse e capacità di spesa."},
            {"title": "Community affezionata", "text": "Chi ci segue torna ogni settimana: interazione alta e costante."},
            {"title": "Territorio + Italia", "text": "Forte legame con il territorio, con una community estesa a livello nazionale."},
        ],
        "contact_email": "partner@unoxdue.net",
    }


def _sponsor_content(content=None):
    c = sponsor_defaults()
    if content:
        for k in c:
            if content.get(k):
                c[k] = content[k]
    return c


def render_sponsor(content=None) -> str:
    c = _sponsor_content(content)
    canonical = f"{SITE_URL}/collaborazioni/"
    page_title = "Collabora con noi"
    page_desc = ("Sponsorizza UnoXdue: podcast e community sulla Serie A. Pacchetti, formati e media kit "
                 "per brand (esclusi operatori di gioco). Richiedi una proposta personalizzata.")
    webpage = {
        "@type": "AboutPage", "@id": f"{canonical}#webpage", "url": canonical,
        "name": f"{page_title} | UnoXdue", "description": page_desc, "inLanguage": "it",
        "isPartOf": {"@type": "WebSite", "@id": f"{SITE_URL}/#website"},
        "publisher": {"@type": "Organization", "name": "UnoXdue", "logo": f"{SITE_URL}/logo.jpg"},
    }
    jsonld = json.dumps({"@context": "https://schema.org", "@graph": [webpage]},
                        ensure_ascii=False, indent=2)
    faq_jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": f["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in SPONSOR_FAQS],
    }, ensure_ascii=False, indent=2)
    bc = breadcrumb_jsonld([("Home", f"{SITE_URL}/"), (page_title, canonical)])
    return env.get_template("sponsor.html").render(
        page_title=page_title, page_desc=page_desc, canonical=canonical, site_url=SITE_URL,
        hero_kicker=c["hero_kicker"], hero_title_a=c["hero_title_a"], hero_title_hl=c["hero_title_hl"],
        hero_title_b=c["hero_title_b"], hero_lead=c["hero_lead"], intro=c["intro"],
        stats=c["stats"], audience=c["audience"], contact_email=c["contact_email"],
        packages=SPONSOR_PACKAGES, formats=SPONSOR_FORMATS, steps=SPONSOR_STEPS,
        podcast_note=SPONSOR_PODCAST_NOTE, package_note=SPONSOR_PACKAGE_NOTE,
        jsonld=jsonld, faq_jsonld=faq_jsonld, breadcrumb_jsonld=bc, year=_year(),
    )


def render_media_kit(content=None) -> str:
    c = _sponsor_content(content)
    rows = ""
    for pk in SPONSOR_PACKAGES:
        feats = "".join(f"<li>{'—' if f.get('no') else '✓'} {f['text']}</li>" for f in pk["features"])
        rows += (f"<div class='pk'><h3>{pk['name']}</h3><p class='tag'>{pk['tagline']}</p>"
                 f"<p class='price'>Su richiesta</p><ul>{feats}</ul></div>")
    stat_html = "".join(f"<div class='st'><b>{s['num']}</b><span>{s['label']}</span></div>" for s in c["stats"])
    aud_html = "".join(f"<li><b>{a['title']}</b> — {a['text']}</li>" for a in c["audience"])
    intro_html = "".join(f"<p>{p}</p>" for p in c["intro"])
    fmt_html = "".join(f"<li><b>{f['title']}</b>: {f['text']}</li>" for f in SPONSOR_FORMATS)
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8"/>
<title>UnoXdue — Media Kit</title>
<style>
@page{{size:A4;margin:16mm}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Helvetica Neue',Arial,sans-serif;color:#14100e;line-height:1.5;font-size:12px}}
.cover{{background:#14100e;color:#fff;padding:34px;border-radius:14px;margin-bottom:22px}}
.cover .kick{{color:#EA4E1B;font-weight:800;text-transform:uppercase;letter-spacing:2px;font-size:11px}}
.cover h1{{font-size:32px;margin:10px 0 6px;line-height:1.1}}
.cover h1 span{{color:#EA4E1B}}
.cover p{{color:rgba(255,255,255,.8);max-width:520px}}
h2{{color:#EA4E1B;font-size:15px;text-transform:uppercase;letter-spacing:1px;margin:20px 0 8px;border-bottom:2px solid #f0e7da;padding-bottom:5px}}
.stats{{display:flex;gap:10px;margin:10px 0}}
.st{{flex:1;border:1px solid #ecdfce;border-radius:10px;padding:12px;text-align:center}}
.st b{{display:block;font-size:16px;color:#14100e}}
.st span{{font-size:10px;color:#8a7a6c}}
ul{{margin:6px 0 6px 18px}}
li{{margin:3px 0}}
.pks{{display:flex;gap:12px;margin-top:10px}}
.pk{{flex:1;border:1px solid #ecdfce;border-radius:12px;padding:14px}}
.pk h3{{font-size:13px}}
.pk .tag{{color:#8a7a6c;font-size:10px;margin:2px 0 6px}}
.pk .price{{color:#EA4E1B;font-weight:800;margin-bottom:6px}}
.pk ul{{list-style:none;margin:0;font-size:10.5px}}
.pk li{{margin:4px 0}}
.note{{background:#fdf1ec;border:1px solid #e6b8a3;border-radius:8px;padding:10px;font-size:10.5px;margin-top:10px}}
.contact{{margin-top:20px;background:#14100e;color:#fff;border-radius:12px;padding:18px}}
.contact a{{color:#EA4E1B;text-decoration:none}}
</style></head><body>
<div class="cover"><div class="kick">Media Kit · Sponsorizzazioni</div>
<h1>Uno<span>X</span>due</h1>
<p>{c['hero_lead']}</p></div>
<h2>Chi siamo</h2>{intro_html}
<div class="stats">{stat_html}</div>
<h2>Il pubblico</h2><ul>{aud_html}</ul>
<h2>Formati disponibili</h2><ul>{fmt_html}</ul>
<h2>Pacchetti</h2><div class="pks">{rows}</div>
<div class="note">{SPONSOR_PACKAGE_NOTE}<br/>{SPONSOR_PODCAST_NOTE}</div>
<div class="contact"><b style="font-size:14px">Parliamo del tuo brand</b><br/>
Scrivici a <a href="mailto:{c['contact_email']}">{c['contact_email']}</a> · unoxdue.net/collaborazioni/</div>
</body></html>"""


# ============================ Archivi Episodi / Interviste ============================
def _archive_date(published_at):
    if not published_at:
        return ""
    try:
        d = datetime.fromisoformat(str(published_at))
        return f"{d.day} {MESI[d.month - 1]} {d.year}"
    except Exception:
        return str(published_at)


def _slug_anchor(text: str) -> str:
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^\w\s-]", "", t).strip().lower()
    return re.sub(r"[\s_-]+", "-", t)[:60] or "capitolo"


def _clean_excerpt(text: str, limit: int = 200) -> str:
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(s) <= limit:
        return s
    cut = s[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:\u2014-")
    return cut + "\u2026"


def _card_tags(ep):
    guest = (ep.get("guest_name") or "").strip().lower()

    def ok(t):
        tl = str(t).strip().lower()
        if not tl or len(str(t)) > 22:
            return False
        if "unoxdue" in tl or "intervista" in tl or "episodio" in tl or "puntata" in tl:
            return False
        if guest and (tl == guest or guest in tl or tl in guest):
            return False
        return True

    for key in ("seo_keywords", "competitions_mentioned"):
        vals = [str(x).strip() for x in (ep.get(key) or []) if ok(x)]
        if vals:
            return vals[:3]
    ents = ep.get("entities") or {}
    pool = [str(x).strip() for x in ((ents.get("competitions") or []) + (ents.get("teams") or [])) if ok(x)]
    if pool:
        return pool[:3]
    return [str(t).strip() for t in (ep.get("topics") or []) if ok(t)][:3]


def _content_card(ep, section):
    yid = ep.get("youtube_id") or ""
    thumb = ep.get("thumbnail") or (f"https://img.youtube.com/vi/{yid}/maxresdefault.jpg" if yid else f"{SITE_URL}/logo.jpg")
    fallback = f"https://img.youtube.com/vi/{yid}/hqdefault.jpg" if yid else f"{SITE_URL}/logo.jpg"
    raw = ep.get("archive_excerpt")
    if not raw:
        summ = ep.get("summary") or []
        raw = ep.get("excerpt") or (summ[0] if summ else "") or ep.get("meta_description") or ""
    return {
        "url": f'{SITE_URL}/{section}/{ep.get("slug")}/',
        "thumb": thumb, "thumb_fallback": fallback,
        "title": ep.get("website_title") or ep.get("title") or "",
        "date": _archive_date(ep.get("published_at")),
        "duration": ep.get("duration") or "",
        "excerpt": _clean_excerpt(raw, 200),
        "guest": ep.get("guest_name") or "",
        "role": ep.get("guest_role") or "",
        "tags": _card_tags(ep),
    }


def _archive_collection_jsonld(page_title, page_desc, canonical, cards):
    item_list = [{"@type": "ListItem", "position": i + 1, "url": c["url"], "name": c["title"]}
                 for i, c in enumerate(cards) if c.get("url")]
    return json.dumps({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": page_title, "description": page_desc, "url": canonical, "inLanguage": "it",
        "isPartOf": {"@type": "WebSite", "@id": f"{SITE_URL}/#website"},
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(item_list), "itemListElement": item_list},
    }, ensure_ascii=False, indent=2)


def _faq_jsonld(faqs):
    if not faqs:
        return None
    return json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": f["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faqs],
    }, ensure_ascii=False, indent=2)


# Testi editoriali unici per gli archivi (niente duplicazioni con la home)
EPISODI_INTRO = [
    "Gli episodi di UnoXdue sono il cuore del progetto: ogni settimana il team analizza la giornata di "
    "Serie A partendo dalle partite e arrivando ai temi caldi del campionato, tra letture tattiche, "
    "momenti di forma, scelte degli allenatori e calendario. Le puntate nascono in diretta su Twitch e "
    "restano poi disponibili, complete, su YouTube e qui in archivio.",
    "In questa sezione trovi tutte le puntate in ordine cronologico, con titolo, sommario e capitoli per "
    "raggiungere subito i momenti chiave. Dove disponibile, ogni episodio ha una trascrizione testuale "
    "navigabile, pensata per chi preferisce leggere o cercare un passaggio specifico.",
]
EPISODI_FAQS = [
    {"q": "Ogni quanto esce un nuovo episodio?",
     "a": "Pubblichiamo nuove puntate con cadenza settimanale, in concomitanza con le giornate di Serie A: prima la diretta su Twitch, poi l'episodio completo su YouTube e in archivio sul sito."},
    {"q": "Gli episodi hanno la trascrizione?",
     "a": "Quando è disponibile una fonte reale (sottotitoli o audio), pubblichiamo una trascrizione testuale navigabile, divisa in capitoli con collegamento al minuto esatto del video. Non inventiamo mai citazioni o minutaggi."},
    {"q": "Dove posso vedere gli episodi completi?",
     "a": "Tutte le puntate integrali sono sul canale YouTube @unoXdue; dal sito puoi aprire ogni episodio con sommario, capitoli ed eventuale trascrizione."},
]
INTERVISTE_INTRO = [
    "Le interviste di UnoXdue danno voce ai protagonisti del calcio italiano: calciatori, allenatori e "
    "addetti ai lavori che si raccontano senza fretta, in conversazioni lunghe e curate. Niente domande "
    "di circostanza: spazio alle storie, alle carriere e ai ricordi che hanno fatto la differenza.",
    "In questa sezione raccogliamo tutte le interviste pubblicate, con sommario e capitoli per orientarti "
    "nel racconto. Dove disponibile, ogni intervista è accompagnata da una trascrizione testuale, utile "
    "per rileggere i passaggi più significativi.",
]
INTERVISTE_FAQS = [
    {"q": "Chi sono gli ospiti delle interviste?",
     "a": "Protagonisti del calcio italiano: ex calciatori, allenatori e personalità legate alla Serie A e ai campionati che raccontiamo nel podcast."},
    {"q": "Come posso proporre un'intervista?",
     "a": "Puoi scriverci dalla pagina Contatti o sui nostri canali social. Per collaborazioni editoriali trovi i dettagli nella pagina Collaborazioni."},
]
PRESS_INTRO = [
    "«Parlano di noi» raccoglie le menzioni reali di UnoXdue e dei suoi protagonisti sulla stampa e sui "
    "media online. Selezioniamo solo articoli verificati, riconducibili a testate identificabili, e ne "
    "salviamo titolo, fonte e data insieme al logo dell'editore.",
    "Ogni segnalazione rimanda all'articolo originale: non riproduciamo i testi integrali, ma offriamo un "
    "punto di accesso ordinato a ciò che è stato scritto sul podcast e sulle persone che lo animano.",
]


def render_episodi_archive(items) -> str:
    cards = [_content_card(e, "episodi") for e in items]
    canonical = f"{SITE_URL}/episodi/"
    page_title = "Episodi"
    page_desc = ("Tutti gli episodi del podcast UnoXdue dedicati alla Serie A: analisi delle partite, "
                 "tattica e racconto di ogni giornata, con dirette su Twitch e puntate complete su YouTube.")
    bc = breadcrumb_jsonld([("Home", f"{SITE_URL}/"), (page_title, canonical)])
    jsonld = _archive_collection_jsonld(page_title, page_desc, canonical, cards)
    faq_jsonld = _faq_jsonld(EPISODI_FAQS)
    return env.get_template("episodi_archive.html").render(
        page_title=page_title, page_desc=page_desc, canonical=canonical, site_url=SITE_URL,
        cards=cards, intro=EPISODI_INTRO, faqs=EPISODI_FAQS,
        breadcrumb_jsonld=bc, jsonld=jsonld, faq_jsonld=faq_jsonld, year=_year())


def render_interviste_archive(items) -> str:
    cards = [_content_card(e, "interviste") for e in items]
    canonical = f"{SITE_URL}/interviste/"
    page_title = "Interviste"
    page_desc = ("Le interviste esclusive di UnoXdue ai protagonisti del calcio italiano: storie, carriere "
                 "e ricordi raccontati senza filtri.")
    bc = breadcrumb_jsonld([("Home", f"{SITE_URL}/"), (page_title, canonical)])
    jsonld = _archive_collection_jsonld(page_title, page_desc, canonical, cards)
    faq_jsonld = _faq_jsonld(INTERVISTE_FAQS)
    return env.get_template("interviste_archive.html").render(
        page_title=page_title, page_desc=page_desc, canonical=canonical, site_url=SITE_URL,
        cards=cards, intro=INTERVISTE_INTRO, faqs=INTERVISTE_FAQS,
        breadcrumb_jsonld=bc, jsonld=jsonld, faq_jsonld=faq_jsonld, year=_year())
