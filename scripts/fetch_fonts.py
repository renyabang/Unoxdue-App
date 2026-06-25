"""Scarica i woff2 (subset latin + latin-ext) dei font del brand UnoXdue
e li salva localmente in backend/static/fonts/ con nomi deterministici.
Nessuna dipendenza da CDN a runtime: i font vengono serviti dal backend."""
import re
import sys
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "backend" / "static" / "fonts"
OUT.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# (slug, css family param, [weights])
FAMILIES = [
    ("anton", "Anton", [400]),
    ("archivo", "Archivo:wght@700;800", [700, 800]),
    ("inter", "Inter:wght@400;500;600;700", [400, 500, 600, 700]),
]

BLOCK_RE = re.compile(r"/\*\s*([\w-]+)\s*\*/\s*@font-face\s*\{([^}]*)\}", re.S)
WEIGHT_RE = re.compile(r"font-weight:\s*(\d+)")
URL_RE = re.compile(r"url\((https://[^)]+\.woff2)\)")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def run():
    downloaded = []
    for slug, fam, weights in FAMILIES:
        css = fetch(f"https://fonts.googleapis.com/css2?family={fam}&display=swap").decode()
        for subset, body in BLOCK_RE.findall(css):
            if subset not in ("latin", "latin-ext"):
                continue
            wm = WEIGHT_RE.search(body)
            um = URL_RE.search(body)
            if not wm or not um:
                continue
            weight = int(wm.group(1))
            if weight not in weights:
                continue
            suffix = "-ext" if subset == "latin-ext" else ""
            name = f"{slug}-{weight}{suffix}.woff2"
            data = fetch(um.group(1))
            (OUT / name).write_bytes(data)
            downloaded.append((name, len(data)))
    for n, sz in downloaded:
        print(f"  {n}  ({sz} bytes)")
    print(f"OK: {len(downloaded)} file font salvati in {OUT}")
    if len(downloaded) < 10:
        print("ATTENZIONE: meno file del previsto", file=sys.stderr)


if __name__ == "__main__":
    run()
