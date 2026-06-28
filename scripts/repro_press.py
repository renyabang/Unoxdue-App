import sys, json, traceback
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
import seo
import press_logos as pl
from seo import SITE_URL

SECTION = {"episode": "episodi", "interview": "interviste", "team": "team"}
LINK_LABEL = {"episode": "Episodio", "interview": "Intervista", "team": "Team"}

docs = json.load(open("/tmp/prod_press.json"))

# replicate published_archive() transform
out = []
seen = set()
for it in docs:
    cu = it.get("canonical_url") or it.get("url")
    if cu in seen:
        continue
    seen.add(cu)
    internals = []
    for l in (it.get("links") or []):
        sec = SECTION.get(l.get("type"))
        if sec and l.get("slug"):
            internals.append({"url": f"{SITE_URL}/{sec}/{l['slug']}/",
                              "label": LINK_LABEL.get(l.get("type"), "Collegato"),
                              "title": l.get("title")})
    lg = pl.public_logo(it)
    out.append({"source": it.get("source"), "title": it.get("title"), "date": it.get("date"),
                "summary": it.get("summary"), "url": it.get("url"), "internals": internals,
                "logo": lg["url"], "initials": lg["initials"]})

print("ITEMS:", len(out))
for o in out:
    print(" ", o["source"], "| logo=", o["logo"], "| initials=", o["initials"], "| internals=", len(o["internals"]))

print("\n=== render_press_archive ===")
try:
    html = seo.render_press_archive(out)
    print("OK len", len(html))
except Exception:
    traceback.print_exc()
