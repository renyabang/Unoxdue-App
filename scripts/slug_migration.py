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
import os, sys, json, datetime, re
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

ORD = {1: "Primo", 2: "Secondo", 3: "Terzo", 4: "Quarto", 5: "Quinto",
       6: "Sesto", 7: "Settimo", 8: "Ottavo", 9: "Nono", 10: "Decimo"}
INTERVIEWS = {"MxHqU7AK97I": "Allan Baclet", "7035L7empWg": "Fabio Ceravolo"}
SPECIALE_YT = "KXkkQhzzvkQ"


def _fix_brand(s):
    return re.sub(r"\bunoxdue\b", "UnoXdue", s, flags=re.IGNORECASE) if isinstance(s, str) else s


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


def cmd_titles():
    """Correzione casing brand (UnoXdue) + H1 descrittivo + campi distinti.
    Indipendente dalla migrazione slug. Idempotente. Preserva youtube_title_original literal."""
    yt2punt = {v[0]: k for k, v in SERIE_A.items()}
    for d in db.episodes.find({}):
        yt = d.get("youtube_id")
        upd = {}
        # preserva il titolo YouTube originale (literal) PRIMA del fix casing
        if not d.get("youtube_title_original"):
            upd["youtube_title_original"] = d.get("title")
        if not d.get("youtube_title_current"):
            upd["youtube_title_current"] = d.get("youtube_title_original") or d.get("title")
        # casing fix sui campi testuali (MAI sugli slug)
        upd["title"] = _fix_brand(d.get("title"))
        for f in ("excerpt", "meta_description", "seo_title"):
            if d.get(f):
                upd[f] = _fix_brand(d[f])
        if isinstance(d.get("summary"), list):
            upd["summary"] = [_fix_brand(p) for p in d["summary"]]
        if isinstance(d.get("topics"), list):
            upd["topics"] = [_fix_brand(t) for t in d["topics"]]
        if isinstance(d.get("summary_sections"), list):
            ss = []
            for s in d["summary_sections"]:
                s = dict(s); s["heading"] = _fix_brand(s.get("heading"))
                if isinstance(s.get("paragraphs"), list):
                    s["paragraphs"] = [_fix_brand(p) for p in s["paragraphs"]]
                ss.append(s)
            upd["summary_sections"] = ss
        if isinstance(d.get("quotes"), list):
            qs = []
            for q in d["quotes"]:
                if isinstance(q, dict):
                    q = dict(q); q["text"] = _fix_brand(q.get("text")); q["speaker"] = _fix_brand(q.get("speaker"))
                else:
                    q = _fix_brand(q)
                qs.append(q)
            upd["quotes"] = qs
        if isinstance(d.get("chapters"), list):
            cs = []
            for c in d["chapters"]:
                c = dict(c); c["label"] = _fix_brand(c.get("label")); c["description"] = _fix_brand(c.get("description"))
                cs.append(c)
            upd["chapters"] = cs
        if isinstance(d.get("related"), list):
            rs = []
            for r in d["related"]:
                r = dict(r); r["title"] = _fix_brand(r.get("title"))
                rs.append(r)
            upd["related"] = rs
        # H1 descrittivo / website_title / breadcrumb_label
        if yt in yt2punt:
            k = yt2punt[yt]; g = SERIE_A[k][1]
            h1 = f"{ORD[k]} appuntamento UnoXdue: Serie A 2025/26, {g}ª giornata"
            upd.update(h1=h1, website_title=h1, breadcrumb_label=f"{ORD[k]} appuntamento")
        elif yt == SPECIALE_YT:
            h1 = "Speciale Mondiali UnoXdue: Coppa del Mondo FIFA 2026"
            upd.update(h1=h1, website_title=h1, breadcrumb_label="Speciale Mondiali 2026")
        elif yt in INTERVIEWS:
            h1 = _fix_brand(d.get("h1") or d.get("title"))
            upd.update(h1=h1, website_title=h1, breadcrumb_label=INTERVIEWS[yt])
        else:
            h1 = _fix_brand(d.get("h1") or d.get("title"))
            upd.update(h1=h1, website_title=h1, breadcrumb_label=h1)
        db.episodes.update_one({"_id": d["_id"]}, {"$set": upd})
        print(f"titles OK {yt}: h1='{upd['h1']}' | bc='{upd['breadcrumb_label']}'")


def cmd_refresh_related():
    """Ricostruisce related[].{section,slug,title} dai documenti target (slug o previous_slugs),
    usando il website_title pulito. Elimina titoli/slug stantii dopo la migrazione."""
    for d in db.episodes.find({}):
        rel = d.get("related") or []
        if not rel:
            continue
        new, changed = [], False
        for r in rel:
            slug = r.get("slug")
            tgt = db.episodes.find_one({"slug": slug}) or db.episodes.find_one({"previous_slugs": slug})
            if tgt:
                nr = {"section": ("interviste" if tgt.get("type") == "intervista" else "episodi"),
                      "slug": tgt.get("slug"),
                      "title": tgt.get("website_title") or tgt.get("title")}
                if nr != r:
                    changed = True
                new.append(nr)
            else:
                new.append(r)
        if changed:
            db.episodes.update_one({"_id": d["_id"]}, {"$set": {"related": new}})
            print(f"related refreshed in {d.get('slug')}")


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
    elif cmd == "titles":
        cmd_titles()
    elif cmd == "refresh-related":
        cmd_refresh_related()
    elif cmd == "migrate":
        cmd_migrate([int(x) for x in sys.argv[2:]])
    elif cmd == "rollback":
        cmd_rollback(sys.argv[2])
    else:
        print(__doc__)
