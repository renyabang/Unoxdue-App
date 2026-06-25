"""Batch caption: scarica i sottotitoli reali per tutti gli episodi 'pending'.
Sicurezza: salta qualsiasi video presente in youtube_exclusions o non episodio/intervista.
Non stampa MAI il testo. Scrive un report finale in /app/scripts/batch_caption_report.txt."""
import asyncio, sys, json
from datetime import datetime
sys.path.insert(0, '/app/backend')

REPORT = '/app/scripts/batch_caption_report.txt'
ALLOWED = {"episodio", "intervista"}


async def main():
    from config_db import db
    import youtube as yt
    excl_ids = set(await db.youtube_exclusions.distinct("youtube_id"))
    pend = await db.episodes.find(
        {"youtube_id": {"$ne": None},
         "$or": [{"transcription_status": "pending"}, {"transcription_status": {"$exists": False}}]},
        {"_id": 0, "slug": 1, "title": 1, "type": 1, "editorial_type": 1, "youtube_id": 1},
    ).to_list(200)

    results = []
    for p in pend:
        slug, yid = p["slug"], p["youtube_id"]
        et = p.get("editorial_type") or p.get("type")
        if yid in excl_ids or et not in ALLOWED:
            results.append({"slug": slug, "title": p["title"], "skipped": True,
                            "reason": f"escluso/non ammesso (et={et})"})
            continue
        try:
            res = await yt.fetch_transcript(slug)
        except Exception as e:
            res = {"ok": False, "error": str(e)}
        results.append({"slug": slug, "title": p["title"],
                        "status": res.get("transcription_status"),
                        "found": res.get("found"), "lang": res.get("language"),
                        "chars": res.get("chars"), "error": res.get("error")})
        print(f"[{res.get('transcription_status')}] {p['title'][:50]} chars={res.get('chars')}")

    counts = {}
    for r in results:
        k = "skipped" if r.get("skipped") else (r.get("status") or "?")
        counts[k] = counts.get(k, 0) + 1
    report = {"finished_at": datetime.now().isoformat(timespec="seconds"),
              "total": len(results), "counts": counts, "items": results}
    open(REPORT, "w").write(json.dumps(report, ensure_ascii=False, indent=2))
    print("\n=== REPORT BATCH ===")
    print("Totale:", len(results), "| Conteggi:", counts)


if __name__ == "__main__":
    asyncio.run(main())
