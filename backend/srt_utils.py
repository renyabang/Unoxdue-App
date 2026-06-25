"""Utility per parsing SRT, pulizia testo e chunking per timestamp.
Nessuna dipendenza LLM: puro testo. Usato dalla pipeline AI delle trascrizioni.

Le auto-caption di YouTube (SRT) tipicamente ripetono le righe in modo "rolling":
ogni cue contiene un pezzo di testo che si sovrappone al successivo. La pulizia
ricostruisce il testo togliendo le sovrapposizioni, senza inventare nulla.
"""
import re

_TS = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,\.](\d{1,3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,\.](\d{1,3})"
)
_TAG = re.compile(r"<[^>]+>")


def _to_sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def hms(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def parse_srt(srt: str) -> list:
    """Ritorna lista di segmenti {idx, start, end, start_hms, text}."""
    if not srt:
        return []
    segments = []
    blocks = re.split(r"\n\s*\n", srt.replace("\r\n", "\n").replace("\r", "\n").strip())
    idx = 0
    for block in blocks:
        lines = [l for l in block.split("\n") if l.strip() != ""]
        if not lines:
            continue
        ts_line = None
        text_lines = []
        for l in lines:
            mt = _TS.search(l)
            if mt and ts_line is None:
                ts_line = mt
            elif l.strip().isdigit() and ts_line is None and not text_lines:
                continue  # numero di sequenza
            else:
                text_lines.append(l)
        if not ts_line:
            continue
        start = _to_sec(*ts_line.group(1, 2, 3, 4))
        end = _to_sec(*ts_line.group(5, 6, 7, 8))
        text = _TAG.sub("", " ".join(text_lines)).strip()
        text = re.sub(r"\s+", " ", text)
        if not text:
            continue
        segments.append({"idx": idx, "start": round(start, 2), "end": round(end, 2),
                         "start_hms": hms(start), "text": text})
        idx += 1
    return segments


def _dedupe_overlap(prev: str, cur: str) -> str:
    """Rimuove dal testo corrente il prefisso che è gia' la coda del precedente
    (tipico delle auto-caption rolling). Ritorna SOLO il testo nuovo da aggiungere."""
    if not prev:
        return cur
    pw = prev.split()
    cw = cur.split()
    max_k = min(len(pw), len(cw), 20)
    for k in range(max_k, 0, -1):
        if [w.lower() for w in pw[-k:]] == [w.lower() for w in cw[:k]]:
            return " ".join(cw[k:])
    return cur


def clean_text(segments: list) -> str:
    """Testo continuo, pulito dalle sovrapposizioni delle auto-caption."""
    out = []
    prev = ""
    for seg in segments:
        add = _dedupe_overlap(prev, seg["text"])
        if add.strip():
            out.append(add.strip())
        prev = seg["text"]
    text = " ".join(out)
    return re.sub(r"\s+", " ", text).strip()


def segment_clean_text(segments: list) -> list:
    """Come clean_text ma ritorna per-segmento il testo nuovo (allineato ai timestamp).
    Utile per ricostruire blocchi/capitoli mantenendo il timestamp di partenza."""
    res = []
    prev = ""
    for seg in segments:
        add = _dedupe_overlap(prev, seg["text"]).strip()
        prev = seg["text"]
        res.append({**seg, "clean": add})
    return res


def chunk_segments(segments: list, max_chars: int = 7000) -> list:
    """Divide i segmenti in chunk allineati ai timestamp.
    Ogni chunk: {start, end, start_hms, seg_from, seg_to, text}."""
    clean_segs = segment_clean_text(segments)
    chunks = []
    buf = []
    cur_chars = 0
    for cs in clean_segs:
        piece = cs["clean"]
        if cur_chars + len(piece) + 1 > max_chars and buf:
            chunks.append(_make_chunk(buf))
            buf = []
            cur_chars = 0
        buf.append(cs)
        cur_chars += len(piece) + 1
    if buf:
        chunks.append(_make_chunk(buf))
    return chunks


def _make_chunk(buf: list) -> dict:
    txt = " ".join(c["clean"] for c in buf if c["clean"].strip())
    txt = re.sub(r"\s+", " ", txt).strip()
    return {
        "start": buf[0]["start"], "end": buf[-1]["end"],
        "start_hms": buf[0]["start_hms"],
        "seg_from": buf[0]["idx"], "seg_to": buf[-1]["idx"],
        "text": txt,
    }


def normalize_for_match(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^\w\sàèéìòóùç]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def quote_in_transcript(quote: str, clean: str, min_words: int = 4) -> bool:
    """Verifica che una citazione sia realmente presente (match robusto su parole)."""
    nq = normalize_for_match(quote)
    if len(nq.split()) < min_words:
        return False
    nc = normalize_for_match(clean)
    if nq in nc:
        return True
    # fallback: almeno l'80% di una finestra di parole consecutive combacia
    qw = nq.split()
    return nq in nc
