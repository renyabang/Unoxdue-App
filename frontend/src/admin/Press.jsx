import React, { useEffect, useState } from "react";
import {
  Newspaper, Search, Loader2, ExternalLink, CheckCircle2, XCircle, AlertTriangle, Link2, Eye,
  History, Ban, ChevronDown, Plus,
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
  const [mode, setMode] = useState("ordinary");
  const [manualQuery, setManualQuery] = useState("");
  const [filter, setFilter] = useState("");
  const [busy, setBusy] = useState("");
  const [runRes, setRunRes] = useState(null);
  const [preview, setPreview] = useState(null);
  const [linkOptions, setLinkOptions] = useState([]);
  const [runs, setRuns] = useState([]);
  const [rejected, setRejected] = useState([]);
  const [rejCounts, setRejCounts] = useState({});
  const [showRejected, setShowRejected] = useState(false);

  const loadStatus = () => api.pressStatus().then((s) => { setStatus(s.provider); setCounts(s.counts || {}); }).catch(() => {});
  const loadList = (f) => api.pressList(f).then((d) => { setItems(d.items || []); setCounts(d.counts || {}); }).catch(() => {});
  const loadRuns = () => api.pressRuns(8).then((d) => setRuns(d.runs || [])).catch(() => {});
  const loadRejected = () => api.pressRejected().then((d) => { setRejected(d.items || []); setRejCounts(d.counts || {}); }).catch(() => {});
  const refresh = async () => {
    try {
      const d = await api.pressList(filter);
      setItems(d.items || []); setCounts(d.counts || {});
      setPreview((prev) => prev ? ((d.items || []).find((x) => x.id === prev.id) || prev) : prev);
    } catch (e) { /* noop */ }
    loadStatus(); loadRuns(); loadRejected();
  };

  useEffect(() => {
    loadStatus(); loadList(""); loadRuns(); loadRejected();
    api.pressLinkOptions().then((d) => setLinkOptions(d.options || [])).catch(() => {});
  }, []);
  useEffect(() => { loadList(filter); /* eslint-disable-next-line */ }, [filter]);

  const run = async () => {
    setBusy("run"); setRunRes(null);
    try {
      const r = await api.pressRun({ mode, query: manualQuery.trim() || undefined });
      setRunRes(r);
      refresh();
    } catch (e) { setRunRes({ ok: false, error: e.message }); }
    setBusy("");
  };

  const setStatusFor = async (id, st) => {
    setBusy(`st-${id}`);
    try { await api.pressSetStatus(id, st); await refresh(); } catch (e) { /* noop */ }
    setBusy("");
  };

  const addLink = async (item, optValue) => {
    const opt = linkOptions.find((o) => `${o.type}|${o.slug}` === optValue);
    if (!opt) return;
    setBusy(`link-${item.id}`);
    try { await api.pressLink({ id: item.id, action: "add", type: opt.type, slug: opt.slug, title: opt.title }); await refresh(); } catch (e) { /* noop */ }
    setBusy("");
  };

  const removeLink = async (item, l) => {
    setBusy(`link-${item.id}`);
    try { await api.pressLink({ id: item.id, action: "remove", type: l.type, slug: l.slug }); await refresh(); } catch (e) { /* noop */ }
    setBusy("");
  };

  const confirmSuggested = async (item, l) => {
    setBusy(`link-${item.id}`);
    try { await api.pressLink({ id: item.id, action: "add", type: l.type, slug: l.slug, title: l.title }); await refresh(); } catch (e) { /* noop */ }
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
          <div>
            <label className="text-xs font-semibold text-[#6b5d52] uppercase">Finestra temporale</label>
            <div className="flex gap-1.5 mt-1" data-testid="press-mode">
              {[
                { v: "ordinary", t: "Ordinaria · 30gg" },
                { v: "weekly", t: "Estesa · 90gg" },
                { v: "backfill", t: "Backfill · 24 mesi" },
              ].map((m) => (
                <button key={m.v} data-testid={`press-mode-${m.v}`} onClick={() => setMode(m.v)}
                  className={`text-xs font-bold uppercase tracking-wide px-3 py-2 rounded-lg transition-colors ${mode === m.v ? "bg-[#14100e] text-white" : "bg-white border border-[#ecdfce] text-[#6b5d52] hover:bg-[#fbf7f2]"}`}>
                  {m.t}
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1 min-w-[220px]">
            <label className="text-xs font-semibold text-[#6b5d52] uppercase">Query manuale (opzionale)</label>
            <input data-testid="press-query" value={manualQuery} onChange={(e) => setManualQuery(e.target.value)} placeholder='Vuoto = query automatiche (brand, team, ospiti)' className="w-full mt-1 border border-[#e2d4c2] rounded-lg px-3 py-2 text-sm" />
          </div>
          <button data-testid="press-run-btn" onClick={run} disabled={busy === "run"} className="inline-flex items-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
            {busy === "run" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Cerca rassegna
          </button>
        </div>
        <p className="text-[#6b5d52] text-xs mt-2">Nessuna pubblicazione automatica: i risultati restano in <b>Trovato</b> o <b>Da revisionare</b>. Esclusi i social e i duplicati; i falsi positivi non vengono associati.</p>
        {busy === "run" && <p className="text-[#6b5d52] text-xs mt-1 inline-flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Ricerca reale in corso (può richiedere ~30-60s)…</p>}
        {runRes && (
          <div data-testid="press-run-result" className="mt-3 text-sm bg-[#fbf7f2] rounded-lg p-3 text-[#4a3d34]">
            {runRes.ok ? (
              <div>
                <p className="font-semibold text-[#1a1411] inline-flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-green-600" /> Ricerca completata · {runRes.window_label}</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
                  {[
                    ["Query eseguite", runRes.stats?.queries_executed],
                    ["Risultati grezzi", runRes.stats?.raw_found],
                    ["Duplicati", runRes.stats?.duplicates],
                    ["Social esclusi", runRes.stats?.social_excluded],
                    ["Pagine non-articolo", runRes.stats?.non_article_excluded],
                    ["URL irraggiungibili", runRes.stats?.unreachable],
                    ["Falsi positivi", runRes.stats?.false_positives],
                    ["Validi", runRes.stats?.valid],
                    ["Salvati in revisione", runRes.stats?.saved_in_review],
                    [`Costo (${runRes.stats?.cost_source || "n/d"})`, `$${runRes.stats?.cost_usd ?? 0}`],
                  ].map(([k, v]) => (
                    <div key={k} className="bg-white rounded-lg border border-[#ecdfce] px-3 py-2">
                      <p className="text-[10px] uppercase tracking-wide text-[#9c8b7d]">{k}</p>
                      <p className="font-bold text-[#1a1411]">{v ?? 0}</p>
                    </div>
                  ))}
                </div>
                <p className="text-[11px] text-[#9c8b7d] mt-2">Categorie esclusive: grezzi − duplicati = unici = social + non-articolo + irraggiungibili + falsi positivi + validi. {runRes.stats?.funnel_balanced ? "✓ funnel coerente" : "⚠ verifica funnel"}</p>
              </div>
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
                      {p.links && p.links.length > 0 && <span className="ml-1 text-indigo-600 inline-flex items-center gap-0.5"><Link2 className="w-3 h-3" /> {p.links[0].title}{p.links.length > 1 ? ` +${p.links.length - 1}` : ""}</span>}
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
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <Badge s={preview.status} />
                {preview.confidence != null && <span className="text-xs text-[#6b5d52]">confidence {Math.round(preview.confidence * 100)}%</span>}
                {preview.relevant === false && <span data-testid="press-false-positive" className="text-[10px] font-bold uppercase tracking-wide bg-red-100 text-red-700 px-2 py-0.5 rounded-full">Falso positivo</span>}
              </div>
              {preview.status_reason && <p data-testid="press-reason" className="text-xs text-[#6b5d52] mb-2 italic">Motivo: {preview.status_reason}</p>}
              <h3 className="font-archivo font-extrabold text-[#1a1411] leading-tight">{preview.title}</h3>
              <p className="text-xs text-[#6b5d52] mt-1">{preview.source} · {preview.date}</p>
              <p className="text-sm text-[#4a3d34] mt-3">{preview.summary}</p>
              <a href={preview.url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex items-center gap-1.5 text-sm text-[#EA4E1B] hover:text-[#d3430f] break-all"><ExternalLink className="w-3.5 h-3.5" /> {preview.url}</a>

              <div className="mt-4 pt-4 border-t border-[#f0e7da]">
                <p className="text-xs font-semibold text-[#6b5d52] uppercase tracking-wide mb-2">Contenuti collegati</p>
                <div className="flex flex-wrap gap-1.5 mb-2" data-testid="press-links">
                  {(preview.links || []).length === 0 && <span className="text-xs text-[#9c8b7d]">Nessun collegamento.</span>}
                  {(preview.links || []).map((l, i) => (
                    <span key={i} className="inline-flex items-center gap-1.5 text-xs bg-indigo-50 text-indigo-700 border border-indigo-100 rounded-full pl-2.5 pr-1 py-0.5" data-testid={`press-link-${l.type}-${l.slug}`}>
                      <Link2 className="w-3 h-3" /> {l.title} <span className="text-indigo-400">({l.source || "auto"})</span>
                      <button onClick={() => removeLink(preview, l)} disabled={busy === `link-${preview.id}`} className="ml-0.5 text-indigo-400 hover:text-red-600" data-testid={`press-link-remove-${l.type}-${l.slug}`}><XCircle className="w-3.5 h-3.5" /></button>
                    </span>
                  ))}
                </div>
                <select data-testid="press-link-add" value="" onChange={(e) => e.target.value && addLink(preview, e.target.value)} disabled={busy === `link-${preview.id}`} className="w-full text-xs border border-[#e2d4c2] rounded-lg px-2 py-2">
                  <option value="">+ Aggiungi collegamento manuale…</option>
                  {linkOptions.map((o) => <option key={`${o.type}|${o.slug}`} value={`${o.type}|${o.slug}`}>{`[${o.type}] ${o.title}`}</option>)}
                </select>

                {(preview.suggested || []).length > 0 && (
                  <div className="mt-3" data-testid="press-suggested">
                    <p className="text-xs font-semibold text-[#6b5d52] uppercase tracking-wide mb-1.5">Suggeriti (da confermare)</p>
                    <div className="flex flex-wrap gap-1.5">
                      {preview.suggested.map((l, i) => (
                        <span key={i} className="inline-flex items-center gap-1.5 text-xs bg-amber-50 text-amber-800 border border-amber-200 rounded-full pl-2.5 pr-1 py-0.5" data-testid={`press-suggested-${l.type}-${l.slug}`}>
                          {l.title}
                          <button onClick={() => confirmSuggested(preview, l)} disabled={busy === `link-${preview.id}`} className="ml-0.5 text-amber-600 hover:text-green-600" title="Conferma collegamento" data-testid={`press-suggested-confirm-${l.type}-${l.slug}`}><Plus className="w-3.5 h-3.5" /></button>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

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

      {/* Riepilogo esecuzioni */}
      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] p-5" data-testid="press-runs">
        <div className="flex items-center gap-2 mb-3">
          <History className="w-4 h-4 text-[#EA4E1B]" />
          <h2 className="font-archivo font-extrabold text-[#1a1411] text-sm uppercase tracking-wide">Ultime esecuzioni</h2>
        </div>
        {runs.length === 0 && <p className="text-[#9c8b7d] text-sm">Nessuna esecuzione registrata.</p>}
        {runs.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-[#9c8b7d] text-left">
                <tr>
                  <th className="py-1.5 pr-3 font-semibold">Quando</th>
                  <th className="py-1.5 pr-3 font-semibold">Finestra</th>
                  <th className="py-1.5 pr-3 font-semibold">Trigger</th>
                  <th className="py-1.5 pr-3 font-semibold">Query</th>
                  <th className="py-1.5 pr-3 font-semibold">Validi</th>
                  <th className="py-1.5 pr-3 font-semibold">Falsi pos.</th>
                  <th className="py-1.5 pr-3 font-semibold">Salvati</th>
                  <th className="py-1.5 pr-3 font-semibold">Errori</th>
                  <th className="py-1.5 pr-3 font-semibold">Costo</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id} className="border-t border-[#f0e7da]">
                    <td className="py-1.5 pr-3 text-[#4a3d34]">{(r.at || "").slice(0, 16).replace("T", " ")}</td>
                    <td className="py-1.5 pr-3">{r.window_label}</td>
                    <td className="py-1.5 pr-3">{r.trigger}</td>
                    <td className="py-1.5 pr-3">{r.queries_count}</td>
                    <td className="py-1.5 pr-3 font-semibold">{r.stats?.valid ?? 0}</td>
                    <td className="py-1.5 pr-3">{r.stats?.false_positives ?? 0}</td>
                    <td className="py-1.5 pr-3">{r.stats?.saved_in_review ?? 0}</td>
                    <td className="py-1.5 pr-3">{(r.errors || []).length}</td>
                    <td className="py-1.5 pr-3">${r.stats?.cost_usd ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Log tecnico scartati */}
      <div className="mt-4 bg-white rounded-xl border border-[#ecdfce] p-5" data-testid="press-rejected">
        <button onClick={() => setShowRejected((v) => !v)} className="w-full flex items-center justify-between" data-testid="press-rejected-toggle">
          <span className="flex items-center gap-2">
            <Ban className="w-4 h-4 text-[#9c8b7d]" />
            <span className="font-archivo font-extrabold text-[#1a1411] text-sm uppercase tracking-wide">Log tecnico (scartati)</span>
            <span className="text-xs text-[#9c8b7d]">
              {Object.entries(rejCounts).map(([k, v]) => `${k}: ${v}`).join(" · ") || "vuoto"}
            </span>
          </span>
          <ChevronDown className={`w-4 h-4 text-[#9c8b7d] transition-transform ${showRejected ? "rotate-180" : ""}`} />
        </button>
        {showRejected && (
          <div className="mt-3 max-h-80 overflow-y-auto">
            <p className="text-[11px] text-[#9c8b7d] mb-2">Risultati non editoriali (falsi positivi, pagine non-articolo, URL irraggiungibili). Solo per audit tecnico, non mostrati nel sito.</p>
            <table className="w-full text-xs">
              <tbody>
                {rejected.slice(0, 100).map((r) => (
                  <tr key={r.id} className="border-t border-[#f0e7da]" data-testid={`press-rejected-row-${r.id}`}>
                    <td className="py-1.5 pr-2"><span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">{r.category}</span></td>
                    <td className="py-1.5 pr-2 text-[#6b5d52] whitespace-nowrap">{r.source}</td>
                    <td className="py-1.5 pr-2 text-[#4a3d34]">{(r.title || "").slice(0, 70)}</td>
                    <td className="py-1.5 pr-2 text-[#9c8b7d]">{r.reason}</td>
                  </tr>
                ))}
                {rejected.length === 0 && <tr><td className="py-2 text-[#9c8b7d]">Nessun elemento scartato.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
