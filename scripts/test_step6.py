"""Test reale Step 6: provider football-data.org + motore settlement (dry-run).
Crea un pronostico di TEST sulla 38a 2024-25 (esiti noti), esegue il settlement in
dry-run (nessuna scrittura sui pronostici), verifica gli esiti e rimuove il record di test."""
import asyncio, sys, json
sys.path.insert(0, '/app/backend')

TEST = {
    "competition": "Serie A", "season": "2024-25", "round": 38, "_test": True, "status": "bozza",
    "picks": [
        {"tipster": "Test-Vincenti", "selections": [
            {"match": "Napoli - Cagliari", "market": "1X2", "pick": "1"},
            {"match": "Atalanta - Parma", "market": "Doppia Chance", "pick": "X2"},
            {"match": "Milan - Monza", "market": "Draw No Bet", "pick": "1"},
            {"match": "Bologna - Genoa", "market": "Over/Under 2.5", "pick": "Over 2.5"},
            {"match": "Udinese - Fiorentina", "market": "Goal/No Goal", "pick": "GG"},
            {"match": "Lazio - Lecce", "market": "Multigol", "pick": "1-3"},
            {"match": "Como - Inter", "market": "Risultato Esatto", "pick": "0-2"},
        ]},
        {"tipster": "Test-Perdenti", "selections": [
            {"match": "Como - Inter", "market": "1X2", "pick": "1"},
            {"match": "Napoli - Cagliari", "market": "Over/Under 2.5", "pick": "Over 2.5"},
            {"match": "Milan - Monza", "market": "Goal/No Goal", "pick": "GG"},
            {"match": "Venezia - Juventus", "market": "Multigol", "pick": "1-3"},
            {"match": "Napoli - Cagliari", "market": "Risultato Esatto", "pick": "1-0"},
        ]},
        {"tipster": "Test-Manuali", "selections": [
            {"match": "Milan - Monza", "market": "1X2 + Over 1.5", "pick": "1 + Over 1.5"},
            {"match": "Inter - Lautaro", "market": "Marcatore", "pick": "Lautaro Martinez"},
            {"match": "Milan - Monza", "market": "Calci d'angolo Over 9.5", "pick": "Over 9.5"},
        ]},
    ],
}

# esiti attesi per selezione (won/lost/manual_review)
EXPECT = {
    "Test-Vincenti": ["won"] * 7,
    "Test-Perdenti": ["lost"] * 5,
    "Test-Manuali": ["manual_review"] * 3,
}
EXPECT_PICK = {"Test-Vincenti": "won", "Test-Perdenti": "lost", "Test-Manuali": "manual_review"}


async def main():
    from config_db import db
    import settlement as settle
    # inserisci record di test (rimuovo eventuale duplicato di test)
    await db.predictions.delete_one({"season": "2024-25", "round": 38, "_test": True})
    await db.predictions.insert_one(dict(TEST))
    try:
        res = await settle.compute_round("Serie A", "2024-25", 38, source="test", dry_run=True)
        print("=== SETTLEMENT DRY-RUN ===")
        print("ok:", res.get("ok"), "| provider:", res.get("provider"), "| eventi:", res.get("events_fetched"),
              "| api_calls:", res.get("api_calls"), "| retries:", res.get("retries"))
        print("summary (per giocata):", res.get("summary"))
        ok_all = True
        for d in res["detail"]:
            tip = d["tipster"]
            got_pick = d["status"]
            exp_pick = EXPECT_PICK.get(tip)
            pick_ok = got_pick == exp_pick
            ok_all = ok_all and pick_ok
            print(f"\n[{tip}] aggregata={got_pick} (atteso {exp_pick}) {'OK' if pick_ok else 'XXX'}")
            for i, s in enumerate(d["selections"]):
                got = s["settlement"]["status"]
                exp = EXPECT[tip][i] if i < len(EXPECT[tip]) else "?"
                mark = "OK" if got == exp else "XXX"
                if got != exp: ok_all = False
                sc = s.get("score")
                print(f"   {mark} {s['match']:24} | {s['market'][:22]:22} | {s['pick']:14} -> {got:14} (atteso {exp}) score={sc} reason={s['settlement'].get('reason','')[:40]}")
        # verifica che NON sia stato scritto nulla (dry-run)
        after = await db.predictions.find_one({"season": "2024-25", "round": 38, "_test": True})
        wrote = any(sel.get("settlement") for p in after.get("picks", []) for sel in p.get("selections", []))
        print("\n*** dry-run NON ha scritto settlement nel DB:", not wrote, "***")
        print("\n=== ESITO TEST:", "TUTTO OK" if ok_all and not wrote else "ANOMALIE", "===")
    finally:
        await db.predictions.delete_one({"season": "2024-25", "round": 38, "_test": True})
        print("(record di test rimosso)")


if __name__ == "__main__":
    asyncio.run(main())
