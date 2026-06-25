#!/usr/bin/env python3
"""Migrazione slug episodi UnoXdue (audit-driven, reversibile).

Uso:
  python slug_migration.py backup                 # backup completo + snapshot slug
  python slug_migration.py plan                    # stampa la tabella old->new
  python slug_migration.py migrate 1               # migra SOLO la puntata 1 (pilota)
  python slug_migration.py migrate 2 3 4 5 6 7 8 9 10 12   # batch
  python slug_migration.py rollback <backup_dir>   # ripristina episodes dal backup

- Trova ogni episodio tramite youtube_id (stabile, non cambia con lo slug).
- Aggiunge il vecchio slug a previous_slugs (per il 301 gestito da server.py).
- Aggiorna i link interni (related[].slug) in TUTTI gli episodi che referenziano il vecchio slug.
- Popola i metadati distinti richiesti senza rigenerare lo slug dal titolo.
"""
import os, sys, json, datetime
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import json_util

load_dotenv(Path(__file__).resolve().parents[1] / "backend" / ".env")
client = MongoClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

SEASON = "2025-2026"
# puntata -> (youtube_id, giornata, competitions_mentioned)
SERIE_A = {
    1:  ("b0xDcw9mYNM", 29, ["champions-league", "europa-league"]),
    2:  ("Dwwyl4nx0dE", 30, ["europa-league"]),
    3:  ("7m82PWSRcrM", 31, []),
    4:  ("JBlPeaOY0vA", 32, []),
    5:  ("-dyr2ruG1r8", 33, ["champions-league"]),
    6:  ("pWmfVNlhz6w", 34, ["coppa-italia", "champions-league"]),
    7:  ("qkDu5MzURiE", 35, []),
    8:  ("Tazb-A0qIcM", 36, ["champions-league"]),
    9:  ("XZozhKAPX0g", 37, []),
    10: ("6TygRGNyIi4", 38, []),
}
SPECIALE = {12: ("KXkkQhzzvkQ",)}  # gestito a parte (slug tematico)


def new_slug(puntata: int) -> str:
    if puntata in SERIE_A:
        g = SERIE_A[puntata][1]
        return f"serie-a-{SEASON}-giornata-{g}-puntata-{puntata}"
    if puntata == 12:
        return "speciale-mondiali-2026-puntata-12"
    raise ValueError(f"puntata {puntata} non mappata")


def doc_for(puntata: int):
    ytid = (SERIE_A.get(puntata) or SPECIALE.get(puntata))[0]
    return db.episodes.find_one({"youtube_id": ytid})


def cmd_plan():
    print(f"{'punt':>4} {'yt_id':12} {'old slug':70} -> new slug")
    for k in list(SERIE_A) + list(SPECIALE):
        d = doc_for(k)
        print(f"{k:>4} {d['youtube_id']:12} {d['slug']:70} -> {new_slug(k)}")


def cmd_backup():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path("/app/backups") / f"slug_migration_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    eps = list(db.episodes.find({}))
    (out / "episodes_full.json").write_text(json_util.dumps(eps, indent=2))
    snap = [{"youtube_id": e.get("youtube_id"), "slug": e.get("slug"),
             "previous_slugs": e.get("previous_slugs")} for e in eps]
    (out / "slug_snapshot.json").write_text(json.dumps(snap, ensure_ascii=False, indent=2))
    # backup anche predictions e transcriptions (riferimenti)
    (out / "predictions.json").write_text(json_util.dumps(list(db.predictions.find({})), indent=2))
    (out / "transcriptions.json").write_text(json_util.dumps(list(db.transcriptions.find({})), indent=2))
    print(f"BACKUP OK -> {out}  ({len(eps)} episodi)")
    print(f"Rollback: python slug_migration.py rollback {out}")
    return out


def cmd_migrate(puntate):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for k in puntate:
        d = doc_for(k)
        if not d:
            print(f"[{k}] SKIP: episodio non trovato"); continue
        old = d["slug"]
        ns = new_slug(k)
        if old == ns:
            print(f"[{k}] gia' migrato ({ns})"); continue
        # collisione?
        if db.episodes.find_one({"slug": ns, "youtube_id": {"$ne": d["youtube_id"]}}):
            print(f"[{k}] ERRORE: slug {ns} gia' usato da altro doc"); continue
        prev = list(d.get("previous_slugs") or [])
        if old not in prev:
            prev.append(old)
        meta = {
            "slug": ns,
            "previous_slugs": prev,
            "season": SEASON,
            "recording_date": d.get("published_at"),
            "publication_date": d.get("published_at"),
            "youtube_video_id": d.get("youtube_id"),
            "youtube_title_original": d.get("youtube_title_original") or d.get("title"),
            "youtube_title_current": d.get("youtube_title_current") or d.get("title"),
            "website_title": d.get("h1") or d.get("title"),
            "updated_at": now,
        }
        if k in SERIE_A:
            meta["episode_number"] = k
            meta["primary_competition"] = "serie-a"
            meta["matchday"] = SERIE_A[k][1]
            meta["competitions_mentioned"] = SERIE_A[k][2]
        elif k == 12:
            meta["episode_number"] = 12
            meta["primary_competition"] = "world-cup"
            meta["tournament_year"] = 2026
            meta["competitions_mentioned"] = ["world-cup"]
        db.episodes.update_one({"youtube_id": d["youtube_id"]}, {"$set": meta})
        # rinomina lo slug nella collezione transcriptions (associazione trascrizione)
        tr = db.transcriptions.update_one({"slug": old}, {"$set": {"slug": ns}})
        # aggiorna link interni (related[].slug) ovunque referenzino il vecchio slug
        touched = 0
        for other in db.episodes.find({"related.slug": old}):
            rel = other.get("related") or []
            for r in rel:
                if r.get("slug") == old:
                    r["slug"] = ns
            db.episodes.update_one({"_id": other["_id"]}, {"$set": {"related": rel}})
            touched += 1
        print(f"[{k}] OK  {old}\n        -> {ns}  | transcr={tr.modified_count} | link interni in {touched} doc")


def cmd_rollback(backup_dir):
    p = Path(backup_dir) / "episodes_full.json"
    eps = json_util.loads(p.read_text())
    for e in eps:
        db.episodes.replace_one({"_id": e["_id"]}, e, upsert=True)
    tp = Path(backup_dir) / "transcriptions.json"
    n_tr = 0
    if tp.exists():
        for t in json_util.loads(tp.read_text()):
            db.transcriptions.replace_one({"_id": t["_id"]}, t, upsert=True)
            n_tr += 1
    print(f"ROLLBACK OK da {backup_dir} ({len(eps)} episodi, {n_tr} trascrizioni ripristinate)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if cmd == "plan":
        cmd_plan()
    elif cmd == "backup":
        cmd_backup()
    elif cmd == "migrate":
        cmd_migrate([int(x) for x in sys.argv[2:]])
    elif cmd == "rollback":
        cmd_rollback(sys.argv[2])
    else:
        print(__doc__)
