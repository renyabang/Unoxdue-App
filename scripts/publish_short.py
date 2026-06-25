#!/usr/bin/env python3
"""Step 3 — Pubblicazione indipendente dei 4 episodi approved_short.
Controlli bloccanti per episodio; pubblica solo chi li supera.
"""
import os, sys, re, asyncio
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / "backend" / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from pymongo import MongoClient
import ai_transcript as ait

client = MongoClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

SLUGS = [
    "serie-a-2025-2026-giornata-37-puntata-9",
    "serie-a-2025-2026-giornata-35-puntata-7",
    "serie-a-2025-2026-giornata-32-puntata-4",
    "serie-a-2025-2026-giornata-31-puntata-3",
]


def _norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9àèéìòù\s]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


async def check(slug):
    ep = db.episodes.find_one({"slug": slug})
    ap = (ep or {}).get("ai_preview") or {}
    b = await ait.get_transcript_clean(slug)
    clean_n = _norm(b.get("clean", ""))
    issues = []
    secs = ap.get("summary_sections") or []
    h2 = [s for s in secs if int(s.get("level", 2)) == 2]
    if len(secs) < 3 or len(h2) < 2:
        issues.append(f"sezioni insufficienti (sez={len(secs)}, H2={len(h2)})")
    chaps = ap.get("chapters") or []
    if not chaps:
        issues.append("0 capitoli")
    if any(not c.get("time") for c in chaps):
        issues.append("capitolo senza timestamp")
    quotes = ap.get("quotes") or []
    if len(quotes) < 2:
        issues.append(f"citazioni insufficienti ({len(quotes)})")
    nonverb = 0
    for q in quotes:
        txt = q.get("text") if isinstance(q, dict) else q
        if _norm(txt) not in clean_n:
            nonverb += 1
    if nonverb:
        issues.append(f"{nonverb} citazioni NON verbatim")
    if not (ap.get("topics") or []):
        issues.append("0 topics")
    if len(clean_n) < 1000:
        issues.append("trascrizione assente/troppo corta")
    return ep, ap, issues


async def main():
    publish = "--publish" in sys.argv
    for slug in SLUGS:
        ep, ap, issues = await check(slug)
        if not ep:
            print(f"[{slug}] NON TROVATO"); continue
        status = "PASS" if not issues else "BLOCCATO"
        print(f"\n=== {slug} -> {status}")
        print(f"    sezioni={len(ap.get('summary_sections') or [])} capitoli={len(ap.get('chapters') or [])} citazioni={len(ap.get('quotes') or [])} topics={len(ap.get('topics') or [])}")
        if issues:
            print("    MOTIVI:", "; ".join(issues), "-> resta in anteprima")
            continue
        if publish:
            r = await ait.publish_preview(slug)
            print("    PUBBLICATO:", r.get("ok"), r.get("error") or "")
        else:
            print("    (dry-run, usa --publish per pubblicare)")


if __name__ == "__main__":
    asyncio.run(main())
