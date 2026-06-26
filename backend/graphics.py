"""Step 5 — Generazione automatica delle grafiche dei pronostici.

Pipeline approvata: HTML/CSS/SVG controllato -> Playwright/Chromium headless -> PNG + WebP.
- Nessun generatore AI per partite/mercati/quote: si rende SOLO ciò che è nei dati.
- 3 formati: orizzontale (1200x630), quadrato (1080x1080), verticale 9:16 (1080x1920).
- Font e immagini locali, embeddati in base64 -> rendering deterministico, niente attese di rete.
- Una sola istanza Chromium riusata (avvio/riuso/chiusura gestiti), con timeout e retry.
- QR verso la pagina del pronostico (se disponibile) o /live/.
- Vietati: importo, bonus, vincita, saldo, ID schedina, dati personali, branding operatore, quote inventate.
"""
import asyncio
import base64
import io
import os
import re
from pathlib import Path

# In ambiente Emergent i browser Playwright sono in /pw-browsers; in Docker si usa il default.
if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/pw-browsers"):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/pw-browsers"

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image

from config_db import db, SITE_URL, ROOT_DIR, UPLOAD_DIR

STATIC = ROOT_DIR / "static"
PUBLIC = STATIC / "public"          # asset brand committati (logo, foto)
FONTS = STATIC / "fonts"
GRAPHICS_DIR = UPLOAD_DIR / "graphics"
GRAPHICS_DIR.mkdir(parents=True, exist_ok=True)

FORMATS = {
    "horizontal": (1200, 630),
    "square": (1080, 1080),
    "vertical": (1080, 1920),
}

# ----------------------------- asset embedding -----------------------------
_font_css_cache = None
_img_cache = {}


def _font_b64(fname: str) -> str:
    return base64.b64encode((FONTS / fname).read_bytes()).decode()


def _fonts_css() -> str:
    global _font_css_cache
    if _font_css_cache:
        return _font_css_cache
    faces = [
        ("Anton", 400, "anton-400.woff2"),
        ("Archivo", 700, "archivo-700.woff2"),
        ("Archivo", 800, "archivo-800.woff2"),
        ("Inter", 400, "inter-400.woff2"),
        ("Inter", 600, "inter-600.woff2"),
        ("Inter", 700, "inter-700.woff2"),
    ]
    out = []
    for fam, w, f in faces:
        try:
            b = _font_b64(f)
            out.append(
                f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{w};"
                f"font-display:block;src:url(data:font/woff2;base64,{b}) format('woff2');}}"
            )
        except Exception:
            pass
    _font_css_cache = "".join(out)
    return _font_css_cache


