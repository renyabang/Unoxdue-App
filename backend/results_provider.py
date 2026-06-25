"""Step 6 — Provider risultati / fixture / stato eventi (NON quote).

Astrazione provider-agnostica: il motore di settlement (settlement.py) NON dipende dal provider concreto.
- FixtureResultsProvider: dataset deterministico (concluse, rinviata, sospesa, cancellata, AET, PEN) per i test.
- ApiFootballResultsProvider: PREDISPOSTO ma attivo SOLO se SPORT_RESULTS_API_PROVIDER=apifootball + SPORT_RESULTS_API_KEY.
- Sostituzione del provider senza toccare la logica del motore.

Stati normalizzati: scheduled | in_play | finished | postponed | suspended | cancelled.
Punteggi: score.ft (90'), score.ht, score.et (supplementari), score.pen (rigori). Mai inventati.
"""
import re
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import requests

from config_db import SPORT_RESULTS_API_PROVIDER, SPORT_RESULTS_API_URL, SPORT_RESULTS_API_KEY

MAPPING_VERSION = "1.0"


def norm_team(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\b(ac|as|us|ss|fc|calcio|1909|1913)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_match(match: str):
    parts = re.split(r"\s+-\s+|\s+vs\s+|\s+v\s+|\s+–\s+|–", match or "", maxsplit=1)
    if len(parts) >= 2:
        return norm_team(parts[0]), norm_team(parts[1])
    return norm_team(match), ""


def _now():
    return datetime.now(timezone.utc).isoformat()


def make_event(provider, pid, comp, season, rnd, home, away, kickoff, status,
               ft=None, ht=None, et=None, pen=None, raw=None):
    return {
        "provider": provider, "provider_event_id": str(pid),
        "competition": comp, "season": season, "round": rnd,
        "home": home, "away": away, "home_norm": norm_team(home), "away_norm": norm_team(away),
        "kickoff": kickoff, "timezone": "UTC", "status": status,
        "score": {"ft": ft, "ht": ht, "et": et, "pen": pen},
        "raw": raw or {}, "mapping_version": MAPPING_VERSION, "fetched_at": _now(),
    }


class ResultsProvider(ABC):
    name = "base"

    @abstractmethod
    async def get_events(self, competition: str, season: str, round_: int):
        ...

    async def get_event(self, competition, season, round_, home, away):
        evs = await self.get_events(competition, season, round_)
        target = {norm_team(home), norm_team(away)}
        for e in evs:
            if {e["home_norm"], e["away_norm"]} == target:
                return e
        return None

    async def get_results(self, competition, season, round_):
        return [e for e in await self.get_events(competition, season, round_) if e["status"] == "finished"]


def _sc(h, a):
    return {"home": h, "away": a}


class FixtureResultsProvider(ResultsProvider):
    """Dataset demo deterministico: copre tutti gli stati richiesti."""
    name = "fixture"

    FIXTURES = [
        # (home, away, status, ft, ht, et, pen)
        ("Inter", "Milan", "finished", _sc(2, 1), _sc(1, 0), None, None),
        ("Napoli", "Roma", "finished", _sc(2, 1), _sc(1, 1), None, None),
        ("Juventus", "Lazio", "finished", _sc(0, 0), _sc(0, 0), None, None),
        ("Roma", "Sassuolo", "finished", _sc(3, 0), _sc(2, 0), None, None),
        ("Napoli", "Udinese", "finished", _sc(1, 1), _sc(0, 1), None, None),
        ("Atalanta", "Torino", "postponed", None, None, None, None),
        ("Bologna", "Genoa", "suspended", None, None, None, None),
        ("Fiorentina", "Empoli", "cancelled", None, None, None, None),
        ("Como", "Cagliari", "finished", _sc(2, 2), _sc(1, 1), _sc(3, 2), None),     # AET
        ("Lecce", "Verona", "finished", _sc(1, 1), _sc(0, 1), _sc(1, 1), _sc(4, 3)),  # PEN
    ]

    async def get_events(self, competition, season, round_):
        out = []
        for i, (h, a, st, ft, ht, et, pen) in enumerate(self.FIXTURES):
            out.append(make_event("fixture", f"fx-{i}", competition, season, round_,
                                   h, a, _now(), st, ft=ft, ht=ht, et=et, pen=pen,
                                   raw={"demo": True}))
        return out


class ApiFootballResultsProvider(ResultsProvider):
    """Predisposto per API-Football (api-sports). Attivo solo con chiave reale."""
    name = "apifootball"
    STATUS_MAP = {
        "FT": "finished", "AET": "finished", "PEN": "finished",
        "PST": "postponed", "SUSP": "suspended", "INT": "suspended",
        "CANC": "cancelled", "ABD": "cancelled", "AWD": "finished", "WO": "finished",
        "NS": "scheduled", "TBD": "scheduled",
        "1H": "in_play", "2H": "in_play", "HT": "in_play", "ET": "in_play",
        "P": "in_play", "BT": "in_play", "LIVE": "in_play",
    }

    def _season_year(self, season: str) -> int:
        return int(str(season).split("-")[0])

    async def get_events(self, competition, season, round_):
        def _call():
            base = (SPORT_RESULTS_API_URL or "https://v3.football.api-sports.io").rstrip("/")
            headers = {"x-apisports-key": SPORT_RESULTS_API_KEY}
            params = {"league": 135, "season": self._season_year(season),
                      "round": f"Regular Season - {round_}"}
            r = requests.get(f"{base}/fixtures", headers=headers, params=params, timeout=15)
            r.raise_for_status()
            return r.json()

        data = await asyncio.get_event_loop().run_in_executor(None, _call)
        out = []
        for it in data.get("response", []):
            fx = it.get("fixture", {}); teams = it.get("teams", {})
            goals = it.get("goals", {}); score = it.get("score", {})
            short = (fx.get("status") or {}).get("short", "NS")
            ft = score.get("fulltime") or {"home": goals.get("home"), "away": goals.get("away")}
            out.append(make_event(
                "apifootball", fx.get("id"), competition, season, round_,
                (teams.get("home") or {}).get("name"), (teams.get("away") or {}).get("name"),
                fx.get("date"), self.STATUS_MAP.get(short, "scheduled"),
                ft=ft, ht=score.get("halftime"), et=score.get("extratime"),
                pen=score.get("penalty"), raw=it))
        return out


def get_provider() -> ResultsProvider:
    prov = (SPORT_RESULTS_API_PROVIDER or "fixture").lower()
    if prov == "apifootball" and SPORT_RESULTS_API_KEY:
        return ApiFootballResultsProvider()
    return FixtureResultsProvider()


def provider_status() -> dict:
    prov = (SPORT_RESULTS_API_PROVIDER or "fixture").lower()
    active = get_provider().name
    return {
        "configured": bool(SPORT_RESULTS_API_KEY),
        "provider": prov, "active": active, "demo": active == "fixture",
        "note": ("Provider risultati in modalità fixture (demo). Imposta SPORT_RESULTS_API_PROVIDER=apifootball "
                 "e SPORT_RESULTS_API_KEY per i dati reali, senza modificare il motore di settlement."),
    }
