"""Rendering SSR (HTML completo) per le pagine pubbliche. URL pulite nei canonical."""
import json
from datetime import datetime
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

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def _year():
    return datetime.now().year


def enrich(ep: dict) -> dict:
    ep = dict(ep)
    ep.pop("_id", None)
    ep.setdefault("type", "episodio")
    ep["type_label"] = ep.get("type_label") or ("Intervista" if ep["type"] == "intervista" else "Episodio")
    ep["section"] = ep.get("section") or ("interviste" if ep["type"] == "intervista" else "episodi")
    ep["section_label"] = ep.get("section_label") or ("Interviste" if ep["type"] == "intervista" else "Episodi")
    ep["h1"] = ep.get("h1") or ep.get("title", "")
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
    for k in ("summary", "topics", "chapters", "quotes", "participants", "related"):
        ep.setdefault(k, [])
    return ep


def episode_jsonld(ep: dict) -> str:
    canonical = f'{SITE_URL}/{ep["section"]}/{ep["slug"]}/'
    schema_type = "PodcastEpisode" if ep["type"] != "intervista" else "VideoObject"
    data = {
        "@context": "https://schema.org", "@type": schema_type,
        "name": ep["h1"], "description": ep["meta_description"], "url": canonical,
        "datePublished": ep.get("published_at"), "uploadDate": ep.get("published_at"),
        "thumbnailUrl": ep.get("thumbnail"), "inLanguage": "it",
        "embedUrl": f'https://www.youtube.com/embed/{ep.get("youtube_id", "")}',
        "contentUrl": f'https://www.youtube.com/watch?v={ep.get("youtube_id", "")}',
        "publisher": {"@type": "Organization", "name": "UnoXdue", "logo": f"{SITE_URL}/logo.jpg"},
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


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
        (ep["title"], canonical),
    ])
    return env.get_template("episode.html").render(
        ep=ep, canonical=canonical, site_url=SITE_URL,
        jsonld=episode_jsonld(ep), breadcrumb_jsonld=bc, year=_year(),
        press=press or [],
    )


def render_archive(page_title, page_desc, canonical_path, items, show_play=False) -> str:
    canonical = f"{SITE_URL}{canonical_path}"
    bc = breadcrumb_jsonld([("Home", f"{SITE_URL}/"), (page_title, canonical)])
    return env.get_template("archive.html").render(
        page_title=page_title, page_desc=page_desc, canonical=canonical,
        items=items, site_url=SITE_URL, breadcrumb_jsonld=bc, year=_year(),
        show_play=show_play,
    )


def render_prediction(p: dict) -> str:
    p = dict(p); p.pop("_id", None)
    season = p.get("season"); rnd = p.get("round")
    p["h1"] = p.get("h1") or f'Pronostici {p.get("competition", "Serie A")} {season} \u2014 {rnd}a giornata'
    p["seo_title"] = p.get("seo_title") or f'{p["h1"]} | UnoXdue'
    p["meta_description"] = p.get("meta_description") or p.get("intro", p["h1"])[:160]
    p.setdefault("intro", "")
    p.setdefault("picks", [])
    canonical = f'{SITE_URL}/pronostici/serie-a/{season}/giornata-{rnd}/'
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "Article",
        "headline": p["h1"], "description": p["meta_description"], "url": canonical,
        "inLanguage": "it",
        "publisher": {"@type": "Organization", "name": "UnoXdue", "logo": f"{SITE_URL}/logo.jpg"},
    }, ensure_ascii=False, indent=2)
    bc = breadcrumb_jsonld([
        ("Home", f"{SITE_URL}/"),
        ("Pronostici", f"{SITE_URL}/pronostici/"),
        (f'{p.get("competition", "Serie A")} {season} - {rnd}a giornata', canonical),
    ])
    return env.get_template("prediction.html").render(
        p=p, canonical=canonical, site_url=SITE_URL, jsonld=jsonld,
        breadcrumb_jsonld=bc, year=_year(),
    )


def render_team_member(m: dict, related, press=None) -> str:
    m = dict(m); m.pop("_id", None)
    m["meta_description"] = (m.get("bio") or m.get("name", ""))[:160]
    photo = m.get("photo", "/logo.jpg")
    m["photo_abs"] = photo if photo.startswith("http") else f"{SITE_URL}{photo}"
    canonical = f'{SITE_URL}/team/{m["slug"]}/'
    same_as = [m["instagram"]] if m.get("instagram") else []
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "Person",
        "name": m["name"], "description": m["meta_description"], "url": canonical,
        "image": m["photo_abs"], "jobTitle": m.get("role", ""), "sameAs": same_as,
        "worksFor": {"@type": "Organization", "name": "UnoXdue"},
    }, ensure_ascii=False, indent=2)
    bc = breadcrumb_jsonld([
        ("Home", f"{SITE_URL}/"), ("Il team", f"{SITE_URL}/team/"), (m["name"], canonical),
    ])
    return env.get_template("team_member.html").render(
        m_=m, canonical=canonical, site_url=SITE_URL, jsonld=jsonld,
        breadcrumb_jsonld=bc, related=related, year=_year(), press=press or [],
    )


def render_press_archive(items) -> str:
    canonical = f"{SITE_URL}/parlano-di-noi/"
    bc = breadcrumb_jsonld([("Home", f"{SITE_URL}/"), ("Parlano di noi", canonical)])
    return env.get_template("press.html").render(
        items=items, canonical=canonical, site_url=SITE_URL,
        breadcrumb_jsonld=bc, year=_year(),
    )


def render_home(episodes, interviews) -> str:
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "PodcastSeries",
        "name": "UnoXdue", "url": f"{SITE_URL}/", "image": f"{SITE_URL}/logo.jpg",
        "inLanguage": "it", "genre": "Sport",
        "sameAs": ["https://www.twitch.tv/unoxdue_", "https://www.instagram.com/unoxdue_",
                   "https://www.youtube.com/@unoXdue", "https://www.tiktok.com/@unoxdue_"],
    }, ensure_ascii=False, indent=2)
    return env.get_template("home.html").render(
        episodes=episodes, interviews=interviews, site_url=SITE_URL,
        jsonld=jsonld, year=_year(),
    )


def render_page(page_title, page_desc, canonical_path, body_html) -> str:
    canonical = f"{SITE_URL}{canonical_path}"
    bc = breadcrumb_jsonld([("Home", f"{SITE_URL}/"), (page_title, canonical)])
    return env.get_template("page.html").render(
        page_title=page_title, page_desc=page_desc, canonical=canonical,
        body_html=body_html, site_url=SITE_URL, breadcrumb_jsonld=bc, year=_year(),
    )