async def _embed_image(path: str):
    """Ritorna un data URI base64 dell'immagine, o None. Risolve locale -> http."""
    if not path:
        return None
    if path in _img_cache:
        return _img_cache[path]
    data = None
    if path.startswith("http"):
        data = await _fetch(path)
    else:
        local = PUBLIC / path.lstrip("/")
        if local.exists():
            data = local.read_bytes()
        else:
            data = await _fetch(f"{SITE_URL}{path}")
    if not data:
        _img_cache[path] = None
        return None
    mime = "image/png" if data[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    uri = f"data:{mime};base64,{base64.b64encode(data).decode()}"
    _img_cache[path] = uri
    return uri


async def _fetch(url: str):
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(url)
            if r.status_code == 200:
                return r.content
    except Exception:
        pass
    return None


def _qr_data_uri(url: str) -> str:
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#14100e", back_color="#ffffff").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _slugify(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "tipster"


def _esc(s) -> str:
    return (str(s or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ----------------------------- HTML build -----------------------------
async def build_html(pred: dict, pick: dict, fmt: str, photo_uri, logo_uri, qr_uri, qr_label: str) -> str:
    w, h = FORMATS[fmt]
    sels = pick.get("selections", []) or []
    n = len(sels)
    season = pred.get("season", "")
    rnd = pred.get("round", "")
    updated = pred.get("updated_at", "")
    tipster = pick.get("tipster", "Tipster")
    ptype = pick.get("type", "Multipla")
    total = (pick.get("total_odds") or "").strip()

    # scala tipografica per formato e numero selezioni
    vertical = fmt == "vertical"
    big = fmt != "horizontal"
    name_sz = 64 if big else 46
    h1_sz = 40 if big else 30
    base_match = (40 if vertical else 34 if fmt == "square" else 26)
    base_meta = (24 if vertical else 21 if fmt == "square" else 16)
    base_odds = (36 if vertical else 31 if fmt == "square" else 24)
    if n >= 5:
        base_match = int(base_match * 0.78); base_meta = int(base_meta * 0.82); base_odds = int(base_odds * 0.82)
    elif n == 4:
        base_match = int(base_match * 0.9); base_meta = int(base_meta * 0.92); base_odds = int(base_odds * 0.9)

    rows = []
    for s in sels:
        odds = (s.get("odds") or "").strip()
        odds_html = (f'<span class="odds">{_esc(odds)}</span>' if odds
                     else '<span class="odds na">Quota non disponibile</span>')
        rows.append(
            '<div class="sel">'
            f'<div class="sel-l"><div class="meta">{_esc(s.get("competition",""))} &middot; {_esc(s.get("date",""))}</div>'
            f'<div class="match">{_esc(s.get("match",""))}</div>'
            f'<div class="pickrow"><span class="mk">{_esc(s.get("market",""))}</span>'
            f'<span class="pk">{_esc(s.get("pick",""))}</span></div></div>'
            f'<div class="sel-r">{odds_html}</div></div>'
        )
    rows_html = "".join(rows)

    total_html = (f'<span class="tval">{_esc(total)}</span>' if total
                  else '<span class="tval na">Non disponibile</span>')

    photo_html = (f'<img class="ava" src="{photo_uri}" alt="" />' if photo_uri
                  else f'<div class="ava ava-fb">{_esc(tipster[:1].upper())}</div>')

    pad = 64 if vertical else 52 if fmt == "square" else 40

    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
{_fonts_css()}
#card{{position:relative;width:{w}px;height:{h}px;overflow:hidden;background:#14100e;color:#fff;
  font-family:'Inter',sans-serif;padding:{pad}px;display:flex;flex-direction:column;
  align-items:center;justify-content:center}}
#inner{{position:relative;z-index:2;width:100%;display:flex;flex-direction:column;gap:{int(pad*0.45)}px}}
#card::before{{content:"";position:absolute;top:-160px;right:-120px;width:560px;height:560px;border-radius:50%;
  background:radial-gradient(closest-side,rgba(234,78,27,.35),transparent)}}
#card::after{{content:"UNOXDUE";position:absolute;bottom:-30px;left:-10px;font-family:'Anton';
  font-size:{int(w/4)}px;color:rgba(255,255,255,.035);letter-spacing:.04em;white-space:nowrap}}
.top{{position:relative;display:flex;align-items:center;justify-content:space-between;z-index:2}}
.brand{{display:flex;align-items:center;gap:16px}}
.brand img{{width:{72 if big else 54}px;height:{72 if big else 54}px;border-radius:50%;object-fit:cover;
  box-shadow:0 0 0 3px rgba(234,78,27,.55)}}
