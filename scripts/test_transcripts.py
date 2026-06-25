"""Test trascrizioni: prende N episodi 'pending' e prova a scaricare i sottotitoli reali.
Non stampa MAI il testo dei sottotitoli (solo esito/lingua/lunghezza)."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


async def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    import youtube as yt
    import youtube_oauth as yto
    refresh = await yto.get_refresh_token()
    print("OAuth refresh token presente:", bool(refresh))
    st = await yto.get_status()
    print("connesso:", st["connected"], "| canale:", st.get("channel_title"))
    data = await yt.transcripts_list()
    print("conteggi stato:", data["counts"])
    pending = [e for e in data["episodes"] if e["transcription_status"] == "pending"]
    targets = pending[:n]
    print(f"\n--- Test su {len(targets)} episodi ---")
    for e in targets:
        print(f"\n> {e['title'][:60]}  (yt={e['youtube_id']})")
        res = await yt.fetch_transcript(e["slug"])
        print("  esito:", {k: v for k, v in res.items() if k not in ("text",)})


if __name__ == "__main__":
    asyncio.run(main())
