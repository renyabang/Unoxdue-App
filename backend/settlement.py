"""Step 6 — Motore interno di settlement, storico versionato, audit correzioni e pubblicazione condizionata.

- Determina l'esito di ogni selezione dai risultati del provider (mai dall'AI, mai inventato).
- Stati selezione/giocata: pending | won | lost | void | postponed | suspended | cancelled | manual_review.
- Mercati auto-risolti: 1X2, Doppia Chance, Draw No Bet, Over/Under, GG/NG (BTTS).
  I mercati combinati/non riconosciuti -> manual_review (correzione manuale in admin, con audit).
- Aggregazione multipla: persa se una persa; in attesa se una pending; altrimenti vinta se almeno una vinta, else void.
- Storico versionato (settlement_history) e audit delle correzioni (settlement_audit): nessuna sovrascrittura silenziosa.
- Pubblicazione condizionata configurabile (publish_min_valid: 1/2/3).
"""
import re
from datetime import datetime, timezone

from config_db import db
import results_provider as rp
import automations as auto

SETTLE_VERSION = "1.0"
SETTLED = {"won", "lost", "void", "postponed", "suspended", "cancelled"}
UNRESOLVED = {"pending", "in_play"}
ALLOWED_MANUAL = {"pending", "won", "lost", "void", "postponed", "suspended", "cancelled", "manual_review"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _num(s):
    m = re.search(r"(\d+(?:[.,]\d+)?)", str(s or ""))
    return float(m.group(1).replace(",", ".")) if m else None


def _ft(event):
    sc = (event or {}).get("score", {}) or {}
    ft = sc.get("ft") or sc.get("final")
    if ft and ft.get("home") is not None and ft.get("away") is not None:
        return ft.get("home"), ft.get("away")
    return None, None


def _market_kind(market: str, pick: str) -> str:
    m = (market or "").lower()
    p = (pick or "").lower().strip()
    # mercati combinati (es. "1X2 + U/O 3,5", "Multigol") -> non auto-risolvibili
    if "+" in m or "multigol" in m or "multi gol" in m or "esatto" in m or "marcatore" in m:
        return "combo"
    if "doppia chance" in m or "double chance" in m or p in ("1x", "x2", "12"):
        return "dc"
    if "draw no bet" in m or "dnb" in m:
        return "dnb"
    if any(k in m for k in ["gg", "ng", "btts", "both teams", "goal/no", "goal no"]) or p in (
            "gg", "ng", "goal", "nogoal", "no goal", "si", "sì", "no", "yes"):
        return "btts"
    if any(k in m for k in ["over", "under", "totale", "totals", "o/u", "u/o", "goal totali"]) or \
            p.startswith("over") or p.startswith("under"):
        return "ou"
    if any(k in m for k in ["esito", "1x2", "match winner", "full time", "risultato finale", "winner", "segno"]) or \
            p in ("1", "x", "2"):
        return "1x2"
    return "unknown"


def settle_selection(sel: dict, event: dict) -> dict:
    """Esito di UNA selezione. Usa il punteggio dei 90' (score.ft) per i mercati standard."""
    if not event:
        return {"status": "manual_review", "reason": "Evento non trovato nel provider"}
    st = event.get("status")
    if st in ("postponed", "suspended", "cancelled"):
        return {"status": st, "reason": f"Evento {st}"}
    if st in ("scheduled", "in_play"):
        return {"status": "pending", "reason": f"Evento {st}"}
    # finished
    h, a = _ft(event)
    if h is None or a is None:
        return {"status": "manual_review", "reason": "Punteggio non disponibile"}
    kind = _market_kind(sel.get("market"), sel.get("pick"))
    p = (sel.get("pick") or "").lower().strip()
    score = f"{h}-{a}"

    def W():
        return {"status": "won", "reason": score}

    def L():
        return {"status": "lost", "reason": score}

    def V():
        return {"status": "void", "reason": f"Push ({score})"}

    if kind == "1x2":
        res = "1" if h > a else ("2" if a > h else "x")
        return W() if p == res else L()
    if kind == "dc":
        res = "1" if h > a else ("2" if a > h else "x")
        ok = (p == "1x" and res in ("1", "x")) or (p == "x2" and res in ("x", "2")) or (p == "12" and res in ("1", "2"))
        return W() if ok else L()
    if kind == "dnb":
        if h == a:
            return V()
        res = "1" if h > a else "2"
        return W() if p == res else L()
    if kind == "btts":
        both = h > 0 and a > 0
        yes = p in ("gg", "goal", "yes", "si", "sì")
        return (W() if both else L()) if yes else (W() if not both else L())
    if kind == "ou":
        line = _num(sel.get("pick")) or _num(sel.get("market"))
        if line is None:
            return {"status": "manual_review", "reason": "Linea Over/Under mancante"}
        total = h + a
        if total == line:
            return V()
        over = "over" in p
        return (W() if total > line else L()) if over else (W() if total < line else L())
    if kind == "combo":
        return {"status": "manual_review", "reason": f"Mercato combinato non auto-risolvibile: {sel.get('market')}"}
    return {"status": "manual_review", "reason": f"Mercato non riconosciuto: {sel.get('market')}"}


def aggregate_pick(pick: dict) -> dict:
    sels = pick.get("selections", []) or []
    statuses = [(s.get("settlement") or {}).get("status", "pending") for s in sels]
    if not statuses:
        return {"status": "pending", "reason": "Nessuna selezione", "computed_at": _now()}
    if any(s == "lost" for s in statuses):
        res = "lost"
    elif any(s in UNRESOLVED for s in statuses):
        res = "pending"
    elif any(s == "manual_review" for s in statuses):
        res = "manual_review"
    else:
        res = "won" if any(s == "won" for s in statuses) else "void"
    return {"status": res, "selections": statuses, "computed_at": _now()}


async def apply_publish_rule(competition: str, season: str, round_: int) -> dict:
    s = await db.settings.find_one({"_id": "global"}) or {}
    min_valid = int((s.get("results") or {}).get("publish_min_valid", 1))
    pred = await db.predictions.find_one({"competition": competition, "season": season, "round": round_})
    if not pred:
        return {"ok": False}
    valid = sum(1 for p in pred.get("picks", []) if p.get("selections"))
    new_status = "pubblicato" if valid >= min_valid else "bozza"
    await db.predictions.update_one(
        {"competition": competition, "season": season, "round": round_},
        {"$set": {"status": new_status}})
    return {"valid_picks": valid, "min_valid": min_valid, "status": new_status}


async def compute_round(competition: str, season: str, round_: int, source: str = "auto", actor: str = None) -> dict:
    pred = await db.predictions.find_one({"competition": competition, "season": season, "round": round_})
    if not pred:
        return {"ok": False, "error": "Pronostico non trovato"}

    provider = rp.get_provider()
    events, last_err = None, None
    for _ in range(2):  # retry
        try:
            events = await provider.get_events(competition, season, round_)
            break
        except Exception as e:
            last_err = str(e)
    if events is None:
        await auto.log_automation("settlement", "error", f"Provider risultati fallito: {last_err}")
        return {"ok": False, "error": last_err or "Provider non disponibile"}

    def find(match):
        target = set(rp.norm_match(match))
        for e in events:
            if {e["home_norm"], e["away_norm"]} == target:
                return e
        return None

    picks = pred.get("picks", [])
    for pick in picks:
        for sel in pick.get("selections", []):
            prev = sel.get("settlement") or {}
            if prev.get("manual"):
                continue  # non sovrascrivere correzioni manuali
            ev = find(sel.get("match"))
            stt = settle_selection(sel, ev)
            stt.update({"computed_at": _now(), "provider": provider.name,
                        "event_id": ev.get("provider_event_id") if ev else None,
                        "event_status": ev.get("status") if ev else None})
            sel["settlement"] = stt
        pick["settlement"] = aggregate_pick(pick)

    version_entry = {
        "version": SETTLE_VERSION, "computed_at": _now(), "provider": provider.name,
        "source": source, "actor": actor,
        "picks": [{"tipster": p.get("tipster"), "status": p.get("settlement", {}).get("status")} for p in picks],
    }
    hist = pred.get("settlement_history", [])
    hist.append(version_entry)

    summary = {}
    for p in picks:
        st = p.get("settlement", {}).get("status", "pending")
        summary[st] = summary.get(st, 0) + 1

    await db.predictions.update_one(
        {"competition": competition, "season": season, "round": round_},
        {"$set": {"picks": picks, "settlement_history": hist,
                  "last_settlement": {"computed_at": version_entry["computed_at"],
                                      "provider": provider.name, "source": source, "summary": summary}}})
    pub = await apply_publish_rule(competition, season, round_)
    await auto.log_automation("settlement", "ok",
                              f"Settlement giornata {round_}: {summary}",
                              {"summary": summary, "provider": provider.name, "source": source})
    return {"ok": True, "summary": summary, "provider": provider.name, "demo": provider.name == "fixture",
            "published": pub, "version": SETTLE_VERSION}


async def correct(competition, season, round_, pick_index, selection_index, new_status, note, actor) -> dict:
    if new_status not in ALLOWED_MANUAL:
        return {"ok": False, "error": f"Stato non valido: {new_status}"}
    pred = await db.predictions.find_one({"competition": competition, "season": season, "round": round_})
    if not pred:
        return {"ok": False, "error": "Pronostico non trovato"}
    picks = pred.get("picks", [])
    if pick_index < 0 or pick_index >= len(picks):
        return {"ok": False, "error": "Indice giocata non valido"}
    pick = picks[pick_index]
    now = _now()
    audit = {"at": now, "actor": actor, "note": note, "manual": True, "round": round_}
    if selection_index is not None:
        sels = pick.get("selections", [])
        if selection_index < 0 or selection_index >= len(sels):
            return {"ok": False, "error": "Indice selezione non valido"}
        sel = sels[selection_index]
        prev = (sel.get("settlement") or {}).get("status")
        sel["settlement"] = {"status": new_status, "reason": note or "Correzione manuale",
                             "manual": True, "computed_at": now, "prev_status": prev}
        audit.update({"scope": "selection", "pick_index": pick_index, "selection_index": selection_index,
                      "prev_status": prev, "new_status": new_status})
        pick["settlement"] = aggregate_pick(pick)
    else:
        prev = (pick.get("settlement") or {}).get("status")
        pick["settlement"] = {"status": new_status, "reason": note or "Correzione manuale",
                              "manual": True, "computed_at": now, "prev_status": prev}
        audit.update({"scope": "pick", "pick_index": pick_index, "prev_status": prev, "new_status": new_status})
    aud = pred.get("settlement_audit", [])
    aud.append(audit)
    await db.predictions.update_one(
        {"competition": competition, "season": season, "round": round_},
        {"$set": {"picks": picks, "settlement_audit": aud}})
    pub = await apply_publish_rule(competition, season, round_)
    await auto.log_automation("settlement", "info",
                              f"Correzione manuale -> {new_status} (giornata {round_})", audit)
    return {"ok": True, "audit": audit, "published": pub}
