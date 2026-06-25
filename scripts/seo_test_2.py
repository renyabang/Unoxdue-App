import asyncio, sys, json
sys.path.insert(0,'/app/backend')

async def run(slug):
    import ai_transcript as ait
    await ait.ensure_bundle(slug)
    res = await ait.generate_preview(slug)
    return slug, res

async def main():
    slugs = [
        "quinto-appuntamento-di-unoxdue-live-studio-serie-a-33-giornata-calcio-pronostici",
        "decimo-appuntamento-di-unoxdue-live-studio-serie-a-38-giornata-calcio-pronostici",
    ]
    out = {}
    for s in slugs:
        slug, res = await run(s)
        if res.get("ok"):
            p = res["preview"]; m = p["meta"]
            out[slug] = {"ok": True, "model": m["model"], "fallback": m["fallback_used"],
                         "needs_review": m["needs_review"], "cost": m["cost_estimate"],
                         "n_chapters": len(p["chapters"]), "n_quotes": len(p["quotes"]),
                         "n_topics": len(p["topics"]), "type": p["type"],
                         "h1": p["h1"], "seo_title": p["seo_title"],
                         "meta_len": len(p["meta_description"] or ""),
                         "summary_paras": len(p["summary"]),
                         "people": p["entities"]["people"][:6], "teams": p["entities"]["teams"][:6]}
        else:
            out[slug] = {"ok": False, "error": res.get("error")}
        print("DONE", slug, out[slug].get("ok"))
    open('/app/scripts/seo_test_2.json','w').write(json.dumps(out, ensure_ascii=False, indent=2))
    print("WROTE /app/scripts/seo_test_2.json")

asyncio.run(main())
