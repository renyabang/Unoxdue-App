"""Genera le anteprime SEO v2 per tutti gli episodi con trascrizione (SENZA pubblicare)
e produce un report QC automatico completo. Scrive /app/scripts/qc_report.json e .md"""
import asyncio, sys, json, re
from datetime import datetime
sys.path.insert(0, '/app/backend')
import srt_utils as su

VAGUE = ["si continua", "altre considerazioni", "considerazioni varie", "si parla di",
         "continua a parlare", "altro ancora", "varie ed eventuali"]


def words(s):
    return len((s or "").split())


def target(dur_min):
    if dur_min <= 45: return (400, 600)
    if dur_min <= 90: return (500, 750)
    return (650, 900)


async def main():
    from config_db import db
    import ai_transcript as ait

    eps = await db.episodes.find({"transcription_status": "done"},
                                 {"_id": 0, "slug": 1, "title": 1, "type": 1, "duration_seconds": 1,
                                  "h1": 1, "seo_title": 1, "meta_description": 1, "summary": 1,
                                  "transcription_seo_status": 1}).to_list(500)
    print(f"Genero anteprime per {len(eps)} contenuti...")
    live_snapshot = {e["slug"]: {"h1": e.get("h1"), "seo_title": e.get("seo_title"),
                                 "meta_description": e.get("meta_description"),
                                 "summary_words": sum(words(p) for p in (e.get("summary") or [])),
                                 "published": e.get("transcription_seo_status") == "published"} for e in eps}

    total_cost = 0.0
    total_tokens = 0
    results = []
    for e in eps:
        slug = e["slug"]
        print(f"  -> {e['title'][:50]}")
        r = await ait.generate_preview(slug)
        if not r.get("ok"):
            results.append({"slug": slug, "title": e["title"], "ok": False, "error": r.get("error")}); continue
        p = r["preview"]; m = p["meta"]
        total_cost += m["cost_estimate"]; total_tokens += m["tokens"]
        b = await db.transcriptions.find_one({"slug": slug}, {"_id": 0, "segments": 1, "clean": 1})
        seg_times = {s["start_hms"] for s in (b.get("segments") or [])}
        clean = b.get("clean", "")
        dur_min = m["duration_min"]
        lo, hi = target(dur_min)
        sections = p["summary_sections"]
        # check gerarchia
        hier_ok = True; last_h2 = False
        for i, s in enumerate(sections):
            if s["level"] == 3 and (i == 0 or not last_h2): hier_ok = False
            last_h2 = s["level"] == 2
        headings = [s["heading"].strip().lower() for s in sections]
        dup_head = len(headings) != len(set(headings))
        # capitoli
        dubious_ts = [c["time"] for c in p["chapters"] if seg_times and c["time"] not in seg_times]
        vague_ch = [c["label"] for c in p["chapters"] if any(v in c["label"].lower() for v in VAGUE)]
        # citazioni
        unsupported_q = [q["text"][:60] for q in p["quotes"] if not su.quote_in_transcript(q["text"], clean, min_words=6)]
        with_speaker = sum(1 for q in p["quotes"] if q.get("speaker"))
        # source refs
        no_src = sum(1 for s in sections if not s.get("source_segment_ids"))
        low_conf = sum(1 for s in sections if (s.get("confidence") or 1) < 0.7)
        # keyword stuffing
        sumtext = " ".join(par for s in sections for par in s["paragraphs"]).lower()
        kw = sumtext.count("unoxdue") + sumtext.count("serie a")
        h2_count = sum(1 for s in sections if s["level"] == 2)
        intro_w = m["intro_words"]; sum_w = m["summary_words"]

        flags = []
        if not (80 <= intro_w <= 150): flags.append(f"intro {intro_w}p")
        if not (lo * 0.85 <= sum_w <= hi * 1.2): flags.append(f"sommario {sum_w}p (target {lo}-{hi})")
        if not (3 <= h2_count <= 6): flags.append(f"{h2_count} H2 (target 3-6)")
        if not hier_ok: flags.append("gerarchia H2/H3 errata")
        if dup_head: flags.append("heading duplicati")
        if dubious_ts: flags.append(f"{len(dubious_ts)} timestamp dubbi")
        if vague_ch: flags.append(f"{len(vague_ch)} capitoli vaghi")
        if not (1 <= len(p["chapters"]) <= 12): flags.append(f"{len(p['chapters'])} capitoli")
        if unsupported_q: flags.append(f"{len(unsupported_q)} citazioni non supportate")
        if no_src: flags.append(f"{no_src} sezioni senza segmento sorgente")
        if low_conf: flags.append(f"{low_conf} sezioni bassa confidence")
        if kw > 8: flags.append(f"possibile keyword stuffing ({kw})")

        status = "approvato" if not flags else "da_revisionare"
        results.append({
            "slug": slug, "title": e["title"], "type": p["type"], "ok": True,
            "status": status, "flags": flags,
            "intro_words": intro_w, "summary_words": sum_w, "target": [lo, hi], "duration_min": dur_min,
            "n_sections": len(sections), "n_h2": h2_count, "hierarchy_ok": hier_ok,
            "n_chapters": len(p["chapters"]), "dubious_timestamps": dubious_ts, "vague_chapters": vague_ch,
            "n_quotes": len(p["quotes"]), "unsupported_quotes": unsupported_q, "quotes_with_speaker": with_speaker,
            "sections_no_source": no_src, "low_confidence_sections": low_conf, "kw_count": kw,
            "h1": p["h1"], "seo_title": p["seo_title"], "meta_description": p["meta_description"],
            "seo_title_len": len(p["seo_title"] or ""), "meta_len": len(p["meta_description"] or ""),
            "model": m["model"], "fallback_used": m["fallback_used"],
            "cost": m["cost_estimate"], "tokens": m["tokens"], "needs_review": m["needs_review"],
        })

    # duplicazioni SEO tra tutte le anteprime
    def dups(key):
        vals = [r[key] for r in results if r.get("ok")]
        seen = {}
        for v in vals:
            seen[v] = seen.get(v, 0) + 1
        return [v for v, c in seen.items() if c > 1 and v]
    seo_dups = {"h1": dups("h1"), "seo_title": dups("seo_title"), "meta_description": dups("meta_description")}
    slugs = [r["slug"] for r in results]
    seo_dups["slug"] = [s for s in set(slugs) if slugs.count(s) > 1]

    # diff per i 3 gia' pubblicati
    diffs = []
    for r in results:
        if r.get("ok") and live_snapshot.get(r["slug"], {}).get("published"):
            live = live_snapshot[r["slug"]]
            diffs.append({"slug": r["slug"], "title": r["title"],
                          "h1_live": live["h1"], "h1_new": r["h1"],
                          "seo_title_live": live["seo_title"], "seo_title_new": r["seo_title"],
                          "summary_words_live": live["summary_words"], "summary_words_new": r["summary_words"]})

    approved = [r for r in results if r.get("status") == "approvato"]
    to_review = [r for r in results if r.get("status") == "da_revisionare"]
    failed = [r for r in results if not r.get("ok")]
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total": len(results), "approved": len(approved), "to_review": len(to_review), "failed": len(failed),
        "total_cost": round(total_cost, 4), "total_tokens": total_tokens,
        "seo_duplicates": seo_dups, "diffs_first_published": diffs, "items": results,
    }
    open('/app/scripts/qc_report.json', 'w').write(json.dumps(report, ensure_ascii=False, indent=2))
    print("\n=== REPORT ===")
    print(f"Totale {len(results)} | approvati {len(approved)} | da revisionare {len(to_review)} | falliti {len(failed)}")
    print(f"Costo totale ~${round(total_cost,4)} | token ~{total_tokens}")
    print("Duplicazioni SEO:", {k: len(v) for k, v in seo_dups.items()})
    print("Scritto /app/scripts/qc_report.json")


if __name__ == "__main__":
    asyncio.run(main())
