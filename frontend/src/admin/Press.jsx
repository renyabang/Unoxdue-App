import React, { useEffect, useState } from "react";
import {
  Newspaper, Search, Loader2, ExternalLink, CheckCircle2, XCircle, AlertTriangle, Link2, Eye,
} from "lucide-react";
import { api } from "./api";

const ST = {
  found: { t: "Trovato", c: "bg-sky-100 text-sky-700" },
  verified: { t: "Verificato", c: "bg-indigo-100 text-indigo-700" },
  review: { t: "Da revisionare", c: "bg-[#fde7d6] text-[#c2410c]" },
  published: { t: "Pubblicato", c: "bg-green-100 text-green-700" },
  discarded: { t: "Scartato", c: "bg-gray-200 text-gray-600" },
  error: { t: "Errore", c: "bg-red-100 text-red-700" },
};
const FILTERS = ["", "found", "verified", "review", "published", "discarded", "error"];

const Badge = ({ s, tid }) => {
  const o = ST[s] || { t: s, c: "bg-gray-100 text-gray-600" };
  return <span data-testid={tid} className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full ${o.c}`}>{o.t}</span>;
};

export default function Press() {
  const [status, setStatus] = useState(null);
  const [counts, setCounts] = useState({});
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState("UnoXdue");
  const [filter, setFilter] = useState("");
  const [busy, setBusy] = useState("");
  const [runRes, setRunRes] = useState(null);
  const [preview, setPreview] = useState(null);

  const loadStatus = () => api.pressStatus().then((s) => { setStatus(s.provider); setCounts(s.counts || {}); }).catch(() => {});
  const loadList = (f) => api.pressList(f).then((d) => { setItems(d.items || []); setCounts(d.counts || {}); }).catch(() => {});

  useEffect(() => { loadStatus(); loadList(""); }, []);
  useEffect(() => { loadList(filter); /* eslint-disable-next-line */ }, [filter]);

  const run = async () => {
    setBusy("run"); setRunRes(null);
    try {
      const r = await api.pressRun(query);
      setRunRes(r);
      loadStatus(); loadList(filter);
    } catch (e) { setRunRes({ ok: false, error: e.message }); }
    setBusy("");
  };

  const setStatusFor = async (id, st) => {
    setBusy(`st-${id}`);
    try { await api.pressSetStatus(id, st); loadStatus(); loadList(filter); if (preview?.id === id) setPreview({ ...preview, status: st }); } catch (e) { /* noop */ }
    setBusy("");
  };

  const demo = status?.demo;

  return (
    <div data-testid="press-page">
      <div className="flex items-center gap-3">
        <Newspaper className="w-7 h-7 text-[#EA4E1B]" />
        <h1 className="font-anton text-3xl text-[#1a1411]">Rassegna stampa</h1>
        {demo && <span data-testid="press-demo-badge" className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full"><AlertTriangle className="w-3 h-3" /> Fixture (demo)</span>}
      </div>
      <p className="text-[#6b5d52] mt-1">Cerca menzioni reali di UnoXdue e dei suoi protagonisti. Salviamo solo metadati e una sintesi originale (mai il testo integrale). Dedup per URL, verifica raggiungibilità e anteprima prima della pubblicazione.</p>

      {/* Ricerca */}
      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] p-5">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[220px]">
            <label className="text-xs font-semibold text-[#6b5d52] uppercase">Query di ricerca</label>
            <input data-testid="press-query" value={query} onChange={(e) => setQuery(e.target.value)} className="w-full mt-1 border border-[#e2d4c2] rounded-lg px-3 py-2 text-sm" />
          </div>
          <button data-testid="press-run-btn" onClick={run} disabled={busy === "run"} className="inline-flex items-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
            {busy === "run" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Cerca rassegna
          </button>
        </div>
        {demo && <p className="text-amber-700 text-xs mt-2">{status?.note}</p>}
        {runRes && (
          <div data-testid="press-run-result" className="mt-3 text-sm bg-[#fbf7f2] rounded-lg p-3 text-[#4a3d34]">
            {runRes.ok ? (
              <span className="flex flex-wrap items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600" /> {runRes.found} nuovi · {runRes.updated} aggiornati · {runRes.skipped} curati saltati · {runRes.errors} errori
                {Object.entries(runRes.by_status || {}).map(([k, v]) => <span key={k} className="inline-flex items-center gap-1"><Badge s={k} /> {v}</span>)}
              </span>
            ) : <span className="text-red-600">Errore: {runRes.error}</span>}
          </div>
        )}
      </div>

      {/* Filtri */}
      <div className="mt-5 flex flex-wrap gap-2" data-testid="press-filters">
        {FILTERS.map((f) => (
          <button key={f || "all"} data-testid={`press-filter-${f || "all"}`} onClick={() => setFilter(f)} className={`text-xs font-bold uppercase tracking-wide px-3 py-1.5 rounded-full transition-colors ${filter === f ? "bg-[#14100e] text-white" : "bg-white border border-[#ecdfce] text-[#6b5d52] hover:bg-[#fbf7f2]"}`}>
            {f ? (ST[f]?.t || f) : "Tutti"}{counts[f] != null && f ? ` (${counts[f]})` : ""}
          </button>
        ))}
      </div>

      {/* Lista */}
      <div className="mt-4 grid lg:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-[#ecdfce] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="text-[#6b5d52] text-left bg-[#fbf7f2]">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Articolo</th>
                <th className="px-4 py-2.5 font-semibold">Stato</th>
                <th className="px-4 py-2.5 font-semibold text-right">Azioni</th>
              </tr>
            </thead>
            <tbody data-testid="press-table">
              {items.map((p) => (
                <tr key={p.id} className="border-t border-[#f0e7da] hover:bg-[#fbf7f2]" data-testid={`press-row-${p.id}`}>
                  <td className="px-4 py-3">
                    <p className="font-semibold text-[#1a1411] leading-tight">{p.title}</p>
                    <p className="text-xs text-[#6b5d52] mt-0.5">{p.source} · {p.date}
                      {p.reachable === false && <span className="ml-1 text-red-600 inline-flex items-center gap-0.5"><XCircle className="w-3 h-3" /> irraggiungibile</span>}
                      {p.linked && <span className="ml-1 text-indigo-600 inline-flex items-center gap-0.5"><Link2 className="w-3 h-3" /> {p.linked.title}</span>}
                    </p>
                  </td>
                  <td className="px-4 py-3"><Badge s={p.status} tid={`press-status-${p.id}`} /></td>
                  <td className="px-4 py-3 text-right">
                    <button data-testid={`press-preview-${p.id}`} onClick={() => setPreview(p)} className="inline-flex items-center gap-1 text-xs font-bold uppercase text-[#EA4E1B] hover:text-[#d3430f]">
                      <Eye className="w-3.5 h-3.5" /> Anteprima
                    </button>
                  </td>
                </tr>
              ))}
              {items.length === 0 && <tr><td colSpan={3} className="px-4 py-5 text-[#6b5d52]">Nessun articolo. Avvia una ricerca.</td></tr>}
            </tbody>
          </table>
        </div>

        {/* Anteprima */}
        <div className="bg-white rounded-xl border border-[#ecdfce] p-5">
          {!preview && <p className="text-[#9c8b7d] text-sm">Seleziona un articolo per l'anteprima prima della pubblicazione.</p>}
          {preview && (
            <div data-testid="press-preview">
              <div className="flex items-center gap-2 mb-2"><Badge s={preview.status} /> {preview.confidence != null && <span className="text-xs text-[#6b5d52]">confidence {Math.round(preview.confidence * 100)}%</span>}</div>
              <h3 className="font-archivo font-extrabold text-[#1a1411] leading-tight">{preview.title}</h3>
              <p className="text-xs text-[#6b5d52] mt-1">{preview.source} · {preview.date}</p>
              <p className="text-sm text-[#4a3d34] mt-3">{preview.summary}</p>
              <a href={preview.url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex items-center gap-1.5 text-sm text-[#EA4E1B] hover:text-[#d3430f] break-all"><ExternalLink className="w-3.5 h-3.5" /> {preview.url}</a>
              {preview.linked && <p className="mt-2 text-xs text-indigo-600 inline-flex items-center gap-1"><Link2 className="w-3.5 h-3.5" /> Collegato a: {preview.linked.title} ({preview.linked.type})</p>}
              <div className="mt-5 flex flex-wrap gap-2">
                <button data-testid="press-publish-btn" onClick={() => setStatusFor(preview.id, "published")} disabled={busy === `st-${preview.id}`} className="inline-flex items-center gap-1.5 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-xs font-bold uppercase tracking-wide px-3 py-2 rounded-lg disabled:opacity-60">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Pubblica
                </button>
                <button data-testid="press-verify-btn" onClick={() => setStatusFor(preview.id, "verified")} disabled={busy === `st-${preview.id}`} className="inline-flex items-center gap-1.5 border border-[#e2d4c2] text-[#4a3d34] hover:bg-[#fbf7f2] text-xs font-bold uppercase tracking-wide px-3 py-2 rounded-lg disabled:opacity-60">
                  Verifica
                </button>
                <button data-testid="press-discard-btn" onClick={() => setStatusFor(preview.id, "discarded")} disabled={busy === `st-${preview.id}`} className="inline-flex items-center gap-1.5 border border-[#e2d4c2] text-[#c2410c] hover:bg-[#fff5ef] text-xs font-bold uppercase tracking-wide px-3 py-2 rounded-lg disabled:opacity-60">
                  <XCircle className="w-3.5 h-3.5" /> Scarta
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
