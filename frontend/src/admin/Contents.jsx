import React, { useEffect, useMemo, useState } from "react";
import { ExternalLink, Trash2, RefreshCw, Sparkles, Loader2, Wand2, AlertTriangle } from "lucide-react";
import { api } from "./api";

const SITE = process.env.REACT_APP_BACKEND_URL;

const FILTERS = [
  { v: "all", l: "Tutti" },
  { v: "da_verificare", l: "Da verificare" },
  { v: "errore", l: "Errore" },
  { v: "non_elaborato", l: "Non elaborato" },
  { v: "elaborato", l: "Elaborato" },
  { v: "pubblicato", l: "Pubblicato" },
];

const aiState = (i) => {
  if (i.status === "da_verificare") return "da_verificare";
  if (i.ai && i.ai.status === "failed") return "errore";
  if (i.ai && i.ai.status === "ok") return "elaborato";
  return "non_elaborato";
};
const isProblem = (i) => aiState(i) === "da_verificare" || aiState(i) === "errore";

export default function Contents() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState({});
  const [batchBusy, setBatchBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState({});

  const load = async () => {
    setLoading(true);
    try { setItems(await api.episodes()); } catch (e) {}
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const toReviewCount = useMemo(() => items.filter((i) => i.status === "da_verificare").length, [items]);

  const view = useMemo(() => {
    let v = items.filter((i) => {
      if (filter === "all") return true;
      if (filter === "pubblicato") return i.status === "pubblicato";
      if (filter === "da_verificare") return i.status === "da_verificare";
      return aiState(i) === filter;
    });
    // contenuti problematici per primi
    return [...v].sort((a, b) => (isProblem(b) ? 1 : 0) - (isProblem(a) ? 1 : 0));
  }, [items, filter]);

  const selectedSlugs = Object.keys(selected).filter((k) => selected[k]);

  const del = async (slug) => {
    if (!window.confirm("Eliminare questo contenuto?")) return;
    await api.deleteEpisode(slug); load();
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

  const reprocessSelected = async () => {
    if (selectedSlugs.length === 0) return;
    setBatchBusy(true); setMsg("");
    try {
      const r = await api.aiProcessBatch({ slugs: selectedSlugs, limit: selectedSlugs.length });
      setMsg(`Rielaborati: ${r.succeeded} ok, ${r.failed} falliti su ${r.processed}.`);
      setSelected({}); await load();
    } catch (e) { setMsg("Errore: " + e.message); }
    finally { setBatchBusy(false); }
  };

  const statusColor = (s) =>
    s === "da_verificare" ? "bg-amber-100 text-amber-700"
      : s === "bozza" ? "bg-gray-100 text-gray-600" : "bg-green-100 text-green-700";

  const aiBadge = (i) => {
    const st = aiState(i);
    if (st === "elaborato") return <span className="text-xs font-bold px-2 py-1 rounded-full bg-emerald-100 text-emerald-700">Generato</span>;
    if (st === "errore") return <span className="text-xs font-bold px-2 py-1 rounded-full bg-red-100 text-red-700">Errore</span>;
    if (st === "da_verificare") return <span className="text-xs font-bold px-2 py-1 rounded-full bg-amber-100 text-amber-700">Da verificare</span>;
    return <span className="text-xs text-[#9c8b7d]">Non elaborato</span>;
  };

  return (
    <div data-testid="contents-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h1 className="font-anton text-3xl text-[#1a1411]">Contenuti</h1>
          {toReviewCount > 0 && (
            <button onClick={() => setFilter("da_verificare")} data-testid="badge-da-verificare"
              className="inline-flex items-center gap-1.5 bg-amber-100 text-amber-700 text-xs font-bold px-3 py-1.5 rounded-full hover:bg-amber-200">
              <AlertTriangle className="w-3.5 h-3.5" /> {toReviewCount} da verificare
            </button>
          )}
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <select value={filter} onChange={(e) => setFilter(e.target.value)} data-testid="content-filter"
            className="border border-[#ecdfce] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#EA4E1B]">
            {FILTERS.map((f) => <option key={f.v} value={f.v}>{f.l}</option>)}
          </select>
          {selectedSlugs.length > 0 && (
            <button onClick={reprocessSelected} disabled={batchBusy} data-testid="reprocess-selected-btn"
              className="inline-flex items-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60">
              {batchBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />} Rielabora selezionati ({selectedSlugs.length})
            </button>
          )}
          <button onClick={processBatch} disabled={batchBusy} data-testid="ai-batch-btn-contents"
            className="inline-flex items-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60">
            {batchBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />} Elabora archivio (AI)
          </button>
          <button onClick={load} className="inline-flex items-center gap-2 text-sm font-semibold text-[#EA4E1B]"><RefreshCw className="w-4 h-4" /> Aggiorna</button>
        </div>
      </div>

      {msg && <p data-testid="contents-msg" className="text-sm text-[#4a3d34] mt-3 bg-[#f4ebe1] border border-[#ecdfce] rounded-lg px-3 py-2">{msg}</p>}

      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[#fbf7f2] text-[#6b5d52] text-left">
            <tr>
              <th className="px-4 py-3 w-10"></th>
              <th className="px-4 py-3 font-semibold">Titolo</th>
              <th className="px-4 py-3 font-semibold">Tipo</th>
              <th className="px-4 py-3 font-semibold">Stato</th>
              <th className="px-4 py-3 font-semibold">AI</th>
              <th className="px-4 py-3 font-semibold">Azioni</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan="6" className="px-4 py-6 text-center text-[#9c8b7d]">Caricamento...</td></tr>}
            {!loading && view.length === 0 && <tr><td colSpan="6" className="px-4 py-6 text-center text-[#9c8b7d]">Nessun contenuto per questo filtro.</td></tr>}
            {!loading && view.map((i) => {
              const sec = i.type === "intervista" ? "interviste" : "episodi";
              return (
                <tr key={i.slug} className="border-t border-[#f0e7da]" data-testid={`content-row-${i.slug}`}>
                  <td className="px-4 py-3">
                    <input type="checkbox" checked={!!selected[i.slug]} data-testid={`content-check-${i.slug}`}
                      onChange={(e) => setSelected((s) => ({ ...s, [i.slug]: e.target.checked }))} />
                  </td>
                  <td className="px-4 py-3 text-[#1a1411] font-medium max-w-md">{i.title}</td>
                  <td className="px-4 py-3"><span className="capitalize text-[#6b5d52]">{i.type}</span></td>
                  <td className="px-4 py-3"><span className={`text-xs font-bold px-2 py-1 rounded-full ${statusColor(i.status)}`}>{i.status || "pubblicato"}</span></td>
                  <td className="px-4 py-3" data-testid={`ai-status-${i.slug}`}>{aiBadge(i)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button onClick={() => processOne(i.slug)} disabled={busy[i.slug]} data-testid={`ai-process-${i.slug}`}
                        className="text-[#EA4E1B] inline-flex items-center gap-1 disabled:opacity-50" title="Elabora con AI">
                        {busy[i.slug] ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                      </button>
                      <a href={`${SITE}/api/seo/${sec}/${i.slug}`} target="_blank" rel="noopener noreferrer" className="text-[#1a1411] hover:text-[#EA4E1B]" title="Anteprima SSR"><ExternalLink className="w-4 h-4" /></a>
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
