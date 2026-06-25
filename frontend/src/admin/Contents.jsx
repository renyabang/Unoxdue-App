import React, { useEffect, useState } from "react";
import { ExternalLink, Trash2, RefreshCw, Sparkles, Loader2, Wand2 } from "lucide-react";
import { api } from "./api";

const SITE = process.env.REACT_APP_BACKEND_URL;

export default function Contents() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState({});
  const [batchBusy, setBatchBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    setLoading(true);
    try { setItems(await api.episodes()); } catch (e) {}
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const del = async (slug) => {
    if (!window.confirm("Eliminare questo contenuto?")) return;
    await api.deleteEpisode(slug);
    load();
  };

  const processOne = async (slug) => {
    setBusy((b) => ({ ...b, [slug]: true })); setMsg("");
    try {
      const r = await api.aiProcess(slug);
      setMsg(r.ok ? `AI completata per "${slug}".` : `AI fallita: ${r.error || "errore"}`);
      await load();
    } catch (e) { setMsg("Errore AI: " + e.message); }
    finally { setBusy((b) => ({ ...b, [slug]: false })); }
  };

  const processBatch = async () => {
    setBatchBusy(true); setMsg("");
    try {
      const r = await api.aiProcessBatch({ only_missing: true, limit: 15 });
      setMsg(`Batch AI: ${r.succeeded} ok, ${r.failed} falliti su ${r.processed}. ${r.remaining_hint || ""}`);
      await load();
    } catch (e) { setMsg("Errore batch: " + e.message); }
    finally { setBatchBusy(false); }
  };

  const statusColor = (s) =>
    s === "da_verificare" ? "bg-amber-100 text-amber-700"
      : s === "bozza" ? "bg-gray-100 text-gray-600"
        : "bg-green-100 text-green-700";

  const aiBadge = (ai) => {
    if (!ai || !ai.status) return <span className="text-xs text-[#9c8b7d]">—</span>;
    if (ai.status === "ok") return <span className="text-xs font-bold px-2 py-1 rounded-full bg-emerald-100 text-emerald-700">Generato</span>;
    if (ai.status === "failed") return <span className="text-xs font-bold px-2 py-1 rounded-full bg-red-100 text-red-700">Errore</span>;
    return <span className="text-xs text-[#9c8b7d]">{ai.status}</span>;
  };

  return (
    <div data-testid="contents-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-anton text-3xl text-[#1a1411]">Contenuti</h1>
          <p className="text-[#6b5d52] mt-1">Episodi e interviste importati dal canale YouTube.</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={processBatch} disabled={batchBusy} data-testid="ai-batch-btn"
            className="inline-flex items-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
            {batchBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />} Elabora archivio (AI)
          </button>
          <button onClick={load} className="inline-flex items-center gap-2 text-sm font-semibold text-[#EA4E1B]">
            <RefreshCw className="w-4 h-4" /> Aggiorna
          </button>
        </div>
      </div>

      {msg && <p data-testid="contents-msg" className="text-sm text-[#4a3d34] mt-3 bg-[#f4ebe1] border border-[#ecdfce] rounded-lg px-3 py-2">{msg}</p>}

      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[#fbf7f2] text-[#6b5d52] text-left">
            <tr>
              <th className="px-4 py-3 font-semibold">Titolo</th>
              <th className="px-4 py-3 font-semibold">Tipo</th>
              <th className="px-4 py-3 font-semibold">Stato</th>
              <th className="px-4 py-3 font-semibold">AI</th>
              <th className="px-4 py-3 font-semibold">Azioni</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan="5" className="px-4 py-6 text-center text-[#9c8b7d]">Caricamento...</td></tr>}
            {!loading && items.map((i) => {
              const sec = i.type === "intervista" ? "interviste" : "episodi";
              return (
                <tr key={i.slug} className="border-t border-[#f0e7da]" data-testid={`content-row-${i.slug}`}>
                  <td className="px-4 py-3 text-[#1a1411] font-medium max-w-md">{i.title}</td>
                  <td className="px-4 py-3"><span className="capitalize text-[#6b5d52]">{i.type}</span></td>
                  <td className="px-4 py-3"><span className={`text-xs font-bold px-2 py-1 rounded-full ${statusColor(i.status)}`}>{i.status || "pubblicato"}</span></td>
                  <td className="px-4 py-3" data-testid={`ai-status-${i.slug}`}>{aiBadge(i.ai)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button onClick={() => processOne(i.slug)} disabled={busy[i.slug]} data-testid={`ai-process-${i.slug}`}
                        className="text-[#EA4E1B] inline-flex items-center gap-1 disabled:opacity-50" title="Elabora con AI">
                        {busy[i.slug] ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                      </button>
                      <a href={`${SITE}/api/seo/${sec}/${i.slug}`} target="_blank" rel="noopener noreferrer" className="text-[#1a1411] hover:text-[#EA4E1B] inline-flex items-center gap-1" title="Anteprima SSR"><ExternalLink className="w-4 h-4" /></a>
                      <button onClick={() => del(i.slug)} className="text-red-500" title="Elimina"><Trash2 className="w-4 h-4" /></button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