.brand .wm{{font-family:'Anton';font-size:{h1_sz+6}px;letter-spacing:.02em}}
.brand .wm b{{color:#EA4E1B;font-weight:400}}
.head-r{{text-align:right}}
.head-r .lg{{font-family:'Archivo';font-weight:800;text-transform:uppercase;letter-spacing:.12em;
  color:#EA4E1B;font-size:{base_meta+4}px}}
.head-r .sub{{color:rgba(255,255,255,.7);font-size:{base_meta}px;margin-top:4px;font-weight:600}}
.tip{{position:relative;z-index:2;display:flex;align-items:center;gap:20px}}
.ava{{width:{96 if big else 70}px;height:{96 if big else 70}px;border-radius:50%;object-fit:cover;object-position:top;
  box-shadow:0 0 0 4px rgba(234,78,27,.6)}}
.ava-fb{{display:flex;align-items:center;justify-content:center;background:#EA4E1B;font-family:'Anton';font-size:{name_sz*0.6}px}}
.tip .nm{{font-family:'Archivo';font-weight:800;font-size:{name_sz}px;line-height:1}}
.tip .ty{{color:#EA4E1B;font-weight:700;text-transform:uppercase;letter-spacing:.08em;font-size:{base_meta}px;margin-top:6px}}
.list{{position:relative;z-index:2;display:flex;flex-direction:column;
  gap:{(14 if vertical else 8)}px}}
.sel{{display:flex;align-items:center;justify-content:space-between;gap:18px;
  background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:18px;
  padding:{(20 if vertical else 14)}px {(24 if big else 18)}px}}
.sel-l{{min-width:0}}
.meta{{color:rgba(255,255,255,.55);font-size:{base_meta}px;font-weight:600;text-transform:uppercase;letter-spacing:.04em}}
.match{{font-family:'Archivo';font-weight:800;font-size:{base_match}px;margin-top:4px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:{int(w-pad*2-220)}px}}
.pickrow{{display:flex;align-items:center;gap:12px;margin-top:6px}}
.mk{{color:rgba(255,255,255,.75);font-size:{base_meta+2}px;max-width:{int((w-pad*2)*0.5)}px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.pk{{color:#fff;font-weight:700;font-size:{base_meta+2}px}}
.odds{{display:inline-block;background:#EA4E1B;color:#fff;font-weight:800;font-size:{base_odds}px;
  padding:6px 16px;border-radius:12px;font-variant-numeric:tabular-nums}}
.odds.na{{background:rgba(255,255,255,.12);font-size:{max(13,base_meta-2)}px;font-weight:700;
  white-space:normal;text-align:center;max-width:220px;line-height:1.15}}
.total{{position:relative;z-index:2;display:flex;align-items:center;justify-content:space-between;
  background:#fff;color:#14100e;border-radius:18px;padding:{(20 if vertical else 14)}px {(28 if big else 20)}px}}
.total .tl{{font-family:'Archivo';font-weight:800;text-transform:uppercase;letter-spacing:.06em;font-size:{base_meta+4}px}}
.tval{{font-family:'Anton';color:#EA4E1B;font-size:{name_sz}px;font-variant-numeric:tabular-nums}}
.tval.na{{font-size:{base_odds}px}}
.foot{{position:relative;z-index:2;display:flex;align-items:flex-end;justify-content:space-between;gap:20px}}
.qr{{display:flex;align-items:center;gap:16px}}
.qr img{{width:{132 if vertical else 104 if fmt=="square" else 88}px;height:{132 if vertical else 104 if fmt=="square" else 88}px;
  border-radius:14px;background:#fff;padding:8px}}
.qr .ql{{font-family:'Archivo';font-weight:800;text-transform:uppercase;letter-spacing:.04em;
  font-size:{base_meta}px;max-width:240px;line-height:1.2}}
.disc{{text-align:right;color:rgba(255,255,255,.55);font-size:{max(13,base_meta-3)}px;line-height:1.45;max-width:{int(w*0.5)}px}}
.disc b{{color:#fff}}
</style></head><body>
<div id="card"><div id="inner">
  <div class="top">
    <div class="brand">{f'<img src="{logo_uri}" alt="">' if logo_uri else ''}<div class="wm">Uno<b>X</b>due</div></div>
    <div class="head-r"><div class="lg">{_esc(pred.get('competition','Serie A'))}</div>
      <div class="sub">{_esc(season)} &middot; {_esc(rnd)}ª giornata</div></div>
  </div>
  <div class="tip">{photo_html}<div><div class="nm">{_esc(tipster)}</div>
    <div class="ty">{_esc(ptype)} ({n})</div></div></div>
  <div class="list">{rows_html}</div>
  <div class="total"><span class="tl">Quota totale</span>{total_html}</div>
  <div class="foot">
    <div class="qr">{f'<img src="{qr_uri}" alt="QR">' if qr_uri else ''}<div class="ql">{_esc(qr_label)}</div></div>
    <div class="disc"><b>18+ &middot; Gioca responsabilmente.</b><br>Quote rilevate dalla grafica comparativa fornita dal team al momento della pubblicazione. Le quote possono variare.{(' &middot; Agg. ' + _esc(updated)) if updated else ''}</div>
  </div>
</div></div></body></html>"""


# ----------------------------- Chromium (istanza riusata) -----------------------------
_pw = None
_browser = None
_block = asyncio.Lock()


async def _get_browser():
    global _pw, _browser
    async with _block:
        if _browser is None or not _browser.is_connected():
            if _pw is None:
                from playwright.async_api import async_playwright
                _pw = await async_playwright().start()
            _browser = await _pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
    return _browser


async def shutdown_browser():
    global _pw, _browser
    try:
        if _browser:
            await _browser.close()
    except Exception:
        pass
    try:
        if _pw:
            await _pw.stop()
    except Exception:
        pass
    _browser = None
    _pw = None


async def _render_png(html: str, w: int, h: int) -> bytes:
    browser = await _get_browser()
    ctx = await browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2)
    try:
        page = await ctx.new_page()
        await page.set_content(html, wait_until="networkidle")
        try:
            await page.evaluate("document.fonts.ready")
        except Exception:
            pass
        # Anti-taglio: se il contenuto eccede l'altezza della card, riduce la scala
        await page.evaluate("""() => {
            const card = document.querySelector('#card');
            const inner = document.querySelector('#inner');
            if (!card || !inner) return;
            const cs = getComputedStyle(card);
            const avail = card.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
            const nat = inner.offsetHeight;
            if (nat > avail) {
                inner.style.transformOrigin = 'center top';
                inner.style.transform = 'scale(' + (avail / nat) + ')';
                card.style.justifyContent = 'flex-start';
            }
        }""")
        await page.wait_for_timeout(60)
        el = await page.query_selector("#card")
        png = await el.screenshot(type="png") if el else await page.screenshot()
        return png
    finally:
        await ctx.close()


def _png_to_webp(png: bytes) -> bytes:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=88, method=6)
    return buf.getvalue()


# ----------------------------- generazione -----------------------------
async def _resolve_photo(tipster: str):
    member = await db.team.find_one({"name": tipster}, {"_id": 0, "photo": 1})
    if member and member.get("photo"):
        return await _embed_image(member["photo"])
    return None


async def generate_pick(season: str, round_: int, pick_index: int) -> dict:
    pred = await db.predictions.find_one({"season": season, "round": round_})
    if not pred:
        return {"ok": False, "error": "Pronostico non trovato."}
    picks = pred.get("picks", [])
    if pick_index < 0 or pick_index >= len(picks):
        return {"ok": False, "error": "Indice giocata non valido."}
    pick = picks[pick_index]

    # QR: pagina del pronostico se disponibile, altrimenti /live/
    pred_url = f"{SITE_URL}/pronostici/serie-a/{season}/giornata-{round_}/"
    qr_url = pred_url
    qr_label = "Inquadra · apri i pronostici"
    qr_uri = _qr_data_uri(qr_url)

    logo_uri = await _embed_image("/logo.jpg")
    photo_uri = await _resolve_photo(pick.get("tipster", ""))

    tslug = _slugify(pick.get("tipster", ""))
    out_dir = GRAPHICS_DIR / season / str(round_) / tslug
    out_dir.mkdir(parents=True, exist_ok=True)

    formats_out = {}
    errors = {}
    for fmt, (w, h) in FORMATS.items():
        last_err = None
        for attempt in range(2):  # 1 retry
            try:
                html = await build_html(pred, pick, fmt, photo_uri, logo_uri, qr_uri, qr_label)
                png = await asyncio.wait_for(_render_png(html, w, h), timeout=30)
                webp = _png_to_webp(png)
                (out_dir / f"{fmt}.png").write_bytes(png)
                (out_dir / f"{fmt}.webp").write_bytes(webp)
                rel = f"/api/uploads/graphics/{season}/{round_}/{tslug}/{fmt}"
                formats_out[fmt] = {"png": f"{SITE_URL}{rel}.png", "webp": f"{SITE_URL}{rel}.webp",
                                    "w": w, "h": h}
                last_err = None
                break
            except Exception as e:
                last_err = str(e)
        if last_err:
            errors[fmt] = last_err

    import automations as auto
    from datetime import datetime, timezone
    gen = {"formats": formats_out, "errors": errors,
           "generated_at": datetime.now(timezone.utc).isoformat(),
           "qr_url": qr_url}
    picks[pick_index]["graphics"] = gen
    await db.predictions.update_one({"season": season, "round": round_}, {"$set": {"picks": picks}})
    status = "ok" if formats_out and not errors else ("warning" if formats_out else "error")
    await auto.log_automation("graphics", status,
                              f"Grafiche {pick.get('tipster','')} (giornata {round_}): {len(formats_out)}/3 formati"
                              + (f", errori: {list(errors)}" if errors else ""),
                              {"season": season, "round": round_, "pick": pick_index})
    return {"ok": bool(formats_out), "graphics": gen, "errors": errors}



# ============================================================
# COPERTINE PRONOSTICI (artefatto distinto dalle schedine)
# Solo: logo UnoXdue, "Pronostici Serie A", stagione, giornata, sfondo nero/arancione,
# elementi tattici discreti. Nessun dato di giocata, nessun bookmaker. WebP 1200x675 + 1200x1200.
# ============================================================
COVER_FORMATS = {"horizontal": (1200, 675), "square": (1200, 1200)}
COVERS_DIR = UPLOAD_DIR / "covers"
COVERS_DIR.mkdir(parents=True, exist_ok=True)


def _season_short(season: str) -> str:
    parts = (season or "").split("-")
    if len(parts) == 2 and len(parts[1]) == 4:
        return f"{parts[0]}/{parts[1][2:]}"
    return season or ""


def _pitch_svg() -> str:
    # Campo + lavagna tattica discreti (slice a coprire la card di qualsiasi formato).
    return (
        '<svg class="pitch" viewBox="0 0 1200 760" preserveAspectRatio="xMidYMid slice" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<g fill="none" stroke="rgba(246,217,191,0.08)" stroke-width="3">'
        '<rect x="70" y="80" width="1060" height="600" rx="8"/>'
        '<line x1="600" y1="80" x2="600" y2="680"/>'
        '<circle cx="600" cy="380" r="120"/>'
        '<rect x="70" y="230" width="150" height="300"/>'
        '<rect x="980" y="230" width="150" height="300"/>'
        '<rect x="70" y="305" width="55" height="150"/>'
        '<rect x="1075" y="305" width="55" height="150"/>'
        '</g>'
        '<circle cx="600" cy="380" r="7" fill="rgba(246,217,191,0.12)"/>'
        '<g fill="none" stroke="rgba(234,78,27,0.22)" stroke-width="3" stroke-dasharray="9 12" stroke-linecap="round">'
        '<path d="M250 600 C 450 460, 520 400, 720 280"/>'
        '<path d="M320 180 C 540 290, 660 380, 880 500"/>'
        '</g></svg>'
    )


async def build_cover_html(pred: dict, w: int, h: int, logo_uri) -> str:
    season_s = _season_short(pred.get("season", ""))
    rnd = pred.get("round", "")
    comp = pred.get("competition", "Serie A")
    date = (pred.get("date") or "").strip()
    big = h >= 1000  # quadrato
    logo_sz = 160 if big else 120
    wm_sz = 58 if big else 50
    label_sz = 36 if big else 30
    title_sz = 104 if big else 92
    sub_sz = 34 if big else 28
    gap = 26 if big else 18
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
{_fonts_css()}
#card{{position:relative;width:{w}px;height:{h}px;overflow:hidden;background:#14100e;color:#fff;
  font-family:'Inter',sans-serif;display:flex;align-items:center;justify-content:center;text-align:center}}
.pitch{{position:absolute;inset:0;width:100%;height:100%;z-index:1}}
#card::before{{content:"";position:absolute;top:-180px;right:-120px;width:640px;height:640px;border-radius:50%;
  background:radial-gradient(closest-side,rgba(234,78,27,.42),transparent);z-index:1}}
#card::after{{content:"UNOXDUE";position:absolute;bottom:-26px;left:-12px;font-family:'Anton';
  font-size:{int(w/4.2)}px;color:rgba(255,255,255,.04);letter-spacing:.04em;white-space:nowrap;z-index:1}}
#inner{{position:relative;z-index:3;display:flex;flex-direction:column;align-items:center;gap:{gap}px;padding:{int(h*0.08)}px}}
.logo{{width:{logo_sz}px;height:{logo_sz}px;border-radius:50%;object-fit:cover;
  box-shadow:0 0 0 4px rgba(234,78,27,.6),0 18px 60px rgba(0,0,0,.5)}}
.wm{{font-family:'Anton';font-size:{wm_sz}px;letter-spacing:.02em;line-height:1}}
.wm b{{color:#EA4E1B;font-weight:400}}
.label{{font-family:'Archivo';font-weight:800;text-transform:uppercase;letter-spacing:.28em;
  color:#EA4E1B;font-size:{label_sz}px;margin-top:{int(gap*0.4)}px}}
.title{{font-family:'Anton';font-size:{title_sz}px;line-height:.94;letter-spacing:.01em}}
.title .gw{{color:#EA4E1B}}
.sub{{display:inline-flex;align-items:center;gap:14px;color:#F6D9BF;font-weight:700;
  text-transform:uppercase;letter-spacing:.12em;font-size:{sub_sz}px}}
.sub .dot{{width:7px;height:7px;border-radius:50%;background:#EA4E1B;display:inline-block}}
</style></head><body>
<div id="card">
  {_pitch_svg()}
  <div id="inner">
    {f'<img class="logo" src="{logo_uri}" alt="">' if logo_uri else ''}
    <div class="wm">Uno<b>X</b>due</div>
    <div class="label">Pronostici {_esc(comp)}</div>
    <div class="title">{_esc(season_s)}<br><span class="gw">{_esc(rnd)}ª GIORNATA</span></div>
    <div class="sub"><span>{_esc(season_s)}</span>{f'<span class="dot"></span><span>{_esc(date)}</span>' if date else ''}</div>
  </div>
</div></body></html>"""


async def generate_cover(season: str, round_: int) -> dict:
    pred = await db.predictions.find_one({"season": season, "round": round_})
    if not pred:
        return {"ok": False, "error": "Pronostico non trovato."}
    logo_uri = await _embed_image("/logo.jpg")
    out_dir = COVERS_DIR / season / str(round_)
    out_dir.mkdir(parents=True, exist_ok=True)
    cover, errors = {}, {}
    for fmt, (w, h) in COVER_FORMATS.items():
        last_err = None
        for _ in range(2):
            try:
                html = await build_cover_html(pred, w, h, logo_uri)
                png = await asyncio.wait_for(_render_png(html, w, h), timeout=30)
                webp = _png_to_webp(png)
                (out_dir / f"{fmt}.webp").write_bytes(webp)
                rel = f"/api/uploads/covers/{season}/{round_}/{fmt}.webp"
                cover[fmt] = {"url": f"{SITE_URL}{rel}", "w": w, "h": h}
                last_err = None
                break
            except Exception as e:
                last_err = str(e)
        if last_err:
            errors[fmt] = last_err
    from datetime import datetime, timezone
    cover["alt"] = f"Pronostici {pred.get('competition','Serie A')} {_season_short(season)} {round_}ª giornata — UnoXdue"
    cover["generated_at"] = datetime.now(timezone.utc).isoformat()
    await db.predictions.update_one({"season": season, "round": round_}, {"$set": {"cover": cover}})
    import automations as auto
    status = "ok" if cover.get("horizontal") else "error"
    await auto.log_automation("cover", status,
                              f"Copertine giornata {round_} ({season}): {len([k for k in cover if k in COVER_FORMATS])}/2 formati"
                              + (f", errori: {list(errors)}" if errors else ""),
                              {"season": season, "round": round_})
    return {"ok": bool(cover.get("horizontal")), "cover": cover, "errors": errors}