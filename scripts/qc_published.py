"""Controllo qualità dei contenuti SEO già pubblicati (lettura sola, niente modifiche)."""
import asyncio, sys, re, json
sys.path.insert(0, '/app/backend')
import srt_utils as su

SLUGS = [
    "quinto-appuntamento-di-unoxdue-live-studio-serie-a-33-giornata-calcio-pronostici",
    "decimo-appuntamento-di-unoxdue-live-studio-serie-a-38-giornata-calcio-pronostici",
    "allan-baclet-playoff-cosenza",
]
VAGUE = ["si continua", "altre considerazioni", "varie", "conclusioni varie", "si parla", "continua a parlare", "altro", "considerazioni finali"]


def words(s):
    return len((s or "").split())


async def main():
    from config_db import db
    targets = {}
    for slug in SLUGS:
        ep = await db.episodes.find_one({"slug": slug})
        b = await db.transcriptions.find_one({"slug": slug}) or {}
        clean = b.get("clean", "")
        clean_norm = su.normalize_for_match(clean)
        seg_times = {s["start_hms"] for s in b.get("segments", [])}
        summary = ep.get("summary", []) or []
        chapters = ep.get("chapters", []) or []
        quotes = ep.get("quotes", []) or []
        intro = ep.get("excerpt", "") or ""
        # metriche
        sum_words = sum(words(p) for p in summary)
        # ripetizioni: paragrafi/sentence duplicati
        topics = ep.get("topics", []) or []
        dup_topics = len(topics) - len({t.lower().strip() for t in topics})
        # capitoli vaghi
        vague_ch = [c for c in chapters if any(v in (c.get("label", "")).lower() for v in VAGUE)]
        # capitoli troppo ravvicinati (<60s)
        def t2s(t):
            p = [int(x) for x in str(t).split(":")]
            return p[0]*60+p[1] if len(p) == 2 else p[0]*3600+p[1]*60+p[2]
        secs = sorted(t2s(c["time"]) for c in chapters if c.get("time"))
        close = sum(1 for i in range(1, len(secs)) if secs[i]-secs[i-1] < 60)
        # timestamp dubbi: non presenti nei segmenti
        dubious_ts = [c["time"] for c in chapters if seg_times and c.get("time") not in seg_times]
        # citazioni non supportate
        unsupported_q = [q for q in quotes if not su.quote_in_transcript((q.get("text") if isinstance(q, dict) else q), clean)]
        with_speaker = sum(1 for q in quotes if isinstance(q, dict) and q.get("speaker"))
        # keyword stuffing: frequenza di 'unoxdue'/'serie a' nel sommario
        sumtext = " ".join(summary).lower()
        kw_uxd = sumtext.count("unoxdue") + sumtext.count("uno x due")
        kw_seriea = sumtext.count("serie a")
        targets[slug] = {
            "title": ep.get("title"),
            "type": ep.get("type"), "guest_name": ep.get("guest_name"),
            "h1": ep.get("h1"), "seo_title": ep.get("seo_title"), "meta": ep.get("meta_description"),
            "intro_words": words(intro), "summary_words": sum_words, "summary_paras": len(summary),
            "n_chapters": len(chapters), "n_quotes": len(quotes),
            "dup_topics": dup_topics, "vague_chapters": [c.get("label") for c in vague_ch],
            "chapters_close_<60s": close, "dubious_timestamps": dubious_ts,
            "unsupported_quotes": len(unsupported_q), "quotes_with_speaker": with_speaker,
            "seo_title_len": len(ep.get("seo_title") or ""), "meta_len": len(ep.get("meta_description") or ""),
            "kw_unoxdue_in_summary": kw_uxd, "kw_seriea_in_summary": kw_seriea,
            "intro": intro, "summary_first": summary[0] if summary else "",
            "chapters_sample": [{"time": c["time"], "label": c["label"]} for c in chapters[:3]],
            "quotes_sample": [{"text": (q.get("text") if isinstance(q, dict) else q)[:140],
                               "time": (q.get("time") if isinstance(q, dict) else None),
                               "speaker": (q.get("speaker") if isinstance(q, dict) else None)} for q in quotes[:2]],
        }
    # duplicazioni SEO tra i 3
    h1s = [v["h1"] for v in targets.values()]
    metas = [v["meta"] for v in targets.values()]
    seos = [v["seo_title"] for v in targets.values()]
    targets["_seo_dup"] = {
        "h1_unique": len(set(h1s)) == len(h1s),
        "meta_unique": len(set(metas)) == len(metas),
        "seo_title_unique": len(set(seos)) == len(seos),
    }
    print(json.dumps(targets, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
