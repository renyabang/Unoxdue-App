"""Controllo finale pre-pubblicazione sugli 8 contenuti approvati, pubblicazione
(solo se 0 errori bloccanti) e smoke test pubblico. Niente token nei log."""
import asyncio, sys, json, re, urllib.request
sys.path.insert(0, '/app/backend')
import srt_utils as su

APPROVED = ["Ceravolo", "Baclet", r"Primo [Aa]ppuntamento", r"Sesto appuntamento",
            r"Secondo [Aa]ppuntamento", r"Ottavo appuntamento", r"Quinto appuntamento",
            r"Decimo appuntamento"]
BASE = "http://localhost:8001"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        r = urllib.request.urlopen(req, timeout=20)
        return r.getcode(), r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, str(e)


async def main():
    from config_db import db
    import ai_transcript as ait
    import seo

    # risolvi gli 8 slug
    targets = []
    for pat in APPROVED:
        e = await db.episodes.find_one({"title": {"$regex": pat}}, {"_id": 0, "slug": 1, "title": 1, "type": 1})
        if e:
            targets.append(e)
        else:
            print("NON TROVATO:", pat)
    print(f"Risolti {len(targets)} contenuti.\n")

    # ===== CONTROLLO FINALE =====
    blocking = {}
    h1s, titles, metas, slugs = {}, {}, {}, {}
    for e in targets:
        slug = e["slug"]
        full = await db.episodes.find_one({"slug": slug})
        p = full.get("ai_preview")
        b = await db.transcriptions.find_one({"slug": slug}, {"_id": 0, "segments": 1, "clean": 1})
        seg_times = {s["start_hms"] for s in (b.get("segments") or [])}
        clean = b.get("clean", "")
        errs = []
        if not p:
            errs.append("anteprima mancante"); blocking[slug] = errs; continue
        # gerarchia
        secs = p["summary_sections"]; last_h2 = False
        for i, s in enumerate(secs):
            if s["level"] == 3 and (i == 0 or not last_h2): errs.append("gerarchia H2/H3")
            if not s["heading"].strip(): errs.append("heading vuoto")
            last_h2 = s["level"] == 2
        heads = [s["heading"].lower() for s in secs]
        if len(heads) != len(set(heads)): errs.append("heading duplicati")
        # timestamp reali
        if [c for c in p["chapters"] if c["time"] not in seg_times]: errs.append("timestamp non reali")
        # citazioni verbatim
        if [q for q in p["quotes"] if not su.quote_in_transcript(q["text"], clean, 6)]: errs.append("citazione non verbatim")
        # JSON-LD valido
        ep_en = seo.enrich({**full, **{k: p[k] for k in ("h1", "seo_title", "meta_description", "excerpt", "summary_sections", "summary", "toc", "chapters", "quotes", "topics", "entities")}, "has_transcript_page": True})
        try:
            json.loads(seo.episode_jsonld(ep_en))
        except Exception as ex:
            errs.append(f"JSON-LD non valido: {ex}")
        h1s.setdefault(p["h1"], []).append(slug)
        titles.setdefault(p["seo_title"], []).append(slug)
        metas.setdefault(p["meta_description"], []).append(slug)
        slugs.setdefault(slug, []).append(slug)
        if errs:
            blocking[slug] = errs
    # duplicazioni SEO tra gli 8
    for label, d in [("H1", h1s), ("SEO title", titles), ("meta", metas)]:
        for v, ss in d.items():
            if len(ss) > 1:
                for s in ss:
                    blocking.setdefault(s, []).append(f"{label} duplicato")

    print("=== CONTROLLO FINALE ===")
    if blocking:
        print("ERRORI BLOCCANTI:", json.dumps(blocking, ensure_ascii=False, indent=2))
        print("\nPubblicazione ANNULLATA.")
        return
    print("Nessun errore bloccante. Procedo alla pubblicazione.\n")

    # ===== PUBBLICAZIONE =====
    published = []
    for e in targets:
        r = await ait.publish_preview(e["slug"])
        published.append((e["slug"], e["type"], r.get("ok")))
        print(f"  pubblicato {e['slug'][:45]} -> {r.get('ok')}")

    # ===== SMOKE TEST PUBBLICO =====
    print("\n=== SMOKE TEST PUBBLICO ===")
    sc, sitemap = fetch(f"{BASE}/api/sitemap.xml")
    print(f"sitemap.xml HTTP {sc}, {sitemap.count('<loc>')} url")
    vc, vsm = fetch(f"{BASE}/api/video-sitemap.xml")
    print(f"video-sitemap.xml HTTP {vc}, {vsm.count('<video:video>')} video")
    smoke = []
    for e in targets:
        sec = "interviste" if e["type"] == "intervista" else "episodi"
        ep_url = f"{BASE}/api/seo/{sec}/{e['slug']}"
        tr_url = f"{ep_url}/trascrizione"
        code, html = fetch(ep_url)
        tcode, _ = fetch(tr_url)
        in_sitemap = f"/{sec}/{e['slug']}/" in sitemap
        tr_in_sitemap = f"/{sec}/{e['slug']}/trascrizione/" in sitemap
        has_canonical = 'rel="canonical"' in html
        has_summary = 'episode-summary' in html
        has_h2 = '<h2 id=' in html
        smoke.append({"slug": e["slug"], "ep_http": code, "tr_http": tcode,
                      "in_sitemap": in_sitemap, "tr_in_sitemap": tr_in_sitemap,
                      "canonical": has_canonical, "summary_sections": has_summary, "h2": has_h2})
        print(f"  {e['slug'][:42]:42} ep={code} tr={tcode} sitemap={in_sitemap} tr_sm={tr_in_sitemap} canon={has_canonical} H2={has_h2}")

    # ===== verifica che i NON pubblicati non abbiano pagina trascrizione =====
    print("\n=== CONTENUTI IN REVISIONE: pagina trascrizione NON pubblica ===")
    pub_slugs = {e["slug"] for e in targets}
    async for e in db.episodes.find({"transcription_status": "done"}, {"_id": 0, "slug": 1, "type": 1}):
        if e["slug"] in pub_slugs:
            continue
        sec = "interviste" if e["type"] == "intervista" else "episodi"
        tcode, _ = fetch(f"{BASE}/api/seo/{sec}/{e['slug']}/trascrizione")
        print(f"  {e['slug'][:42]:42} trascrizione HTTP {tcode} (atteso 404)")

    open('/app/scripts/publish_smoke.json', 'w').write(json.dumps({"published": published, "smoke": smoke}, ensure_ascii=False, indent=2))
    print("\nScritto /app/scripts/publish_smoke.json")


if __name__ == "__main__":
    asyncio.run(main())
